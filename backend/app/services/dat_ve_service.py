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
from app.repositories import ve_lich_su_repository as lich_su_repo
from app.repositories import ve_thanh_toan_repository as thanh_toan_repo
from app.services import thong_bao_khach_service as thong_bao
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


def phan_loai_lich_su(cac_ve: list[dict], bay_gio: datetime.datetime) -> tuple[str, str]:
    """Trang Booking: xếp 1 lượt đặt vào nhóm `sap_di` / `da_di` / `da_huy` và cho biết nhãn trạng thái hiển thị.

    Nhãn: sap_di → dang_giu · cho_thanh_toan · dat_thanh_cong_tai_quay · da_thanh_toan · da_len_xe;
          da_di → da_di · khong_den; da_huy → da_huy · het_han · chuyen_bi_huy.
    Ghế khách đã bỏ (✕) là vé `da_huy` — không tính vào lượt đặt, trừ khi cả lượt đã hủy."""
    huu_hieu = [v for v in cac_ve if v["trang_thai"] != "da_huy"] or cac_ve

    def trang_thai_ve(v: dict) -> str:
        het_han = v["trang_thai"] == "giu_cho" and v["han_giu_cho_den"] is not None and v["han_giu_cho_den"] <= bay_gio
        return "het_han" if het_han else v["trang_thai"]

    cac = {trang_thai_ve(v) for v in huu_hieu}
    trang_thai_chuyen = huu_hieu[0]["trang_thai_chuyen"]
    if cac <= {"da_huy", "het_han"}:
        return "da_huy", "het_han" if "het_han" in cac else "da_huy"
    if trang_thai_chuyen == "da_huy":
        return "da_huy", "chuyen_bi_huy"
    if cac & {"da_xuong_xe", "khong_den"} or trang_thai_chuyen == "hoan_thanh":
        khong_den = "khong_den" in cac and not cac & {"da_xuong_xe", "da_thanh_toan", "da_len_xe"}
        return "da_di", "khong_den" if khong_den else "da_di"
    if "da_len_xe" in cac:
        return "sap_di", "da_len_xe"
    return "sap_di", trang_thai_dat_cho(huu_hieu, bay_gio)


TRANG_THAI_DA_TRA = ("da_thanh_toan", "da_len_xe", "da_xuong_xe")


def _ve_con_giu_cho(v: dict, bay_gio: datetime.datetime) -> bool:
    return v["trang_thai"] == "giu_cho" and (v["han_giu_cho_den"] is None or v["han_giu_cho_den"] > bay_gio)


def tien_da_tra_con_lai(v: dict, bay_gio: datetime.datetime) -> tuple[int, int]:
    """(đã thanh toán, còn lại) của 1 vé: đã trả thì hết nợ; đang giữ chỗ thì còn nguyên giá; hủy/hết hạn/không đến thì 0/0."""
    gia = int(v["gia"])
    if v["trang_thai"] in TRANG_THAI_DA_TRA:
        return gia, 0
    if _ve_con_giu_cho(v, bay_gio):
        return 0, gia
    return 0, 0


def _con_truoc_moc_chot_cua_ve(v: dict, bay_gio: datetime.datetime) -> bool:
    return v["trang_thai_chuyen"] == "chua_khoi_hanh" and con_truoc_moc_chot(v["gio_don_du_kien"], bay_gio)


def ve_huy_duoc(v: dict, nhan_luot: str, bay_gio: datetime.datetime) -> bool:
    """Khách tự hủy riêng 1 vé khi vé còn giữ chỗ (chưa trả tiền) và còn trước mốc chốt (UC-08). Vé đã trả tiền không tự hủy
    được (hoàn tiền chỉ theo mục 7). Vé trả VNPay của lượt đang chờ thanh toán thì không hủy lẻ — tổng tiền cổng đã tính."""
    if not _ve_con_giu_cho(v, bay_gio) or not _con_truoc_moc_chot_cua_ve(v, bay_gio):
        return False
    return not (v["loai_hinh_thanh_toan"] == "thanh_toan_ngay" and nhan_luot == "cho_thanh_toan")


def ve_thanh_toan_duoc(v: dict, bay_gio: datetime.datetime) -> bool:
    """Khách trả online riêng 1 vé đã chốt "thanh toán tại quầy" (không hạn giữ chỗ), khi còn trước mốc chốt."""
    return (
        v["trang_thai"] == "giu_cho"
        and v["loai_hinh_thanh_toan"] == "thanh_toan_tai_quay"
        and v["han_giu_cho_den"] is None
        and _con_truoc_moc_chot_cua_ve(v, bay_gio)
    )


def lich_su(nguoi_dung_id: str) -> list[dict]:
    """Trang Booking: mọi lượt đặt gần đây của khách (mới đặt trước), mỗi lượt kèm nhóm + nhãn trạng thái, tiền đã trả/còn
    lại và danh sách từng vé (mã vé, ghế, giá, đã trả/còn lại, hủy/thanh toán riêng được hay không)."""
    bay_gio = _bay_gio()
    theo_luot: dict[str, list[dict]] = {}
    for v in lich_su_repo.lay_ve_cua_khach(nguoi_dung_id):
        theo_luot.setdefault(v["ma_dat_cho"], []).append(v)
    ket_qua = []
    for ma, cac_ve in theo_luot.items():
        nhom, nhan = phan_loai_lich_su(cac_ve, bay_gio)
        huu_hieu = [v for v in cac_ve if v["trang_thai"] != "da_huy"] or cac_ve
        dau = huu_hieu[0]
        han = [v["han_giu_cho_den"] for v in huu_hieu if v["trang_thai"] == "giu_cho" and v["han_giu_cho_den"] is not None]
        han_giu = min(han) if han else None
        ve_ra = []
        for v in huu_hieu:
            da_tra, con_lai = tien_da_tra_con_lai(v, bay_gio)
            ve_ra.append({
                "id": v["id"], "ma_ve": v["ma_ve"], "so_ghe": v["so_ghe"], "gia": int(v["gia"]), "trang_thai": v["trang_thai"],
                "loai_hinh_thanh_toan": v["loai_hinh_thanh_toan"], "da_thanh_toan": da_tra, "con_lai": con_lai,
                "co_the_huy": ve_huy_duoc(v, nhan, bay_gio), "co_the_thanh_toan": ve_thanh_toan_duoc(v, bay_gio),
                "ten_diem_don": v["ten_diem_don"], "ten_diem_tra": v["ten_diem_tra"],
                "gio_don_du_kien": v["gio_don_du_kien"], "gio_den_du_kien": v["gio_den_du_kien"],
            })
        ket_qua.append({
            "ma_dat_cho": ma,
            "nhom": nhom,
            "trang_thai": nhan,
            "chuyen": {
                "id": dau["chuyen_id"], "ma": dau["ma_chuyen"], "gio_khoi_hanh": dau["gio_khoi_hanh"],
                "gio_don_du_kien": dau["gio_don_du_kien"], "gio_den_du_kien": dau["gio_den_du_kien"],
                "ten_loai_xe": dau["ten_loai_xe"], "ten_diem_don": dau["ten_diem_don"], "ten_diem_tra": dau["ten_diem_tra"],
                "ten_tuyen": dau["ten_tuyen"], "bien_so": dau["bien_so"],
            },
            "ve": ve_ra,
            "so_ve": len(huu_hieu),
            "tong_tien": sum(int(v["gia"]) for v in huu_hieu),
            "da_thanh_toan": sum(v["da_thanh_toan"] for v in ve_ra),
            "con_lai": sum(v["con_lai"] for v in ve_ra),
            "ngay_dat": min(v["ngay_tao"] for v in cac_ve),
            "han_giu_cho_den": han_giu,
            "han_thanh_toan": han_thanh_toan_tu_han_giu(han_giu) if nhan == "cho_thanh_toan" and han_giu else None,
            "co_the_tiep_tuc": nhan in ("dang_giu", "cho_thanh_toan"),
        })
    return ket_qua


def _lay_ve_cua_khach(nguoi_dung_id: str, ve_id: str) -> dict:
    ve = lich_su_repo.lay_ve_theo_id(ve_id, nguoi_dung_id)
    if not ve:
        raise GiaTriLoi("Không tìm thấy vé này")
    return ve


def huy_ve(nguoi_dung_id: str, ve_id: str) -> dict:
    """UC-08 theo từng vé: tự hủy riêng 1 vé còn giữ chỗ (chưa trả tiền) trước mốc chốt; các vé khác của lượt giữ nguyên."""
    ve = _lay_ve_cua_khach(nguoi_dung_id, ve_id)
    bay_gio = _bay_gio()
    if ve["trang_thai"] in TRANG_THAI_DA_TRA:
        raise GiaTriLoi("Vé đã thanh toán không tự hủy được — vui lòng liên hệ nhà xe")
    if not _ve_con_giu_cho(ve, bay_gio):
        raise GiaTriLoi("Vé này không còn ở trạng thái giữ chỗ")
    if not _con_truoc_moc_chot_cua_ve(ve, bay_gio):
        raise GiaTriLoi("Đã qua mốc chốt trước giờ lên xe, không thể tự hủy vé nữa")
    if ve["loai_hinh_thanh_toan"] == "thanh_toan_ngay":
        cac_ve = lock_repo.lay_dat_cho(ve["ma_dat_cho"], nguoi_dung_id)
        if trang_thai_dat_cho(cac_ve, bay_gio) == "cho_thanh_toan":
            raise GiaTriLoi("Lượt đặt đang chờ thanh toán VNPay — hãy hoàn tất thanh toán hoặc hủy cả lượt trong giỏ hàng")
    if not thanh_toan_repo.huy_ve_dang_giu(str(ve["id"]), nguoi_dung_id):
        raise GiaTriLoi("Vé này không còn ở trạng thái giữ chỗ")
    return {"ma_ve": ve["ma_ve"], "trang_thai": "da_huy"}


def tao_duong_dan_thanh_toan_ve(nguoi_dung_id: str, ve_id: str, frontend_origin: str, ip_khach: str = "127.0.0.1") -> str:
    """Đường dẫn sang cổng VNPay để trả riêng 1 vé đã chốt "thanh toán tại quầy". Trả không xong thì vé vẫn là vé trả tại quầy
    như cũ (không bị hết hạn). Mỗi lần gọi là 1 mã giao dịch mới, gọi lại được."""
    ve = _lay_ve_cua_khach(nguoi_dung_id, ve_id)
    bay_gio = _bay_gio()
    if ve["trang_thai"] in TRANG_THAI_DA_TRA:
        raise GiaTriLoi("Vé này đã được thanh toán")
    if not ve_thanh_toan_duoc(ve, bay_gio):
        raise GiaTriLoi("Vé này không thanh toán online được (không phải vé trả tại quầy đang giữ chỗ, hoặc đã qua mốc chốt)")
    ma_giao_dich = vnpay_service.tao_ma_giao_dich(ve["ma_ve"], bay_gio)
    han_thanh_toan = bay_gio + datetime.timedelta(minutes=HAN_THANH_TOAN_NGAY_PHUT)
    url = vnpay_service.tao_url_thanh_toan(
        ve["ma_ve"], int(ve["gia"]), han_thanh_toan, frontend_origin, ip_khach, bay_gio, ma_giao_dich,
        noi_dung=f"Thanh toan ve xe ma ve {ve['ma_ve']}",
    )
    thanh_toan_repo.luu_ma_tham_chieu_vnpay_ve(str(ve["id"]), ma_giao_dich)
    return url


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
    dat_cho = xem_dat_cho(nguoi_dung_id, ma_dat_cho)
    chuyen = dat_cho["chuyen"]
    thong_bao.gui(
        nguoi_dung_id,
        thong_bao.nd_dat_ve_tai_quay(ma_dat_cho, chon, chuyen["ten_diem_don"], chuyen["gio_don_du_kien"], tong_tien),
        ve_id=next((v["id"] for v in dat_cho["ve"] if v["so_ghe"] in chon), None),
    )
    return dat_cho


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
