"""Cảnh báo giấy tờ nhân sự vận hành sắp/đã hết hạn (⏱) — nhánh kèm theo
UC-49 (trước đây là UC-50 riêng), NGHIEP_VU.md mục 8.9 điểm 5, mục 12.

Không phải use case riêng của actor nào (⏱, không nối actor trên sơ đồ use
case — UML_DIAGRAMS.md mục 1.8) — chạy định kỳ mỗi ngày 1 lần (mốc tính theo
ngày nên không cần quét 1 phút như các job khác, ARCHITECTURE.md mục 5).

Chỉ nhắc con người xử lý — KHÔNG tự khóa tài khoản, gỡ biên chế hay chặn gán
xe (cùng nguyên tắc UC-46, quet_hang_ton).
"""

import logging

from app.config import NGUONG_CANH_BAO_GIAY_TO_NGAY
from app.repositories import giay_to_nhan_su_repository as giay_to_repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.services import thong_bao_khach_service as thong_bao

logger = logging.getLogger(__name__)

# Tên hiển thị trong nội dung thông báo (tránh hiện mã "bang_lai" cho người dùng).
TEN_GIAY_TO = {"bang_lai": "bằng lái", "giay_kham_suc_khoe": "giấy khám sức khỏe"}


def _nguoi_nhan() -> list[str]:
    """Mọi quan_ly_nhan_su đang hoạt động; không có ai thì gửi cho quan_ly
    (NGHIEP_VU.md UC-49, luồng rẽ nhánh)."""
    ds = nguoi_dung_repo.danh_sach_id_theo_vai_tro("quan_ly_nhan_su", chi_dang_hoat_dong=True)
    return ds or nguoi_dung_repo.danh_sach_id_theo_vai_tro("quan_ly", chi_dang_hoat_dong=True)


def chay(nguong_ngay: int = NGUONG_CANH_BAO_GIAY_TO_NGAY) -> tuple[int, int]:
    """Trả (số giấy tờ sắp hết hạn vừa cảnh báo, số giấy tờ đã hết hạn vừa cảnh báo)."""
    # Quy trình: lấy người nhận -> cảnh báo "sắp hết hạn" -> cảnh báo "đã hết hạn".
    # Mỗi giấy tờ chỉ nhắc 1 lần cho mỗi mốc nhờ cờ da_canh_bao_* trong DB
    # (job chạy mỗi ngày nhưng không spam). Gia hạn giấy tờ -> cờ reset -> nhắc lại.
    nguoi_nhan = _nguoi_nhan()

    # Mốc 1: giấy tờ còn <= nguong_ngay ngày nữa là hết hạn
    sap_het_han = giay_to_repo.can_canh_bao_sap_het_han(nguong_ngay)
    for gt in sap_het_han:
        noi_dung = (
            f'Giấy tờ sắp hết hạn: {TEN_GIAY_TO.get(gt["loai"], gt["loai"])} của {gt["ho_ten"]} '
            f'hết hạn ngày {gt["ngay_het_han"]:%d/%m/%Y}.'
        )
        for nd_id in nguoi_nhan:
            thong_bao.gui(nd_id, noi_dung)
        # Gửi xong mới đánh dấu để lần chạy sau không nhắc lại
        giay_to_repo.danh_dau_da_canh_bao_sap_het_han(gt["id"])


    # Mốc 2: giấy tờ đã quá hạn (nội dung gắn nhãn [KHẨN])
    da_het_han = giay_to_repo.can_canh_bao_da_het_han()
    for gt in da_het_han:
        noi_dung = (
            f'[KHẨN] Giấy tờ đã hết hạn: {TEN_GIAY_TO.get(gt["loai"], gt["loai"])} của {gt["ho_ten"]} '
            f'đã hết hạn ngày {gt["ngay_het_han"]:%d/%m/%Y}.'
        )
        for nd_id in nguoi_nhan:
            thong_bao.gui(nd_id, noi_dung)
        giay_to_repo.danh_dau_da_canh_bao_het_han(gt["id"])

    if sap_het_han or da_het_han:
        logger.info("Cảnh báo giấy tờ: %d sắp hết hạn, %d đã hết hạn", len(sap_het_han), len(da_het_han))
    return len(sap_het_han), len(da_het_han)
