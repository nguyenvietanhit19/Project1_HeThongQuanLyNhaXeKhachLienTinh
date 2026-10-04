/*
 * Modal "Tài khoản của tôi" (thông tin cá nhân) — mở từ menu "Xin chào, …" hoặc footer, ngay trên trang
 * đang xem, không chuyển trang. Xem họ tên / email / số điện thoại; bấm biểu tượng cây bút để sửa họ tên
 * hoặc số điện thoại tại chỗ (email không sửa được). Có đổi mật khẩu và đăng xuất.
 * Cần /shared/api-client.js, /shared/so-dien-thoai.js và khach-hang/khung-trang.js nạp trước. CSS: .hs-* trong trang-chu.css.
 */

const HS_BUT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="M13.5 6.5l4 4"/></svg>';
const HS_NGUOI = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="7.5" r="4.2"/><path d="M3.8 21c0-4.2 3.6-7 8.2-7s8.2 2.8 8.2 7c0 .6-.4 1-1 1H4.8c-.6 0-1-.4-1-1Z"/></svg>';
const HS_VAI_TRO = { khach_hang: "Khách hàng" };
const HS_TRUONG = {
  ho_ten: { nhan: "Họ và tên", loai: "text", autocomplete: "name" },
  so_dien_thoai: { nhan: "Số điện thoại", loai: "tel", autocomplete: "tel" },
};

let hsModal = null;
let hsHoSo = null; // { ho_ten, email, so_dien_thoai, ngay_tao }
let hsDangSua = null; // "ho_ten" | "so_dien_thoai" | null
let hsLoiSua = "";
let hsBaoOk = "";
let hsMoDoiMk = false;
let hsBaoOkTimer = null;

function hsDungModal() {
  if (hsModal) return;
  hsModal = document.createElement("div");
  hsModal.className = "tc-modal";
  hsModal.hidden = true;
  hsModal.innerHTML = `
    <div class="tc-modal__hop tc-modal__hop--nho" role="dialog" aria-modal="true" aria-labelledby="hs-tieu-de">
      <button type="button" class="tc-modal__dong" id="hs-dong" aria-label="Đóng">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>
      </button>
      <div id="hs-noi-dung"></div>
    </div>`;
  document.body.appendChild(hsModal);
  hsModal.addEventListener("click", (e) => {
    if (e.target === hsModal) hsDong();
  });
  hsModal.querySelector("#hs-dong").addEventListener("click", hsDong);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !hsModal.hidden && !hsDangSua) hsDong();
  });
}

function hsDong() {
  hsModal.hidden = true;
  document.body.style.overflow = "";
}

function hsChuDau(ten) {
  return ((ten || "").trim().split(/\s+/).slice(-1)[0] || "?").charAt(0).toUpperCase();
}

async function moHoSo() {
  hsDungModal();
  hsDangSua = null;
  hsLoiSua = "";
  hsBaoOk = "";
  hsMoDoiMk = false;
  hsModal.hidden = false;
  document.body.style.overflow = "hidden";
  const noiDung = hsModal.querySelector("#hs-noi-dung");
  noiDung.innerHTML = '<div class="tc-khung-xuong" style="height:220px"></div>';
  try {
    hsHoSo = await apiGet("/auth/toi");
    hsVe();
  } catch (err) {
    // Token hỏng/hết hạn — coi như đã đăng xuất
    ["token", "vai_tro", "ho_ten"].forEach((k) => localStorage.removeItem(k));
    veNav();
    hsDong();
  }
}

function hsDongThongTin(truong) {
  const t = HS_TRUONG[truong];
  const gia = hsHoSo[truong] || "";
  const dangSua = hsDangSua === truong;
  return `
    <li class="hs-muc" data-truong="${truong}">
      <div class="hs-hang">
        <span class="hs-nhan">${t.nhan}</span>
        <span class="hs-phai">
          <span class="hs-gia-tri">${esc(gia)}</span>
          <button type="button" class="hs-but" data-hanh="sua" aria-label="Sửa ${t.nhan.toLowerCase()}">${HS_BUT}</button>
        </span>
      </div>
      ${
        dangSua
          ? `<div class="hs-sua">
              <input type="${t.loai}" id="hs-o-${truong}" value="${esc(gia)}" maxlength="100" autocomplete="${t.autocomplete}" placeholder="Nhập ${t.nhan.toLowerCase()} mới..." />
              ${hsLoiSua ? `<div class="hs-loi-dong">${esc(hsLoiSua)}</div>` : ""}
              <div class="hs-sua__nut">
                <button type="button" class="hs-nut-nho hs-nut-nho--phu" data-hanh="huy">Huỷ</button>
                <button type="button" class="hs-nut-nho hs-nut-nho--chinh" data-hanh="luu">Lưu</button>
              </div>
            </div>`
          : ""
      }
    </li>`;
}

function hsNgayThamGia(iso) {
  if (!iso) return "";
  const p = new Intl.DateTimeFormat("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric", hour12: false })
    .formatToParts(new Date(iso))
    .reduce((o, x) => ({ ...o, [x.type]: x.value }), {});
  return `${p.hour}:${p.minute} ${p.day}/${p.month}/${p.year}`;
}

function hsVe() {
  const noiDung = hsModal.querySelector("#hs-noi-dung");
  noiDung.innerHTML = `
    <h2 class="hs-tieu-de" id="hs-tieu-de"><span class="hs-tieu-de__icon">${HS_NGUOI}</span>Thông tin tài khoản</h2>
    <div class="hs-avatar" aria-hidden="true">${esc(hsChuDau(hsHoSo.ho_ten))}</div>

    ${hsBaoOk ? `<div class="hs-bao-ok" role="status">${esc(hsBaoOk)}</div>` : ""}

    <ul class="hs-ds">
      ${hsDongThongTin("ho_ten")}
      ${hsDongThongTin("so_dien_thoai")}
      <li class="hs-muc">
        <div class="hs-hang">
        <span class="hs-nhan">Email</span>
        <span class="hs-phai"><span class="hs-gia-tri" title="Email không thể thay đổi">${esc(hsHoSo.email)}</span></span>
        </div>
      </li>
      <li class="hs-muc">
        <div class="hs-hang">
        <span class="hs-nhan">Vai trò</span>
        <span class="hs-phai"><span class="hs-gia-tri">${esc(HS_VAI_TRO[hsHoSo.vai_tro] || hsHoSo.vai_tro || "")}</span></span>
        </div>
      </li>
      <li class="hs-muc">
        <div class="hs-hang">
        <span class="hs-nhan">Ngày tham gia</span>
        <span class="hs-phai"><span class="hs-gia-tri">${esc(hsNgayThamGia(hsHoSo.ngay_tao))}</span></span>
        </div>
      </li>
    </ul>

    <button type="button" class="hs-ghi-chu-nut" id="hs-mo-doi-mk" aria-expanded="${hsMoDoiMk}">
      Đổi mật khẩu <span aria-hidden="true">${hsMoDoiMk ? "▴" : "▾"}</span>
    </button>
    <form class="hs-doi-mk" id="hs-form-mk" novalidate ${hsMoDoiMk ? "" : "hidden"}>
      <label>Mật khẩu hiện tại<input type="password" id="hs-mk-cu" autocomplete="current-password" /></label>
      <label>Mật khẩu mới<input type="password" id="hs-mk-moi" autocomplete="new-password" placeholder="Tối thiểu 6 ký tự" /></label>
      <label>Nhập lại mật khẩu mới<input type="password" id="hs-mk-lai" autocomplete="new-password" /></label>
      <div class="hs-loi-dong" id="hs-loi-mk" hidden></div>
      <button type="submit" class="hs-nut hs-nut--chinh">Cập nhật mật khẩu</button>
    </form>
`;

  hsGanSuKien(noiDung);
  const o = noiDung.querySelector(".hs-sua input");
  if (o) {
    o.focus();
    o.setSelectionRange(o.value.length, o.value.length);
  }
}

function hsGanSuKien(goc) {
  goc.querySelectorAll("[data-hanh]").forEach((nut) => {
    const truong = nut.closest("[data-truong]").dataset.truong;
    nut.addEventListener("click", () => {
      if (nut.dataset.hanh === "sua") {
        hsDangSua = truong;
        hsLoiSua = "";
        hsBaoOk = "";
        hsVe();
      } else if (nut.dataset.hanh === "huy") {
        hsDangSua = null;
        hsLoiSua = "";
        hsVe();
      } else {
        hsLuu(truong);
      }
    });
  });

  const oSua = goc.querySelector(".hs-sua input");
  if (oSua) {
    oSua.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        hsLuu(oSua.closest("[data-truong]").dataset.truong);
      } else if (e.key === "Escape") {
        e.stopPropagation(); // chỉ thoát chế độ sửa, không đóng luôn cả modal
        hsDangSua = null;
        hsLoiSua = "";
        hsVe();
      }
    });
  }

  goc.querySelector("#hs-mo-doi-mk").addEventListener("click", () => {
    hsMoDoiMk = !hsMoDoiMk;
    hsVe();
  });
  goc.querySelector("#hs-form-mk").addEventListener("submit", hsDoiMatKhau);
}

async function hsLuu(truong) {
  const goc = hsModal.querySelector("#hs-noi-dung");
  const gia = goc.querySelector(`#hs-o-${truong}`).value.trim();
  if (gia === (hsHoSo[truong] || "")) {
    hsDangSua = null;
    return hsVe(); // không đổi gì thì chỉ thoát chế độ sửa
  }
  let giaGui = gia;
  if (truong === "so_dien_thoai") {
    const kq = kiemTraSoDienThoai(gia);
    if (!kq.hopLe) {
      hsLoiSua = kq.loi;
      return hsVe();
    }
    giaGui = kq.soChuan;
    if (giaGui === hsHoSo.so_dien_thoai) {
      hsDangSua = null; // gõ khác dạng nhưng cùng 1 số
      return hsVe();
    }
  } else if (!gia) {
    hsLoiSua = "Họ và tên không được để trống.";
    return hsVe();
  }
  try {
    await apiPut("/auth/toi", { [truong]: giaGui });
    // Lấy lại từ server để hiện đúng giá trị đã được chuẩn hóa (VD số điện thoại bỏ khoảng trắng)
    hsHoSo = await apiGet("/auth/toi");
    if (truong === "ho_ten") {
      localStorage.setItem("ho_ten", hsHoSo.ho_ten);
      veNav(); // cập nhật lời chào "Xin chào, …" ở thanh trên
    }
    hsDangSua = null;
    hsLoiSua = "";
    hsBaoOk = "Đã lưu thay đổi.";
    clearTimeout(hsBaoOkTimer);
    hsBaoOkTimer = setTimeout(() => {
      hsBaoOk = "";
      if (!hsModal.hidden && !hsDangSua) hsVe();
    }, 2500);
  } catch (err) {
    hsLoiSua = err.message;
  }
  hsVe();
}

async function hsDoiMatKhau(e) {
  e.preventDefault();
  const loi = hsModal.querySelector("#hs-loi-mk");
  const bao = (nd) => {
    loi.textContent = nd;
    loi.hidden = !nd;
  };
  bao("");
  const cu = hsModal.querySelector("#hs-mk-cu").value;
  const moi = hsModal.querySelector("#hs-mk-moi").value;
  const lai = hsModal.querySelector("#hs-mk-lai").value;
  if (!cu || !moi) return bao("Vui lòng nhập đủ mật khẩu hiện tại và mật khẩu mới.");
  if (moi.length < 6) return bao("Mật khẩu mới cần tối thiểu 6 ký tự.");
  if (moi !== lai) return bao("Mật khẩu nhập lại chưa khớp.");
  try {
    await apiPut("/auth/doi-mat-khau", { mat_khau_cu: cu, mat_khau_moi: moi });
    hsMoDoiMk = false;
    hsBaoOk = "Đổi mật khẩu thành công.";
    hsVe();
  } catch (err) {
    bao(err.message);
  }
}
