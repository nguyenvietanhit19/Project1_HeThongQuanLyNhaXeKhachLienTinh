/*
 * "Cài đặt" của phụ xe — 3 hộp thoại mở từ menu ☰ → Cài đặt: Giao diện · Âm báo · Hồ sơ.
 *   - Giao diện: chọn Tự động / Sáng / Tối (đổi ngay, nhớ lại lần sau) — phu-xe-theme.js
 *   - Âm báo: bật/tắt, âm lượng, rung, nghe thử từng kiểu âm — phuXe.amThanh (phu-xe-pro.js)
 *   - Hồ sơ: cùng cách làm với "Tài khoản của tôi" của Quản lý (quan-ly/tai-khoan.js): sửa tại chỗ họ tên / SĐT bằng nút bút chì,
 *     email + vai trò + ngày tham gia chỉ xem, đổi mật khẩu. API dùng chung: GET/PUT /auth/toi, PUT /auth/doi-mat-khau.
 * Nạp SAU phu-xe-pro.js, phu-xe-theme.js, api-client.js (và shared/so-dien-thoai.js nếu có để báo lỗi SĐT sớm).
 */
(function () {
  "use strict";

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const chuDau = (ten) => ((ten || "").trim().split(/\s+/).slice(-1)[0] || "?").charAt(0).toUpperCase();
  const VAI_TRO = { phu_xe: "Phụ xe" };
  const ICON_BUT = '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="M13.5 6.5l4 4"/>';
  const svg = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;

  // ---------- Hộp thoại dùng chung ----------
  let hop = null, noiDung = null, truocFocus = null, khiDong = null;

  function dungHop() {
    if (hop) return;
    hop = document.createElement("div");
    hop.className = "modal-overlay";
    hop.hidden = true;
    hop.innerHTML = `<div class="modal-sheet cd-sheet" role="dialog" aria-modal="true" aria-labelledby="cd-tieu-de"><div id="cd-noi-dung"></div></div>`;
    document.body.appendChild(hop);
    noiDung = hop.querySelector("#cd-noi-dung");
    hop.addEventListener("click", (e) => { if (e.target === hop) dong(); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !hop.hidden && !document.querySelector(".cd-sua")) dong();
    });
  }
  function mo(html, onDong) {
    dungHop();
    truocFocus = document.activeElement;
    khiDong = onDong || null;
    noiDung.innerHTML = html;
    hop.hidden = false;
  }
  let dangDong = false;
  function dong() {
    if (!hop || hop.hidden || dangDong) return;
    dangDong = true;
    hop.classList.add("dang-dong");   // mờ dần + sheet trượt xuống rồi mới ẩn (xem phu-xe-pro.css mục 12)
    const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    setTimeout(xongDong, reduce ? 0 : 200);
  }
  function xongDong() {
    hop.classList.remove("dang-dong");
    dangDong = false;
    hop.hidden = true;
    noiDung.innerHTML = "";
    if (khiDong) { khiDong(); khiDong = null; }
    window.dispatchEvent(new Event("phuxe:cai-dat-doi"));   // menu ☰ làm mới giá trị hiện bên phải (Giao diện, Âm báo)
    if (truocFocus && truocFocus.focus && document.body.contains(truocFocus)) truocFocus.focus();
  }
  const dauHop = (icon, tieuDe, phu) => `
    <div class="cd-dau">
      <span class="cd-dau__icon">${svg(icon)}</span>
      <div><h2 id="cd-tieu-de">${esc(tieuDe)}</h2>${phu ? `<p class="cd-dau__phu">${esc(phu)}</p>` : ""}</div>
    </div>`;
  const nutDong = '<button type="button" class="btn-confirm btn-confirm--outline btn-confirm--block cd-dong" data-cd-dong>Xong</button>';
  const ganDong = () => noiDung.querySelectorAll("[data-cd-dong]").forEach((n) => n.addEventListener("click", dong));

  // ================= 1. Giao diện =================
  const LUA_CHON_GD = [
    { k: "auto", ten: "Tự động", mo: "Theo cài đặt của điện thoại / máy tính", mau: "tudong" },
    { k: "sang", ten: "Sáng", mo: "Nền sáng, chữ đậm — dễ đọc ban ngày", mau: "sang" },
    { k: "toi", ten: "Tối", mo: "Nền tối, đỡ chói khi chạy ban đêm", mau: "toi" },
  ];
  function moGiaoDien() {
    const ve = () => {
      const hienTai = window.phuXeGiaoDien ? window.phuXeGiaoDien.lay() : "auto";
      noiDung.innerHTML = `
        ${dauHop('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>', "Giao diện", "Chọn màu nền của ứng dụng")}
        <div class="cd-chon" role="radiogroup" aria-label="Giao diện">
          ${LUA_CHON_GD.map((l) => `
            <button type="button" class="cd-the${l.k === hienTai ? " is-chon" : ""}" role="radio" aria-checked="${l.k === hienTai}" data-gd="${l.k}">
              <span class="cd-xem cd-xem--${l.mau}" aria-hidden="true"><i></i><i></i><i></i></span>
              <span class="cd-the__chu"><b>${l.ten}</b><small>${l.mo}</small></span>
              <span class="cd-the__tick" aria-hidden="true">✓</span>
            </button>`).join("")}
        </div>
        ${nutDong}`;
      noiDung.querySelectorAll("[data-gd]").forEach((n) => n.addEventListener("click", () => {
        window.phuXeGiaoDien && window.phuXeGiaoDien.dat(n.dataset.gd);
        ve();
      }));
      ganDong();
    };
    mo("");
    ve();
  }

  // ================= 2. Âm báo =================
  const KIEU_AM = [
    { k: "thanhCong", ten: "Thành công", mo: "Xác nhận lên/xuống xe, chất/dỡ hàng xong" },
    { k: "hoanTac", ten: "Hoàn tác", mo: "Khi hoàn tác một thao tác" },
    { k: "canhBao", ten: "Cảnh báo", mo: "Cần chú ý hoặc xác nhận lại" },
    { k: "loi", ten: "Lỗi / mất mạng", mo: "Thao tác không thực hiện được" },
    { k: "nhacNho", ten: "Nhắc việc", mo: "Bến mở, đến giờ chạy" },
  ];
  function moAmThanh() {
    const A = window.phuXe.amThanh;
    const ve = () => {
      const c = A.lay();
      noiDung.innerHTML = `
        ${dauHop('<path d="M11 5 6 9H2v6h4l5 4V5Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>', "Âm báo", "Phát tiếng khi có kết quả thao tác để khỏi phải nhìn màn hình")}
        <div class="cd-hang">
          <div class="cd-hang__chu"><b>Âm thanh</b><small>Phát tiếng khi thao tác thành công, lỗi, nhắc việc</small></div>
          <button type="button" class="cd-gat${c.bat ? " is-bat" : ""}" role="switch" aria-checked="${c.bat}" aria-label="Âm thanh" data-am="bat"><i></i></button>
        </div>
        <div class="cd-hang cd-hang--doc${c.bat ? "" : " is-tat"}">
          <div class="cd-hang__chu"><b>Âm lượng</b><small id="cd-luong-so">${c.luong}%</small></div>
          <input type="range" class="cd-truot" min="0" max="100" step="5" value="${c.luong}" aria-label="Âm lượng" data-am="luong" ${c.bat ? "" : "disabled"} />
        </div>
        <div class="cd-hang">
          <div class="cd-hang__chu"><b>Rung</b><small>Rung nhẹ khi xác nhận (chỉ điện thoại có hỗ trợ)</small></div>
          <button type="button" class="cd-gat${c.rung ? " is-bat" : ""}" role="switch" aria-checked="${c.rung}" aria-label="Rung" data-am="rung"><i></i></button>
        </div>
        <h3 class="cd-muc">Nghe thử</h3>
        <div class="cd-thu">
          ${KIEU_AM.map((m) => `
            <button type="button" class="cd-thu__nut" data-thu="${m.k}">
              <span class="cd-thu__play" aria-hidden="true">▶</span>
              <span class="cd-hang__chu"><b>${m.ten}</b><small>${m.mo}</small></span>
            </button>`).join("")}
        </div>
        ${c.bat ? "" : '<p class="cd-ghi-chu">Âm thanh đang tắt — nghe thử vẫn phát để bạn biết tiếng kêu thế nào.</p>'}
        ${nutDong}`;
      noiDung.querySelectorAll("[data-am]").forEach((n) => {
        if (n.type === "range") {
          n.addEventListener("input", () => {
            document.getElementById("cd-luong-so").textContent = `${n.value}%`;
            A.dat({ luong: Number(n.value) });
          });
          n.addEventListener("change", () => A.thu("thanhCong"));   // thả tay → nghe thử mức vừa chọn
        } else {
          n.addEventListener("click", () => {
            const khoa = n.dataset.am;
            const hienTai = A.lay()[khoa];
            A.dat({ [khoa]: !hienTai });
            ve();
            if (!hienTai) A.thu("thanhCong");
          });
        }
      });
      noiDung.querySelectorAll("[data-thu]").forEach((n) => n.addEventListener("click", () => {
        A.thu(n.dataset.thu);
        n.classList.add("dang-phat");
        setTimeout(() => n.classList.remove("dang-phat"), 600);
      }));
      ganDong();
    };
    mo("");
    ve();
  }

  // ================= 3. Hồ sơ (theo "Tài khoản của tôi" của Quản lý) =================
  const TRUONG = { ho_ten: { nhan: "Họ và tên", loai: "text", ac: "name" }, so_dien_thoai: { nhan: "Số điện thoại", loai: "tel", ac: "tel" } };
  let hoSo = null, dangSua = null, loiSua = "", baoOk = "", moDoiMk = false, henBao = null;

  function moHoSo() {
    dangSua = null; loiSua = ""; baoOk = ""; moDoiMk = false;
    mo(`${dauHop('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>', "Tài khoản của tôi")}<p class="cd-ghi-chu">Đang tải…</p>`);
    apiGet("/auth/toi")
      .then((d) => { hoSo = d; veHoSo(); })
      .catch((err) => {
        noiDung.innerHTML = `${dauHop("", "Tài khoản của tôi")}<p class="text-error" role="alert">${esc(err.message)}</p>${nutDong}`;
        ganDong();
      });
  }

  function hangSua(truong) {
    const t = TRUONG[truong];
    const gia = hoSo[truong] || "";
    return `
      <li class="hs-muc" data-truong="${truong}">
        <div class="hs-hang">
          <span class="hs-nhan">${t.nhan}</span>
          <span class="hs-phai">
            <span class="hs-gia-tri">${esc(gia) || "—"}</span>
            <button type="button" class="hs-but" data-hanh="sua" aria-label="Sửa ${t.nhan.toLowerCase()}">${svg(ICON_BUT)}</button>
          </span>
        </div>
        ${dangSua === truong ? `
          <div class="hs-sua cd-sua">
            <input class="input-field" type="${t.loai}" id="hs-o-${truong}" value="${esc(gia)}" maxlength="100" autocomplete="${t.ac}" ${t.loai === "tel" ? 'inputmode="tel"' : ""} placeholder="Nhập ${t.nhan.toLowerCase()} mới…" />
            ${loiSua ? `<div class="text-error" role="alert">${esc(loiSua)}</div>` : ""}
            <div class="hs-sua__nut">
              <button type="button" class="btn-confirm btn-confirm--outline" data-hanh="huy">Hủy</button>
              <button type="button" class="btn-primary" data-hanh="luu">Lưu</button>
            </div>
          </div>` : ""}
      </li>`;
  }
  const hangCoDinh = (nhan, giaTri, ghiChu) => `<li class="hs-muc"><div class="hs-hang"><span class="hs-nhan">${nhan}</span><span class="hs-phai"><span class="hs-gia-tri"${ghiChu ? ` title="${esc(ghiChu)}"` : ""}>${esc(giaTri) || "—"}</span></span></div></li>`;

  function veHoSo() {
    noiDung.innerHTML = `
      ${dauHop('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>', "Tài khoản của tôi")}
      <div class="hs-avatar" aria-hidden="true">${esc(chuDau(hoSo.ho_ten))}</div>
      ${baoOk ? `<div class="hs-bao-ok" role="status">${esc(baoOk)}</div>` : ""}
      <ul class="hs-ds">
        ${hangSua("ho_ten")}
        ${hangSua("so_dien_thoai")}
        ${hangCoDinh("Email", hoSo.email, "Email không thể thay đổi")}
        ${hangCoDinh("Vai trò", VAI_TRO[hoSo.vai_tro] || hoSo.vai_tro)}
        ${hangCoDinh("Ngày tham gia", hoSo.ngay_tao ? window.phuXe.ngay(hoSo.ngay_tao) : "")}
      </ul>
      <button type="button" class="hs-doi-mk-nut" id="hs-mo-mk" aria-expanded="${moDoiMk}">Đổi mật khẩu <span aria-hidden="true">${moDoiMk ? "▴" : "▾"}</span></button>
      <form class="hs-doi-mk" id="hs-form-mk" novalidate ${moDoiMk ? "" : "hidden"}>
        <label class="hs-nhan" for="hs-mk-cu">Mật khẩu hiện tại</label>
        <input class="input-field" type="password" id="hs-mk-cu" autocomplete="current-password" />
        <label class="hs-nhan" for="hs-mk-moi">Mật khẩu mới</label>
        <input class="input-field" type="password" id="hs-mk-moi" autocomplete="new-password" placeholder="Tối thiểu 6 ký tự" />
        <label class="hs-nhan" for="hs-mk-lai">Nhập lại mật khẩu mới</label>
        <input class="input-field" type="password" id="hs-mk-lai" autocomplete="new-password" />
        <div class="text-error" id="hs-loi-mk" role="alert" hidden></div>
        <button type="submit" class="btn-primary">Cập nhật mật khẩu</button>
      </form>
      ${nutDong}`;
    ganDong();
    noiDung.querySelectorAll("[data-hanh]").forEach((nut) => {
      const truong = nut.closest("[data-truong]").dataset.truong;
      nut.addEventListener("click", () => {
        if (nut.dataset.hanh === "sua") { dangSua = truong; loiSua = ""; baoOk = ""; veHoSo(); }
        else if (nut.dataset.hanh === "huy") { dangSua = null; loiSua = ""; veHoSo(); }
        else luuTruong(truong, nut);
      });
    });
    const o = noiDung.querySelector(".hs-sua input");
    if (o) {
      o.focus();
      o.setSelectionRange(o.value.length, o.value.length);
      o.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); luuTruong(o.closest("[data-truong]").dataset.truong); }
        else if (e.key === "Escape") { e.stopPropagation(); dangSua = null; loiSua = ""; veHoSo(); }
      });
    }
    noiDung.querySelector("#hs-mo-mk").addEventListener("click", () => { moDoiMk = !moDoiMk; veHoSo(); });
    noiDung.querySelector("#hs-form-mk").addEventListener("submit", doiMatKhau);
  }

  async function luuTruong(truong, nut) {
    let gia = noiDung.querySelector(`#hs-o-${truong}`).value.trim();
    if (gia === (hoSo[truong] || "")) { dangSua = null; return veHoSo(); }
    if (truong === "ho_ten" && !gia) { loiSua = "Họ và tên không được để trống."; return veHoSo(); }
    if (truong === "so_dien_thoai" && typeof kiemTraSoDienThoai === "function") {
      const kq = kiemTraSoDienThoai(gia);   // báo lỗi SĐT ngay, khỏi chờ server
      if (!kq.hopLe) { loiSua = kq.loi; return veHoSo(); }
      gia = kq.soChuan;
    }
    if (nut) { nut.disabled = true; nut.setAttribute("aria-busy", "true"); }
    try {
      await apiPut("/auth/toi", { [truong]: gia });
      hoSo = await apiGet("/auth/toi");   // lấy lại để hiện đúng giá trị đã chuẩn hóa (VD số điện thoại)
      if (truong === "ho_ten") {
        localStorage.setItem("ho_ten", hoSo.ho_ten);
        window.phuXeCapNhatTen && window.phuXeCapNhatTen(hoSo.ho_ten);
        const chao = document.getElementById("loi-chao");
        if (chao) chao.textContent = `Xin chào, ${hoSo.ho_ten}`;
      }
      dangSua = null; loiSua = "";
      baoOk = "Đã lưu thay đổi.";
      clearTimeout(henBao);
      henBao = setTimeout(() => { baoOk = ""; if (hop && !hop.hidden && !dangSua && hoSo) veHoSo(); }, 2500);
    } catch (err) {
      loiSua = err.message;
    }
    veHoSo();
  }

  async function doiMatKhau(e) {
    e.preventDefault();
    const loi = noiDung.querySelector("#hs-loi-mk");
    const bao = (nd) => { loi.textContent = nd; loi.hidden = !nd; };
    bao("");
    const cu = noiDung.querySelector("#hs-mk-cu").value;
    const moi = noiDung.querySelector("#hs-mk-moi").value;
    const lai = noiDung.querySelector("#hs-mk-lai").value;
    if (!cu || !moi) return bao("Vui lòng nhập đủ mật khẩu hiện tại và mật khẩu mới.");
    if (moi.length < 6) return bao("Mật khẩu mới cần tối thiểu 6 ký tự.");
    if (moi !== lai) return bao("Mật khẩu nhập lại chưa khớp.");
    const nut = e.submitter;
    if (nut) { nut.disabled = true; nut.setAttribute("aria-busy", "true"); }
    try {
      await apiPut("/auth/doi-mat-khau", { mat_khau_cu: cu, mat_khau_moi: moi });
      moDoiMk = false;
      baoOk = "Đổi mật khẩu thành công.";
      veHoSo();
    } catch (err) {
      bao(err.message);
      if (nut) { nut.disabled = false; nut.removeAttribute("aria-busy"); }
    }
  }

  window.phuXeCaiDat = { moGiaoDien, moAmThanh, moHoSo, dong };
})();
