/*
 * Menu chung của phụ xe: nút ☰ ở góc phải thanh trên → mở menu gom TẤT CẢ điều hướng
 * (Chuyến của tôi, Thao tác / Tổng quan chuyến đang xem, Thống kê & chuyến đã chạy) cùng
 * "Hồ sơ" / "Đăng xuất" — thay cho các liên kết rải rác từng trang. "Hồ sơ" mở hộp thoại xem họ tên, SĐT, email, vai trò, ngày tham gia
 * và cho sửa họ tên + SĐT (NGHIEP_VU.md UC-53 — API GET/PUT /auth/toi dùng chung mọi vai trò;
 * email và vai trò không sửa được). Cần nạp SAU /shared/api-client.js và ../shared/auth-check.js.
 * CSS: các lớp .tk-* và .modal-* trong phu-xe.css.
 */
(function () {
  const VAI_TRO = { phu_xe: "Phụ xe" };

  function esc(giaTri) {
    return String(giaTri ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function chuDau(ten) {
    return ((ten || "").trim().split(/\s+/).slice(-1)[0] || "?").charAt(0).toUpperCase();
  }

  function dinhDangNgay(iso) {
    return iso ? window.phuXe.ngay(iso) : "";
  }

  // ---------- Điều hướng: các mục chung + các mục theo chuyến đang xem (có ?chuyen_id=) ----------
  const ICON = {
    chuyen: '<path d="M4 16V8a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v8"/><path d="M3 16h18v2a1 1 0 0 1-1 1h-1M5 19H4a1 1 0 0 1-1-1v-2"/><circle cx="8" cy="16" r="1.2"/><circle cx="16" cy="16" r="1.2"/>',
    thaoTac: '<path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/>',
    tongQuan: '<path d="M8 6h12M8 12h12M8 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01"/>',
    thongKe: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    hanhTrinh: '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h6a4 4 0 0 1 0 8h-4a4 4 0 0 0 0 8"/>',
    hangHoa: '<path d="M21 8l-9-5-9 5 9 5 9-5Z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>',
  };

  function veMucDieuHuong() {
    const trang = location.pathname.split("/").pop() || "";
    const chuyenId = new URLSearchParams(location.search).get("chuyen_id");
    const q = chuyenId ? `?chuyen_id=${encodeURIComponent(chuyenId)}` : "";
    // "Thao tác chuyến này" chia 2 phần cùng trang chuyen-dang-chay.html, phân biệt bằng ?phan=
    const phanDangXem = new URLSearchParams(location.search).get("phan") === "hang" ? "hang" : "khach";
    const muc = [
      { file: "chuyen-cua-toi.html", nhan: "Chuyến của tôi", icon: ICON.chuyen },
      chuyenId && {
        nhom: "Thao tác chuyến này", icon: ICON.thaoTac,
        con: [
          { file: "chuyen-dang-chay.html", nhan: "Hành trình chuyến xe", q, phan: "khach", icon: ICON.hanhTrinh },
          { file: "chuyen-dang-chay.html", nhan: "Hàng hóa chuyến này", q: `${q}&phan=hang`, phan: "hang", icon: ICON.hangHoa },
        ],
      },
      chuyenId && { file: "chi-tiet-chuyen.html", nhan: "Tổng quan chuyến này", icon: ICON.tongQuan, q },
      { file: "thong-ke.html", nhan: "Thống kê & chuyến đã chạy", icon: ICON.thongKe },
    ].filter(Boolean);
    const svg = (icon) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon}</svg>`;
    const lienKet = (m, la_con) => {
      const dang = m.file === trang && (m.phan === undefined || m.phan === phanDangXem);
      return `<a class="tk-menu__muc${la_con ? " tk-menu__muc--con" : ""}${dang ? " tk-menu__muc--dang-chon" : ""}" role="menuitem" href="${m.file}${m.q || ""}"${dang ? ' aria-current="page"' : ""}>
        ${svg(m.icon)}${esc(m.nhan)}
      </a>`;
    };
    return muc
      .map((m) => m.nhom
        ? `<div class="tk-menu__nhom" role="group" aria-label="${esc(m.nhom)}"><div class="tk-menu__nhom-ten">${svg(m.icon)}${esc(m.nhom)}</div>${m.con.map((c) => lienKet(c, true)).join("")}</div>`
        : lienKet(m, false))
      .join("") + '<div class="tk-menu__chia" role="separator"></div>';
  }

  // ---------- Nút ☰ + menu thả xuống ----------
  let hoTenHienTai = localStorage.getItem("ho_ten") || "";

  const khungNut = document.createElement("div");
  khungNut.className = "tk-khung";
  khungNut.innerHTML = `
    <button type="button" class="btn-icon-circle btn-icon-circle--dark tk-avatar" id="tk-avatar"
            aria-haspopup="true" aria-expanded="false" aria-label="Menu" title="Menu">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
    </button>
    <div class="tk-menu" id="tk-menu" role="menu" hidden>
      <div class="tk-menu__ten"><span class="tk-menu__chu" id="tk-menu-chu"></span><span id="tk-menu-ten"></span></div>
      ${veMucDieuHuong()}
      <button type="button" class="tk-menu__muc tk-menu__muc--tuy-chon" data-px="giao-dien" role="menuitem">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>
        Giao diện <span class="tk-menu__gt" id="px-giao-dien-gt"></span>
      </button>
      <button type="button" class="tk-menu__muc tk-menu__muc--tuy-chon" data-px="am-bao" role="menuitem">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/></svg>
        Âm báo khi xác nhận <span class="tk-menu__gt" id="px-am-bao-gt"></span>
      </button>
      <button type="button" class="tk-menu__muc" id="tk-ho-so" role="menuitem">
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="7.5" r="4.2"/><path d="M3.8 21c0-4.2 3.6-7 8.2-7s8.2 2.8 8.2 7c0 .6-.4 1-1 1H4.8c-.6 0-1-.4-1-1Z"/></svg>
        Hồ sơ
      </button>
      <button type="button" class="tk-menu__muc tk-menu__muc--dang-xuat" id="tk-dang-xuat" role="menuitem">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>
        Đăng xuất
      </button>
    </div>`;

  function capNhatTen(ten) {
    hoTenHienTai = ten;
    khungNut.querySelector("#tk-menu-chu").textContent = chuDau(ten);
    khungNut.querySelector("#tk-menu-ten").textContent = ten || "Phụ xe";
  }

  // Gắn vào thanh trên: thay nút "Đăng xuất" cũ (nếu còn), hoặc thêm vào cuối nhóm nút
  let nhomNut = document.querySelector(".topbar-actions");
  if (!nhomNut) {
    nhomNut = document.createElement("div");
    nhomNut.className = "topbar-actions";
    document.querySelector(".topbar").appendChild(nhomNut);
  }
  nhomNut.querySelectorAll('button[onclick="dangXuat()"]').forEach((nut) => nut.remove());
  nhomNut.appendChild(khungNut);
  capNhatTen(hoTenHienTai);

  const nutAvatar = khungNut.querySelector("#tk-avatar");
  const menu = khungNut.querySelector("#tk-menu");

  function moMenu(mo) {
    menu.hidden = !mo;
    nutAvatar.setAttribute("aria-expanded", String(mo));
  }

  nutAvatar.addEventListener("click", (e) => {
    e.stopPropagation();
    moMenu(menu.hidden);
  });
  document.addEventListener("click", (e) => {
    if (!khungNut.contains(e.target)) moMenu(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") moMenu(false);
  });
  khungNut.querySelector("#tk-dang-xuat").addEventListener("click", () => dangXuat());
  khungNut.querySelector("#tk-ho-so").addEventListener("click", () => {
    moMenu(false);
    moHoSo();
  });

  // ---------- Hộp thoại hồ sơ ----------
  const hop = document.createElement("div");
  hop.className = "modal-overlay";
  hop.hidden = true;
  hop.innerHTML = `
    <div class="modal-sheet" role="dialog" aria-modal="true" aria-labelledby="tk-tieu-de">
      <div class="tk-ho-so" id="tk-noi-dung"></div>
    </div>`;
  document.body.appendChild(hop);
  const noiDung = hop.querySelector("#tk-noi-dung");
  hop.addEventListener("click", (e) => {
    if (e.target === hop) dongHoSo();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !hop.hidden) dongHoSo();
  });

  let hoSo = null;
  let baoLoi = "";
  let baoOk = "";

  function dongHoSo() {
    hop.hidden = true;
  }

  async function moHoSo() {
    baoLoi = "";
    baoOk = "";
    hop.hidden = false;
    noiDung.innerHTML = '<p class="empty-state">Đang tải...</p>';
    try {
      hoSo = await apiGet("/auth/toi");
      veHoSo();
    } catch (err) {
      noiDung.innerHTML = `<p class="text-error">${esc(err.message)}</p>
        <button type="button" class="btn-confirm btn-confirm--outline btn-confirm--block" data-dong>Đóng</button>`;
      noiDung.querySelector("[data-dong]").addEventListener("click", dongHoSo);
    }
  }

  function veHoSo() {
    noiDung.innerHTML = `
      <div class="tk-ho-so__dau">
        <div class="tk-ho-so__avatar">${esc(chuDau(hoSo.ho_ten))}</div>
        <div>
          <h2 id="tk-tieu-de">${esc(hoSo.ho_ten)}</h2>
          <span class="chip chip--tim">${esc(VAI_TRO[hoSo.vai_tro] || hoSo.vai_tro)}</span>
        </div>
      </div>
      ${baoOk ? `<p class="text-success">${esc(baoOk)}</p>` : ""}
      <form id="tk-form" novalidate>
        <label class="tk-nhan" for="tk-ho-ten">Họ và tên</label>
        <input class="input-field" id="tk-ho-ten" autocomplete="name" value="${esc(hoSo.ho_ten)}" required />
        <label class="tk-nhan" for="tk-sdt">Số điện thoại</label>
        <input class="input-field" id="tk-sdt" type="tel" inputmode="tel" autocomplete="tel" value="${esc(hoSo.so_dien_thoai)}" required />
        <label class="tk-nhan" for="tk-email">Email (không sửa được)</label>
        <input class="input-field" id="tk-email" value="${esc(hoSo.email)}" disabled />
        <p class="hint">Tham gia từ ${esc(dinhDangNgay(hoSo.ngay_tao))}</p>
        ${baoLoi ? `<div class="text-error">${esc(baoLoi)}</div>` : ""}
        <button class="btn-primary" type="submit">Lưu thay đổi</button>
        <button class="btn-confirm btn-confirm--outline btn-confirm--block" type="button" data-dong>Đóng</button>
      </form>`;
    noiDung.querySelector("[data-dong]").addEventListener("click", dongHoSo);
    noiDung.querySelector("#tk-form").addEventListener("submit", luuHoSo);
  }

  async function luuHoSo(e) {
    e.preventDefault();
    const hoTen = noiDung.querySelector("#tk-ho-ten").value.trim();
    const sdt = noiDung.querySelector("#tk-sdt").value.trim();
    const nut = e.submitter;
    baoLoi = "";
    baoOk = "";

    // Chỉ gửi trường thật sự đổi (API cho sửa từng trường)
    const thayDoi = {};
    if (hoTen !== hoSo.ho_ten) thayDoi.ho_ten = hoTen;
    if (sdt !== hoSo.so_dien_thoai) thayDoi.so_dien_thoai = sdt;
    if (!hoTen) {
      baoLoi = "Họ và tên không được để trống";
      return veHoSo();
    }
    if (Object.keys(thayDoi).length === 0) {
      baoOk = "Không có gì thay đổi.";
      return veHoSo();
    }

    if (nut) nut.disabled = true;
    try {
      await apiPut("/auth/toi", thayDoi);
      hoSo = await apiGet("/auth/toi");
      localStorage.setItem("ho_ten", hoSo.ho_ten);
      capNhatTen(hoSo.ho_ten);
      const loiChao = document.getElementById("loi-chao");
      if (loiChao) loiChao.textContent = `Xin chào, ${hoSo.ho_ten}`;
      baoOk = "Đã lưu thông tin.";
    } catch (err) {
      baoLoi = err.message;
    }
    veHoSo();
  }
})();
