"""Service chuyến xe — UC-44/UC-45/UC-19/UC-20/UC-40 (Người 4: Điều độ viên).

Quy tắc Service (ARCHITECTURE.md mục 2):
- Chứa toàn bộ quy tắc nghiệp vụ
- Gọi repository, không tự viết SQL
- Không import từ routes hay FastAPI Request/Response

Contract hàm cung cấp cho Người 3 (Phụ xe) — CONTRIBUTING.md mục 5.6:
  xac_nhan_xuat_phat(chuyen_id)
  xac_nhan_toi_diem(chuyen_id, diem_id)
  bao_su_co(chuyen_id, loai_su_co, ly_do)
"""

from datetime import datetime, timedelta, timezone

import json

from app.repositories import chuyen_xe_repository as repo
from app.repositories import nguoi_dung_repository as nd_repo
from app.repositories import ve_repository as ve_repo
from app.services.websocket_manager import manager as ws_manager
from app.utils.loi import GiaTriLoi


def _lay_van_phong_dieu_do_vien(nguoi_dung_id: str) -> str:
    """Lấy van_phong_id (diem_don_tra_id loại van_phong) từ ho_so_can_bo_diem.
    Điều độ viên bắt buộc phải có van_phong gắn vào.
    """
    ho_so = nd_repo.lay_ho_so_can_bo(nguoi_dung_id)
    if not ho_so or not ho_so.get("van_phong_id"):
        raise GiaTriLoi("Tài khoản chưa được gắn văn phòng phụ trách")
    return ho_so["van_phong_id"]


# ============================================================
# UC-44: Gán xe cho chuyến
# ============================================================

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

    Sắp: xe cố định tuyến trước, dự phòng sau (đã làm trong repository).
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")

    # Tính khung giờ kiểm tra trùng lịch: gio_khoi_hanh ± 60 phút
    # (thời gian di chuyển tối thiểu buffer — đủ để xe từ chuyến trước về kịp)
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
    """Validate rồi gán xe_id vào chuyến.

    Luồng (NGHIEP_VU.md UC-44):
    1. Chuyến tồn tại, trang_thai = 'chua_khoi_hanh'
    2. Xe có trong danh sách đủ điều kiện (loại đúng, không trùng lịch)
    3. Gán xe_id, tắt dang_hoan nếu đang hoãn
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "chua_khoi_hanh":
        raise GiaTriLoi("Chỉ gán xe được cho chuyến chưa khởi hành")

    # Kiểm tra xe có trong danh sách đủ điều kiện không
    xe_hop_le = lay_xe_du_dieu_kien(chuyen_id)
    xe_ids_hop_le = {str(xe["id"]) for xe in xe_hop_le}
    if xe_id not in xe_ids_hop_le:
        raise GiaTriLoi(
            "Xe không đủ điều kiện: sai loại xe, không đúng tuyến, "
            "trùng lịch, hoặc xe không hoạt động"
        )

    repo.gan_xe(chuyen_id, xe_id)
    # dang_hoan tự tắt trong repo.gan_xe nếu đang true


# ============================================================
# UC-45: Tự động chuyển "đang hoãn" khi tới giờ chưa gán xe (Job)
# ============================================================

async def xu_ly_tu_dong_chuyen_dang_hoan() -> list[dict]:
    """UC-45: Quét các chuyến chưa khởi hành có gio_khoi_hanh <= now()
    nhưng xe_id IS NULL và dang_hoan = false.

    Thực hiện theo NGHIEP_VU.md mục 3.3 và UC-45:
    1. Bật dang_hoan = true
    2. Dời gio_khoi_hanh sang thời điểm dự kiến mới (tạm thời +60 phút)
    3. Gửi thông báo WebSocket cho khách đã có vé trên chuyến này
    """
    chuyen_can_hoan = repo.lay_danh_sach_chuyen_can_hoan()
    ket_qua = []

    for chuyen in chuyen_can_hoan:
        chuyen_id = str(chuyen["id"])
        gio_cu: datetime = chuyen["gio_khoi_hanh"]
        gio_moi = gio_cu + timedelta(minutes=60)

        # 1 + 2: Cập nhật cờ dang_hoan và giờ dự kiến mới
        repo.bat_co_dang_hoan(chuyen_id, gio_moi)

        # 3: Gửi thông báo WebSocket tới khách hàng có vé đã thanh toán
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


# ============================================================
# UC-19: Xử lý sự cố giữa đường (Người 4: Điều độ viên)
# ============================================================

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
    """UC-19: Điều xe thay thế khẩn cấp giữa đường (lỗi nhà xe > 1h).
    Không bắt buộc cùng loại xe (tình huống khẩn cấp).
    Chuyến quay lại dang_chay với xe_thuc_te_id mới.
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "gap_su_co":
        raise GiaTriLoi("Chuyến không ở trạng thái gặp sự cố")

    repo.dieu_xe_thay_the_su_co(chuyen_id, xe_thay_the_id)

    # Thông báo WebSocket cho khách có vé trên chuyến này
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
    """UC-19 -> UC-21: Hủy chuyến do sự cố khách quan (thiên tai, sạt lở) không thể hoàn thành.
    Chỉ áp dụng với loi_khach_quan.
    Tự động ghi nhận hoàn tiền 100% cho các vé đã thanh toán.
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "gap_su_co":
        raise GiaTriLoi("Chuyến không ở trạng thái gặp sự cố")
    if chuyen["loai_su_co"] != "loi_khach_quan":
        raise GiaTriLoi("Chỉ sự cố khách quan (thiên tai/sạt lở) mới được phép hủy chuyến. Lỗi nhà xe phải luôn điều xe thay thế.")

    # 1. Chuyển trạng thái chuyến thành da_huy
    repo.huy_chuyen_do_su_co_khach_quan(chuyen_id)

    # 2. Xử lý hoàn tiền tự động (UC-21) cho các vé da_thanh_toan
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


# ============================================================
# UC-20: Đổi xe trước giờ khởi hành
# ============================================================

def lay_danh_sach_chuyen_can_doi_xe(nguoi_dung_id: str) -> list[dict]:
    """Các chuyến chua_khoi_hanh đã có xe nhưng cần đổi xe thay thế."""
    van_phong_id = _lay_van_phong_dieu_do_vien(nguoi_dung_id)
    return repo.lay_danh_sach_chuyen_can_doi_xe(van_phong_id)


def lay_xe_thay_the_du_dieu_kien(chuyen_id: str) -> list[dict]:
    """UC-20: Liệt kê xe thay thế cùng loại xe, không trùng lịch.
    Ưu tiên xe dự phòng trong đội xe (hoặc xe thuê ngoài).
    """
    return lay_xe_du_dieu_kien(chuyen_id)


async def gan_xe_thay_the(chuyen_id: str, xe_thay_the_id: str) -> list[str]:
    """UC-20: Gán xe_thuc_te_id cho chuyến hiện tại và toàn bộ chuỗi chuyến sau cùng xe gốc.
    Ghế giữ nguyên, thông báo WebSocket tới hành khách.
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "chua_khoi_hanh":
        raise GiaTriLoi("Chỉ đổi xe trước giờ khởi hành cho chuyến chưa xuất phát")
    if not chuyen["xe_id"]:
        raise GiaTriLoi("Chuyến chưa có xe gốc. Dùng UC-44 để gán xe lần đầu.")

    affected_ids = repo.gan_xe_thay_the_truoc_gio(chuyen_id, xe_thay_the_id)

    # Báo WebSocket cho khách
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


# ============================================================
# UC-40: Gán lại xe gốc cho chuyến đang chạy thay
# ============================================================

def lay_danh_sach_chuyen_dang_chay_thay(nguoi_dung_id: str | None = None) -> list[dict]:
    """Danh sách các chuyến đang có xe_thuc_te_id (chạy thay bằng xe khác)."""
    return repo.lay_danh_sach_chuyen_dang_chay_thay()


async def gan_lai_xe_goc(chuyen_id: str) -> list[str]:
    """UC-40: Xe gốc đã sửa xong và hoạt động trở lại. Đặt xe_thuc_te_id = NULL
    cho chuyến này và chuỗi chuyến tương lai cùng xe gốc.
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if not chuyen.get("xe_thuc_te_id"):
        raise GiaTriLoi("Chuyến này không có xe chạy thay")

    affected_ids = repo.gan_lai_xe_goc(chuyen_id)
    return affected_ids


# ============================================================
# UC-39: Thống kê vận hành
# ============================================================

def lay_thong_ke_van_hanh(tu_ngay: str, den_ngay: str, nguoi_dung_id: str | None = None) -> dict:
    """UC-39: Thống kê hiệu suất vận hành trong khoảng thời gian."""
    return repo.thong_ke_van_hanh(tu_ngay, den_ngay)


# ============================================================
# CONTRACT cho Người 3 (Phụ xe) — KHÔNG đổi signature
# CONTRIBUTING.md mục 5.6
# ============================================================

def xac_nhan_xuat_phat(chuyen_id: str) -> None:
    """UC-15: Phụ xe bấm xuất phát.

    Tiền điều kiện: chuyến 'chua_khoi_hanh', đã có xe_id.
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "chua_khoi_hanh":
        raise GiaTriLoi("Chuyến không ở trạng thái chờ khởi hành")
    if not chuyen["xe_id"]:
        raise GiaTriLoi("Chuyến chưa được gán xe, không thể xuất phát")

    repo.chuyen_sang_dang_chay(chuyen_id)


def xac_nhan_toi_diem(chuyen_id: str, diem_id: str) -> None:
    """UC-16: Phụ xe xác nhận xe đã tới 1 điểm dừng.

    Ghi nhận giờ thực tế. Nếu là điểm cuối → chuyển 'hoan_thanh'.
    Broadcast ETA cập nhật cho khách ở các điểm phía sau qua WebSocket.
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến không đang chạy")

    repo.ghi_nhan_toi_diem(chuyen_id, diem_id)

    # Kiểm tra có phải điểm cuối tuyến không
    diem_cuoi = repo.lay_diem_cuoi_cua_chuyen(chuyen_id)
    if diem_cuoi and str(diem_cuoi["diem_don_tra_id"]) == diem_id:
        repo.chuyen_sang_hoan_thanh(chuyen_id)
        # TODO: Broadcast WebSocket tới khách có vé trên chuyến này
        # ws_manager.broadcast() là async — gọi qua BackgroundTask ở route
        # hoặc dùng asyncio.create_task nếu đang trong async context.
        # Tạm thời bỏ qua trong UC-44, sẽ nối trong UC-19/UC-45.
    else:
        # TODO: Broadcast ETA cập nhật
        pass


def bao_su_co(chuyen_id: str, loai_su_co: str, ly_do: str) -> None:
    """UC-17: Phụ xe báo sự cố giữa đường.

    loai_su_co: 'loi_nha_xe' | 'loi_khach_quan' — quyết định quyền hoàn
    tiền của khách (NGHIEP_VU.md mục 3.3/7).

    Broadcast WebSocket tới điều độ viên để xử lý UC-19.
    """
    chuyen = repo.lay_chuyen_theo_id(chuyen_id)
    if not chuyen:
        raise GiaTriLoi("Không tìm thấy chuyến")
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến không đang chạy")
    if loai_su_co not in ("loi_nha_xe", "loi_khach_quan"):
        raise GiaTriLoi("loai_su_co phải là 'loi_nha_xe' hoặc 'loi_khach_quan'")

    repo.chuyen_sang_gap_su_co(chuyen_id, loai_su_co, ly_do)
    # TODO: Broadcast cảnh báo tới điều độ viên (UC-44 scope không cần,
    # sẽ nối đầy đủ trong nhánh UC-19)
