/*
 * Ô nhập mã xác nhận dạng 6 ô số riêng biệt + đếm ngược gửi lại mã
 * — dùng chung cho dang-ky.html và quen-mat-khau.html (2 trang duy nhất
 * có bước nhập OTP). Đặt ở frontend/khach-hang/ (không phải shared/) vì
 * chỉ 2 trang trong domain này dùng, xem CONTRIBUTING.md mục 6.
 */

function initOtpInput(containerEl) {
  const boxes = Array.from(containerEl.querySelectorAll(".otp-box"));

  function xoaLoi() {
    boxes.forEach((o) => o.classList.remove("is-error"));
  }

  boxes.forEach((box, i) => {
    box.addEventListener("input", () => {
      box.value = box.value.replace(/[^0-9]/g, "").slice(0, 1);
      box.classList.toggle("is-filled", box.value !== "");
      xoaLoi();
      if (box.value && i < boxes.length - 1) boxes[i + 1].focus();
    });

    box.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !box.value && i > 0) {
        boxes[i - 1].focus();
      }
    });

    box.addEventListener("paste", (e) => {
      e.preventDefault();
      const so = (e.clipboardData.getData("text") || "").replace(/[^0-9]/g, "").slice(0, boxes.length);
      so.split("").forEach((ky_tu, idx) => {
        if (boxes[idx]) {
          boxes[idx].value = ky_tu;
          boxes[idx].classList.add("is-filled");
        }
      });
      xoaLoi();
      (boxes[so.length - 1] || boxes[0]).focus();
    });
  });

  return {
    layDayDuMa: () => boxes.map((o) => o.value).join(""),
    baoLoi() {
      boxes.forEach((o) => o.classList.add("is-error"));
      boxes[0].focus();
    },
    reset() {
      boxes.forEach((o) => {
        o.value = "";
        o.classList.remove("is-filled", "is-error");
      });
      boxes[0].focus();
    },
  };
}

function initOtpResendCountdown(linkEl, giay, onClick) {
  const nhanGoc = linkEl.textContent;
  let dem = giay;
  let hen = null;

  function capNhat() {
    if (dem <= 0) {
      linkEl.textContent = nhanGoc;
      linkEl.classList.remove("is-disabled");
      return;
    }
    linkEl.textContent = `Gửi lại mã (${dem}s)`;
    linkEl.classList.add("is-disabled");
    dem -= 1;
    hen = setTimeout(capNhat, 1000);
  }

  linkEl.addEventListener("click", async (e) => {
    e.preventDefault();
    if (linkEl.classList.contains("is-disabled")) return;
    const thanhCong = await onClick();
    if (thanhCong !== false) {
      dem = giay;
      capNhat();
    }
  });

  return {
    batDau() {
      clearTimeout(hen);
      dem = giay;
      capNhat();
    },
  };
}
