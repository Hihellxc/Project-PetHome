# คู่มือผู้พัฒนา PetHome

## 1. ภาพรวมโครงการ

PetHome เป็น Flask application แบบ server-rendered ใช้ MySQL โดยมี entry point ที่ [backend/app.py](./backend/app.py)

```text
backend/app.py             Flask routes, validation, SQL และ integration
frontend/templates/        Jinja2 pages
frontend/static/css/       styles
frontend/static/js/        browser behavior
database/schema.sql        schema หลัก
database/migrations/       migrations สำหรับฐานข้อมูลเดิม
requirements.txt            Python dependencies
Procfile                   Gunicorn command
```

## 2. ข้อกำหนดเครื่องมือ

- Python และ pip
- MySQL 8-compatible
- Git
- (production) บัญชี Cloudinary และ Resend ตามต้องการ

ติดตั้ง dependency:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

ใน repository นี้มีโฟลเดอร์ `env/` อยู่แล้ว แต่ไม่ควร commit secret หรือใช้ environment ที่ไม่ตรงกับเครื่องโดยไม่ตรวจสอบ

## 3. ตั้งค่า environment

สร้าง `.env` ที่ root:

```dotenv
MYSQLHOST=localhost
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=your-password
MYSQLDATABASE=pethome
SECRET_KEY=replace-with-a-long-random-value
```

การแจ้งเตือนอีเมล:

```dotenv
RESEND_API_KEY=your-resend-key
RESEND_FROM_EMAIL=sender@example.com
```

การเก็บรูปบน Cloudinary:

```dotenv
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

อย่าใส่ค่า secret จริงในเอกสาร source control และอย่าแสดง API key ใน log

## 4. ฐานข้อมูลและ migration

สร้าง database แล้วรัน schema:

```sql
CREATE DATABASE pethome CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```powershell
mysql -u root -p pethome < database\schema.sql
```

สำหรับฐานข้อมูลที่มีอยู่แล้ว ให้รัน migration ตามลำดับ:

1. `001_adoption_request_indexes.sql`
2. `002_add_pet_indexes.sql`
3. `003_verification_reports.sql`
4. `004_remove_pet_approval.sql`
5. `005_remove_pet_text_length_limits.sql`

`init_db()` ในแอปสร้างตารางที่ยังไม่มีจาก schema หลัก แต่ migration ของฐานข้อมูลเดิมควรจัดการแยกและตรวจสอบผลก่อน deploy

## 5. รันแอป

โหมดพัฒนา:

```powershell
python -m backend.app
```

เปิด `http://127.0.0.1:5000` และตรวจ health:

```powershell
curl http://127.0.0.1:5000/health
```

production:

```powershell
gunicorn backend.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60
```

## 6. แนวทางการแก้ไขโค้ด

- ใช้ route guard ที่มีอยู่ (`login_required`, `admin_required`) แทนตรวจ session ซ้ำ
- ใช้ parameterized SQL กับ `mysql.connector` เสมอ
- เพิ่ม CSRF token ให้ทุกฟอร์ม `POST`
- ทำ validation ฝั่ง server แม้มี HTML validation
- เมื่อเพิ่มสถานะหรือฟิลด์ ให้ปรับ schema, migration, route, template และเอกสารที่เกี่ยวข้อง
- รักษาการแยกสิทธิ์: เจ้าของเข้าถึงเฉพาะข้อมูลของตนเอง และ admin ใช้ route ที่มี `admin_required`
- ไม่บันทึก password, secret หรือ API key ลง log
- หากเพิ่มอีเมล ให้ตรวจว่าการส่งล้มเหลวไม่ทำให้ transaction หลักเสีย

## 7. จุดเชื่อมต่อภายนอก

### Cloudinary

`upload_image()` ใช้ Cloudinary เมื่อมี environment variables ครบ ถ้าไม่มีหรือ upload ล้มเหลวจะใช้ไฟล์ local ใน `frontend/static/uploads` เป็น fallback การเปลี่ยนพฤติกรรมควรแจ้งผู้ใช้และพิจารณา storage ที่ไม่หายเมื่อ redeploy

### Resend

`send_email()` เรียก Resend ผ่าน HTTPS และ timeout 15 วินาที ฟังก์ชันคืน `False` เมื่อไม่มี key หรือส่งไม่สำเร็จ โดยไม่ทำให้ route คำขอรับเลี้ยงล้มเหลว

## 8. การตรวจสอบก่อน merge/deploy

ตรวจ syntax และ import:

```powershell
python -m compileall backend
```

ตรวจ diff:

```powershell
git diff --check
git status --short
```

ทดสอบด้วยตนเองอย่างน้อย:

1. `/health`
2. สมัครสมาชิกด้วยอีเมลใหม่และอีเมลซ้ำ
3. login/logout และการเข้าหน้าที่ต้อง login
4. เพิ่ม/แก้ไข/ลบประกาศ พร้อมรูปที่ถูกและผิดประเภท
5. filter และ pagination หน้าแรก
6. ส่งคำขอใหม่และส่งซ้ำ
7. อนุมัติ/ปฏิเสธคำขอ และตรวจสถานะสัตว์
8. รายงานและ action ทั้งสามของ admin
9. กรณีไม่มี Resend/Cloudinary configuration

## 9. Deployment

บน Render หรือบริการที่รองรับ Gunicorn:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn backend.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
- ตั้ง environment variables ของ MySQL, `SECRET_KEY`, Resend และ Cloudinary
- ใช้ MySQL ที่เปิด SSL; โค้ดตั้ง encrypted connection แต่ปัจจุบันไม่ verify certificate identity
- รัน migration ก่อนเปิด traffic หากเป็นฐานข้อมูลเดิม
- ตรวจ `/health`, log การเชื่อมต่อ และการเขียนรูปหลัง deploy

## 10. โครงสร้างข้อมูลและข้อควรระวัง

ตารางและ foreign key อยู่ใน [database/schema.sql](./database/schema.sql) โดยมี unique key `(pet_id, applicant_id)` ป้องกันคำขอซ้ำ และ index สำหรับ status/filter สำคัญ

การเปลี่ยน schema ที่ทำให้ข้อมูลเดิมใช้งานไม่ได้ต้องทำเป็น migration ใหม่ ห้ามแก้ schema อย่างเดียวแล้วคาดหวังว่า production จะปรับตามอัตโนมัติ

## 11. เอกสารอ้างอิงใน repository

- [SRS/README](./README.md)
- [คู่มือผู้ใช้](./USER_GUIDE.md)
- [backend/app.py](./backend/app.py)
- [database/schema.sql](./database/schema.sql)
- [frontend/templates](./frontend/templates)
