"""
PetHome - ระบบรับเลี้ยงสัตว์
Backend: Flask + MySQL
"""

import os
import secrets
import cloudinary
import cloudinary.uploader
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect
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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
)
# ใช้ secret จาก environment; ถ้าไม่มีจะสร้างชั่วคราวสำหรับการรันเครื่อง local
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
csrf = CSRFProtect(app)

# หมายเหตุสำคัญ:
# แพลตฟอร์ม cloud อย่าง Aiven จะสร้างฐานข้อมูล MySQL ให้ แล้วให้ค่าการเชื่อมต่อมา
# เราตั้งให้อ่านค่าจาก environment variable ก่อนเสมอ ถ้าไม่มี (เช่นตอนรันในเครื่องตัวเอง)
# ค่อย fallback ไปใช้ค่าเดิมที่ตั้งไว้สำหรับ localhost
DB_CONFIG = {
    "host": os.environ.get("MYSQLHOST", "localhost"),
    "port": int(os.environ.get("MYSQLPORT", 3306)),
    "user": os.environ.get("MYSQLUSER", "root"),
    "password": os.environ.get("MYSQLPASSWORD", ""),
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

UPLOAD_FOLDER = os.path.join(FRONTEND_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"} #อนุญาตให้อัปโหลดเฉพาะไฟล์รูป

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

THAI_PROVINCES = [
    "กรุงเทพมหานคร", "กระบี่", "กาญจนบุรี", "กาฬสินธุ์", "กำแพงเพชร",
    "ขอนแก่น", "จันทบุรี", "ฉะเชิงเทรา", "ชลบุรี", "ชัยนาท",
    "ชัยภูมิ", "ชุมพร", "เชียงราย", "เชียงใหม่", "ตรัง", "ตราด",
    "ตาก", "นครนายก", "นครปฐม", "นครพนม", "นครราชสีมา",
    "นครศรีธรรมราช", "นครสวรรค์", "นนทบุรี", "นราธิวาส", "น่าน",
    "บึงกาฬ", "บุรีรัมย์", "ปทุมธานี", "ประจวบคีรีขันธ์", "ปราจีนบุรี",
    "ปัตตานี", "พระนครศรีอยุธยา", "พังงา", "พัทลุง", "พิจิตร", "พิษณุโลก",
    "เพชรบุรี", "เพชรบูรณ์", "แพร่", "ภูเก็ต", "มหาสารคาม", "มุกดาหาร",
    "แม่ฮ่องสอน", "ยโสธร", "ยะลา", "ร้อยเอ็ด", "ระนอง", "ระยอง", "ราชบุรี",
    "ลพบุรี", "ลำปาง", "ลำพูน", "เลย", "ศรีสะเกษ", "สกลนคร", "สงขลา",
    "สตูล", "สมุทรปราการ", "สมุทรสงคราม", "สมุทรสาคร", "สระแก้ว", "สระบุรี",
    "สิงห์บุรี", "สุโขทัย", "สุพรรณบุรี", "สุราษฎร์ธานี", "สุรินทร์", "หนองคาย",
    "หนองบัวลำภู", "อยุธยา", "อ่างทอง", "อำนาจเจริญ", "อุดรธานี", "อุตรดิตถ์",
    "อุทัยธานี", "อุบลราชธานี",
]


def get_db():
    """เปิดการเชื่อมต่อ MySQL"""
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """สร้างตารางจาก schema หลัก ถ้ายังไม่มี"""
    conn = get_db()
    cur = conn.cursor()
    with open(os.path.join(PROJECT_ROOT, "database", "schema.sql"), encoding="utf-8") as schema_file:
        statements = [statement.strip() for statement in schema_file.read().split(";") if statement.strip()]
    for statement in statements:
        cur.execute(statement)
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

    debug_cursor.execute("SELECT COUNT(*) FROM pets")
    pet_count = debug_cursor.fetchone()[0]
    print("PET COUNT:", pet_count)
    print("================================")

    debug_cursor.close()

    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT pets.*, pets.id AS pet_id, pets.species AS type,
               ROUND(pets.age_months / 12, 1) AS age,
               COALESCE(pet_images.image_url, '') AS image
        FROM pets
        LEFT JOIN pet_images ON pet_images.pet_id = pets.id AND pet_images.is_primary = 1
        WHERE pets.status = 'available'
    """
    params = []

    if pet_type:
        query += " AND pets.species = %s"
        params.append(pet_type)

    if province:
        query += " AND pets.province LIKE %s"
        params.append(f"%{province}%")

    query += " ORDER BY pets.created_at DESC"

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
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
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
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"ยินดีต้อนรับ {user['name']}")
            return redirect(url_for("home"))
        else:
            flash("อีเมลหรือรหัสผ่านไม่ถูกต้อง")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
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
        gender = {"ผู้": "male", "เมีย": "female"}.get(request.form["gender"], "unknown")
        age = int(request.form["age"]) * 12
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
                    # 1. อัปโหลดไป Cloudinary
                    
                    upload_result = cloudinary.uploader.upload(image_file)
                    image_filename = upload_result["secure_url"]

                except Exception as e:
                    print("================================")
                    print("CLOUDINARY ERROR:", repr(e))
                    print("================================")
                    image_filename = ""
                    flash("อัปโหลดรูปภาพไม่สำเร็จ กรุณาดู Error ใน Terminal/Render Logs")

            else:
                flash("ไฟล์รูปภาพต้องเป็นนามสกุล png, jpg, jpeg หรือ gif เท่านั้น (บันทึกประกาศโดยไม่มีรูป)")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO pets (user_id, name, species, gender, age_months, province,
               description, status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'available', %s)""",
            # หมายเหตุ: ส่ง datetime.now() เป็น object ตรงๆ แทนการแปลงเป็น string ด้วย isoformat()
            # เพราะ isoformat() คั่นวันที่กับเวลาด้วยตัว "T" (เช่น 2026-01-01T12:00:00)
            # ซึ่งคอลัมน์ประเภท DATETIME ของ MySQL ไม่รับรูปแบบนี้โดยตรง ต้องให้ driver แปลงให้เอง
            (session["user_id"], name, pet_type, gender, age, province,
             description, datetime.now()),
        )
        pet_id = cursor.lastrowid
        if image_filename:
            cursor.execute(
                "INSERT INTO pet_images (pet_id, image_url, is_primary) VALUES (%s, %s, 1)",
                (pet_id, image_filename),
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
    cursor.execute(
        """SELECT pets.*, pets.id AS pet_id, pets.species AS type,
                  ROUND(pets.age_months / 12, 1) AS age,
                  COALESCE(pet_images.image_url, '') AS image,
                  pets.user_id AS owner_id
           FROM pets
           LEFT JOIN pet_images ON pet_images.pet_id = pets.id AND pet_images.is_primary = 1
           WHERE pets.id = %s""",
        (pet_id,),
    )
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
        gender = {"ผู้": "male", "เมีย": "female"}.get(request.form["gender"], "unknown")
        age = int(request.form["age"]) * 12
        province = request.form["province"]
        description = request.form["description"]
        status = {"Available": "available", "Adopted": "adopted"}.get(
            request.form["status"], "available"
        )

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
            """UPDATE pets SET name=%s, species=%s, gender=%s, age_months=%s,
               province=%s, description=%s, status=%s WHERE id=%s""",
            (name, pet_type, gender, age, province, description,
             status, pet_id),
        )
        if image_filename and image_filename != pet["image"]:
            cursor.execute("DELETE FROM pet_images WHERE pet_id = %s", (pet_id,))
            cursor.execute(
                "INSERT INTO pet_images (pet_id, image_url, is_primary) VALUES (%s, %s, 1)",
                (pet_id, image_filename),
            )
        conn.commit()
        cursor.close()
        conn.close()

        flash("แก้ไขประกาศสำเร็จ")
        return redirect(url_for("my_pets"))

    cursor.close()
    conn.close()
    return render_template("edit_pet.html", pet=pet, provinces=THAI_PROVINCES)


@app.route("/delete_pet/<int:pet_id>", methods=["POST"])
@login_required
def delete_pet(pet_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, user_id FROM pets WHERE id = %s", (pet_id,))
    pet = cursor.fetchone()

    if pet and pet["user_id"] == session["user_id"]:
        cursor.execute("DELETE FROM adoption_requests WHERE pet_id = %s", (pet_id,))
        cursor.execute("DELETE FROM pets WHERE id = %s", (pet_id,))
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
        """SELECT pets.*, pets.id AS pet_id, pets.species AS type,
              ROUND(pets.age_months / 12, 1) AS age,
              COALESCE(pet_images.image_url, '') AS image
           FROM pets
           LEFT JOIN pet_images ON pet_images.pet_id = pets.id AND pet_images.is_primary = 1
           WHERE pets.user_id = %s ORDER BY pets.created_at DESC""",
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
         """SELECT pets.*, pets.id AS pet_id, pets.species AS type,
                ROUND(pets.age_months / 12, 1) AS age,
                COALESCE(pet_images.image_url, '') AS image,
                users.name AS owner_name, users.email AS owner_email
            FROM pets
            JOIN users ON pets.user_id = users.id
            LEFT JOIN pet_images ON pet_images.pet_id = pets.id AND pet_images.is_primary = 1
            WHERE pets.id = %s""",
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
    applicant_email = email or f"guest-{secrets.token_hex(8)}@pethome.local"
    cursor.execute("SELECT id FROM users WHERE email = %s", (applicant_email,))
    applicant = cursor.fetchone()
    if applicant:
        applicant_id = applicant[0]
        cursor.execute(
            "UPDATE users SET name = %s, phone_number = %s WHERE id = %s",
            (user_name, phone, applicant_id),
        )
    else:
        cursor.execute(
            """INSERT INTO users (name, email, password_hash, phone_number)
               VALUES (%s, %s, %s, %s)""",
            (user_name, applicant_email, generate_password_hash(secrets.token_urlsafe(24)), phone),
        )
        applicant_id = cursor.lastrowid

    experience_note = " | ".join(
        value for value in (
            f"อาชีพ: {occupation}" if occupation else "",
            f"ประสบการณ์: {pet_experience}" if pet_experience else "",
            f"สมาชิกในบ้าน: {household_info}" if household_info else "",
            f"จังหวัด: {province}" if province else "",
        ) if value
    )
    contact_channel = " | ".join(value for value in (phone, email) if value)
    cursor.execute(
        """INSERT INTO adoption_requests
           (pet_id, applicant_id, housing_type, housing_permission,
            experience_note, contact_channel, message, status)
           VALUES (%s, %s, %s, 1, %s, %s, %s, 'pending')""",
        (pet_id, applicant_id, housing_type or "ไม่ระบุ", experience_note,
         contact_channel, message),
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
         """SELECT adoption_requests.*, adoption_requests.id AS request_id,
                users.name AS user_name, users.phone_number AS phone,
                users.email AS email, pets.name AS pet_name,
                pets.id AS pet_id, pets.status AS pet_status
            FROM adoption_requests
            JOIN pets ON adoption_requests.pet_id = pets.id
            JOIN users ON adoption_requests.applicant_id = users.id
            WHERE pets.user_id = %s
            ORDER BY adoption_requests.created_at DESC""",
        (session["user_id"],),
    )
    requests_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("adoption_requests.html", requests=requests_list)


@app.route("/request/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_request(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """SELECT adoption_requests.*, adoption_requests.id AS request_id,
                pets.user_id AS owner_id, pets.status AS pet_status,
                pets.id AS pet_id
           FROM adoption_requests JOIN pets ON adoption_requests.pet_id = pets.id
           WHERE adoption_requests.id = %s""",
        (request_id,),
    )
    req = cursor.fetchone()

    if req and req["owner_id"] == session["user_id"]:
        if req["pet_status"] == "adopted":
            flash("สัตว์ตัวนี้มีผู้ได้รับอนุมัติไปแล้ว ไม่สามารถอนุมัติคำขออื่นซ้ำได้")
        else:
            cursor.execute("UPDATE adoption_requests SET status='approved' WHERE id=%s", (request_id,))
            cursor.execute("UPDATE pets SET status='adopted' WHERE id=%s", (req["pet_id"],))
            cursor.execute(
                """UPDATE adoption_requests SET status='rejected'
                   WHERE pet_id=%s AND status='pending' AND id != %s""",
                (req["pet_id"], request_id),
            )
            conn.commit()
            flash("อนุมัติคำขอสำเร็จ และปฏิเสธคำขออื่นที่ค้างอยู่ให้อัตโนมัติแล้ว")
    else:
        flash("ไม่พบคำขอ หรือคุณไม่มีสิทธิ์ดำเนินการ")

    cursor.close()
    conn.close()
    return redirect(url_for("adoption_requests"))


@app.route("/request/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_request(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
          """SELECT adoption_requests.*, pets.user_id AS owner_id
              FROM adoption_requests JOIN pets ON adoption_requests.pet_id = pets.id
              WHERE adoption_requests.id = %s""",
        (request_id,),
    )
    req = cursor.fetchone()

    if req and req["owner_id"] == session["user_id"]:
        cursor.execute("UPDATE adoption_requests SET status='rejected' WHERE id=%s", (request_id,))
        conn.commit()
        flash("ปฏิเสธคำขอสำเร็จ")
    else:
        flash("ไม่พบคำขอ หรือคุณไม่มีสิทธิ์ดำเนินการ")

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