"""Giá bán vé = giá gốc (bộ giá) × hệ số giá của chuyến, làm tròn tới bội số của BUOC_LAM_TRON (NGHIEP_VU.md mục 3.1).
Mọi chỗ tính giá bán (tìm kiếm, chi tiết chuyến, giữ ghế) phải đi qua `tinh_gia_ban` để cùng ra một con số.
Hệ số ghế (`chuyen_xe.he_so_ghe`, dạng {mã ghế: hệ số}, ghế vắng mặt = 1) cũng được chốt vào chuyến lúc sinh chuyến."""

from decimal import ROUND_HALF_UP, Decimal

BUOC_LAM_TRON = 10_000  # đ


def tinh_gia_ban(gia_goc, he_so_gia, he_so_ghe=1) -> int:
    """gia_goc × hệ số của chuyến × hệ số của ghế, làm tròn MỘT LẦN ở cuối (không làm tròn từng bước) nửa-lên tới bội số
    của BUOC_LAM_TRON, tối thiểu 1 bước (không để giá bán về 0)."""
    gia = Decimal(gia_goc) * Decimal(str(he_so_gia)) * Decimal(str(he_so_ghe))
    so_buoc = (gia / BUOC_LAM_TRON).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(max(so_buoc, Decimal(1))) * BUOC_LAM_TRON


def gia_theo_ghe(gia_goc, he_so_gia, cac_ma_ghe, he_so_ghe: dict | None) -> dict[str, int]:
    """Giá bán của từng ghế: {mã ghế: giá}. `he_so_ghe` có thể thiếu ghế (= hệ số 1)."""
    he_so_ghe = he_so_ghe or {}
    return {ma: tinh_gia_ban(gia_goc, he_so_gia, he_so_ghe.get(ma, 1)) for ma in cac_ma_ghe}
