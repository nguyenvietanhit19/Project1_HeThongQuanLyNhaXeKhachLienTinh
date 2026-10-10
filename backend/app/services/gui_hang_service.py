"""Quy tắc nghiệp vụ Gửi hàng — NGHIEP_VU.md mục 10 & ma trận UC (UC-23, 24, 25, 26, 27, 28, 39, 46).

Service quản lý vòng đời đơn hàng gửi theo tuyến:
- Tạo đơn, cân đo, nhập cước, chặn hàng cấm (UC-23).
- Giao hàng cho người nhận, kiểm tra thu COD (UC-24).
- Xử lý hàng chờ quá lâu tại điểm nhận (UC-25) + job cảnh báo (UC-46).
- Hàm cho Phụ xe chất/dỡ hàng, báo sự cố (UC-26, UC-27, UC-28).
- Thống kê & đối soát tiền tại văn phòng (UC-39).
"""

import logging
from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import don_hang_repository as don_hang_repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.schemas.don_hang_schema import TRUONG_LIEN_HE, SuaThongTinLienHeRequest, TaoDonHangRequest
from app.services import chuyen_xe_service
from app.services.chuyen_xe_service import diem_hien_tai, lay_chuyen_cua_phu_xe
from app.services.websocket_manager import broadcast_sync
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay, LoiHeThong

logger = logging.getLogger(__name__)

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
SO_LAN_THU_SINH_MA = 3
SO_NGAY_THONG_KE_TOI_DA = 366


def _gui_thong_bao(nguoi_nhan_id: str, noi_dung: str, don_hang_id: str | None = None) -> None:
    """Ghi vào DB TRƯỚC (người nhận offline vẫn đọc lại được, DATABASE.md mục 6.1)
    rồi mới đẩy real-time — đúng thứ tự websocket_manager.py yêu cầu."""
    thong_bao_repo.tao(nguoi_nhan_id, noi_dung, don_hang_id=don_hang_id)
    broadcast_sync(nguoi_nhan_id, noi_dung)


def _gui_thong_bao_an_toan(nguoi_nhan_ids: list[str], noi_dung: str, don_hang_id: str) -> None:
    """Thông báo là phần phụ của thao tác chính (dỡ hàng, báo sự cố) — thao tác
    chính đã commit thì lỗi gửi thông báo chỉ ghi log, không trả lỗi cho người dùng."""
    for nguoi_nhan_id in nguoi_nhan_ids:
        try:
            _gui_thong_bao(nguoi_nhan_id, noi_dung, don_hang_id)
        except Exception:  # noqa: BLE001
            logger.exception("Không gửi được thông báo đơn %s tới %s", don_hang_id, nguoi_nhan_id)


def _kiem_tra_don_thuoc_van_phong(don: dict, van_phong_id: str | None, chi_diem_nhan: bool = False) -> None:
    """van_phong_id None = quản lý (toàn hệ thống). Nhân viên chỉ thao tác đơn
    có điểm gửi/nhận là văn phòng mình (mục 8.5)."""
    if not van_phong_id:
        return
    cac_diem = (str(don["diem_nhan_id"]),) if chi_diem_nhan else (str(don["diem_gui_id"]), str(don["diem_nhan_id"]))
    if str(van_phong_id) not in cac_diem:
        raise CamTruyCap("Đơn hàng không thuộc văn phòng phụ trách")


def _kiem_tra_khoang_ngay(tu_ngay: date, den_ngay: date) -> None:
    if tu_ngay > den_ngay:
        raise GiaTriLoi("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
    if (den_ngay - tu_ngay).days >= SO_NGAY_THONG_KE_TOI_DA:
        raise GiaTriLoi("Khoảng thống kê tối đa 1 năm")


# ====================================================================
# 1. Tạo đơn gửi hàng tại quầy (UC-23)
# ====================================================================

def _sinh_ma_van_don() -> str:
    """Sinh mã vận đơn ngẫu nhiên dễ đọc, vd: DH-20260920-A1B2C3 (ngày theo giờ Việt Nam)."""
    ngay = datetime.now(MUI_GIO_VN).strftime("%Y%m%d")
    ngau_nhien = uuid4().hex[:6].upper()
    return f"DH-{ngay}-{ngau_nhien}"


def lay_danh_sach_loai_hang() -> list[dict]:
    """Danh mục loại hàng (gồm cả hàng cấm, để giao diện hiển thị & từ chối đúng UC-23 bước 5)."""
    return don_hang_repo.lay_danh_sach_loai_hang()


def gan_van_phong_can_bo(nguoi_dung_id: str, van_phong_id: str) -> None:
    """Chỉ gán hồ sơ văn phòng cho các vai trò nhân viên có phạm vi theo điểm."""
    can_bo = nguoi_dung_repo.tim_theo_id(nguoi_dung_id)
    if not can_bo or can_bo["vai_tro"] not in ("nhan_vien_quay_ve", "nhan_vien_gui_hang", "dieu_do_vien"):
        raise GiaTriLoi("Tài khoản không thuộc nhóm cán bộ cần gán văn phòng")
    van_phong = dia_diem_repo.tim_diem_don_tra_theo_id(van_phong_id)
    if not van_phong or van_phong.get("loai") != "van_phong":
        raise GiaTriLoi("Điểm phụ trách phải là văn phòng hợp lệ")
    nguoi_dung_repo.gan_van_phong(nguoi_dung_id, van_phong_id)


def lay_van_phong(van_phong_id: str) -> dict:
    van_phong = dia_diem_repo.tim_diem_don_tra_theo_id(van_phong_id)
    if not van_phong:
        raise KhongTimThay("Văn phòng phụ trách không tồn tại")
    return {
        "id": str(van_phong["id"]),
        "ten": van_phong["ten"],
        "dia_chi": van_phong.get("dia_chi"),
        "sdt_lien_he": van_phong.get("sdt_lien_he"),
    }


def lay_diem_nhan_kha_dung(van_phong_gui_id: str) -> list[dict]:
    """UC-23 bước 2 / mục 10.4.1 bước 3: danh sách 2 tầng khu_vực → văn phòng nhận,
    chỉ gồm văn phòng có ít nhất 1 tuyến chung với văn phòng gửi."""
    nhom: dict[str, dict] = {}
    for vp in don_hang_repo.danh_sach_diem_nhan_kha_dung(van_phong_gui_id):
        khu_vuc_id = str(vp["khu_vuc_id"])
        if khu_vuc_id not in nhom:
            nhom[khu_vuc_id] = {
                "khu_vuc_id": khu_vuc_id,
                "ten_khu_vuc": vp["ten_khu_vuc"],
                "tinh_thanh": vp.get("tinh_thanh"),
                "van_phong": [],
            }
        nhom[khu_vuc_id]["van_phong"].append({"id": str(vp["id"]), "ten": vp["ten"], "dia_chi": vp.get("dia_chi")})
    return list(nhom.values())


def lay_tuyen_phu_hop(diem_gui_id: str, diem_nhan_id: str) -> list[dict]:
    """UC-23 bước 3: các tuyến đi qua cả điểm gửi và điểm nhận (nhiều tuyến thì nhân viên chọn 1)."""
    return don_hang_repo.tim_cac_tuyen_qua_hai_diem(diem_gui_id, diem_nhan_id)


def tao_don_hang(
    du_lieu: TaoDonHangRequest,
    nhan_vien_id: str,
    diem_gui_id: str | None = None,
    khoa_chong_trung: str | None = None,
) -> dict:
    """UC-23: Nhận hàng tại quầy, tạo đơn `cho_van_chuyen` gắn tuyến (chưa gắn chuyến).

    - Chặn hàng cấm (bước 5).
    - Điểm gửi và nhận bắt buộc là văn phòng, khác nhau (mục 10.1).
    - Tuyến phải đi qua cả 2 điểm (tuyến 2 chiều).
    - Trả trước phải xác nhận đã thu; COD không được ghi nhận thu ở điểm gửi.
    """
    # Gửi lại cùng khóa (bấm 2 lần, mạng chậm, F5) → trả đơn đã tạo, không tạo đơn thứ hai.
    if khoa_chong_trung:
        don_da_tao = don_hang_repo.tim_theo_khoa_chong_trung(nhan_vien_id, khoa_chong_trung)
        if don_da_tao:
            return don_da_tao

    loai_hang = don_hang_repo.tim_loai_hang_theo_id(str(du_lieu.loai_hang_id))
    if not loai_hang:
        raise GiaTriLoi("Loại hàng hóa không tồn tại trong hệ thống")
    if loai_hang["la_hang_cam"]:
        raise GiaTriLoi(f"Mặt hàng '{loai_hang['ten']}' thuộc danh mục cấm vận chuyển, từ chối tiếp nhận")

    # Với nhân viên, điểm gửi lấy từ hồ sơ BE — không tin giá trị client gửi lên.
    diem_gui_id = diem_gui_id or str(du_lieu.diem_gui_id)
    if str(du_lieu.diem_gui_id) != diem_gui_id:
        raise GiaTriLoi("Văn phòng gửi không khớp với văn phòng được phân công")
    diem_gui = dia_diem_repo.tim_diem_don_tra_theo_id(diem_gui_id)
    if not diem_gui:
        raise GiaTriLoi("Điểm gửi không tồn tại")
    if diem_gui["loai"] != "van_phong":
        raise GiaTriLoi("Điểm gửi phải là văn phòng có nhân viên tiếp nhận")

    diem_nhan = dia_diem_repo.tim_diem_don_tra_theo_id(str(du_lieu.diem_nhan_id))
    if not diem_nhan:
        raise GiaTriLoi("Điểm nhận không tồn tại")
    if diem_nhan["loai"] != "van_phong":
        raise GiaTriLoi("Điểm nhận phải là văn phòng để lưu kho và bàn giao cho người nhận")

    if str(du_lieu.diem_gui_id) == str(du_lieu.diem_nhan_id):
        raise GiaTriLoi("Điểm nhận không được trùng với điểm gửi")

    if du_lieu.phuong_thuc_thanh_toan == "nguoi_gui_tra_truoc" and not du_lieu.xac_nhan_da_thu:
        raise GiaTriLoi("Cần xác nhận đã thu cước từ người gửi")
    if du_lieu.phuong_thuc_thanh_toan == "cod_nguoi_nhan_tra" and du_lieu.xac_nhan_da_thu:
        raise GiaTriLoi("Đơn COD chưa được thu tiền tại điểm gửi")

    tuyen = dia_diem_repo.tim_tuyen_theo_id(str(du_lieu.tuyen_id))
    if not tuyen:
        raise GiaTriLoi("Tuyến xe gửi hàng không tồn tại")
    if not don_hang_repo.kiem_tra_diem_thuoc_tuyen(
        str(du_lieu.tuyen_id), str(du_lieu.diem_gui_id), str(du_lieu.diem_nhan_id)
    ):
        raise GiaTriLoi("Tuyến xe được chọn không đi qua điểm gửi hoặc điểm nhận đã chọn")

    payload = {
        "tuyen_id": str(du_lieu.tuyen_id),
        "diem_gui_id": diem_gui_id,
        "diem_nhan_id": str(du_lieu.diem_nhan_id),
        "loai_hang_id": str(du_lieu.loai_hang_id),
        "can_nang_kg": du_lieu.can_nang_kg,
        "dai_cm": du_lieu.dai_cm,
        "rong_cm": du_lieu.rong_cm,
        "cao_cm": du_lieu.cao_cm,
        "gia_cuoc": du_lieu.gia_cuoc,
        "ten_nguoi_gui": du_lieu.ten_nguoi_gui,
        "sdt_nguoi_gui": du_lieu.sdt_nguoi_gui,
        "ten_nguoi_nhan": du_lieu.ten_nguoi_nhan,
        "sdt_nguoi_nhan": du_lieu.sdt_nguoi_nhan,
        "phuong_thuc_thanh_toan": du_lieu.phuong_thuc_thanh_toan,
        "nhan_vien_gui_id": nhan_vien_id,
        "da_thu_tien": du_lieu.xac_nhan_da_thu,
        "nhan_vien_thu_id": nhan_vien_id if du_lieu.xac_nhan_da_thu else None,
        "khoa_chong_trung": khoa_chong_trung,
    }

    # Mã 6 ký tự hex ngẫu nhiên có thể trùng (rất hiếm) — sinh lại và thử tối đa 3 lần.
    for _ in range(SO_LAN_THU_SINH_MA):
        try:
            return don_hang_repo.tao_don_hang({**payload, "ma_van_don": _sinh_ma_van_don()})
        except don_hang_repo.MaVanDonDaTonTai:
            continue
    raise LoiHeThong("Không sinh được mã vận đơn, vui lòng thử lại")


# ====================================================================
# 2. Giao hàng cho người nhận & Thu COD (UC-24)
# ====================================================================

def xac_nhan_giao_hang(
    ma_van_don: str,
    nhan_vien_nhan_id: str,
    van_phong_id: str | None = None,
    xac_nhan_da_thu: bool = False,
) -> dict:
    """UC-24: Bàn giao hàng cho người nhận tại quầy.

    - Chỉ văn phòng NHẬN của đơn được giao.
    - Đơn phải ở `cho_lay`, hoặc `qua_han_luu_kho` khi người nhận tới lấy theo
      thỏa thuận UC-25 (hàng tồn không tự hủy, mục 10.3.1 điểm 4).
    - COD: nhân viên phải xác nhận đã thu đủ trước khi giao (10.4.2 bước 4).
    """
    don = don_hang_repo.tim_theo_ma_van_don(ma_van_don.strip().upper())
    if not don:
        raise KhongTimThay(f"Không tìm thấy đơn hàng với mã vận đơn: {ma_van_don}")

    if van_phong_id and str(don["diem_nhan_id"]) != str(van_phong_id):
        raise CamTruyCap("Đơn hàng thuộc văn phòng nhận khác")

    if don["trang_thai"] == "da_giao":
        raise GiaTriLoi("Đơn hàng này đã được giao cho người nhận trước đó")

    if don["trang_thai"] in ("cho_van_chuyen", "da_len_xe"):
        raise GiaTriLoi("Đơn hàng đang trong quá trình luân chuyển, chưa tới điểm nhận để giao")

    if don["trang_thai"] not in ("cho_lay", "qua_han_luu_kho"):
        raise GiaTriLoi(f"Trạng thái đơn hàng '{don['trang_thai']}' không hợp lệ để giao")

    if don["phuong_thuc_thanh_toan"] == "cod_nguoi_nhan_tra" and not xac_nhan_da_thu:
        raise GiaTriLoi("Xác nhận đã thu đủ cước COD trước khi giao hàng")
    if don["phuong_thuc_thanh_toan"] == "nguoi_gui_tra_truoc" and not don.get("da_thu_tien"):
        raise GiaTriLoi("Đơn chưa có ghi nhận đã thu cước")

    don_cap_nhat = don_hang_repo.cap_nhat_giao_hang(
        don["id"], nhan_vien_nhan_id, van_phong_id=van_phong_id,
        xac_nhan_da_thu=xac_nhan_da_thu and don["phuong_thuc_thanh_toan"] == "cod_nguoi_nhan_tra",
    )
    if not don_cap_nhat:
        raise GiaTriLoi("Đơn hàng vừa được xử lý bởi người khác, vui lòng tải lại")

    return don_cap_nhat


# ====================================================================
# 3. Tra cứu Đơn hàng (công khai + nội bộ)
# ====================================================================

def tra_cuu_theo_ma_van_don(ma_van_don: str) -> dict:
    """Tra cứu chi tiết đơn hàng theo mã vận đơn."""
    don = don_hang_repo.tim_theo_ma_van_don(ma_van_don.strip().upper())
    if not don:
        raise KhongTimThay(f"Không tìm thấy đơn hàng với mã vận đơn: {ma_van_don}")
    return don


def tra_cuu_noi_bo(ma_van_don: str, van_phong_id: str | None) -> dict:
    """Nhân viên chỉ xem được đơn có điểm gửi hoặc điểm nhận là văn phòng mình."""
    don = tra_cuu_theo_ma_van_don(ma_van_don)
    _kiem_tra_don_thuoc_van_phong(don, van_phong_id)
    return don


def tra_cuu_theo_sdt(sdt: str, van_phong_id: str | None = None, muc_dich: str = "tat_ca") -> list[dict]:
    """Tra theo SĐT. muc_dich='giao': chỉ đơn chờ giao tại văn phòng này, khớp SĐT
    người nhận — dùng khi người nhận quên mã vận đơn (mục 10.3.1 điểm 5)."""
    return don_hang_repo.tim_theo_sdt(sdt.strip(), van_phong_id, chi_cho_giao=(muc_dich == "giao"))


def lay_danh_sach_don(
    van_phong_id: str | None,
    huong: str = "tat_ca",
    trang_thai: str | None = None,
    phuong_thuc_thanh_toan: str | None = None,
    tu_khoa: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    items, total = don_hang_repo.lay_danh_sach_don(
        van_phong_id=van_phong_id,
        huong=huong,
        trang_thai=trang_thai,
        phuong_thuc_thanh_toan=phuong_thuc_thanh_toan,
        tu_khoa=tu_khoa,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total}


# ====================================================================
# 4. Hỗ trợ Phụ xe: Chất / Dỡ hàng & Báo sự cố (UC-26, UC-27, UC-28)
# ====================================================================

TRANG_THAI_CHUYEN_DUOC_CHAT = ("chua_khoi_hanh", "dang_chay")
# 'hoan_thanh' vẫn được dỡ: xác nhận tới điểm CUỐI chuyển chuyến sang
# hoan_thanh (mục 8.2 điểm 8) nhưng hàng tới đúng điểm cuối vẫn cần dỡ nốt.
TRANG_THAI_CHUYEN_DUOC_DO = ("chua_khoi_hanh", "dang_chay", "hoan_thanh")


def _chuyen_cua_phu_xe_dang_hoat_dong(chuyen_id: str, nguoi_dung_id: str, trang_thai_hop_le: tuple) -> dict:
    """Chuyến phải thuộc biên chế xe của phụ xe đang thao tác (mục 3.2) và
    đang ở trạng thái cho phép chất/dỡ hàng."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in trang_thai_hop_le:
        raise GiaTriLoi(f"Chuyến đang ở trạng thái '{chuyen['trang_thai']}', không thể thao tác hàng")
    return chuyen


def _gan_so_bao_cao(danh_sach: list[dict]) -> list[dict]:
    """Gắn so_bao_hu_hong / so_bao_that_lac vào từng đơn để giao diện hiện nhãn cảnh báo."""
    dem = don_hang_repo.dem_bao_cao_theo_loai([d["id"] for d in danh_sach])
    for d in danh_sach:
        so = dem.get(d["id"], {})
        d["so_bao_hu_hong"] = so.get("hu_hong", 0)
        d["so_bao_that_lac"] = so.get("that_lac", 0)
    return danh_sach


def danh_sach_cho_chat(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """UC-26: Đơn đang chờ CÙNG TUYẾN, CÙNG CHIỀU với chuyến, và đang chờ
    đúng tại điểm xe đang đứng (mục 10.2) — đơn cũ hiện trước."""
    chuyen = _chuyen_cua_phu_xe_dang_hoat_dong(chuyen_id, nguoi_dung_id, TRANG_THAI_CHUYEN_DUOC_CHAT)
    diem = diem_hien_tai(chuyen)

    don_hang_list = don_hang_repo.lay_danh_sach_cho_xep_xe(str(chuyen["tuyen_id"]), chuyen_id)
    return _gan_so_bao_cao([
        {
            "id": str(d["id"]),
            "ma_van_don": d["ma_van_don"],
            "ten_nguoi_nhan": d["ten_nguoi_nhan"],
            "ten_diem_nhan": d.get("ten_diem_nhan") or "",
            "can_nang_kg": float(d["can_nang_kg"]),
            "ngay_tao": d["ngay_tao"],
        }
        for d in don_hang_list
        if str(d["diem_gui_id"]) == str(diem["diem_don_tra_id"])
    ])


def danh_sach_cho_do(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """UC-27: Đơn đang trên chính chuyến này, có điểm nhận đúng là điểm xe đang đứng."""
    chuyen = _chuyen_cua_phu_xe_dang_hoat_dong(chuyen_id, nguoi_dung_id, TRANG_THAI_CHUYEN_DUOC_DO)
    diem = diem_hien_tai(chuyen)

    don_hang_list = don_hang_repo.tim_don_can_do_tai_diem(chuyen_id, str(diem["diem_don_tra_id"]))
    return _gan_so_bao_cao([
        {
            "id": str(d["id"]),
            "ma_van_don": d["ma_van_don"],
            "ten_nguoi_nhan": d["ten_nguoi_nhan"],
            "can_nang_kg": float(d["can_nang_kg"]),
        }
        for d in don_hang_list
    ])


def xac_nhan_chat_hang(don_hang_id: str, chuyen_id: str, nguoi_dung_id: str) -> dict:
    """UC-26: Phụ xe xác nhận đã chất 1 đơn lên chuyến của mình.

    Chuyến phải thuộc phụ xe, cùng tuyến + cùng chiều với đơn (mục 10.2 &
    THAY_DOI_TUYEN_2_CHIEU.md), và đơn phải đang chờ đúng tại điểm xe đang đứng.
    """
    chuyen = _chuyen_cua_phu_xe_dang_hoat_dong(chuyen_id, nguoi_dung_id, TRANG_THAI_CHUYEN_DUOC_CHAT)

    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")
    if don["trang_thai"] != "cho_van_chuyen" or don.get("chuyen_id"):
        raise GiaTriLoi(f"Đơn hàng đang ở trạng thái '{don['trang_thai']}', không thể chất lên xe")
    if str(chuyen["tuyen_id"]) != str(don["tuyen_id"]):
        raise GiaTriLoi("Chuyến xe không thuộc tuyến vận chuyển của đơn hàng")

    diem = diem_hien_tai(chuyen)
    if str(don["diem_gui_id"]) != str(diem["diem_don_tra_id"]):
        raise GiaTriLoi("Đơn hàng không chờ tại điểm xe đang đứng")

    tuyen_info = don_hang_repo.kiem_tra_diem_thuoc_tuyen(
        str(don["tuyen_id"]), str(don["diem_gui_id"]), str(don["diem_nhan_id"])
    )
    if not tuyen_info:
        raise GiaTriLoi("Lộ trình của đơn hàng không khớp với tuyến của chuyến xe")

    # chuyen_xe_repository.tim_theo_id (dùng trong lay_chuyen_cua_phu_xe) không trả cột chieu
    chieu_chuyen = (don_hang_repo.tim_chuyen_xe_theo_id(chuyen_id) or {}).get("chieu")
    if chieu_chuyen and tuyen_info["chieu_van_chuyen"] != chieu_chuyen:
        raise GiaTriLoi(
            f"Chuyến xe đang chạy chiều '{chieu_chuyen}', "
            f"không thể chở đơn hàng gửi theo chiều '{tuyen_info['chieu_van_chuyen']}'"
        )

    don_cap_nhat = don_hang_repo.cap_nhat_chat_hang_len_chuyen(don_hang_id, chuyen_id, nguoi_dung_id)
    if not don_cap_nhat:
        raise GiaTriLoi("Đơn hàng vừa được xử lý bởi người khác, vui lòng tải lại danh sách")
    return don_cap_nhat


def xac_nhan_do_hang(don_hang_id: str, nguoi_dung_id: str) -> dict:
    """UC-27: Phụ xe dỡ hàng tại đúng điểm nhận, bắt đầu tính hạn chờ lấy (mục 10.3).

    Sau khi dỡ, nhắc nhân viên gửi hàng tại điểm nhận gọi báo người nhận ngay
    (mục 10.3.1 điểm 2, 10.4.2 bước 1 — kênh báo tin duy nhất là gọi điện).
    """
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")
    if don["trang_thai"] != "da_len_xe" or not don.get("chuyen_id"):
        raise GiaTriLoi("Đơn hàng chưa được xếp lên xe để dỡ")

    chuyen = _chuyen_cua_phu_xe_dang_hoat_dong(str(don["chuyen_id"]), nguoi_dung_id, TRANG_THAI_CHUYEN_DUOC_DO)
    diem = diem_hien_tai(chuyen)
    if str(don["diem_nhan_id"]) != str(diem["diem_don_tra_id"]):
        raise GiaTriLoi("Xe chưa tới điểm nhận của đơn hàng này")

    don_cap_nhat = don_hang_repo.cap_nhat_do_hang_tai_diem(don_hang_id, str(don["chuyen_id"]), nguoi_dung_id)
    if not don_cap_nhat:
        raise GiaTriLoi("Đơn hàng vừa được xử lý bởi người khác, vui lòng tải lại danh sách")

    _gui_thong_bao_an_toan(
        don_hang_repo.danh_sach_nhan_vien_gui_hang_tai_diem(str(don["diem_nhan_id"])),
        f"Đơn {don['ma_van_don']} vừa tới văn phòng — gọi báo người nhận "
        f"{don['ten_nguoi_nhan']} ({don['sdt_nguoi_nhan']}).",
        str(don["id"]),
    )
    return don_cap_nhat


def chat_tat_ca(chuyen_id: str, nguoi_dung_id: str) -> dict:
    """Chất hết đơn đang chờ tại điểm xe đứng. Từng đơn vẫn qua đủ kiểm tra như chất lẻ;
    đơn không chất được (sai chiều, vừa bị người khác xử lý...) được liệt kê lại thay vì làm hỏng cả lô."""
    ok, loi = 0, []
    for d in danh_sach_cho_chat(chuyen_id, nguoi_dung_id):
        if d.get("so_bao_that_lac"):
            loi.append(f"{d['ma_van_don']}: đã báo thất lạc, hãy kiểm tra rồi chất riêng từng đơn")
            continue
        try:
            xac_nhan_chat_hang(d["id"], chuyen_id, nguoi_dung_id)
            ok += 1
        except GiaTriLoi as e:
            loi.append(f"{d['ma_van_don']}: {e}")
    return {"so_luong": ok, "loi": loi}


def do_tat_ca(chuyen_id: str, nguoi_dung_id: str) -> dict:
    ok, loi = 0, []
    for d in danh_sach_cho_do(chuyen_id, nguoi_dung_id):
        if d.get("so_bao_that_lac"):
            loi.append(f"{d['ma_van_don']}: đã báo thất lạc, hãy kiểm tra rồi dỡ riêng từng đơn")
            continue
        try:
            xac_nhan_do_hang(d["id"], nguoi_dung_id)
            ok += 1
        except GiaTriLoi as e:
            loi.append(f"{d['ma_van_don']}: {e}")
    return {"so_luong": ok, "loi": loi}


def danh_sach_hoan_tac(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """Đơn vừa chất/dỡ tại ĐÚNG điểm xe đang đứng — phụ xe có thể hoàn tác nếu bấm nhầm."""
    chuyen = _chuyen_cua_phu_xe_dang_hoat_dong(chuyen_id, nguoi_dung_id, TRANG_THAI_CHUYEN_DUOC_DO)
    diem = diem_hien_tai(chuyen)
    return _gan_so_bao_cao([
        {
            "id": str(d["id"]),
            "ma_van_don": d["ma_van_don"],
            "ten_nguoi_nhan": d["ten_nguoi_nhan"],
            "can_nang_kg": float(d["can_nang_kg"]),
            "loai": d["loai"],
        }
        for d in don_hang_repo.tim_don_co_the_hoan_tac(chuyen_id, str(diem["diem_don_tra_id"]))
    ])


def hoan_tac_chat_hang(don_hang_id: str, chuyen_id: str, nguoi_dung_id: str) -> None:
    """Bấm nhầm "đã chất": trả đơn về hàng chờ chất. Chỉ khi xe còn đứng ở điểm gửi của đơn."""
    chuyen = _chuyen_cua_phu_xe_dang_hoat_dong(chuyen_id, nguoi_dung_id, TRANG_THAI_CHUYEN_DUOC_CHAT)
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don or str(don.get("chuyen_id")) != str(chuyen_id) or don["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Đơn hàng không ở trạng thái đã chất trên chuyến này, không có gì để hoàn tác")
    if str(don["diem_gui_id"]) != str(diem_hien_tai(chuyen)["diem_don_tra_id"]):
        raise GiaTriLoi("Xe đã rời điểm gửi của đơn này, không thể hoàn tác — hãy báo điều độ viên")
    if not don_hang_repo.hoan_tac_chat_hang(don_hang_id, chuyen_id, nguoi_dung_id):
        raise GiaTriLoi("Đơn hàng vừa được xử lý bởi người khác, vui lòng tải lại danh sách")


def hoan_tac_do_hang(don_hang_id: str, chuyen_id: str, nguoi_dung_id: str) -> None:
    """Bấm nhầm "đã dỡ": đưa đơn về trên xe, nhắn lại nhân viên văn phòng nhận đừng báo người nhận.
    Không làm được nếu văn phòng đã gọi báo người nhận (khách có thể đang đến lấy)."""
    chuyen = _chuyen_cua_phu_xe_dang_hoat_dong(chuyen_id, nguoi_dung_id, TRANG_THAI_CHUYEN_DUOC_DO)
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don or str(don.get("chuyen_id")) != str(chuyen_id) or don["trang_thai"] != "cho_lay":
        raise GiaTriLoi("Đơn hàng không ở trạng thái đã dỡ trên chuyến này, không có gì để hoàn tác")
    if str(don["diem_nhan_id"]) != str(diem_hien_tai(chuyen)["diem_don_tra_id"]):
        raise GiaTriLoi("Xe đã rời điểm nhận của đơn này, không thể hoàn tác — hãy báo điều độ viên")
    if don.get("da_thong_bao_nguoi_nhan"):
        raise GiaTriLoi("Văn phòng đã gọi báo người nhận, không thể hoàn tác — hãy báo điều độ viên")
    if not don_hang_repo.hoan_tac_do_hang(don_hang_id, chuyen_id, nguoi_dung_id):
        raise GiaTriLoi("Đơn hàng vừa được xử lý bởi người khác (hoặc đã báo người nhận), vui lòng tải lại")

    _gui_thong_bao_an_toan(
        don_hang_repo.danh_sach_nhan_vien_gui_hang_tai_diem(str(don["diem_nhan_id"])),
        f"Đơn {don['ma_van_don']}: phụ xe vừa hoàn tác — hàng CHƯA dỡ xuống văn phòng, đừng gọi báo người nhận.",
        str(don["id"]),
    )


def bao_that_lac(don_hang_id: str, mo_ta: str, nguoi_dung_id: str, loai: str = "hu_hong") -> dict:
    """UC-28: Phụ xe báo thất lạc/hư hỏng. Ghi nhận rồi chuyển tin tới nhân
    viên gửi hàng (điểm gửi nếu chưa lên xe, điểm nhận nếu đã lên xe) và
    quản lý (UC-28 bước 2) — không đổi trạng thái đơn, không chặn UC-26/27."""
    if loai not in ("hu_hong", "that_lac"):
        raise GiaTriLoi("Loại sự cố hàng không hợp lệ")
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")

    if not mo_ta or not mo_ta.strip():
        raise GiaTriLoi("Mô tả sự cố hàng hóa không được để trống")

    # UC-28 chỉ phát sinh trong lúc chất (UC-26) hoặc dỡ (UC-27) hàng:
    # - đã lên xe: chỉ phụ xe của đúng chuyến đó được báo;
    # - còn chờ chất: phụ xe phải có chuyến của xe mình cùng tuyến với đơn;
    # - trạng thái khác (đã dỡ/giao/hàng tồn): ngoài giai đoạn chất/dỡ.
    if don.get("chuyen_id"):
        lay_chuyen_cua_phu_xe(str(don["chuyen_id"]), nguoi_dung_id)
    elif don["trang_thai"] == "cho_van_chuyen":
        chuyen_cua_toi = chuyen_xe_service.danh_sach_chuyen_cua_toi(nguoi_dung_id)
        if not any(str(c["tuyen_id"]) == str(don["tuyen_id"]) for c in chuyen_cua_toi):
            raise CamTruyCap("Đơn hàng này không thuộc tuyến xe của bạn")
    else:
        raise GiaTriLoi("Đơn hàng không ở giai đoạn chất/dỡ hàng")

    bao_cao = don_hang_repo.luu_bao_cao_su_co_hang(don_hang_id, nguoi_dung_id, mo_ta.strip(), loai)

    diem_lien_quan = str(don["diem_nhan_id"] if don.get("chuyen_id") else don["diem_gui_id"])
    nguoi_nhan_tin = don_hang_repo.danh_sach_nhan_vien_gui_hang_tai_diem(diem_lien_quan) + \
        nguoi_dung_repo.danh_sach_id_theo_vai_tro("quan_ly", chi_dang_hoat_dong=True)
    _gui_thong_bao_an_toan(
        nguoi_nhan_tin,
        f"Phụ xe báo {'THẤT LẠC' if loai == 'that_lac' else 'hư hỏng'} hàng đơn {don['ma_van_don']}: {mo_ta.strip()}",
        str(don["id"]),
    )
    return bao_cao


def lay_bao_cao_su_co(don_hang_id: str, van_phong_id: str | None) -> list[dict]:
    """Báo cáo sự cố của 1 đơn — để nhân viên kiểm hàng cùng người nhận khi giao."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise KhongTimThay("Đơn hàng không tồn tại")
    _kiem_tra_don_thuoc_van_phong(don, van_phong_id)
    return don_hang_repo.lay_bao_cao_su_co(don_hang_id)


# ====================================================================
# 5. Hàng đến & Xử lý Hàng chờ quá lâu tại Điểm nhận (UC-24, UC-25, UC-46)
# ====================================================================

def lay_hang_den(van_phong_id: str | None) -> list[dict]:
    """Hàng sắp đến / chờ lấy / hàng tồn tại văn phòng nhận (None = toàn hệ thống)."""
    return don_hang_repo.lay_hang_den(van_phong_id)


def lay_lich_su_lien_he(don_hang_id: str, van_phong_id: str | None) -> list[dict]:
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise KhongTimThay("Đơn hàng không tồn tại")
    _kiem_tra_don_thuoc_van_phong(don, van_phong_id, chi_diem_nhan=True)
    return don_hang_repo.lay_lich_su_lien_he(don_hang_id)


def lay_lich_su_trang_thai(don_hang_id: str, van_phong_id: str | None) -> list[dict]:
    """Timeline đổi trạng thái — xem được ở cả văn phòng gửi lẫn văn phòng nhận."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise KhongTimThay("Đơn hàng không tồn tại")
    _kiem_tra_don_thuoc_van_phong(don, van_phong_id)
    return don_hang_repo.lay_lich_su_trang_thai(don_hang_id)


NHAN_TRUONG_LIEN_HE = {
    "ten_nguoi_gui": "tên người gửi",
    "sdt_nguoi_gui": "SĐT người gửi",
    "ten_nguoi_nhan": "tên người nhận",
    "sdt_nguoi_nhan": "SĐT người nhận",
}


def sua_thong_tin_lien_he(
    don_hang_id: str, nguoi_dung_id: str, van_phong_id: str | None, du_lieu: SuaThongTinLienHeRequest
) -> dict:
    """Sửa tên/SĐT người gửi, người nhận khi đơn chưa giao (gõ nhầm SĐT là lý do chính khiến
    không gọi được người nhận). Văn phòng gửi lẫn văn phòng nhận đều sửa được; văn phòng còn lại
    được thông báo để gọi đúng số. Mọi lần sửa đều để lại nhật ký."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise KhongTimThay("Đơn hàng không tồn tại")
    _kiem_tra_don_thuoc_van_phong(don, van_phong_id)
    if don["trang_thai"] == "da_giao":
        raise GiaTriLoi("Đơn đã giao xong, không thể sửa thông tin")

    thay_doi = {t: getattr(du_lieu, t) for t in TRUONG_LIEN_HE if getattr(du_lieu, t) is not None}
    try:
        don_moi = don_hang_repo.sua_thong_tin_lien_he(don_hang_id, thay_doi, nguoi_dung_id, du_lieu.ly_do)
    except don_hang_repo.DonDaGiao:
        raise GiaTriLoi("Đơn vừa được giao xong, không thể sửa thông tin") from None
    if not don_moi:
        raise KhongTimThay("Đơn hàng không tồn tại")

    cac_truong_doi = [t for t in thay_doi if don[t] != don_moi[t]]
    if cac_truong_doi and van_phong_id:
        # Báo văn phòng còn lại để họ gọi đúng số / đúng tên.
        diem_con_lai = (
            str(don["diem_nhan_id"]) if str(van_phong_id) == str(don["diem_gui_id"]) else str(don["diem_gui_id"])
        )
        noi_dung = (
            f"Đơn {don['ma_van_don']} vừa được sửa {', '.join(NHAN_TRUONG_LIEN_HE[t] for t in cac_truong_doi)}"
            " — kiểm tra lại thông tin trước khi gọi/bàn giao."
        )
        _gui_thong_bao_an_toan(don_hang_repo.danh_sach_nhan_vien_gui_hang_tai_diem(diem_con_lai), noi_dung, don_hang_id)
    return don_moi


def lay_lich_su_chinh_sua(don_hang_id: str, van_phong_id: str | None) -> list[dict]:
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise KhongTimThay("Đơn hàng không tồn tại")
    _kiem_tra_don_thuoc_van_phong(don, van_phong_id)
    return don_hang_repo.lay_lich_su_chinh_sua(don_hang_id)


def goi_y_khach(sdt: str, vai_tro: str, van_phong_id: str | None) -> list[dict]:
    """Gợi ý họ tên từ các đơn cũ của văn phòng khi nhân viên nhập SĐT người gửi/nhận."""
    return don_hang_repo.goi_y_khach_theo_sdt(sdt.strip(), vai_tro == "gui", van_phong_id)


def ghi_ket_qua_lien_he(
    don_hang_id: str,
    nguoi_dung_id: str,
    van_phong_id: str | None,
    doi_tuong: str,
    ket_qua: str,
    ghi_chu: str | None = None,
) -> dict:
    """Mục 10.3.1 & UC-25: lưu kết quả gọi người nhận / người gửi, hoặc báo quản lý.

    - Chỉ văn phòng NHẬN của đơn, đơn đang `cho_lay` hoặc `qua_han_luu_kho`.
    - Gọi người nhận thành công → bật cờ `da_thong_bao_nguoi_nhan` (chỉ bật, không tắt).
    - Báo quản lý chỉ khi đơn đã có cảnh báo 7 ngày hoặc đã là hàng tồn (UC-25:
      không liên hệ được ai) — tạo thông báo cho các quản lý đang hoạt động.
    """
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")
    if van_phong_id and str(don["diem_nhan_id"]) != str(van_phong_id):
        raise CamTruyCap("Đơn hàng thuộc văn phòng nhận khác")
    if don["trang_thai"] not in ("cho_lay", "qua_han_luu_kho"):
        raise GiaTriLoi("Chỉ ghi nhận liên hệ cho đơn đang chờ lấy hoặc hàng tồn")

    thong_bao_cho: list[str] = []
    noi_dung: str | None = None
    if doi_tuong == "quan_ly":
        if not (don.get("co_canh_bao_cho_lau") or don["trang_thai"] == "qua_han_luu_kho"):
            raise GiaTriLoi("Chỉ báo quản lý với đơn đã chờ quá 7 ngày hoặc đã chuyển hàng tồn")
        thong_bao_cho = nguoi_dung_repo.danh_sach_id_theo_vai_tro("quan_ly", chi_dang_hoat_dong=True)
        noi_dung = (
            f"Đơn {don['ma_van_don']} tại {don.get('ten_diem_nhan') or 'văn phòng nhận'} không liên hệ được "
            f"người nhận/người gửi, cần quản lý xử lý hàng tồn."
            + (f" Ghi chú: {ghi_chu}" if ghi_chu else "")
        )

    don_hang_repo.ghi_lien_he(
        don_hang_id,
        nguoi_dung_id,
        doi_tuong,
        ket_qua,
        ghi_chu,
        danh_dau_da_thong_bao=(doi_tuong == "nguoi_nhan" and ket_qua == "da_lien_he"),
        thong_bao_cho=thong_bao_cho,
        noi_dung_thong_bao=noi_dung,
    )
    for quan_ly_id in thong_bao_cho:
        broadcast_sync(quan_ly_id, noi_dung)
    return don_hang_repo.tim_theo_id(don_hang_id)


def _noi_dung_canh_bao_7_ngay(don: dict) -> str:
    if don.get("da_thong_bao_nguoi_nhan"):
        return f"Đơn {don['ma_van_don']} đã chờ lấy 7 ngày — gọi lại người nhận hỏi khi nào tới lấy."
    return (
        f"Đơn {don['ma_van_don']} đã chờ lấy 7 ngày nhưng chưa từng báo được người nhận — "
        f"gọi người gửi để hỏi hướng xử lý."
    )


def _noi_dung_hang_ton_14_ngay(don: dict) -> str:
    return (
        f"Đơn {don['ma_van_don']} đã chuyển hàng tồn (14 ngày chưa ai lấy) — liên hệ người gửi xử lý; "
        f"không liên hệ được ai thì báo quản lý."
    )


def quet_canh_bao_va_chuyen_hang_ton() -> dict:
    """UC-46: Cronjob chạy định kỳ — không tự hủy/thanh lý, chỉ đổi cờ/trạng thái để nhắc người xử lý.

    - Mốc >= 7 ngày: bật co_canh_bao_cho_lau, nhắc gọi đúng đối tượng (mục 10.3.1 điểm 3).
    - Mốc >= 14 ngày: chuyển qua_han_luu_kho, nhắc liên hệ người gửi (điểm 4).
    """
    so_canh_bao, can_day_7 = don_hang_repo.quet_canh_bao_7_ngay(_noi_dung_canh_bao_7_ngay)
    so_hang_ton, can_day_14 = don_hang_repo.quet_chuyen_hang_ton_14_ngay(_noi_dung_hang_ton_14_ngay)
    for nguoi_nhan_id, noi_dung in can_day_7 + can_day_14:
        broadcast_sync(nguoi_nhan_id, noi_dung)
    return {"so_don_canh_bao_7_ngay": so_canh_bao, "so_don_chuyen_ton_14_ngay": so_hang_ton}


# ====================================================================
# 6. Thống kê & Đối soát tiền (UC-39)
# ====================================================================

def thong_ke_hang_tai_diem(diem_id: str | None, tu_ngay: date, den_ngay: date) -> dict:
    """UC-39: Thống kê hàng & tiền tại văn phòng (hoặc toàn hệ thống nếu diem_id None)."""
    _kiem_tra_khoang_ngay(tu_ngay, den_ngay)
    if diem_id and not dia_diem_repo.tim_diem_don_tra_theo_id(diem_id):
        raise GiaTriLoi("Điểm/văn phòng không tồn tại")
    return don_hang_repo.thong_ke_hang_tai_diem(diem_id, tu_ngay, den_ngay)


def thong_ke_hang_theo_ngay(diem_id: str | None, so_ngay: int) -> list[dict]:
    if so_ngay not in (7, 14, 30):
        raise GiaTriLoi("Khoảng thống kê chỉ hỗ trợ 7, 14 hoặc 30 ngày")
    return don_hang_repo.thong_ke_hang_theo_ngay(diem_id, so_ngay)


def doi_soat_tien(diem_id: str | None, tu_ngay: date, den_ngay: date) -> dict:
    """Tiền mặt từng nhân viên đã thu trong kỳ (trả trước + COD) — đối soát két cuối ca."""
    _kiem_tra_khoang_ngay(tu_ngay, den_ngay)
    nhan_vien = don_hang_repo.doi_soat_tien_theo_nhan_vien(diem_id, tu_ngay, den_ngay)
    return {
        "tu_ngay": tu_ngay.isoformat(),
        "den_ngay": den_ngay.isoformat(),
        "nhan_vien": nhan_vien,
        "tong_tien": sum(r["tong_tien"] for r in nhan_vien),
    }
