/*
 * renderDataTable — component viết tay dùng cho các trang danh mục trong
 * frontend/nhan-vien/quan-ly/. Không dùng framework, chỉ render lại
 * innerHTML. Riêng của domain Quản lý — vai trò khác cần bảng tương tự thì
 * tự viết bản của họ, không import file này.
 *
 *   renderDataTable(containerEl, columns, rows, { onEdit, editLabel, onDelete, tenXoa, onRowClick })
 *   - columns: [{ key, label, render?(row) }]
 *   - onEdit(row): optional — nếu có, thêm 1 nút hành động mỗi hàng
 *   - editLabel: chữ trên nút hành động sửa/xem, mặc định "Sửa"
 *   - onDelete(row): optional — nếu có, thêm nút "Xóa"; tự hỏi xác nhận
 *     trước khi gọi (không cần page tự confirm() lại)
 *   - tenXoa(row): chữ hiển thị trong hộp thoại xác nhận, mặc định dùng
 *     cột đầu tiên
 *   - onRowClick(row, tdChiTietEl): optional — bấm cả hàng để mở rộng 1
 *     hàng chi tiết ngay bên dưới, bấm lại (hoặc mở hàng khác) để đóng —
 *     chỉ 1 hàng mở tại 1 thời điểm (accordion). Hàm nhận ô <td> trống
 *     (đã có "Đang tải..."), tự điền nội dung vào đó (có thể await gọi API).
 */

function renderDataTable(containerEl, columns, rows, { onEdit, editLabel = "Sửa", onDelete, tenXoa, onRowClick } = {}) {
  if (!rows.length) {
    containerEl.innerHTML = '<div class="nv-table__empty">Chưa có dữ liệu</div>';
    return;
  }

  const coCotHanhDong = onEdit || onDelete;
  const soCot = columns.length + (coCotHanhDong ? 1 : 0);
  const theadCols = columns.map((c) => `<th>${c.label}</th>`).join("") + (coCotHanhDong ? "<th></th>" : "");

  const tbodyRows = rows
    .map((row, idx) => {
      const tds = columns.map((c) => `<td>${c.render ? c.render(row) : (row[c.key] ?? "")}</td>`).join("");
      const nutSua = onEdit ? `<button class="nv-btn-sua" data-idx="${idx}" type="button">${editLabel}</button>` : "";
      const nutXoa = onDelete ? `<button class="nv-btn-xoa" data-idx="${idx}" type="button">Xóa</button>` : "";
      const actionTd = coCotHanhDong ? `<td style="text-align:right"><div class="nv-hang-hanh-dong">${nutSua}${nutXoa}</div></td>` : "";
      const lopMoRong = onRowClick ? " nv-table__hang-mo-rong" : "";
      const lopSoc = idx % 2 === 1 ? " nv-table__row--soc" : "";
      return `<tr data-idx="${idx}" class="${lopMoRong}${lopSoc}">${tds}${actionTd}</tr>`;
    })
    .join("");

  containerEl.innerHTML = `
    <div class="nv-table-wrap">
      <table class="nv-table">
        <thead><tr>${theadCols}</tr></thead>
        <tbody>${tbodyRows}</tbody>
      </table>
    </div>
  `;

  if (onEdit) {
    containerEl.querySelectorAll(".nv-btn-sua").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        onEdit(rows[Number(btn.dataset.idx)]);
      });
    });
  }

  if (onDelete) {
    containerEl.querySelectorAll(".nv-btn-xoa").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const row = rows[Number(btn.dataset.idx)];
        const ten = tenXoa ? tenXoa(row) : Object.values(row)[0];
        if (confirm(`Xóa "${ten}"? Không thể hoàn tác.`)) {
          onDelete(row);
        }
      });
    });
  }

  if (onRowClick) {
    const tbody = containerEl.querySelector("tbody");
    tbody.querySelectorAll("tr[data-idx]").forEach((tr) => {
      tr.addEventListener("click", async () => {
        const hangSau = tr.nextElementSibling;
        const dangMo = hangSau && hangSau.classList.contains("nv-table__hang-chi-tiet");

        // đóng hàng chi tiết đang mở (nếu có) — chỉ 1 hàng mở tại 1 thời điểm
        tbody.querySelectorAll(".nv-table__hang-chi-tiet").forEach((h) => h.remove());
        tbody.querySelectorAll("tr[data-idx]").forEach((r) => r.classList.remove("dang-mo"));

        if (dangMo) return; // bấm lại đúng hàng đang mở -> chỉ đóng

        tr.classList.add("dang-mo");
        const hangMoi = document.createElement("tr");
        hangMoi.className = "nv-table__hang-chi-tiet";
        const tdMoi = document.createElement("td");
        tdMoi.colSpan = soCot;
        tdMoi.innerHTML = '<div class="nv-table__dang-tai">Đang tải...</div>';
        hangMoi.appendChild(tdMoi);
        tr.after(hangMoi);

        await onRowClick(rows[Number(tr.dataset.idx)], tdMoi);
      });
    });
  }
}
