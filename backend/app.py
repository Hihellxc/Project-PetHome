"""
PetHome - ระบบรับเลี้ยงสัตว์
Backend: Flask + MySQL
"""

from dotenv import load_dotenv
load_dotenv()
import os
import json
from functools import wraps
from html import escape
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import secrets
import mysql.connector
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash #แอดมินไม่เห็นรหัสของผู้ใช้
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader #เพื่ออัปโหลดรูปไปเก็บบน Cloudinary แทนเก็บไว้ในเครื่องตัวเอง

# ---------- ตั้งค่าเบื้องต้น ----------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
)
# อ่าน secret key จาก environment variable ก่อน ถ้าไม่มีค่อยใช้ค่า default (สำหรับรันในเครื่องตัวเอง)
app.secret_key = os.environ.get("SECRET_KEY", "pethome-secret-key")


def login_required(view_func):
    """บังคับให้ผู้ใช้เข้าสู่ระบบก่อนเข้าหน้านี้"""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("กรุณาเข้าสู่ระบบก่อน")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view

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

UPLOAD_FOLDER = os.path.join(FRONTEND_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"} #อนุญาตให้อัปโหลดเฉพาะไฟล์รูป

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# รายชื่อ 77 จังหวัดของไทย ใช้แสดงเป็นตัวเลือกในช่องกรอกจังหวัด (พิมพ์ค้นหาได้ผ่าน <datalist>)
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

# สร้างโฟลเดอร์เก็บรูปภาพไว้ล่วงหน้าเสมอ (เผื่อโฟลเดอร์ถูกลบ หรือรันครั้งแรกในเครื่องใหม่)
# ถ้าไม่มีบรรทัดนี้ และโฟลเดอร์นี้ไม่มีอยู่จริง การอัปโหลดรูปจะทำให้ทั้งคำขอ error
# และส่งผลให้ข้อมูลสัตว์เลี้ยงไม่ถูกบันทึกลงฐานข้อมูลเลย (แม้กรอกข้อมูลถูกต้องก็ตาม)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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


# ---------- ตั้งค่าสำหรับส่งอีเมลผ่าน Resend ----------
# Render ไม่สามารถใช้ Gmail SMTP แบบเดิมได้ จึงเรียก Resend ผ่าน HTTPS API
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.environ.get(
    "RESEND_FROM_EMAIL",
    "onboarding@resend.dev"
).strip()
RESEND_API_URL = "https://api.resend.com/emails"

# ---- DEBUG: แสดงเฉพาะสถานะว่า key มีหรือไม่มี ห้ามพิมพ์ค่า key จริง ----
print(
    f"[Resend] API key configured: {'YES' if RESEND_API_KEY else 'NO'} | "
    f"From: {RESEND_FROM_EMAIL}",
    flush=True
)

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

def send_email(to_address, subject, body):
    """
    ส่งอีเมลผ่าน Resend Email API ผ่าน HTTPS
    - แสดง log ทุกขั้นตอนเพื่อ debug บน Render
    - ไม่พิมพ์ API Key ออกมา
    - ถ้าส่งไม่สำเร็จ จะคืน False แทนการทำให้ route หลักล้ม
    """
    print(
        f"[Resend] send_email() called | to={to_address!r} | subject={subject!r}",
        flush=True
    )

    if not to_address:
        print("[Resend] STOP: ไม่มีอีเมลผู้รับ", flush=True)
        return False

    if not RESEND_API_KEY:
        print("[Resend] STOP: ไม่พบ RESEND_API_KEY ใน Environment Variables", flush=True)
        return False

    try:
        # Resend รับ HTML จึงแปลง newline ให้แสดงเป็นบรรทัดใหม่ และ escape HTML
        html_body = escape(str(body)).replace("\n", "<br>")

        payload = {
            "from": RESEND_FROM_EMAIL,
            "to": [to_address],
            "subject": subject,
            "html": html_body,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        print(
            f"[Resend] POST {RESEND_API_URL} | from={RESEND_FROM_EMAIL!r}",
            flush=True
        )

        req = Request(
            RESEND_API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "PetHome/1.0",
            },
            method="POST",
        )

        with urlopen(req, timeout=15) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            print(
                f"[Resend] SUCCESS | HTTP {response.status} | response={response_body}",
                flush=True
            )
            return True

    except HTTPError as e:
        try:
            error_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = "<อ่าน response ไม่ได้>"
        print(
            f"[Resend] HTTP ERROR | status={e.code} | body={error_body}",
            flush=True
        )
        return False

    except URLError as e:
        print(
            f"[Resend] URL ERROR | reason={e.reason}",
            flush=True
        )
        return False

    except Exception as e:
        print(
            f"[Resend] UNEXPECTED ERROR | type={type(e).__name__} | error={e}",
            flush=True
        )
        return False


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

    return render_template("home.html", pets=pets, pet_type=pet_type, province=province, provinces=THAI_PROVINCES)


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


@app.route("/logout")
def logout():
    session.clear()
    flash("ออกจากระบบแล้ว")
    return redirect(url_for("home"))


# ---------- ขอรีเซ็ตรหัสผ่าน / ตั้งรหัสผ่านใหม่ ----------

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        print(f"[Forgot Password] request received | email={email!r}", flush=True)

        cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()

        print(
            f"[Forgot Password] user found: {'YES' if user else 'NO'}",
            flush=True
        )

        if user:
            # สร้าง token แบบสุ่มที่คาดเดาไม่ได้ และตั้งอายุ 1 ชั่วโมง
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            cursor.execute(
                "UPDATE User SET reset_token=%s, reset_token_expiry=%s WHERE user_id=%s",
                (token, expiry, user["user_id"]),
            )
            conn.commit()

            reset_link = url_for("reset_password", token=token, _external=True)
            body = (
                f"สวัสดีคุณ {user['name']},\n\n"
                f"มีการขอรีเซ็ตรหัสผ่านสำหรับบัญชี PetHome ของคุณ\n"
                f"กดลิงก์นี้เพื่อตั้งรหัสผ่านใหม่ (ลิงก์จะหมดอายุใน 1 ชั่วโมง):\n\n"
                f"{reset_link}\n\n"
                f"ถ้าคุณไม่ได้ขอรีเซ็ตรหัสผ่าน สามารถละเลยอีเมลนี้ได้เลยค่ะ\n\n"
                f"— PetHome"
            )
            print(
                f"[Forgot Password] calling send_email() for {user['email']!r}",
                flush=True
            )
            send_result = send_email(
                user["email"],
                "ขอรีเซ็ตรหัสผ่าน PetHome",
                body
            )
            print(
                f"[Forgot Password] send_email result: {send_result}",
                flush=True
            )

        cursor.close()
        conn.close()

        # แสดงข้อความเดียวกันไม่ว่าจะเจออีเมลนี้ในระบบหรือไม่ ป้องกันการเดาว่าอีเมลไหนมีอยู่ในระบบบ้าง
        flash("ถ้าอีเมลนี้มีอยู่ในระบบ เราได้ส่งลิงก์รีเซ็ตรหัสผ่านไปให้แล้ว กรุณาเช็คอีเมลของคุณ")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM User WHERE reset_token = %s", (token,))
    user = cursor.fetchone()

    # เช็คว่า token มีอยู่จริง และยังไม่หมดอายุ
    # (กันไว้เผื่อ driver บางกรณีคืนค่าคอลัมน์ DATETIME มาเป็น string แทน datetime object)
    expiry = user["reset_token_expiry"] if user else None
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry)

    if not user or expiry is None or datetime.now() > expiry:
        cursor.close()
        conn.close()
        flash("ลิงก์รีเซ็ตรหัสผ่านไม่ถูกต้องหรือหมดอายุแล้ว กรุณาขอลิงก์ใหม่")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            cursor.close()
            conn.close()
            flash("รหัสผ่านทั้งสองช่องไม่ตรงกัน กรุณากรอกใหม่")
            return redirect(url_for("reset_password", token=token))

        hashed_password = generate_password_hash(new_password)
        # ตั้งรหัสผ่านใหม่ และล้าง token ทันที เพื่อไม่ให้ลิงก์เดิมใช้ซ้ำได้อีก
        cursor.execute(
            "UPDATE User SET password=%s, reset_token=NULL, reset_token_expiry=NULL WHERE user_id=%s",
            (hashed_password, user["user_id"]),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("ตั้งรหัสผ่านใหม่สำเร็จแล้ว กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่")
        return redirect(url_for("login"))

    cursor.close()
    conn.close()
    return render_template("reset_password.html", token=token)


# ---------- ทดสอบ Resend ----------
# ใช้ชั่วคราวสำหรับตรวจสอบว่า Render -> Resend -> อีเมล ทำงานหรือไม่
# ต้อง login ก่อน และระบบจะส่งไปยังอีเมลของบัญชีที่ login อยู่เท่านั้น
@app.route("/test_email")
@login_required
def test_email():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT email, name FROM User WHERE user_id = %s",
        (session["user_id"],)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not user.get("email"):
        print("[Resend Test] ไม่พบอีเมลของผู้ใช้ที่ login", flush=True)
        flash("ไม่พบอีเมลของบัญชีนี้")
        return redirect(url_for("home"))

    print(
        f"[Resend Test] Starting test email to {user['email']!r}",
        flush=True
    )

    result = send_email(
        user["email"],
        "PetHome - ทดสอบระบบส่งอีเมล",
        f"สวัสดีคุณ {user['name']}\n\n"
        "นี่คืออีเมลทดสอบจาก PetHome ผ่าน Resend API\n"
        "ถ้าได้รับอีเมลนี้ แสดงว่าระบบส่งอีเมลทำงานแล้ว\n\n"
        "— PetHome"
    )

    print(f"[Resend Test] Result: {result}", flush=True)

    if result:
        flash("ส่งอีเมลทดสอบแล้ว กรุณาเช็ค Inbox / Spam")
    else:
        flash("ส่งอีเมลทดสอบไม่สำเร็จ ให้ดู Render Logs")

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
                    result = cloudinary.uploader.upload(
                    image_file,
                    folder="pethome"
                    )

                    image_filename = result["secure_url"]
                except Exception as e:
                    print(f"อัปโหลดรูปไป Cloudinary ไม่สำเร็จ: {e}")
                    image_filename = ""
                    flash("อัปโหลดรูปภาพไม่สำเร็จ แต่ข้อมูลอื่นถูกบันทึกแล้ว")
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
                    result = cloudinary.uploader.upload(
                    image_file,
                    folder="pethome"
                    )
                    image_filename = result["secure_url"]
                except Exception as e:
                    print(f"อัปโหลดรูปไป Cloudinary ไม่สำเร็จ: {e}")
                    flash("บันทึกรูปภาพใหม่ไม่สำเร็จ ระบบใช้รูปเดิมไว้ก่อน")
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


@app.route("/delete_pet/<int:pet_id>")
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

    # ดึงชื่อสัตว์ + ชื่อและอีเมลของเจ้าไว้ก่อน จะได้เอาไปใช้ส่งอีเมลแจ้งเตือน
    info_cursor = conn.cursor(dictionary=True)
    info_cursor.execute(
        """SELECT Pet.name AS pet_name, User.name AS owner_name, User.email AS owner_email
           FROM Pet JOIN User ON Pet.owner_id = User.user_id
           WHERE Pet.pet_id = %s""",
        (pet_id,),
    )
    pet_owner = info_cursor.fetchone()
    info_cursor.close()

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

    # ---------- ส่งอีเมลแจ้งเจ้าของว่ามีคนสนใจรับเลี้ยง ----------
    if pet_owner:
        owner_body = (
            f"สวัสดีคุณ {pet_owner['owner_name']},\n\n"
            f"มีคนส่งคำขอรับเลี้ยง \"{pet_owner['pet_name']}\" เข้ามาใหม่ครับ\n\n"
            f"ชื่อผู้ขอ: {user_name}\n"
            f"เบอร์โทร: {phone}\n"
            f"อีเมล: {email or '-'}\n"
            f"จังหวัดที่พัก: {province or '-'}\n"
            f"ข้อความ: {message or '-'}\n\n"
            f"เข้าไปดูรายละเอียดและตอบรับ/ปฏิเสธได้ที่:\n"
            f"{url_for('adoption_requests', _external=True)}\n\n"
            f"— PetHome"
        )
        send_email(
            pet_owner["owner_email"],
            f"มีคนสนใจรับเลี้ยง {pet_owner['pet_name']} 🐾",
            owner_body,
        )

    # ---------- ส่งอีเมลยืนยันให้ผู้ขอรับเลี้ยง (ถ้าเขากรอกอีเมลไว้) ----------
    if email:
        pet_name_text = pet_owner["pet_name"] if pet_owner else "สัตว์เลี้ยงตัวนี้"
        requester_body = (
            f"สวัสดีคุณ {user_name},\n\n"
            f"เราได้รับคำขอรับเลี้ยง \"{pet_name_text}\" ของคุณแล้วครับ\n"
            f"ตอนนี้เจ้าของกำลังตรวจสอบข้อมูล เมื่อมีผลจะส่งอีเมลแจ้งให้ทราบอีกครั้ง\n"
            f"ไม่ต้องเข้าเว็บมาเช็กเองก็ได้ครับ\n\n"
            f"— PetHome"
        )
        send_email(email, f"ได้รับคำขอรับเลี้ยง {pet_name_text} แล้ว", requester_body)

    # ใช้ category "adopt_success" แยกจาก flash message ทั่วไป (ที่ใช้ category default คือ "message")
    # เพื่อให้หน้า pet_detail.html นำไปแสดงเป็น popup แจ้งเตือนแบบเด่นชัด แทนแถบข้อความธรรมดา
    flash("ส่งคำขอรับเลี้ยงสำเร็จ! รอเจ้าของตรวจสอบและติดต่อกลับหาคุณนะครับ", "adopt_success")
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


@app.route("/request/<int:request_id>/approve")
@login_required
def approve_request(request_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    # หา request และเช็คว่าสัตว์นี้เป็นของ user ที่ login อยู่จริง
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

    cursor.close()
    conn.close()
    return redirect(url_for("adoption_requests"))


@app.route("/request/<int:request_id>/reject")
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

        # ส่งอีเมลแจ้งผู้ขอรับเลี้ยงว่าคำขอไม่ได้รับการคัดเลือก (ถ้าเขากรอกอีเมลไว้)
        if req.get("email"):
            body = (
                f"สวัสดีคุณ {req['user_name']},\n\n"
                f"ขอบคุณที่สนใจรับเลี้ยง \"{req['pet_name']}\" นะครับ\n"
                f"แต่ครั้งนี้เจ้าของเลือกผู้รับเลี้ยงรายอื่นแล้ว ขอให้เจอน้องที่ใช่ในเร็วๆ นี้ครับ 🐾\n\n"
                f"— PetHome"
            )
            send_email(req["email"], f"ผลการขอรับเลี้ยง {req['pet_name']}", body)

    cursor.close()
    conn.close()
    return redirect(url_for("adoption_requests"))


# ---------- เริ่มรันเว็บ ----------

if __name__ == "__main__":
    init_db()
    # รันแบบนี้ใช้สำหรับทดสอบในเครื่องตัวเองเท่านั้น
    # ตอน deploy จริงบน Railway จะไม่ใช้บรรทัดนี้ แต่ใช้ gunicorn แทน (ดูไฟล์ Procfile)
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
else:
    # เมื่อรันผ่าน gunicorn (production) ให้สร้างตารางฐานข้อมูลตอนโมดูลถูก import ครั้งแรก
    init_db()