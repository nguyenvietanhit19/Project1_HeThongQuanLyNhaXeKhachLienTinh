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

function veNav() {
  const navPhai = document.getElementById("tc-nav-phai");
  if (!navPhai) return;
  const hotline = `
    <div class="tc-popup-goc">
      <button type="button" class="tc-nut-nav tc-nut-nav--hotline" id="btn-hotline" aria-haspopup="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/></svg>
        Hotline 24/7
      </button>
      <div class="tc-popup tc-popup--hotline" id="popup-hotline" hidden>
        <a class="tc-popup__so" href="tel:${SO_HOTLINE}">${SO_HOTLINE}</a>
        <span class="tc-popup__mo-ta">Để đặt vé qua điện thoại 24/7</span>
      </div>
    </div>`;

  const dangNhap = localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang";
  if (!dangNhap) {
    navPhai.innerHTML = `${hotline}<a class="tc-nut-nav tc-nut-nav--chinh" href="/khach-hang/dang-nhap.html">Đăng nhập</a>`;
    ganPopup("btn-hotline", "popup-hotline");
    return;
  }

  const ten = (localStorage.getItem("ho_ten") || "bạn").trim().split(/\s+/).slice(-1)[0];
  navPhai.innerHTML = `
    ${hotline}
    <div class="tc-popup-goc">
      <button type="button" class="tc-nut-nav" id="btn-menu-nguoi-dung" aria-haspopup="true">Xin chào, ${esc(ten)}</button>
      <div class="tc-popup tc-popup--menu" id="menu-nguoi-dung" hidden>
        <button type="button" id="btn-ho-so">Tài khoản của tôi</button>
        <button type="button" id="btn-dang-xuat">Đăng xuất</button>
      </div>
    </div>`;
  ganPopup("btn-hotline", "popup-hotline");
  ganPopup("btn-menu-nguoi-dung", "menu-nguoi-dung");
  document.getElementById("btn-ho-so").addEventListener("click", () => {
    dongMoiPopup();
    moHoSo();
  });
  document.getElementById("btn-dang-xuat").addEventListener("click", () => {
    ["token", "vai_tro", "ho_ten"].forEach((k) => localStorage.removeItem(k));
    veNav();
  });
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
