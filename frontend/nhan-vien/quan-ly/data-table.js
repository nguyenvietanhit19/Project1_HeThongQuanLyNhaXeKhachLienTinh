/*
 * renderDataTable — component viết tay dùng cho các trang danh mục trong
 * frontend/nhan-vien/quan-ly/. Không dùng framework, chỉ render lại
 * innerHTML. Riêng của domain Quản lý — vai trò khác cần bảng tương tự thì
 * tự viết bản của họ, không import file này.
 *
 *   renderDataTable(containerEl, columns, rows, { onEdit, editLabel, onDelete, tenXoa, onRowClick, extraActions })
 *   - columns: [{ key, label, render?(row) }]
 *   - extraActions: optional — [{ label: string | (row) => string, onClick(row) }] nút
 *     hành động thêm, đặt TRƯỚC nút Sửa (VD "Biên chế", "Ngừng áp dụng")
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

function renderDataTable(containerEl, columns, rows, { onEdit, editLabel = "Sửa", onDelete, tenXoa, onRowClick, extraActions = [] } = {}) {
  if (!rows.length) {
    containerEl.innerHTML = '<div class="nv-table__empty">Chưa có dữ liệu</div>';
    return;
  }

  const coCotHanhDong = onEdit || onDelete || extraActions.length;
  const soCot = columns.length + (coCotHanhDong ? 1 : 0);
  const theadCols = columns.map((c) => `<th>${c.label}</th>`).join("") + (coCotHanhDong ? "<th></th>" : "");

  const tbodyRows = rows
    .map((row, idx) => {
      const tds = columns.map((c) => `<td>${c.render ? c.render(row) : (row[c.key] ?? "")}</td>`).join("");
      const nutSua = onEdit ? `<button class="nv-btn-sua" data-idx="${idx}" type="button">${editLabel}</button>` : "";
      const nutXoa = onDelete ? `<button class="nv-btn-xoa" data-idx="${idx}" type="button">Xóa</button>` : "";
      const nutPhu = extraActions
        .map((a, i) => `<button class="nv-btn-phu" data-extra="${i}" data-idx="${idx}" type="button">${typeof a.label === "function" ? a.label(row) : a.label}</button>`)
        .join("");
      const actionTd = coCotHanhDong ? `<td style="text-align:right"><div class="nv-hang-hanh-dong">${nutPhu}${nutSua}${nutXoa}</div></td>` : "";
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

  containerEl.querySelectorAll(".nv-btn-phu").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      extraActions[Number(btn.dataset.extra)].onClick(rows[Number(btn.dataset.idx)]);
    });
  });

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
