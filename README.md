# 🐾 PetHome – ระบบรับเลี้ยงสัตว์

เว็บไซต์ลงประกาศสัตว์ที่ต้องการหาบ้านใหม่ ดูรายละเอียดสัตว์ (สุนัข, แมว) ค้นหาตามประเภท/จังหวัด
และส่งคำขอรับเลี้ยงได้ พร้อมระบบแจ้งเตือนอีเมลอัตโนมัติทั้งเจ้าของและผู้ขอรับเลี้ยง

## เทคโนโลยีที่ใช้
- **Frontend:** HTML, CSS (ธีมฟ้า-ขาวน่ารัก ฟอนต์ Mali + Sarabun), Bootstrap 5, JavaScript พื้นฐาน
- **Backend:** Flask (Python)
- **Database:** MySQL (ใช้ผ่าน `mysql.connector`) — ใช้ตาราง `users`, `pets`, `pet_images`, `adoption_requests` และ `admin_audit_logs` จาก `database/schema.sql`
- **อีเมล:** ส่งผ่าน Resend Email API ด้วย HTTPS

## โครงสร้างไฟล์
```
backend/
├── app.py                      # Flask backend
└── __init__.py                 # Python package
frontend/
├── templates/                  # Jinja2 templates
└── static/                     # CSS, JavaScript และ uploads
database/
├── schema.sql                  # โครงสร้างฐานข้อมูลหลัก
└── migrations/                 # SQL สำหรับปรับฐานข้อมูลเดิม
backend/requirements.txt        # Python libraries
Procfile                        # คำสั่ง deploy ด้วย Gunicorn
README.md
```

## วิธีติดตั้งและรันในเครื่องตัวเอง

### 1. เตรียมฐานข้อมูล MySQL
ต้องมี MySQL server อยู่แล้ว (ในเครื่องตัวเอง หรือใช้บริการ MySQL บนคลาวด์อย่าง Aiven)
สร้างฐานข้อมูลและตารางด้วย:
```bash
mysql -u root -p < database/schema.sql
```
หรือปล่อยให้ `backend/app.py` โหลด schema และสร้างตารางให้อัตโนมัติตอนรันครั้งแรกก็ได้ (ฟังก์ชัน `init_db()`)

### 2. ตั้งค่าการเชื่อมต่อฐานข้อมูล
เปิด `backend/app.py` แก้ค่า `DB_CONFIG` หรือตั้งเป็น environment variable ก็ได้ (แนะนำ):

**Windows PowerShell:**
```powershell
$env:MYSQLHOST="localhost"
$env:MYSQLPORT="3306"
$env:MYSQLUSER="root"
$env:MYSQLPASSWORD="รหัสผ่าน MySQL ของคุณ"
$env:MYSQLDATABASE="pethome"
```

### 3. (ทางเลือก) ตั้งค่าให้ส่งอีเมลแจ้งเตือนได้
ตั้งค่า `RESEND_API_KEY` และ `RESEND_FROM_EMAIL` — ถ้าไม่ตั้งค่า เว็บยังทำงานได้ปกติทุกอย่าง แค่ข้ามการส่งอีเมล

### 4. ติดตั้ง Python library ที่จำเป็น
```bash
pip install -r requirements.txt
```

### 5. รันเว็บไซต์
```bash
python -m backend.app
```
เปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:5000`

ตรวจสอบสถานะเซิร์ฟเวอร์ได้ที่ `http://127.0.0.1:5000/health`

## Deploy ขึ้นคลาวด์
ใช้ **Render** เป็น hosting เว็บ และ **Aiven** เป็น MySQL ได้ โดยตั้งค่าตามคำสั่งด้านล่าง

สำหรับ Render ให้ตั้งค่า:

- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** `gunicorn backend.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
- **Environment Variables:** `SECRET_KEY`, `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL` และค่า Cloudinary ทั้งสามตัว

ถ้าเป็นฐานข้อมูลเดิม ให้รัน migration ใน `database/migrations/001_adoption_request_indexes.sql` และ `database/migrations/002_add_pet_indexes.sql` ตามลำดับก่อนเปิดใช้งานจริง

## ฟีเจอร์หลัก
1. **สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ** — เข้ารหัสรหัสผ่านด้วย `werkzeug.security`
2. **ลงประกาศสัตว์ (CRUD)** — เพิ่ม / แก้ไข / ลบ / ดูประกาศของตัวเอง พร้อมอัปโหลดรูป
3. **หน้าหลัก** — แสดงรายการสัตว์ทั้งหมดที่ยังหาบ้านอยู่ (สถานะ Available)
4. **ค้นหา** — ค้นหาตามประเภทสัตว์และจังหวัด (ช่องจังหวัดพิมพ์ค้นหาได้ เลือกจาก 77 จังหวัดทั้งหมด)
5. **หน้ารายละเอียดสัตว์** — รูปใหญ่ ข้อมูลครบ พร้อมฟอร์มส่งคำขอรับเลี้ยง
6. **ส่งคำขอรับเลี้ยง** (ไม่ต้อง login) — ระบบสร้างผู้สมัคร Guest ใน `users` ให้อัตโนมัติ และเก็บข้อมูลผู้ขอละเอียดขึ้น: ชื่อ, เบอร์, อีเมล, จังหวัดที่พัก,
   อาชีพ, ประสบการณ์เลี้ยงสัตว์, ลักษณะที่พัก, สมาชิกในบ้าน, ข้อความ — ช่วยให้เจ้าของตัดสินใจได้ง่ายขึ้น
   ส่งสำเร็จจะมี popup แจ้งเตือนกลางหน้าจอ
7. **เจ้าของดูคำขอ** (การ์ดแยกต่อคำขอ) และกดอนุมัติ/ปฏิเสธ — ถ้าอนุมัติ สถานะสัตว์เปลี่ยนเป็น Adopted อัตโนมัติ
8. **แจ้งเตือนอีเมลอัตโนมัติ**
   - เจ้าของได้อีเมลทันทีที่มีคนส่งคำขอรับเลี้ยงเข้ามาใหม่
   - ผู้ขอได้อีเมลยืนยันว่าส่งคำขอสำเร็จ (ถ้ากรอกอีเมลไว้)
   - ผู้ขอได้อีเมลแจ้งผลทันทีที่เจ้าของกดอนุมัติ/ปฏิเสธ

## Database Schema
ฐานข้อมูลหลักอยู่ใน `database/schema.sql` ประกอบด้วยตาราง `users`, `pets`, `pet_images`,
`adoption_requests` และ `admin_audit_logs` โดยคำขอรับเลี้ยงหนึ่งคนต่อสัตว์หนึ่งตัวจะส่งซ้ำไม่ได้
ถ้ามีฐานข้อมูลเดิม ให้รัน migration ใน `database/migrations/001_adoption_request_indexes.sql` หลังตรวจสอบคำขอซ้ำ

## หมายเหตุเกี่ยวกับโค้ด
- โค้ดฝั่ง Backend (`app.py`) เขียนแบบฟังก์ชันตรงไปตรงมา ไม่ใช้ ORM ที่ซับซ้อน ใช้ `mysql.connector`
  เขียน SQL ตรงๆ เพื่อให้อ่านและเข้าใจง่าย
- โค้ดฝั่ง Frontend (`static/js/main.js`) ใช้คำสั่ง JavaScript พื้นฐาน เช่น `addEventListener`,
  `querySelector`, `confirm()`, `FileReader` พร้อมคอมเมนต์อธิบายทุกฟังก์ชัน
- รหัสผ่านผู้ใช้ถูกเข้ารหัสด้วย `werkzeug.security` ก่อนบันทึกลงฐานข้อมูล (ไม่เก็บเป็นข้อความธรรมดา)
- ระบบล็อกอินใช้ Flask `session` แบบพื้นฐาน ยังไม่ได้ใช้ library เสริมอย่าง Flask-Login
  เพื่อให้เข้าใจการทำงานได้ง่าย
- การเชื่อมต่อ MySQL เปิด SSL (`ssl_disabled=False`) แต่ไม่บังคับตรวจสอบใบรับรอง
  (`ssl_verify_cert=False`) เพื่อรองรับผู้ให้บริการ MySQL บนคลาวด์อย่าง Aiven โดยไม่ต้องพึ่งไฟล์ CA
- การส่งอีเมลถูกออกแบบให้ **ไม่ทำให้เว็บ error** แม้ตั้งค่า SMTP ผิดหรือไม่ได้ตั้งค่าไว้เลย
  (ข้ามการส่งไปเงียบๆ แค่ print log แจ้งไว้)

## แนวทางต่อยอด (ถ้าต้องการพัฒนาเพิ่ม)
- หน้า Home มี pagination และคงค่าตัวกรองประเภท/จังหวัดระหว่างเปลี่ยนหน้า
- เพิ่มระบบ Admin กลางสำหรับจัดการทั้งระบบ
- ย้ายรูปที่อัปโหลดไปเก็บบน cloud storage (เช่น Cloudinary) เพื่อไม่ให้หายตอน redeploy
- เพิ่มการอัปโหลดรูปได้หลายรูปต่อประกาศ