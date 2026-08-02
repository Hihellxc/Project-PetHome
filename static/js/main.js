

/* ---------------------------------------------------------
   1) ยืนยันก่อนลบประกาศ
   ใช้กับปุ่ม "ลบ" ในหน้า my_pets.html
   ถ้าไม่กด "ตกลง" จะไม่ลบ (return false)
--------------------------------------------------------- */
function confirmDelete() {
    return confirm("คุณแน่ใจหรือไม่ว่าต้องการลบประกาศนี้?");
}


/* ---------------------------------------------------------
   2) แสดงตัวอย่างรูปภาพก่อนอัปโหลด (Image Preview)
   ใช้ในหน้า add_pet.html / edit_pet.html
   เมื่อผู้ใช้เลือกไฟล์รูป จะแสดงตัวอย่างให้ดูทันที
--------------------------------------------------------- */
function setupImagePreview() {
    // หา input type="file" ในหน้านี้
    const imageInput = document.querySelector('input[name="image"]');
    if (!imageInput) {
        return; // ถ้าหน้านี้ไม่มี input รูป ก็ไม่ต้องทำอะไรต่อ
    }

    imageInput.addEventListener("change", function (event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        // สร้าง element รูปภาพสำหรับ preview (ถ้ายังไม่มีให้สร้างใหม่)
        let previewImg = document.getElementById("imagePreview");
        if (!previewImg) {
            previewImg = document.createElement("img");
            previewImg.id = "imagePreview";
            previewImg.className = "mt-2 pet-image-small";
            imageInput.parentElement.appendChild(previewImg);
        }

        // อ่านไฟล์แล้วนำมาแสดงผล
        const reader = new FileReader();
        reader.onload = function (e) {
            previewImg.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}


/* ---------------------------------------------------------
   3) ตรวจสอบฟอร์มเบื้องต้นก่อนส่ง (Form Validation)
   เช่น เช็คว่ากรอกอายุเป็นตัวเลขที่มากกว่าหรือเท่ากับ 0
--------------------------------------------------------- */
function setupPetFormValidation() {
    const ageInput = document.querySelector('input[name="age"]');
    if (!ageInput) {
        return;
    }

    const form = ageInput.closest("form");
    form.addEventListener("submit", function (event) {
        const ageValue = Number(ageInput.value);

        if (ageValue < 0) {
            event.preventDefault(); // หยุดการส่งฟอร์ม
            alert("กรุณากรอกอายุที่ถูกต้อง (ต้องไม่ติดลบ)");
        }
    });
}


/* ---------------------------------------------------------
   4) ปิด Alert แจ้งเตือนอัตโนมัติหลังจาก 3 วินาที
--------------------------------------------------------- */
function autoHideAlerts() {
    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(function (alertBox) {
        setTimeout(function () {
            alertBox.style.display = "none";
        }, 3000); // 3000 มิลลิวินาที = 3 วินาที
    });
}


/* ---------------------------------------------------------
   เมื่อโหลดหน้าเว็บเสร็จ ให้เรียกใช้ฟังก์ชันทั้งหมดข้างบน
--------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {
    setupImagePreview();
    setupPetFormValidation();
    autoHideAlerts();
});
