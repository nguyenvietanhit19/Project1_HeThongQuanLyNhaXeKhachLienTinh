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

// ---------- Sơ đồ ghế của 1 chuyến ----------
const modalSoDo = document.getElementById("modal-so-do");
const noiDungSoDo = document.getElementById("tc-so-do-noi-dung");

function dongSoDo() {
  modalSoDo.hidden = true;
  document.body.style.overflow = "";
}
document.getElementById("btn-dong-so-do").addEventListener("click", dongSoDo);
modalSoDo.addEventListener("click", (e) => {
  if (e.target === modalSoDo) dongSoDo();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalSoDo.hidden) dongSoDo();
});

async function moSoDo(chuyenId) {
  modalSoDo.hidden = false;
  document.body.style.overflow = "hidden";
  noiDungSoDo.innerHTML = '<div class="tc-khung-xuong" style="height:260px"></div>';
  try {
    const ct = await apiGet(`/chuyen/${chuyenId}/so-do-ghe?diem_di_id=${lanTim.di.id}&diem_den_id=${lanTim.den.id}`);
    veSoDo(ct);
  } catch (err) {
    noiDungSoDo.innerHTML = `<div class="tc-trong tc-trong--loi"><strong>Chưa tải được sơ đồ ghế</strong>${esc(err.message)}</div>`;
  }
}

function veTang(ghe, tang, tl, soTang) {
  const cacGhe = ghe.filter((g) => g.tang === tang);
  const rong = tl.rong;
  const cao = tl.cao;
  const hopWidth = document.querySelector(".tc-modal__hop").clientWidth;
  const tiLe = Math.min(1, (hopWidth - 90 - (soTang - 1) * 22) / soTang / rong);
  const o = cacGhe
    .map(
      (g) =>
        `<span class="tc-ghe ${g.trang_thai === "trong" ? "tc-ghe--trong" : "tc-ghe--co-nguoi"}" style="left:${g.x - tl.minX + 16}px; top:${g.y - tl.minY + 32}px" title="${esc(g.ma_ghe)} — ${g.trang_thai === "trong" ? "trống" : "đã có người"}">${esc(g.ma_ghe)}</span>`
    )
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

function veSoDo(ct) {
  const phut = Math.round((new Date(ct.gio_den_du_kien) - new Date(ct.gio_don_du_kien)) / 60000);
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
    <div class="tc-so-do__dau">
      <h2 id="tc-so-do-tieu-de">${esc(ct.ten_diem_don)} → ${esc(ct.ten_diem_tra)}</h2>
      <p>${nhanNgay(ngayVN(ct.gio_don_du_kien))} · ${gioVN(ct.gio_don_du_kien)} → ${gioVN(ct.gio_den_du_kien)} (${thoiLuong(phut)})</p>
      <div class="tc-so-do__thong-tin">
        <span class="tc-the">${esc(ct.ten_loai_xe)}</span>
        <span class="tc-the">${tien(ct.gia)}</span>
        <span class="tc-the ${ct.so_ghe_trong === 0 ? "tc-the--het" : ct.so_ghe_trong <= 5 ? "tc-the--ghe-it" : "tc-the--ghe-nhieu"}">${ct.so_ghe_trong === 0 ? "Hết chỗ" : `Còn ${ct.so_ghe_trong}/${ct.tong_ghe} ghế`}</span>
        ${ct.bien_so ? `<span class="tc-the">Xe ${esc(ct.bien_so)}</span>` : ""}
        ${ct.dang_hoan ? '<span class="tc-the tc-the--hoan">Đang hoãn — giờ có thể thay đổi</span>' : ""}
      </div>
    </div>
    <div class="tc-so-do__chu-thich">
      <span><i class="tc-mau-ghe tc-ghe--trong"></i>Ghế trống</span>
      <span><i class="tc-mau-ghe tc-ghe--co-nguoi"></i>Đã có người</span>
    </div>
    <div class="tc-so-do__khu">
      ${Array.from({ length: ct.so_tang }, (_, i) => veTang(ghe, i + 1, tl, ct.so_tang)).join("")}
    </div>
    <div class="tc-so-do__diem">
      <div><h3>Điểm đón</h3><ul>${dsDiem(ct.diem_don_co_the_chon)}</ul></div>
      <div><h3>Điểm trả</h3><ul>${dsDiem(ct.diem_tra_co_the_chon)}</ul></div>
    </div>`;
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
    timChuyen();
  }
}

khoiTao();
