-- รันคำสั่งนี้กับฐานข้อมูล MySQL ที่มีอยู่แล้ว (บน Aiven หรือที่ไหนก็ตาม)
-- เพื่อเพิ่มคอลัมน์สำหรับระบบรีเซ็ตรหัสผ่าน โดยไม่ต้องลบข้อมูลผู้ใช้เดิม
--
-- วิธีใช้: เข้า MySQL console ของคุณ (Aiven console / mysql client) แล้วรันคำสั่งนี้
-- ถ้าเป็นฐานข้อมูลที่เพิ่งสร้างใหม่ (ยังไม่เคยรัน init_db()) ไม่ต้องรันไฟล์นี้
-- เพราะ init_db() ในโค้ดใหม่จะสร้างคอลัมน์เหล่านี้ให้ครบอยู่แล้ว

ALTER TABLE User
  ADD COLUMN reset_token VARCHAR(255) AFTER password,
  ADD COLUMN reset_token_expiry DATETIME AFTER reset_token;
