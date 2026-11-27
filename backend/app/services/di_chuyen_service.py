"""Phụ xe bấm "Bắt đầu di chuyển" rời điểm dừng tới điểm kế tiếp.

Tại điểm xuất phát, "Bắt đầu di chuyển" cũng là lúc xuất phát: chuyến chưa khởi hành chỉ đi được từ ĐÚNG giờ chạy
(bến mở cho khách lên/chất hàng từ 15 phút trước đó — chuyen_xe_service.kiem_tra_ben_da_mo), không còn bước
"xác nhận xuất phát" riêng.

Mỗi điểm có 2 pha: ĐANG DỪNG (cho khách lên/xuống, chất/dỡ hàng) rồi ĐANG DI CHUYỂN tới điểm kế tiếp
(`chuyen_xe.dang_di_chuyen`). Quy tắc rời điểm:
- CHẶN: còn khách phải xuống tại điểm này, hoặc còn hàng phải dỡ tại điểm này — bỏ lại họ là sai lệch
  nghiệp vụ, không có "bỏ qua".
- CẢNH BÁO: còn khách chưa lên / hàng chưa chất tại điểm này — phụ xe được phép đi tiếp sau khi tích xác nhận
  từng mục. NGAY LÚC ĐÓ khách chưa lên bị đánh dấu "không đến" (khong_den_service); hàng chưa chất vẫn là hàng
  chờ vận chuyển cho chuyến sau. Đây là cách DUY NHẤT một vé thành "không đến" — không có job tự đánh dấu theo giờ.
- CHẶN ĐI SỚM: ở điểm đón dọc đường, còn khách chưa lên thì chưa được rời trước giờ đón dự kiến của điểm đó (khách chưa
  trễ giờ). Qua giờ đó phụ xe đợi thêm bao lâu tùy tình hình thực tế. Điểm xuất phát vốn không đi được trước giờ chạy.
Phụ xe tích nhầm / khách đuổi kịp xe: hoàn tác được khi xe CHƯA tới điểm kế tiếp (hoan_tac_khong_den).
"""

from datetime import timedelta, timezone

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import don_hang_repository as don_hang_repo
from app.repositories import ve_repository as ve_repo
from app.services import gui_hang_service
from app.services import khong_den_service
from app.services.chuyen_xe_service import (
    _bay_gio,
    diem_theo_chieu,
    gio_du_kien_tai_diem,
    diem_xe_vua_roi_hoac_dung,
    kiem_tra_co_the_xuat_phat,
    lay_chuyen_cua_phu_xe,
    xac_nhan_xuat_phat,
)
from app.utils.loi import GiaTriLoi

GIO_VIET_NAM = timezone(timedelta(hours=7))


def _viec_con_lai_tai_diem(chuyen: dict, diem_id: str, nguoi_dung_id: str) -> dict:
    return {
        "khach_chua_xuong": ve_repo.tim_ve_can_xuong_xe_tai_diem(chuyen["id"], diem_id),
        "hang_chua_do": don_hang_repo.tim_don_can_do_tai_diem(chuyen["id"], diem_id),
        "khach_chua_len": ve_repo.tim_ve_chua_len_tai_diem(chuyen["id"], diem_id),
        "hang_chua_chat": gui_hang_service.danh_sach_cho_chat(chuyen["id"], nguoi_dung_id),
    }


def bat_dau_di_chuyen(chuyen_id: str, bo_qua_canh_bao: bool, nguoi_dung_id: str) -> dict:
    """Trả về điểm xe đang đi tới và số khách bị đánh dấu "không đến" khi rời điểm."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    chua_khoi_hanh = chuyen["trang_thai"] == "chua_khoi_hanh"
    if chua_khoi_hanh:
        kiem_tra_co_the_xuat_phat(chuyen)  # đúng giờ chạy mới được đi, không hoãn
    elif chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chỉ bắt đầu di chuyển được khi chuyến đang chạy")
    if chuyen.get("dang_di_chuyen"):
        raise GiaTriLoi("Xe đã bắt đầu di chuyển rồi")

    diem_list = diem_theo_chieu(chuyen)
    diem = diem_xe_vua_roi_hoac_dung(chuyen)
    vi_tri = next(i for i, d in enumerate(diem_list) if d["diem_don_tra_id"] == diem["diem_don_tra_id"])
    if vi_tri >= len(diem_list) - 1:
        raise GiaTriLoi("Xe đã ở điểm cuối, không còn điểm nào để di chuyển tới")
    diem_ke_tiep = diem_list[vi_tri + 1]

    viec = _viec_con_lai_tai_diem(chuyen, str(diem["diem_don_tra_id"]), nguoi_dung_id)

    chan = []
    if viec["khach_chua_xuong"]:
        chan.append(f"{len(viec['khach_chua_xuong'])} khách chưa xuống xe")
    if viec["hang_chua_do"]:
        chan.append(f"{len(viec['hang_chua_do'])} đơn hàng chưa dỡ")
    if chan:
        raise GiaTriLoi(f"Chưa thể rời {diem['ten']}: còn " + " và ".join(chan) + " tại điểm này")

    khach_bi_bo = [v for v in viec["khach_chua_len"] if khong_den_service.se_bi_danh_dau(v)]
    if khach_bi_bo and vi_tri > 0:
        gio_don = gio_du_kien_tai_diem(chuyen, diem_list, diem)
        if _bay_gio() < gio_don:
            raise GiaTriLoi(
                f"Chưa tới giờ đón dự kiến tại {diem['ten']} ({gio_don.astimezone(GIO_VIET_NAM):%H:%M}) mà còn {len(khach_bi_bo)} khách "
                "chưa lên xe — chưa được rời điểm"
            )

    canh_bao = []
    if viec["khach_chua_len"]:
        canh_bao.append(f"{len(viec['khach_chua_len'])} khách chưa lên xe (sẽ bị đánh dấu \"Không đến\")")
    if viec["hang_chua_chat"]:
        canh_bao.append(f"{len(viec['hang_chua_chat'])} đơn hàng chưa chất lên xe")
    if canh_bao and not bo_qua_canh_bao:
        raise GiaTriLoi("Còn " + " và ".join(canh_bao) + ". Xác nhận bỏ qua để bắt đầu di chuyển")

    if chua_khoi_hanh:
        xac_nhan_xuat_phat(chuyen_id, nguoi_dung_id)  # chuyển dang_chay + vào pha di chuyển trong 1 câu UPDATE
    elif not chuyen_xe_repo.dat_dang_di_chuyen(chuyen_id, True):
        raise GiaTriLoi("Chuyến vừa đổi trạng thái hoặc đã bắt đầu di chuyển, vui lòng tải lại")

    # Xe đã được ghi nhận rời điểm → những khách phụ xe vừa tích xác nhận là "không đến"
    so_khong_den = sum(1 for v in khach_bi_bo if khong_den_service.danh_dau_khong_den(v))

    return {"diem_ke_tiep": diem_ke_tiep["ten"], "so_khach_chua_len": len(viec["khach_chua_len"]), "so_khach_khong_den": so_khong_den}


def hoan_tac_khong_den(chuyen_id: str, ve_id: str, nguoi_dung_id: str) -> None:
    """Phụ xe tích nhầm hoặc khách đuổi kịp xe: chỉ khi xe vừa rời đúng điểm đón của vé và CHƯA tới điểm kế tiếp."""
    chuyen = lay_chuyen_cua_phu_xe(chuyen_id, nguoi_dung_id)
    if chuyen["trang_thai"] != "dang_chay":
        raise GiaTriLoi("Chuyến không ở trạng thái đang chạy, không thể hoàn tác")
    ve = ve_repo.tim_theo_id(ve_id)
    if not ve or str(ve["chuyen_id"]) != str(chuyen_id):
        raise GiaTriLoi("Không tìm thấy vé của chuyến này")
    if ve["trang_thai"] != "khong_den":
        raise GiaTriLoi('Vé không ở trạng thái "Không đến", không có gì để hoàn tác')
    if not chuyen.get("dang_di_chuyen") or str(diem_xe_vua_roi_hoac_dung(chuyen)["diem_don_tra_id"]) != str(ve["diem_don_id"]):
        raise GiaTriLoi("Xe đã tới điểm kế tiếp, không thể hoàn tác — hãy báo điều độ viên")
    if ve.get("gio_thanh_toan") is None:
        raise GiaTriLoi("Vé chưa trả tiền nên không ghi nhận lên xe được")
    if not khong_den_service.hoan_tac_khong_den(ve):
        raise GiaTriLoi("Vé đã được xử lý trước đó, vui lòng tải lại")

