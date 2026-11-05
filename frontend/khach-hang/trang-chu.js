/*
 * Trang chủ khách hàng (frontend/index.html) — ô tìm chuyến; bấm "Tìm chuyến" chuyển sang trang kết quả
 * (khach-hang/tim-chuyen.html, xem tim-chuyen.js). Không cần đăng nhập.
 * Cần api-client.js, khung-trang.js, tien-ich-ngay.js, o-tim-kiem.js, dat-ve.js (mở lại lượt đặt từ giỏ hàng) nạp trước.
 */

const TRANG_KET_QUA = "/khach-hang/tim-chuyen.html";
const chipNgay = document.getElementById("tc-chip-ngay");

// Chip chọn nhanh ngày: Hôm nay / Ngày mai / 2 ngày kế tiếp
function veChipNgay() {
  const hom = homNayVN();
  const nhanh = [
    { ngay: hom, nhan: "Hôm nay" },
    { ngay: congNgay(hom, 1), nhan: "Ngày mai" },
    { ngay: congNgay(hom, 2), nhan: nhanNgay(congNgay(hom, 2), true) },
    { ngay: congNgay(hom, 3), nhan: nhanNgay(congNgay(hom, 3), true) },
  ];
  chipNgay.innerHTML = nhanh
    .map((c) => `<button type="button" class="tc-chip${oNgay.value === c.ngay ? " is-active" : ""}" data-ngay="${c.ngay}">${c.nhan}</button>`)
    .join("");
  chipNgay.querySelectorAll("[data-ngay]").forEach((b) =>
    b.addEventListener("click", () => {
      datNgay(b.dataset.ngay);
      if (coDi.lay() && coDen.lay()) xuLyTim();
    })
  );
}
datKhiDoiNgay(veChipNgay);

// Tìm chuyến: sang trang kết quả, đường dẫn mang đủ điểm đi/đến/ngày để chia sẻ và tải lại được
function thucHienTim({ di, den, ngay }) {
  location.href = `${TRANG_KET_QUA}?di=${encodeURIComponent(di.ma)}&den=${encodeURIComponent(den.ma)}&ngay=${ngay}`;
}

async function khoiTao() {
  // Đường dẫn cũ "/?di=…&den=…&ngay=…" (liên kết đã chia sẻ/lưu) → chuyển sang trang kết quả
  const q = new URLSearchParams(location.search);
  if (q.get("di") && q.get("den")) {
    location.replace(TRANG_KET_QUA + location.search);
    return;
  }

  oNgay.min = homNayVN();
  datNgay(homNayVN());

  // Từ giỏ hàng ở trang khác sang: mở thẳng lượt đặt cần hoàn tất (?tiep-tuc=MÃ_ĐẶT_CHỖ)
  const maTiepTuc = q.get("tiep-tuc");
  if (maTiepTuc && DA_DANG_NHAP_KHACH()) {
    history.replaceState(null, "", location.pathname);
    moTiepDatCho(maTiepTuc);
  }
  await taiKhuVuc();
}

khoiTao();
