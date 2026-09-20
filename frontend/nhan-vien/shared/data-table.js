/*
 * renderDataTable — component viết tay dùng chung cho các trang danh mục
 * trong frontend/nhan-vien/quan-ly/ (CONTRIBUTING.md mục 6, ví dụ đã gợi ý
 * sẵn chữ ký hàm này). Không dùng framework, chỉ render lại innerHTML.
 *
 *   renderDataTable(containerEl, columns, rows, { onEdit, editLabel })
 *   - columns: [{ key, label, render?(row) }]
 *   - onEdit(row): optional — nếu có, thêm 1 nút hành động mỗi hàng
 *   - editLabel: chữ trên nút hành động, mặc định "Sửa"
 */

function renderDataTable(containerEl, columns, rows, { onEdit, editLabel = "Sửa" } = {}) {
  if (!rows.length) {
    containerEl.innerHTML = '<div class="nv-table__empty">Chưa có dữ liệu</div>';
    return;
  }

  const theadCols = columns.map((c) => `<th>${c.label}</th>`).join("") + (onEdit ? "<th></th>" : "");

  const tbodyRows = rows
    .map((row, idx) => {
      const tds = columns.map((c) => `<td>${c.render ? c.render(row) : (row[c.key] ?? "")}</td>`).join("");
      const actionTd = onEdit
        ? `<td style="text-align:right"><button class="nv-btn-sua" data-idx="${idx}" type="button">${editLabel}</button></td>`
        : "";
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
}
