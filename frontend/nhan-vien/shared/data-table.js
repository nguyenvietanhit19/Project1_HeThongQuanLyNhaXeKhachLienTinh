/*
 * renderDataTable — component viết tay dùng chung cho các trang danh mục
 * trong frontend/nhan-vien/quan-ly/ (CONTRIBUTING.md mục 6, ví dụ đã gợi ý
 * sẵn chữ ký hàm này). Không dùng framework, chỉ render lại innerHTML.
 *
 *   renderDataTable(containerEl, columns, rows, { onEdit, editLabel, onDelete, tenXoa })
 *   - columns: [{ key, label, render?(row) }]
 *   - onEdit(row): optional — nếu có, thêm 1 nút hành động mỗi hàng
 *   - editLabel: chữ trên nút hành động sửa/xem, mặc định "Sửa"
 *   - onDelete(row): optional — nếu có, thêm nút "Xóa"; tự hỏi xác nhận
 *     trước khi gọi (không cần page tự confirm() lại)
 *   - tenXoa(row): chữ hiển thị trong hộp thoại xác nhận, mặc định dùng
 *     cột đầu tiên
 */

function renderDataTable(containerEl, columns, rows, { onEdit, editLabel = "Sửa", onDelete, tenXoa } = {}) {
  if (!rows.length) {
    containerEl.innerHTML = '<div class="nv-table__empty">Chưa có dữ liệu</div>';
    return;
  }

  const coCotHanhDong = onEdit || onDelete;
  const theadCols = columns.map((c) => `<th>${c.label}</th>`).join("") + (coCotHanhDong ? "<th></th>" : "");

  const tbodyRows = rows
    .map((row, idx) => {
      const tds = columns.map((c) => `<td>${c.render ? c.render(row) : (row[c.key] ?? "")}</td>`).join("");
      const nutSua = onEdit ? `<button class="nv-btn-sua" data-idx="${idx}" type="button">${editLabel}</button>` : "";
      const nutXoa = onDelete ? `<button class="nv-btn-xoa" data-idx="${idx}" type="button">Xóa</button>` : "";
      const actionTd = coCotHanhDong ? `<td style="text-align:right"><div class="nv-hang-hanh-dong">${nutSua}${nutXoa}</div></td>` : "";
      return `<tr>${tds}${actionTd}</tr>`;
    })
    .join("");

  containerEl.innerHTML = `
    <table class="nv-table">
      <thead><tr>${theadCols}</tr></thead>
      <tbody>${tbodyRows}</tbody>
    </table>
  `;

  if (onEdit) {
    containerEl.querySelectorAll(".nv-btn-sua").forEach((btn) => {
      btn.addEventListener("click", () => onEdit(rows[Number(btn.dataset.idx)]));
    });
  }

  if (onDelete) {
    containerEl.querySelectorAll(".nv-btn-xoa").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = rows[Number(btn.dataset.idx)];
        const ten = tenXoa ? tenXoa(row) : Object.values(row)[0];
        if (confirm(`Xóa "${ten}"? Không thể hoàn tác.`)) {
          onDelete(row);
        }
      });
    });
  }
}
