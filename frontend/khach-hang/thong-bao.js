/*
 * Trang Thông báo — thông báo về vé/chuyến của khách (đặt vé thành công, thanh toán, hết hạn giữ chỗ, sắp đến giờ đi, sự cố...).
 * Dữ liệu từ GET /thong-bao/cua-toi (mới nhất trước). Bấm vào thông báo: đánh dấu đã đọc, nếu gắn với 1 vé thì mở chi tiết lượt đặt
 * trong trang Booking (?ma=…). Thông báo mới tới khi đang mở trang (WebSocket, xem khung-trang.js) → tự tải lại danh sách.
 * Dùng esc() và các hàm số chưa đọc từ khung-trang.js.
 */

const noiDung = document.getElementById("tb-noi-dung");
const MUI_GIO = "Asia/Ho_Chi_Minh";
const dinhDang = (iso, tuyChon) => new Intl.DateTimeFormat("vi-VN", { timeZone: MUI_GIO, hour12: false, ...tuyChon }).format(new Date(iso));

let danhSach = [];
let chiChuaDoc = false;

const daDangNhap = () => !!localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang";

// "5 phút trước", "3 giờ trước"; quá 1 ngày thì ghi ngày giờ cụ thể
function thoiGianTuongDoi(iso) {
  const giay = (Date.now() - new Date(iso).getTime()) / 1000;
  if (giay < 60) return "Vừa xong";
  if (giay < 3600) return `${Math.floor(giay / 60)} phút trước`;
  if (giay < 86400) return `${Math.floor(giay / 3600)} giờ trước`;
  return `${dinhDang(iso, { hour: "2-digit", minute: "2-digit" })} · ${dinhDang(iso, { day: "2-digit", month: "2-digit", year: "numeric" })}`;
}

// Loại thông báo (chỉ để chọn biểu tượng/màu) suy ra từ nội dung
function loaiThongBao(noiDungTB) {
  if (/không thành công|hết hạn|không đến|sự cố|bị hủy/i.test(noiDungTB)) return "canh-bao";
  if (/sắp đến giờ/i.test(noiDungTB)) return "gio";
  if (/thành công/i.test(noiDungTB)) return "ok";
  return "tin";
}

const BIEU_TUONG = {
  ok: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  gio: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  "canh-bao": '<path d="M12 4 3 19.5h18Z"/><path d="M12 10v4.5M12 17.2v.1"/>',
  tin: '<path d="M6 17V11a6 6 0 1 1 12 0v6l1.5 2h-15Z"/><path d="M10 21a2 2 0 0 0 4 0"/>',
};

function veYeuCauDangNhap() {
  noiDung.innerHTML = `
    <div class="bk-trong">
      <h2>Đăng nhập để xem thông báo của bạn</h2>
      <a class="tc-btn tc-btn--chinh" href="/khach-hang/dang-nhap.html">Đăng nhập</a>
    </div>`;
}

function veLoi(thongDiep) {
  noiDung.innerHTML = `
    <div class="bk-trong bk-trong--loi">
      <h2>Chưa tải được thông báo</h2>
      <p>${esc(thongDiep)}</p>
      <button type="button" class="tc-btn tc-btn--chinh" id="tb-thu-lai">Thử lại</button>
    </div>`;
  document.getElementById("tb-thu-lai").addEventListener("click", tai);
}

function veMuc(tb) {
  const loai = loaiThongBao(tb.noi_dung);
  return `
    <li>
      <button type="button" class="tb-muc tb-muc--${loai}${tb.da_doc ? "" : " tb-muc--chua-doc"}" data-id="${esc(tb.id)}" data-ma="${esc(tb.ma_dat_cho || "")}">
        <span class="tb-muc__bieu-tuong"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${BIEU_TUONG[loai]}</svg></span>
        <span class="tb-muc__thong-tin">
          <span class="tb-muc__noi-dung">${esc(tb.noi_dung)}</span>
          <time datetime="${esc(tb.ngay_tao)}" title="${esc(dinhDang(tb.ngay_tao, { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric" }))}">${esc(thoiGianTuongDoi(tb.ngay_tao))}</time>
        </span>
        ${tb.da_doc ? "" : '<i class="tb-muc__cham" aria-label="Chưa đọc"></i>'}
      </button>
    </li>`;
}

function veTrang() {
  const soChuaDoc = danhSach.filter((t) => !t.da_doc).length;
  const hienThi = chiChuaDoc ? danhSach.filter((t) => !t.da_doc) : danhSach;
  noiDung.innerHTML = `
    <div class="tb-dau">
      <h1 class="bk-tieu-de">Thông báo</h1>
      <button type="button" class="tb-doc-het" id="tb-doc-het" ${soChuaDoc ? "" : "disabled"}>Đánh dấu tất cả đã đọc</button>
    </div>
    <div class="bk-tab tb-tab" role="tablist">
      <button type="button" role="tab" class="bk-tab__nut${chiChuaDoc ? "" : " is-active"}" aria-selected="${!chiChuaDoc}" data-loc="tat-ca">Tất cả<span>${danhSach.length}</span></button>
      <button type="button" role="tab" class="bk-tab__nut${chiChuaDoc ? " is-active" : ""}" aria-selected="${chiChuaDoc}" data-loc="chua-doc">Chưa đọc<span>${soChuaDoc}</span></button>
    </div>
    ${
      hienThi.length
        ? `<ul class="tb-ds">${hienThi.map(veMuc).join("")}</ul>`
        : `<div class="bk-trong"><h2>${chiChuaDoc ? "Bạn đã đọc hết thông báo" : "Bạn chưa có thông báo nào"}</h2></div>`
    }`;
  noiDung.querySelectorAll("[data-loc]").forEach((b) =>
    b.addEventListener("click", () => {
      chiChuaDoc = b.dataset.loc === "chua-doc";
      veTrang();
    })
  );
  noiDung.querySelectorAll(".tb-muc").forEach((m) => m.addEventListener("click", () => moThongBao(m.dataset.id, m.dataset.ma)));
  document.getElementById("tb-doc-het").addEventListener("click", docTatCa);
}

async function moThongBao(id, maDatCho) {
  const tb = danhSach.find((t) => t.id === id);
  if (tb && !tb.da_doc) {
    try {
      await apiPut(`/thong-bao/${encodeURIComponent(id)}/da-doc`, {});
      tb.da_doc = true;
    } catch {
      /* không đánh dấu được thì vẫn cho đi tiếp */
    }
    if (typeof capNhatSoThongBao === "function") capNhatSoThongBao();
  }
  if (maDatCho) location.href = `/khach-hang/ve-cua-toi.html?ma=${encodeURIComponent(maDatCho)}`;
  else veTrang();
}

async function docTatCa() {
  try {
    await apiPut("/thong-bao/da-doc-tat-ca", {});
    danhSach.forEach((t) => (t.da_doc = true));
  } catch {
    return;
  }
  if (typeof capNhatSoThongBao === "function") capNhatSoThongBao();
  veTrang();
}

async function tai() {
  if (!daDangNhap()) return veYeuCauDangNhap();
  try {
    danhSach = (await apiGet("/thong-bao/cua-toi?limit=100")).items;
  } catch (err) {
    return veLoi(err.message);
  }
  veTrang();
}

// Thông báo mới tới (WebSocket) khi đang mở trang: tải lại danh sách, giữ nguyên bộ lọc đang chọn
document.addEventListener("co-thong-bao-moi", () => {
  if (daDangNhap()) tai();
});

tai();
