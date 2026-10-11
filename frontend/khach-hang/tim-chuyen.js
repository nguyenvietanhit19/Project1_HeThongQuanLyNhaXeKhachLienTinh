/*
 * Trang kết quả tìm chuyến (khach-hang/tim-chuyen.html) — UC-04 tra cứu chuyến công khai, NGHIEP_VU.md mục 3.4/8.1.
 * Đường dẫn mang đủ hành trình: ?di=KV001&den=KV005&ngay=2026-10-08 (chia sẻ/tải lại được). Trang có: ô tìm (sửa hành trình tại chỗ),
 * thanh chọn ngày, bộ lọc (giờ đi, loại xe, còn ghế), sắp xếp, thẻ chuyến; chọn chuyến → cửa sổ sơ đồ ghế + đặt vé (dat-ve.js).
 * Cần: api-client.js, khung-trang.js, tien-ich-ngay.js, o-tim-kiem.js, dat-ve.js nạp trước.
 */

const TRANG_KET_QUA = "/khach-hang/tim-chuyen.html";
const TEN_THU_NGAN = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const SO_NGAY_TREN_THANH = 7;

const SAP_XEP = [
  ["gio", "Giờ sớm nhất"],
  ["gia", "Giá thấp nhất"],
  ["ghe", "Nhiều ghế trống"],
];

// Khung giờ đón (giờ Việt Nam), nửa mở [tu, den)
const KHUNG_GIO = [
  { ma: "dem", ten: "Đêm", mo_ta: "00:00 – 05:59", tu: 0, den: 6 },
  { ma: "sang", ten: "Sáng", mo_ta: "06:00 – 11:59", tu: 6, den: 12 },
  { ma: "chieu", ten: "Chiều", mo_ta: "12:00 – 17:59", tu: 12, den: 18 },
  { ma: "toi", ten: "Tối", mo_ta: "18:00 – 23:59", tu: 18, den: 24 },
];

const vungKetQua = document.getElementById("tk-ket-qua");
const vungLoc = document.getElementById("tk-loc");
const formTim = document.getElementById("form-tim");
const nutTomTat = document.getElementById("tk-tom-tat");
const chuTomTat = document.getElementById("tk-tom-tat-chu");

let ketQua = [];
let lanTim = null; // { di, den, ngay } của lần tìm hiện tại — dat-ve.js dùng lại đúng cặp này
let sapXep = "gio";
let boLoc = { khungGio: new Set(), loaiXe: new Set(), conGhe: false };
let dangTai = false;
let loiTai = "";

const gioDon = (c) => Number(gioVN(c.gio_don_du_kien).slice(0, 2));
const khungCua = (c) => KHUNG_GIO.find((k) => gioDon(c) >= k.tu && gioDon(c) < k.den)?.ma;

// ---------- Ô tìm: đóng/mở trên điện thoại ----------
function datMoForm(mo) {
  formTim.classList.toggle("tk-tim--mo", mo);
  nutTomTat.setAttribute("aria-expanded", String(mo));
}
nutTomTat.addEventListener("click", () => datMoForm(!formTim.classList.contains("tk-tim--mo")));

function capNhatTomTat() {
  chuTomTat.textContent = lanTim ? `${lanTim.di.ten} → ${lanTim.den.ten} · ${nhanNgay(lanTim.ngay, true)}` : "Chọn hành trình";
}

// ---------- Tìm chuyến (trang chủ cũng gọi qua o-tim-kiem.js → xuLyTim → thucHienTim) ----------
function thucHienTim({ di, den, ngay }) {
  const doiTuyen = !lanTim || lanTim.di.id !== di.id || lanTim.den.id !== den.id;
  lanTim = { di, den, ngay };
  if (doiTuyen) {
    ketQua = []; // không để bộ lọc/số đếm của hành trình trước hiện lên trong lúc tải
    boLoc = { khungGio: new Set(), loaiXe: new Set(), conGhe: false };
  }
  history.replaceState(null, "", `${TRANG_KET_QUA}?di=${encodeURIComponent(di.ma)}&den=${encodeURIComponent(den.ma)}&ngay=${ngay}`);
  document.title = `${di.ten} → ${den.ten} — GoBus`;
  capNhatTomTat();
  datMoForm(false);
  return timChuyen();
}

async function timChuyen() {
  const { di, den, ngay } = lanTim;
  dangTai = true;
  loiTai = "";
  btnTim.disabled = true;
  veKetQua();
  try {
    ketQua = await apiGet(`/chuyen/tim-kiem?diem_di_id=${di.id}&diem_den_id=${den.id}&ngay=${ngay}`);
    // bỏ lựa chọn loại xe không còn trong kết quả mới
    const coLoaiXe = new Set(ketQua.map((c) => c.ten_loai_xe));
    boLoc.loaiXe = new Set([...boLoc.loaiXe].filter((x) => coLoaiXe.has(x)));
  } catch (err) {
    ketQua = [];
    loiTai = err.message;
  } finally {
    dangTai = false;
    btnTim.disabled = false;
  }
  veKetQua();
}

// ---------- Lọc + sắp xếp ----------
function locKetQua() {
  return ketQua.filter(
    (c) =>
      (!boLoc.khungGio.size || boLoc.khungGio.has(khungCua(c))) &&
      (!boLoc.loaiXe.size || boLoc.loaiXe.has(c.ten_loai_xe)) &&
      (!boLoc.conGhe || c.so_ghe_trong > 0)
  );
}

function sapXepDanhSach(ds) {
  const theoGio = (a, b) => a.gio_khoi_hanh.localeCompare(b.gio_khoi_hanh);
  const kq = [...ds];
  if (sapXep === "gia") kq.sort((a, b) => a.gia - b.gia || theoGio(a, b));
  else if (sapXep === "ghe") kq.sort((a, b) => b.so_ghe_trong - a.so_ghe_trong || theoGio(a, b));
  else kq.sort(theoGio);
  return kq;
}

const dangLoc = () => boLoc.khungGio.size > 0 || boLoc.loaiXe.size > 0 || boLoc.conGhe;

// ---------- Bộ lọc ----------
function veLoc() {
  if (!ketQua.length) {
    vungLoc.hidden = true;
    return;
  }
  vungLoc.hidden = false;
  const demKhung = (ma) => ketQua.filter((c) => khungCua(c) === ma).length;
  const cacLoaiXe = [...new Set(ketQua.map((c) => c.ten_loai_xe))].sort();
  const mucLoc = (loai, gia, ten, phu, so, dangChon) => `
    <label class="tk-loc__muc${dangChon ? " is-chon" : ""}${so === 0 ? " is-het" : ""}">
      <input type="checkbox" data-loc="${loai}" value="${esc(gia)}" ${dangChon ? "checked" : ""} ${so === 0 && !dangChon ? "disabled" : ""} />
      <span class="tk-loc__chu"><b>${esc(ten)}</b>${phu ? `<small>${esc(phu)}</small>` : ""}</span>
      <em>${so}</em>
    </label>`;
  vungLoc.innerHTML = `
    <div class="tk-loc__dau">
      <b>Bộ lọc</b>
      <button type="button" class="tk-loc__xoa" id="tk-xoa-loc" ${dangLoc() ? "" : "hidden"}>Xóa bộ lọc</button>
    </div>
    <div class="tk-loc__nhom">
      <h3>Giờ khởi hành</h3>
      ${KHUNG_GIO.map((k) => mucLoc("khung-gio", k.ma, k.ten, k.mo_ta, demKhung(k.ma), boLoc.khungGio.has(k.ma))).join("")}
    </div>
    ${
      cacLoaiXe.length > 1
        ? `<div class="tk-loc__nhom"><h3>Loại xe</h3>${cacLoaiXe
            .map((x) => mucLoc("loai-xe", x, x, "", ketQua.filter((c) => c.ten_loai_xe === x).length, boLoc.loaiXe.has(x)))
            .join("")}</div>`
        : ""
    }
    <div class="tk-loc__nhom">
      <label class="tk-gat${boLoc.conGhe ? " is-chon" : ""}">
        <input type="checkbox" data-loc="con-ghe" ${boLoc.conGhe ? "checked" : ""} />
        <span class="tk-gat__nut" aria-hidden="true"></span>
        <span class="tk-loc__chu"><b>Chỉ chuyến còn ghế</b></span>
      </label>
    </div>`;

  vungLoc.querySelectorAll("input[data-loc]").forEach((o) =>
    o.addEventListener("change", () => {
      const tap = o.dataset.loc === "khung-gio" ? boLoc.khungGio : o.dataset.loc === "loai-xe" ? boLoc.loaiXe : null;
      if (tap) (o.checked ? tap.add(o.value) : tap.delete(o.value));
      else boLoc.conGhe = o.checked;
      veKetQua();
    })
  );
  document.getElementById("tk-xoa-loc")?.addEventListener("click", () => {
    boLoc = { khungGio: new Set(), loaiXe: new Set(), conGhe: false };
    veKetQua();
  });
}

// ---------- Thanh chọn ngày ----------
function veThanhNgay() {
  const hom = homNayVN();
  let bat = congNgay(lanTim.ngay, -2);
  if (bat < hom) bat = hom;
  const ngay = Array.from({ length: SO_NGAY_TREN_THANH }, (_, i) => congNgay(bat, i));
  return `
    <div class="tk-ngay" role="tablist" aria-label="Chọn ngày đi">
      ${ngay
        .map((n) => {
          const [, m, d] = n.split("-");
          const thu = n === hom ? "Hôm nay" : TEN_THU_NGAN[new Date(`${n}T00:00:00Z`).getUTCDay()];
          return `<button type="button" role="tab" class="tk-ngay__nut${n === lanTim.ngay ? " is-active" : ""}" aria-selected="${n === lanTim.ngay}" data-ngay="${n}"><small>${thu}</small><b>${d}/${m}</b></button>`;
        })
        .join("")}
    </div>`;
}

// ---------- Thẻ chuyến ----------
function theChuyen(c) {
  const phut = Math.round((new Date(c.gio_den_du_kien) - new Date(c.gio_don_du_kien)) / 60000);
  const qua = Math.round((new Date(`${ngayVN(c.gio_den_du_kien)}T00:00:00Z`) - new Date(`${ngayVN(c.gio_don_du_kien)}T00:00:00Z`)) / 86400000);
  const het = c.so_ghe_trong === 0;
  const tiLe = c.tong_ghe ? Math.round((c.so_ghe_trong / c.tong_ghe) * 100) : 0;
  const mucGhe = het ? "het" : c.so_ghe_trong <= 5 || tiLe <= 20 ? "it" : "nhieu";
  // Còn ghế: cả thẻ là nút bấm (mở sơ đồ ghế); hết chỗ: thẻ mờ, không bấm được
  const thuocTinh = het
    ? 'aria-disabled="true"'
    : `role="button" tabindex="0" data-chuyen="${esc(c.id)}" aria-label="Chọn chuyến ${gioVN(c.gio_don_du_kien)} từ ${esc(c.ten_diem_don)}, giá ${tien(c.gia)}"`;
  return `
    <article class="tk-chuyen${het ? " tk-chuyen--het" : ""}" ${thuocTinh}>
      <div class="tk-chuyen__chinh">
        <div class="tk-chuyen__nhan">
          <span class="tk-nhan">${esc(c.ten_loai_xe)}</span>
          ${c.bien_so ? `<span class="tk-nhan tk-nhan--nhat">Xe ${esc(c.bien_so)}</span>` : ""}
          ${c.dang_hoan ? '<span class="tk-nhan tk-nhan--canh-bao">Đang hoãn — giờ có thể thay đổi</span>' : ""}
        </div>
        <div class="tk-hanh-trinh">
          <div class="tk-moc"><b>${gioVN(c.gio_don_du_kien)}</b><span title="${esc(c.ten_diem_don)}">${esc(c.ten_diem_don)}</span></div>
          <div class="tk-giua"><small>${thoiLuong(phut)}</small><i></i></div>
          <div class="tk-moc tk-moc--den"><b>${gioVN(c.gio_den_du_kien)}${qua > 0 ? `<sup>+${qua}</sup>` : ""}</b><span title="${esc(c.ten_diem_tra)}">${esc(c.ten_diem_tra)}</span></div>
        </div>
        <div class="tk-ghe tk-ghe--${mucGhe}">
          <div class="tk-ghe__thanh"><i style="width:${het ? 100 : Math.max(tiLe, 4)}%"></i></div>
          <span>${het ? "Hết chỗ" : `Còn <b>${c.so_ghe_trong}</b>/${c.tong_ghe} ghế`}</span>
        </div>
      </div>
      <div class="tk-chuyen__gia">
        <small>Giá vé</small>
        <b>${tien(c.gia)}</b>
        ${
          het
            ? '<span class="tk-chuyen__het">Hết chỗ</span>'
            : '<i class="tk-chuyen__mui" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg></i>'
        }
      </div>
    </article>`;
}

function veKhungTrong(bieuTuong, tieuDe, noiDung, nut = "") {
  return `<div class="tk-trong"><span class="tk-trong__bt">${bieuTuong}</span><h2>${tieuDe}</h2><p>${noiDung}</p>${nut}</div>`;
}
const BT_XE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="12" rx="3"/><path d="M3 11h18M7 17v2M17 17v2"/><circle cx="7.5" cy="14" r=".6"/><circle cx="16.5" cy="14" r=".6"/></svg>';
const BT_LOI = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4 3 19.5h18Z"/><path d="M12 10v4.5M12 17.2v.1"/></svg>';

// ---------- Vẽ phần kết quả ----------
function veKetQua() {
  if (!lanTim) {
    vungLoc.hidden = true;
    vungKetQua.innerHTML = veKhungTrong(BT_XE, "Chọn hành trình của bạn", "Nhập điểm đi, điểm đến và ngày rồi bấm “Tìm chuyến” để xem giờ chạy, giá vé và ghế còn trống.");
    return;
  }
  const { di, den, ngay } = lanTim;
  const danhSach = sapXepDanhSach(locKetQua());
  veLoc();

  let noiDung;
  if (dangTai) {
    noiDung = `<div class="tk-ds">${'<div class="tc-khung-xuong tk-xuong"></div>'.repeat(3)}</div>`;
  } else if (loiTai) {
    noiDung = veKhungTrong(BT_LOI, "Chưa tải được danh sách chuyến", esc(loiTai), '<button type="button" class="tk-nut-phu" id="tk-thu-lai">Thử lại</button>');
  } else if (!ketQua.length) {
    const ngaySau = congNgay(ngay, 1);
    noiDung = veKhungTrong(
      BT_XE,
      "Chưa có chuyến phù hợp",
      `Không có chuyến ${esc(di.ten)} → ${esc(den.ten)} vào ${nhanNgay(ngay)}.`,
      `<button type="button" class="tk-nut-phu" data-ngay="${ngaySau}">Xem ${nhanNgay(ngaySau, true)}</button>`
    );
  } else if (!danhSach.length) {
    noiDung = veKhungTrong(BT_XE, "Không có chuyến khớp bộ lọc", `Có ${ketQua.length} chuyến trong ngày nhưng không chuyến nào khớp bộ lọc hiện tại.`, '<button type="button" class="tk-nut-phu" id="tk-xoa-loc-2">Xóa bộ lọc</button>');
  } else {
    noiDung = `<div class="tk-ds">${danhSach.map(theChuyen).join("")}</div>`;
  }

  vungKetQua.innerHTML = `
    <div class="tk-ket-qua__dau">
      <div>
        <h1>${esc(di.ten)} <span aria-hidden="true">→</span> ${esc(den.ten)}</h1>
        <p>${[dangTai ? "Đang tìm chuyến…" : loiTai ? "" : `${dangLoc() ? `${danhSach.length}/${ketQua.length}` : ketQua.length} chuyến`, nhanNgay(ngay)].filter(Boolean).join(" · ")}</p>
      </div>
      ${
        ketQua.length && !dangTai && !loiTai
          ? `<div class="tk-sap-xep" role="group" aria-label="Sắp xếp">
        ${SAP_XEP.map(([gt, nhan]) => `<button type="button" class="tk-sap-xep__nut${sapXep === gt ? " is-active" : ""}" data-sap-xep="${gt}">${nhan}</button>`).join("")}
      </div>`
          : ""
      }
    </div>
    ${veThanhNgay()}
    ${noiDung}`;

  vungKetQua.querySelectorAll("[data-sap-xep]").forEach((b) =>
    b.addEventListener("click", () => {
      sapXep = b.dataset.sapXep;
      veKetQua();
    })
  );
  vungKetQua.querySelectorAll("[data-ngay]").forEach((b) =>
    b.addEventListener("click", () => {
      datNgay(b.dataset.ngay);
      thucHienTim({ di, den, ngay: b.dataset.ngay });
    })
  );
  vungKetQua.querySelectorAll(".tk-chuyen[data-chuyen]").forEach((the) => {
    the.addEventListener("click", () => moSoDo(the.dataset.chuyen));
    the.addEventListener("keydown", (e) => {
      if ((e.key === "Enter" || e.key === " ") && e.target === the) {
        e.preventDefault();
        moSoDo(the.dataset.chuyen);
      }
    });
  });
  document.getElementById("tk-thu-lai")?.addEventListener("click", timChuyen);
  document.getElementById("tk-xoa-loc-2")?.addEventListener("click", () => {
    boLoc = { khungGio: new Set(), loaiXe: new Set(), conGhe: false };
    veKetQua();
  });
}

// ---------- Khởi tạo ----------
async function khoiTao() {
  oNgay.min = homNayVN();
  const q = new URLSearchParams(location.search);
  datNgay(homNayVN());
  veKetQua();
  if (!(await taiKhuVuc())) return datMoForm(true);

  const di = dsKhuVuc.find((k) => k.ma === q.get("di") && k.co_van_phong);
  const den = dsKhuVuc.find((k) => k.ma === q.get("den"));
  if (!di || !den || di.id === den.id) return datMoForm(true); // đường dẫn thiếu/sai hành trình: để khách chọn lại

  const ngay = q.get("ngay") && q.get("ngay") >= homNayVN() ? q.get("ngay") : homNayVN();
  coDi.dat(di);
  coDen.dat(den);
  datNgay(ngay);
  await thucHienTim({ di, den, ngay });
}

khoiTao();
