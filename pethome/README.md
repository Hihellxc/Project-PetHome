# 🐾 PetHome – ระบบรับเลี้ยงสัตว์

เว็บไซต์ลงประกาศสัตว์ที่ต้องการหาบ้านใหม่ ค้นหาสัตว์ ดูรายละเอียด และส่งคำขอรับเลี้ยงได้

## เทคโนโลยีที่ใช้
- **Frontend:** HTML, CSS, Bootstrap 5, JavaScript (พื้นฐาน)
- **Backend:** Flask (Python)
- **Database:** SQLite (โครงสร้างตารางเหมือน MySQL — มีไฟล์ `database_mysql_schema.sql` แนบไว้ให้ ถ้าต้องการย้ายไปใช้ MySQL จริง)

## โครงสร้างไฟล์
```
pethome/
├── app.py                     # Flask backend (routes ทั้งหมด)
├── requirements.txt           # รายชื่อ library ที่ต้องติดตั้ง
├── database_mysql_schema.sql  # โครงสร้างตาราง (ฉบับ MySQL)
├── pethome.db                 # ฐานข้อมูล SQLite (ถูกสร้างอัตโนมัติตอนรันครั้งแรก)
├── templates/                 # ไฟล์ HTML (Jinja2 templates)
│   ├── base.html
│   ├── home.html
│   ├── login.html
│   ├── register.html
│   ├── add_pet.html
│   ├── edit_pet.html
│   ├── my_pets.html
│   ├── pet_detail.html
│   └── adoption_requests.html
└── static/
    ├── css/style.css
    ├── js/main.js
    └── uploads/               # เก็บรูปสัตว์ที่อัปโหลด
```

## วิธีติดตั้งและรัน

### 1. ติดตั้ง Python library ที่จำเป็น
```bash
pip install -r requirements.txt
```

### 2. รันเว็บไซต์
```bash
python app.py
```

### 3. เปิดเบราว์เซอร์
```
http://127.0.0.1:5000
```

ฐานข้อมูล `pethome.db` จะถูกสร้างขึ้นอัตโนมัติในครั้งแรกที่รัน (มี 3 ตาราง: User, Pet, Adoption)

## ฟีเจอร์หลัก (ตาม MVP)
1. สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ
2. ลงประกาศสัตว์ (เพิ่ม / แก้ไข / ลบ / ดูประกาศของตัวเอง)
3. หน้าหลักแสดงรายการสัตว์ทั้งหมด
4. ค้นหาสัตว์ตามประเภทและจังหวัด
5. หน้ารายละเอียดสัตว์
6. ส่งคำขอรับเลี้ยง (ไม่ต้อง login ก็ส่งได้)
7. เจ้าของดูคำขอ และกดอนุมัติ/ปฏิเสธ (ถ้าอนุมัติ สถานะสัตว์จะเปลี่ยนเป็น Adopted อัตโนมัติ)

## หมายเหตุเกี่ยวกับโค้ด
- โค้ดฝั่ง Backend (`app.py`) เขียนแบบฟังก์ชันตรงไปตรงมา ไม่ใช้ ORM ที่ซับซ้อน ใช้ `sqlite3` เขียน SQL ตรงๆ เพื่อให้อ่านและเข้าใจง่าย
- โค้ดฝั่ง Frontend (`static/js/main.js`) ใช้คำสั่ง JavaScript พื้นฐาน เช่น `addEventListener`, `querySelector`, `confirm()`, `FileReader` พร้อมคอมเมนต์อธิบายทุกฟังก์ชัน
- รหัสผ่านผู้ใช้ถูกเข้ารหัสด้วย `werkzeug.security` ก่อนบันทึกลงฐานข้อมูล (ไม่เก็บเป็นข้อความธรรมดา)
- ระบบล็อกอินใช้ Flask `session` แบบพื้นฐาน ยังไม่ได้ใช้ library เสริมอย่าง Flask-Login เพื่อให้เข้าใจการทำงานได้ง่าย

## แนวทางต่อยอด (ถ้าต้องการพัฒนาเพิ่ม)
- เปลี่ยนจาก SQLite เป็น MySQL จริง (ใช้ `database_mysql_schema.sql` ที่แนบไว้)
- เพิ่มการแบ่งหน้า (pagination) ในหน้า Home
- เพิ่มระบบแจ้งเตือนทางอีเมลเมื่อมีคำขอรับเลี้ยงใหม่
- เพิ่มการอัปโหลดรูปได้หลายรูปต่อประกาศ
