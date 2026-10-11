/*
 * Ô tìm chuyến dùng chung (trang chủ + trang kết quả): chọn điểm đi/đến (2 bước, gõ chữ tìm không dấu), ngày dd/mm/yyyy,
 * đổi chiều, kiểm tra dữ liệu rồi gọi thucHienTim({ di, den, ngay }) — hàm này do TỪNG TRANG định nghĩa (trang chủ: chuyển sang
 * trang kết quả; trang kết quả: tìm lại ngay tại chỗ). Cần tien-ich-ngay.js và khung-trang.js nạp trước.
 * Trang cần có đúng các id: form-tim, combo-di, o-di, btn-doi-cho, combo-den, o-den, o-ngay-hien, btn-lich, o-ngay, btn-tim, tc-loi-tim.
 */

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

// ---------- Trạng thái ô tìm kiếm ----------
const oNgay = document.getElementById("o-ngay"); // giá trị thật (yyyy-mm-dd), ẩn
const oNgayHien = document.getElementById("o-ngay-hien"); // ô khách thấy và gõ: dd/mm/yyyy
const oLoiTim = document.getElementById("tc-loi-tim");
const btnTim = document.getElementById("btn-tim");

let dsKhuVuc = [];
let daTaiKhuVuc = false;
let khiDoiNgay = () => {}; // trang đăng ký hàm chạy mỗi khi ngày đổi (VD vẽ lại chip chọn nhanh)
const datKhiDoiNgay = (fn) => (khiDoiNgay = fn);

const coDi = taoCombo(document.getElementById("combo-di"), { loaiTru: () => coDen.lay() });
const coDen = taoCombo(document.getElementById("combo-den"), { loaiTru: () => coDi.lay() });

function baoLoiTim(noiDung) {
  oLoiTim.textContent = noiDung || "";
  oLoiTim.hidden = !noiDung;
}

// ---------- Ngày: gõ dd/mm/yyyy hoặc chọn từ lịch ----------
const ngayHien = (iso) => (iso ? iso.split("-").reverse().join("/") : "");

function datNgay(iso) {
  oNgay.value = iso;
  oNgayHien.value = ngayHien(iso);
  khiDoiNgay();
}

// Gõ dd/mm/yyyy (tự thêm dấu /); đủ 8 chữ số và là ngày thật, không ở quá khứ thì mới nhận vào ô giá trị
function docNgayGo() {
  const so = oNgayHien.value.replace(/\D/g, "").slice(0, 8);
  oNgayHien.value = [so.slice(0, 2), so.slice(2, 4), so.slice(4, 8)].filter(Boolean).join("/");
  if (so.length < 8) return;
  const [d, m, y] = [+so.slice(0, 2), +so.slice(2, 4), +so.slice(4, 8)];
  const thu = new Date(y, m - 1, d);
  if (thu.getFullYear() !== y || thu.getMonth() !== m - 1 || thu.getDate() !== d) return;
  const iso = `${y}-${pad2(m)}-${pad2(d)}`;
  if (iso < homNayVN()) return;
  oNgay.value = iso;
  khiDoiNgay();
}
oNgayHien.addEventListener("input", docNgayGo);
oNgayHien.addEventListener("blur", () => (oNgayHien.value = ngayHien(oNgay.value))); // gõ dở hoặc sai thì quay về ngày đang chọn
oNgay.addEventListener("change", () => {
  oNgayHien.value = ngayHien(oNgay.value);
  khiDoiNgay();
});
document.getElementById("btn-lich").addEventListener("click", () => {
  if (oNgay.showPicker) oNgay.showPicker();
  else oNgay.focus();
});

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

// ---------- Tìm chuyến: kiểm tra rồi giao cho trang xử lý ----------
document.getElementById("form-tim").addEventListener("submit", (e) => {
  e.preventDefault();
  xuLyTim();
});

async function xuLyTim() {
  baoLoiTim("");
  if (!daTaiKhuVuc && !(await taiKhuVuc())) return;
  const di = coDi.lay();
  const den = coDen.lay();
  const ngay = oNgay.value;
  if (!di || !den) return baoLoiTim("Vui lòng chọn điểm đi và điểm đến từ danh sách gợi ý.");
  if (di.id === den.id) return baoLoiTim("Điểm đi và điểm đến phải khác nhau.");
  if (!ngay) return baoLoiTim("Vui lòng chọn ngày đi.");
  if (ngay < homNayVN()) return baoLoiTim("Không thể tìm chuyến ở ngày đã qua.");
  thucHienTim({ di, den, ngay });
}

// ---------- Tải danh sách điểm đi/đến ----------
async function taiKhuVuc() {
  coDi.dongBang.placeholder = coDen.dongBang.placeholder = "Đang tải…";
  try {
    dsKhuVuc = await apiGet("/chuyen/khu-vuc");
  } catch (err) {
    coDi.dongBang.placeholder = "Chọn điểm đi";
    coDen.dongBang.placeholder = "Chọn điểm đến";
    baoLoiTim(`Chưa tải được danh sách điểm đi/đến (${err.message}). Bấm "Tìm chuyến" để thử lại.`);
    return false;
  }
  coDi.dongBang.placeholder = "Chọn điểm đi";
  coDen.dongBang.placeholder = "Chọn điểm đến";
  coDi.datDanhSach(dsKhuVuc.filter((k) => k.co_van_phong)); // điểm đón luôn là văn phòng (mục 3.1)
  coDen.datDanhSach(dsKhuVuc);
  daTaiKhuVuc = true;
  return true;
}
