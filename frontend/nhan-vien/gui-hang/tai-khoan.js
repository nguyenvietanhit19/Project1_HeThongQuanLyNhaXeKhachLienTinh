/*
 * tai-khoan.js — Modal "Tài khoản của tôi" (mở từ menu ở cuối sidebar, nav.js).
 * Cùng chức năng với bản của Quản lý (quan-ly/tai-khoan.js): xem họ tên / email / SĐT / vai trò /
 * ngày tham gia, sửa họ tên và SĐT tại chỗ (email không sửa được), đổi mật khẩu.
 * API dùng chung mọi vai trò: GET/PUT /auth/toi, PUT /auth/doi-mat-khau.
 * Khung modal nằm trong index.html (#modalTaiKhoan), dùng class modal của phân hệ gửi hàng.
 */

const TaiKhoanGuiHang = (() => {
  const ICON_BUT = '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="M13.5 6.5l4 4"/>';
  const TRUONG = {
    ho_ten: { nhan: "Họ và tên", loai: "text" },
    so_dien_thoai: { nhan: "Số điện thoại", loai: "tel" },
  };
  let hoSo = null;
  let dangSua = null; // "ho_ten" | "so_dien_thoai" | null
  let loiSua = "";
  let baoOk = "";
  let moDoiMk = false;
  let baoOkTimer = null;
  let daGanSuKienKhung = false;

  const chuDau = ten => (ten || "").trim().split(/\s+/).slice(-1)[0]?.charAt(0).toUpperCase() || "?";
  const noiDung = () => $("tkNoiDung");
  const dangMo = () => $("modalTaiKhoan").classList.contains("active");

  function dong() {
    dongModal("modalTaiKhoan");
  }

  function ganSuKienKhung() {
    if (daGanSuKienKhung) return;
    daGanSuKienKhung = true;
    // Tự đóng bằng Esc kể cả khi phim-tat.js chưa khởi tạo (tài khoản chưa gán văn phòng)
    $("modalTaiKhoan").addEventListener("keydown", e => {
      if (e.key === "Escape" && !dangSua) dong();
    });
  }

  function dinhDangNgayThamGia(iso) {
    if (!iso) return "";
    const p = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric" })
      .formatToParts(new Date(iso))
      .reduce((o, x) => ({ ...o, [x.type]: x.value }), {});
    return `${p.day}/${p.month}/${p.year}`;
  }

  function hangThongTin(truong) {
    const t = TRUONG[truong];
    const gia = hoSo[truong] || "";
    return `
      <li class="tk-muc" data-truong="${truong}">
        <div class="tk-hang">
          <span class="tk-nhan">${t.nhan}</span>
          <span class="tk-phai">
            <span class="tk-gia-tri">${escapeHtml(gia) || "—"}</span>
            <button type="button" class="tk-but" data-hanh="sua" aria-label="Sửa ${t.nhan.toLowerCase()}">${svgIcon(ICON_BUT, "")}</button>
          </span>
        </div>
        ${dangSua === truong
          ? `<div class="tk-sua">
              <input class="form-input" type="${t.loai}" id="tk-o-${truong}" value="${escapeHtml(gia)}" maxlength="100" placeholder="Nhập ${t.nhan.toLowerCase()} mới..." />
              ${loiSua ? `<div class="tk-loi">${escapeHtml(loiSua)}</div>` : ""}
              <div class="tk-sua__nut">
                <button type="button" class="btn-close-modal" data-hanh="huy">Hủy</button>
                <button type="button" class="btn-print" data-hanh="luu">Lưu</button>
              </div>
            </div>`
          : ""}
      </li>`;
  }

  function dongCoDinh(nhan, giaTri, ghiChu = "") {
    return `<li class="tk-muc"><div class="tk-hang"><span class="tk-nhan">${nhan}</span><span class="tk-phai"><span class="tk-gia-tri"${ghiChu ? ` title="${ghiChu}"` : ""}>${escapeHtml(giaTri)}</span></span></div></li>`;
  }

  function ve() {
    const goc = noiDung();
    goc.innerHTML = `
      <div class="tk-avatar" aria-hidden="true">${escapeHtml(chuDau(hoSo.ho_ten))}</div>
      ${baoOk ? `<div class="tk-bao-ok" role="status">${escapeHtml(baoOk)}</div>` : ""}
      <ul class="tk-ds">
        ${hangThongTin("ho_ten")}
        ${hangThongTin("so_dien_thoai")}
        ${dongCoDinh("Email", hoSo.email, "Email không thể thay đổi")}
        ${dongCoDinh("Vai trò", NHAN_VAI_TRO[hoSo.vai_tro] || hoSo.vai_tro || "")}
        ${state.vanPhong ? dongCoDinh("Văn phòng", state.vanPhong.ten) : ""}
        ${dongCoDinh("Ngày tham gia", dinhDangNgayThamGia(hoSo.ngay_tao))}
      </ul>

      <button type="button" class="tk-doi-mk-nut" id="tk-mo-doi-mk" aria-expanded="${moDoiMk}">Đổi mật khẩu <span aria-hidden="true">${moDoiMk ? "▴" : "▾"}</span></button>
      <form class="tk-doi-mk" id="tk-form-mk" novalidate ${moDoiMk ? "" : "hidden"}>
        <div class="form-group">
          <label class="form-label" for="tk-mk-cu">Mật khẩu hiện tại</label>
          <input class="form-input" type="password" id="tk-mk-cu" autocomplete="current-password" />
        </div>
        <div class="form-group">
          <label class="form-label" for="tk-mk-moi">Mật khẩu mới</label>
          <input class="form-input" type="password" id="tk-mk-moi" autocomplete="new-password" placeholder="Tối thiểu 6 ký tự" />
        </div>
        <div class="form-group">
          <label class="form-label" for="tk-mk-lai">Nhập lại mật khẩu mới</label>
          <input class="form-input" type="password" id="tk-mk-lai" autocomplete="new-password" />
        </div>
        <div class="tk-loi" id="tk-loi-mk" hidden></div>
        <div class="receipt-actions"><button type="submit" class="btn-print">Cập nhật mật khẩu</button></div>
      </form>

      <div class="receipt-actions"><button type="button" class="btn-close-modal" id="tk-dong">Đóng</button></div>`;
    ganSuKien(goc);
    const o = goc.querySelector(".tk-sua input");
    if (o) {
      o.focus();
      o.setSelectionRange(o.value.length, o.value.length);
    }
  }

  function ganSuKien(goc) {
    goc.querySelector("#tk-dong").addEventListener("click", dong);
    goc.querySelectorAll("[data-hanh]").forEach(nut => {
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
      oSua.addEventListener("keydown", e => {
        if (e.key === "Enter") {
          e.preventDefault();
          luu(oSua.closest("[data-truong]").dataset.truong);
        } else if (e.key === "Escape") {
          e.stopPropagation(); // chỉ thoát chế độ sửa, không đóng cả modal (phim-tat.js đóng mọi modal khi Esc)
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
    const gia = $(`tk-o-${truong}`).value.trim();
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
        try { localStorage.setItem("ho_ten", hoSo.ho_ten); } catch (_) {}
        renderThongTinTaiKhoan();
      }
      dangSua = null;
      loiSua = "";
      baoOk = "Đã lưu thay đổi.";
      clearTimeout(baoOkTimer);
      baoOkTimer = setTimeout(() => {
        baoOk = "";
        if (dangMo() && !dangSua) ve();
      }, 2500);
    } catch (err) {
      loiSua = err.message;
    }
    ve();
  }

  async function doiMatKhau(e) {
    e.preventDefault();
    const loi = $("tk-loi-mk");
    const bao = nd => {
      loi.textContent = nd;
      loi.hidden = !nd;
    };
    bao("");
    const cu = $("tk-mk-cu").value;
    const moi = $("tk-mk-moi").value;
    const lai = $("tk-mk-lai").value;
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
    ganSuKienKhung();
    dangSua = null;
    loiSua = "";
    baoOk = "";
    moDoiMk = false;
    moModal("modalTaiKhoan");
    const goc = noiDung();
    goc.innerHTML = '<p class="card-desc">Đang tải...</p>';
    try {
      hoSo = await apiGet("/auth/toi");
      ve();
    } catch (err) {
      goc.innerHTML = `<div class="tk-loi">${escapeHtml(err.message)}</div><div class="receipt-actions"><button type="button" class="btn-close-modal" id="tk-dong">Đóng</button></div>`;
      goc.querySelector("#tk-dong").addEventListener("click", dong);
    }
  }

  return { mo };
})();
