"""Giá vé — UC-33, NGHIEP_VU.md mục 3.1 (giá gốc theo cặp điểm đi/đến,
không phụ thuộc loại xe — hệ số loai_xe.he_so_gia nhân vào lúc bán vé).
Đúng theo ARCHITECTURE.md mục 2: Service quyết định quy tắc nghiệp vụ,
Repository chỉ đọc/ghi SQL thuần.

Quy tắc đổi giá (NGHIEP_VU.md mục 3.1, UC-33): vé đã đặt luôn giữ giá lúc khách giữ ghế (ve.gia) nên đổi giá không
ảnh hưởng vé cũ; để đổi giá có lịch sử và không đột ngột, giá đã được dùng để sinh chuyến (tuyến có chuyến khởi hành
trong khoảng ngày áp dụng của giá đó) không được sửa số tiền/xóa, kể cả khi chưa có khách đặt — chỉ đóng bằng ngày
kết thúc, rồi thêm giá mới. Giá mới mặc định bắt đầu từ ngày mai, tự đóng giá cũ ở ngày liền trước, và phải qua bước
xem trước (cảnh báo giá bất thường) trước khi lưu.
"""

import datetime
from zoneinfo import ZoneInfo

import psycopg2.errors

from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import gia_ve_repository as repo
from app.utils.loi import GiaTriLoi

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")

# Ngưỡng cảnh báo giá bất thường (chỉ cảnh báo, quản lý xác nhận vẫn lưu được)
TI_LE_GIAM_CANH_BAO = 0.5  # giá mới thấp hơn giá hiện tại quá 50%
TI_LE_TANG_CANH_BAO = 2.0  # giá mới cao hơn giá hiện tại hơn 2 lần
GIA_THAP_BAT_THUONG = 50_000
GIA_CAO_BAT_THUONG = 5_000_000
SO_CANH_BAO_TOI_DA = 4


def hom_nay() -> datetime.date:
    return datetime.datetime.now(MUI_GIO_VN).date()


def _dinh_dang_tien(so) -> str:
    return f"{int(so):,}".replace(",", ".") + "đ"


def _dinh_dang_ngay(ngay) -> str:
    return ngay.strftime("%d/%m/%Y") if ngay else "…"


def _da_hieu_luc(gv: dict, ngay: datetime.date) -> bool:
    return gv["ap_dung_tu"] is None or gv["ap_dung_tu"] <= ngay


def _con_hieu_luc(gv: dict, ngay: datetime.date) -> bool:
    """Đang áp dụng hoặc sắp áp dụng (chưa kết thúc tính tới `ngay`)."""
    return gv["ap_dung_den"] is None or gv["ap_dung_den"] >= ngay


def trang_thai_dong_gia(gv: dict, ngay: datetime.date) -> str:
    if not _con_hieu_luc(gv, ngay):
        return "da_ket_thuc"
    if not _da_hieu_luc(gv, ngay):
        return "sap_ap_dung"
    return "dang_ap_dung"


def _so_chuyen_da_sinh(gv: dict) -> int:
    """Số chuyến của tuyến đã sinh ra trong khoảng ngày áp dụng của dòng giá này."""
    return repo.so_chuyen_trong_khoang(str(gv["tuyen_id"]), gv["ap_dung_tu"], gv["ap_dung_den"])


def _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id: str) -> list[dict]:
    """Danh sách khu vực (không trùng lặp) mà tuyến đi qua, theo đúng thứ
    tự tuyến di chuyển (dùng thu_tu điểm dừng nhỏ nhất của mỗi khu vực) —
    dùng để xác định cặp điểm đi/đến hợp lệ (điểm đi phải đứng trước
    điểm đến theo đúng chiều tuyến)."""
    diem = dia_diem_repo.danh_sach_diem_theo_tuyen(tuyen_id)
    da_thay: dict[str, dict] = {}
    for d in sorted(diem, key=lambda x: x["thu_tu"]):
        kv_id = str(d["khu_vuc_id"])
        if kv_id not in da_thay:
            da_thay[kv_id] = {"khu_vuc_id": kv_id, "ten": d["ten_khu_vuc"]}
    return list(da_thay.values())


def cac_cap_thieu_gia(tuyen_id: str) -> list[str]:
    """Các cặp khu vực (điểm đi → điểm đến theo chiều đi của tuyến) chưa có giá đang hoặc sắp áp dụng. Rỗng = tuyến
    đã đủ giá vé, bán được vé mọi đoạn."""
    khu_vuc = _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id)
    ngay = hom_nay()
    da_co_gia = {(str(g["diem_di_id"]), str(g["diem_den_id"])) for g in repo.danh_sach_gia_ve(tuyen_id) if _con_hieu_luc(g, ngay)}
    return [
        f"{a['ten']} → {b['ten']}"
        for i, a in enumerate(khu_vuc)
        for b in khu_vuc[i + 1:]
        if (a["khu_vuc_id"], b["khu_vuc_id"]) not in da_co_gia
    ]


def _kiem_tra_cap_diem(tuyen_id: str, diem_di_id: str, diem_den_id: str) -> None:
    if diem_di_id == diem_den_id:
        raise GiaTriLoi("Điểm đi và điểm đến không được trùng nhau")

    khu_vuc_tuyen = _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id)
    thu_tu_theo_id = {kv["khu_vuc_id"]: i for i, kv in enumerate(khu_vuc_tuyen)}

    if diem_di_id not in thu_tu_theo_id or diem_den_id not in thu_tu_theo_id:
        raise GiaTriLoi("Điểm đi/điểm đến phải là khu vực mà tuyến này đi qua")

    if thu_tu_theo_id[diem_di_id] >= thu_tu_theo_id[diem_den_id]:
        raise GiaTriLoi("Điểm đi phải đứng trước điểm đến theo đúng chiều di chuyển của tuyến")


def _kiem_tra_thoi_han(ap_dung_tu, ap_dung_den) -> None:
    if ap_dung_tu and ap_dung_den and ap_dung_tu > ap_dung_den:
        raise GiaTriLoi("Ngày bắt đầu áp dụng phải trước ngày kết thúc")


def _khoang_ngay_giao_nhau(a1, b1, a2, b2) -> bool:
    """True nếu 2 khoảng ngày [a1, b1] và [a2, b2] giao nhau — None ở đầu
    khoảng coi như vô cực về trước, None ở cuối coi như vô cực về sau
    (đúng nghĩa "áp dụng vô thời hạn")."""
    return (a1 is None or b2 is None or a1 <= b2) and (a2 is None or b1 is None or a2 <= b1)


_LOI_CHONG_LAN = (
    "Khoảng thời gian áp dụng bị chồng lấn với 1 giá vé khác đã cấu hình "
    "cho đúng cặp điểm đi/đến này — sửa lại khoảng ngày hoặc sửa giá vé cũ"
)


def _kiem_tra_khong_chong_leo(tuyen_id: str, diem_di_id: str, diem_den_id: str, ap_dung_tu, ap_dung_den, tru_id: str | None = None) -> None:
    """UNIQUE constraint của bảng gia_ve không tự chặn được 2 dòng cùng
    ap_dung_tu = NULL (SQL coi NULL khác NULL, không tính là trùng) — phải
    tự kiểm tra chồng lấn khoảng ngày áp dụng ở đây, tránh 2 giá vé "vô
    thời hạn" (hoặc 2 khoảng ngày đè lên nhau) cùng tồn tại cho 1 cặp điểm,
    không biết giá nào là giá thật."""
    hien_co = repo.danh_sach_gia_ve_theo_cap_diem(tuyen_id, diem_di_id, diem_den_id)
    for gv in hien_co:
        if tru_id and str(gv["id"]) == str(tru_id):
            continue
        if _khoang_ngay_giao_nhau(ap_dung_tu, ap_dung_den, gv["ap_dung_tu"], gv["ap_dung_den"]):
            raise GiaTriLoi(_LOI_CHONG_LAN)


# ---------------------------------------------------------
# Cảnh báo giá bất thường (lớp bảo vệ khi nhập nhầm, vd 30.000 thay vì 300.000)
# ---------------------------------------------------------
def _gia_hieu_luc_vao_ngay(cac_dong: list[dict], ngay: datetime.date) -> dict | None:
    for g in cac_dong:
        if _da_hieu_luc(g, ngay) and _con_hieu_luc(g, ngay):
            return g
    return None


def _canh_bao_gia(
    tuyen_id: str, diem_di_id: str, diem_den_id: str, gia_goc: int, ngay_ap_dung: datetime.date,
    tru_id: str | None = None, gia_cu_tham_chieu: int | None = None,
) -> list[str]:
    canh_bao: list[str] = []
    tat_ca = [g for g in repo.danh_sach_gia_ve(tuyen_id) if not (tru_id and str(g["id"]) == str(tru_id))]

    if gia_goc < GIA_THAP_BAT_THUONG:
        canh_bao.append(f"{_dinh_dang_tien(gia_goc)} thấp bất thường cho vé xe khách liên tỉnh (dưới {_dinh_dang_tien(GIA_THAP_BAT_THUONG)})")
    elif gia_goc > GIA_CAO_BAT_THUONG:
        canh_bao.append(f"{_dinh_dang_tien(gia_goc)} cao bất thường cho 1 vé (trên {_dinh_dang_tien(GIA_CAO_BAT_THUONG)})")

    cung_cap = [g for g in tat_ca if str(g["diem_di_id"]) == diem_di_id and str(g["diem_den_id"]) == diem_den_id]
    gia_hien_tai = _gia_hieu_luc_vao_ngay(cung_cap, ngay_ap_dung) or _gia_hieu_luc_vao_ngay(cung_cap, hom_nay())
    gia_tham_chieu = gia_cu_tham_chieu if gia_cu_tham_chieu is not None else (int(gia_hien_tai["gia_goc"]) if gia_hien_tai else None)
    if gia_tham_chieu:
        ti_le = gia_goc / gia_tham_chieu
        if ti_le < TI_LE_GIAM_CANH_BAO:
            canh_bao.append(f"Giá mới {_dinh_dang_tien(gia_goc)} giảm hơn một nửa so với giá hiện tại {_dinh_dang_tien(gia_tham_chieu)} của chặng này")
        elif ti_le > TI_LE_TANG_CANH_BAO:
            canh_bao.append(f"Giá mới {_dinh_dang_tien(gia_goc)} tăng hơn gấp đôi so với giá hiện tại {_dinh_dang_tien(gia_tham_chieu)} của chặng này")

    # Chặng ngắn nằm trong chặng dài thì không được đắt hơn chặng dài
    thu_tu = {kv["khu_vuc_id"]: i for i, kv in enumerate(_khu_vuc_theo_tuyen_co_thu_tu(tuyen_id))}
    ten = {kv["khu_vuc_id"]: kv["ten"] for kv in _khu_vuc_theo_tuyen_co_thu_tu(tuyen_id)}
    if diem_di_id in thu_tu and diem_den_id in thu_tu:
        i, j = thu_tu[diem_di_id], thu_tu[diem_den_id]
        theo_cap: dict = {}
        for g in tat_ca:
            theo_cap.setdefault((str(g["diem_di_id"]), str(g["diem_den_id"])), []).append(g)
        for (di, den), dong in theo_cap.items():
            if (di, den) == (diem_di_id, diem_den_id) or di not in thu_tu or den not in thu_tu:
                continue
            g = _gia_hieu_luc_vao_ngay(dong, ngay_ap_dung)
            if not g:
                continue
            k, l = thu_tu[di], thu_tu[den]
            gia_khac = int(g["gia_goc"])
            if k >= i and l <= j and gia_khac > gia_goc:
                canh_bao.append(f"Chặng ngắn hơn {ten[di]} → {ten[den]} đang có giá {_dinh_dang_tien(gia_khac)}, cao hơn giá chặng dài này")
            elif k <= i and l >= j and gia_khac < gia_goc:
                canh_bao.append(f"Chặng dài hơn {ten[di]} → {ten[den]} đang có giá {_dinh_dang_tien(gia_khac)}, thấp hơn giá chặng ngắn này")
    return canh_bao[:SO_CANH_BAO_TOI_DA]


def _bao_loi_neu_chua_xac_nhan(canh_bao: list[str], xac_nhan: bool) -> None:
    if canh_bao and not xac_nhan:
        raise GiaTriLoi("Giá có dấu hiệu bất thường: " + "; ".join(canh_bao) + ". Hãy kiểm tra lại, hoặc xác nhận nếu đúng.")


# ---------------------------------------------------------
# Tạo giá mới
# ---------------------------------------------------------
def _chuan_bi_tao(tuyen_id: str, diem_di_id: str, diem_den_id: str, ap_dung_tu, ap_dung_den) -> tuple[datetime.date, dict | None, datetime.date | None]:
    """Kiểm tra và quyết định: ngày bắt đầu thực tế (mặc định ngày mai), giá cũ cần đóng (nếu có) và ngày đóng."""
    if not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến không tồn tại")
    _kiem_tra_cap_diem(tuyen_id, diem_di_id, diem_den_id)

    ngay = hom_nay()
    bat_dau = ap_dung_tu or ngay + datetime.timedelta(days=1)
    if bat_dau < ngay:
        raise GiaTriLoi("Giá mới không được bắt đầu áp dụng trong quá khứ")
    _kiem_tra_thoi_han(bat_dau, ap_dung_den)

    giao_nhau = [
        g for g in repo.danh_sach_gia_ve_theo_cap_diem(tuyen_id, diem_di_id, diem_den_id)
        if _khoang_ngay_giao_nhau(bat_dau, ap_dung_den, g["ap_dung_tu"], g["ap_dung_den"])
    ]
    if not giao_nhau:
        return bat_dau, None, None
    if len(giao_nhau) > 1:
        raise GiaTriLoi(_LOI_CHONG_LAN)

    # Giá mới thay thế giá hiện hành: tự đóng giá cũ ở ngày liền trước, miễn giá mới phủ hết phần còn lại của giá cũ
    cu = giao_nhau[0]
    bat_dau_cu_truoc = cu["ap_dung_tu"] is None or cu["ap_dung_tu"] < bat_dau
    phu_het = ap_dung_den is None or (cu["ap_dung_den"] is not None and ap_dung_den >= cu["ap_dung_den"])
    if not (bat_dau_cu_truoc and phu_het):
        raise GiaTriLoi(_LOI_CHONG_LAN)
    ngay_dong = bat_dau - datetime.timedelta(days=1)
    if ngay_dong < ngay and _so_chuyen_da_sinh(cu) > 0:
        raise GiaTriLoi(
            "Giá cũ đã có chuyến được sinh ra nên không thể kết thúc trong quá khứ — hãy cho giá mới bắt đầu từ ngày mai trở đi"
        )
    return bat_dau, cu, ngay_dong


def xem_truoc_tao_gia_ve(tuyen_id: str, diem_di_id: str, diem_den_id: str, gia_goc: int, ap_dung_tu, ap_dung_den) -> dict:
    bat_dau, cu, ngay_dong = _chuan_bi_tao(tuyen_id, diem_di_id, diem_den_id, ap_dung_tu, ap_dung_den)
    return {
        "gia_goc": gia_goc,
        "ap_dung_tu": bat_dau,
        "ap_dung_den": ap_dung_den,
        "gia_cu": (
            {"gia_goc": int(cu["gia_goc"]), "ap_dung_tu": cu["ap_dung_tu"], "ap_dung_den": cu["ap_dung_den"], "se_ket_thuc_vao": ngay_dong}
            if cu else None
        ),
        "canh_bao": _canh_bao_gia(tuyen_id, diem_di_id, diem_den_id, gia_goc, bat_dau),
    }


def tao_gia_ve(
    tuyen_id: str, diem_di_id: str, diem_den_id: str, gia_goc: int, ap_dung_tu, ap_dung_den, xac_nhan_canh_bao: bool = False
) -> dict:
    bat_dau, cu, ngay_dong = _chuan_bi_tao(tuyen_id, diem_di_id, diem_den_id, ap_dung_tu, ap_dung_den)
    _bao_loi_neu_chua_xac_nhan(_canh_bao_gia(tuyen_id, diem_di_id, diem_den_id, gia_goc, bat_dau), xac_nhan_canh_bao)
    try:
        return repo.tao_gia_ve_va_dong_gia_cu(
            tuyen_id, diem_di_id, diem_den_id, gia_goc, bat_dau, ap_dung_den, str(cu["id"]) if cu else None, ngay_dong
        )
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi("Đã có giá vé cho đúng cặp điểm đi/đến này (cùng thời hạn áp dụng)")


# ---------------------------------------------------------
# Sửa / xóa giá đã có
# ---------------------------------------------------------
def _kiem_tra_duoc_sua(gv: dict, gia_goc: int, ap_dung_tu, ap_dung_den) -> datetime.date | None:
    """Trả về ngày bắt đầu hiệu lực cuối cùng (giữ nguyên nếu giá đã áp dụng, mặc định ngày mai nếu giá chưa áp dụng mà
    bỏ trống). Ném lỗi nếu giá đã được dùng để sinh chuyến mà bị sửa số tiền/ngày bắt đầu."""
    ngay = hom_nay()
    so_chuyen = _so_chuyen_da_sinh(gv)
    if so_chuyen:
        if int(gia_goc) != int(gv["gia_goc"]) or ap_dung_tu != gv["ap_dung_tu"]:
            raise GiaTriLoi(
                f"Giá này đã có {so_chuyen} chuyến được sinh ra nên không sửa số tiền hay ngày bắt đầu được — "
                "hãy đặt ngày kết thúc cho giá này rồi thêm giá mới"
            )
        if gv["ap_dung_den"] is not None and gv["ap_dung_den"] < ngay:
            raise GiaTriLoi("Giá này đã kết thúc và đã có chuyến được sinh ra nên không sửa được nữa")
        if ap_dung_den is not None and ap_dung_den < ngay:
            raise GiaTriLoi("Ngày kết thúc không được trước hôm nay vì giá này đã có chuyến được sinh ra")
        return ap_dung_tu
    if _da_hieu_luc(gv, ngay):
        return ap_dung_tu
    bat_dau = ap_dung_tu or ngay + datetime.timedelta(days=1)
    if bat_dau < ngay:
        raise GiaTriLoi("Giá chưa áp dụng không được dời về quá khứ")
    return bat_dau


def xem_truoc_sua_gia_ve(gia_ve_id: str, gia_goc: int, ap_dung_tu, ap_dung_den) -> dict:
    gv = repo.tim_gia_ve_theo_id(gia_ve_id)
    if not gv:
        raise GiaTriLoi("Không tìm thấy giá vé")
    _kiem_tra_thoi_han(ap_dung_tu, ap_dung_den)
    bat_dau = _kiem_tra_duoc_sua(gv, gia_goc, ap_dung_tu, ap_dung_den)
    _kiem_tra_khong_chong_leo(str(gv["tuyen_id"]), str(gv["diem_di_id"]), str(gv["diem_den_id"]), bat_dau, ap_dung_den, tru_id=gia_ve_id)
    doi_so_tien = int(gia_goc) != int(gv["gia_goc"])
    return {
        "gia_goc": gia_goc,
        "ap_dung_tu": bat_dau,
        "ap_dung_den": ap_dung_den,
        "gia_cu": {"gia_goc": int(gv["gia_goc"]), "ap_dung_tu": gv["ap_dung_tu"], "ap_dung_den": gv["ap_dung_den"], "se_ket_thuc_vao": None},
        "canh_bao": (
            _canh_bao_gia(str(gv["tuyen_id"]), str(gv["diem_di_id"]), str(gv["diem_den_id"]), gia_goc, bat_dau or hom_nay(), tru_id=gia_ve_id, gia_cu_tham_chieu=int(gv["gia_goc"]))
            if doi_so_tien else []
        ),
    }


def sua_gia_ve(gia_ve_id: str, gia_goc: int, ap_dung_tu, ap_dung_den, xac_nhan_canh_bao: bool = False) -> None:
    gia_ve_hien_tai = repo.tim_gia_ve_theo_id(gia_ve_id)
    if not gia_ve_hien_tai:
        raise GiaTriLoi("Không tìm thấy giá vé")
    _kiem_tra_thoi_han(ap_dung_tu, ap_dung_den)
    bat_dau = _kiem_tra_duoc_sua(gia_ve_hien_tai, gia_goc, ap_dung_tu, ap_dung_den)
    _kiem_tra_khong_chong_leo(
        str(gia_ve_hien_tai["tuyen_id"]),
        str(gia_ve_hien_tai["diem_di_id"]),
        str(gia_ve_hien_tai["diem_den_id"]),
        bat_dau,
        ap_dung_den,
        tru_id=gia_ve_id,
    )
    if int(gia_goc) != int(gia_ve_hien_tai["gia_goc"]):
        canh_bao = _canh_bao_gia(
            str(gia_ve_hien_tai["tuyen_id"]), str(gia_ve_hien_tai["diem_di_id"]), str(gia_ve_hien_tai["diem_den_id"]),
            gia_goc, bat_dau or hom_nay(), tru_id=gia_ve_id, gia_cu_tham_chieu=int(gia_ve_hien_tai["gia_goc"]),
        )
        _bao_loi_neu_chua_xac_nhan(canh_bao, xac_nhan_canh_bao)
    try:
        repo.sua_gia_ve(gia_ve_id, gia_goc, bat_dau, ap_dung_den)
    except psycopg2.errors.UniqueViolation:
        raise GiaTriLoi("Đã có giá vé khác trùng thời hạn áp dụng cho đúng cặp điểm đi/đến này")


def danh_sach_gia_ve(tuyen_id: str | None = None) -> list[dict]:
    ngay = hom_nay()
    ket_qua = repo.danh_sach_gia_ve(tuyen_id)
    for g in ket_qua:
        g["trang_thai"] = trang_thai_dong_gia(g, ngay)
        # Khóa số tiền: giá đã được dùng để sinh chuyến (chỉ còn đóng bằng ngày kết thúc)
        g["so_chuyen_da_sinh"] = _so_chuyen_da_sinh(g)
        g["khoa_so_tien"] = g["so_chuyen_da_sinh"] > 0
    return ket_qua


def xoa_gia_ve(gia_ve_id: str) -> None:
    gv = repo.tim_gia_ve_theo_id(gia_ve_id)
    if not gv:
        raise GiaTriLoi("Không tìm thấy giá vé")
    so_chuyen = _so_chuyen_da_sinh(gv)
    if so_chuyen:
        raise GiaTriLoi(
            f"Không thể xóa: giá này đã có {so_chuyen} chuyến được sinh ra — hãy đặt ngày kết thúc cho giá này (nút Sửa)"
        )
    repo.xoa_gia_ve(gia_ve_id)
