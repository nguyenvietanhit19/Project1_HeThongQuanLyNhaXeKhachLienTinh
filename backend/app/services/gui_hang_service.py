"""Quy tắc nghiệp vụ Gửi hàng — NGHIEP_VU.md mục 10 & ma trận UC (UC-23, 24, 25, 26, 27, 46).

Service quản lý vòng đời đơn hàng gửi theo tuyến:
- Tạo đơn, cân đo, tính cước, chặn hàng cấm (UC-23).
- Giao hàng cho người nhận, kiểm tra thu COD (UC-24).
- Xử lý hàng chờ quá lâu tại điểm nhận (UC-25).
- Cung cấp hàm cho Phụ xe chất/dỡ hàng (UC-26, UC-27).
"""

from datetime import datetime
from uuid import uuid4

from app.repositories import bao_cao_su_co_hang_repository as bao_cao_repo
from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import don_hang_repository as don_hang_repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.schemas.don_hang_schema import TaoDonHangRequest
from app.services import chuyen_xe_service
from app.services.chuyen_xe_service import diem_hien_tai, lay_chuyen_cua_phu_xe
from app.services.websocket_manager import broadcast_sync
from app.utils.loi import GiaTriLoi, KhongDuQuyen


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


def tao_don_hang(du_lieu: TaoDonHangRequest, nhan_vien_id: str) -> dict:
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

    # 2. Kiểm tra điểm gửi và điểm nhận
    diem_gui = dia_diem_repo.tim_diem_don_tra_theo_id(str(du_lieu.diem_gui_id))
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

    # 3. Kiểm tra tuyến
    tuyen = dia_diem_repo.tim_tuyen_theo_id(str(du_lieu.tuyen_id))
    if not tuyen:
        raise GiaTriLoi("Tuyến xe gửi hàng không tồn tại")

    # 4. Sinh mã vận đơn và lưu vào CSDL
    ma_van_don = _sinh_ma_van_don()
    payload = {
        "ma_van_don": ma_van_don,
        "tuyen_id": str(du_lieu.tuyen_id),
        "diem_gui_id": str(du_lieu.diem_gui_id),
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
    }

    return don_hang_repo.tao_don_hang(payload)


# ====================================================================
# 2. Giao hàng cho người nhận & Thu COD (UC-24)
# ====================================================================

def xac_nhan_giao_hang(ma_van_don: str, nhan_vien_nhan_id: str) -> dict:
    """UC-24: Bàn giao hàng cho người nhận tại quầy.

    - Đơn phải ở trạng thái 'cho_lay' hoặc 'qua_han_luu_kho'.
    - Nếu hình thức là 'cod_nguoi_nhan_tra', nhân viên quầy thu cước rồi xác nhận giao.
    """
    don = don_hang_repo.tim_theo_ma_van_don(ma_van_don.strip().upper())
    if not don:
        raise GiaTriLoi(f"Không tìm thấy đơn hàng với mã vận đơn: {ma_van_don}")

    if don["trang_thai"] == "da_giao":
        raise GiaTriLoi("Đơn hàng này đã được giao cho người nhận trước đó")

    if don["trang_thai"] in ("cho_van_chuyen", "da_len_xe"):
        raise GiaTriLoi("Đơn hàng đang trong quá trình luân chuyển, chưa tới điểm nhận để giao")

    if don["trang_thai"] not in ("cho_lay", "qua_han_luu_kho"):
        raise GiaTriLoi(f"Trạng thái đơn hàng '{don['trang_thai']}' không hợp lệ để giao")

    don_cap_nhat = don_hang_repo.cap_nhat_giao_hang(don["id"], nhan_vien_nhan_id)
    if not don_cap_nhat:
        raise GiaTriLoi("Không thể cập nhật giao hàng, vui lòng thử lại")

    return don_cap_nhat


# ====================================================================
# 3. Tra cứu Đơn hàng (Khách hàng + Nhân viên)
# ====================================================================

def tra_cuu_theo_ma_van_don(ma_van_don: str) -> dict:
    """Tra cứu chi tiết đơn hàng theo mã vận đơn."""
    don = don_hang_repo.tim_theo_ma_van_don(ma_van_don.strip().upper())
    if not don:
        raise GiaTriLoi(f"Không tìm thấy đơn hàng với mã vận đơn: {ma_van_don}")
    return don


def tra_cuu_theo_sdt(sdt: str) -> list[dict]:
    """Tra cứu danh sách các đơn hàng theo số điện thoại người gửi hoặc người nhận."""
    return don_hang_repo.tim_theo_sdt(sdt.strip())


# ====================================================================
# 4. Hỗ trợ Phụ xe: Chất / Dỡ hàng (UC-26, UC-27)
# ====================================================================

def lay_danh_sach_cho_xep_xe(tuyen_id: str) -> list[dict]:
    """UC-26: Phụ xe xem các đơn hàng đang chờ chất lên xe tại tuyến này."""
    return don_hang_repo.lay_danh_sach_cho_xep_xe(tuyen_id)


def xac_nhan_chat_hang(don_hang_id: str, chuyen_id: str) -> dict:
    """UC-26: Phụ xe chất hàng lên xe của chuyến cụ thể."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")

    if don["trang_thai"] != "cho_van_chuyen":
        raise GiaTriLoi(f"Đơn hàng đang ở trạng thái '{don['trang_thai']}', không thể chất lên xe")

    don_cap_nhat = don_hang_repo.cap_nhat_chat_hang_len_chuyen(don_hang_id, chuyen_id)
    if not don_cap_nhat:
        raise GiaTriLoi("Không thể cập nhật chất hàng lên xe")
    return don_cap_nhat


def danh_sach_cho_chat(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """UC-26 bước 1 (mục 10.2): đơn `cho_van_chuyen` cùng tuyến với chuyến, còn
    chờ TẠI ĐIỂM phụ xe đang đứng, đơn cũ hiện trước (chỉ để tham khảo).

    Khác lay_danh_sach_cho_xep_xe() (route gui_hang.py, chỉ lọc theo tuyến):
    phụ xe gắn với 1 xe nên được kiểm tra đúng chuyến của mình và lọc thêm
    theo điểm hiện tại."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("chua_khoi_hanh", "dang_chay"):
        raise GiaTriLoi("Chuyến không ở trạng thái phù hợp để chất hàng")

    diem = diem_hien_tai(chuyen)
    don_cua_tuyen = don_hang_repo.lay_danh_sach_cho_xep_xe(chuyen["tuyen_id"])
    return [d for d in don_cua_tuyen if str(d["diem_gui_id"]) == str(diem["diem_don_tra_id"])]


def xac_nhan_chat_hang_cua_phu_xe(don_hang_id: str, chuyen_id: str, nguoi_dung_id: str) -> None:
    """UC-26 bước 3-4: phụ xe bấm xác nhận đã chất đơn lên xe → gán
    `chuyen_id` = chuyến này (bước DUY NHẤT xác định đơn đi chuyến nào, mục
    10.2), chuyển `da_len_xe`. Không kiểm tra sức chứa — phụ xe tự đánh giá
    khoang hàng thực tế."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("chua_khoi_hanh", "dang_chay"):
        raise GiaTriLoi("Chuyến không ở trạng thái phù hợp để chất hàng")

    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Không tìm thấy đơn hàng")
    if don["trang_thai"] != "cho_van_chuyen" or don["chuyen_id"] is not None:
        raise GiaTriLoi("Đơn hàng không ở trạng thái chờ chất lên chuyến")
    if str(don["tuyen_id"]) != str(chuyen["tuyen_id"]):
        raise GiaTriLoi("Đơn hàng không cùng tuyến với chuyến này")

    if not don_hang_repo.chat_len_chuyen_neu_dang_cho(don_hang_id, chuyen_id):
        raise GiaTriLoi("Đơn hàng vừa được chất lên chuyến khác, vui lòng tải lại danh sách")


def danh_sach_cho_do(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """UC-27 (mục 8.2 điểm 9): đơn đang trên xe (`da_len_xe`) cần dỡ tại đúng
    điểm phụ xe đang đứng. Cho phép cả chuyến `hoan_thanh` — xác nhận đến
    điểm cuối chuyển chuyến sang hoan_thanh, nhưng hàng nhận tại điểm cuối
    đó vẫn cần dỡ nốt ngay sau đó."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến không ở trạng thái phù hợp để dỡ hàng")

    diem = diem_hien_tai(chuyen)
    return don_hang_repo.tim_don_can_do_tai_diem(chuyen_id, diem["diem_don_tra_id"])


def xac_nhan_do_hang_cua_phu_xe(don_hang_id: str, nguoi_dung_id: str) -> None:
    """UC-27: phụ xe bấm xác nhận đã dỡ hàng → `cho_lay`, ghi
    `thoi_gian_den_diem_nhan` (mốc bắt đầu tính 7/14 ngày của UC-46).

    Tiền điều kiện (spec): đơn `da_len_xe` và xe ĐÃ TỚI điểm nhận của đơn —
    chặn dỡ nhầm đơn của điểm còn phía sau."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Không tìm thấy đơn hàng")
    if not don["chuyen_id"]:
        raise GiaTriLoi("Đơn hàng chưa từng được chất lên chuyến nào")

    chuyen = lay_chuyen_cua_phu_xe(str(don["chuyen_id"]), nguoi_dung_id)
    if chuyen["trang_thai"] not in ("dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến không ở trạng thái phù hợp để dỡ hàng")
    if don["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Đơn hàng không ở trạng thái đang trên xe")

    da_toi = {str(d["diem_don_tra_id"]) for d in chuyen_xe_repo.lay_diem_da_xac_nhan(str(chuyen["id"]))}
    if str(don["diem_nhan_id"]) not in da_toi:
        raise GiaTriLoi("Xe chưa tới điểm nhận của đơn hàng này")

    if not don_hang_repo.do_hang_neu_dang_tren_xe(don_hang_id):
        raise GiaTriLoi("Đơn hàng vừa được dỡ hoặc đổi trạng thái, vui lòng tải lại")


def bao_that_lac(don_hang_id: str, mo_ta: str, nguoi_dung_id: str) -> None:
    """UC-28: phụ xe ghi nhận thất lạc/hư hỏng phát hiện lúc chất (UC-26) hoặc
    dỡ (UC-27) hàng — KHÔNG đổi trạng thái đơn, không chặn UC-26/27.

    Quyền: đơn đã gắn chuyến → phải là chuyến của chính phụ xe; đơn còn chờ
    chất (`cho_van_chuyen`, chưa có chuyến — hư hỏng phát hiện ngay lúc cầm
    kiện hàng lên xe) → phụ xe phải có chuyến của xe mình cùng tuyến.
    Báo cáo chuyển tới nhân viên gửi hàng đã tạo đơn (mục UC-28 bước 2)."""
    mo_ta = mo_ta.strip()
    if not mo_ta:
        raise GiaTriLoi("Vui lòng mô tả tình trạng thất lạc/hư hỏng")

    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Không tìm thấy đơn hàng")

    if don["chuyen_id"]:
        lay_chuyen_cua_phu_xe(str(don["chuyen_id"]), nguoi_dung_id)
    else:
        if don["trang_thai"] != "cho_van_chuyen":
            raise GiaTriLoi("Đơn hàng không ở giai đoạn chất/dỡ hàng")
        chuyen_cua_toi = chuyen_xe_service.danh_sach_chuyen_cua_toi(nguoi_dung_id)
        if not any(str(c["tuyen_id"]) == str(don["tuyen_id"]) for c in chuyen_cua_toi):
            raise KhongDuQuyen("Đơn hàng này không thuộc tuyến xe của bạn")

    bao_cao_repo.tao(don_hang_id, nguoi_dung_id, mo_ta)

    # Ghi DB TRƯỚC rồi mới đẩy real-time (cùng thứ tự chuyen_xe_service._gui_thong_bao).
    noi_dung = f"Phụ xe báo hàng {don['ma_van_don']} thất lạc/hư hỏng: {mo_ta}"
    thong_bao_repo.tao(str(don["nhan_vien_gui_id"]), noi_dung)
    broadcast_sync(str(don["nhan_vien_gui_id"]), noi_dung)


def xac_nhan_do_hang(don_hang_id: str) -> dict:
    """UC-27: Phụ xe dỡ hàng xuống điểm nhận, bắt đầu tính hạn chờ lấy."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")

    if don["trang_thai"] != "da_len_xe":
        raise GiaTriLoi("Đơn hàng chưa được xếp lên xe để dỡ")

    don_cap_nhat = don_hang_repo.cap_nhat_do_hang_tai_diem(don_hang_id)
    if not don_cap_nhat:
        raise GiaTriLoi("Không thể cập nhật dỡ hàng")
    return don_cap_nhat


# ====================================================================
# 5. Xử lý Hàng chờ quá lâu tại Điểm nhận (UC-25, UC-46)
# ====================================================================

def lay_danh_sach_hang_cho_tai_diem(diem_nhan_id: str | None = None) -> list[dict]:
    """UC-25: Nhân viên quầy xem danh sách hàng đang chờ nhận / cảnh báo / tồn kho tại văn phòng mình (hoặc toàn bộ nếu diem_nhan_id là None)."""
    return don_hang_repo.lay_danh_sach_hang_cho_tai_diem(diem_nhan_id)


def cap_nhat_thong_bao_nguoi_nhan(don_hang_id: str, da_thong_bao: bool) -> dict:
    """UC-25: Ghi nhận nhân viên quầy đã liên lạc thành công với người nhận."""
    don = don_hang_repo.tim_theo_id(don_hang_id)
    if not don:
        raise GiaTriLoi("Đơn hàng không tồn tại")

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
) -> list[dict]:
    """Lấy danh sách các đơn hàng mới nhất để hiển thị tại quầy."""
    return don_hang_repo.lay_danh_sach_don_gan_day(
        limit=limit,
        diem_gui_id=diem_gui_id,
        trang_thai=trang_thai,
        tu_khoa=tu_khoa,
    )


def thong_ke_hang_tai_diem(diem_id: str | None = None) -> dict:
    """UC-39: Thống kê đơn hàng và doanh thu tại văn phòng (hoặc toàn bộ nếu diem_id là None)."""
    if diem_id:
        diem = dia_diem_repo.tim_diem_don_tra_theo_id(diem_id)
        if not diem:
            raise GiaTriLoi("Điểm/văn phòng không tồn tại")
    return don_hang_repo.thong_ke_hang_tai_diem(diem_id)

