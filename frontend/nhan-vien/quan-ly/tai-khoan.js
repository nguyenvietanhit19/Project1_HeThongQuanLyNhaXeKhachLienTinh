/*
 * Modal "Tài khoản của tôi" cho Quản lý: xem họ tên / email / số điện thoại / vai trò / ngày tham gia, sửa họ tên
 * và số điện thoại tại chỗ (email không sửa được), đổi mật khẩu. Dùng chung API với khách hàng và phụ xe:
 * GET/PUT /auth/toi, PUT /auth/doi-mat-khau. Mở từ menu ở cuối sidebar (nav.js).
 * Bọc trong IIFE để không đụng tên biến của từng trang. Cần nạp SAU api-client.js và nav.js.
 */

const TaiKhoanQuanLy = (() => {
  const ICON_BUT = '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="M13.5 6.5l4 4"/>';
  const TRUONG = {
    ho_ten: { nhan: "Họ và tên", loai: "text" },
    so_dien_thoai: { nhan: "Số điện thoại", loai: "tel" },
  };
  let overlay = null;
  let hoSo = null;
  let dangSua = null; // "ho_ten" | "so_dien_thoai" | null
  let loiSua = "";
  let baoOk = "";
  let moDoiMk = false;
  let baoOkTimer = null;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const chuDau = (ten) => (ten || "").trim().split(/\s+/).slice(-1)[0]?.charAt(0).toUpperCase() || "?";

  function dungOverlay() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "nv-modal-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="nv-modal" style="max-width:480px;" role="dialog" aria-modal="true" aria-labelledby="tk-tieu-de">
        <div class="nv-modal__header">
          <div class="nv-modal__header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_NGUOI}</svg>
          </div>
          <h2 id="tk-tieu-de">Tài khoản của tôi</h2>
        </div>
        <div class="nv-modal__body" id="tk-noi-dung"></div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) dong();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !overlay.hidden && !dangSua) dong();
    });
  }

  function dong() {
    overlay.hidden = true;
  }

  function hangThongTin(truong) {
    const t = TRUONG[truong];
    const gia = hoSo[truong] || "";
    return `
      <li class="tk-muc" data-truong="${truong}">
        <div class="tk-hang">
          <span class="tk-nhan">${t.nhan}</span>
          <span class="tk-phai">
            <span class="tk-gia-tri">${esc(gia) || "—"}</span>
            <button type="button" class="tk-but" data-hanh="sua" aria-label="Sửa ${t.nhan.toLowerCase()}">${svgIcon(ICON_BUT)}</button>
          </span>
        </div>
        ${
          dangSua === truong
            ? `<div class="tk-sua">
                <input class="input-field" type="${t.loai}" id="tk-o-${truong}" value="${esc(gia)}" maxlength="100" placeholder="Nhập ${t.nhan.toLowerCase()} mới..." />
                ${loiSua ? `<div class="text-error">${esc(loiSua)}</div>` : ""}
                <div class="tk-sua__nut">
                  <button type="button" class="nv-btn-secondary" data-hanh="huy">Hủy</button>
                  <button type="button" class="btn-primary" data-hanh="luu">Lưu</button>
                </div>
              </div>`
            : ""
        }
      </li>`;
  }

  function dinhDangNgay(iso) {
    if (!iso) return "";
    const p = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric" })
      .formatToParts(new Date(iso))
      .reduce((o, x) => ({ ...o, [x.type]: x.value }), {});
    return `${p.day}/${p.month}/${p.year}`;
  }

  function dongCoDinh(nhan, giaTri, ghiChu = "") {
    return `<li class="tk-muc"><div class="tk-hang"><span class="tk-nhan">${nhan}</span><span class="tk-phai"><span class="tk-gia-tri"${ghiChu ? ` title="${ghiChu}"` : ""}>${esc(giaTri)}</span></span></div></li>`;
  }

  function ve() {
    const noiDung = overlay.querySelector("#tk-noi-dung");
    noiDung.innerHTML = `
      <div class="tk-avatar" aria-hidden="true">${esc(chuDau(hoSo.ho_ten))}</div>
      ${baoOk ? `<div class="tk-bao-ok" role="status">${esc(baoOk)}</div>` : ""}
      <ul class="tk-ds">
        ${hangThongTin("ho_ten")}
        ${hangThongTin("so_dien_thoai")}
        ${dongCoDinh("Email", hoSo.email, "Email không thể thay đổi")}
        ${dongCoDinh("Vai trò", NHAN_VAI_TRO_QUAN_LY[hoSo.vai_tro] || hoSo.vai_tro || "")}
        ${dongCoDinh("Ngày tham gia", dinhDangNgay(hoSo.ngay_tao))}
      </ul>

      <button type="button" class="tk-doi-mk-nut" id="tk-mo-doi-mk" aria-expanded="${moDoiMk}">Đổi mật khẩu <span aria-hidden="true">${moDoiMk ? "▴" : "▾"}</span></button>
      <form class="tk-doi-mk" id="tk-form-mk" novalidate ${moDoiMk ? "" : "hidden"}>
        <label class="nv-label" for="tk-mk-cu">Mật khẩu hiện tại</label>
        <input class="input-field" type="password" id="tk-mk-cu" autocomplete="current-password" />
        <label class="nv-label" for="tk-mk-moi">Mật khẩu mới</label>
        <input class="input-field" type="password" id="tk-mk-moi" autocomplete="new-password" placeholder="Tối thiểu 6 ký tự" />
        <label class="nv-label" for="tk-mk-lai">Nhập lại mật khẩu mới</label>
        <input class="input-field" type="password" id="tk-mk-lai" autocomplete="new-password" />
        <div class="text-error" id="tk-loi-mk" hidden></div>
        <div class="nv-modal__actions"><button type="submit" class="btn-primary">Cập nhật mật khẩu</button></div>
      </form>

      <div class="nv-modal__actions tk-chan"><button type="button" class="nv-btn-secondary" id="tk-dong">Đóng</button></div>`;
    ganSuKien(noiDung);
    const o = noiDung.querySelector(".tk-sua input");
    if (o) {
      o.focus();
      o.setSelectionRange(o.value.length, o.value.length);
    }
  }

  function ganSuKien(goc) {
    goc.querySelector("#tk-dong").addEventListener("click", dong);
    goc.querySelectorAll("[data-hanh]").forEach((nut) => {
      const truong = nut.closest("[data-truong]").dataset.truong;
      nut.addEventListener("click", () => {
        if (nut.dataset.hanh === "sua") {
          dangSua = truong;
          loiSua = "";
          baoOk = "";
          ve();
        } else if (nut.dataset.hanh === "huy") {
          dangSua = null;
          loiSua = "";
          ve();
        } else {
          luu(truong);
        }
      });
    });
    const oSua = goc.querySelector(".tk-sua input");
    if (oSua) {
      oSua.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          luu(oSua.closest("[data-truong]").dataset.truong);
        } else if (e.key === "Escape") {
          e.stopPropagation(); // chỉ thoát chế độ sửa, không đóng cả modal
          dangSua = null;
          loiSua = "";
          ve();
        }
      });
    }
    goc.querySelector("#tk-mo-doi-mk").addEventListener("click", () => {
      moDoiMk = !moDoiMk;
      ve();
    });
    goc.querySelector("#tk-form-mk").addEventListener("submit", doiMatKhau);
  }

  async function luu(truong) {
    const gia = overlay.querySelector(`#tk-o-${truong}`).value.trim();
    if (gia === (hoSo[truong] || "")) {
      dangSua = null;
      return ve();
    }
    if (truong === "ho_ten" && !gia) {
      loiSua = "Họ và tên không được để trống.";
      return ve();
    }
    try {
      await apiPut("/auth/toi", { [truong]: gia });
      hoSo = await apiGet("/auth/toi"); // lấy lại để hiện đúng giá trị đã chuẩn hóa (VD số điện thoại)
      if (truong === "ho_ten") {
        localStorage.setItem("ho_ten", hoSo.ho_ten);
        renderThongTinTaiKhoan();
      }
      dangSua = null;
      loiSua = "";
      baoOk = "Đã lưu thay đổi.";
      clearTimeout(baoOkTimer);
      baoOkTimer = setTimeout(() => {
        baoOk = "";
        if (!overlay.hidden && !dangSua) ve();
      }, 2500);
    } catch (err) {
      loiSua = err.message;
    }
    ve();
  }

  async function doiMatKhau(e) {
    e.preventDefault();
    const loi = overlay.querySelector("#tk-loi-mk");
    const bao = (nd) => {
      loi.textContent = nd;
      loi.hidden = !nd;
    };
    bao("");
    const cu = overlay.querySelector("#tk-mk-cu").value;
    const moi = overlay.querySelector("#tk-mk-moi").value;
    const lai = overlay.querySelector("#tk-mk-lai").value;
    if (!cu || !moi) return bao("Vui lòng nhập đủ mật khẩu hiện tại và mật khẩu mới.");
    if (moi.length < 6) return bao("Mật khẩu mới cần tối thiểu 6 ký tự.");
    if (moi !== lai) return bao("Mật khẩu nhập lại chưa khớp.");
    try {
      await apiPut("/auth/doi-mat-khau", { mat_khau_cu: cu, mat_khau_moi: moi });
      moDoiMk = false;
      baoOk = "Đổi mật khẩu thành công.";
      ve();
    } catch (err) {
      bao(err.message);
    }
  }

  async function mo() {
    dungOverlay();
    dangSua = null;
    loiSua = "";
    baoOk = "";
    moDoiMk = false;
    overlay.hidden = false;
    const noiDung = overlay.querySelector("#tk-noi-dung");
    noiDung.innerHTML = '<p class="nv-hint">Đang tải...</p>';
    try {
      hoSo = await apiGet("/auth/toi");
      ve();
    } catch (err) {
      noiDung.innerHTML = `<div class="text-error">${esc(err.message)}</div><div class="nv-modal__actions tk-chan"><button type="button" class="nv-btn-secondary" id="tk-dong">Đóng</button></div>`;
      noiDung.querySelector("#tk-dong").addEventListener("click", dong);
    }
  }

  return { mo };
})();
