/*
 * Trang chủ khách hàng (frontend/index.html) — UC-04 tra cứu chuyến công khai, NGHIEP_VU.md mục 3.4/8.1.
 * Không cần đăng nhập. Chỉ XEM: danh sách chuyến + sơ đồ ghế (chưa chọn/đặt ghế — UC-05).
 * Cần /shared/api-client.js và khach-hang/khung-trang.js (thanh trên, footer, esc/boDau/pad2) nạp trước.
 */

const MUI_GIO = "Asia/Ho_Chi_Minh";
const TEN_THU = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];

// ---------- Ngày giờ theo múi giờ Việt Nam ----------
const homNayVN = () => new Intl.DateTimeFormat("en-CA", { timeZone: MUI_GIO }).format(new Date()); // "YYYY-MM-DD"
const ngayVN = (iso) => new Intl.DateTimeFormat("en-CA", { timeZone: MUI_GIO }).format(new Date(iso));
const gioVN = (iso) => new Intl.DateTimeFormat("vi-VN", { timeZone: MUI_GIO, hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(iso));

function congNgay(ngayIso, n) {
  const d = new Date(`${ngayIso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function nhanNgay(ngayIso, ngan = false) {
  const d = new Date(`${ngayIso}T00:00:00Z`);
  const [y, m, ngay] = ngayIso.split("-");
  return ngan ? `${TEN_THU[d.getUTCDay()]} ${ngay}/${m}` : `${TEN_THU[d.getUTCDay()]}, ${ngay}/${m}/${y}`;
}

function thoiLuong(phut) {
  const h = Math.floor(phut / 60);
  const m = phut % 60;
  return m ? `${h}g${pad2(m)}` : `${h} giờ`;
}

const tien = (so) => `${Number(so).toLocaleString("vi-VN")}đ`;

// ---------- Ô chọn 2 bước: tỉnh/thành trước, rồi điểm trong tỉnh (gõ chữ thì tìm thẳng, không dấu) ----------
function taoCombo(goc, { loaiTru = () => null } = {}) {
  const o = goc.querySelector("input");
  const ul = goc.querySelector(".tc-combo__ds");
  let items = [];
  let chon = null;
  let viTri = -1;
  let hienThi = []; // các dòng đang hiện: { loai: "tinh" | "quay_lai" | "khu_vuc", ... }
  let buoc = "tinh"; // tinh | diem | tim
  let tinhHienTai = null;
  let khiDoi = () => {};

  const mo = () => {
    ul.hidden = false;
    o.setAttribute("aria-expanded", "true");
  };
  const dong = () => {
    ul.hidden = true;
    o.setAttribute("aria-expanded", "false");
  };

  const khaDung = () => {
    const tru = loaiTru();
    return items.filter((k) => !tru || k.id !== tru.id);
  };

  function ve(tuKhoa = "") {
    const tk = boDau(tuKhoa.trim());
    const kha = khaDung();
    if (tk) {
      buoc = "tim";
      hienThi = kha.filter((k) => boDau(`${k.ten} ${k.tinh_thanh}`).includes(tk)).map((k) => ({ loai: "khu_vuc", k }));
    } else if (buoc === "diem" && tinhHienTai && kha.some((k) => k.tinh_thanh === tinhHienTai)) {
      hienThi = [
        { loai: "quay_lai", tinh: tinhHienTai },
        ...kha.filter((k) => k.tinh_thanh === tinhHienTai).map((k) => ({ loai: "khu_vuc", k })),
      ];
    } else {
      buoc = "tinh";
      const dem = new Map();
      kha.forEach((k) => dem.set(k.tinh_thanh, (dem.get(k.tinh_thanh) || 0) + 1));
      hienThi = [...dem.entries()].sort((a, b) => a[0].localeCompare(b[0], "vi")).map(([tinh, so]) => ({ loai: "tinh", tinh, so }));
    }
    viTri = -1;
    ul.innerHTML = hienThi.length
      ? hienThi
          .map((d, i) => {
            if (d.loai === "tinh")
              return `<li class="tc-combo__muc tc-combo__muc--tinh" role="option" data-i="${i}"><span class="tc-combo__ten">${esc(d.tinh)}</span><span class="tc-combo__tinh">${d.so} điểm ›</span></li>`;
            if (d.loai === "quay_lai")
              return `<li class="tc-combo__muc tc-combo__muc--quay-lai" role="option" data-i="${i}"><span class="tc-combo__ten">‹ ${esc(d.tinh)}</span><span class="tc-combo__tinh">Chọn tỉnh khác</span></li>`;
            return `<li class="tc-combo__muc" role="option" data-i="${i}"><span class="tc-combo__ten">${esc(d.k.ten)}</span>${
              buoc === "tim" && d.k.tinh_thanh !== d.k.ten ? `<span class="tc-combo__tinh">${esc(d.k.tinh_thanh)}</span>` : ""
            }</li>`;
          })
          .join("")
      : '<li class="tc-combo__trong">Không có điểm nào khớp</li>';
  }

  function datChon(k, thongBao = true) {
    chon = k;
    o.value = k ? k.ten : "";
    dong();
    if (thongBao) khiDoi(k);
  }

  // Bấm 1 dòng trong danh sách: tỉnh -> xem các điểm của tỉnh; quay lại -> về danh sách tỉnh; điểm -> chọn
  function chonDong(d) {
    if (!d) return;
    if (d.loai === "khu_vuc") return datChon(d.k);
    if (d.loai === "quay_lai") {
      buoc = "tinh";
      return ve("");
    }
    const cuaTinh = khaDung().filter((k) => k.tinh_thanh === d.tinh);
    if (cuaTinh.length === 1) return datChon(cuaTinh[0]); // tỉnh chỉ có 1 điểm: chọn luôn, đỡ 1 lần bấm
    tinhHienTai = d.tinh;
    buoc = "diem";
    ve("");
  }

  function tomLaiChon(dichChuyen) {
    const muc = ul.querySelectorAll(".tc-combo__muc");
    muc.forEach((m, i) => m.classList.toggle("is-chon", i === viTri));
    if (dichChuyen && muc[viTri]) muc[viTri].scrollIntoView({ block: "nearest" });
  }

  function moTheoHienTai() {
    // Đã có điểm được chọn thì mở thẳng danh sách điểm của tỉnh đó (tiện đổi sang điểm khác cùng tỉnh)
    if (chon) {
      tinhHienTai = chon.tinh_thanh;
      buoc = "diem";
    } else {
      buoc = "tinh";
    }
    ve("");
    mo();
  }

  o.addEventListener("focus", () => {
    o.select();
    moTheoHienTai();
  });
  o.addEventListener("click", () => {
    if (ul.hidden) moTheoHienTai();
  });
  o.addEventListener("input", () => {
    chon = null;
    ve(o.value);
    mo();
  });
  o.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (ul.hidden) moTheoHienTai();
      viTri = (viTri + (e.key === "ArrowDown" ? 1 : -1) + hienThi.length) % Math.max(hienThi.length, 1);
      tomLaiChon(true);
    } else if (e.key === "Enter" && !ul.hidden && hienThi.length) {
      e.preventDefault();
      chonDong(hienThi[viTri >= 0 ? viTri : 0]);
    } else if (e.key === "Escape") {
      dong();
    }
  });
  o.addEventListener("blur", () => {
    setTimeout(() => {
      if (!ul.hidden && document.activeElement === o) return;
      dong();
      if (chon) return;
      // Gõ dở: nếu chỉ còn đúng 1 điểm khớp thì tự chọn, ngược lại xóa chữ gõ dở
      if (o.value.trim() && buoc === "tim" && hienThi.length === 1) datChon(hienThi[0].k);
      else {
        o.value = "";
        khiDoi(null);
      }
    }, 120);
  });
  ul.addEventListener("mousedown", (e) => {
    const muc = e.target.closest(".tc-combo__muc");
    if (!muc) return;
    e.preventDefault(); // giữ ô nhập đang focus để danh sách không tắt khi sang bước 2
    chonDong(hienThi[Number(muc.dataset.i)]);
  });

  return {
    lay: () => chon,
    dat: (k) => datChon(k, false),
    datDanhSach(ds) {
      items = ds;
      if (chon && !ds.some((k) => k.id === chon.id)) datChon(null, false);
    },
    khiDoi(fn) {
      khiDoi = fn;
    },
    dongBang: o,
  };
}

// ---------- Trạng thái trang ----------
const oNgay = document.getElementById("o-ngay");
const vungKetQua = document.getElementById("tc-ket-qua");
const oLoiTim = document.getElementById("tc-loi-tim");
const btnTim = document.getElementById("btn-tim");
const chipNgay = document.getElementById("tc-chip-ngay");

let dsKhuVuc = [];
let ketQua = [];
let sapXep = "gio"; // gio | gia | ghe
let lanTim = null; // { di, den, ngay } của lần tìm gần nhất — sơ đồ ghế dùng lại đúng cặp này

const coDi = taoCombo(document.getElementById("combo-di"), { loaiTru: () => coDen.lay() });
const coDen = taoCombo(document.getElementById("combo-den"), { loaiTru: () => coDi.lay() });

function baoLoiTim(noiDung) {
  oLoiTim.textContent = noiDung || "";
  oLoiTim.hidden = !noiDung;
}

// ---------- Chip chọn nhanh ngày ----------
function veChipNgay() {
  const hom = homNayVN();
  const nhanh = [
    { ngay: hom, nhan: "Hôm nay" },
    { ngay: congNgay(hom, 1), nhan: "Ngày mai" },
    { ngay: congNgay(hom, 2), nhan: nhanNgay(congNgay(hom, 2), true) },
    { ngay: congNgay(hom, 3), nhan: nhanNgay(congNgay(hom, 3), true) },
  ];
  chipNgay.innerHTML = nhanh
    .map((c) => `<button type="button" class="tc-chip${oNgay.value === c.ngay ? " is-active" : ""}" data-ngay="${c.ngay}">${c.nhan}</button>`)
    .join("");
  chipNgay.querySelectorAll("[data-ngay]").forEach((b) =>
    b.addEventListener("click", () => {
      oNgay.value = b.dataset.ngay;
      veChipNgay();
      if (coDi.lay() && coDen.lay()) timChuyen();
    })
  );
}
oNgay.addEventListener("change", veChipNgay);

// ---------- Đổi chiều đi/đến ----------
document.getElementById("btn-doi-cho").addEventListener("click", () => {
  const a = coDi.lay();
  const b = coDen.lay();
  baoLoiTim("");
  if (b && !b.co_van_phong) {
    baoLoiTim(`${b.ten} chưa có văn phòng nên không thể làm điểm đi.`);
    return;
  }
  coDi.dat(b);
  coDen.dat(a);
});

// ---------- Tìm chuyến ----------
document.getElementById("form-tim").addEventListener("submit", (e) => {
  e.preventDefault();
  timChuyen();
});

function veXuong() {
  vungKetQua.innerHTML = `<div class="tc-danh-sach">${'<div class="tc-khung-xuong"></div>'.repeat(3)}</div>`;
}

function veTrangThaiTrong(tieuDe, noiDung, { loi = false, nut = "" } = {}) {
  vungKetQua.innerHTML = `<div class="tc-trong${loi ? " tc-trong--loi" : ""}"><strong>${tieuDe}</strong>${noiDung}${nut}</div>`;
}

async function timChuyen() {
  baoLoiTim("");
  const di = coDi.lay();
  const den = coDen.lay();
  const ngay = oNgay.value;
  if (!di || !den) return baoLoiTim("Vui lòng chọn điểm đi và điểm đến từ danh sách gợi ý.");
  if (di.id === den.id) return baoLoiTim("Điểm đi và điểm đến phải khác nhau.");
  if (!ngay) return baoLoiTim("Vui lòng chọn ngày đi.");
  if (ngay < homNayVN()) return baoLoiTim("Không thể tìm chuyến ở ngày đã qua.");

  btnTim.disabled = true;
  veXuong();
  try {
    ketQua = await apiGet(`/chuyen/tim-kiem?diem_di_id=${di.id}&diem_den_id=${den.id}&ngay=${ngay}`);
    lanTim = { di, den, ngay };
    history.replaceState(null, "", `?di=${encodeURIComponent(di.ma)}&den=${encodeURIComponent(den.ma)}&ngay=${ngay}`);
    sapXep = "gio";
    veKetQua();
  } catch (err) {
    veTrangThaiTrong("Chưa tải được danh sách chuyến", esc(err.message), { loi: true });
  } finally {
    btnTim.disabled = false;
  }
}

// ---------- Danh sách chuyến ----------
const SAP_XEP = [
  ["gio", "Giờ sớm nhất"],
  ["gia", "Giá thấp nhất"],
  ["ghe", "Nhiều ghế trống"],
];

function sapXepKetQua() {
  const ds = [...ketQua];
  if (sapXep === "gia") ds.sort((a, b) => a.gia - b.gia || a.gio_khoi_hanh.localeCompare(b.gio_khoi_hanh));
  else if (sapXep === "ghe") ds.sort((a, b) => b.so_ghe_trong - a.so_ghe_trong || a.gio_khoi_hanh.localeCompare(b.gio_khoi_hanh));
  else ds.sort((a, b) => a.gio_khoi_hanh.localeCompare(b.gio_khoi_hanh));
  return ds;
}

function theChuyen(c) {
  const phut = Math.round((new Date(c.gio_den_du_kien) - new Date(c.gio_don_du_kien)) / 60000);
  const qua = Math.round((new Date(`${ngayVN(c.gio_den_du_kien)}T00:00:00Z`) - new Date(`${ngayVN(c.gio_don_du_kien)}T00:00:00Z`)) / 86400000);
  const het = c.so_ghe_trong === 0;
  const theGhe = het
    ? '<span class="tc-the tc-the--het">Hết chỗ</span>'
    : `<span class="tc-the ${c.so_ghe_trong <= 5 ? "tc-the--ghe-it" : "tc-the--ghe-nhieu"}">Còn ${c.so_ghe_trong} ghế</span>`;
  return `
    <article class="tc-chuyen${het ? " tc-chuyen--het" : ""}">
      <div class="tc-gio">
        <div class="tc-gio__moc"><b>${gioVN(c.gio_don_du_kien)}</b><small title="${esc(c.ten_diem_don)}">${esc(c.ten_diem_don)}</small></div>
        <div class="tc-gio__giua"><span>${thoiLuong(phut)}</span><i class="tc-gio__duong"></i></div>
        <div class="tc-gio__moc"><b>${gioVN(c.gio_den_du_kien)}${qua > 0 ? `<sup>+${qua}</sup>` : ""}</b><small title="${esc(c.ten_diem_tra)}">${esc(c.ten_diem_tra)}</small></div>
      </div>
      <div class="tc-chuyen__phai">
        <div class="tc-gia"><small>Giá vé</small><b>${tien(c.gia)}</b></div>
        <button type="button" class="tc-nut-xem" data-chuyen="${c.id}">Xem sơ đồ ghế</button>
      </div>
      <div class="tc-chuyen__nhan">
        <span class="tc-the">${esc(c.ten_loai_xe)}</span>
        ${theGhe}
        ${c.bien_so ? `<span class="tc-the">Xe ${esc(c.bien_so)}</span>` : ""}
        ${c.dang_hoan ? '<span class="tc-the tc-the--hoan">Đang hoãn — giờ có thể thay đổi</span>' : ""}
      </div>
    </article>`;
}

function veKetQua() {
  const { di, den, ngay } = lanTim;
  if (!ketQua.length) {
    const ngaySau = congNgay(ngay, 1);
    veTrangThaiTrong(
      "Chưa có chuyến phù hợp",
      `Không có chuyến ${esc(di.ten)} → ${esc(den.ten)} vào ${nhanNgay(ngay)}.`,
      { nut: `<div><button type="button" class="tc-chip" id="btn-ngay-sau">Xem ${nhanNgay(ngaySau, true)}</button></div>` }
    );
    document.getElementById("btn-ngay-sau").addEventListener("click", () => {
      oNgay.value = ngaySau;
      veChipNgay();
      timChuyen();
    });
    return;
  }

  vungKetQua.innerHTML = `
    <div class="tc-kq__dau">
      <h2 class="tc-kq__tieu-de">${esc(di.ten)} → ${esc(den.ten)}<span>${ketQua.length} chuyến · ${nhanNgay(ngay)}</span></h2>
      <div class="tc-kq__sap-xep">
        ${SAP_XEP.map(([gt, nhan]) => `<button type="button" class="tc-chip${sapXep === gt ? " is-active" : ""}" data-sap-xep="${gt}">${nhan}</button>`).join("")}
      </div>
    </div>
    <div class="tc-danh-sach">${sapXepKetQua().map(theChuyen).join("")}</div>`;

  vungKetQua.querySelectorAll("[data-sap-xep]").forEach((b) =>
    b.addEventListener("click", () => {
      sapXep = b.dataset.sapXep;
      veKetQua();
    })
  );
  vungKetQua.querySelectorAll("[data-chuyen]").forEach((b) => b.addEventListener("click", () => moSoDo(b.dataset.chuyen)));
}

// ---------- Sơ đồ ghế + đặt vé của 1 chuyến (UC-04, UC-05) ----------
// Cùng 1 cửa sổ đi qua các bước: ① chọn ghế → ② chọn điểm đón/trả → ③ thanh toán → xong.
// Ghế CHỈ bị khóa khi khách bấm "Tiếp tục" ở bước ② (ai nhanh hơn thì giữ được, 10 phút). Từ đó lượt đặt nằm trong
// giỏ hàng: thoát ra giữa chừng vẫn quay lại hoàn tất được, ghế tiếp tục đếm ngược hạn giữ.
const modalSoDo = document.getElementById("modal-so-do");
const noiDungSoDo = document.getElementById("tc-so-do-noi-dung");
const KHOA_DAT_DANG_CHO = "tc-cho-dat"; // việc đang dở khi khách bị chuyển sang trang đăng nhập

let chuyenXem = null; // chi tiết chuyến đang xem (kết quả /so-do-ghe); null khi mở lại lượt đặt từ giỏ hàng
let gheDangChon = new Set(); // ghế đang chọn ở bước ① (chưa khóa gì)
let diemDonChon = null;
let diemTraChon = null;
let datCho = null; // lượt đặt chỗ đã khóa ghế
let dongHoDemNguoc = null;
let gheThanhToan = new Set(); // ghế đang được tích để thanh toán (bước ③)
const DA_DANG_NHAP_KHACH = () => !!localStorage.getItem("token") && localStorage.getItem("vai_tro") === "khach_hang";
const SO_GHE_TOI_DA = 10;
const veConGiu = () => datCho.ve.filter((v) => v.trang_thai === "giu_cho");

function dungDemNguoc() {
  clearInterval(dongHoDemNguoc);
  dongHoDemNguoc = null;
}

// Đóng cửa sổ. Đang giữ ghế mà chưa xong thì hỏi lại; thoát thật thì ghế VẪN được giữ (nằm trong giỏ hàng).
function dongSoDo() {
  if (modalSoDo.querySelector(".tc-xn")) return;
  if (datCho && ["dang_giu", "cho_thanh_toan"].includes(datCho.trang_thai)) return hienXacNhanThoat();
  dongHan();
}

function xoaHopXacNhanThoat() {
  modalSoDo.querySelector(".tc-xn")?.remove();
}

function dongHan() {
  xoaHopXacNhanThoat(); // không để sót hộp hỏi: lần mở sau sẽ hiện sẵn
  dungDemNguoc();
  datCho = null;
  chuyenXem = null;
  gheDangChon = new Set();
  modalSoDo.hidden = true;
  document.body.style.overflow = "";
  if (typeof capNhatGioHang === "function") capNhatGioHang();
}

function hienXacNhanThoat() {
  const lop = document.createElement("div");
  lop.className = "tc-xn";
  lop.setAttribute("role", "alertdialog");
  lop.innerHTML = `
    <div class="tc-xn__hop">
      <h3>Bạn có muốn thoát?</h3>
      <p>Nếu muốn tiếp tục hoàn thành vé, hãy kiểm tra giỏ hàng.</p>
      <div class="tc-xn__nut">
        <button type="button" class="tc-btn tc-btn--phu" id="btn-xn-thoat">Đồng ý</button>
        <button type="button" class="tc-btn tc-btn--chinh" id="btn-xn-quay-lai">Hủy</button>
      </div>
    </div>`;
  modalSoDo.appendChild(lop);
  lop.querySelector("#btn-xn-quay-lai").addEventListener("click", () => lop.remove());
  lop.querySelector("#btn-xn-thoat").addEventListener("click", dongHan);
  lop.querySelector("#btn-xn-quay-lai").focus();
}

document.getElementById("btn-dong-so-do").addEventListener("click", dongSoDo);
modalSoDo.addEventListener("click", (e) => {
  if (e.target === modalSoDo) dongSoDo();
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape" || modalSoDo.hidden) return;
  const xn = modalSoDo.querySelector(".tc-xn");
  if (xn) xn.remove();
  else dongSoDo();
});

async function moSoDo(chuyenId, gheChonSan = []) {
  xoaHopXacNhanThoat();
  modalSoDo.hidden = false;
  document.body.style.overflow = "hidden";
  dungDemNguoc();
  datCho = null;
  noiDungSoDo.innerHTML = '<div class="tc-khung-xuong" style="height:260px"></div>';
  try {
    const ct = await apiGet(`/chuyen/${chuyenId}/so-do-ghe?diem_di_id=${lanTim.di.id}&diem_den_id=${lanTim.den.id}`);
    chuyenXem = ct;
    const trong = new Set(ct.so_do_ghe.filter((g) => g.trang_thai === "trong").map((g) => g.ma_ghe));
    gheDangChon = new Set(gheChonSan.filter((g) => trong.has(g)));
    veSoDo();
  } catch (err) {
    noiDungSoDo.innerHTML = `<div class="tc-trong tc-trong--loi"><strong>Chưa tải được sơ đồ ghế</strong>${esc(err.message)}</div>`;
  }
}

// Mở lại 1 lượt đặt đã giữ ghế (từ giỏ hàng) — vào thẳng bước thanh toán hoặc bước chờ thanh toán
async function moTiepDatCho(maDatCho) {
  xoaHopXacNhanThoat();
  modalSoDo.hidden = false;
  document.body.style.overflow = "hidden";
  dungDemNguoc();
  noiDungSoDo.innerHTML = '<div class="tc-khung-xuong" style="height:260px"></div>';
  try {
    datCho = await apiGet(`/ve/dat-cho/${encodeURIComponent(maDatCho)}`);
  } catch (err) {
    datCho = null;
    noiDungSoDo.innerHTML = `<div class="tc-trong tc-trong--loi"><strong>Không mở được lượt đặt</strong>${esc(err.message)}</div>`;
    return;
  }
  chuyenXem = null;
  if (datCho.trang_thai === "dang_giu") {
    gheThanhToan = new Set(veConGiu().map((v) => v.so_ghe));
    veBuocThanhToan();
  } else if (datCho.trang_thai === "cho_thanh_toan") {
    veChoThanhToan();
  } else {
    const t = datCho;
    datCho = null;
    noiDungSoDo.innerHTML = `<div class="tc-trong tc-trong--loi"><strong>Lượt đặt này không còn giữ ghế</strong>${t.trang_thai === "het_han" ? "Đã hết hạn giữ chỗ." : "Đã được xử lý."}</div>`;
    if (typeof capNhatGioHang === "function") capNhatGioHang();
  }
}

function veTang(ghe, tang, tl, soTang) {
  const cacGhe = ghe.filter((g) => g.tang === tang);
  const rong = tl.rong;
  const cao = tl.cao;
  const hopWidth = document.querySelector(".tc-modal__hop").clientWidth;
  const tiLe = Math.min(1, (hopWidth - 90 - (soTang - 1) * 22) / soTang / rong);
  const o = cacGhe
    .map((g) => {
      const trong = g.trang_thai === "trong";
      const chon = gheDangChon.has(g.ma_ghe);
      const lop = !trong ? "tc-ghe--co-nguoi" : chon ? "tc-ghe--trong tc-ghe--chon" : "tc-ghe--trong";
      const nhan = !trong ? "đã có người" : chon ? "đang chọn" : "trống";
      return `<span class="tc-ghe ${lop}" ${trong ? `data-ghe="${esc(g.ma_ghe)}" role="button" tabindex="0" aria-pressed="${chon}"` : ""} style="left:${g.x - tl.minX + 16}px; top:${g.y - tl.minY + 32}px" title="${esc(g.ma_ghe)} — ${nhan}">${esc(g.ma_ghe)}</span>`;
    })
    .join("");
  return `
    <div class="tc-tang">
      ${soTang > 1 ? `<div class="tc-tang__ten">Tầng ${tang}</div>` : ""}
      <div style="width:${rong * tiLe}px; height:${cao * tiLe}px; margin:0 auto">
        <div class="tc-tang__xe" style="width:${rong}px; height:${cao}px; transform:scale(${tiLe}); transform-origin:top left">
          <span class="tc-tang__dau-xe">▲ Đầu xe</span>${o}
        </div>
      </div>
    </div>`;
}

const dauChuyen = (ct) => {
  const phut = Math.round((new Date(ct.gio_den_du_kien) - new Date(ct.gio_don_du_kien)) / 60000);
  return `
    <div class="tc-so-do__dau">
      <h2 id="tc-so-do-tieu-de">${esc(ct.ten_diem_don)} → ${esc(ct.ten_diem_tra)}</h2>
      <p>${nhanNgay(ngayVN(ct.gio_don_du_kien))} · ${gioVN(ct.gio_don_du_kien)} → ${gioVN(ct.gio_den_du_kien)} (${thoiLuong(phut)})</p>
    </div>`;
};

// Đầu trang của lượt đặt đã khóa ghế (điểm đón/trả đã chọn thật)
const dauDatCho = (d) => `
  <div class="tc-so-do__dau">
    <h2 id="tc-so-do-tieu-de">${esc(d.chuyen.ten_diem_don)} → ${esc(d.chuyen.ten_diem_tra)}</h2>
    <p>${nhanNgay(ngayVN(d.chuyen.gio_don_du_kien))} · ${gioVN(d.chuyen.gio_don_du_kien)} → ${gioVN(d.chuyen.gio_den_du_kien)} · ${esc(d.chuyen.ten_loai_xe)}</p>
  </div>`;

const buocDat = (dang) => {
  const ten = ["Chọn ghế", "Điểm đón, điểm trả", "Thanh toán"];
  return `<ol class="tc-buoc">${ten.map((t, i) => `<li class="${i + 1 === dang ? "is-active" : i + 1 < dang ? "is-xong" : ""}"><b>${i + 1}</b>${t}</li>`).join("")}</ol>`;
};

// ----- Bước 1: chọn ghế (chưa khóa gì) -----
function veSoDo(loi = "") {
  const ct = chuyenXem;
  const ghe = ct.so_do_ghe;
  const minX = Math.min(...ghe.map((g) => g.x));
  const minY = Math.min(...ghe.map((g) => g.y));
  const tl = {
    minX,
    minY,
    rong: Math.max(...ghe.map((g) => g.x)) - minX + 40 + 32,
    cao: Math.max(...ghe.map((g) => g.y)) - minY + 30 + 32 + 16,
  };
  const dsDiem = (ds) =>
    ds.length
      ? ds.map((d) => `<li><span>${esc(d.ten)}</span><b>${gioVN(d.gio_du_kien)}</b></li>`).join("")
      : '<li><span>—</span></li>';

  noiDungSoDo.innerHTML = `
    ${dauChuyen(ct)}
    <div class="tc-so-do__thong-tin tc-so-do__thong-tin--giua">
      <span class="tc-the">${esc(ct.ten_loai_xe)}</span>
      <span class="tc-the">${tien(ct.gia)}/ghế</span>
      <span class="tc-the ${ct.so_ghe_trong === 0 ? "tc-the--het" : ct.so_ghe_trong <= 5 ? "tc-the--ghe-it" : "tc-the--ghe-nhieu"}">${ct.so_ghe_trong === 0 ? "Hết chỗ" : `Còn ${ct.so_ghe_trong}/${ct.tong_ghe} ghế`}</span>
      ${ct.bien_so ? `<span class="tc-the">Xe ${esc(ct.bien_so)}</span>` : ""}
      ${ct.dang_hoan ? '<span class="tc-the tc-the--hoan">Đang hoãn — giờ có thể thay đổi</span>' : ""}
    </div>
    ${buocDat(1)}
    <div class="tc-so-do__chu-thich">
      <span><i class="tc-mau-ghe tc-ghe--trong"></i>Ghế trống</span>
      <span><i class="tc-mau-ghe tc-ghe--trong tc-ghe--chon"></i>Đang chọn</span>
      <span><i class="tc-mau-ghe tc-ghe--co-nguoi"></i>Đã có người</span>
    </div>
    <div class="tc-so-do__khu" id="tc-khu-ghe">
      ${Array.from({ length: ct.so_tang }, (_, i) => veTang(ghe, i + 1, tl, ct.so_tang)).join("")}
    </div>
    <div class="tc-dat-loi" id="tc-dat-loi" role="alert" ${loi ? "" : "hidden"}>${esc(loi)}</div>
    <div class="tc-dat-thanh">
      <div class="tc-dat-thanh__tt" id="tc-dat-tt"></div>
      <button type="button" class="tc-btn tc-btn--chinh" id="btn-sang-diem">Cập nhật điểm đón trả</button>
    </div>
    <div class="tc-so-do__diem">
      <div><h3>Điểm đón</h3><ul>${dsDiem(ct.diem_don_co_the_chon)}</ul></div>
      <div><h3>Điểm trả</h3><ul>${dsDiem(ct.diem_tra_co_the_chon)}</ul></div>
    </div>`;
  capNhatThanhChon();
  document.getElementById("btn-sang-diem").addEventListener("click", () => veBuocDiemDonTra());
}

function capNhatThanhChon() {
  const ct = chuyenXem;
  const n = gheDangChon.size;
  document.getElementById("tc-dat-tt").innerHTML = n
    ? `<b>${n} ghế:</b> ${[...gheDangChon].map(esc).join(", ")} <span class="tc-dat-thanh__tong">${tien(n * ct.gia)}</span>`
    : "Chọn ghế trên sơ đồ để đặt vé";
  document.getElementById("btn-sang-diem").disabled = n === 0;
  document.querySelectorAll("#tc-khu-ghe [data-ghe]").forEach((el) => {
    const chon = gheDangChon.has(el.dataset.ghe);
    el.classList.toggle("tc-ghe--chon", chon);
    el.setAttribute("aria-pressed", chon);
  });
}

function doiChonGhe(el) {
  const ma = el.dataset.ghe;
  const loi = document.getElementById("tc-dat-loi");
  loi.hidden = true;
  if (gheDangChon.has(ma)) gheDangChon.delete(ma);
  else if (gheDangChon.size >= SO_GHE_TOI_DA) {
    loi.textContent = `Mỗi lần chỉ đặt tối đa ${SO_GHE_TOI_DA} ghế`;
    loi.hidden = false;
    return;
  } else gheDangChon.add(ma);
  capNhatThanhChon();
}
noiDungSoDo.addEventListener("click", (e) => {
  const el = e.target.closest("#tc-khu-ghe [data-ghe]");
  if (el) doiChonGhe(el);
});
noiDungSoDo.addEventListener("keydown", (e) => {
  const el = e.target.closest("#tc-khu-ghe [data-ghe]");
  if (el && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault();
    doiChonGhe(el);
  }
});

// ----- Bước 2: chọn điểm đón + điểm trả (vẫn chưa khóa gì; "Tiếp tục" mới khóa ghế) -----
function veBuocDiemDonTra(loi = "") {
  const ct = chuyenXem;
  const macDinhDon = ct.diem_don_co_the_chon.findIndex((d) => d.diem_id === diemDonChon);
  const macDinhTra = ct.diem_tra_co_the_chon.findIndex((d) => d.diem_id === diemTraChon);
  const danhSach = (ds, ten, macDinh) =>
    ds
      .map(
        (d, i) => `
        <label class="tc-chon-diem__muc">
          <input type="radio" name="${ten}" value="${esc(d.diem_id)}" ${i === macDinh ? "checked" : ""} />
          <span class="tc-chon-diem__ten">${esc(d.ten)}${d.loai === "diem_dung" ? ' <em>điểm dừng</em>' : ""}</span>
          <b>${gioVN(d.gio_du_kien)}</b>
        </label>`
      )
      .join("");

  noiDungSoDo.innerHTML = `
    ${dauChuyen(ct)}
    ${buocDat(2)}
    <div class="tc-chon-diem">
      <div><h3>Điểm đón</h3>${danhSach(ct.diem_don_co_the_chon, "diem-don", macDinhDon >= 0 ? macDinhDon : 0)}</div>
      <div><h3>Điểm trả</h3>${danhSach(ct.diem_tra_co_the_chon, "diem-tra", macDinhTra >= 0 ? macDinhTra : ct.diem_tra_co_the_chon.length - 1)}</div>
    </div>
    <div class="tc-dat-loi" id="tc-dat-loi" role="alert" ${loi ? "" : "hidden"}>${esc(loi)}</div>
    <div class="tc-dat-thanh">
      <button type="button" class="tc-btn tc-btn--phu" id="btn-quay-lai">Quay lại</button>
      <button type="button" class="tc-btn tc-btn--chinh" id="btn-tiep-tuc">Tiếp tục</button>
    </div>`;
  document.getElementById("btn-quay-lai").addEventListener("click", () => {
    diemDonChon = document.querySelector('input[name="diem-don"]:checked')?.value ?? diemDonChon;
    diemTraChon = document.querySelector('input[name="diem-tra"]:checked')?.value ?? diemTraChon;
    veSoDo();
  });
  document.getElementById("btn-tiep-tuc").addEventListener("click", tiepTuc);
}

// "Tiếp tục": mốc khóa ghế. Ai bấm trước giữ được ghế (10 phút); người sau nhận lỗi và quay về chọn lại.
async function tiepTuc() {
  diemDonChon = document.querySelector('input[name="diem-don"]:checked').value;
  diemTraChon = document.querySelector('input[name="diem-tra"]:checked').value;
  if (!DA_DANG_NHAP_KHACH()) {
    // Chưa đăng nhập: nhớ việc đang dở, đăng nhập xong quay về đúng chuyến + ghế + điểm đón/trả này
    sessionStorage.setItem(
      KHOA_DAT_DANG_CHO,
      JSON.stringify({ chuyenId: chuyenXem.id, ghe: [...gheDangChon], diemDon: diemDonChon, diemTra: diemTraChon })
    );
    location.href = `/khach-hang/dang-nhap.html?next=${encodeURIComponent(location.pathname + location.search)}`;
    return;
  }
  const nut = document.getElementById("btn-tiep-tuc");
  nut.disabled = true;
  nut.textContent = "Đang giữ ghế…";
  try {
    datCho = await apiPost("/ve/giu-cho", {
      chuyen_id: chuyenXem.id,
      diem_di_id: lanTim.di.id,
      diem_den_id: lanTim.den.id,
      diem_don_id: diemDonChon,
      diem_tra_id: diemTraChon,
      danh_sach_ghe: [...gheDangChon],
    });
    gheThanhToan = new Set(veConGiu().map((v) => v.so_ghe)); // mặc định tích hết
    if (typeof capNhatGioHang === "function") capNhatGioHang();
    veBuocThanhToan();
  } catch (err) {
    // Hay gặp nhất: ghế vừa bị người khác giữ trước → tải lại sơ đồ để thấy ghế nào còn trống
    const gheCu = [...gheDangChon];
    await moSoDo(chuyenXem.id, gheCu);
    if (chuyenXem) veSoDo(err.message);
  }
}

// ----- Đếm ngược -----
function batDemNguoc(denLuc, khiHet) {
  dungDemNguoc();
  const hien = () => {
    const el = document.getElementById("tc-dem-nguoc");
    const con = Math.max(0, Math.floor((new Date(denLuc) - Date.now()) / 1000));
    if (el) el.textContent = `${pad2(Math.floor(con / 60))}:${pad2(con % 60)}`;
    if (con === 0) {
      dungDemNguoc();
      khiHet();
    }
  };
  hien();
  dongHoDemNguoc = setInterval(hien, 1000);
}

// Hết thời gian giữ ghế: ghế đã được nhả, về lại chọn ghế (hoặc đóng nếu đang mở từ giỏ hàng)
function hetGioGiuGhe() {
  const id = chuyenXem && chuyenXem.id;
  datCho = null;
  if (typeof capNhatGioHang === "function") capNhatGioHang();
  if (id && typeof lanTim !== "undefined" && lanTim) {
    moSoDo(id).then(() => chuyenXem && veSoDo("Đã hết thời gian giữ ghế — vui lòng chọn ghế lại"));
  } else {
    noiDungSoDo.innerHTML = `<div class="tc-trong tc-trong--loi"><strong>Đã hết thời gian giữ ghế</strong>Ghế đã được nhả, bạn có thể đặt lại.</div>`;
  }
}

const dongDemNguoc = (nhan = "Ghế được giữ cho bạn trong") =>
  `<div class="tc-dem"><span>${nhan}</span><b id="tc-dem-nguoc">--:--</b></div>`;

async function huyGiuChoVaQuayLai() {
  const ma = datCho.ma_dat_cho;
  dungDemNguoc();
  datCho = null;
  try {
    await apiPost(`/ve/dat-cho/${ma}/huy`, {});
  } catch {
    /* hết hạn/đã nhả thì thôi */
  }
  if (typeof capNhatGioHang === "function") capNhatGioHang();
  if (chuyenXem && typeof lanTim !== "undefined" && lanTim) moSoDo(chuyenXem.id);
  else dongHan();
}

// ----- Bước 3: thanh toán — chọn ghế nào thanh toán (tích), bỏ hẳn ghế (✕), chọn loại hình, bấm "Thanh toán" -----
function veBuocThanhToan(loi = "") {
  const d = datCho;
  const ve = veConGiu();
  gheThanhToan = new Set([...gheThanhToan].filter((g) => ve.some((v) => v.so_ghe === g)));
  noiDungSoDo.innerHTML = `
    ${dauDatCho(d)}
    ${buocDat(3)}
    ${dongDemNguoc()}
    <div class="tc-tt-ds">
      <div class="tc-tt-ds__dau">
        <label class="tc-tt-chon-het"><input type="checkbox" id="chon-tat-ca" /> Chọn tất cả</label>
        <span id="tc-tt-dem-ghe"></span>
      </div>
      ${ve
        .map(
          (v) => `
        <div class="tc-tt-ghe">
          <label class="tc-tt-ghe__chon">
            <input type="checkbox" data-ghe-tt="${esc(v.so_ghe)}" />
            <span class="tc-tt-ghe__ma">Ghế ${esc(v.so_ghe)}</span>
            <b>${tien(v.gia)}</b>
          </label>
          <button type="button" class="tc-tt-bo" data-bo-ghe="${esc(v.so_ghe)}" aria-label="Bỏ ghế ${esc(v.so_ghe)}" title="Bỏ ghế này">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>
          </button>
        </div>`
        )
        .join("")}
    </div>
    <div class="tc-tt-tom-tat" id="tc-tt-tom-tat"></div>
    <div class="tc-dat-loi" id="tc-dat-loi" role="alert" ${loi ? "" : "hidden"}>${esc(loi)}</div>
    <div class="tc-tt-hang">
      <label class="tc-tt-hang__nhan" for="loai-hinh">Loại hình thanh toán</label>
      <select id="loai-hinh" class="tc-tt-chon">
        <option value="thanh_toan_tai_quay">Thanh toán tại quầy</option>
        <option value="vnpay_qr">VNPay – VNPay QR</option>
      </select>
    </div>
    <div class="tc-dat-thanh">
      <button type="button" class="tc-btn tc-btn--phu" id="btn-quay-lai">Hủy giữ chỗ</button>
      <button type="button" class="tc-btn tc-btn--chinh" id="btn-thanh-toan">Thanh toán</button>
    </div>`;
  batDemNguoc(d.han_giu_cho_den, hetGioGiuGhe);
  capNhatThanhToan();

  document.getElementById("btn-quay-lai").addEventListener("click", huyGiuChoVaQuayLai);
  document.getElementById("chon-tat-ca").addEventListener("change", (e) => {
    gheThanhToan = e.target.checked ? new Set(veConGiu().map((v) => v.so_ghe)) : new Set();
    capNhatThanhToan();
  });
  noiDungSoDo.querySelectorAll("[data-ghe-tt]").forEach((o) =>
    o.addEventListener("change", () => {
      o.checked ? gheThanhToan.add(o.dataset.gheTt) : gheThanhToan.delete(o.dataset.gheTt);
      capNhatThanhToan();
    })
  );
  noiDungSoDo.querySelectorAll("[data-bo-ghe]").forEach((n) => n.addEventListener("click", () => boGhe(n.dataset.boGhe)));
  document.getElementById("btn-thanh-toan").addEventListener("click", thanhToan);
}

// Tính lại tổng tiền, diện đặt cọc, loại hình được phép — theo đúng các ghế đang tích
function capNhatThanhToan() {
  const d = datCho;
  const ve = veConGiu();
  const chon = ve.filter((v) => gheThanhToan.has(v.so_ghe));
  const tong = chon.reduce((t, v) => t + v.gia, 0);
  const soCoc = chon.length >= 2 && tong > d.nguong_dat_coc ? Math.floor(chon.length * d.ty_le_dat_coc) : 0;
  const khongTraSau = !d.duoc_chon_thanh_toan_tai_quay;
  const khongChon = ve.length - chon.length;

  noiDungSoDo.querySelectorAll("[data-ghe-tt]").forEach((o) => (o.checked = gheThanhToan.has(o.dataset.gheTt)));
  document.getElementById("chon-tat-ca").checked = ve.length > 0 && chon.length === ve.length;
  document.getElementById("tc-tt-dem-ghe").textContent = `${chon.length}/${ve.length} ghế`;

  const dong = [`<div class="tc-tt-tom-tat__tong"><span>Tổng thanh toán</span><b>${tien(tong)}</b></div>`];
  if (soCoc) dong.push(`<p>Cần đặt cọc: thanh toán VNPay cho <b>${soCoc}</b> vé, <b>${chon.length - soCoc}</b> vé còn lại thanh toán tại quầy.</p>`);
  if (khongTraSau) dong.push("<p>Tài khoản của bạn chỉ được thanh toán ngay do đã vi phạm không đến nhiều lần.</p>");
  if (khongChon) dong.push(`<p class="tc-tt-tom-tat__nha">${khongChon} ghế không được tích sẽ được nhả, không đặt.</p>`);
  document.getElementById("tc-tt-tom-tat").innerHTML = dong.join("");

  // Diện đặt cọc hoặc bị hạn chế: không được chọn "tại quầy" cho cả đơn — VNPay là lối duy nhất
  const chonLoai = document.getElementById("loai-hinh");
  const batBuocVnpay = soCoc > 0 || khongTraSau;
  chonLoai.querySelector('[value="thanh_toan_tai_quay"]').disabled = batBuocVnpay;
  if (batBuocVnpay) chonLoai.value = "vnpay_qr";
  document.getElementById("btn-thanh-toan").disabled = chon.length === 0;
}

async function boGhe(soGhe) {
  try {
    datCho = await apiPost(`/ve/dat-cho/${datCho.ma_dat_cho}/bo-ghe`, { so_ghe: soGhe });
  } catch (err) {
    const el = document.getElementById("tc-dat-loi");
    el.textContent = err.message;
    el.hidden = false;
    return;
  }
  gheThanhToan.delete(soGhe);
  if (typeof capNhatGioHang === "function") capNhatGioHang();
  if (datCho.trang_thai === "da_huy" || !veConGiu().length) {
    // bỏ hết ghế thì quay lại chọn ghế từ đầu
    dungDemNguoc();
    datCho = null;
    if (chuyenXem && typeof lanTim !== "undefined" && lanTim) moSoDo(chuyenXem.id);
    else dongHan();
    return;
  }
  veBuocThanhToan();
}

async function thanhToan() {
  const nut = document.getElementById("btn-thanh-toan");
  nut.disabled = true;
  try {
    datCho = await apiPost(`/ve/dat-cho/${datCho.ma_dat_cho}/thanh-toan`, {
      danh_sach_ghe: [...gheThanhToan],
      loai_hinh: document.getElementById("loai-hinh").value,
    });
  } catch (err) {
    nut.disabled = false;
    const el = document.getElementById("tc-dat-loi");
    el.textContent = err.message;
    el.hidden = false;
    return;
  }
  if (typeof capNhatGioHang === "function") capNhatGioHang();
  if (datCho.trang_thai === "cho_thanh_toan") veChoThanhToan();
  else veThanhCong();
}

// ----- Đặt vé thành công, chờ khách trả VNPay trong 5 phút (không trả/thoát: ghế mở lại; có thể quay lại từ giỏ hàng) -----
function veChoThanhToan(loi = "") {
  const d = datCho;
  const ve = veConGiu();
  const online = ve.filter((v) => v.loai_hinh_thanh_toan === "thanh_toan_ngay");
  const taiQuay = ve.filter((v) => v.loai_hinh_thanh_toan === "thanh_toan_tai_quay");
  const tongOnline = online.reduce((t, v) => t + v.gia, 0);
  const tongQuay = taiQuay.reduce((t, v) => t + v.gia, 0);
  noiDungSoDo.innerHTML = `
    <div class="tc-xong">
      <div class="tc-xong__dau">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>
      </div>
      <h2 id="tc-so-do-tieu-de">Đặt vé thành công</h2>
      <p>Vui lòng thanh toán VNPay trong 5 phút để hoàn tất. Mã đặt chỗ <b class="tc-xong__ma">${esc(d.ma_dat_cho)}</b></p>
    </div>
    ${dongDemNguoc("Hạn thanh toán còn")}
    <div class="tc-tom-tat">
      <div><span>Chuyến</span><b>${esc(d.chuyen.ten_diem_don)} → ${esc(d.chuyen.ten_diem_tra)}</b></div>
      <div><span>Giờ đón</span><b>${nhanNgay(ngayVN(d.chuyen.gio_don_du_kien))} · ${gioVN(d.chuyen.gio_don_du_kien)}</b></div>
      <div><span>Ghế thanh toán VNPay</span><b>${online.map((v) => esc(v.so_ghe)).join(", ")}</b></div>
      ${taiQuay.length ? `<div><span>Ghế thanh toán tại quầy</span><b>${taiQuay.map((v) => esc(v.so_ghe)).join(", ")} (${tien(tongQuay)})</b></div>` : ""}
      <div class="tc-tom-tat__tong"><span>Cần thanh toán VNPay</span><b>${tien(tongOnline)}</b></div>
    </div>
    <div class="tc-dat-loi" id="tc-dat-loi" role="alert" ${loi ? "" : "hidden"}>${esc(loi)}</div>
    <div class="tc-dat-thanh">
      <button type="button" class="tc-btn tc-btn--phu" id="btn-quay-lai">Hủy đặt vé</button>
      <button type="button" class="tc-btn tc-btn--chinh" id="btn-vnpay">Thanh toán VNPay</button>
    </div>`;
  batDemNguoc(d.han_thanh_toan, () => {
    datCho = null;
    if (typeof capNhatGioHang === "function") capNhatGioHang();
    noiDungSoDo.innerHTML = `<div class="tc-trong tc-trong--loi"><strong>Đã hết thời gian thanh toán</strong>Ghế đã được nhả, bạn có thể đặt lại.</div>`;
  });
  document.getElementById("btn-quay-lai").addEventListener("click", huyGiuChoVaQuayLai);
  document.getElementById("btn-vnpay").addEventListener("click", async () => {
    const nut = document.getElementById("btn-vnpay");
    nut.disabled = true;
    try {
      const kq = await apiPost(`/ve/dat-cho/${datCho.ma_dat_cho}/duong-dan-thanh-toan`, { frontend_origin: location.origin });
      dungDemNguoc();
      location.href = kq.duong_dan_thanh_toan; // sang cổng thanh toán; kết quả do IPN quyết định, khách được đưa về trang kết quả
    } catch (err) {
      nut.disabled = false;
      const el = document.getElementById("tc-dat-loi");
      el.textContent = err.message;
      el.hidden = false;
    }
  });
}

// ----- Xong (thanh toán tại quầy) -----
function veThanhCong() {
  dungDemNguoc();
  const d = datCho;
  noiDungSoDo.innerHTML = `
    <div class="tc-xong">
      <div class="tc-xong__dau">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>
      </div>
      <h2 id="tc-so-do-tieu-de">Đặt vé thành công</h2>
      <p>Mã đặt chỗ <b class="tc-xong__ma">${esc(d.ma_dat_cho)}</b></p>
    </div>
    <div class="tc-tom-tat">
      <div><span>Chuyến</span><b>${esc(d.chuyen.ten_diem_don)} → ${esc(d.chuyen.ten_diem_tra)}</b></div>
      <div><span>Giờ đón</span><b>${nhanNgay(ngayVN(d.chuyen.gio_don_du_kien))} · ${gioVN(d.chuyen.gio_don_du_kien)}</b></div>
      <div><span>Ghế</span><b>${d.ve.map((v) => esc(v.so_ghe)).join(", ")}</b></div>
      <div class="tc-tom-tat__tong"><span>Thanh toán tại quầy</span><b>${tien(d.tong_tien)}</b></div>
    </div>
    <p class="tc-xong__nhac">Vui lòng ra văn phòng <b>${esc(d.chuyen.ten_diem_don)}</b> trước giờ khởi hành để thanh toán và nhận vé.</p>
    <div class="tc-dat-thanh tc-dat-thanh--giua">
      <button type="button" class="tc-btn tc-btn--chinh" id="btn-xong">Đóng</button>
    </div>`;
  document.getElementById("btn-xong").addEventListener("click", () => {
    dongHan();
    if (typeof lanTim !== "undefined" && lanTim) timChuyen(); // số ghế trống đã đổi
  });
}

// ---------- Khởi tạo ----------
async function taiKhuVuc() {
  veTrangThaiTrong("Đang tải danh sách điểm…", "");
  coDi.dongBang.placeholder = coDen.dongBang.placeholder = "Đang tải…";
  try {
    dsKhuVuc = await apiGet("/chuyen/khu-vuc");
  } catch (err) {
    veTrangThaiTrong("Chưa tải được danh sách điểm đi/đến", esc(err.message), {
      loi: true,
      nut: '<div><button type="button" class="tc-chip" id="btn-thu-lai">Thử lại</button></div>',
    });
    document.getElementById("btn-thu-lai").addEventListener("click", khoiTao);
    return false;
  }
  coDi.dongBang.placeholder = "Chọn điểm đi";
  coDen.dongBang.placeholder = "Chọn điểm đến";
  coDi.datDanhSach(dsKhuVuc.filter((k) => k.co_van_phong)); // điểm đón luôn là văn phòng (mục 3.1)
  coDen.datDanhSach(dsKhuVuc);
  vungKetQua.innerHTML = "";
  return true;
}

async function khoiTao() {
  oNgay.min = homNayVN();
  oNgay.value = oNgay.value || homNayVN();
  veChipNgay();

  // Từ giỏ hàng ở trang khác sang: mở thẳng lượt đặt cần hoàn tất (?tiep-tuc=MÃ_ĐẶT_CHỖ)
  const maTiepTuc = new URLSearchParams(location.search).get("tiep-tuc");
  if (maTiepTuc && DA_DANG_NHAP_KHACH()) {
    history.replaceState(null, "", location.pathname);
    moTiepDatCho(maTiepTuc);
  }
  if (!(await taiKhuVuc())) return;

  // Mở lại đúng lần tìm từ đường dẫn (?di=KV001&den=KV003&ngay=2026-10-05) — để chia sẻ/tải lại trang
  const q = new URLSearchParams(location.search);
  const di = dsKhuVuc.find((k) => k.ma === q.get("di") && k.co_van_phong);
  const den = dsKhuVuc.find((k) => k.ma === q.get("den"));
  if (di && den) {
    coDi.dat(di);
    coDen.dat(den);
    if (q.get("ngay") && q.get("ngay") >= homNayVN()) oNgay.value = q.get("ngay");
    veChipNgay();
    await timChuyen();
    tiepTucDatVeDangDo();
  }
}

// Khách vừa đăng nhập xong để đặt vé: mở lại đúng chuyến, chọn sẵn các ghế đã chọn trước khi bị chuyển sang trang đăng nhập
function tiepTucDatVeDangDo() {
  let viec = null;
  try {
    viec = JSON.parse(sessionStorage.getItem(KHOA_DAT_DANG_CHO) || "null");
  } catch {}
  sessionStorage.removeItem(KHOA_DAT_DANG_CHO);
  if (!viec || !DA_DANG_NHAP_KHACH() || !ketQua.some((c) => c.id === viec.chuyenId)) return;
  moSoDo(viec.chuyenId, viec.ghe || []).then(() => {
    // Quay lại đúng bước chọn điểm đón/trả với lựa chọn trước đó, khách chỉ cần bấm "Tiếp tục"
    if (chuyenXem && viec.diemDon && viec.diemTra && gheDangChon.size) {
      diemDonChon = viec.diemDon;
      diemTraChon = viec.diemTra;
      veBuocDiemDonTra();
    }
  });
}

khoiTao();
