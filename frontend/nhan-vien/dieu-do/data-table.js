/*
 * renderDataTable — component hiển thị bảng dùng cho các trang trong
 * frontend/nhan-vien/dieu-do/. Bám sát phong cách chuẩn của quản lý.
 *
 *   renderDataTable(containerEl, columns, rows, { onEdit, editLabel, onDelete, tenXoa, onRowClick })
 */

function renderDataTable(containerEl, columns, rows, { onEdit, editLabel = "Sửa", onDelete, tenXoa, onRowClick } = {}) {
  if (!rows || !rows.length) {
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
    containerEl.querySelectorAll(".nv-table tbody tr").forEach((tr) => {
      tr.addEventListener("click", () => {
        const idx = Number(tr.dataset.idx);
        const row = rows[idx];
        const hangMoRongCu = containerEl.querySelector(".nv-table__chi-tiet");

        if (hangMoRongCu) {
          const laChinhHangNay = hangMoRongCu.previousElementSibling === tr;
          hangMoRongCu.remove();
          containerEl.querySelectorAll(".nv-table tr").forEach((r) => r.classList.remove("mo"));
          if (laChinhHangNay) return;
        }

        tr.classList.add("mo");
        const trChiTiet = document.createElement("tr");
        trChiTiet.className = "nv-table__chi-tiet";
        const td = document.createElement("td");
        td.colSpan = columns.length + (coCotHanhDong ? 1 : 0);
        td.textContent = "Đang tải...";
        trChiTiet.appendChild(td);
        tr.after(trChiTiet);

        onRowClick(row, td);
      });
    });
  }
}
