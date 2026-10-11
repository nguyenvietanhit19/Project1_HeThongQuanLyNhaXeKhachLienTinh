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

from datetime import datetime, timedelta

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import nguoi_dung_repository as nd_repo
from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.repositories import thong_bao_repository as thong_bao_repo
from app.repositories import ve_repository as ve_repo
from app.services.websocket_manager import broadcast_sync, manager as ws_manager
from app.utils.loi import GiaTriLoi, KhongDuQuyen

repo = chuyen_xe_repo
LOAI_SU_CO_HOP_LE = ("loi_nha_xe", "loi_khach_quan")


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


def diem_hien_tai(chuyen: dict) -> dict:
    """Điểm phụ xe đang đứng: điểm cuối cùng đã xác nhận đến, hoặc điểm đầu
    tuyến nếu chưa xác nhận điểm nào (mục 8.2 điểm 1/5).

    Dùng chung cho khach_tai_diem_hien_tai() ở đây và
    gui_hang_service.danh_sach_cho_chat() — cả hai đều cần biết "điểm hiện
    tại" của cùng 1 chuyến."""
    diem_list = dia_diem_repo.danh_sach_diem_theo_tuyen(chuyen["tuyen_id"])
    if not diem_list:
        raise GiaTriLoi("Tuyến chưa có điểm đón/trả nào")

    da_xac_nhan = chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen["id"])
    if not da_xac_nhan:
        return diem_list[0]

    diem_id_hien_tai = da_xac_nhan[0]["diem_don_tra_id"]  # thu_tu DESC -> dòng đầu là mới nhất
    for diem in diem_list:
        if diem["diem_don_tra_id"] == diem_id_hien_tai:
            return diem
    raise GiaTriLoi("Dữ liệu điểm dừng không nhất quán với tuyến")


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

    ty_le_lap_day = [c["so_ve_ban"] / c["tong_ghe"] for c in chuyen_list if c["tong_ghe"]]

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

    chuyen_xe_repo.cap_nhat_xac_nhan_xuat_phat(chuyen_id)


def hanh_trinh(chuyen_id: str, nguoi_dung_id: str) -> list[dict]:
    """Toàn bộ điểm của tuyến, kèm cờ đã xác nhận đến hay chưa — dùng để
    giao diện hiển thị hành trình và biết điểm tiếp theo cần xác nhận
    (mục 8.2 điểm 5)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    diem_list = dia_diem_repo.danh_sach_diem_theo_tuyen(chuyen["tuyen_id"])
    da_xac_nhan = {d["diem_don_tra_id"]: d["gio_thuc_te"] for d in chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen_id)}

    return [
        {
            "diem_don_tra_id": diem["diem_don_tra_id"],
            "ten_diem": diem["ten"],
            "thu_tu": diem["thu_tu"],
            "da_toi": diem["diem_don_tra_id"] in da_xac_nhan,
            "gio_thuc_te": da_xac_nhan.get(diem["diem_don_tra_id"]),
        }
        for diem in diem_list
    ]


def xac_nhan_toi_diem(chuyen_id: str, diem_don_tra_id: str, nguoi_dung_id: str) -> bool:
    """Trả về True nếu đây là điểm cuối tuyến (chuyến chuyển hoan_thanh)."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến chưa xuất phát")

    diem_list = dia_diem_repo.danh_sach_diem_theo_tuyen(chuyen["tuyen_id"])
    diem_muc_tieu = next((d for d in diem_list if d["diem_don_tra_id"] == diem_don_tra_id), None)
    if diem_muc_tieu is None:
        raise GiaTriLoi("Điểm này không thuộc tuyến của chuyến")

    da_xac_nhan_ids = {d["diem_don_tra_id"] for d in chuyen_xe_repo.lay_diem_da_xac_nhan(chuyen_id)}
    if diem_don_tra_id in da_xac_nhan_ids:
        raise GiaTriLoi("Điểm này đã được xác nhận đến trước đó")

    # Điểm đầu tuyến (thu_tu nhỏ nhất) là nơi xe xuất phát (UC-15), không
    # phải điểm "đến" — các điểm còn lại phải xác nhận đúng thứ tự, không
    # được nhảy cóc bỏ qua 1 điểm giữa đường.
    con_lai = [d for d in diem_list[1:] if d["diem_don_tra_id"] not in da_xac_nhan_ids]
    if not con_lai or diem_muc_tieu["diem_don_tra_id"] != con_lai[0]["diem_don_tra_id"]:
        raise GiaTriLoi("Phải xác nhận lần lượt theo đúng thứ tự các điểm trên tuyến")

    chuyen_xe_repo.them_lich_su_diem_dung(chuyen_id, diem_don_tra_id)

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
    if loai_su_co not in LOAI_SU_CO_HOP_LE:
        raise GiaTriLoi("Nguyên nhân sự cố không hợp lệ")

    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chỉ báo được sự cố khi chuyến đang chạy")

    chuyen_xe_repo.cap_nhat_gap_su_co(chuyen_id, loai_su_co, ly_do)
    chuyen_xe_repo.gan_co_xung_dot_vi_tri_cho_chuyen_tuong_lai(chuyen["xe_id"], chuyen_id)

    # mục 8.1 điểm 4 — báo khách đang có vé active trên chuyến này.
    # Báo điều độ viên phụ trách điểm xuất phát (mục 8.2 điểm 7) CHƯA làm
    # được ở đây vì hệ thống chưa có bảng phạm vi văn phòng của điều độ
    # viên (ho_so_can_bo_diem) lẫn tài khoản điều độ viên nào — thuộc
    # phần chưa xây (CONTRIBUTING.md, "người 4").
    noi_dung = "Chuyến bạn đang đi gặp sự cố dọc đường, nhà xe đang xử lý"
    for khach in ve_repo.tim_khach_hang_dang_hoat_dong_theo_chuyen(chuyen_id):
        _gui_thong_bao(khach["khach_hang_id"], noi_dung)


# ============================================================
# CÁC HÀM NGHIỆP VỤ CHO ĐIỀU ĐỘ VIÊN (Người 4: UC-44, UC-45, UC-19, UC-20, UC-40, UC-39)
# ============================================================

def _lay_van_phong_dieu_do_vien(nguoi_dung_id: str) -> str:
    """Lấy van_phong_id (diem_don_tra_id loại van_phong) từ ho_so_can_bo_diem.
    Điều độ viên bắt buộc phải có van_phong gắn vào.
    """
    ho_so = nd_repo.lay_ho_so_can_bo(nguoi_dung_id)
    if not ho_so or not ho_so.get("van_phong_id"):
        raise GiaTriLoi("Tài khoản chưa được gắn văn phòng phụ trách")
    return ho_so["van_phong_id"]


def lay_danh_sach_chuyen(nguoi_dung_id: str) -> list[dict]:
    """Chuyến chua_khoi_hanh xuất phát từ văn phòng điều độ viên phụ trách.
    Sắp theo gio_khoi_hanh tăng dần (gần nhất lên đầu).
    """
    van_phong_id = _lay_van_phong_dieu_do_vien(nguoi_dung_id)
    return repo.lay_danh_sach_chuyen_theo_diem_khoi_hanh(van_phong_id)


def lay_chuyen_theo_id(chuyen_id: str) -> dict:
    """Lấy thông tin chi tiết một chuyến theo ID."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    return chuyen


def lay_xe_du_dieu_kien(chuyen_id: str) -> list[dict]:
    """Trả xe đủ điều kiện gán vào chuyến:
    - Đúng loai_xe_id của chuyến (cứng, không cho phép khác loại)
    - trang_thai = 'hoat_dong'
    - tuyen_id IS NULL (xe dự phòng) hoặc trùng tuyen_id của chuyến
    - Không trùng lịch (buffer 60 phút mỗi đầu)
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")

    gio_kh: datetime = chuyen["gio_khoi_hanh"]
    gio_bat_dau = (gio_kh - timedelta(hours=1)).isoformat()
    gio_ket_thuc = (gio_kh + timedelta(hours=1)).isoformat()

    return repo.lay_xe_du_loai_va_tuyen(
        chuyen["loai_xe_id"],
        chuyen["tuyen_id"],
        gio_bat_dau,
        gio_ket_thuc,
    )


def gan_xe_cho_chuyen(chuyen_id: str, xe_id: str) -> None:
    """Validate rồi gán xe_id vào chuyến (UC-44)."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "chua_khoi_hanh":
        raise GiaTriLoi("Chỉ gán xe được cho chuyến chưa khởi hành")

    xe_hop_le = lay_xe_du_dieu_kien(chuyen_id)
    xe_ids_hop_le = {str(xe["id"]) for xe in xe_hop_le}
    if xe_id not in xe_ids_hop_le:
        raise GiaTriLoi(
            "Xe không đủ điều kiện: sai loại xe, không đúng tuyến, "
            "trùng lịch, hoặc xe không hoạt động"
        )

    repo.gan_xe(chuyen_id, xe_id)


async def xu_ly_tu_dong_chuyen_dang_hoan() -> list[dict]:
    """UC-45: Quét các chuyến chưa khởi hành có gio_khoi_hanh <= now()
    nhưng xe_id IS NULL và dang_hoan = false.
    """
    chuyen_can_hoan = repo.lay_danh_sach_chuyen_can_hoan()
    ket_qua = []

    for chuyen in chuyen_can_hoan:
        chuyen_id = str(chuyen["id"])
        gio_cu: datetime = chuyen["gio_khoi_hanh"]
        gio_moi = gio_cu + timedelta(minutes=60)

        repo.bat_co_dang_hoan(chuyen_id, gio_moi)

        try:
            ve_list = ve_repo.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)
            gio_cu_str = gio_cu.strftime("%H:%M %d/%m/%Y")
            gio_moi_str = gio_moi.strftime("%H:%M %d/%m/%Y")
            ten_tuyen = chuyen.get("ten_tuyen") or "của quý khách"
            noi_dung = (
                f"Thông báo hoãn chuyến: Chuyến xe {ten_tuyen} dự kiến xuất phát lúc "
                f"{gio_cu_str} tạm thời bị hoãn do chưa thể bố trí xe. "
                f"Thời gian khởi hành dự kiến mới: {gio_moi_str}. "
                f"Quý khách có quyền yêu cầu hủy vé nhận hoàn 100% trong thời gian chờ."
            )
            for ve in ve_list:
                khach_id = ve.get("khach_hang_id")
                if khach_id:
                    await ws_manager.broadcast(str(khach_id), noi_dung)
        except Exception:
            pass

        ket_qua.append({
            "id": chuyen_id,
            "ten_tuyen": chuyen.get("ten_tuyen"),
            "gio_khoi_hanh_cu": gio_cu.isoformat(),
            "gio_khoi_hanh_moi": gio_moi.isoformat(),
        })

    return ket_qua


def lay_danh_sach_su_co(nguoi_dung_id: str | None = None) -> list[dict]:
    """Lấy danh sách các chuyến đang gap_su_co."""
    return repo.lay_danh_sach_chuyen_gap_su_co()


async def tiep_tuc_chuyen_su_co(chuyen_id: str) -> None:
    """UC-19: Tài xế sửa xong tại chỗ (<= 1h) hoặc đường đã thông -> tiếp tục chạy."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "gap_su_co":
        raise GiaTriLoi("Chuyến không ở trạng thái gặp sự cố")

    repo.tiep_tuc_sau_su_co(chuyen_id)


async def dieu_xe_thay_the_su_co(chuyen_id: str, xe_thay_the_id: str) -> None:
    """UC-19: Điều xe thay thế khẩn cấp giữa đường (lỗi nhà xe > 1h)."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "gap_su_co":
        raise GiaTriLoi("Chuyến không ở trạng thái gặp sự cố")

    repo.dieu_xe_thay_the_su_co(chuyen_id, xe_thay_the_id)

    try:
        ve_list = ve_repo.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)
        noi_dung = (
            f"Thông báo: Chuyến xe {chuyen.get('ten_tuyen', '')} đã được điều xe cứu trợ thay thế. "
            f"Hành trình đang được tiếp tục."
        )
        for ve in ve_list:
            khach_id = ve.get("khach_hang_id")
            if khach_id:
                await ws_manager.broadcast(str(khach_id), noi_dung)
    except Exception:
        pass


async def huy_chuyen_su_co_khach_quan(chuyen_id: str) -> None:
    """UC-19 -> UC-21: Hủy chuyến do sự cố khách quan (thiên tai, sạt lở) không thể hoàn thành."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "gap_su_co":
        raise GiaTriLoi("Chuyến không ở trạng thái gặp sự cố")
    if chuyen["loai_su_co"] != "loi_khach_quan":
        raise GiaTriLoi("Chỉ sự cố khách quan (thiên tai/sạt lở) mới được phép hủy chuyến. Lỗi nhà xe phải luôn điều xe thay thế.")

    repo.huy_chuyen_do_su_co_khach_quan(chuyen_id)

    ve_list = ve_repo.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)
    noi_dung = (
        f"Thông báo: Chuyến xe {chuyen.get('ten_tuyen', '')} buộc phải hủy do sự cố bất khả kháng ngoài ý muốn. "
        f"Toàn bộ vé đã thanh toán sẽ được hoàn tiền 100%."
    )
    for ve in ve_list:
        khach_id = ve.get("khach_hang_id")
        if khach_id:
            try:
                await ws_manager.broadcast(str(khach_id), noi_dung)
            except Exception:
                pass


def lay_danh_sach_chuyen_can_doi_xe(nguoi_dung_id: str) -> list[dict]:
    """Các chuyến chua_khoi_hanh đã có xe nhưng cần đổi xe thay thế."""
    van_phong_id = _lay_van_phong_dieu_do_vien(nguoi_dung_id)
    return repo.lay_danh_sach_chuyen_can_doi_xe(van_phong_id)


def lay_xe_thay_the_du_dieu_kien(chuyen_id: str) -> list[dict]:
    """UC-20: Liệt kê xe thay thế cùng loại xe, không trùng lịch."""
    return lay_xe_du_dieu_kien(chuyen_id)


async def gan_xe_thay_the(chuyen_id: str, xe_thay_the_id: str) -> list[str]:
    """UC-20: Gán xe_thuc_te_id cho chuyến hiện tại và toàn bộ chuỗi chuyến sau cùng xe gốc."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "chua_khoi_hanh":
        raise GiaTriLoi("Chỉ đổi xe trước giờ khởi hành cho chuyến chưa xuất phát")
    if not chuyen["xe_id"]:
        raise GiaTriLoi("Chuyến chưa có xe gốc. Dùng UC-44 để gán xe lần đầu.")

    affected_ids = repo.gan_xe_thay_the_truoc_gio(chuyen_id, xe_thay_the_id)

    try:
        ve_list = ve_repo.tim_ve_da_thanh_toan_theo_chuyen(chuyen_id)
        noi_dung = (
            f"Thông báo: Chuyến xe {chuyen.get('ten_tuyen', '')} sẽ được vận hành bởi xe thay thế. "
            f"Vị trí chỗ ngồi của quý khách được giữ nguyên không đổi."
        )
        for ve in ve_list:
            khach_id = ve.get("khach_hang_id")
            if khach_id:
                await ws_manager.broadcast(str(khach_id), noi_dung)
    except Exception:
        pass

    return affected_ids


async def hoan_chuyen_do_chua_co_xe_thay(chuyen_id: str, gio_khoi_hanh_moi: datetime) -> None:
    """UC-20: Nếu xe thay thế trễ > 30 phút hoặc chưa có xe -> chuyển sang 'đang hoãn'."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")

    repo.hoan_chuyen_truoc_gio(chuyen_id, gio_khoi_hanh_moi)


def lay_danh_sach_chuyen_dang_chay_thay(nguoi_dung_id: str | None = None) -> list[dict]:
    """Danh sách các chuyến đang có xe_thuc_te_id (chạy thay bằng xe khác)."""
    return repo.lay_danh_sach_chuyen_dang_chay_thay()


async def gan_lai_xe_goc(chuyen_id: str) -> list[str]:
    """UC-40: Xe gốc đã sửa xong và hoạt động trở lại. Đặt xe_thuc_te_id = NULL."""
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if not chuyen.get("xe_thuc_te_id"):
        raise GiaTriLoi("Chuyến này không có xe chạy thay")

    affected_ids = repo.gan_lai_xe_goc(chuyen_id)
    return affected_ids


def lay_thong_ke_van_hanh(tu_ngay: str, den_ngay: str, nguoi_dung_id: str | None = None) -> dict:
    """UC-39: Thống kê hiệu suất vận hành trong khoảng thời gian."""
    return repo.thong_ke_van_hanh(tu_ngay, den_ngay)

