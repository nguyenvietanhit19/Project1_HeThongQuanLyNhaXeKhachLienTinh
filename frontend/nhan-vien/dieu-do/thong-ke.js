/*
 * Trang "Tổng quan" của điều độ viên: số liệu tình trạng gán xe (tổng, theo tuyến, theo ngày), đội xe và chuyến 7 ngày qua.
 * Dữ liệu từ GET /dieu-do/thong-ke?so_ngay=N. Ba trạng thái gán xe dùng màu trạng thái cố định (xanh = đã gán, vàng = chưa gán,
 * đỏ = đang hoãn) và luôn đi kèm chữ + số, không dựa vào màu. Cần nạp SAU api-client.js, auth-check.js, nav.js, tai-khoan.js, menu.js.
 */

const MUI_GIO_TK = "Asia/Ho_Chi_Minh";
const TEN_THU_NGAN = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const TRANG_THAI = [
  { khoa: "da_gan", nhan: "Đã gán xe" },
  { khoa: "chua_gan", nhan: "Chưa gán xe" },
  { khoa: "dang_hoan", nhan: "Đang hoãn" },
];

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pad2 = (n) => String(n).padStart(2, "0");

const ttTrang = TrangThaiTrang.doc();
let soNgay = ["3", "5", "7"].includes(String(ttTrang.soNgay)) ? String(ttTrang.soNgay) : "3";
const oNoiDung = document.getElementById("tk-noi-dung");

// "2026-11-06" → { thu: "T6", ngayThang: "06/11" }
function nhanNgay(ngayIso) {
  const [y, m, d] = ngayIso.split("-").map(Number);
  return { thu: TEN_THU_NGAN[new Date(Date.UTC(y, m - 1, d)).getUTCDay()], ngayThang: `${pad2(d)}/${pad2(m)}` };
}

const homNayIso = () => {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: MUI_GIO_TK, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date()).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
};

// ---------- Thanh chồng 3 trạng thái (đo theo tổng của chính dòng; mỗi đoạn cách nhau 2px) ----------
function htmlThanh(nhom) {
  if (!nhom.so_chu_trinh) return '<div class="tk-thanh tk-thanh--rong" aria-hidden="true"></div>';
  const doan = TRANG_THAI.filter((t) => nhom[t.khoa] > 0)
    .map((t) => `<span class="tk-doan tk-doan--${t.khoa}" style="flex:${nhom[t.khoa]}" title="${t.nhan}: ${nhom[t.khoa]}"></span>`)
    .join("");
  return `<div class="tk-thanh" role="img" aria-label="${esc(motaNhom(nhom))}">${doan}</div>`;
}

function motaNhom(nhom) {
  return TRANG_THAI.map((t) => `${t.nhan.toLowerCase()} ${nhom[t.khoa]}`).join(", ");
}

function htmlChuThich() {
  return `<div class="tk-chu-thich">${TRANG_THAI.map((t) => `<span><i class="tk-doan tk-doan--${t.khoa}"></i>${t.nhan}</span>`).join("")}</div>`;
}

// ---------- Các khối ----------
function htmlTheSo(nhan, so, phu, lop = "", href = "/nhan-vien/dieu-do/gan-xe.html") {
  return `
    <a class="tk-the ${lop}" href="${href}">
      <span class="tk-the__nhan">${nhan}</span>
      <strong class="tk-the__so">${so}</strong>
      <small class="tk-the__phu">${phu}</small>
    </a>`;
}

function htmlTheSoLieu(d) {
  const t = d.tong;
  const phanTram = t.so_chu_trinh ? Math.round((t.da_gan / t.so_chu_trinh) * 100) : 0;
  return `
    <div class="tk-the-luoi">
      ${htmlTheSo("Chu trình", t.so_chu_trinh, `${t.so_chuyen} chuyến trong ${d.so_ngay} ngày tới`)}
      ${htmlTheSo("Đã gán xe", t.da_gan, t.so_chu_trinh ? `${phanTram}% số chu trình` : "—", "tk-the--da_gan")}
      ${htmlTheSo("Chưa gán xe", t.chua_gan, t.chua_gan ? "cần gán xe" : "đã xong", t.chua_gan ? "tk-the--chua_gan" : "")}
      ${htmlTheSo("Đang hoãn", t.dang_hoan, t.dang_hoan ? "quá giờ mà chưa có xe" : "không có", t.dang_hoan ? "tk-the--dang_hoan" : "")}
      ${htmlTheSo("Xe chạy thay", t.dang_chay_thay, t.dang_chay_thay ? "chu trình đang đổi xe" : "không có")}
      ${htmlTheSo("Việc cần chú ý", t.viec_can_chu_y, t.viec_khan ? `${t.viec_khan} chu trình khẩn` : "không có việc khẩn", t.viec_khan ? "tk-the--dang_hoan" : "")}
    </div>
    ${t.su_co_dang_xay_ra ? `<div class="tk-su-co"><strong>${t.su_co_dang_xay_ra} chuyến đang gặp sự cố</strong> dọc đường — xem ở mục Cần chú ý của trang Gán xe.</div>` : ""}`;
}

function htmlTheoTuyen(d) {
  if (!d.theo_tuyen.length) return '<div class="kv-trong">Chưa có tuyến nào trong phạm vi của bạn.</div>';
  return `
    ${htmlChuThich()}
    <table class="tk-bang">
      <thead><tr><th>Tuyến</th><th class="tk-bang__thanh">Tình trạng gán xe</th><th class="tk-so">Chu trình</th><th class="tk-so">Đã gán</th><th class="tk-so">Chưa gán</th><th class="tk-so">Hoãn</th></tr></thead>
      <tbody>
        ${d.theo_tuyen
          .map(
            (t) => `<tr>
              <td><strong>${esc(t.ten_tuyen)}</strong> ${htmlMa(esc(t.ma_tuyen))}</td>
              <td class="tk-bang__thanh">${htmlThanh(t)}</td>
              <td class="tk-so">${t.so_chu_trinh}</td>
              <td class="tk-so">${t.da_gan}</td>
              <td class="tk-so${t.chua_gan ? " tk-so--chua_gan" : ""}">${t.chua_gan}</td>
              <td class="tk-so${t.dang_hoan ? " tk-so--dang_hoan" : ""}">${t.dang_hoan}</td>
            </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
}

function htmlTheoNgay(d) {
  if (!d.theo_ngay.length) return '<div class="kv-trong">Không có chu trình nào khởi hành trong khoảng này.</div>';
  const homNay = homNayIso();
  return `
    ${htmlChuThich()}
    <div class="tk-ngay-ds">
      ${d.theo_ngay
        .map((n) => {
          const { thu, ngayThang } = nhanNgay(n.ngay);
          return `<div class="tk-ngay${n.ngay === homNay ? " tk-ngay--nay" : ""}">
            <span class="tk-ngay__nhan"><b>${thu}</b> ${ngayThang}${n.ngay === homNay ? "<em>hôm nay</em>" : ""}</span>
            ${htmlThanh(n)}
            <span class="tk-ngay__so">${n.da_gan}/${n.so_chu_trinh} đã gán${n.dang_hoan ? ` · <b class="tk-so--dang_hoan">${n.dang_hoan} hoãn</b>` : ""}</span>
          </div>`;
        })
        .join("")}
    </div>`;
}

function htmlDoiXe(d) {
  const x = d.doi_xe;
  const o = (nhan, so, phu, lop = "") => `<div class="tk-o ${lop}"><strong>${so}</strong><span>${nhan}</span>${phu ? `<small>${phu}</small>` : ""}</div>`;
  return `
    <div class="tk-o-luoi">
      ${o("Xe hoạt động", x.hoat_dong, `${x.du_phong} dự phòng · ${x.co_dinh_tuyen} cố định tuyến`)}
      ${o("Xe rảnh", x.ranh, `chưa có chuyến trong ${d.so_ngay} ngày tới`)}
      ${o("Đang bảo trì", x.bao_tri, x.bao_tri ? "không gán được" : "", x.bao_tri ? "tk-o--canh-bao" : "")}
      ${o("Đang chạy thay", x.dang_chay_thay, x.dang_chay_thay ? "xe chạy thay xe gốc" : "")}
    </div>
    <p class="tk-ghi-chu">Đội xe tính chung toàn hệ thống (xe dùng chung giữa các tuyến), không riêng tuyến bạn phụ trách.</p>`;
}

function htmlGanDay(d) {
  const g = d.chuyen_gan_day;
  const o = (nhan, so, lop = "") => `<div class="tk-o ${lop}"><strong>${so}</strong><span>${nhan}</span></div>`;
  return `
    <div class="tk-o-luoi">
      ${o("Đã hoàn thành", g.hoan_thanh)}
      ${o("Đang chạy", g.dang_chay)}
      ${o("Gặp sự cố", g.gap_su_co, g.gap_su_co ? "tk-o--canh-bao" : "")}
      ${o("Đã hủy", g.da_huy)}
    </div>
    <p class="tk-ghi-chu">Chuyến khởi hành trong ${g.so_ngay} ngày vừa qua thuộc các tuyến bạn phụ trách.</p>`;
}

function hienThi(d) {
  document.getElementById("stat-can-xu-ly").textContent = d.tong.chua_gan + d.tong.dang_hoan;
  oNoiDung.innerHTML = `
    ${htmlTheSoLieu(d)}
    <div class="tk-luoi-2">
      <section class="tk-khoi"><h2>Gán xe theo tuyến</h2>${htmlTheoTuyen(d)}</section>
      <section class="tk-khoi"><h2>Theo ngày khởi hành</h2>${htmlTheoNgay(d)}</section>
      <section class="tk-khoi"><h2>Đội xe</h2>${htmlDoiXe(d)}</section>
      <section class="tk-khoi"><h2>${d.chuyen_gan_day.so_ngay} ngày qua</h2>${htmlGanDay(d)}</section>
    </div>`;
}

// imLang = true: làm mới ngầm (định kỳ) — giữ nguyên màn hình cũ nếu lỗi
async function tai(imLang = false) {
  if (!imLang) oNoiDung.innerHTML = '<div class="kv-trong">Đang tải...</div>';
  try {
    hienThi(await apiGet(`/dieu-do/thong-ke?so_ngay=${soNgay}`));
  } catch (err) {
    if (!imLang) oNoiDung.innerHTML = `<div class="text-error">${esc(err.message)}</div>`;
  }
}

const nguoiDung = yeuCauVaiTro("dieu_do_vien", "quan_ly");
if (nguoiDung) {
  renderSidebar(document.getElementById("nv-sidebar"), "/nhan-vien/dieu-do/thong-ke.html", menuDieuDoCho(nguoiDung.vaiTro), "Điều độ");
  const selectCuaSo = document.getElementById("loc-cua-so");
  selectCuaSo.value = soNgay;
  selectCuaSo.addEventListener("change", () => {
    soNgay = selectCuaSo.value;
    TrangThaiTrang.luu({ soNgay });
    tai();
  });
  tai();
  setInterval(() => { if (!document.hidden) tai(true); }, 60000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) tai(true); });
}
