"""Lịch chạy định kỳ — UC-18, NGHIEP_VU.md mục 3.5. Đây là nơi quản lý "lên lịch"
(tuyến + chiều + giờ + loại xe) và chủ động sinh chuyen_xe cho 1 khoảng ngày cụ
thể từ mỗi lịch — KHÔNG có job nền tự động: quản lý bấm "Sinh chuyến" mỗi khi
cần thêm, chọn hẳn ngày bắt đầu/kết thúc thay vì đếm N ngày trừu tượng.
"""

import datetime
from zoneinfo import ZoneInfo

import psycopg2.errors

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import gia_ve_repository as gia_ve_repo
from app.repositories import lich_chay_repository as repo
from app.repositories import xe_repository as xe_repo
from app.utils.loi import GiaTriLoi

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
SO_NGAY_TOI_DA_MOI_LAN = 180  # chặn nhỡ tay chọn khoảng quá dài, VD gõ nhầm năm


def _kiem_tra_loai_xe(loai_xe_id: str) -> None:
    if not xe_repo.tim_loai_xe_theo_id(loai_xe_id):
        raise GiaTriLoi("Loại xe không tồn tại")


def _bao_loi_neu_trung(tuyen_id: str, chieu: str, gio_khoi_hanh, loai_xe_id: str, tru_id: str | None = None) -> None:
    if repo.tim_trung(tuyen_id, chieu, gio_khoi_hanh, loai_xe_id, tru_id):
        raise GiaTriLoi("Đã có lịch chạy cùng tuyến, chiều, giờ khởi hành và loại xe này")


def tao_lich_chay(tuyen_id: str, chieu: str, gio_khoi_hanh, loai_xe_id: str) -> dict:
    if not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến không tồn tại")
    # Tiền điều kiện UC-18: tuyến phải có ít nhất 1 giá vé, nếu không khách không thể đặt vé cho các chuyến sinh ra
    if not gia_ve_repo.danh_sach_gia_ve(tuyen_id):
        raise GiaTriLoi("Tuyến này chưa có giá vé nào — hãy cấu hình giá vé (mục Giá vé) trước khi lập lịch chạy")
    _kiem_tra_loai_xe(loai_xe_id)
    _bao_loi_neu_trung(tuyen_id, chieu, gio_khoi_hanh, loai_xe_id)

    lich_id = repo.tao(tuyen_id, chieu, gio_khoi_hanh, loai_xe_id)
    return repo.tim_theo_id(str(lich_id))


def sua_lich_chay(lich_id: str, chieu: str, gio_khoi_hanh, loai_xe_id: str) -> dict:
    lich = repo.tim_theo_id(lich_id)
    if not lich:
        raise GiaTriLoi("Không tìm thấy lịch chạy")
    _kiem_tra_loai_xe(loai_xe_id)
    _bao_loi_neu_trung(str(lich["tuyen_id"]), chieu, gio_khoi_hanh, loai_xe_id, tru_id=lich_id)

    # Lịch đã sinh chuyến thì khóa sửa: chuyến cũ giữ nguyên giờ/chiều/loại xe cũ nên
    # lịch và chuyến sẽ lệch nhau, và những ngày đã có chuyến sẽ không bao giờ được sinh
    # lại theo lịch mới (chống trùng theo lịch + ngày). Muốn đổi: ngừng áp dụng + tạo lịch mới.
    if lich["so_chuyen_da_sinh"] > 0:
        raise GiaTriLoi(
            f"Lịch này đã sinh {lich['so_chuyen_da_sinh']} chuyến nên không sửa được — "
            "hãy ngừng áp dụng lịch này rồi tạo lịch mới"
        )
    repo.sua(lich_id, chieu, gio_khoi_hanh, loai_xe_id)
    return repo.tim_theo_id(lich_id)


def doi_ap_dung(lich_id: str, dang_ap_dung: bool) -> dict:
    if not repo.tim_theo_id(lich_id):
        raise GiaTriLoi("Không tìm thấy lịch chạy")
    # dang_ap_dung = false chỉ ngừng sinh chuyến mới, không hủy/đụng các chuyến đã sinh
    repo.doi_ap_dung(lich_id, dang_ap_dung)
    return repo.tim_theo_id(lich_id)


def danh_sach_lich_chay(tuyen_id: str | None = None) -> list[dict]:
    return repo.danh_sach(tuyen_id)


def xoa_lich_chay(lich_id: str) -> None:
    if not repo.tim_theo_id(lich_id):
        raise GiaTriLoi("Không tìm thấy lịch chạy")
    try:
        repo.xoa(lich_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: lịch này đã sinh chuyến — hãy ngừng áp dụng thay vì xóa")


def sinh_chuyen_theo_khoang_ngay(lich_id: str, tu_ngay: datetime.date, den_ngay: datetime.date) -> dict:
    """UC-18 — quản lý chủ động sinh chuyen_xe cho 1 khoảng ngày cụ thể từ 1
    lịch. Bỏ qua ngày đã có sẵn (bấm nhiều lần/khoảng chồng nhau vẫn an toàn),
    nên không đổi giờ/loại xe của chuyến đã sinh dù sau đó lịch bị sửa. Trả về
    số chuyến mới sinh và số ngày đã có sẵn (bị bỏ qua)."""
    lich = repo.tim_theo_id(lich_id)
    if not lich:
        raise GiaTriLoi("Không tìm thấy lịch chạy")
    if not lich["dang_ap_dung"]:
        raise GiaTriLoi("Lịch này đã ngừng áp dụng — hãy bật lại trước khi sinh chuyến")
    if tu_ngay > den_ngay:
        raise GiaTriLoi("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")

    hom_nay = datetime.datetime.now(MUI_GIO_VN).date()
    if tu_ngay < hom_nay:
        raise GiaTriLoi("Không thể sinh chuyến cho ngày trong quá khứ")
    if (den_ngay - tu_ngay).days + 1 > SO_NGAY_TOI_DA_MOI_LAN:
        raise GiaTriLoi(f"Mỗi lần chỉ sinh tối đa {SO_NGAY_TOI_DA_MOI_LAN} ngày — hãy chia nhỏ khoảng ngày")

    so_sinh = 0
    so_da_co_san = 0
    ngay = tu_ngay
    while ngay <= den_ngay:
        if chuyen_xe_repo.da_co_chuyen_theo_ngay(lich_id, ngay):
            so_da_co_san += 1
        else:
            # gio_khoi_hanh lưu TIMESTAMPTZ nhưng session Postgres mặc định
            # Etc/UTC — phải gắn múi giờ VN tường minh, không gửi datetime "naive".
            gio_khoi_hanh = datetime.datetime.combine(ngay, lich["gio_khoi_hanh"], tzinfo=MUI_GIO_VN)
            chuyen_xe_repo.tao_chuyen_tu_lich_dinh_ky(
                str(lich["tuyen_id"]), lich["chieu"], str(lich["loai_xe_id"]), lich_id, gio_khoi_hanh
            )
            so_sinh += 1
        ngay += datetime.timedelta(days=1)

    return {"so_chuyen_moi_sinh": so_sinh, "so_ngay_da_co_san": so_da_co_san}
