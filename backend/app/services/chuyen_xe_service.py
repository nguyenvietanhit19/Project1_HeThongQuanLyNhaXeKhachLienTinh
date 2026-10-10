"""Vòng đời chuyến — phần dùng bởi phụ xe (UC-15, UC-16, UC-17), NGHIEP_VU.md
mục 3.2/3.3/4/8.2.

Gán xe cho chuyến (UC-44), đổi xe khi hỏng (UC-19/20/40), sinh chuyến định
kỳ (UC-18) thuộc điều độ viên/quản lý — chưa cài đặt ở đây (CONTRIBUTING.md
mục 5.6 liệt kê các hàm này do "người 4" cung cấp cho "người 3"; ở đây gộp
chung 1 file vì cùng đang xây tuần tự).

Đọc danh sách điểm/thứ tự của 1 tuyến qua `dia_diem_repository` (vanh, UC-29
đến 31, #7) thay vì tự viết repository riêng — tránh trùng lặp với domain
"quản lý danh mục" đã có sẵn.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.repositories import ve_repository as ve_repo
from app.services.websocket_manager import broadcast_sync
from app.utils.loi import GiaTriLoi, KhongDuQuyen

logger = logging.getLogger(__name__)

LOAI_SU_CO_HOP_LE = ("loi_nha_xe", "loi_khach_quan")
GIO_VIET_NAM = timezone(timedelta(hours=7))


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _gui_thong_bao(nguoi_nhan_id: str, noi_dung: str) -> None:
    """Ghi vào DB TRƯỚC (khách offline vẫn đọc lại được sau,
    DATABASE.md mục 6.1) rồi mới đẩy real-time — đúng thứ tự
    websocket_manager.py yêu cầu."""
    thong_bao_repo.tao(nguoi_nhan_id, noi_dung)
    broadcast_sync(nguoi_nhan_id, noi_dung)


def lay_chuyen_cua_phu_xe(chuyen_id: str, nguoi_dung_id: str) -> dict:
    """Kiểm tra chuyến tồn tại VÀ thuộc đúng phụ xe đang thao tác — suy ra
    live qua biên chế xe (mục 3.2), không có bảng gán riêng theo chuyến.

    Dùng chung cho mọi service cần xác thực quyền phụ xe trên 1 chuyến cụ
    thể (ve_service khi soát vé, gui_hang_service khi chất/dỡ hàng) —
    không viết lại logic này ở nơi khác."""
    chuyen = chuyen_xe_repo.tim_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")

    nhan_su = nhan_su_repo.tim_theo_nguoi_dung_id(nguoi_dung_id)
    if not nhan_su or nhan_su["chuc_danh"] != "phu_xe":
        raise KhongDuQuyen("Tài khoản không phải phụ xe")

    xe_id_cua_toi = nhan_su_repo.tim_xe_dang_gan(nhan_su["id"])
    if not xe_id_cua_toi or chuyen["xe_id"] != xe_id_cua_toi:
        raise KhongDuQuyen("Chuyến này không thuộc về bạn")

    return chuyen


def diem_theo_chieu(chuyen: dict) -> list[dict]:
    """Các điểm của tuyến theo ĐÚNG HƯỚNG xe chạy: điểm xuất phát đứng đầu,
    điểm cuối đứng cuối.

    `tuyen_diem_don_tra.thu_tu` luôn lưu theo chiều xuôi; chuyến `nguoc` đi
    theo `thu_tu` giảm dần (THAY_DOI_TUYEN_2_CHIEU.md mục 3). Mọi nơi cần
    "điểm đầu / điểm cuối / điểm kế tiếp / điểm phía sau" phải lấy từ danh
    sách này, không tự giả định `thu_tu` tăng = hướng xe đi. Giá trị `thu_tu`
    gốc trong từng phần tử được giữ nguyên (dùng cho truy vấn SQL)."""
    diem_list = sorted(dia_diem_repo.danh_sach_diem_theo_tuyen(chuyen["tuyen_id"]), key=lambda d: d["thu_tu"])
    if chuyen["chieu"] == "nguoc":
        diem_list.reverse()
    return diem_list


def diem_hien_tai(chuyen: dict) -> dict:
    """Điểm phụ xe đang đứng: điểm cuối cùng đã xác nhận đến, hoặc điểm đầu
    tuyến nếu chưa xác nhận điểm nào (mục 8.2 điểm 1/5).

    Dùng chung cho khach_tai_diem_hien_tai() ở đây và
    gui_hang_service.danh_sach_cho_chat() — cả hai đều cần biết "điểm hiện
    tại" của cùng 1 chuyến."""
    diem_list = diem_theo_chieu(chuyen)
    if not diem_list:
        raise GiaTriLoi("Tuyến chưa có điểm đón/trả nào")

    da_xac_nhan_ids = {d["diem_don_tra_id"] for d in chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen["id"])}
    if not da_xac_nhan_ids:
        return diem_list[0]

    # Điểm hiện tại = điểm xa nhất THEO HƯỚNG ĐI trong số các điểm đã xác nhận đến.
    diem_da_toi = [d for d in diem_list if d["diem_don_tra_id"] in da_xac_nhan_ids]
    if not diem_da_toi:
        raise GiaTriLoi("Dữ liệu điểm dừng không nhất quán với tuyến")
    return diem_da_toi[-1]


def chi_tiet_cho_phu_xe(chuyen_id: str, nguoi_dung_id: str) -> dict:
    """Thông tin hiển thị đầu trang (tuyến, biển số, giờ, trạng thái) cho
    ĐÚNG 1 chuyến, không lọc theo trạng thái như danh_sach_chuyen_cua_toi()
    — cần để giao diện chuyen-dang-chay.html vẫn tải được header ngay sau
    khi chuyến vừa chuyển hoan_thanh (không còn nằm trong danh sách
    'chuyến của tôi' nữa, nhưng phụ xe vẫn đang xử lý nốt khách/hàng)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    xe_id_hien_thi = chuyen["xe_thuc_te_id"] or chuyen["xe_id"]
    ten_tuyen_va_xe = chuyen_xe_repo.lay_ten_tuyen_va_bien_so(chuyen["tuyen_id"], xe_id_hien_thi)
    return {
        "id": chuyen["id"],
        "tuyen_ten": ten_tuyen_va_xe["tuyen_ten"],
        "bien_so": ten_tuyen_va_xe["bien_so"],
        "gio_khoi_hanh": chuyen["gio_khoi_hanh"],
        "trang_thai": chuyen["trang_thai"],
        "dang_hoan": chuyen["dang_hoan"],
    }


def danh_sach_chuyen_cua_toi(nguoi_dung_id: str) -> list[dict]:
    nhan_su = nhan_su_repo.tim_theo_nguoi_dung_id(nguoi_dung_id)
    if not nhan_su or nhan_su["chuc_danh"] != "phu_xe":
        raise KhongDuQuyen("Tài khoản không phải phụ xe")

    xe_id = nhan_su_repo.tim_xe_dang_gan(nhan_su["id"])
    if not xe_id:
        return []  # chưa được biên chế vào xe nào (mục 3.2)

    return chuyen_xe_repo.tim_chuyen_cua_xe(xe_id)


def thong_ke_cua_toi(nguoi_dung_id: str, tu_ngay, den_ngay) -> dict:
    """UC-39 — phụ xe chỉ xem thống kê các chuyến của xe mình (mục 8.2/8.7
    'switch theo actor' trong UML_DIAGRAMS.md AD_UC39_ThongKe). `den_ngay`
    là mốc loại trừ (exclusive) — Route cộng thêm 1 ngày trước khi gọi
    xuống đây để bao trọn ngày kết thúc theo lựa chọn của người dùng."""
    if tu_ngay >= den_ngay:
        raise GiaTriLoi("Ngày bắt đầu phải trước ngày kết thúc")

    nhan_su = nhan_su_repo.tim_theo_nguoi_dung_id(nguoi_dung_id)
    if not nhan_su or nhan_su["chuc_danh"] != "phu_xe":
        raise KhongDuQuyen("Tài khoản không phải phụ xe")

    xe_id = nhan_su_repo.tim_xe_dang_gan(nhan_su["id"])
    if not xe_id:
        return {"so_chuyen": 0, "doanh_thu": 0, "ty_le_lap_day_trung_binh": 0, "so_chuyen_su_co": 0, "so_chuyen_huy": 0}

    chuyen_list = chuyen_xe_repo.thong_ke_theo_xe(xe_id, tu_ngay, den_ngay)
    if not chuyen_list:
        return {"so_chuyen": 0, "doanh_thu": 0, "ty_le_lap_day_trung_binh": 0, "so_chuyen_su_co": 0, "so_chuyen_huy": 0}

    # Chuyến đã hủy không tính vào tỷ lệ lấp đầy (không chạy nên không có "ghế bán được" để so).
    ty_le_lap_day = [c["so_ve_ban"] / c["tong_ghe"] for c in chuyen_list if c["tong_ghe"] and c["trang_thai"] != "da_huy"]

    return {
        "so_chuyen": len(chuyen_list),
        "doanh_thu": sum(c["doanh_thu"] for c in chuyen_list),
        "ty_le_lap_day_trung_binh": sum(ty_le_lap_day) / len(ty_le_lap_day) if ty_le_lap_day else 0,
        "so_chuyen_su_co": sum(1 for c in chuyen_list if c["trang_thai"] == "gap_su_co"),
        "so_chuyen_huy": sum(1 for c in chuyen_list if c["trang_thai"] == "da_huy"),
    }


def khach_tai_diem_hien_tai(chuyen_id: str, nguoi_dung_id: str) -> dict:
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] not in ("chua_khoi_hanh", "dang_chay", "hoan_thanh"):
        raise GiaTriLoi("Chuyến không ở trạng thái đang phục vụ khách")
    # Cho phép cả 'hoan_thanh' — xác nhận đến điểm CUỐI cùng lúc chuyển
    # chuyến sang hoan_thanh (mục 8.2 điểm 8), nhưng phụ xe vẫn cần xử lý
    # nốt khách xuống xe/hàng dỡ tại đúng điểm cuối đó ngay sau đó — không
    # thể chặn chỉ vì chuyến đã "xong" theo nghĩa xe đã tới đích.

    diem = diem_hien_tai(chuyen)
    return {
        "diem_don_tra_id": diem["diem_don_tra_id"],
        "ten_diem": diem["ten"],
        "khach_can_len": ve_repo.tim_ve_can_len_xe_tai_diem(chuyen_id, diem["diem_don_tra_id"]),
        "khach_can_xuong": ve_repo.tim_ve_can_xuong_xe_tai_diem(chuyen_id, diem["diem_don_tra_id"]),
    }


def xac_nhan_xuat_phat(chuyen_id: str, nguoi_dung_id: str) -> None:
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "chua_khoi_hanh":
        raise GiaTriLoi("Chuyến không ở trạng thái chưa khởi hành")
    # Mục 3.3 điểm 9: chuyến đang "hoãn" (chưa có xe thay thế) chưa được chạy — chờ điều độ viên tắt cờ hoãn.
    if chuyen.get("dang_hoan"):
        raise GiaTriLoi("Chuyến đang hoãn, chưa thể xác nhận xuất phát — chờ điều độ viên xử lý")
    # UC-15: chỉ được xác nhận đúng giờ hoặc muộn hơn, không xuất phát sớm.
    # (Repository kiểm lại ngay trong UPDATE bằng now() của DB.)
    if _bay_gio() < chuyen["gio_khoi_hanh"]:
        gio_vn = chuyen["gio_khoi_hanh"].astimezone(GIO_VIET_NAM).strftime("%H:%M %d/%m/%Y")
        raise GiaTriLoi(f"Chưa đến giờ khởi hành ({gio_vn}), không thể xác nhận xuất phát sớm")

    if not chuyen_xe_repo.cap_nhat_xac_nhan_xuat_phat(chuyen_id):
        raise GiaTriLoi("Chuyến vừa được xác nhận xuất phát hoặc đổi trạng thái, vui lòng tải lại")


def hanh_trinh(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """Toàn bộ điểm của tuyến, kèm cờ đã xác nhận đến hay chưa — dùng để
    giao diện hiển thị hành trình và biết điểm tiếp theo cần xác nhận
    (mục 8.2 điểm 5)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    diem_list = diem_theo_chieu(chuyen)
    da_xac_nhan = {d["diem_don_tra_id"]: d["gio_thuc_te"] for d in chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen_id)}
    # Giờ dự kiến tới từng điểm — cùng công thức với job no-show (ve_repository.tim_ve_qua_gio_len_xe):
    # chiều xuôi = mốc của điểm; chiều ngược = mốc cuối tuyến trừ mốc của điểm.
    moc_cuoi = max((d["thoi_gian_du_kien_phut"] for d in diem_list), default=0)

    def gio_du_kien(diem):
        phut = diem["thoi_gian_du_kien_phut"]
        return chuyen["gio_khoi_hanh"] + timedelta(minutes=phut if chuyen["chieu"] == "xuoi" else moc_cuoi - phut)

    return [
        {
            "diem_don_tra_id": diem["diem_don_tra_id"],
            "ten_diem": diem["ten"],
            "thu_tu": vi_tri,  # thứ tự THEO HƯỚNG ĐI (1 = điểm xuất phát), không phải thu_tu gốc của tuyến
            "da_toi": diem["diem_don_tra_id"] in da_xac_nhan,
            "gio_thuc_te": da_xac_nhan.get(diem["diem_don_tra_id"]),
            "gio_du_kien": gio_du_kien(diem),
        }
        for vi_tri, diem in enumerate(diem_list, start=1)
    ]


def xac_nhan_toi_diem(chuyen_id: str, diem_don_tra_id: str, nguoi_dung_id: str) -> bool:
    """Trả về True nếu đây là điểm cuối tuyến (chuyến chuyển hoan_thanh)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến chưa xuất phát")

    diem_list = diem_theo_chieu(chuyen)
    diem_muc_tieu = next((d for d in diem_list if d["diem_don_tra_id"] == diem_don_tra_id), None)
    if diem_muc_tieu is None:
        raise GiaTriLoi("Điểm này không thuộc tuyến của chuyến")

    da_xac_nhan_ids = {d["diem_don_tra_id"] for d in chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen_id)}
    if diem_don_tra_id in da_xac_nhan_ids:
        raise GiaTriLoi("Điểm này đã được xác nhận đến trước đó")

    # Điểm đầu theo hướng đi (xuôi: thu_tu nhỏ nhất, ngược: lớn nhất) là nơi xe xuất phát (UC-15), không
    # phải điểm "đến" — các điểm còn lại phải xác nhận đúng thứ tự, không
    # được nhảy cóc bỏ qua 1 điểm giữa đường.
    con_lai = [d for d in diem_list[1:] if d["diem_don_tra_id"] not in da_xac_nhan_ids]
    if not con_lai or diem_muc_tieu["diem_don_tra_id"] != con_lai[0]["diem_don_tra_id"]:
        raise GiaTriLoi("Phải xác nhận lần lượt theo đúng thứ tự các điểm trên tuyến")

    if not chuyen_xe_repo.them_lich_su_diem_dung(chuyen_id, diem_don_tra_id):
        raise GiaTriLoi("Điểm này đã được xác nhận đến trước đó")

    diem_cuoi_tuyen = diem_list[-1]["diem_don_tra_id"]
    da_hoan_thanh = diem_don_tra_id == diem_cuoi_tuyen
    if da_hoan_thanh:
        chuyen_xe_repo.cap_nhat_hoan_thanh(chuyen_id)

    # mục 8.2 điểm 5 — cập nhật ETA cho khách đang chờ đón ở các điểm PHÍA
    # SAU điểm vừa xác nhận (không phải toàn bộ khách trên chuyến).
    if not da_hoan_thanh:
        noi_dung = f"Xe vừa đến {diem_muc_tieu['ten']} — cập nhật giờ dự kiến đón bạn"
        for khach in ve_repo.tim_khach_cho_don_sau_diem(chuyen_id, diem_muc_tieu["thu_tu"]):
            _gui_thong_bao(khach["khach_hang_id"], noi_dung)

    return da_hoan_thanh


def bao_su_co(chuyen_id: str, loai_su_co: str, ly_do: str, nguoi_dung_id: str) -> None:
    """UC-17. Phụ xe chọn nguyên nhân theo thông tin tài xế cung cấp bằng lời."""
    if loai_su_co not in LOAI_SU_CO_HOP_LE:
        raise GiaTriLoi("Nguyên nhân sự cố không hợp lệ")
    if not ly_do.strip():
        raise GiaTriLoi("Vui lòng nhập mô tả sự cố")

    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chỉ báo được sự cố khi chuyến đang chạy")

    if not chuyen_xe_repo.cap_nhat_gap_su_co(chuyen_id, loai_su_co, ly_do):
        raise GiaTriLoi("Chuyến vừa được báo sự cố hoặc đổi trạng thái, vui lòng tải lại")
    chuyen_xe_repo.gan_co_xung_dot_vi_tri_cho_chuyen_tuong_lai(chuyen["xe_id"], chuyen_id)

    # mục 8.1 điểm 4 — báo khách đang có vé active trên chuyến này.
    noi_dung = "Chuyến bạn đang đi gặp sự cố dọc đường, nhà xe đang xử lý"
    for khach in ve_repo.tim_khach_hang_dang_hoat_dong_theo_chuyen(chuyen_id):
        _gui_thong_bao(khach["khach_hang_id"], noi_dung)

    _bao_dieu_do_vien_su_co(chuyen, loai_su_co, ly_do)


def _bao_dieu_do_vien_su_co(chuyen: dict, loai_su_co: str, ly_do: str) -> None:
    """UC-17 bước 4 (mục 8.2 điểm 7): điều độ viên nhận cảnh báo ngay. Ưu tiên
    người phụ trách văn phòng ở điểm xuất phát của chuyến; chưa ai phụ trách
    điểm đó thì báo toàn bộ điều độ viên để cảnh báo không bị bỏ sót. Sự cố đã
    được ghi (commit) nên lỗi gửi thông báo chỉ ghi log, không làm hỏng thao tác."""
    try:
        diem_xuat_phat = diem_theo_chieu(chuyen)[0]["diem_don_tra_id"]
        nguoi_nhan = chuyen_xe_repo.danh_sach_dieu_do_vien_tai_diem(str(diem_xuat_phat))
        if not nguoi_nhan:
            nguoi_nhan = nguoi_dung_repo.danh_sach_id_theo_vai_tro("dieu_do_vien", chi_dang_hoat_dong=True)
        nguyen_nhan = "lỗi nhà xe" if loai_su_co == "loi_nha_xe" else "lỗi khách quan"
        noi_dung = f"Chuyến {chuyen.get('ma') or chuyen['id']} gặp sự cố ({nguyen_nhan}): {ly_do.strip()}"
        for nguoi_id in nguoi_nhan:
            _gui_thong_bao(nguoi_id, noi_dung)
    except Exception:  # noqa: BLE001
        logger.exception("Không báo được điều độ viên về sự cố chuyến %s", chuyen["id"])
