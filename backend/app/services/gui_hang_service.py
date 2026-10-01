"""Quy tắc nghiệp vụ Gửi hàng — NGHIEP_VU.md mục 10 & ma trận UC (UC-23, 24, 25, 26, 27, 46).

Service quản lý vòng đời đơn hàng gửi theo tuyến:
- Tạo đơn, cân đo, tính cước, chặn hàng cấm (UC-23).
- Giao hàng cho người nhận, kiểm tra thu COD (UC-24).
- Xử lý hàng chờ quá lâu tại điểm nhận (UC-25).
- Cung cấp hàm cho Phụ xe chất/dỡ hàng (UC-26, UC-27).
"""

from datetime import datetime
from uuid import uuid4

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import don_hang_repository as don_hang_repo
from app.repositories import ho_so_can_bo_diem_repository as ho_so_diem_repo
from app.schemas.don_hang_schema import TaoDonHangRequest
from app.utils.loi import GiaTriLoi, KhongDuQuyen


def _van_phong_theo_quyen(nguoi_dung_id: str, vai_tro: str, van_phong_yeu_cau: str | None = None) -> str | None:
    """NV gửi hàng luôn bị giới hạn vào văn phòng được gán ở BE.

    Quản lý có thể chọn một văn phòng cụ thể hoặc để trống để xem toàn hệ thống.
    """
    if vai_tro == "nhan_vien_gui_hang":
        ho_so = ho_so_diem_repo.lay_theo_nguoi_dung_id(nguoi_dung_id)
        if not ho_so:
            raise KhongDuQuyen("Tài khoản chưa được phân công văn phòng gửi hàng")
        van_phong_id = str(ho_so["van_phong_id"])
        if van_phong_yeu_cau and str(van_phong_yeu_cau) != van_phong_id:
            raise KhongDuQuyen("Bạn chỉ được thao tác tại văn phòng đã được phân công")
        return van_phong_id
    return str(van_phong_yeu_cau) if van_phong_yeu_cau else None


def lay_pham_vi(nguoi_dung_id: str, vai_tro: str) -> dict:
    if vai_tro == "quan_ly":
        return {"pham_vi_toan_he_thong": True, "van_phong_id": None, "ten_van_phong": None}
    van_phong_id = _van_phong_theo_quyen(nguoi_dung_id, vai_tro)
    ho_so = ho_so_diem_repo.lay_theo_nguoi_dung_id(nguoi_dung_id)
    return {
        "pham_vi_toan_he_thong": False,
        "van_phong_id": van_phong_id,
        "ten_van_phong": ho_so["ten_van_phong"],
    }


# ====================================================================
# 1. Tạo đơn gửi hàng tại quầy (UC-23)
# ====================================================================

def _sinh_ma_van_don() -> str:
    """Sinh mã vận đơn ngẫu nhiên dễ đọc, vd: DH-20260920-A1B2C3."""
    ngay = datetime.now().strftime("%Y%m%d")
    ngau_nhien = uuid4().hex[:6].upper()
    return f"DH-{ngay}-{ngau_nhien}"


def lay_danh_sach_loai_hang() -> list[dict]:
    """Lấy danh mục loại hàng cho nhân viên chọn lúc nhận hàng."""
    return don_hang_repo.lay_danh_sach_loai_hang()


def tao_don_hang(du_lieu: TaoDonHangRequest, nhan_vien_id: str, vai_tro: str) -> dict:
    """UC-23: Nhận hàng tại quầy, tính cước và tạo đơn hàng.

    - Kiểm tra loại hàng: chặn nếu là hàng cấm.
    - Điểm gửi và nhận bắt buộc là văn phòng (loai = 'van_phong').
    - Tạo đơn gắn với tuyến (không gán chuyến xe cụ thể).
    """
    # 1. Kiểm tra loại hàng
    loai_hang = don_hang_repo.tim_loai_hang_theo_id(str(du_lieu.loai_hang_id))
    if not loai_hang:
        raise GiaTriLoi("Loại hàng hóa không tồn tại trong hệ thống")
    if loai_hang["la_hang_cam"]:
        raise GiaTriLoi(f"Mặt hàng '{loai_hang['ten']}' thuộc danh mục cấm vận chuyển, từ chối tiếp nhận")

    # 2. Điểm gửi do BE suy ra từ hồ sơ nhân viên; quản lý có thể chọn điểm gửi.
    diem_gui_id = _van_phong_theo_quyen(nhan_vien_id, vai_tro, str(du_lieu.diem_gui_id))
    if not diem_gui_id:
        raise GiaTriLoi("Vui lòng chọn văn phòng gửi")
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

    if diem_gui_id == str(du_lieu.diem_nhan_id):
        raise GiaTriLoi("Điểm nhận không được trùng với điểm gửi")

    if du_lieu.phuong_thuc_thanh_toan == "nguoi_gui_tra_truoc" and not du_lieu.xac_nhan_da_thu_truoc:
        raise GiaTriLoi("Vui lòng xác nhận đã thu đủ cước của người gửi trước khi tạo đơn")
    if du_lieu.phuong_thuc_thanh_toan == "cod_nguoi_nhan_tra" and du_lieu.xac_nhan_da_thu_truoc:
        raise GiaTriLoi("Đơn COD chưa thu tiền tại quầy gửi")

    # 3. Kiểm tra tuyến
    tuyen = dia_diem_repo.tim_tuyen_theo_id(str(du_lieu.tuyen_id))
    if not tuyen:
        raise GiaTriLoi("Tuyến xe gửi hàng không tồn tại")

    cac_diem_tuyen = dia_diem_repo.danh_sach_diem_theo_tuyen(str(du_lieu.tuyen_id))
    id_diem_tuyen = {str(d.get("diem_don_tra_id") or d.get("id")) for d in cac_diem_tuyen}
    if diem_gui_id not in id_diem_tuyen or str(du_lieu.diem_nhan_id) not in id_diem_tuyen:
        raise GiaTriLoi("Điểm gửi hoặc điểm nhận không thuộc lộ trình tuyến đã chọn")

    # 4. Sinh mã vận đơn và lưu vào CSDL
    ma_van_don = _sinh_ma_van_don()
    payload = {
        "ma_van_don": ma_van_don,
        "tuyen_id": str(du_lieu.tuyen_id),
        "diem_gui_id": diem_gui_id,
        "diem_nhan_id": str(du_lieu.diem_nhan_id),
        "loai_hang_id": str(du_lieu.loai_hang_id),
        "can_nang_kg": float(du_lieu.can_nang_kg),
        "dai_cm": float(du_lieu.dai_cm) if du_lieu.dai_cm else None,
        "rong_cm": float(du_lieu.rong_cm) if du_lieu.rong_cm else None,
        "cao_cm": float(du_lieu.cao_cm) if du_lieu.cao_cm else None,
        "gia_cuoc": du_lieu.gia_cuoc,
        "ten_nguoi_gui": du_lieu.ten_nguoi_gui.strip(),
        "sdt_nguoi_gui": du_lieu.sdt_nguoi_gui.strip(),
        "ten_nguoi_nhan": du_lieu.ten_nguoi_nhan.strip(),
        "sdt_nguoi_nhan": du_lieu.sdt_nguoi_nhan.strip(),
        "phuong_thuc_thanh_toan": du_lieu.phuong_thuc_thanh_toan,
        "nhan_vien_gui_id": nhan_vien_id,
        "da_thu_tien": du_lieu.phuong_thuc_thanh_toan == "nguoi_gui_tra_truoc",
        "nhan_vien_thu_id": nhan_vien_id if du_lieu.phuong_thuc_thanh_toan == "nguoi_gui_tra_truoc" else None,
    }

    return don_hang_repo.tao_don_hang(payload)


# ====================================================================
# 2. Giao hàng cho người nhận & Thu COD (UC-24)
# ====================================================================

def xac_nhan_thu_cod(
    ma_van_don: str, nhan_vien_thu_id: str, vai_tro: str, xac_nhan_da_thu: bool
) -> dict:
    """Ghi nhận riêng việc thu đủ COD tại văn phòng nhận, trước khi bàn giao."""
    if not xac_nhan_da_thu:
        raise GiaTriLoi("Cần xác nhận đã thu đủ tiền COD trước khi tiếp tục")

    don = don_hang_repo.tim_theo_ma_van_don(ma_van_don.strip().upper())
    if not don:
        raise GiaTriLoi(f"Không tìm thấy đơn hàng với mã vận đơn: {ma_van_don}")
    van_phong_id = _van_phong_theo_quyen(nhan_vien_thu_id, vai_tro)
    if van_phong_id and str(don["diem_nhan_id"]) != van_phong_id:
        raise KhongDuQuyen("Chỉ văn phòng nhận được phân công mới được thu COD cho đơn này")
    if don["trang_thai"] != "cho_lay":
        raise GiaTriLoi("Chỉ thu COD khi đơn đã đến văn phòng và đang chờ người nhận lấy")
    if don["phuong_thuc_thanh_toan"] != "cod_nguoi_nhan_tra":
        raise GiaTriLoi("Đơn hàng này không sử dụng hình thức thanh toán COD")
    if don["da_thu_tien"]:
        raise GiaTriLoi("Đơn hàng đã được ghi nhận thu tiền")

    da_thu = don_hang_repo.cap_nhat_thu_cod(don["id"], nhan_vien_thu_id, van_phong_id)
    if not da_thu:
        raise GiaTriLoi("Không thể ghi nhận thu COD; đơn vừa được cập nhật hoặc không còn ở trạng thái chờ lấy")
    return da_thu


def xac_nhan_giao_hang(ma_van_don: str, nhan_vien_nhan_id: str, vai_tro: str) -> dict:
    """UC-24: Bàn giao hàng cho người nhận tại quầy.

    - Chỉ đơn ở trạng thái 'cho_lay' được bàn giao theo mục 10.4.2.
    - Đơn chỉ được giao sau khi khoản cước cần thu đã được ghi nhận.
    """
    don = don_hang_repo.tim_theo_ma_van_don(ma_van_don.strip().upper())
    if not don:
        raise GiaTriLoi(f"Không tìm thấy đơn hàng với mã vận đơn: {ma_van_don}")

    van_phong_id = _van_phong_theo_quyen(nhan_vien_nhan_id, vai_tro)
    if van_phong_id and str(don["diem_nhan_id"]) != van_phong_id:
        raise KhongDuQuyen("Chỉ văn phòng nhận được phân công mới được bàn giao đơn này")
    if don["trang_thai"] != "cho_lay":
        raise GiaTriLoi("Chỉ giao đơn ở trạng thái chờ lấy tại văn phòng nhận")
    if not don["da_thu_tien"]:
        raise GiaTriLoi("Chưa ghi nhận thu đủ cước; hãy hoàn tất thu tiền trước khi giao hàng")

    don_cap_nhat = don_hang_repo.cap_nhat_giao_hang(don["id"], nhan_vien_nhan_id, van_phong_id)
    if not don_cap_nhat:
        raise GiaTriLoi("Không thể cập nhật giao hàng, vui lòng thử lại")

    return don_cap_nhat


# ====================================================================
# 3. Tra cứu Đơn hàng (Khách hàng + Nhân viên)
# ====================================================================

def tra_cuu_theo_ma_van_don(ma_van_don: str, nguoi_dung_id: str, vai_tro: str) -> dict:
    """Tra cứu chi tiết đơn hàng theo mã vận đơn."""
    don = don_hang_repo.tim_theo_ma_van_don(ma_van_don.strip().upper())
    if not don:
        raise GiaTriLoi(f"Không tìm thấy đơn hàng với mã vận đơn: {ma_van_don}")
    van_phong_id = _van_phong_theo_quyen(nguoi_dung_id, vai_tro)
    if van_phong_id and van_phong_id not in (str(don["diem_gui_id"]), str(don["diem_nhan_id"])):
        raise KhongDuQuyen("Đơn hàng không thuộc văn phòng bạn phụ trách")
    return don


def tra_cuu_cong_khai(ma_van_don: str, sdt: str) -> dict:
    """Trả trạng thái tối thiểu sau khi đối chiếu mã vận đơn và số điện thoại."""
    don = don_hang_repo.tim_thong_tin_theo_ma_van_don_cong_khai(
        ma_van_don.strip().upper(), sdt.strip()
    )
    if not don:
        raise GiaTriLoi("Không tìm thấy vận đơn phù hợp với mã và số điện thoại đã nhập")
    return don


def tra_cuu_theo_sdt(sdt: str, ten: str, nguoi_dung_id: str, vai_tro: str) -> list[dict]:
    """Nhân viên tra cứu theo số điện thoại + tên trong phạm vi được phân công."""
    van_phong_id = _van_phong_theo_quyen(nguoi_dung_id, vai_tro)
    return don_hang_repo.tim_theo_sdt(sdt.strip(), ten.strip(), van_phong_id)


# ====================================================================
# 4. Hỗ trợ Phụ xe: Chất / Dỡ hàng (UC-26, UC-27, UC-28)
# ====================================================================

def lay_danh_sach_cho_xep_xe(tuyen_id: str) -> list[dict]:
    """UC-26: Phụ xe xem các đơn hàng đang chờ chất lên xe tại tuyến này."""
    return don_hang_repo.lay_danh_sach_cho_xep_xe(tuyen_id)


def danh_sach_cho_chat(chuyen_id: str, phu_xe_id: str) -> list[dict]:
    """UC-26: Phụ xe lấy danh sách đơn hàng chờ chất lên chuyến tại điểm hiện tại."""
    from app.services import chuyen_xe_service
    chuyen = chuyen_xe_service.lay_chuyen_cua_phu_xe(chuyen_id, phu_xe_id)
    if chuyen["trang_thai"] not in ("chua_khoi_hanh", "dang_chay"):
        raise GiaTriLoi("Chỉ xem hàng chờ chất của chuyến đang chuẩn bị xuất phát hoặc đang chạy")
    diem_ht = chuyen_xe_service.diem_hien_tai(chuyen)
    diem_gui_id = str(diem_ht["diem_don_tra_id"]) if diem_ht else None
    return don_hang_repo.lay_danh_sach_cho_xep_xe(
        tuyen_id=str(chuyen["tuyen_id"]),
        chuyen_id=chuyen_id,
        diem_gui_id=diem_gui_id,
    )


def danh_sach_cho_do(chuyen_id: str, phu_xe_id: str) -> list[dict]:
    """UC-27: Phụ xe lấy danh sách đơn hàng cần dỡ tại điểm dừng hiện tại."""
    from app.services import chuyen_xe_service
    chuyen = chuyen_xe_service.lay_chuyen_cua_phu_xe(chuyen_id, phu_xe_id)
    if chuyen["trang_thai"] not in ("dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chỉ xem hàng cần dỡ khi chuyến đang chạy hoặc vừa đến điểm cuối")
    diem_ht = chuyen_xe_service.diem_hien_tai(chuyen)
    diem_nhan_id = str(diem_ht["diem_don_tra_id"]) if diem_ht else ""
    return don_hang_repo.tim_don_can_do_tai_diem(chuyen_id, diem_nhan_id)


def bao_that_lac(don_hang_id: str, mo_ta: str, phu_xe_id: str) -> None:
    """UC-28: Phụ xe báo cáo thất lạc / hư hỏng kiện hàng."""
    from app.repositories import bao_cao_su_co_hang_repository as bao_cao_hang_repo
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")
    if don["trang_thai"] != "da_len_xe" or not don.get("chuyen_id"):
        raise GiaTriLoi("Chỉ báo cáo kiện hàng đang được vận chuyển trên xe")
    from app.services import chuyen_xe_service
    chuyen_xe_service.lay_chuyen_cua_phu_xe(str(don["chuyen_id"]), phu_xe_id)
    bao_cao_hang_repo.tao(don_hang_id, phu_xe_id, mo_ta)


def xac_nhan_chat_hang(don_hang_id: str, chuyen_id: str, phu_xe_id: str) -> dict:
    """UC-26: Phụ xe chất hàng lên xe của chuyến cụ thể."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")

    if don["trang_thai"] != "cho_van_chuyen":
        raise GiaTriLoi(f"Đơn hàng đang ở trạng thái '{don['trang_thai']}', không thể chất lên xe")

    from app.services import chuyen_xe_service
    chuyen = chuyen_xe_service.lay_chuyen_cua_phu_xe(chuyen_id, phu_xe_id)
    if chuyen["trang_thai"] not in ("chua_khoi_hanh", "dang_chay"):
        raise GiaTriLoi("Chỉ chất hàng lên chuyến đang chuẩn bị xuất phát hoặc đang chạy")

    if str(chuyen["tuyen_id"]) != str(don["tuyen_id"]):
        raise GiaTriLoi("Chuyến xe không thuộc tuyến vận chuyển của đơn hàng")

    # Kiểm tra hướng tuyến và vị trí xe: phụ xe chỉ chất tại đúng điểm xe đang dừng.
    cac_diem = dia_diem_repo.danh_sach_diem_theo_tuyen(str(don["tuyen_id"]))
    thu_tu_map = {str(d.get("diem_don_tra_id") or d.get("id")): d.get("thu_tu", 0) for d in cac_diem}
    tt_gui = thu_tu_map.get(str(don.get("diem_gui_id")))
    tt_nhan = thu_tu_map.get(str(don.get("diem_nhan_id")))

    if tt_gui is not None and tt_nhan is not None:
        chieu = chuyen.get("chieu", "xuoi")
        if chieu == "xuoi" and tt_gui >= tt_nhan:
            raise GiaTriLoi("Đơn hàng không cùng chiều với chuyến xe đang chạy")
        if chieu == "nguoc" and tt_gui <= tt_nhan:
            raise GiaTriLoi("Đơn hàng không cùng chiều với chuyến xe đang chạy")

    diem_hien_tai = chuyen_xe_service.diem_hien_tai(chuyen)
    if not diem_hien_tai or str(diem_hien_tai["diem_don_tra_id"]) != str(don["diem_gui_id"]):
        raise GiaTriLoi("Chỉ có thể chất đơn tại đúng văn phòng gửi đang là điểm dừng hiện tại của chuyến")

    don_cap_nhat = don_hang_repo.cap_nhat_chat_hang_len_chuyen(don_hang_id, chuyen_id)
    if not don_cap_nhat:
        raise GiaTriLoi("Không thể cập nhật chất hàng lên xe")
    return don_cap_nhat


def xac_nhan_do_hang(don_hang_id: str, phu_xe_id: str) -> dict:
    """UC-27: Phụ xe dỡ hàng xuống điểm nhận, bắt đầu tính hạn chờ lấy."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")

    if don["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Đơn hàng chưa được xếp lên xe để dỡ")

    from app.services import chuyen_xe_service
    if not don.get("chuyen_id"):
        raise GiaTriLoi("Đơn hàng chưa được gắn với chuyến xe")
    chuyen = chuyen_xe_service.lay_chuyen_cua_phu_xe(str(don["chuyen_id"]), phu_xe_id)
    if str(chuyen["tuyen_id"]) != str(don["tuyen_id"]):
        raise GiaTriLoi("Chuyến xe không thuộc tuyến vận chuyển của đơn hàng")
    if chuyen["trang_thai"] not in ("dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến chưa đến trạng thái có thể dỡ hàng")
    diem_hien_tai = chuyen_xe_service.diem_hien_tai(chuyen)
    if not diem_hien_tai or str(diem_hien_tai["diem_don_tra_id"]) != str(don["diem_nhan_id"]):
        raise GiaTriLoi("Chỉ có thể dỡ hàng tại đúng văn phòng nhận khi chuyến đang dừng tại đó")

    don_cap_nhat = don_hang_repo.cap_nhat_do_hang_tai_diem(don_hang_id, str(don["chuyen_id"]))
    if not don_cap_nhat:
        raise GiaTriLoi("Không thể cập nhật dỡ hàng")
    return don_cap_nhat


# ====================================================================
# 5. Xử lý Hàng chờ quá lâu tại Điểm nhận (UC-25, UC-46)
# ====================================================================

def lay_danh_sach_hang_cho_tai_diem(
    diem_nhan_id: str | None, nguoi_dung_id: str, vai_tro: str
) -> list[dict]:
    """UC-25: Nhân viên quầy xem danh sách hàng đang chờ nhận / cảnh báo / tồn kho tại văn phòng mình (hoặc toàn bộ nếu diem_nhan_id là None)."""
    diem_pham_vi = _van_phong_theo_quyen(nguoi_dung_id, vai_tro, diem_nhan_id)
    return don_hang_repo.lay_danh_sach_hang_cho_tai_diem(diem_pham_vi)


def cap_nhat_thong_bao_nguoi_nhan(
    don_hang_id: str, da_thong_bao: bool, nguoi_dung_id: str, vai_tro: str
) -> dict:
    """UC-25: Ghi nhận nhân viên quầy đã liên lạc thành công với người nhận."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")

    van_phong_id = _van_phong_theo_quyen(nguoi_dung_id, vai_tro)
    if van_phong_id and str(don["diem_nhan_id"]) != van_phong_id:
        raise KhongDuQuyen("Đơn hàng không thuộc văn phòng nhận bạn phụ trách")
    if don["trang_thai"] not in ("cho_lay", "qua_han_luu_kho"):
        raise GiaTriLoi("Chỉ có thể cập nhật liên hệ cho hàng đã đến văn phòng nhận")

    don_hang_repo.cap_nhat_thong_bao_nguoi_nhan(don_hang_id, da_thong_bao)
    return don_hang_repo.tim_theo_id(don_hang_id)


def quet_canh_bao_va_chuyen_hang_ton() -> dict:
    """UC-46: Cronjob chạy định kỳ quét:

    - Mốc >= 7 ngày: Bật cờ co_canh_bao_cho_lau.
    - Mốc >= 14 ngày: Chuyển sang qua_han_luu_kho (hàng tồn).
    """
    so_canh_bao = don_hang_repo.quet_bat_canh_bao_7_ngay()
    so_hang_ton = don_hang_repo.quet_chuyen_hang_ton_14_ngay()
    return {"so_don_canh_bao_7_ngay": so_canh_bao, "so_don_chuyen_ton_14_ngay": so_hang_ton}


# ====================================================================
# 6. Thống kê Hoạt động Gửi hàng & Đơn gần đây (UC-39)
# ====================================================================

def lay_danh_sach_don_gan_day(
    limit: int = 20,
    diem_gui_id: str | None = None,
    trang_thai: str | None = None,
    tu_khoa: str | None = None,
    nguoi_dung_id: str | None = None,
    vai_tro: str | None = None,
) -> list[dict]:
    """Lấy danh sách các đơn hàng mới nhất để hiển thị tại quầy."""
    if nguoi_dung_id and vai_tro:
        diem_gui_id = _van_phong_theo_quyen(nguoi_dung_id, vai_tro, diem_gui_id)
    return don_hang_repo.lay_danh_sach_don_gan_day(
        limit=limit,
        diem_gui_id=diem_gui_id,
        trang_thai=trang_thai,
        tu_khoa=tu_khoa,
    )


def thong_ke_hang_tai_diem(
    diem_id: str | None, nguoi_dung_id: str, vai_tro: str, so_ngay: int = 7
) -> dict:
    """UC-39: Thống kê đơn hàng và doanh thu tại văn phòng (hoặc toàn bộ nếu diem_id là None)."""
    diem_id = _van_phong_theo_quyen(nguoi_dung_id, vai_tro, diem_id)
    if diem_id:
        diem = dia_diem_repo.tim_diem_don_tra_theo_id(diem_id)
        if not diem:
            raise GiaTriLoi("Điểm/văn phòng không tồn tại")
    return don_hang_repo.thong_ke_hang_tai_diem(diem_id, so_ngay)

