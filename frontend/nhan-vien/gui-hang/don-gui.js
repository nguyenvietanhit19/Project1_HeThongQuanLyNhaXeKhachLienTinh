/* don-gui.js — tab Đơn gửi đi (phân trang phía server). */

let henGioTimDonGui = null;

/** Bộ lọc đang chọn trên thanh lọc (dùng cho cả tải trang và xuất CSV). */
function boLocDonGui() {
  return {
    huong: "gui",
    trang_thai: $("selectTrangThaiDonGui").value,
    phuong_thuc_thanh_toan: $("selectThanhToanDonGui").value,
    tu_khoa: $("inputTuKhoaDonGui").value.trim(),
    ...phamViQuery(),
  };
}

async function taiDonGui() {
  const params = { ...boLocDonGui(), limit: SO_DONG_MOI_TRANG, offset: state.donGui.offset };
  try {
    const data = await apiGet(`/gui-hang/don-hang${taoQuery(params)}`);
    state.donGui.items = data.items;
    state.donGui.total = data.total;
    if (!params.trang_thai && !params.phuong_thuc_thanh_toan && !params.tu_khoa) datText("stat-don-gui-count", data.total);
    renderDonGui();
  } catch (err) {
    hienTrangThaiBang("tbodyDonGui", 7, `Lỗi tải danh sách: ${err.message}`, "table-empty table-error");
  }
}

function renderDonGui() {
  const tbody = $("tbodyDonGui");
  const { items, total, offset } = state.donGui;
  if (!items.length) {
    hienTrangThaiBang("tbodyDonGui", 7, total ? "Không có đơn ở trang này." : "Không có đơn nào phù hợp.");
  } else {
    tbody.innerHTML = items.map(d => `
      <tr class="hd-row hd-row--tt-${escapeHtml(d.trang_thai)}">
        <td><strong class="order-code-badge">${escapeHtml(d.ma_van_don)}</strong><div class="cell-sub">${escapeHtml(dinhDangThoiGian(d.ngay_tao))}</div></td>
        <td><div class="party-name">${escapeHtml(d.ten_nguoi_gui)}</div><div class="cell-sub">${escapeHtml(d.sdt_nguoi_gui)}</div></td>
        <td><div class="party-name">${escapeHtml(d.ten_nguoi_nhan)}</div><div class="cell-sub">${escapeHtml(d.sdt_nguoi_nhan)} · ${escapeHtml(d.ten_diem_nhan || "--")}</div></td>
        <td><div class="goods-name">${escapeHtml(d.ten_loai_hang || "Hàng hóa")}</div><div class="cell-sub">${escapeHtml(dinhDangKg(d.can_nang_kg))}</div></td>
        <td class="text-right"><div class="price-tag">${escapeHtml(dinhDangTien(d.gia_cuoc))}</div>${badgeThanhToan(d)}</td>
        <td class="text-center">${badgeTrangThai(d.trang_thai)}${d.trang_thai === "da_len_xe" && d.bien_so_xe ? `<div class="cell-sub">${escapeHtml(d.bien_so_xe)}</div>` : ""}</td>
        <td class="text-center"><div class="table-actions-cell">
          ${coTheSuaDon(d) ? `<button type="button" class="btn-action-icon" data-hanh-dong="sua-lien-he" data-id="${escapeHtml(d.id)}" title="Sửa tên / SĐT người gửi, người nhận">✏️</button>` : ""}
          <button type="button" class="btn-action-icon" data-hanh-dong="in-bien-nhan" data-id="${escapeHtml(d.id)}" title="In lại biên nhận cho người gửi">🖨️</button>
          <button type="button" class="btn-action-icon" data-hanh-dong="in-nhan" data-id="${escapeHtml(d.id)}" title="In lại nhãn dán kiện hàng">🏷️</button>
        </div></td>
      </tr>`).join("");
  }

  veThanhPhanTrang("phanTrangDonGui", total, offset);
}

/** Xuất mọi đơn khớp bộ lọc hiện tại (không chỉ trang đang xem), tối đa 5000 đơn. */
async function xuatCsvDonGui() {
  const btn = $("btnXuatCsvDonGui");
  btn.disabled = true;
  try {
    const loc = boLocDonGui();
    const BUOC = 100, TOI_DA = 5000;
    const tatCa = [];
    let offset = 0, total = 0;
    do {
      const data = await apiGet(`/gui-hang/don-hang${taoQuery({ ...loc, limit: BUOC, offset })}`);
      tatCa.push(...data.items);
      total = data.total;
      offset += BUOC;
    } while (offset < total && tatCa.length < TOI_DA);
    if (!tatCa.length) {
      showToast("warning", "Không có dữ liệu", "Không có đơn nào để xuất.");
      return;
    }
    xuatCsv(`don-gui-${ngayISO(new Date())}.csv`,
      ["Mã vận đơn", "Ngày tạo", "Người gửi", "SĐT người gửi", "Người nhận", "SĐT người nhận", "Văn phòng nhận",
        "Loại hàng", "Khối lượng (kg)", "Cước (VNĐ)", "Hình thức", "Trạng thái"],
      tatCa.map(d => [
        d.ma_van_don, dinhDangThoiGian(d.ngay_tao), d.ten_nguoi_gui, d.sdt_nguoi_gui, d.ten_nguoi_nhan, d.sdt_nguoi_nhan,
        d.ten_diem_nhan || "", d.ten_loai_hang || "", d.can_nang_kg, d.gia_cuoc,
        laCod(d) ? "COD" : "Trả trước",
        TRANG_THAI[d.trang_thai]?.ten || d.trang_thai,
      ]));
    if (total > tatCa.length) {
      showToast("warning", "Đã xuất một phần", `File chứa ${tatCa.length}/${total} đơn đầu tiên — hãy thu hẹp bộ lọc để xuất phần còn lại.`);
    }
  } catch (err) {
    showToast("error", "Không xuất được file", err.message);
  } finally {
    btn.disabled = false;
  }
}

function locLaiDonGui() {
  state.donGui.offset = 0;
  taiDonGui();
}

