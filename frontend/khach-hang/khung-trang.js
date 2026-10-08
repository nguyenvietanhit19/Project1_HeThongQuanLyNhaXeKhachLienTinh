/*
 * Khung dùng chung cho các trang khách hàng công khai (trang chủ, tài khoản): thanh trên cùng
 * (logo, Hotline 24/7, đăng nhập / tên khách) và footer. Trang chỉ cần có
 *   <header class="tc-nav" id="tc-nav-goc"></header> và <footer class="tc-chan" id="tc-chan-goc"></footer>
 * rồi nạp file này — CSS nằm ở trang-chu.css (.tc-nav*, .tc-popup*, .tc-chan*).
 */

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const boDau = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
const pad2 = (n) => String(n).padStart(2, "0");

// ---------- Thanh điều hướng: hotline + đăng nhập / tên khách ----------
const SO_HOTLINE = "0123459999";

const dongMoiPopup = () => document.querySelectorAll(".tc-popup").forEach((p) => (p.hidden = true));

// Gắn nút bấm mở/đóng 1 popup nhỏ (đóng khi bấm ra ngoài hoặc mở popup khác)
function ganPopup(nutId, popupId) {
  const popup = document.getElementById(popupId);
  document.getElementById(nutId).addEventListener("click", (e) => {
    e.stopPropagation();
    const dangMo = !popup.hidden;
    dongMoiPopup();
    popup.hidden = dangMo;
  });
}

// ---------- Giỏ hàng: các lượt đặt vé còn đang giữ ghế (chưa chọn cách thanh toán, hoặc chờ trả VNPay) ----------
// Mỗi lượt có đồng hồ đếm ngược hạn giữ ghế; khách bấm "Tiếp tục" để quay lại hoàn tất, "Xóa" để nhả ghế.
let ghDanhSach = [];
let ghDongHo = null;
const ghTien = (so) => `${Number(so).toLocaleString("vi-VN")}đ`;
const ghGioVN = (iso) => new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(iso));
const ghNgayVN = (iso) => new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit" }).format(new Date(iso));
const ghDangNhapKhach = () => !!localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang";
const ghHanCua = (d) => (d.trang_thai === "cho_thanh_toan" ? d.han_thanh_toan : d.han_giu_cho_den);

async function capNhatGioHang() {
  if (!ghDangNhapKhach() || !document.getElementById("btn-gio-hang")) return;
  try {
    ghDanhSach = await apiGet("/ve/gio-hang");
  } catch {
    ghDanhSach = [];
  }
  ghVeHuyHieu();
  ghVeDanhSach();
}

function ghVeHuyHieu() {
  const so = document.getElementById("gh-so");
  if (!so) return;
  so.textContent = ghDanhSach.length;
  so.hidden = ghDanhSach.length === 0;
}

function ghVeDanhSach() {
  const hop = document.getElementById("popup-gio-hang");
  if (!hop) return;
  if (!ghDanhSach.length) {
    hop.innerHTML = '<div class="tc-gh-trong">Giỏ hàng trống</div>';
    return;
  }
  hop.innerHTML = `<div class="tc-gh-tieu-de">Giỏ hàng</div>` + ghDanhSach
    .map(
      (d) => `
    <div class="tc-gh-muc" data-ma="${esc(d.ma_dat_cho)}">
      <div class="tc-gh-muc__tren">
        <b>${esc(d.chuyen.ten_diem_don)} → ${esc(d.chuyen.ten_diem_tra)}</b>
        <span class="tc-gh-chip ${d.trang_thai === "cho_thanh_toan" ? "tc-gh-chip--cho" : ""}">${d.trang_thai === "cho_thanh_toan" ? "Chờ thanh toán VNPay" : "Chưa thanh toán"}</span>
      </div>
      <div class="tc-gh-muc__phu">${ghNgayVN(d.chuyen.gio_don_du_kien)} · ${ghGioVN(d.chuyen.gio_don_du_kien)} · Ghế ${d.ve.filter((v) => v.trang_thai === "giu_cho").map((v) => esc(v.so_ghe)).join(", ")} · <b>${ghTien(d.tong_tien)}</b></div>
      <div class="tc-gh-muc__duoi">
        <span>Còn <b data-gh-han="${esc(ghHanCua(d))}">--:--</b></span>
        <span class="tc-gh-muc__nut">
          <button type="button" class="tc-gh-nut" data-gh-xoa="${esc(d.ma_dat_cho)}">Xóa</button>
          <button type="button" class="tc-gh-nut tc-gh-nut--chinh" data-gh-tiep="${esc(d.ma_dat_cho)}">Tiếp tục</button>
        </span>
      </div>
    </div>`
    )
    .join("");
  ghChayDongHo();
}

// Đếm ngược từng lượt; hết hạn thì tải lại giỏ (server đã nhả ghế)
function ghChayDongHo() {
  const tick = () => {
    let hetHan = false;
    document.querySelectorAll("[data-gh-han]").forEach((el) => {
      const con = Math.max(0, Math.floor((new Date(el.dataset.ghHan) - Date.now()) / 1000));
      el.textContent = `${pad2(Math.floor(con / 60))}:${pad2(con % 60)}`;
      if (con === 0) hetHan = true;
    });
    if (hetHan) {
      clearInterval(ghDongHo);
      capNhatGioHang();
    }
  };
  clearInterval(ghDongHo);
  tick();
  ghDongHo = setInterval(tick, 1000);
}

function ghGanSuKien() {
  const hop = document.getElementById("popup-gio-hang");
  hop.addEventListener("click", async (e) => {
    e.stopPropagation(); // bấm trong giỏ hàng không đóng giỏ
    const tiep = e.target.closest("[data-gh-tiep]");
    const xoa = e.target.closest("[data-gh-xoa]");
    if (tiep) {
      dongMoiPopup();
      const ma = tiep.dataset.ghTiep;
      if (typeof moTiepDatCho === "function") moTiepDatCho(ma);
      else location.href = `/?tiep-tuc=${encodeURIComponent(ma)}`;
    } else if (xoa) {
      xoa.disabled = true;
      try {
        await apiPost(`/ve/dat-cho/${encodeURIComponent(xoa.dataset.ghXoa)}/huy`, {});
      } catch {
        /* đã hết hạn/đã nhả thì thôi */
      }
      capNhatGioHang();
    }
  });
  document.getElementById("btn-gio-hang").addEventListener("click", () => capNhatGioHang());
}

// ---------- Thông báo: số chưa đọc + nhận thông báo mới theo thời gian thực (WebSocket /ws) ----------
let tbSoChuaDoc = 0;
let tbWs = null;
let tbTimerNoiLai = null;

function veHuyHieuThongBao() {
  document.querySelectorAll("[data-tb-so]").forEach((el) => {
    el.textContent = tbSoChuaDoc > 99 ? "99+" : tbSoChuaDoc;
    el.hidden = tbSoChuaDoc === 0;
  });
}

async function capNhatSoThongBao() {
  if (!ghDangNhapKhach()) {
    tbSoChuaDoc = 0;
    return veHuyHieuThongBao();
  }
  try {
    tbSoChuaDoc = (await apiGet("/thong-bao/cua-toi?limit=1")).so_chua_doc;
  } catch {
    /* giữ số cũ */
  }
  veHuyHieuThongBao();
}

// Có thông báo mới: tăng huy hiệu ngay; trang nào quan tâm (Thông báo, Booking, giỏ hàng) nghe sự kiện "co-thong-bao-moi"
function noiThongBaoRealtime() {
  if (tbWs || !ghDangNhapKhach()) return;
  clearTimeout(tbTimerNoiLai);
  let ws;
  try {
    ws = new WebSocket(`${API_BASE_URL.replace(/^http/, "ws")}/ws?token=${encodeURIComponent(localStorage.getItem("token"))}`);
  } catch {
    return;
  }
  tbWs = ws;
  ws.onmessage = (e) => {
    tbSoChuaDoc += 1;
    veHuyHieuThongBao();
    capNhatGioHang();
    let chiTiet = {};
    try {
      chiTiet = JSON.parse(e.data);
    } catch {
      /* nội dung không phải JSON thì bỏ qua */
    }
    document.dispatchEvent(new CustomEvent("co-thong-bao-moi", { detail: chiTiet }));
  };
  ws.onclose = (e) => {
    tbWs = null;
    // 1008: token sai/hết hạn — không nối lại; còn lại (mất mạng, server khởi động lại) thì thử lại sau 5 giây
    if (e.code !== 1008 && ghDangNhapKhach()) tbTimerNoiLai = setTimeout(noiThongBaoRealtime, 5000);
  };
}

function ngatThongBaoRealtime() {
  clearTimeout(tbTimerNoiLai);
  const ws = tbWs;
  tbWs = null;
  tbSoChuaDoc = 0;
  if (ws) ws.close(1000);
}

function veNav() {
  const navPhai = document.getElementById("tc-nav-phai");
  if (!navPhai) return;
  const hotline = `
    <div class="tc-popup-goc">
      <button type="button" class="tc-nut-nav tc-nut-nav--hotline" id="btn-hotline" aria-haspopup="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/></svg>
        <span class="tc-nut-nav__chu">Hotline 24/7</span>
      </button>
      <div class="tc-popup tc-popup--hotline" id="popup-hotline" hidden>
        <a class="tc-popup__so" href="tel:${SO_HOTLINE}">${SO_HOTLINE}</a>
        <span class="tc-popup__mo-ta">Để đặt vé qua điện thoại 24/7</span>
      </div>
    </div>`;

  // Các mục chính trên màn hình lớn (điện thoại dùng thanh dưới thay thế, CSS ẩn nhóm này ở ≤700px)
  const duongHienTai = location.pathname.replace(/index\.html$/, "");
  const lienKet = (href, nhan) => `<a class="tc-lk${duongHienTai === href ? " is-active" : ""}" href="${href}"${duongHienTai === href ? ' aria-current="page"' : ""}>${nhan}</a>`;
  const cacMuc = `<div class="tc-nav__lien-ket">${lienKet("/", "Trang chủ")}${lienKet("/khach-hang/ve-cua-toi.html", "Booking")}${lienKet("/khach-hang/thong-bao.html", 'Thông báo<span class="tc-so" data-tb-so hidden>0</span>')}</div>`;

  const dangNhap = localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang";
  if (!dangNhap) {
    navPhai.innerHTML = `${cacMuc}${hotline}<a class="tc-nut-nav tc-nut-nav--chinh tc-nav__nguoi-dung" href="/khach-hang/dang-nhap.html">Đăng nhập</a>`;
    ganPopup("btn-hotline", "popup-hotline");
    veDayNav();
    return;
  }

  const ten = (localStorage.getItem("ho_ten") || "bạn").trim().split(/\s+/).slice(-1)[0];
  navPhai.innerHTML = `
    ${cacMuc}
    ${hotline}
    <div class="tc-popup-goc">
      <button type="button" class="tc-nut-nav tc-nut-nav--gio" id="btn-gio-hang" aria-haspopup="true" aria-label="Giỏ hàng">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 4h2l2.4 11h10.2L20 8H6.2"/><circle cx="9" cy="19" r="1.4"/><circle cx="17" cy="19" r="1.4"/></svg>
        <span class="tc-nut-nav__chu">Giỏ hàng</span>
        <span class="tc-gh-so" id="gh-so" hidden>0</span>
      </button>
      <div class="tc-popup tc-popup--gio" id="popup-gio-hang" hidden></div>
    </div>
    <div class="tc-popup-goc tc-nav__nguoi-dung">
      <button type="button" class="tc-nut-nav" id="btn-menu-nguoi-dung" aria-haspopup="true">Xin chào, ${esc(ten)}</button>
      <div class="tc-popup tc-popup--menu" id="menu-nguoi-dung" hidden>
        <button type="button" id="btn-ho-so">Tài khoản của tôi</button>
        <button type="button" id="btn-dang-xuat">Đăng xuất</button>
      </div>
    </div>`;
  ganPopup("btn-hotline", "popup-hotline");
  ganPopup("btn-menu-nguoi-dung", "menu-nguoi-dung");
  ganPopup("btn-gio-hang", "popup-gio-hang");
  ghGanSuKien();
  capNhatGioHang();
  document.getElementById("btn-ho-so").addEventListener("click", () => {
    dongMoiPopup();
    moHoSo();
  });
  document.getElementById("btn-dang-xuat").addEventListener("click", dangXuat);
  veDayNav();
}

function dangXuat() {
  ["token", "vai_tro", "ho_ten"].forEach((k) => localStorage.removeItem(k));
  ngatThongBaoRealtime();
  clearInterval(ghDongHo);
  ghDanhSach = [];
  veNav();
}

// ---------- Thanh điều hướng dưới (chỉ hiện trên điện thoại, CSS .tc-day-nav ở trang-chu.css) ----------
const BIEU_TUONG_DAY_NAV = {
  trangChu: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v10h13V10"/><path d="M10 20v-5.5h4V20"/>',
  booking: '<path d="M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2.2a2 2 0 0 0 0 3.6V16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2.2a2 2 0 0 0 0-3.6Z"/><path d="M14 6v12" stroke-dasharray="2 2.5"/>',
  thongBao: '<path d="M6 17V11a6 6 0 1 1 12 0v6l1.5 2h-15Z"/><path d="M10 21a2 2 0 0 0 4 0"/>',
  taiKhoan: '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5c.8-3.6 3.7-5.5 7.5-5.5s6.7 1.9 7.5 5.5"/>',
};
const bieuTuongDayNav = (ten) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${BIEU_TUONG_DAY_NAV[ten]}</svg>`;

function veDayNav() {
  let nav = document.getElementById("tc-day-nav");
  if (!nav) {
    nav = document.createElement("nav");
    nav.id = "tc-day-nav";
    nav.className = "tc-day-nav";
    nav.setAttribute("aria-label", "Điều hướng chính");
    document.body.appendChild(nav);
    document.body.classList.add("co-day-nav");
  }
  const duong = location.pathname.replace(/index\.html$/, "");
  const muc = (href, ten, nhan, bieuTuong) =>
    `<a class="tc-day-nav__muc${duong === href ? " is-active" : ""}" href="${href}"${duong === href ? ' aria-current="page"' : ""}>${bieuTuongDayNav(bieuTuong)}<span>${nhan}</span></a>`;
  const dangNhap = localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang";
  const taiKhoan = dangNhap
    ? `<div class="tc-popup-goc">
         <button type="button" class="tc-day-nav__muc" id="btn-day-nav-tai-khoan" aria-haspopup="true">${bieuTuongDayNav("taiKhoan")}<span>Tài khoản</span></button>
         <div class="tc-popup tc-popup--menu" id="menu-day-nav" hidden>
           <button type="button" id="btn-ho-so-day-nav">Tài khoản của tôi</button>
           <button type="button" id="btn-dang-xuat-day-nav">Đăng xuất</button>
         </div>
       </div>`
    : `<a class="tc-day-nav__muc" href="/khach-hang/dang-nhap.html">${bieuTuongDayNav("taiKhoan")}<span>Tài khoản</span></a>`;
  nav.innerHTML =
    muc("/", "Trang chủ", "Trang chủ", "trangChu") +
    muc("/khach-hang/ve-cua-toi.html", "Booking", "Booking", "booking") +
    muc("/khach-hang/thong-bao.html", "Thông báo", 'Thông báo<span class="tc-so" data-tb-so hidden>0</span>', "thongBao") +
    taiKhoan;
  if (dangNhap) {
    ganPopup("btn-day-nav-tai-khoan", "menu-day-nav");
    document.getElementById("btn-ho-so-day-nav").addEventListener("click", () => {
      dongMoiPopup();
      if (typeof moHoSo === "function") moHoSo();
    });
    document.getElementById("btn-dang-xuat-day-nav").addEventListener("click", dangXuat);
  }
  veHuyHieuThongBao();
  if (dangNhap) {
    capNhatSoThongBao();
    noiThongBaoRealtime();
  }
}
document.addEventListener("click", dongMoiPopup);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") dongMoiPopup();
});


const HTML_LOGO = `
  <a class="tc-nav__logo" href="/" aria-label="GoBus — trang chủ">
    <img src="/shared/assets/logo-mark.png" alt="" />
    <span>GoBus</span>
  </a>
  <nav class="tc-nav__phai" id="tc-nav-phai"></nav>`;

const HTML_CHAN = `
  <div class="tc-chan__khung">
    <div class="tc-chan__cot tc-chan__cot--thuong-hieu">
      <a class="tc-chan__logo" href="/">
        <img src="/shared/assets/logo-mark.png" alt="" />
        <span>GoBus</span>
      </a>
      <p>Kết nối mọi hành trình. Xe khách liên tỉnh, giá vé minh bạch, giờ chạy rõ ràng.</p>
    </div>

    <div class="tc-chan__cot">
      <h3>Khách hàng</h3>
      <ul>
        <li><a href="/">Tìm chuyến xe</a></li>
        <li><a href="/khach-hang/dang-nhap.html">Đăng nhập</a></li>
        <li><a href="/khach-hang/dang-ky.html">Đăng ký tài khoản</a></li>
        <li><a href="/khach-hang/dang-nhap.html" id="lien-ket-ho-so">Tài khoản của tôi</a></li>
      </ul>
    </div>

    <div class="tc-chan__cot">
      <h3>Dịch vụ</h3>
      <ul>
        <li><span>Đặt vé online</span></li>
        <li><span>Mua vé tại văn phòng</span></li>
        <li><span>Gửi hàng liên tỉnh</span></li>
      </ul>
    </div>

    <div class="tc-chan__cot">
      <h3>Nhà xe</h3>
      <ul>
        <li><a href="/nhan-vien/dang-nhap.html">Dành cho nhân viên</a></li>
        <li><a href="/nhan-vien/quen-mat-khau.html">Quên mật khẩu nhân viên</a></li>
      </ul>
    </div>
  </div>

  <div class="tc-chan__duoi">
    <span>© GoBus. Mọi quyền được bảo lưu.</span>
  </div>`;

function dungKhung() {
  const nav = document.getElementById("tc-nav-goc");
  if (nav) nav.innerHTML = HTML_LOGO;
  const chan = document.getElementById("tc-chan-goc");
  if (chan) {
    chan.innerHTML = HTML_CHAN;
    // Đã đăng nhập thì mở modal tài khoản ngay tại trang; chưa đăng nhập thì giữ liên kết sang trang đăng nhập
    chan.querySelector("#lien-ket-ho-so").addEventListener("click", (e) => {
      if (localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang" && typeof moHoSo === "function") {
        e.preventDefault();
        moHoSo();
      }
    });
  }
  veNav();
}
dungKhung();
