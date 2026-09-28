-- ตรวจสอบและจัดการแถวคำขอซ้ำก่อนรัน migration นี้
-- Migration นี้ใช้กับฐานข้อมูลเดิมที่ยังมีดัชนี idx_pet_applicant
ALTER TABLE adoption_requests
    DROP INDEX idx_pet_applicant,
    ADD UNIQUE KEY uq_pet_applicant (pet_id, applicant_id),
    ADD INDEX idx_adoption_status (pet_id, status);
