/* ma-vach.js — Vẽ mã vạch Code128 cho mã vận đơn.
 * Dùng JsBarcode (MIT, bản chỉ có Code128) đặt sẵn trong vendor/ để chạy được cả khi
 * máy quầy không ra được Internet. Mã vận đơn dạng DH-YYYYMMDD-XXXXXX gồm chữ in hoa,
 * số và dấu gạch ngang nên Code128 mã hóa trực tiếp; máy quét USB đọc ra đúng chuỗi đó. */

/** Vẽ mã vạch của `ma` vào thẻ <svg id="svgId">. Lỗi/thiếu thư viện thì ẩn mã vạch, vẫn còn mã chữ để gõ tay. */
function veMaVach(svgId, ma, { chieuCao = 48 } = {}) {
  const svg = document.getElementById(svgId);
  if (!svg) return;
  svg.replaceChildren();
  if (typeof JsBarcode !== "function" || !ma) {
    svg.style.display = "none";
    return;
  }
  try {
    JsBarcode(svg, ma, {
      format: "CODE128",
      width: 2,
      height: chieuCao,
      displayValue: false,
      margin: 0,
      background: "#ffffff",
      lineColor: "#000000",
    });
    // JsBarcode đặt kích thước cố định; đổi sang viewBox để mã vạch co theo khung biên nhận/nhãn.
    const rong = parseFloat(svg.getAttribute("width"));
    const cao = parseFloat(svg.getAttribute("height"));
    if (rong > 0 && cao > 0) svg.setAttribute("viewBox", `0 0 ${rong} ${cao}`);
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.style.width = "";
    svg.style.height = "";
    svg.style.display = "";
  } catch (_) {
    svg.style.display = "none";
  }
}
