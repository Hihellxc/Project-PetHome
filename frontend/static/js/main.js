/* =========================================================
   PetHome - main.js
   ไฟล์นี้รวมคำสั่ง JavaScript พื้นฐานที่ใช้ในเว็บไซต์
   เขียนแบบง่าย ไม่ซับซ้อน เหมาะสำหรับผู้เริ่มต้นศึกษา
   ========================================================= */


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

function setupSelfiePreview() {
    const selfieInput = document.getElementById("selfieInput");
    const previewImg = document.getElementById("selfiePreview");
    if (!selfieInput || !previewImg) {
        return;
    }

    selfieInput.addEventListener("change", function () {
        const file = selfieInput.files[0];
        if (!file) {
            previewImg.classList.add("d-none");
            return;
        }
        previewImg.src = URL.createObjectURL(file);
        previewImg.classList.remove("d-none");
    });
}


/* ---------------------------------------------------------
   3) ตรวจสอบฟอร์มเบื้องต้นก่อนส่ง (Form Validation)
   เช่น เช็คว่ากรอกอายุเป็นตัวเลขที่มากกว่าหรือเท่ากับ 0
--------------------------------------------------------- */
function setupPetFormValidation() {
    const ageYearsInput = document.querySelector('input[name="age_years"]');
    const ageMonthsInput = document.querySelector('input[name="age_months"]');
    if (!ageYearsInput || !ageMonthsInput) {
        return;
    }

    const form = ageYearsInput.closest("form");
    form.addEventListener("submit", function (event) {
        const ageYears = Number(ageYearsInput.value);
        const ageMonths = Number(ageMonthsInput.value);

        if (!Number.isInteger(ageYears) || ageYears < 0 || ageYears > 30 ||
            !Number.isInteger(ageMonths) || ageMonths < 0 || ageMonths > 11) {
            event.preventDefault(); // หยุดการส่งฟอร์ม
            alert("กรุณากรอกอายุให้ถูกต้อง (ปี 0-30 และเดือน 0-11)");
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


/* ป้องกันการกดส่งฟอร์มซ้ำระหว่างรอ server ตอบกลับ */
function preventDuplicateSubmit() {
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            if (form.dataset.submitting === "true") {
                return;
            }

            form.dataset.submitting = "true";
            form.querySelectorAll('button[type="submit"]').forEach(function (button) {
                button.disabled = true;
                button.classList.add("is-submitting");
            });
        });
    });
}

function setupActionConfirmations() {
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
}


/* ---------------------------------------------------------
   เมื่อโหลดหน้าเว็บเสร็จ ให้เรียกใช้ฟังก์ชันทั้งหมดข้างบน
--------------------------------------------------------- */

/* ปิดคำแนะนำก่อนเลื่อนไปยังรายการ เพื่อไม่ให้การคืนโฟกัสดึงหน้ากลับด้านบน */
function setupAdoptionGuide() {
    const modal = document.getElementById("howToAdoptModal");
    const browseButton = document.querySelector("[data-adoption-browse]");
    const target = document.getElementById("browsePets");
    if (!modal || !browseButton || !target) {
        return;
    }
    browseButton.addEventListener("click", function () {
        modal.addEventListener("hidden.bs.modal", function () {
            target.focus({ preventScroll: true });
            target.scrollIntoView({
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
                block: "start"
            });
        }, { once: true });
    });
}

document.addEventListener("DOMContentLoaded", function () {
    setupAdoptionGuide();
    setupImagePreview();
    setupSelfiePreview();
    setupPetFormValidation();
    autoHideAlerts();
    preventDuplicateSubmit();
    setupActionConfirmations();
});
