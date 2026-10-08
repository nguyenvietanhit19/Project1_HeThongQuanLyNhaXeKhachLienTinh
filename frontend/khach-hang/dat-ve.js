/*
 * Cửa sổ sơ đồ ghế + đặt vé của 1 chuyến (UC-04, UC-05) — dùng chung cho trang chủ (mở lại lượt đặt từ giỏ hàng: moTiepDatCho)
 * và trang kết quả tìm chuyến (chọn chuyến: moSoDo). Trang cần có khung #modal-so-do (xem tim-chuyen.html) và nạp trước:
 * api-client.js, khung-trang.js, tien-ich-ngay.js. Trang kết quả định nghĩa thêm `lanTim` ({di, den, ngay}) và `timChuyen()`.
 */

// ---------- Sơ đồ ghế + đặt vé của 1 chuyến (UC-04, UC-05) ----------
// Cùng 1 cửa sổ đi qua các bước: ① chọn ghế → ② chọn điểm đón/trả → ③ thanh toán → xong.
// Ghế CHỈ bị khóa khi khách bấm "Tiếp tục" ở bước ② (ai nhanh hơn thì giữ được, 10 phút). Từ đó lượt đặt nằm trong
// giỏ hàng: thoát ra giữa chừng vẫn quay lại hoàn tất được, ghế tiếp tục đếm ngược hạn giữ.
const modalSoDo = document.getElementById("modal-so-do");
const noiDungSoDo = document.getElementById("tc-so-do-noi-dung");

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
  return `<ol class="tc-buoc">${ten.map((t, i) => `<li class="${i + 1 === dang ? "is-active" : i + 1 < dang ? "is-xong" : ""}"><b>${i + 1}</b><span>${t}</span></li>`).join("")}</ol>`;
};

// ----- Lộ trình chuyến: mọi điểm dừng theo thứ tự chạy thật + giờ dự kiến (xem từ bước chọn ghế, quay lại giữ nguyên ghế đã chọn) -----
const boNhoLoTrinh = new Map(); // chuyenId → lộ trình đã tải

function veLoiLoTrinh(thongDiep) {
  noiDungSoDo.innerHTML = `
    <div class="tc-trong tc-trong--loi"><strong>Chưa xem được lộ trình</strong>${esc(thongDiep)}</div>
    <div class="tc-dat-thanh tc-dat-thanh--giua"><button type="button" class="tc-btn tc-btn--phu" id="btn-lo-trinh-quay-lai">Quay lại chọn ghế</button></div>`;
  document.getElementById("btn-lo-trinh-quay-lai").addEventListener("click", () => veSoDo());
}

async function moLoTrinh() {
  const ct = chuyenXem;
  if (!ct) return;
  noiDungSoDo.innerHTML = '<div class="tc-khung-xuong" style="height:260px"></div>';
  try {
    let lt = boNhoLoTrinh.get(ct.id);
    if (!lt) {
      lt = await apiGet(`/chuyen/${ct.id}/lo-trinh`);
      boNhoLoTrinh.set(ct.id, lt);
    }
    veLoTrinh(lt);
  } catch (err) {
    veLoiLoTrinh(err.message || "Có lỗi xảy ra, thử lại sau");
  }
}

function veLoTrinh(lt) {
  const ct = chuyenXem;
  const lenXe = new Set(ct.diem_don_co_the_chon.map((d) => d.diem_id));
  const xuongXe = new Set(ct.diem_tra_co_the_chon.map((d) => d.diem_id));
  const viTri = lt.diem.map((d, i) => i);
  const dau = viTri.find((i) => lenXe.has(lt.diem[i].diem_id));
  const cuoi = [...viTri].reverse().find((i) => xuongXe.has(lt.diem[i].diem_id));
  const trongChang = (i) => dau !== undefined && cuoi !== undefined && i >= dau && i <= cuoi;
  const tenChang = typeof lanTim !== "undefined" && lanTim ? `${lanTim.di.ten} → ${lanTim.den.ten}` : `${ct.ten_diem_don} → ${ct.ten_diem_tra}`;
  const diemTheoKhuVuc = lt.diem
    .map((d, i) => {
      const nhan = lenXe.has(d.diem_id) ? '<em class="lt-nhan lt-nhan--len">Có thể lên xe</em>' : xuongXe.has(d.diem_id) ? '<em class="lt-nhan lt-nhan--xuong">Có thể xuống xe</em>' : "";
      return `
        <li class="lt-diem${trongChang(i) ? " lt-diem--trong" : ""}${trongChang(i) && trongChang(i + 1) ? " lt-diem--noi" : ""}${i === lt.diem.length - 1 ? " lt-diem--cuoi" : ""}">
          <time>${gioVN(d.gio_du_kien)}</time>
          <span class="lt-cham" aria-hidden="true"></span>
          <div class="lt-thong-tin">
            <b>${esc(d.ten)}</b>
            <small>${esc(d.dia_chi)} · ${esc(d.ten_khu_vuc)}</small>
            <span class="lt-the">${d.loai === "van_phong" ? "Văn phòng" : "Điểm dừng"}</span>${nhan}
          </div>
        </li>`;
    })
    .join("");
  noiDungSoDo.innerHTML = `
    <div class="tc-so-do__dau">
      <h2 id="tc-so-do-tieu-de">Lộ trình chuyến</h2>
      <p>${esc(lt.ten_tuyen)} · khởi hành ${gioVN(lt.gio_khoi_hanh)} ${nhanNgay(ngayVN(lt.gio_khoi_hanh), true)} · tổng ${thoiLuong(lt.tong_thoi_gian_phut)}</p>
    </div>
    <p class="lt-chu-thich">Chặng của bạn: <b>${esc(tenChang)}</b> — các điểm trong chặng được tô đậm.</p>
    <ol class="lt-ds">${diemTheoKhuVuc}</ol>
    <div class="tc-dat-thanh tc-dat-thanh--giua">
      <button type="button" class="tc-btn tc-btn--chinh" id="btn-lo-trinh-quay-lai">Quay lại chọn ghế</button>
    </div>`;
  document.getElementById("btn-lo-trinh-quay-lai").addEventListener("click", () => veSoDo());
}

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
      <button type="button" class="tc-nut-lo-trinh" id="btn-xem-lo-trinh">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="6" cy="6" r="2.2"/><circle cx="18" cy="18" r="2.2"/><path d="M8.2 6H15a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h6.8"/></svg>
        Xem lộ trình
      </button>
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
  document.getElementById("btn-xem-lo-trinh").addEventListener("click", moLoTrinh);
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

// Chưa đăng nhập mà bấm "Tiếp tục": hiện hộp hỏi. Chọn "Đăng nhập" thì chuyển sang trang đăng nhập (đăng nhập xong về trang chủ);
// chọn "Để sau" (hoặc Esc, bấm ra ngoài) thì ở lại, ghế đang chọn vẫn còn nguyên.
function hoiDangNhap() {
  if (modalSoDo.querySelector(".tc-xn")) return;
  const lop = document.createElement("div");
  lop.className = "tc-xn";
  lop.setAttribute("role", "alertdialog");
  lop.setAttribute("aria-labelledby", "tc-xn-dn-tieu-de");
  lop.innerHTML = `
    <div class="tc-xn__hop">
      <h3 id="tc-xn-dn-tieu-de">Bạn cần đăng nhập</h3>
      <p>Bạn cần đăng nhập để giữ ghế và đặt vé.</p>
      <div class="tc-xn__nut">
        <button type="button" class="tc-btn tc-btn--phu" id="btn-dn-de-sau">Để sau</button>
        <button type="button" class="tc-btn tc-btn--chinh" id="btn-dn-dang-nhap">Đăng nhập</button>
      </div>
    </div>`;
  modalSoDo.appendChild(lop);
  lop.querySelector("#btn-dn-de-sau").addEventListener("click", () => lop.remove());
  lop.addEventListener("click", (e) => {
    if (e.target === lop) lop.remove(); // bấm ra ngoài hộp = Để sau
  });
  lop.querySelector("#btn-dn-dang-nhap").addEventListener("click", () => {
    location.href = "/khach-hang/dang-nhap.html";
  });
  lop.querySelector("#btn-dn-dang-nhap").focus();
}

// "Tiếp tục": mốc khóa ghế. Ai bấm trước giữ được ghế (10 phút); người sau nhận lỗi và quay về chọn lại.
async function tiepTuc() {
  diemDonChon = document.querySelector('input[name="diem-don"]:checked').value;
  diemTraChon = document.querySelector('input[name="diem-tra"]:checked').value;
  if (!DA_DANG_NHAP_KHACH()) return hoiDangNhap(); // chưa đăng nhập: hỏi khách trước, không tự chuyển trang
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
