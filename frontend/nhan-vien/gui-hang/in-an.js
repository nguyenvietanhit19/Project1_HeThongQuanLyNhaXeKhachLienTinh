/* in-an.js — biên nhận, nhãn dán, phiếu bàn giao. */

let donDangIn = null;

function hienThiBienNhan(don) {
  donDangIn = don;
  const cod = laCod(don);
  datText("bnMaVanDon", don.ma_van_don);
  veMaVach("bnMaVach", don.ma_van_don);
  $("bnDaChinhSua").hidden = !(don.so_lan_chinh_sua > 0);
  datText("bnThoiGian", dinhDangThoiGian(don.ngay_tao));
  datText("bnDiemGui", don.ten_diem_gui || "--");
  datText("bnDiemNhan", don.ten_diem_nhan || "--");
  datText("bnDiemNhanLienHe", [don.dia_chi_diem_nhan, don.sdt_diem_nhan ? `ĐT: ${don.sdt_diem_nhan}` : ""].filter(Boolean).join(" · "));
  datText("bnTuyen", don.ten_tuyen || "--");
  datText("bnNguoiGui", `${don.ten_nguoi_gui} (${don.sdt_nguoi_gui})`);
  datText("bnNguoiNhan", `${don.ten_nguoi_nhan} (${don.sdt_nguoi_nhan})`);
  datText("bnHang", moTaHang(don));
  datText("bnThanhToan", cod ? "COD — người nhận trả khi lấy hàng" : "Người gửi trả trước");
  datText("bnTienNhan", cod ? "NGƯỜI NHẬN TRẢ KHI LẤY:" : "ĐÃ THU CỦA NGƯỜI GỬI:");
  datText("bnTien", dinhDangTien(don.gia_cuoc));
  moModal("modalBienNhan");
}

function hienThiNhanDan(don) {
  donDangIn = don;
  datText("ndMaVanDon", don.ma_van_don);
  veMaVach("ndMaVach", don.ma_van_don, { chieuCao: 64 });
  datText("ndDiemNhan", don.ten_diem_nhan || "--");
  datText("ndTuyen", `Tuyến: ${don.ten_tuyen || "--"}`);
  datText("ndNguoiNhan", don.ten_nguoi_nhan);
  datText("ndSdtNhan", `📞 ${don.sdt_nguoi_nhan}`);
  datText("ndLoaiHang", don.ten_loai_hang || "Hàng hóa");
  datText("ndCanNang", `⚖️ ${dinhDangKg(don.can_nang_kg)}${kichThuocHang(don)}`);

  const banner = $("ndThanhToan");
  const cod = laCod(don);
  banner.className = `label-payment-banner${cod ? " is-cod" : ""}`;
  banner.innerHTML = '<div class="label-payment-badge"></div><div class="label-cod-highlight"></div>';
  banner.firstElementChild.textContent = cod ? "🚚 THU COD KHI GIAO:" : "💵 ĐÃ THANH TOÁN CƯỚC TRƯỚC";
  banner.lastElementChild.textContent = cod ? dinhDangTien(don.gia_cuoc) : "Không thu thêm";
  moModal("modalNhanDan");
}

function hienThiPhieuBanGiao(don) {
  const cod = laCod(don);
  datText("pxMaVanDon", don.ma_van_don);
  veMaVach("pxMaVach", don.ma_van_don);
  datText("pxThoiGian", dinhDangThoiGian(don.ngay_giao));
  datText("pxVanPhong", don.ten_diem_nhan || "--");
  datText("pxNguoiNhan", `${don.ten_nguoi_nhan} (${don.sdt_nguoi_nhan})`);
  datText("pxThanhToan", cod ? "COD — thu tại quầy khi giao" : "Người gửi đã trả trước");
  datText("pxTienThu", cod ? dinhDangTien(don.gia_cuoc) : "0 đ");
  moModal("modalPhieuXuatKho");
}

