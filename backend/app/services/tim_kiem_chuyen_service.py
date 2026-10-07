"""Tra cứu chuyến công khai — UC-04, NGHIEP_VU.md mục 3.4 bước 1-3, mục 8.1 điểm 1.

Không cần đăng nhập. Chỉ ĐỌC: chưa khóa ghế/đặt vé (UC-05). Quy tắc nằm ở đây, SQL nằm ở
repositories/tim_kiem_chuyen_repository.py.
"""

import datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from app.repositories import tim_kiem_chuyen_repository as repo
from app.utils.loi import GiaTriLoi

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")


# ---------------------------------------------------------
# Các hàm thuần (không đụng DB) — dễ unit test
# ---------------------------------------------------------
def gio_tai_diem(gio_khoi_hanh: datetime.datetime, phut: int) -> datetime.datetime:
    """Giờ dự kiến xe tới 1 điểm = giờ khởi hành + số phút từ điểm đầu (đã tính theo đúng chiều)."""
    return gio_khoi_hanh + datetime.timedelta(minutes=phut)


def chon_gia(
    dong_gia: list[dict], chieu: str, khu_vuc_di: str, khu_vuc_den: str, ngay: datetime.date, he_so_gia
) -> int | None:
    """Giá vé bán ra của 1 chuyến cho cặp khu vực khách tìm — `None` nếu chưa cấu hình giá.

    `gia_ve` chỉ lưu 1 dòng cho mỗi cặp theo thứ tự CHIỀU XUÔI, dùng chung 2 chiều (THAY_DOI_TUYEN_2_CHIEU.md
    mục 3) → chuyến ngược phải đảo cặp đi/đến trước khi tra. Có giá theo mùa đang áp dụng đúng ngày đi thì
    dùng giá mùa, không thì dùng giá thường (không giới hạn thời gian). Giá bán = giá gốc × hệ số loại xe.
    """
    cap = (khu_vuc_di, khu_vuc_den) if chieu == "xuoi" else (khu_vuc_den, khu_vuc_di)
    ung_vien = [g for g in dong_gia if (str(g["diem_di_id"]), str(g["diem_den_id"])) == cap]

    def dang_ap_dung(g) -> bool:
        return (g["ap_dung_tu"] is None or g["ap_dung_tu"] <= ngay) and (g["ap_dung_den"] is None or ngay <= g["ap_dung_den"])

    gia_mua = [g for g in ung_vien if (g["ap_dung_tu"] or g["ap_dung_den"]) and dang_ap_dung(g)]
    gia_thuong = [g for g in ung_vien if not g["ap_dung_tu"] and not g["ap_dung_den"]]
    if gia_mua:
        # Nhiều giá mùa chồng nhau thì lấy mùa bắt đầu muộn nhất (cụ thể nhất)
        chon = max(gia_mua, key=lambda g: g["ap_dung_tu"] or datetime.date.min)
    elif gia_thuong:
        chon = gia_thuong[0]
    else:
        return None
    return int((Decimal(chon["gia_goc"]) * Decimal(he_so_gia)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def tinh_ghe_dang_giu(doan_ve: list[dict], hl_don: int, hl_tra: int) -> set[str]:
    """Ghế bị chiếm trên đoạn `[hl_don, hl_tra)`: có vé đang giữ mà đoạn của nó GIAO với đoạn này
    (2 đoạn nửa mở không giao nhau khi `a.tra ≤ b.don` hoặc `b.tra ≤ a.don`, mục 6)."""
    return {v["so_ghe"] for v in doan_ve if v["hl_don"] < hl_tra and hl_don < v["hl_tra"]}


# ---------------------------------------------------------
# Nghiệp vụ
# ---------------------------------------------------------
def danh_sach_khu_vuc() -> list[dict]:
    return repo.danh_sach_khu_vuc_co_tuyen()


def _kiem_tra_cap_khu_vuc(khu_vuc_di_id: str, khu_vuc_den_id: str) -> None:
    if str(khu_vuc_di_id) == str(khu_vuc_den_id):
        raise GiaTriLoi("Điểm đi và điểm đến phải khác nhau")
    if not repo.tim_khu_vuc_theo_id(khu_vuc_di_id):
        raise GiaTriLoi("Điểm đi không tồn tại")
    if not repo.tim_khu_vuc_theo_id(khu_vuc_den_id):
        raise GiaTriLoi("Điểm đến không tồn tại")


def _dung_the_chuyen(r: dict, gia: int, so_ghe_trong: int) -> dict:
    return {
        "id": r["id"],
        "ma": r["ma"],
        "chieu": r["chieu"],
        "gio_khoi_hanh": r["gio_khoi_hanh"],
        "gio_don_du_kien": gio_tai_diem(r["gio_khoi_hanh"], r["phut_don"]),
        "gio_den_du_kien": gio_tai_diem(r["gio_khoi_hanh"], r["phut_tra"]),
        "diem_don_id": r["diem_don_id"],
        "ten_diem_don": r["ten_diem_don"],
        "diem_tra_id": r["diem_tra_id"],
        "ten_diem_tra": r["ten_diem_tra"],
        "ma_loai_xe": r["ma_loai_xe"],
        "ten_loai_xe": r["ten_loai_xe"],
        "gia": gia,
        "so_ghe_trong": so_ghe_trong,
        "tong_ghe": r["tong_ghe"],
        "bien_so": r["bien_so"],
        "dang_hoan": r["dang_hoan"],
    }


def _lap_the_chuyen(ket_qua: list[dict], khu_vuc_di_id: str, khu_vuc_den_id: str) -> list[tuple[dict, dict, set[str]]]:
    """Với mỗi chuyến tìm được: tính giá + ghế đang bị giữ. Chuyến chưa có giá bị bỏ (không bán được)."""
    if not ket_qua:
        return []
    chuyen_ids = [str(r["id"]) for r in ket_qua]
    tuyen_ids = list({str(r["tuyen_id"]) for r in ket_qua})
    dong_gia = repo.danh_sach_gia_ve(tuyen_ids, khu_vuc_di_id, khu_vuc_den_id)
    doan_theo_chuyen: dict[str, list[dict]] = {}
    for v in repo.tim_doan_ve_dang_giu(chuyen_ids):
        doan_theo_chuyen.setdefault(str(v["chuyen_id"]), []).append(v)

    ket_qua_the = []
    for r in ket_qua:
        ngay_di = r["gio_khoi_hanh"].astimezone(MUI_GIO_VN).date()
        gia_cua_tuyen = [g for g in dong_gia if str(g["tuyen_id"]) == str(r["tuyen_id"])]
        gia = chon_gia(gia_cua_tuyen, r["chieu"], str(khu_vuc_di_id), str(khu_vuc_den_id), ngay_di, r["he_so_gia"])
        if gia is None:
            continue
        ghe_bi_giu = tinh_ghe_dang_giu(doan_theo_chuyen.get(str(r["id"]), []), r["hl_don"], r["hl_tra"])
        ket_qua_the.append((r, {"gia": gia}, ghe_bi_giu))
    return ket_qua_the


def tim_chuyen(khu_vuc_di_id: str, khu_vuc_den_id: str, ngay: datetime.date) -> list[dict]:
    """UC-04 bước 1-3: danh sách chuyến đi từ khu vực đi tới khu vực đến vào ngày đã chọn."""
    _kiem_tra_cap_khu_vuc(khu_vuc_di_id, khu_vuc_den_id)
    if ngay < datetime.datetime.now(MUI_GIO_VN).date():
        raise GiaTriLoi("Không thể tìm chuyến ở ngày đã qua")

    tu = datetime.datetime.combine(ngay, datetime.time.min, tzinfo=MUI_GIO_VN)
    ket_qua = repo.tim_chuyen(str(khu_vuc_di_id), str(khu_vuc_den_id), tu, tu + datetime.timedelta(days=1))
    the = []
    for r, gia_info, ghe_bi_giu in _lap_the_chuyen(ket_qua, str(khu_vuc_di_id), str(khu_vuc_den_id)):
        the.append(_dung_the_chuyen(r, gia_info["gia"], max(r["tong_ghe"] - len(ghe_bi_giu), 0)))
    return the


def lay_chuyen_mo_ban(chuyen_id: str, khu_vuc_di_id: str, khu_vuc_den_id: str) -> tuple[dict, dict, set[str]]:
    """1 chuyến còn mở bán cho đúng cặp khu vực: (dòng chuyến, {"gia"}, các ghế đang bị giữ trên đoạn rộng nhất).
    Dùng chung cho xem sơ đồ ghế (UC-04) và giữ chỗ/đặt vé (UC-05) để 2 nơi luôn thấy cùng một sự thật."""
    _kiem_tra_cap_khu_vuc(khu_vuc_di_id, khu_vuc_den_id)
    ket_qua = repo.tim_chuyen(str(khu_vuc_di_id), str(khu_vuc_den_id), chuyen_id=str(chuyen_id))
    cac_the = _lap_the_chuyen(ket_qua, str(khu_vuc_di_id), str(khu_vuc_den_id))
    if not cac_the:
        raise GiaTriLoi("Chuyến không còn mở bán hoặc không đi qua cặp điểm này")
    return cac_the[0]


def so_do_ghe_chuyen(chuyen_id: str, khu_vuc_di_id: str, khu_vuc_den_id: str) -> dict:
    """UC-04 bước 4: sơ đồ ghế của 1 chuyến theo đoạn rộng nhất khách có thể đi (mục 3.4 bước 3)."""
    r, gia_info, ghe_bi_giu = lay_chuyen_mo_ban(chuyen_id, khu_vuc_di_id, khu_vuc_den_id)
    so_do_ghe = [
        {**g, "trang_thai": "da_co_nguoi" if g["ma_ghe"] in ghe_bi_giu else "trong"}
        for g in r["so_do_ghe"]
    ]
    chi_tiet = _dung_the_chuyen(r, gia_info["gia"], sum(1 for g in so_do_ghe if g["trang_thai"] == "trong"))

    def _diem(d: dict) -> dict:
        return {"diem_id": d["diem_id"], "ten": d["ten"], "loai": d["loai"], "gio_du_kien": gio_tai_diem(r["gio_khoi_hanh"], d["phut"])}

    diem_don = [_diem(d) for d in repo.danh_sach_diem_cua_chuyen(str(chuyen_id), str(khu_vuc_di_id)) if d["loai"] == "van_phong" and d["hl"] < r["hl_tra"]]
    diem_tra = [_diem(d) for d in repo.danh_sach_diem_cua_chuyen(str(chuyen_id), str(khu_vuc_den_id)) if d["hl"] > r["hl_don"]]
    chi_tiet.update(
        so_tang=2 if any(g["tang"] == 2 for g in so_do_ghe) else 1,
        so_do_ghe=so_do_ghe,
        diem_don_co_the_chon=diem_don,
        diem_tra_co_the_chon=diem_tra,
    )
    return chi_tiet
