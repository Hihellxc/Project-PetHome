"""
PetHome - ระบบรับเลี้ยงสัตว์
Backend: Flask + MySQL
"""

import os
import cloudinary
import cloudinary.uploader
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash #แอดมินไม่เห็นรหัสของผู้ใช้
from werkzeug.utils import secure_filename


load_dotenv() # โหลด environment variables จากไฟล์ .env (สำหรับรันในเครื่องตัวเอง)
cloudinary.config( #ในการอัปโหลดรูปภาพไปเก็บบน Cloudinary (ไม่ต้องเก็บไว้ในเครื่องตัวเอง)
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)
# ---------- ตั้งค่าเบื้องต้น ----------
app = Flask(__name__)
# อ่าน secret key จาก environment variable ก่อน ถ้าไม่มีค่อยใช้ค่า default (สำหรับรันในเครื่องตัวเอง)
app.secret_key = os.environ.get("SECRET_KEY", "pethome-secret-key")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# หมายเหตุสำคัญ:
# แพลตฟอร์ม cloud อย่าง Aiven จะสร้างฐานข้อมูล MySQL ให้ แล้วให้ค่าการเชื่อมต่อมา
# เราตั้งให้อ่านค่าจาก environment variable ก่อนเสมอ ถ้าไม่มี (เช่นตอนรันในเครื่องตัวเอง)
# ค่อย fallback ไปใช้ค่าเดิมที่ตั้งไว้สำหรับ localhost
DB_CONFIG = {
    "host": os.environ.get("MYSQLHOST", "localhost"),
    "port": int(os.environ.get("MYSQLPORT", 3306)),
    "user": os.environ.get("MYSQLUSER", "root"),
    "password": os.environ.get("MYSQLPASSWORD", "123456"),
    "database": os.environ.get("MYSQLDATABASE", "pethome"),
}

# Aiven (และผู้ให้บริการ MySQL บนคลาวด์ส่วนใหญ่) บังคับให้เชื่อมต่อผ่าน SSL เท่านั้น
# หมายเหตุ: เดิมเคยตั้งให้ตรวจสอบใบรับรอง (ssl_verify_cert=True) ด้วยไฟล์ ca.pem
# แต่พบว่าทำให้เกิด error "SSL routines::certificate verify failed" ทั้งตอนรันในเครื่อง
# และตอน deploy บน Render (สาเหตุมักมาจากใบรับรองไม่ตรงเวอร์ชัน/หมุนใหม่/ปัญหาการตรวจสอบ
# บนระบบปฏิบัติการที่ต่างกัน) จึงเปลี่ยนมาใช้ "เชื่อมต่อแบบเข้ารหัส แต่ไม่ตรวจสอบใบรับรอง"
# แทน ข้อมูลยังถูกเข้ารหัสระหว่างทางเหมือนเดิม (ปลอดภัยเพียงพอสำหรับโปรเจกต์นี้)
# แค่ไม่ต้องพึ่งไฟล์ ca.pem อีกต่อไป
DB_CONFIG["ssl_disabled"] = False
DB_CONFIG["ssl_verify_cert"] = False
DB_CONFIG["ssl_verify_identity"] = False

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"} #อนุญาตให้อัปโหลดเฉพาะไฟล์รูป

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# รายชื่อ 77 จังหวัดของไทย ใช้แสดงเป็นตัวเลือกในช่องกรอกจังหวัด (พิมพ์ค้นหาได้ผ่าน <datalist>)
THAI_PROVINCES = [
    "กรุงเทพมหานคร", "กระบี่", "กาญจนบุรี", "กาฬสินธุ์", "กำแพงเพชร",
    "ขอนแก่น", "จันทบุรี", "ฉะเชิงเทรา", "ชลบุรี", "ชัยนาท",
    "ชัยภูมิ", "ชุมพร", "เชียงราย", "เชียงใหม่", "ตรัง",
    "ตราด", "ตาก", "นครนายก", "นครปฐม", "นครพนม",
    "นครราชสีมา", "นครศรีธรรมราช", "นครสวรรค์", "นนทบุรี", "นราธิวาส",
    "น่าน", "บึงกาฬ", "บุรีรัมย์", "ปทุมธานี", "ประจวบคีรีขันธ์",
    "ปราจีนบุรี", "ปัตตานี", "พระนครศรีอยุธยา", "พังงา", "พัทลุง",
    "พิจิตร", "พิษณุโลก", "เพชรบุรี", "เพชรบูรณ์", "แพร่",
    "ภูเก็ต", "มหาสารคาม", "มุกดาหาร", "แม่ฮ่องสอน", "ยโสธร",
    "ยะลา", "ร้อยเอ็ด", "ระนอง", "ระยอง", "ราชบุรี",
    "ลพบุรี", "ลำปาง", "ลำพูน", "เลย", "ศรีสะเกษ",
    "สกลนคร", "สงขลา", "สตูล", "สมุทรปราการ", "สมุทรสงคราม",
    "สมุทรสาคร", "สระแก้ว", "สระบุรี", "สิงห์บุรี", "สุโขทัย",
    "สุพรรณบุรี", "สุราษฎร์ธานี", "สุรินทร์", "หนองคาย", "หนองบัวลำภู",
    "อยุธยา", "อ่างทอง", "อำนาจเจริญ", "อุดรธานี", "อุตรดิตถ์",
    "อุทัยธานี", "อุบลราชธานี",
]

# สร้างโฟลเดอร์เก็บรูปภาพไว้ล่วงหน้าเสมอ (เผื่อโฟลเดอร์ถูกลบ หรือรันครั้งแรกในเครื่องใหม่)
# ถ้าไม่มีบรรทัดนี้ และโฟลเดอร์นี้ไม่มีอยู่จริง การอัปโหลดรูปจะทำให้ทั้งคำขอ error
# และส่งผลให้ข้อมูลสัตว์เลี้ยงไม่ถูกบันทึกลงฐานข้อมูลเลย (แม้กรอกข้อมูลถูกต้องก็ตาม)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------- ฟังก์ชันช่วยเหลือ (Helper) ----------

def get_db():
    """เปิดการเชื่อมต่อ MySQL"""
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn


def init_db():
    """สร้างตารางฐานข้อมูล ถ้ายังไม่มี (รันครั้งแรกครั้งเดียว)"""
    conn = get_db()
    cur = conn.cursor()

    # ตาราง User
    # หมายเหตุ: MySQL ใช้ "AUTO_INCREMENT" (มีขีดล่าง) ไม่ใช่ "AUTOINCREMENT" แบบ SQLite
    # และคอลัมน์ที่จะใช้ UNIQUE ต้องเป็น VARCHAR (กำหนดความยาว) ไม่ใช่ TEXT
    cur.execute("""
        CREATE TABLE IF NOT EXISTS User (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)

    # ตาราง Pet
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Pet (
            pet_id INT AUTO_INCREMENT PRIMARY KEY,
            owner_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            gender VARCHAR(20) NOT NULL,
            age INT NOT NULL,
            province VARCHAR(100) NOT NULL,
            description TEXT,
            image VARCHAR(255),
            status VARCHAR(20) DEFAULT 'Available',
            created_at DATETIME,
            FOREIGN KEY (owner_id) REFERENCES User(user_id)
        )
    """)

    # ตาราง Adoption
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Adoption (
            request_id INT AUTO_INCREMENT PRIMARY KEY,
            pet_id INT NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            email VARCHAR(150),
            province VARCHAR(100),
            occupation VARCHAR(100),
            pet_experience VARCHAR(20),
            housing_type VARCHAR(50),
            household_info TEXT,
            message TEXT,
            status VARCHAR(20) DEFAULT 'Pending',
            created_at DATETIME,
            FOREIGN KEY (pet_id) REFERENCES Pet(pet_id)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def allowed_file(filename):
    """เช็คนามสกุลไฟล์รูปที่อนุญาต"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def login_required(view_func):
    """Decorator: ต้อง login ก่อนถึงจะเข้าหน้านี้ได้"""
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("กรุณาเข้าสู่ระบบก่อน")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ---------- หน้า Home + ค้นหา ----------

@app.route("/")
def home():
    pet_type = request.args.get("type", "")
    province = request.args.get("province", "")

    conn = get_db()

    # ตรวจสอบว่า Render กำลังใช้ Database ตัวไหน
    debug_cursor = conn.cursor()
    debug_cursor.execute("SELECT DATABASE(), @@hostname")
    db_info = debug_cursor.fetchone()
    print("================================")
    print("DATABASE:", db_info[0])
    print("HOST:", db_info[1])

    debug_cursor.execute("SELECT COUNT(*) FROM Pet")
    pet_count = debug_cursor.fetchone()[0]
    print("PET COUNT:", pet_count)
    print("================================")

    debug_cursor.close()

    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM Pet WHERE status = 'Available'"
    params = []

    if pet_type:
        query += " AND type = %s"
        params.append(pet_type)

    if province:
        query += " AND province LIKE %s"
        params.append(f"%{province}%")

    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    pets = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "home.html",
        pets=pets,
        pet_type=pet_type,
        province=province,
        provinces=THAI_PROVINCES
    )
# ---------- สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO User (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password),
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash("สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            cursor.close()
            conn.close()
            flash("อีเมลนี้ถูกใช้งานแล้ว")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            flash(f"ยินดีต้อนรับ {user['name']}")
            return redirect(url_for("home"))
        else:
            flash("อีเมลหรือรหัสผ่านไม่ถูกต้อง")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("ออกจากระบบแล้ว")
    return redirect(url_for("home"))


# ---------- ลงประกาศสัตว์ (CRUD) ----------

@app.route("/add_pet", methods=["GET", "POST"])
@login_required
def add_pet():
    if request.method == "POST":
        name = request.form["name"]
        pet_type = request.form["type"]
        gender = request.form["gender"]
        age = request.form["age"]
        province = request.form["province"]
        description = request.form["description"]

        # จัดการไฟล์รูปภาพ
        # หมายเหตุ: ถ้าการบันทึกรูปเกิดปัญหา (เช่น โฟลเดอร์หาย, ไฟล์เสีย)
        # เราจะ "ไม่ปล่อยให้ error ล้มทั้งคำขอ" แต่จะบันทึกประกาศต่อไปโดยไม่มีรูป
        # แล้วแจ้งเตือนผู้ใช้ให้รู้ตัว
        image_file = request.files.get("image")
        image_filename = ""
        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                try:
                    upload_result = cloudinary.uploader.upload(image_file)
                    image_url = upload_result["secure_url"]

                    image_file.seek(0)
                    local_filename = secure_filename(image_file.filename)
                    image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], local_filename))

                except Exception:
                    image_filename = ""
                    flash("อัปโหลดรูปภาพไม่สำเร็จ แต่ข้อมูลอื่นถูกบันทึกแล้ว กรุณาแก้ไขประกาศเพื่อเพิ่มรูปใหม่")
            else:
                flash("ไฟล์รูปภาพต้องเป็นนามสกุล png, jpg, jpeg หรือ gif เท่านั้น (บันทึกประกาศโดยไม่มีรูป)")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO Pet (owner_id, name, type, gender, age, province,
               description, image, status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Available', %s)""",
            # หมายเหตุ: ส่ง datetime.now() เป็น object ตรงๆ แทนการแปลงเป็น string ด้วย isoformat()
            # เพราะ isoformat() คั่นวันที่กับเวลาด้วยตัว "T" (เช่น 2026-01-01T12:00:00)
            # ซึ่งคอลัมน์ประเภท DATETIME ของ MySQL ไม่รับรูปแบบนี้โดยตรง ต้องให้ driver แปลงให้เอง
            (session["user_id"], name, pet_type, gender, age, province,
             description, image_filename, datetime.now()),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("เพิ่มประกาศสำเร็จ")
        return redirect(url_for("my_pets"))

    return render_template("add_pet.html", provinces=THAI_PROVINCES)


@app.route("/edit_pet/<int:pet_id>", methods=["GET", "POST"])
@login_required
def edit_pet(pet_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Pet WHERE pet_id = %s", (pet_id,))
    pet = cursor.fetchone()

    # เช็คว่าเป็นเจ้าของประกาศจริงหรือไม่
    if pet is None or pet["owner_id"] != session["user_id"]:
        cursor.close()
        conn.close()
        flash("ไม่พบประกาศ หรือคุณไม่มีสิทธิ์แก้ไข")
        return redirect(url_for("my_pets"))

    if request.method == "POST":
        name = request.form["name"]
        pet_type = request.form["type"]
        gender = request.form["gender"]
        age = request.form["age"]
        province = request.form["province"]
        description = request.form["description"]
        status = request.form["status"]

        image_filename = pet["image"]
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                try:
                    upload_result = cloudinary.uploader.upload(image_file)
                    image_filename = upload_result["secure_url"]
                except Exception:
                    flash("อัปโหลดรูปภาพใหม่ไม่สำเร็จ ระบบใช้รูปเดิมไว้ก่อน")
            else:
                flash("ไฟล์รูปภาพต้องเป็นนามสกุล png, jpg, jpeg หรือ gif เท่านั้น (ใช้รูปเดิมไว้ก่อน)")

        # หมายเหตุ: connection object ของ mysql.connector ไม่มีเมธอด .execute()
        # ต้องสั่งผ่าน cursor เท่านั้น (ใช้ cursor ตัวเดิมที่เปิดไว้ด้านบนได้เลย)
        cursor.execute(
            """UPDATE Pet SET name=%s, type=%s, gender=%s, age=%s, province=%s,
               description=%s, image=%s, status=%s WHERE pet_id=%s""",
            (name, pet_type, gender, age, province, description,
             image_filename, status, pet_id),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("แก้ไขประกาศสำเร็จ")
        return redirect(url_for("my_pets"))

    cursor.close()
    conn.close()
    return render_template("edit_pet.html", pet=pet, provinces=THAI_PROVINCES)


@app.route("/delete_pet/<int:pet_id>")
@login_required
def delete_pet(pet_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Pet WHERE pet_id = %s", (pet_id,))
    pet = cursor.fetchone()

    if pet and pet["owner_id"] == session["user_id"]:
        cursor.execute("DELETE FROM Adoption WHERE pet_id = %s", (pet_id,))
        cursor.execute("DELETE FROM Pet WHERE pet_id = %s", (pet_id,))
        conn.commit()
        flash("ลบประกาศสำเร็จ")
    else:
        flash("คุณไม่มีสิทธิ์ลบประกาศนี้")

    cursor.close()
    conn.close()
    return redirect(url_for("my_pets"))


@app.route("/my_pets")
@login_required
def my_pets():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM Pet WHERE owner_id = %s ORDER BY created_at DESC",
        (session["user_id"],),
    )
    pets = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("my_pets.html", pets=pets)


# ---------- หน้ารายละเอียดสัตว์ ----------

@app.route("/pet/<int:pet_id>")
def pet_detail(pet_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT Pet.*, User.name AS owner_name, User.email AS owner_email
           FROM Pet JOIN User ON Pet.owner_id = User.user_id
           WHERE Pet.pet_id = %s""",
        (pet_id,),
    )
    pet = cursor.fetchone()
    cursor.close()
    conn.close()

    if pet is None:
        flash("ไม่พบประกาศนี้")
        return redirect(url_for("home"))

    return render_template("pet_detail.html", pet=pet, provinces=THAI_PROVINCES)


# ---------- ส่งคำขอรับเลี้ยง ----------

@app.route("/pet/<int:pet_id>/adopt", methods=["POST"])
def send_adoption_request(pet_id):
    user_name = request.form["user_name"]
    phone = request.form["phone"]
    email = request.form.get("email", "")
    province = request.form.get("province", "")
    occupation = request.form.get("occupation", "")
    pet_experience = request.form.get("pet_experience", "")
    housing_type = request.form.get("housing_type", "")
    household_info = request.form.get("household_info", "")
    message = request.form["message"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO Adoption (pet_id, user_name, phone, email, province,
           occupation, pet_experience, housing_type, household_info,
           message, status, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', %s)""",
        (pet_id, user_name, phone, email, province, occupation,
         pet_experience, housing_type, household_info, message, datetime.now()),
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("ส่งคำขอรับเลี้ยงสำเร็จ กรุณารอเจ้าของติดต่อกลับ")
    return redirect(url_for("pet_detail", pet_id=pet_id))


# ---------- เจ้าของดูคำขอ / อนุมัติ / ปฏิเสธ ----------

@app.route("/adoption_requests")
@login_required
def adoption_requests():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT Adoption.*, Pet.name AS pet_name, Pet.pet_id AS pet_id
           FROM Adoption JOIN Pet ON Adoption.pet_id = Pet.pet_id
           WHERE Pet.owner_id = %s
           ORDER BY Adoption.created_at DESC""",
        (session["user_id"],),
    )
    requests_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("adoption_requests.html", requests=requests_list)


@app.route("/request/<int:request_id>/approve")
@login_required
def approve_request(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    # หา request และเช็คว่าสัตว์นี้เป็นของ user ที่ login อยู่จริง
    cursor.execute(
        """SELECT Adoption.*, Pet.owner_id AS owner_id
           FROM Adoption JOIN Pet ON Adoption.pet_id = Pet.pet_id
           WHERE Adoption.request_id = %s""",
        (request_id,),
    )
    req = cursor.fetchone()

    if req and req["owner_id"] == session["user_id"]:
        cursor.execute("UPDATE Adoption SET status='Approved' WHERE request_id=%s", (request_id,))
        cursor.execute("UPDATE Pet SET status='Adopted' WHERE pet_id=%s", (req["pet_id"],))
        conn.commit()
        flash("อนุมัติคำขอสำเร็จ")

    cursor.close()
    conn.close()
    return redirect(url_for("adoption_requests"))


@app.route("/request/<int:request_id>/reject")
@login_required
def reject_request(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT Adoption.*, Pet.owner_id AS owner_id
           FROM Adoption JOIN Pet ON Adoption.pet_id = Pet.pet_id
           WHERE Adoption.request_id = %s""",
        (request_id,),
    )
    req = cursor.fetchone()

    if req and req["owner_id"] == session["user_id"]:
        cursor.execute("UPDATE Adoption SET status='Rejected' WHERE request_id=%s", (request_id,))
        conn.commit()
        flash("ปฏิเสธคำขอสำเร็จ")

    cursor.close()
    conn.close()
    return redirect(url_for("adoption_requests"))


# ---------- เริ่มรันเว็บ ----------

if __name__ == "__main__":
    init_db()
    # รันแบบนี้ใช้สำหรับทดสอบในเครื่องตัวเองเท่านั้น
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
else:
    # เมื่อรันผ่าน gunicorn (production) ให้สร้างตารางฐานข้อมูลตอนโมดูลถูก import ครั้งแรก
    init_db()