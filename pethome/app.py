"""
PetHome - ระบบรับเลี้ยงสัตว์
Backend: Flask + SQLite
"""

import os
import mysql.connector
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash #แอดมินไม่เห็นรหัสของผู้ใช้
from werkzeug.utils import secure_filename

# ---------- ตั้งค่าเบื้องต้น ----------
app = Flask(__name__)
app.secret_key = "pethome-secret-key"  # ใช้สำหรับ session 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "pethome"
}

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"} #อนุญาตให้อัปโหลดเฉพาะไฟล์รูป

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS User (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # ตาราง Pet
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Pet (
            pet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            gender TEXT NOT NULL,
            age INTEGER NOT NULL,
            province TEXT NOT NULL,
            description TEXT,
            image TEXT,
            status TEXT DEFAULT 'Available',
            created_at TEXT,
            FOREIGN KEY (owner_id) REFERENCES User(user_id)
        )
    """)

    # ตาราง Adoption
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Adoption (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            FOREIGN KEY (pet_id) REFERENCES Pet(pet_id)
        )
    """)

    conn.commit()
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
    query = "SELECT * FROM Pet WHERE status = 'Available'"
    params = []

    if pet_type:
        query += " AND type = %s"
        params.append(pet_type)

    if province:
        query += " AND province LIKE %s"
        params.append(f"%{province}%")

    query += " ORDER BY created_at DESC"
    pets = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("home.html", pets=pets, pet_type=pet_type, province=province)


# ---------- สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO User (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password),
            )
            conn.commit()
            conn.close()
            flash("สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
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
        user = conn.execute("SELECT * FROM User WHERE email = %s", (email,)).fetchone()
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
                    image_filename = secure_filename(
                        f"{datetime.now().timestamp()}_{image_file.filename}"
                    )
                    image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
                except OSError:
                    image_filename = ""
                    flash("บันทึกรูปภาพไม่สำเร็จ แต่ข้อมูลอื่นถูกบันทึกแล้ว กรุณาแก้ไขประกาศเพื่อเพิ่มรูปใหม่")
            else:
                flash("ไฟล์รูปภาพต้องเป็นนามสกุล png, jpg, jpeg หรือ gif เท่านั้น (บันทึกประกาศโดยไม่มีรูป)")

        conn = get_db()
        conn.execute(
            """INSERT INTO Pet (owner_id, name, type, gender, age, province,
               description, image, status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Available', %s)""",
            (session["user_id"], name, pet_type, gender, age, province,
             description, image_filename, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        flash("เพิ่มประกาศสำเร็จ")
        return redirect(url_for("my_pets"))

    return render_template("add_pet.html")


@app.route("/edit_pet/<int:pet_id>", methods=["GET", "POST"])
@login_required
def edit_pet(pet_id):
    conn = get_db()
    pet = conn.execute("SELECT * FROM Pet WHERE pet_id = %s", (pet_id,)).fetchone()

    # เช็คว่าเป็นเจ้าของประกาศจริงหรือไม่
    if pet is None or pet["owner_id"] != session["user_id"]:
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
                    new_filename = secure_filename(
                        f"{datetime.now().timestamp()}_{image_file.filename}"
                    )
                    image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], new_filename))
                    image_filename = new_filename  # เปลี่ยนเป็นรูปใหม่เมื่อบันทึกสำเร็จเท่านั้น
                except OSError:
                    flash("บันทึกรูปภาพใหม่ไม่สำเร็จ ระบบใช้รูปเดิมไว้ก่อน")
            else:
                flash("ไฟล์รูปภาพต้องเป็นนามสกุล png, jpg, jpeg หรือ gif เท่านั้น (ใช้รูปเดิมไว้ก่อน)")

        conn.execute(
            """UPDATE Pet SET name=%s, type=%s, gender=%s, age=%s, province=%s,
               description=%s, image=%s, status=%s WHERE pet_id=%s""",
            (name, pet_type, gender, age, province, description,
             image_filename, status, pet_id),
        )
        conn.commit()
        conn.close()

        flash("แก้ไขประกาศสำเร็จ")
        return redirect(url_for("my_pets"))

    conn.close()
    return render_template("edit_pet.html", pet=pet)


@app.route("/delete_pet/<int:pet_id>")
@login_required
def delete_pet(pet_id):
    conn = get_db()
    pet = conn.execute("SELECT * FROM Pet WHERE pet_id = %s", (pet_id,)).fetchone()

    if pet and pet["owner_id"] == session["user_id"]:
        conn.execute("DELETE FROM Pet WHERE pet_id = %s", (pet_id,))
        conn.execute("DELETE FROM Adoption WHERE pet_id = %s", (pet_id,))
        conn.commit()
        flash("ลบประกาศสำเร็จ")
    else:
        flash("คุณไม่มีสิทธิ์ลบประกาศนี้")

    conn.close()
    return redirect(url_for("my_pets"))


@app.route("/my_pets")
@login_required
def my_pets():
    conn = get_db()
    pets = conn.execute(
        "SELECT * FROM Pet WHERE owner_id = %s ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("my_pets.html", pets=pets)


# ---------- หน้ารายละเอียดสัตว์ ----------

@app.route("/pet/<int:pet_id>")
def pet_detail(pet_id):
    conn = get_db()
    pet = conn.execute(
        """SELECT Pet.*, User.name AS owner_name, User.email AS owner_email
           FROM Pet JOIN User ON Pet.owner_id = User.user_id
           WHERE Pet.pet_id = %s""",
        (pet_id,),
    ).fetchone()
    conn.close()

    if pet is None:
        flash("ไม่พบประกาศนี้")
        return redirect(url_for("home"))

    return render_template("pet_detail.html", pet=pet)


# ---------- ส่งคำขอรับเลี้ยง ----------

@app.route("/pet/<int:pet_id>/adopt", methods=["POST"])
def send_adoption_request(pet_id):
    user_name = request.form["user_name"]
    phone = request.form["phone"]
    message = request.form["message"]

    conn = get_db()
    conn.execute(
        """INSERT INTO Adoption (pet_id, user_name, phone, message, status, created_at)
           VALUES (%s, %s, %s, %s, 'Pending', %s)""",
        (pet_id, user_name, phone, message, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    flash("ส่งคำขอรับเลี้ยงสำเร็จ กรุณารอเจ้าของติดต่อกลับ")
    return redirect(url_for("pet_detail", pet_id=pet_id))


# ---------- เจ้าของดูคำขอ / อนุมัติ / ปฏิเสธ ----------

@app.route("/adoption_requests")
@login_required
def adoption_requests():
    conn = get_db()
    requests_list = conn.execute(
        """SELECT Adoption.*, Pet.name AS pet_name, Pet.pet_id AS pet_id
           FROM Adoption JOIN Pet ON Adoption.pet_id = Pet.pet_id
           WHERE Pet.owner_id = %s
           ORDER BY Adoption.created_at DESC""",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("adoption_requests.html", requests=requests_list)


@app.route("/request/<int:request_id>/approve")
@login_required
def approve_request(request_id):
    conn = get_db()
    # หา request และเช็คว่าสัตว์นี้เป็นของ user ที่ login อยู่จริง
    req = conn.execute(
        """SELECT Adoption.*, Pet.owner_id AS owner_id
           FROM Adoption JOIN Pet ON Adoption.pet_id = Pet.pet_id
           WHERE Adoption.request_id = %s""",
        (request_id,),
    ).fetchone()

    if req and req["owner_id"] == session["user_id"]:
        conn.execute("UPDATE Adoption SET status='Approved' WHERE request_id=%s", (request_id,))
        conn.execute("UPDATE Pet SET status='Adopted' WHERE pet_id=%s", (req["pet_id"],))
        conn.commit()
        flash("อนุมัติคำขอสำเร็จ")

    conn.close()
    return redirect(url_for("adoption_requests"))


@app.route("/request/<int:request_id>/reject")
@login_required
def reject_request(request_id):
    conn = get_db()
    req = conn.execute(
        """SELECT Adoption.*, Pet.owner_id AS owner_id
           FROM Adoption JOIN Pet ON Adoption.pet_id = Pet.pet_id
           WHERE Adoption.request_id = %s""",
        (request_id,),
    ).fetchone()

    if req and req["owner_id"] == session["user_id"]:
        conn.execute("UPDATE Adoption SET status='Rejected' WHERE request_id=%s", (request_id,))
        conn.commit()
        flash("ปฏิเสธคำขอสำเร็จ")

    conn.close()
    return redirect(url_for("adoption_requests"))


# ---------- เริ่มรันเว็บ ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
