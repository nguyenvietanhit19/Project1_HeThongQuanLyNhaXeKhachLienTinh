"""Đặt vé online — UC-05 (chọn ghế, chọn điểm đón/trả, giữ ghế, thanh toán) và UC-08 (hủy giữ chỗ), kèm giỏ hàng.

NGHIEP_VU.md mục 3.4 (luồng), 6 (khóa ghế, hạn giữ chỗ), 9 (hạn chế no-show). Quy tắc nằm ở đây; SQL và cơ chế
khóa ghế nằm ở repositories/ve_lock_repository.py và ve_thanh_toan_repository.py.

Vòng đời 1 lượt đặt: chọn ghế → chọn điểm đón/trả (CHƯA khóa gì) → "Tiếp tục" = khóa ghế (ai nhanh hơn giữ được, 10 phút)
→ chọn ghế thanh toán + loại hình → hoặc "tại quầy" (đặt thành công ngay) hoặc VNPay (đặt thành công, chờ thanh toán
trong 5 phút). Lượt đặt còn đang giữ có hạn nằm trong giỏ hàng, khách thoát ra vẫn quay lại hoàn tất được.
"""

import datetime
import math
import secrets

from app.config import (
    HAN_DE_DUNG_TRE_IPN_PHUT,
    HAN_GIU_TAM_PHUT,
    HAN_THANH_TOAN_NGAY_PHUT,
    NGUONG_GIA_TRI_DAT_COC,
    SO_GHE_TOI_DA_MOI_LAN_DAT,
    TY_LE_DAT_COC,
    X_PHUT_CHOT_LEN_XE,
)
from app.repositories import ho_so_khach_hang_repository as ho_so_repo
from app.repositories import ve_lock_repository as lock_repo
from app.repositories import ve_thanh_toan_repository as thanh_toan_repo
from app.services import tim_kiem_chuyen_service as tim_kiem
from app.services import vnpay_service
from app.utils.loi import GiaTriLoi


# ---------------------------------------------------------
# Các hàm thuần (không đụng DB) — dễ unit test
# ---------------------------------------------------------
def chuan_hoa_danh_sach_ghe(danh_sach_ghe: list[str]) -> list[str]:
    """Bỏ khoảng trắng, chặn ghế trùng và quá số ghế tối đa 1 lần đặt."""
    ghe = [g.strip() for g in danh_sach_ghe if g and g.strip()]
    if not ghe:
        raise GiaTriLoi("Vui lòng chọn ít nhất 1 ghế")
    if len(set(ghe)) != len(ghe):
        raise GiaTriLoi("Có ghế bị chọn trùng")
    if len(ghe) > SO_GHE_TOI_DA_MOI_LAN_DAT:
        raise GiaTriLoi(f"Mỗi lần chỉ đặt tối đa {SO_GHE_TOI_DA_MOI_LAN_DAT} ghế")
    return ghe


def can_dat_coc(so_ve: int, tong_tien: int) -> bool:
    """Mục 3.4: 1 vé không cọc; ≥2 vé mà tổng giá trị ≤ ngưỡng không cọc; ≥2 vé và vượt ngưỡng thì bắt buộc cọc."""
    return so_ve >= 2 and tong_tien > NGUONG_GIA_TRI_DAT_COC


def so_ve_phai_dat_coc(so_ve: int, tong_tien: int) -> int:
    """Số vé bắt buộc thanh toán trực tuyến (VNPay) trong số vé khách đang thanh toán: một nửa, làm tròn xuống
    (mục 3.4). Tính trên đúng các ghế được tích để thanh toán, không phải cả lượt đặt."""
    return math.floor(so_ve * TY_LE_DAT_COC) if can_dat_coc(so_ve, tong_tien) else 0


def sinh_ma_dat_cho() -> str:
    return "DC" + secrets.token_hex(4).upper()


def trang_thai_dat_cho(cac_ve: list[dict], bay_gio: datetime.datetime) -> str:
    """Suy ra trạng thái của cả lượt đặt từ các vé. Vé `giu_cho` đã quá hạn coi như đã hết hạn (job quét có thể chưa chạy)."""
    tt = set()
    for v in cac_ve:
        if v["trang_thai"] == "giu_cho" and v["han_giu_cho_den"] is not None and v["han_giu_cho_den"] <= bay_gio:
            tt.add("het_han")
        else:
            tt.add(v["trang_thai"])
    if "da_thanh_toan" in tt:
        return "da_thanh_toan"
    if tt == {"da_huy"}:
        return "da_huy"
    if "het_han" in tt or tt <= {"da_huy", "het_han"}:
        return "het_han"
    dang_giu = [v for v in cac_ve if v["trang_thai"] == "giu_cho"]
    # đã bấm Thanh toán bằng VNPay: có vé trả online đã bắt đầu đếm hạn thanh toán
    if any(v["loai_hinh_thanh_toan"] == "thanh_toan_ngay" and v.get("gio_bat_dau_dem_han") is not None for v in dang_giu):
        return "cho_thanh_toan"
    # đã chốt "thanh toán tại quầy" (không hạn) hay vẫn đang giữ tạm 10 phút
    if all(v["loai_hinh_thanh_toan"] == "thanh_toan_tai_quay" and v["han_giu_cho_den"] is None for v in dang_giu):
        return "dat_thanh_cong_tai_quay"
    return "dang_giu"


def han_thanh_toan_tu_han_giu(han_giu: datetime.datetime) -> datetime.datetime:
    """Hạn khách phải trả VNPay = hạn giữ vé trừ phần đệm dành cho IPN (vé được giữ lâu hơn cổng thanh toán một chút)."""
    return han_giu - datetime.timedelta(minutes=HAN_DE_DUNG_TRE_IPN_PHUT)


def ve_con_giu(cac_ve: list[dict], bay_gio: datetime.datetime) -> list[dict]:
    """Các vé còn đang giữ chỗ (chưa hủy/hết hạn/thanh toán) của 1 lượt đặt."""
    return [
        v for v in cac_ve
        if v["trang_thai"] == "giu_cho" and (v["han_giu_cho_den"] is None or v["han_giu_cho_den"] > bay_gio)
    ]


def con_truoc_moc_chot(gio_don_du_kien: datetime.datetime, bay_gio: datetime.datetime) -> bool:
    """Mục 7: còn tự hủy giữ chỗ được khi chưa tới (giờ tại điểm đón − X phút)."""
    return bay_gio < gio_don_du_kien - datetime.timedelta(minutes=X_PHUT_CHOT_LEN_XE)


# ---------------------------------------------------------
# Dựng response
# ---------------------------------------------------------
def _bay_gio() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _dung_dat_cho(cac_ve: list[dict], ho_so: dict) -> dict:
    bay_gio = _bay_gio()
    # Ghế khách đã bỏ (✕) hoặc không tích khi thanh toán là vé `da_huy` — không tính vào lượt đặt, trừ khi hủy sạch
    cac_ve = [v for v in cac_ve if v["trang_thai"] != "da_huy"] or cac_ve
    dau = cac_ve[0]
    tong_tien = sum(int(v["gia"]) for v in cac_ve)
    trang_thai = trang_thai_dat_cho(cac_ve, bay_gio)
    han = [v["han_giu_cho_den"] for v in cac_ve if v["han_giu_cho_den"] is not None and v["trang_thai"] == "giu_cho"]
    han_giu = min(han) if han else None
    return {
        "ma_dat_cho": dau["ma_dat_cho"],
        "trang_thai": trang_thai,
        "chuyen": {
            "id": dau["chuyen_id"],
            "ma": dau["ma_chuyen"],
            "gio_khoi_hanh": dau["gio_khoi_hanh"],
            "gio_don_du_kien": dau["gio_don_du_kien"],
            "gio_den_du_kien": dau["gio_den_du_kien"],
            "ten_loai_xe": dau["ten_loai_xe"],
            "ten_diem_don": dau["ten_diem_don"],
            "ten_diem_tra": dau["ten_diem_tra"],
        },
        "ve": [
            {
                "id": v["id"], "so_ghe": v["so_ghe"], "gia": int(v["gia"]), "trang_thai": v["trang_thai"],
                "loai_hinh_thanh_toan": v["loai_hinh_thanh_toan"],
            }
            for v in cac_ve
        ],
        "so_ve": len(cac_ve),
        "tong_tien": tong_tien,
        "han_giu_cho_den": han_giu,
        "han_thanh_toan": han_thanh_toan_tu_han_giu(han_giu) if trang_thai == "cho_thanh_toan" and han_giu else None,
        "duoc_chon_thanh_toan_tai_quay": not ho_so["khoa_thanh_toan_tai_quay"],
        "can_dat_coc": can_dat_coc(len(cac_ve), tong_tien),
        "nguong_dat_coc": NGUONG_GIA_TRI_DAT_COC,
        "ty_le_dat_coc": TY_LE_DAT_COC,
        "cho_phep_huy": trang_thai in ("dang_giu", "cho_thanh_toan", "dat_thanh_cong_tai_quay") and con_truoc_moc_chot(dau["gio_don_du_kien"], bay_gio),
    }


def _lay_dat_cho_con_giu(nguoi_dung_id: str, ma_dat_cho: str) -> list[dict]:
    """Các vé của lượt đặt, bắt buộc còn đang giữ ghế và CHƯA chọn cách thanh toán (bỏ ghế, thanh toán chỉ làm ở đây)."""
    cac_ve = lock_repo.lay_dat_cho(ma_dat_cho, nguoi_dung_id)
    if not cac_ve:
        raise GiaTriLoi("Không tìm thấy lượt đặt chỗ này")
    if trang_thai_dat_cho(cac_ve, _bay_gio()) != "dang_giu":
        raise GiaTriLoi("Lượt đặt chỗ đã hết hạn hoặc đã được xử lý — vui lòng chọn ghế lại")
    return cac_ve


# ---------------------------------------------------------
# Nghiệp vụ
# ---------------------------------------------------------
def _kiem_tra_diem_don_tra(chuyen_id: str, khu_vuc_di_id: str, khu_vuc_den_id: str, diem_don_id: str, diem_tra_id: str) -> None:
    """Mục 3.4 bước 5/mục 6: điểm đón = văn phòng thuộc khu vực đi, điểm trả thuộc khu vực đến và đứng sau điểm đón."""
    cac_diem = {d["diem_id"]: d for d in lock_repo.tim_diem_cua_chuyen(str(chuyen_id))}
    don, tra = cac_diem.get(str(diem_don_id)), cac_diem.get(str(diem_tra_id))
    if not don or not tra:
        raise GiaTriLoi("Điểm đón/trả không thuộc tuyến của chuyến này")
    if don["loai"] != "van_phong":
        raise GiaTriLoi("Điểm đón phải là văn phòng")
    if str(don["khu_vuc_id"]) != str(khu_vuc_di_id):
        raise GiaTriLoi("Điểm đón phải thuộc khu vực điểm đi bạn đã chọn")
    if str(tra["khu_vuc_id"]) != str(khu_vuc_den_id):
        raise GiaTriLoi("Điểm trả phải thuộc khu vực điểm đến bạn đã chọn")
    if don["hl"] >= tra["hl"]:
        raise GiaTriLoi("Điểm trả phải đứng sau điểm đón")


def giu_cho(
    nguoi_dung_id: str,
    chuyen_id: str,
    khu_vuc_di_id: str,
    khu_vuc_den_id: str,
    danh_sach_ghe: list[str],
    diem_don_id: str | None = None,
    diem_tra_id: str | None = None,
) -> dict:
    """Mốc khóa ghế — khách bấm "Tiếp tục" sau khi đã chọn ghế và điểm đón/trả: khóa ghế trên đúng đoạn khách sẽ đi,
    tạo vé `giu_cho` hạn 10 phút. Ai bấm "Tiếp tục" trước thì giữ được ghế; người sau nhận lỗi "ghế đã có người".
    Không truyền điểm đón/trả thì giữ cả đoạn rộng nhất (mục 3.4 bước 3)."""
    ho_so = ho_so_repo.lay_theo_id(nguoi_dung_id)
    if ho_so["bi_khoa"]:
        raise GiaTriLoi("Tài khoản đang bị hạn chế đặt vé" + (f": {ho_so['ly_do_khoa']}" if ho_so["ly_do_khoa"] else ""))

    ghe = chuan_hoa_danh_sach_ghe(danh_sach_ghe)
    r, gia_info, _ghe_bi_giu_doan_rong = tim_kiem.lay_chuyen_mo_ban(chuyen_id, khu_vuc_di_id, khu_vuc_den_id)
    if not set(ghe) <= {g["ma_ghe"] for g in r["so_do_ghe"]}:
        raise GiaTriLoi("Có ghế không tồn tại trên xe của chuyến này")
    if diem_don_id is None or diem_tra_id is None:
        diem_don_id, diem_tra_id = r["diem_don_id"], r["diem_tra_id"]
    else:
        _kiem_tra_diem_don_tra(chuyen_id, khu_vuc_di_id, khu_vuc_den_id, diem_don_id, diem_tra_id)
    # Không kiểm tra "ghế đã có người" ở đây: sơ đồ ghế tính theo đoạn rộng nhất, còn đoạn khách chọn có thể hẹp hơn và vẫn
    # trống. Việc phán quyết duy nhất nằm trong giu_ghe (khóa + kiểm tra giao đoạn trên ĐÚNG đoạn đã chọn).

    ma_dat_cho = sinh_ma_dat_cho()
    lock_repo.giu_ghe(
        chuyen_id=str(chuyen_id),
        danh_sach_ghe=ghe,
        diem_don_id=str(diem_don_id),
        diem_tra_id=str(diem_tra_id),
        khach_hang_id=nguoi_dung_id,
        gia=gia_info["gia"],
        ma_dat_cho=ma_dat_cho,
        han_giu_tam_phut=HAN_GIU_TAM_PHUT,
    )
    return xem_dat_cho(nguoi_dung_id, ma_dat_cho)


def xem_dat_cho(nguoi_dung_id: str, ma_dat_cho: str) -> dict:
    cac_ve = lock_repo.lay_dat_cho(ma_dat_cho, nguoi_dung_id)
    if not cac_ve:
        raise GiaTriLoi("Không tìm thấy lượt đặt chỗ này")
    return _dung_dat_cho(cac_ve, ho_so_repo.lay_theo_id(nguoi_dung_id))


def gio_hang(nguoi_dung_id: str) -> list[dict]:
    """Giỏ hàng: các lượt đặt còn giữ ghế có hạn — chưa chọn cách thanh toán (đếm tiếp 10 phút) hoặc đang chờ trả VNPay
    (đếm tiếp hạn 5 phút). Lượt sắp hết hạn nhất xếp trước."""
    ket_qua = []
    for ma in lock_repo.tim_ma_dat_cho_con_giu(nguoi_dung_id):
        dat_cho = xem_dat_cho(nguoi_dung_id, ma)
        if dat_cho["trang_thai"] in ("dang_giu", "cho_thanh_toan"):
            ket_qua.append(dat_cho)
    return ket_qua


def bo_ghe(nguoi_dung_id: str, ma_dat_cho: str, so_ghe: str) -> dict:
    """Khách bấm ✕ ở 1 ghế: hủy riêng ghế đó, ghế mở lại ngay. Cùng quy tắc mốc chốt như hủy giữ chỗ (UC-08)."""
    cac_ve = _lay_dat_cho_con_giu(nguoi_dung_id, ma_dat_cho)
    bay_gio = _bay_gio()
    if so_ghe not in {v["so_ghe"] for v in ve_con_giu(cac_ve, bay_gio)}:
        raise GiaTriLoi("Ghế này không còn trong lượt đặt chỗ")
    if not con_truoc_moc_chot(cac_ve[0]["gio_don_du_kien"], bay_gio):
        raise GiaTriLoi("Đã qua mốc chốt trước giờ lên xe, không thể bỏ ghế nữa")
    if not lock_repo.bo_ghe(ma_dat_cho, nguoi_dung_id, so_ghe):
        raise GiaTriLoi("Lượt đặt chỗ đã hết hạn — vui lòng chọn ghế lại")
    return xem_dat_cho(nguoi_dung_id, ma_dat_cho)


def thanh_toan(nguoi_dung_id: str, ma_dat_cho: str, danh_sach_ghe: list[str], loai_hinh: str) -> dict:
    """Mục 3.4 bước 6-7: thanh toán CHỈ cho các ghế khách đã tích. Ghế không tích coi như không đặt — được nhả ngay.

    - `thanh_toan_tai_quay`: đặt vé thành công ngay (không hạn). Nếu các ghế được chọn rơi vào diện đặt cọc (≥2 vé, tổng
      > 600.000đ) thì bắt buộc trả VNPay trước cho một nửa số vé (làm tròn xuống) — nửa còn lại mới trả tại quầy.
    - `vnpay_qr` (thanh toán ngay): ĐẶT VÉ THÀNH CÔNG ở trạng thái chờ thanh toán, khách có 5 phút để trả VNPay (không
      trả/thoát thì ghế mở lại). Lô không cọc: mọi ghế được tích trả VNPay. Lô cọc: chỉ `so_coc` ghế ĐẦU TIÊN (theo thứ
      tự ghế) trả VNPay, các ghế còn lại trả tại quầy và được chốt khi phần cọc thanh toán xong. Đường dẫn sang cổng
      tạo riêng ở tao_duong_dan_thanh_toan (để khách quay lại trả tiếp trong hạn); kết quả do IPN quyết định.
    """
    cac_ve = ve_con_giu(_lay_dat_cho_con_giu(nguoi_dung_id, ma_dat_cho), _bay_gio())
    chon = chuan_hoa_danh_sach_ghe(danh_sach_ghe)
    if not set(chon) <= {v["so_ghe"] for v in cac_ve}:
        raise GiaTriLoi("Có ghế không còn trong lượt đặt chỗ này")
    tong_tien = sum(int(v["gia"]) for v in cac_ve if v["so_ghe"] in chon)
    so_coc = so_ve_phai_dat_coc(len(chon), tong_tien)

    if loai_hinh == "vnpay_qr":
        ve_chon = [v for v in cac_ve if v["so_ghe"] in chon]  # cac_ve đã sắp theo số ghế
        so_online = so_coc or len(ve_chon)
        ve_online, ve_quay = ve_chon[:so_online], ve_chon[so_online:]
        # Vé giữ lâu hơn hạn của cổng một chút (HAN_DE_DUNG_TRE_IPN_PHUT) để IPN tới sau vẫn còn vé
        if not thanh_toan_repo.bat_dau_thanh_toan_ngay(
            ma_dat_cho, nguoi_dung_id, [v["so_ghe"] for v in ve_online], [v["so_ghe"] for v in ve_quay],
            len(cac_ve), HAN_THANH_TOAN_NGAY_PHUT + HAN_DE_DUNG_TRE_IPN_PHUT, so_coc > 0,
        ):
            raise GiaTriLoi("Lượt đặt chỗ đã hết hạn — vui lòng chọn ghế lại")
        return xem_dat_cho(nguoi_dung_id, ma_dat_cho)

    if loai_hinh != "thanh_toan_tai_quay":
        raise GiaTriLoi("Loại hình thanh toán không hợp lệ")
    if ho_so_repo.lay_theo_id(nguoi_dung_id)["khoa_thanh_toan_tai_quay"]:
        raise GiaTriLoi("Tài khoản của bạn chỉ được thanh toán ngay (đã vi phạm không đến nhiều lần)")
    if so_coc:
        raise GiaTriLoi(
            f"Đơn này cần đặt cọc: phải thanh toán VNPay trước cho {so_coc} vé, "
            "các vé còn lại mới được thanh toán tại quầy"
        )
    if not lock_repo.chot_thanh_toan_tai_quay(ma_dat_cho, nguoi_dung_id, chon, len(cac_ve)):
        raise GiaTriLoi("Lượt đặt chỗ đã hết hạn — vui lòng chọn ghế lại")
    return xem_dat_cho(nguoi_dung_id, ma_dat_cho)


def tao_duong_dan_thanh_toan(nguoi_dung_id: str, ma_dat_cho: str, frontend_origin: str, ip_khach: str = "127.0.0.1") -> str:
    """Đường dẫn sang cổng VNPay cho lượt đặt đang chờ thanh toán. Gọi lại nhiều lần được (mỗi lần mã giao dịch mới) miễn
    còn trong hạn — nên khách thoát ra rồi quay lại từ giỏ hàng vẫn trả tiếp được."""
    cac_ve = lock_repo.lay_dat_cho(ma_dat_cho, nguoi_dung_id)
    if not cac_ve:
        raise GiaTriLoi("Không tìm thấy lượt đặt chỗ này")
    bay_gio = _bay_gio()
    if trang_thai_dat_cho(cac_ve, bay_gio) != "cho_thanh_toan":
        raise GiaTriLoi("Lượt đặt chỗ này không ở trạng thái chờ thanh toán (có thể đã hết hạn)")
    ve_online = [
        v for v in ve_con_giu(cac_ve, bay_gio)
        if v["loai_hinh_thanh_toan"] == "thanh_toan_ngay" and v.get("gio_bat_dau_dem_han") is not None
    ]
    han_thanh_toan = han_thanh_toan_tu_han_giu(min(v["han_giu_cho_den"] for v in ve_online))
    if han_thanh_toan <= bay_gio:
        raise GiaTriLoi("Đã hết thời gian thanh toán, vui lòng đặt lại")
    ma_giao_dich = vnpay_service.tao_ma_giao_dich(ma_dat_cho, bay_gio)
    url = vnpay_service.tao_url_thanh_toan(
        ma_dat_cho, sum(int(v["gia"]) for v in ve_online), han_thanh_toan, frontend_origin, ip_khach, bay_gio, ma_giao_dich
    )
    thanh_toan_repo.luu_ma_tham_chieu_vnpay(ma_dat_cho, ma_giao_dich)
    return url


def huy_dat_cho(nguoi_dung_id: str, ma_dat_cho: str) -> dict:
    """UC-08: tự hủy giữ chỗ trước khi thanh toán và trước mốc chốt lên xe tại điểm đón (mục 7)."""
    cac_ve = lock_repo.lay_dat_cho(ma_dat_cho, nguoi_dung_id)
    if not cac_ve:
        raise GiaTriLoi("Không tìm thấy lượt đặt chỗ này")
    bay_gio = _bay_gio()
    trang_thai = trang_thai_dat_cho(cac_ve, bay_gio)
    if trang_thai == "da_thanh_toan":
        raise GiaTriLoi("Vé đã thanh toán không tự hủy được — vui lòng liên hệ nhà xe")
    if trang_thai not in ("dang_giu", "cho_thanh_toan", "dat_thanh_cong_tai_quay"):
        raise GiaTriLoi("Lượt đặt chỗ này không còn ở trạng thái giữ chỗ")
    if not con_truoc_moc_chot(cac_ve[0]["gio_don_du_kien"], bay_gio):
        raise GiaTriLoi("Đã qua mốc chốt trước giờ lên xe, không thể tự hủy giữ chỗ nữa")
    return {"ma_dat_cho": ma_dat_cho, "so_ve_da_huy": lock_repo.huy_dat_cho(ma_dat_cho, nguoi_dung_id)}
