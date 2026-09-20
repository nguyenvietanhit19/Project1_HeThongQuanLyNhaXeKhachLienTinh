/*
 * Combo tìm kiếm dùng chung: 1 ô nhập gõ được để lọc/tìm (kèm <datalist>
 * gợi ý) + 1 ô ẩn giữ đúng ID thực của mục đã chọn — dùng khi số lượng lựa
 * chọn có thể nhiều, duyệt <select> thường sẽ khó tìm (VD chọn khu vực khi
 * tạo điểm đón/trả, nếu hệ thống có hàng trăm khu vực).
 *
 *   const combo = khoiTaoComboTimKiem(inputEl, hiddenIdEl, dsMuc, { hienThi });
 *   - dsMuc: [{ id, ... }] — danh sách mục để tìm
 *   - hienThi(muc): trả về chuỗi hiển thị + dùng để tìm (phải là duy nhất)
 *   - combo.hopLe(): true nếu giá trị đang gõ khớp đúng 1 mục có thật
 *   - combo.chon(id): đặt sẵn giá trị theo ID (dùng khi mở form sửa)
 *   - combo.xoa(): xóa trắng
 */

function khoiTaoComboTimKiem(inputEl, hiddenIdEl, dsMuc, { hienThi }) {
  const datalistId = `${inputEl.id}-goi-y`;
  let datalist = document.getElementById(datalistId);
  if (!datalist) {
    datalist = document.createElement("datalist");
    datalist.id = datalistId;
    inputEl.after(datalist);
    inputEl.setAttribute("list", datalistId);
    inputEl.setAttribute("autocomplete", "off");
  }

  const idTheoText = new Map();
  datalist.innerHTML = dsMuc
    .map((muc) => {
      const text = hienThi(muc);
      idTheoText.set(text, muc.id);
      return `<option value="${text}"></option>`;
    })
    .join("");

  function dongBoIdAn() {
    hiddenIdEl.value = idTheoText.get(inputEl.value) || "";
  }

  inputEl.addEventListener("input", dongBoIdAn);

  return {
    hopLe: () => idTheoText.has(inputEl.value),
    chon(id) {
      const muc = dsMuc.find((m) => m.id === id);
      if (muc) {
        inputEl.value = hienThi(muc);
        hiddenIdEl.value = id;
      }
    },
    xoa() {
      inputEl.value = "";
      hiddenIdEl.value = "";
    },
  };
}
