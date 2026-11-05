"""Chuyến chưa có xe — UC-44 ⏱ (NGHIEP_VU.md mục 3.3 và 3.5), mỗi 5 phút:

1. NHẮC điều độ viên phụ trách tuyến khi chuyến còn ≤48 tiếng mà chưa gán xe, và nhắc lại một lần nữa ở mức khẩn khi còn ≤6 tiếng.
   Mỗi mức chỉ nhắc 1 lần cho mỗi chu trình (nội dung cố định theo chu trình + mức nên bị bỏ qua nhờ `da_co_thong_bao_giong`).
2. Chuyến đã tới/quá giờ khởi hành (tối đa BU_TOI_DA_GIO giờ trước) mà vẫn chưa có xe → TỰ ĐỘNG chuyển "đang hoãn" (bật `dang_hoan`): khách có vé đã thanh toán được
   hủy nhận hoàn 100% (UC-41), điều độ viên + quản lý được báo, khách có vé được báo. Điều độ viên vẫn gán xe bình thường — gán
   xong thì cờ tự tắt (repo.gan_xe_cho_chu_trinh). Chuyến chỉ được báo 1 lần vì cờ chỉ bật 1 lần.

Lỗi ở một mục chỉ ghi log, không chặn các mục còn lại. Chỉ nhắc/báo — không tự gán xe hay hủy chuyến.
"""

import datetime
import logging
from zoneinfo import ZoneInfo

from app.repositories import dieu_do_repository as repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.repositories import ve_repository as ve_repo
from app.services import dieu_do_service
from app.services import thong_bao_khach_service as thong_bao

logger = logging.getLogger(__name__)
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
# Chỉ chuyển "đang hoãn" chuyến quá giờ trong khoảng này: job chạy 5 phút/lần nên chỉ cần bù lúc dịch vụ tạm ngưng; chuyến quá khứ xa
# hơn (dữ liệu cũ chưa từng gán xe) bỏ qua, không hoãn hàng loạt và không báo khách nhầm.
BU_TOI_DA_GIO = 12


def _gio(thoi_diem: datetime.datetime) -> str:
    return thoi_diem.astimezone(MUI_GIO_VN).strftime("%H:%M %d/%m")


def _theo_chu_trinh(chuyen: list[dict]) -> list[list[dict]]:
    """Gom chuyến theo chu trình (chuyến không có chu_trinh_id tự thành một nhóm), mỗi nhóm theo giờ khởi hành."""
    nhom: dict[str, list[dict]] = {}
    for c in chuyen:
        nhom.setdefault(str(c["chu_trinh_id"] or c["id"]), []).append(c)
    return list(nhom.values())


def noi_dung_nhac(nhom: list[dict], con_lai: datetime.timedelta) -> str:
    """Nội dung nhắc cho 1 chu trình chưa có xe; 2 mức (≤48 giờ / ≤6 giờ) có nội dung khác nhau để mức khẩn được báo thêm 1 lần."""
    dau = nhom[0]
    gio_di = _gio(dau["gio_khoi_hanh"])
    if con_lai <= datetime.timedelta(hours=dieu_do_service.NGUONG_KHAN_CHUA_GAN_XE_GIO):
        return f"KHẨN: chuyến {dau['ma']} ({dau['ten_tuyen']}) khởi hành lúc {gio_di} — còn dưới {dieu_do_service.con_lai_dang_chu(datetime.timedelta(hours=dieu_do_service.NGUONG_KHAN_CHUA_GAN_XE_GIO))} mà chưa gán xe."
    return f"Chuyến {dau['ma']} ({dau['ten_tuyen']}) khởi hành lúc {gio_di} — còn dưới {dieu_do_service.con_lai_dang_chu(datetime.timedelta(hours=dieu_do_service.NGUONG_NHAC_CHUA_GAN_XE_GIO))} mà chưa gán xe."


def _gui_neu_chua_co(nguoi_nhan: list[str], noi_dung: str, duong_dan: str) -> int:
    so = 0
    for nguoi_id in nguoi_nhan:
        if thong_bao_repo.da_co_thong_bao_giong(nguoi_id, noi_dung):
            continue
        thong_bao.gui(nguoi_id, noi_dung, duong_dan=duong_dan)
        so += 1
    return so


def nhac_chua_gan_xe(bay_gio: datetime.datetime) -> int:
    """Trả số thông báo nhắc vừa gửi."""
    gioi_han = bay_gio + datetime.timedelta(hours=dieu_do_service.NGUONG_NHAC_CHUA_GAN_XE_GIO)
    so = 0
    for nhom in _theo_chu_trinh(repo.chuyen_chua_gan_xe_sap_toi(bay_gio, gioi_han)):
        try:
            noi_dung = noi_dung_nhac(nhom, nhom[0]["gio_khoi_hanh"] - bay_gio)
            so += _gui_neu_chua_co(
                dieu_do_service.nguoi_nhan_thong_bao_cua_tuyen(str(nhom[0]["tuyen_id"])), noi_dung, dieu_do_service.duong_dan_chu_trinh(nhom[0]["chu_trinh_id"])
            )
        except Exception:  # noqa: BLE001
            logger.exception("Không nhắc được chu trình chưa gán xe %s", nhom[0]["chu_trinh_id"])
    return so


def chuyen_sang_dang_hoan(bay_gio: datetime.datetime) -> int:
    """Trả số chuyến vừa chuyển sang đang hoãn."""
    vua_hoan = repo.danh_dau_dang_hoan_chuyen_qua_gio(bay_gio, bay_gio - datetime.timedelta(hours=BU_TOI_DA_GIO))
    for c in vua_hoan:
        try:
            noi_dung = f"Chuyến {c['ma']} ({c['ten_tuyen']}, {_gio(c['gio_khoi_hanh'])}) đã quá giờ khởi hành mà chưa có xe — chuyến chuyển sang ĐANG HOÃN, cần gán xe ngay."
            nguoi_nhan = set(dieu_do_service.nguoi_nhan_thong_bao_cua_tuyen(str(c["tuyen_id"])))
            nguoi_nhan.update(nguoi_dung_repo.danh_sach_id_theo_vai_tro("quan_ly", chi_dang_hoat_dong=True))
            for nguoi_id in nguoi_nhan:
                thong_bao.gui(nguoi_id, noi_dung, duong_dan=dieu_do_service.duong_dan_chu_trinh(c["chu_trinh_id"]))
            khach_noi_dung = (
                f"Chuyến {c['ma']} lúc {_gio(c['gio_khoi_hanh'])} đang hoãn do nhà xe chưa bố trí được xe. "
                "Bạn có thể hủy vé nhận hoàn 100% hoặc chờ chuyến chạy theo giờ mới."
            )
            for khach in ve_repo.tim_khach_hang_dang_hoat_dong_theo_chuyen(str(c["id"])):
                thong_bao.gui(khach["khach_hang_id"], khach_noi_dung)
        except Exception:  # noqa: BLE001
            logger.exception("Không báo được chuyến đang hoãn %s", c["id"])
    return len(vua_hoan)


def chay(bay_gio: datetime.datetime | None = None) -> tuple[int, int]:
    """Trả (số thông báo nhắc, số chuyến vừa chuyển đang hoãn). Chuyển đang hoãn chạy TRƯỚC để chuyến vừa quá giờ không bị nhắc
    "còn dưới 6 giờ" nữa (nhắc chỉ xét chuyến chưa hoãn, khởi hành sau bây giờ)."""
    bay_gio = bay_gio or datetime.datetime.now(datetime.timezone.utc)
    so_hoan = chuyen_sang_dang_hoan(bay_gio)
    so_nhac = nhac_chua_gan_xe(bay_gio)
    return so_nhac, so_hoan
