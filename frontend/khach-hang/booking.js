/*
 * Trang Booking — các vé của khách (xem vé đã đặt và lịch sử vé).
 * Dữ liệu từ GET /ve/lich-su: mỗi phần tử là 1 lượt đặt, đã được backend xếp nhóm (sap_di / da_di / da_huy) và gắn nhãn
 * trạng thái. Bấm vào thẻ vé để xem chi tiết; lượt còn nằm trong giỏ hàng có nút "Tiếp tục" quay về trang chủ để hoàn tất.
 * Dùng esc() từ khung-trang.js.
 */

const NHOM = [
  { ma: "sap_di", ten: "Sắp đi", trong: "Bạn chưa có vé nào sắp đi" },
  { ma: "da_di", ten: "Đã đi", trong: "Bạn chưa có chuyến nào đã đi" },
  { ma: "da_huy", ten: "Đã hủy", trong: "Không có vé nào đã hủy hoặc hết hạn" },
];

// nhãn của cả lượt đặt: [chữ hiển thị, tông màu]
const NHAN_LUOT = {
  dang_giu: ["Đang giữ chỗ", "cam"],
  cho_thanh_toan: ["Chờ thanh toán", "cam"],
  dat_thanh_cong_tai_quay: ["Trả tại quầy", "cam"],
  da_thanh_toan: ["Đã thanh toán", "xanh"],
  da_len_xe: ["Đang trên xe", "xanh"],
  da_di: ["Đã hoàn thành", "xanh"],
  khong_den: ["Không đến", "do"],
  da_huy: ["Đã hủy", "xam"],
  het_han: ["Hết hạn giữ chỗ", "xam"],
  chuyen_bi_huy: ["Chuyến bị hủy", "xam"],
};

function nhanVe(v) {
  if (v.trang_thai === "giu_cho") return v.loai_hinh_thanh_toan === "thanh_toan_tai_quay" ? "Trả tại quầy" : "Chờ thanh toán";
  return { da_thanh_toan: "Đã thanh toán", da_len_xe: "Đã lên xe", da_xuong_xe: "Đã xuống xe", khong_den: "Không đến", het_han: "Hết hạn", da_huy: "Đã hủy" }[v.trang_thai] || "";
}

const noiDung = document.getElementById("bk-noi-dung");
const modal = document.getElementById("bk-modal");
const chiTiet = document.getElementById("bk-chi-tiet");
const MUI_GIO = "Asia/Ho_Chi_Minh";
const tien = (so) => `${Number(so).toLocaleString("vi-VN")}đ`;
const gioVN = (iso) => new Intl.DateTimeFormat("vi-VN", { timeZone: MUI_GIO, hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(iso));
const ngayVN = (iso) => new Intl.DateTimeFormat("vi-VN", { timeZone: MUI_GIO, weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(iso));
const ngayNganVN = (iso) => new Intl.DateTimeFormat("vi-VN", { timeZone: MUI_GIO, weekday: "short", day: "2-digit", month: "2-digit" }).format(new Date(iso));
const ngayGioVN = (iso) => `${gioVN(iso)} ${new Intl.DateTimeFormat("vi-VN", { timeZone: MUI_GIO, day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(iso))}`;
const thoiLuong = (tu, den) => {
  const phut = Math.max(0, Math.round((new Date(den) - new Date(tu)) / 60000));
  return phut >= 60 ? `${Math.floor(phut / 60)}g${String(phut % 60).padStart(2, "0")}` : `${phut} phút`;
};

let danhSach = [];
let nhomDangXem = "sap_di";

const daDangNhap = () => !!localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang";

function veYeuCauDangNhap() {
  noiDung.innerHTML = `
    <div class="bk-trong">
      <h2>Đăng nhập để xem vé của bạn</h2>
      <a class="tc-btn tc-btn--chinh" href="/khach-hang/dang-nhap.html">Đăng nhập</a>
    </div>`;
}

function veLoi(thongDiep) {
  noiDung.innerHTML = `
    <div class="bk-trong bk-trong--loi">
      <h2>Chưa tải được vé của bạn</h2>
      <p>${esc(thongDiep)}</p>
      <button type="button" class="tc-btn tc-btn--chinh" id="bk-thu-lai">Thử lại</button>
    </div>`;
  document.getElementById("bk-thu-lai").addEventListener("click", tai);
}

// Sắp đi: giờ đón gần nhất trước; đã đi / đã hủy: mới nhất trước
function sapXepNhom(ma, ds) {
  const theoGio = (a, b) => new Date(a.chuyen.gio_don_du_kien) - new Date(b.chuyen.gio_don_du_kien);
  return [...ds].sort(ma === "sap_di" ? theoGio : (a, b) => theoGio(b, a));
}

// ---------- Thẻ vé trong danh sách ----------
function veThe(d) {
  const [chu, tong] = NHAN_LUOT[d.trang_thai] || [d.trang_thai, "xam"];
  const c = d.chuyen;
  return `
    <article class="bk-the bk-the--${tong}" role="button" tabindex="0" data-ma="${esc(d.ma_dat_cho)}" aria-label="Xem chi tiết vé ${esc(d.ma_dat_cho)}">
      <div class="bk-the__tren">
        <span class="bk-nhan bk-nhan--${tong}">${esc(chu)}</span>
        <span class="bk-the__ngay">${esc(ngayNganVN(c.gio_don_du_kien))}</span>
      </div>
      <div class="bk-hanh-trinh">
        <div class="bk-hanh-trinh__diem">
          <b>${gioVN(c.gio_don_du_kien)}</b>
          <span>${esc(c.ten_diem_don)}</span>
        </div>
        <div class="bk-hanh-trinh__giua">
          <small>${thoiLuong(c.gio_don_du_kien, c.gio_den_du_kien)}</small>
          <i></i>
        </div>
        <div class="bk-hanh-trinh__diem bk-hanh-trinh__diem--den">
          <b>${gioVN(c.gio_den_du_kien)}</b>
          <span>${esc(c.ten_diem_tra)}</span>
        </div>
      </div>
      <div class="bk-the__chan">
        <ul class="bk-chip-ghe">${d.ve.map((v) => `<li>${esc(v.so_ghe)}</li>`).join("")}</ul>
        <b class="bk-the__tong">${tien(d.tong_tien)}</b>
        ${
          d.co_the_tiep_tuc
            ? `<a class="tc-btn tc-btn--chinh bk-the__nut" href="/?tiep-tuc=${encodeURIComponent(d.ma_dat_cho)}" data-tiep>Tiếp tục</a>`
            : ""
        }
      </div>
    </article>`;
}

function veTrang() {
  const theoNhom = Object.fromEntries(NHOM.map((n) => [n.ma, danhSach.filter((d) => d.nhom === n.ma)]));
  const nhom = NHOM.find((n) => n.ma === nhomDangXem);
  const ds = sapXepNhom(nhomDangXem, theoNhom[nhomDangXem]);
  noiDung.innerHTML = `
    <h1 class="bk-tieu-de">Booking</h1>
    <div class="bk-tab" role="tablist">
      ${NHOM.map(
        (n) =>
          `<button type="button" role="tab" class="bk-tab__nut${n.ma === nhomDangXem ? " is-active" : ""}" aria-selected="${n.ma === nhomDangXem}" data-nhom="${n.ma}">${n.ten}<span>${theoNhom[n.ma].length}</span></button>`
      ).join("")}
    </div>
    ${
      ds.length
        ? `<div class="bk-ds">${ds.map(veThe).join("")}</div>`
        : `<div class="bk-trong"><h2>${nhom.trong}</h2>${nhomDangXem === "sap_di" ? '<a class="tc-btn tc-btn--chinh" href="/">Đặt vé ngay</a>' : ""}</div>`
    }`;
  noiDung.querySelectorAll("[data-nhom]").forEach((b) =>
    b.addEventListener("click", () => {
      nhomDangXem = b.dataset.nhom;
      veTrang();
    })
  );
  noiDung.querySelectorAll(".bk-the").forEach((the) => {
    const mo = () => moChiTiet(the.dataset.ma);
    the.addEventListener("click", (e) => {
      if (!e.target.closest("[data-tiep]")) mo(); // nút "Tiếp tục" là liên kết riêng
    });
    the.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === " ") && e.target === the) {
        e.preventDefault();
        mo();
      }
    });
  });
}

// ---------- Chi tiết 1 lượt đặt: thông tin lượt + từng vé như tờ vé cứng ----------
// Tông màu theo trạng thái từng vé
const TONG_VE = { da_thanh_toan: "xanh", da_len_xe: "xanh", da_xuong_xe: "xanh", giu_cho: "cam", khong_den: "do", het_han: "xam", da_huy: "xam" };

// Mã vạch trang trí dựng từ chính mã vé (không phải mã vạch quét được)
function maVach(ma) {
  const bit = "101" + [...ma].map((c) => c.charCodeAt(0).toString(2).padStart(8, "0")).join("01") + "101";
  const thanh = [...bit].map((b, k) => (b === "1" ? `<rect x="${k * 1.7}" y="0" width="1.4" height="40"/>` : "")).join("");
  return `<svg class="ve-cung__vach" viewBox="0 0 ${bit.length * 1.7} 40" preserveAspectRatio="none" aria-hidden="true">${thanh}</svg>`;
}

function dongTT(nhan, giaTri, lop = "") {
  return `<div class="ve-cung__o ${lop}"><dt>${nhan}</dt><dd>${giaTri}</dd></div>`;
}

function veVeCung(v, c) {
  const tong = TONG_VE[v.trang_thai] || "xam";
  const coNut = v.co_the_huy || v.co_the_thanh_toan;
  return `
    <article class="ve-cung ve-cung--${tong}${coNut ? " ve-cung--co-nut" : ""}" data-ve="${esc(v.id)}">
      <div class="ve-cung__the">
        <div class="ve-cung__chinh">
          <header class="ve-cung__dau">
            <span class="ve-cung__thuong-hieu"><img src="/shared/assets/logo-mark.png" alt="" />GoBus<small>Vé xe khách liên tỉnh</small></span>
            <span class="ve-cung__ma"><small>Mã vé</small><b>${esc(v.ma_ve)}</b></span>
          </header>
          <h4 class="ve-cung__tuyen">${esc(c.ten_tuyen)}</h4>
          <div class="ve-cung__diem">
            <div><small>Điểm đầu</small><b>${esc(v.ten_diem_don)}</b><span>${gioVN(v.gio_don_du_kien)} · ${esc(ngayVN(v.gio_don_du_kien))}</span></div>
            <i class="ve-cung__mui-ten" aria-hidden="true"></i>
            <div><small>Điểm cuối</small><b>${esc(v.ten_diem_tra)}</b><span>${gioVN(v.gio_den_du_kien)} · dự kiến</span></div>
          </div>
          <dl class="ve-cung__luoi">
            ${dongTT("Loại xe", esc(c.ten_loai_xe))}
            ${dongTT("Biển số", c.bien_so ? esc(c.bien_so) : "Chưa gán xe")}
            ${dongTT("Giá vé", tien(v.gia))}
            ${dongTT("Đã TT", tien(v.da_thanh_toan), v.da_thanh_toan ? "ve-cung__o--xanh" : "")}
            ${dongTT("Còn lại", tien(v.con_lai), v.con_lai ? "ve-cung__o--cam" : "")}
          </dl>
          <span class="ve-cung__dau-moc ve-cung__dau-moc--${tong}">${esc(nhanVe(v))}</span>
        </div>
        <div class="ve-cung__cuong">
          <div class="ve-cung__ghe"><small>Ghế</small><b>${esc(v.so_ghe)}</b></div>
          <div class="ve-cung__ma-vach">${maVach(v.ma_ve)}<span>${esc(v.ma_ve)}</span></div>
          ${
            coNut
              ? `<div class="ve-cung__nut">
                   ${v.co_the_huy ? `<button type="button" class="ve-cung__btn" data-huy="${esc(v.id)}">Hủy vé</button>` : ""}
                   ${v.co_the_thanh_toan ? `<button type="button" class="ve-cung__btn ve-cung__btn--chinh" data-tt="${esc(v.id)}">Thanh toán</button>` : ""}
                 </div>`
              : ""
          }
        </div>
      </div>
    </article>`;
}

function veChiTiet(d) {
  const [chu, tong] = NHAN_LUOT[d.trang_thai] || [d.trang_thai, "xam"];
  const han = d.han_thanh_toan || d.han_giu_cho_den;
  const coTaiQuay = d.ve.some((v) => v.trang_thai === "giu_cho" && v.loai_hinh_thanh_toan === "thanh_toan_tai_quay" && d.trang_thai !== "dang_giu");
  const nhacDenQuay = d.nhom === "sap_di" && (d.trang_thai === "da_thanh_toan" || d.trang_thai === "dat_thanh_cong_tai_quay" || coTaiQuay);

  chiTiet.innerHTML = `
    <div class="bk-ct__dau">
      <span class="bk-nhan bk-nhan--${tong}">${esc(chu)}</span>
      <h2 id="bk-ct-tieu-de">Mã đặt chỗ <span>${esc(d.ma_dat_cho)}</span></h2>
      <p>Đặt lúc ${esc(ngayGioVN(d.ngay_dat))}</p>
    </div>

    <dl class="bk-ct__tong-quan">
      <div><dt>Tổng số vé</dt><dd>${d.so_ve}</dd></div>
      <div><dt>Tổng thanh toán</dt><dd>${tien(d.tong_tien)}</dd></div>
      <div><dt>Đã thanh toán</dt><dd class="${d.da_thanh_toan ? "bk-xanh" : ""}">${tien(d.da_thanh_toan)}</dd></div>
      <div><dt>Còn lại</dt><dd class="${d.con_lai ? "bk-cam" : ""}">${tien(d.con_lai)}</dd></div>
    </dl>

    ${nhacDenQuay ? `<p class="bk-ct__nhac">Vui lòng ra văn phòng <b>${esc(d.chuyen.ten_diem_don)}</b> trước giờ khởi hành để nhận vé.</p>` : ""}
    ${d.co_the_tiep_tuc && han ? `<p class="bk-ct__nhac bk-ct__nhac--cam">Giữ chỗ đến <b>${gioVN(han)}</b></p>` : ""}
    ${d.co_the_tiep_tuc ? `<a class="tc-btn tc-btn--chinh bk-ct__tiep" href="/?tiep-tuc=${encodeURIComponent(d.ma_dat_cho)}">Tiếp tục hoàn tất</a>` : ""}

    <p class="bk-ct__loi" id="bk-ct-loi" role="alert" hidden></p>
    <div class="bk-ct__ve">${d.ve.map((v) => veVeCung(v, d.chuyen)).join("")}</div>`;

  chiTiet.querySelectorAll("[data-huy]").forEach((b) => b.addEventListener("click", () => hoiHuyVe(b.dataset.huy)));
  chiTiet.querySelectorAll("[data-tt]").forEach((b) => b.addEventListener("click", () => thanhToanVe(b)));
}

function baoLoiChiTiet(noiDung) {
  const o = document.getElementById("bk-ct-loi");
  if (!o) return;
  o.textContent = noiDung || "";
  o.hidden = !noiDung;
  if (noiDung) o.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// Hỏi lại trước khi hủy 1 vé
function hoiHuyVe(veId) {
  const luot = danhSach.find((x) => x.ma_dat_cho === maDangXem);
  const v = luot?.ve.find((x) => x.id === veId);
  if (!v) return;
  const lop = document.createElement("div");
  lop.className = "tc-xn";
  lop.setAttribute("role", "alertdialog");
  lop.innerHTML = `
    <div class="tc-xn__hop">
      <h3>Hủy vé ${esc(v.ma_ve)}?</h3>
      <p>Ghế ${esc(v.so_ghe)} sẽ được nhả cho người khác. Các vé khác trong lượt đặt này giữ nguyên.</p>
      <div class="tc-xn__nut">
        <button type="button" class="tc-btn tc-btn--phu" id="bk-huy-quay-lai">Quay lại</button>
        <button type="button" class="tc-btn tc-btn--chinh" id="bk-huy-dong-y">Đồng ý</button>
      </div>
    </div>`;
  modal.appendChild(lop);
  lop.querySelector("#bk-huy-quay-lai").addEventListener("click", () => lop.remove());
  lop.querySelector("#bk-huy-dong-y").addEventListener("click", async (e) => {
    e.target.disabled = true;
    try {
      await apiPost(`/ve/${encodeURIComponent(veId)}/huy`, {});
      lop.remove();
      await taiLaiGiuChiTiet();
    } catch (err) {
      lop.remove();
      baoLoiChiTiet(err.message);
    }
  });
  lop.querySelector("#bk-huy-quay-lai").focus();
}

// Trả online riêng 1 vé đã chốt "thanh toán tại quầy": sang cổng VNPay, xong quay về trang kết quả
async function thanhToanVe(nut) {
  baoLoiChiTiet("");
  nut.disabled = true;
  const chu = nut.textContent;
  nut.textContent = "Đang chuyển…";
  try {
    const r = await apiPost(`/ve/${encodeURIComponent(nut.dataset.tt)}/duong-dan-thanh-toan`, { frontend_origin: location.origin });
    location.href = r.duong_dan_thanh_toan;
  } catch (err) {
    nut.disabled = false;
    nut.textContent = chu;
    baoLoiChiTiet(err.message);
  }
}

let maDangXem = null;

function moChiTiet(ma) {
  const d = danhSach.find((x) => x.ma_dat_cho === ma);
  if (!d) return;
  maDangXem = ma;
  modal.querySelector(".tc-xn")?.remove();
  veChiTiet(d);
  modal.hidden = false;
  document.body.style.overflow = "hidden";
  document.getElementById("bk-dong").focus();
}

function dongChiTiet() {
  modal.querySelector(".tc-xn")?.remove();
  maDangXem = null;
  modal.hidden = true;
  document.body.style.overflow = "";
}

document.getElementById("bk-dong").addEventListener("click", dongChiTiet);
modal.addEventListener("click", (e) => {
  if (e.target === modal) dongChiTiet();
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape" || modal.hidden) return;
  const hoi = modal.querySelector(".tc-xn");
  if (hoi) hoi.remove();
  else dongChiTiet();
});

async function tai() {
  if (!daDangNhap()) return veYeuCauDangNhap();
  noiDung.innerHTML = '<div class="tc-khung-xuong" style="height:260px"></div>';
  try {
    danhSach = await apiGet("/ve/lich-su");
  } catch (err) {
    return veLoi(err.message);
  }
  // Mở ngay nhóm có vé: không có vé sắp đi mà có vé ở nhóm khác thì mở nhóm đầu tiên có vé
  if (!danhSach.some((d) => d.nhom === nhomDangXem)) nhomDangXem = NHOM.find((n) => danhSach.some((d) => d.nhom === n.ma))?.ma || "sap_di";
  veTrang();
  moTuDuongDan();
}

// Tới từ 1 thông báo (?ma=MÃ_ĐẶT_CHỖ): chọn đúng nhóm và mở chi tiết lượt đó, rồi bỏ tham số khỏi đường dẫn
function moTuDuongDan() {
  const ma = new URLSearchParams(location.search).get("ma");
  if (!ma) return;
  history.replaceState(null, "", location.pathname);
  const d = danhSach.find((x) => x.ma_dat_cho === ma);
  if (!d) return;
  nhomDangXem = d.nhom;
  veTrang();
  moChiTiet(ma);
}

// Sau khi hủy 1 vé: tải lại danh sách, giữ cửa sổ chi tiết nếu lượt đó còn (có thể đã chuyển nhóm), không thì đóng
async function taiLaiGiuChiTiet() {
  const ma = maDangXem;
  try {
    danhSach = await apiGet("/ve/lich-su");
  } catch (err) {
    return baoLoiChiTiet(err.message);
  }
  veTrang();
  if (ma && danhSach.some((x) => x.ma_dat_cho === ma)) moChiTiet(ma);
  else dongChiTiet();
}

tai();
