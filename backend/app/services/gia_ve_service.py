"""Giá vé theo BỘ — UC-33, NGHIEP_VU.md mục 3.1. Mỗi tuyến có nhiều bộ giá nối liền nhau; mỗi bộ có NGÀY BẮT ĐẦU và NGÀY
KẾT THÚC (bắt buộc) và gồm giá gốc của MỌI cặp khu vực trên tuyến (điểm đi đứng trước điểm đến theo chiều đi). Bộ mới luôn nối
tiếp bộ cuối cùng: bắt đầu ngày liền sau ngày kết thúc của bộ trước → không chồng, không hở, không có giá theo mùa. Muốn đổi
giá 1 chặng thì tạo bộ mới, các chặng còn lại giữ nguyên.

Sinh chuyến chỉ được trong khoảng ngày của các bộ giá (hết bộ cuối là hết hạn bán, gia hạn bằng cách kéo dài ngày kết thúc bộ
cuối hoặc tạo bộ mới).

Vé đã đặt luôn giữ giá lúc khách giữ ghế (ve.gia) nên đổi giá không ảnh hưởng vé cũ. Bộ đã được dùng để sinh chuyến (tuyến có
chuyến khởi hành trong khoảng ngày bộ đó áp dụng) thì khóa: không sửa giá/ngày bắt đầu, không xóa — kể cả khi chưa có khách
đặt; riêng bộ cuối vẫn kéo dài/rút ngắn được ngày kết thúc (không rút ngắn trước chuyến xa nhất đã sinh). Bộ mới mặc định bắt
đầu ngay sau bộ trước (bộ đầu tiên: từ ngày mai) và phải qua bước xem trước (cảnh báo giá bất thường) trước khi lưu.

Đúng theo ARCHITECTURE.md mục 2: Service quyết định quy tắc nghiệp vụ, Repository chỉ đọc/ghi SQL thuần.
"""

import datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import psycopg2.errors

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import gia_ve_repository as repo
from app.utils.loi import GiaTriLoi

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
MOT_NGAY = datetime.timedelta(days=1)

# Ngưỡng cảnh báo giá bất thường (chỉ cảnh báo, quản lý xác nhận vẫn lưu được)
TI_LE_GIAM_CANH_BAO = 0.5  # giá mới thấp hơn giá của bộ trước quá 50%
TI_LE_TANG_CANH_BAO = 2.0  # giá mới cao hơn giá của bộ trước hơn 2 lần
GIA_THAP_BAT_THUONG = 50_000
GIA_CAO_BAT_THUONG = 5_000_000
SO_CANH_BAO_TOI_DA = 6


def hom_nay() -> datetime.date:
    return datetime.datetime.now(MUI_GIO_VN).date()


def _dinh_dang_tien(so) -> str:
    return f"{int(so):,}".replace(",", ".") + "đ"


def _dinh_dang_ngay(ngay) -> str:
    return ngay.strftime("%d/%m/%Y")


def trang_thai_bo(ap_dung_tu: datetime.date, ap_dung_den: datetime.date, ngay: datetime.date) -> str:
    if ap_dung_den < ngay:
        return "da_ket_thuc"
    if ap_dung_tu > ngay:
        return "sap_ap_dung"
    return "dang_ap_dung"


def _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id: str) -> list[dict]:
    """Danh sách khu vực (không trùng lặp) mà tuyến đi qua, theo đúng thứ tự tuyến di chuyển (dùng thu_tu điểm dừng
    nhỏ nhất của mỗi khu vực)."""
    diem = dia_diem_repo.danh_sach_diem_theo_tuyen(tuyen_id)
    da_thay: dict[str, dict] = {}
    for d in sorted(diem, key=lambda x: x["thu_tu"]):
        kv_id = str(d["khu_vuc_id"])
        if kv_id not in da_thay:
            da_thay[kv_id] = {"khu_vuc_id": kv_id, "ten": d["ten_khu_vuc"]}
    return list(da_thay.values())


def _cac_cap_cua_tuyen(tuyen_id: str) -> list[tuple[str, str, str]]:
    """Mọi cặp khu vực hợp lệ của tuyến: (id đi, id đến, tên chặng), điểm đi đứng trước điểm đến."""
    kv = _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id)
    return [(a["khu_vuc_id"], b["khu_vuc_id"], f"{a['ten']} → {b['ten']}") for i, a in enumerate(kv) for b in kv[i + 1:]]


def _sap_xep(cac_bo: list[dict]) -> list[dict]:
    return sorted(cac_bo, key=lambda b: b["ap_dung_tu"])


def _bo_ap_dung_vao_ngay(cac_bo: list[dict], ngay: datetime.date) -> dict | None:
    """Bộ có `ngay` nằm trong khoảng ngày áp dụng của nó (các bộ của 1 tuyến nối liền nên tối đa 1 bộ)."""
    return next((b for b in cac_bo if b["ap_dung_tu"] <= ngay <= b["ap_dung_den"]), None)


def _cap_thieu_trong_bo(bo: dict, cac_cap: list[tuple[str, str, str]]) -> list[str]:
    co = {(str(g["diem_di_id"]), str(g["diem_den_id"])) for g in bo["danh_sach_gia"]}
    return [ten for di, den, ten in cac_cap if (di, den) not in co]


def cac_cap_thieu_gia(tuyen_id: str) -> list[str]:
    """Các chặng chưa có giá trong bộ giá hiện hành của tuyến (bộ đang áp dụng hôm nay; chưa có thì bộ sắp áp dụng gần
    nhất; không còn bộ nào hiệu lực thì mọi chặng). Rỗng = tuyến đã đủ giá. Bộ tạo qua hệ thống luôn đủ chặng; chỉ dữ
    liệu cũ mới thiếu."""
    cac_cap = _cac_cap_cua_tuyen(tuyen_id)
    cac_bo = _sap_xep(repo.danh_sach_bo(tuyen_id))
    ngay = hom_nay()
    bo = _bo_ap_dung_vao_ngay(cac_bo, ngay) or next((b for b in cac_bo if b["ap_dung_tu"] > ngay), None)
    return [ten for _, _, ten in cac_cap] if bo is None else _cap_thieu_trong_bo(bo, cac_cap)


def khoang_ngay_co_gia(tuyen_id: str) -> tuple[datetime.date, datetime.date] | None:
    """(ngày bắt đầu bộ đầu tiên, ngày kết thúc bộ cuối cùng) — khoảng ngày chuyến được phép khởi hành; None nếu chưa có bộ
    nào. Các bộ nối liền nên toàn khoảng này đều có giá."""
    cac_bo = _sap_xep(repo.danh_sach_bo(tuyen_id))
    return (cac_bo[0]["ap_dung_tu"], cac_bo[-1]["ap_dung_den"]) if cac_bo else None


def ngay_chua_co_gia(tuyen_id: str, cac_ngay: list[datetime.date]) -> list[datetime.date]:
    """Những ngày (trong `cac_ngay`) mà tuyến chưa có bộ giá đầy đủ áp dụng — chuyến khởi hành vào các ngày này sẽ không
    có giá nên khách không thấy. Dùng chặn sinh chuyến."""
    cac_cap = _cac_cap_cua_tuyen(tuyen_id)
    cac_bo = repo.danh_sach_bo(tuyen_id)
    thieu = []
    for ngay in sorted(set(cac_ngay)):
        bo = _bo_ap_dung_vao_ngay(cac_bo, ngay)
        if bo is None or _cap_thieu_trong_bo(bo, cac_cap):
            thieu.append(ngay)
    return thieu


def bang_gia_cua_chuyen(tuyen_id: str, chieu: str, ngay_khoi_hanh: datetime.date, he_so_gia) -> dict | None:
    """Bảng giá vé của 1 chuyến: bộ giá áp dụng cho ngày khởi hành của chuyến, từng chặng đọc theo ĐÚNG CHIỀU chuyến chạy
    (chuyến về đảo cặp), kèm giá bán = giá gốc × hệ số loại xe. None nếu ngày đó chưa có bộ giá đầy đủ (khách không thấy
    chuyến này)."""
    bo = _bo_ap_dung_vao_ngay(repo.danh_sach_bo(tuyen_id), ngay_khoi_hanh)
    if bo is None or _cap_thieu_trong_bo(bo, _cac_cap_cua_tuyen(tuyen_id)):
        return None
    thu_tu = {kv["khu_vuc_id"]: i for i, kv in enumerate(_khu_vuc_theo_tuyen_co_thu_tu(tuyen_id))}
    cac_chang = []
    for g in bo["danh_sach_gia"]:
        di, den = str(g["diem_di_id"]), str(g["diem_den_id"])
        xuoi = chieu == "xuoi"
        cac_chang.append({
            "ten_chang": f"{g['ten_diem_di']} → {g['ten_diem_den']}" if xuoi else f"{g['ten_diem_den']} → {g['ten_diem_di']}",
            "gia_goc": int(g["gia_goc"]),
            "gia_ban": int((Decimal(g["gia_goc"]) * Decimal(he_so_gia)).quantize(Decimal(1), rounding=ROUND_HALF_UP)),
            "_khoa": (thu_tu[di], thu_tu[den]) if xuoi else (-thu_tu[den], -thu_tu[di]),
        })
    cac_chang.sort(key=lambda c: c["_khoa"])
    for c in cac_chang:
        del c["_khoa"]
    return {"ap_dung_tu": bo["ap_dung_tu"], "he_so_gia": Decimal(he_so_gia), "cac_chang": cac_chang}


# ---------------------------------------------------------
# Kiểm tra dữ liệu bộ giá + cảnh báo giá bất thường
# ---------------------------------------------------------
def _chuan_hoa_gia(tuyen_id: str, danh_sach_gia: list[dict]) -> tuple[list[dict], dict[tuple[str, str], int]]:
    """Bộ phải có giá (> 0) cho đúng mọi chặng của tuyến: không thiếu, không thừa, không trùng."""
    cac_cap = _cac_cap_cua_tuyen(tuyen_id)
    ten_cap = {(di, den): ten for di, den, ten in cac_cap}
    gia_theo_cap: dict[tuple[str, str], int] = {}
    for g in danh_sach_gia:
        cap = (str(g["diem_di_id"]), str(g["diem_den_id"]))
        if cap not in ten_cap:
            raise GiaTriLoi("Có chặng không thuộc tuyến này hoặc sai chiều đi của tuyến")
        if cap in gia_theo_cap:
            raise GiaTriLoi(f"Chặng {ten_cap[cap]} bị nhập 2 lần")
        if int(g["gia_goc"]) <= 0:
            raise GiaTriLoi(f"Giá chặng {ten_cap[cap]} phải lớn hơn 0")
        gia_theo_cap[cap] = int(g["gia_goc"])
    thieu = [ten for cap, ten in ten_cap.items() if cap not in gia_theo_cap]
    if thieu:
        raise GiaTriLoi("Bộ giá phải có giá cho đủ mọi chặng của tuyến — còn thiếu: " + ", ".join(thieu))
    chuan = [{"diem_di_id": di, "diem_den_id": den, "gia_goc": gia_theo_cap[(di, den)]} for di, den, _ in cac_cap]
    return chuan, gia_theo_cap


def _canh_bao_bo(tuyen_id: str, gia_moi: dict[tuple[str, str], int], gia_bo_truoc: dict[tuple[str, str], int] | None) -> list[str]:
    cac_cap = _cac_cap_cua_tuyen(tuyen_id)
    ten_cap = {(di, den): ten for di, den, ten in cac_cap}
    thu_tu = {kv["khu_vuc_id"]: i for i, kv in enumerate(_khu_vuc_theo_tuyen_co_thu_tu(tuyen_id))}
    canh_bao: list[str] = []
    for cap, gia in gia_moi.items():
        ten = ten_cap[cap]
        if gia < GIA_THAP_BAT_THUONG:
            canh_bao.append(f"{ten}: {_dinh_dang_tien(gia)} thấp bất thường cho vé xe khách liên tỉnh (dưới {_dinh_dang_tien(GIA_THAP_BAT_THUONG)})")
        elif gia > GIA_CAO_BAT_THUONG:
            canh_bao.append(f"{ten}: {_dinh_dang_tien(gia)} cao bất thường cho 1 vé (trên {_dinh_dang_tien(GIA_CAO_BAT_THUONG)})")
        cu = (gia_bo_truoc or {}).get(cap)
        if cu and cu != gia:
            if gia / cu < TI_LE_GIAM_CANH_BAO:
                canh_bao.append(f"{ten}: {_dinh_dang_tien(gia)} giảm hơn một nửa so với giá bộ trước {_dinh_dang_tien(cu)}")
            elif gia / cu > TI_LE_TANG_CANH_BAO:
                canh_bao.append(f"{ten}: {_dinh_dang_tien(gia)} tăng hơn gấp đôi so với giá bộ trước {_dinh_dang_tien(cu)}")
    # Chặng ngắn nằm trong chặng dài thì không được đắt hơn chặng dài
    for (di, den), gia in gia_moi.items():
        for (di2, den2), gia2 in gia_moi.items():
            if (di, den) != (di2, den2) and thu_tu[di] <= thu_tu[di2] and thu_tu[den2] <= thu_tu[den] and gia2 > gia:
                canh_bao.append(f"{ten_cap[(di2, den2)]} ({_dinh_dang_tien(gia2)}) là chặng ngắn hơn nhưng đắt hơn {ten_cap[(di, den)]} ({_dinh_dang_tien(gia)})")
    return canh_bao[:SO_CANH_BAO_TOI_DA]


def _bao_loi_neu_chua_xac_nhan(canh_bao: list[str], xac_nhan: bool) -> None:
    if canh_bao and not xac_nhan:
        raise GiaTriLoi("Giá có dấu hiệu bất thường: " + "; ".join(canh_bao) + ". Hãy kiểm tra lại, hoặc xác nhận nếu đúng.")


def _gia_theo_cap(bo: dict | None) -> dict[tuple[str, str], int] | None:
    if bo is None:
        return None
    return {(str(g["diem_di_id"]), str(g["diem_den_id"])): int(g["gia_goc"]) for g in bo["danh_sach_gia"]}


# ---------------------------------------------------------
# Tạo / sửa / xóa / liệt kê bộ giá
# ---------------------------------------------------------
def _lay_bo(bo_id: str) -> dict:
    bo = repo.tim_bo_theo_id(bo_id)
    if not bo:
        raise GiaTriLoi("Không tìm thấy bộ giá vé")
    return bo


def _so_chuyen_da_sinh(bo: dict) -> int:
    return repo.so_chuyen_trong_khoang(str(bo["tuyen_id"]), bo["ap_dung_tu"], bo["ap_dung_den"])


def _kiem_tra_khoang(bat_dau: datetime.date, ket_thuc: datetime.date | None) -> None:
    if ket_thuc is None:
        raise GiaTriLoi("Bộ giá phải có ngày kết thúc")
    if ket_thuc < bat_dau:
        raise GiaTriLoi("Ngày kết thúc phải sau hoặc bằng ngày bắt đầu")


def _kiem_tra_chua_co_chuyen_tu(tuyen_id: str, bat_dau: datetime.date, ngay: datetime.date) -> None:
    """Bắt đầu từ hôm nay trở về trước sẽ đổi giá của những chuyến đã sinh cho các ngày đó → chỉ cho phép khi chưa có."""
    if bat_dau <= ngay and repo.so_chuyen_trong_khoang(tuyen_id, bat_dau, ngay) > 0:
        raise GiaTriLoi("Tuyến đã có chuyến khởi hành từ ngày này nên bộ giá không được bắt đầu sớm như vậy — phải bắt đầu từ ngày mai trở đi")


def _chuan_bi_tao(tuyen_id: str, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict]) -> dict:
    if not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến không tồn tại")
    ngay = hom_nay()
    cac_bo = _sap_xep(repo.danh_sach_bo(tuyen_id))
    if cac_bo:
        # Bộ mới luôn nối liền bộ cuối: bắt đầu ngày liền sau ngày kết thúc của bộ trước
        bat_dau = cac_bo[-1]["ap_dung_den"] + MOT_NGAY
        if ap_dung_tu is not None and ap_dung_tu != bat_dau:
            raise GiaTriLoi(f"Bộ mới phải bắt đầu từ ngày {_dinh_dang_ngay(bat_dau)} — ngay sau khi bộ giá trước kết thúc")
    else:
        bat_dau = ap_dung_tu or ngay + MOT_NGAY
        if bat_dau < ngay:
            raise GiaTriLoi("Bộ giá đầu tiên không được bắt đầu áp dụng trong quá khứ")
    _kiem_tra_khoang(bat_dau, ap_dung_den)
    if ap_dung_den < ngay:
        raise GiaTriLoi("Ngày kết thúc không được ở quá khứ")
    _kiem_tra_chua_co_chuyen_tu(tuyen_id, bat_dau, ngay)
    chuan, gia_moi = _chuan_hoa_gia(tuyen_id, danh_sach_gia)
    return {"bat_dau": bat_dau, "ket_thuc": ap_dung_den, "chuan": chuan, "gia_moi": gia_moi, "bo_truoc": cac_bo[-1] if cac_bo else None}


def _chuan_bi_sua(bo: dict, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict]) -> dict:
    tuyen_id = str(bo["tuyen_id"])
    ngay = hom_nay()
    cac_bo = _sap_xep(repo.danh_sach_bo(tuyen_id))
    vi_tri = next(i for i, b in enumerate(cac_bo) if str(b["id"]) == str(bo["id"]))
    la_dau, la_cuoi = vi_tri == 0, vi_tri == len(cac_bo) - 1
    bat_dau = ap_dung_tu or bo["ap_dung_tu"]
    ket_thuc = ap_dung_den
    _kiem_tra_khoang(bat_dau, ket_thuc)

    chuan, gia_moi = _chuan_hoa_gia(tuyen_id, danh_sach_gia)
    if bat_dau != bo["ap_dung_tu"] and not la_dau:
        raise GiaTriLoi("Chỉ đổi được ngày bắt đầu của bộ giá đầu tiên — các bộ sau phải nối liền bộ trước")
    if ket_thuc != bo["ap_dung_den"] and not la_cuoi:
        raise GiaTriLoi("Chỉ đổi được ngày kết thúc của bộ giá cuối cùng — bộ sau đã nối liền ngay sau bộ này")

    so_chuyen = _so_chuyen_da_sinh(bo)
    if so_chuyen:
        if bat_dau != bo["ap_dung_tu"] or gia_moi != _gia_theo_cap(bo):
            raise GiaTriLoi(
                f"Bộ giá này đã có {so_chuyen} chuyến được sinh ra nên không sửa giá hay ngày bắt đầu được — "
                + ("chỉ kéo dài hoặc rút ngắn được ngày kết thúc; muốn đổi giá hãy tạo bộ giá mới nối tiếp" if la_cuoi
                   else "muốn đổi giá hãy tạo bộ giá mới nối tiếp bộ cuối cùng")
            )
        chuyen_cuoi = repo.ngay_chuyen_cuoi_trong_khoang(tuyen_id, bo["ap_dung_tu"], bo["ap_dung_den"])
        if chuyen_cuoi and ket_thuc < chuyen_cuoi:
            raise GiaTriLoi(f"Không rút ngắn trước ngày {_dinh_dang_ngay(chuyen_cuoi)} vì đã có chuyến sinh ra tới ngày đó")
    else:
        if bat_dau != bo["ap_dung_tu"]:
            if bat_dau < ngay:
                raise GiaTriLoi("Bộ giá không được dời ngày bắt đầu về quá khứ")
            _kiem_tra_chua_co_chuyen_tu(tuyen_id, bat_dau, ngay)
        if ket_thuc != bo["ap_dung_den"] and ket_thuc < ngay:
            raise GiaTriLoi("Ngày kết thúc không được ở quá khứ")
    return {
        "bat_dau": bat_dau, "ket_thuc": ket_thuc, "chuan": chuan, "gia_moi": gia_moi,
        "bo_truoc": cac_bo[vi_tri - 1] if vi_tri > 0 else None,
    }


def _xem_truoc(tuyen_id: str, kq: dict) -> dict:
    ten_cap = {(di, den): ten for di, den, ten in _cac_cap_cua_tuyen(tuyen_id)}
    gia_cu = _gia_theo_cap(kq["bo_truoc"])
    bo_truoc = kq["bo_truoc"]
    return {
        "ap_dung_tu": kq["bat_dau"],
        "ap_dung_den": kq["ket_thuc"],
        "bo_truoc": {"ap_dung_tu": bo_truoc["ap_dung_tu"], "ap_dung_den": bo_truoc["ap_dung_den"]} if bo_truoc else None,
        "thay_doi": [
            {"ten_chang": ten_cap[cap], "gia_cu": (gia_cu or {}).get(cap), "gia_moi": gia}
            for cap, gia in kq["gia_moi"].items()
        ],
        "canh_bao": _canh_bao_bo(tuyen_id, kq["gia_moi"], gia_cu),
    }


def xem_truoc_tao_bo(tuyen_id: str, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict]) -> dict:
    return _xem_truoc(tuyen_id, _chuan_bi_tao(tuyen_id, ap_dung_tu, ap_dung_den, danh_sach_gia))


def tao_bo(tuyen_id: str, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict], xac_nhan_canh_bao: bool = False) -> dict:
    kq = _chuan_bi_tao(tuyen_id, ap_dung_tu, ap_dung_den, danh_sach_gia)
    _bao_loi_neu_chua_xac_nhan(_xem_truoc(tuyen_id, kq)["canh_bao"], xac_nhan_canh_bao)
    try:
        bo_id = repo.tao_bo(tuyen_id, kq["bat_dau"], kq["ket_thuc"], kq["chuan"])
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f"Tuyến đã có bộ giá áp dụng từ ngày {_dinh_dang_ngay(kq['bat_dau'])}")
    return next(b for b in danh_sach_bo(tuyen_id) if str(b["id"]) == bo_id)


def xem_truoc_sua_bo(bo_id: str, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict]) -> dict:
    bo = _lay_bo(bo_id)
    return _xem_truoc(str(bo["tuyen_id"]), _chuan_bi_sua(bo, ap_dung_tu, ap_dung_den, danh_sach_gia))


def sua_bo(bo_id: str, ap_dung_tu, ap_dung_den, danh_sach_gia: list[dict], xac_nhan_canh_bao: bool = False) -> dict:
    bo = _lay_bo(bo_id)
    tuyen_id = str(bo["tuyen_id"])
    kq = _chuan_bi_sua(bo, ap_dung_tu, ap_dung_den, danh_sach_gia)
    # Chỉ cảnh báo giá khi giá thực sự đổi (kéo dài/rút ngắn ngày kết thúc thì giá giữ nguyên)
    if kq["gia_moi"] != _gia_theo_cap(bo):
        _bao_loi_neu_chua_xac_nhan(_xem_truoc(tuyen_id, kq)["canh_bao"], xac_nhan_canh_bao)
    try:
        repo.sua_bo(bo_id, kq["bat_dau"], kq["ket_thuc"], kq["chuan"])
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi(f"Tuyến đã có bộ giá áp dụng từ ngày {_dinh_dang_ngay(kq['bat_dau'])}")
    return next(b for b in danh_sach_bo(tuyen_id) if str(b["id"]) == str(bo_id))


def xoa_bo(bo_id: str) -> None:
    bo = _lay_bo(bo_id)
    tuyen_id = str(bo["tuyen_id"])
    cac_bo = _sap_xep(repo.danh_sach_bo(tuyen_id))
    if str(cac_bo[-1]["id"]) != str(bo_id):
        raise GiaTriLoi("Chỉ xóa được bộ giá cuối cùng của tuyến — xóa bộ ở giữa sẽ làm hở giữa các bộ")
    so_chuyen = _so_chuyen_da_sinh(bo)
    if so_chuyen:
        raise GiaTriLoi(f"Không thể xóa: bộ giá này đã có {so_chuyen} chuyến được sinh ra — hãy tạo bộ giá mới nối tiếp thay thế")
    repo.xoa_bo(bo_id)


def danh_sach_bo(tuyen_id: str | None = None) -> list[dict]:
    """Mọi bộ giá kèm: trạng thái, số chuyến đã sinh, khóa, có phải bộ cuối không, ngày chuyến xa nhất đã sinh, chặng còn
    thiếu (chỉ dữ liệu cũ)."""
    ngay = hom_nay()
    theo_tuyen: dict[str, list[dict]] = {}
    for b in repo.danh_sach_bo(tuyen_id):
        theo_tuyen.setdefault(str(b["tuyen_id"]), []).append(b)
    ket_qua: list[dict] = []
    for tid, cac_bo in theo_tuyen.items():
        cac_bo = _sap_xep(cac_bo)
        cac_cap = _cac_cap_cua_tuyen(tid)
        thu_tu_cap = {(di, den): i for i, (di, den, _) in enumerate(cac_cap)}
        for i, b in enumerate(cac_bo):
            b["trang_thai"] = trang_thai_bo(b["ap_dung_tu"], b["ap_dung_den"], ngay)
            b["so_chuyen_da_sinh"] = repo.so_chuyen_trong_khoang(tid, b["ap_dung_tu"], b["ap_dung_den"])
            b["khoa"] = b["so_chuyen_da_sinh"] > 0
            b["la_bo_cuoi"] = i == len(cac_bo) - 1
            b["ngay_chuyen_cuoi"] = repo.ngay_chuyen_cuoi_trong_khoang(tid, b["ap_dung_tu"], b["ap_dung_den"]) if b["khoa"] else None
            b["cac_cap_thieu_gia"] = _cap_thieu_trong_bo(b, cac_cap)
            b["danh_sach_gia"].sort(key=lambda g: thu_tu_cap.get((str(g["diem_di_id"]), str(g["diem_den_id"])), 999))
        ket_qua.extend(cac_bo)
    return sorted(ket_qua, key=lambda b: (b["ten_tuyen"], b["ap_dung_tu"]))
