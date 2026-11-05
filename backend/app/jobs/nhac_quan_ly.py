"""Nhắc QUẢN LÝ những việc phải làm trước khi hết (⏱, mỗi ngày 1 lần): sinh thêm chuyến cho cặp lịch chạy đang áp dụng,
tạo bộ giá vé nối tiếp. Quản lý tự bấm "Sinh chuyến" (UC-47, không có job nền tự sinh) nên cần được nhắc sớm.

Chỉ NHẮC — không tự sinh chuyến hay tạo giá (cùng nguyên tắc quet_hang_ton, canh_bao_giay_to). Mỗi tình trạng chỉ nhắc 1 lần
cho mỗi quản lý: nội dung nhắc luôn chứa ngày cuối cùng nên giữ nguyên khi tình trạng không đổi (bị bỏ qua nhờ
`da_co_thong_bao_giong`), còn khi quản lý sinh thêm chuyến / tạo thêm bộ giá thì ngày đổi và lần sau (nếu lại sắp hết) là
thông báo mới. Thông báo kèm đường dẫn để bấm vào mở đúng trang Lịch chạy / Giá vé.
"""

import datetime
import logging
from zoneinfo import ZoneInfo

from app.config import NGUONG_NHAC_BO_GIA_NGAY, NGUONG_NHAC_SINH_CHUYEN_NGAY
from app.repositories import lich_chay_repository
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.services import gia_ve_service
from app.services import thong_bao_khach_service as thong_bao

logger = logging.getLogger(__name__)
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")

DUONG_DAN_LICH_CHAY = "/nhan-vien/quan-ly/lich-chay.html"
DUONG_DAN_GIA_VE = "/nhan-vien/quan-ly/gia-ve.html"


def _ngay(ngay: datetime.date) -> str:
    return ngay.strftime("%d/%m/%Y")


def noi_dung_nhac_sinh_chuyen(
    cap: dict, hom_nay: datetime.date, nguong_ngay: int = NGUONG_NHAC_SINH_CHUYEN_NGAY
) -> str | None:
    """Nội dung nhắc cho 1 cặp lịch đang áp dụng; None nếu chuyến còn đủ dài. `cap`: ten_tuyen, gio_di, gio_ve, ngay_chuyen_cuoi."""
    ngay_cuoi = cap["ngay_chuyen_cuoi"]
    ten = f'{cap["ten_tuyen"]} (đi {cap["gio_di"]:%H:%M} / về {cap["gio_ve"]:%H:%M})'
    if ngay_cuoi is None:
        return f"Lịch chạy {ten} chưa sinh chuyến nào — hãy sinh chuyến để khách đặt được vé."
    if ngay_cuoi < hom_nay:
        return f"Lịch chạy {ten} đã hết chuyến từ ngày {_ngay(ngay_cuoi)} — hãy sinh thêm chuyến."
    if (ngay_cuoi - hom_nay).days <= nguong_ngay:
        return f"Lịch chạy {ten} chỉ còn chuyến đến ngày {_ngay(ngay_cuoi)} — hãy sinh thêm chuyến."
    return None


def noi_dung_nhac_bo_gia(
    ten_tuyen: str, khoang_gia: tuple[datetime.date, datetime.date] | None, hom_nay: datetime.date,
    nguong_ngay: int = NGUONG_NHAC_BO_GIA_NGAY,
) -> str | None:
    """Nội dung nhắc cho 1 tuyến có lịch đang áp dụng; None nếu bộ giá còn đủ dài. `khoang_gia`: gia_ve_service.khoang_ngay_co_gia."""
    if khoang_gia is None:
        return f"Tuyến {ten_tuyen} chưa có bộ giá vé nào nên chưa sinh được chuyến — hãy tạo bộ giá."
    ngay_cuoi = khoang_gia[1]
    if ngay_cuoi < hom_nay:
        return f"Bộ giá vé tuyến {ten_tuyen} đã kết thúc ngày {_ngay(ngay_cuoi)} — hãy tạo bộ giá nối tiếp để sinh được chuyến mới."
    if (ngay_cuoi - hom_nay).days <= nguong_ngay:
        return f"Bộ giá vé tuyến {ten_tuyen} sẽ kết thúc ngày {_ngay(ngay_cuoi)} — hãy tạo bộ giá nối tiếp."
    return None


def _gui_cho_cac_quan_ly(nguoi_nhan: list[str], noi_dung: str, duong_dan: str) -> bool:
    """Gửi cho từng quản lý chưa nhận đúng nội dung này gần đây. True nếu có ít nhất 1 người được gửi mới."""
    da_gui = False
    for nguoi_id in nguoi_nhan:
        if thong_bao_repo.da_co_thong_bao_giong(nguoi_id, noi_dung):
            continue
        thong_bao.gui(nguoi_id, noi_dung, duong_dan=duong_dan)
        da_gui = True
    return da_gui


def chay(hom_nay: datetime.date | None = None) -> tuple[int, int]:
    """Trả (số cặp lịch vừa nhắc sinh chuyến, số tuyến vừa nhắc bộ giá). Lỗi ở 1 mục chỉ ghi log, không chặn các mục còn lại."""
    hom_nay = hom_nay or datetime.datetime.now(MUI_GIO_VN).date()
    nguoi_nhan = nguoi_dung_repo.danh_sach_id_theo_vai_tro("quan_ly", chi_dang_hoat_dong=True)
    if not nguoi_nhan:
        return 0, 0

    cac_cap = lich_chay_repository.cac_cap_dang_ap_dung_kem_ngay_chuyen_cuoi()

    so_nhac_chuyen = 0
    for cap in cac_cap:
        try:
            noi_dung = noi_dung_nhac_sinh_chuyen(cap, hom_nay)
            if noi_dung and _gui_cho_cac_quan_ly(nguoi_nhan, noi_dung, DUONG_DAN_LICH_CHAY):
                so_nhac_chuyen += 1
        except Exception:  # noqa: BLE001
            logger.exception("Không nhắc được sinh chuyến cho cặp lịch %s", cap.get("cap_id"))

    ten_theo_tuyen: dict[str, str] = {}
    for cap in cac_cap:
        ten_theo_tuyen.setdefault(str(cap["tuyen_id"]), cap["ten_tuyen"])
    so_nhac_gia = 0
    for tuyen_id, ten_tuyen in ten_theo_tuyen.items():
        try:
            noi_dung = noi_dung_nhac_bo_gia(ten_tuyen, gia_ve_service.khoang_ngay_co_gia(tuyen_id), hom_nay)
            if noi_dung and _gui_cho_cac_quan_ly(nguoi_nhan, noi_dung, DUONG_DAN_GIA_VE):
                so_nhac_gia += 1
        except Exception:  # noqa: BLE001
            logger.exception("Không nhắc được bộ giá cho tuyến %s", tuyen_id)

    return so_nhac_chuyen, so_nhac_gia
