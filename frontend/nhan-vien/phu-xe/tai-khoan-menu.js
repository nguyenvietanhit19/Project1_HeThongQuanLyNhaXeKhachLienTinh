/*
 * Menu tài khoản của phụ xe: nút tròn chữ cái đầu tên ở góc phải thanh trên → mở menu
 * "Hồ sơ" / "Đăng xuất". "Hồ sơ" mở hộp thoại xem họ tên, SĐT, email, vai trò, ngày tham gia
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
    return iso ? new Date(iso).toLocaleDateString("vi-VN") : "";
  }

  // ---------- Nút avatar + menu thả xuống ----------
  let hoTenHienTai = localStorage.getItem("ho_ten") || "";

  const khungNut = document.createElement("div");
  khungNut.className = "tk-khung";
  khungNut.innerHTML = `
    <button type="button" class="btn-icon-circle btn-icon-circle--dark tk-avatar" id="tk-avatar"
            aria-haspopup="true" aria-expanded="false" aria-label="Tài khoản của tôi" title="Tài khoản"></button>
    <div class="tk-menu" id="tk-menu" role="menu" hidden>
      <div class="tk-menu__ten" id="tk-menu-ten"></div>
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
    khungNut.querySelector("#tk-avatar").textContent = chuDau(ten);
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
