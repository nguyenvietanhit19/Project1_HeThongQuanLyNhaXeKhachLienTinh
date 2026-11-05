"""Điều độ viên gán xe theo CHU TRÌNH (chuyến đi + chuyến về cùng `chu_trinh_id`) — UC-44, DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md.

Phạm vi: chu trình thuộc điều độ viên được `quan_ly` phân công phụ trách TUYẾN đó (bảng dieu_do_vien_tuyen); quản lý thay được mọi tuyến.
Gán xe cho chu trình thì cả hai chuyến nhận cùng xe trong 1 giao dịch. Cửa sổ làm việc mặc định 3 ngày tới.
Kiểm tra mọi quy tắc (loại xe, trạng thái xe, tuyến cố định, trùng lịch, đúng vị trí, chuyến kế tiếp) nằm ở `danh_gia_xe` —
dùng chung cho danh sách xe gợi ý (hiện mọi lý do) và lúc gán thật (chặn nếu còn lý do nào).
"""

import datetime
from zoneinfo import ZoneInfo

from app.middleware.auth_middleware import NguoiDungHienTai
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import dieu_do_repository as repo
from app.repositories import phan_cong_dieu_do_repository as phan_cong_repo
from app.repositories import xe_repository as xe_repo
from app.services.lich_chay_service import KHOANG_NGHI_TOI_THIEU_PHUT
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
CUA_SO_MAC_DINH_NGAY = 3  # tạm thời: điều độ viên làm việc với chu trình khởi hành trong 3 ngày tới
CUA_SO_TOI_DA_NGAY = 7


def _bay_gio() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _gio_vn(thoi_diem: datetime.datetime) -> str:
    return thoi_diem.astimezone(MUI_GIO_VN).strftime("%H:%M %d/%m")


def _pham_vi_tuyen(nguoi_dung: NguoiDungHienTai) -> list[str] | None:
    """None = mọi tuyến (quản lý thay điều độ viên); điều độ viên = các tuyến được phân công (có thể rỗng: chưa được phân công thì
    không thấy chu trình nào, giao diện nhắc liên hệ quản lý)."""
    if nguoi_dung.vai_tro == "quan_ly":
        return None
    return [str(t["id"]) for t in phan_cong_repo.danh_sach_tuyen_cua_dieu_do_vien(nguoi_dung.id)]


def _kiem_tra_thuoc_pham_vi(chuyen: list[dict], tuyen_ids: list[str] | None) -> None:
    if tuyen_ids is not None and str(chuyen[0]["tuyen_id"]) not in tuyen_ids:
        raise CamTruyCap(f"Chu trình này thuộc tuyến {chuyen[0]['ten_tuyen']}, bạn chưa được phân công phụ trách tuyến này")


def danh_sach_tuyen_phu_trach(nguoi_dung: NguoiDungHienTai) -> list[dict]:
    """Tuyến người gọi làm việc được (id, ma, ten): điều độ viên = tuyến được phân công; quản lý = mọi tuyến."""
    if nguoi_dung.vai_tro == "quan_ly":
        return [{"id": t["id"], "ma": t["ma"], "ten": t["ten"]} for t in dia_diem_repo.danh_sach_tuyen()]
    return phan_cong_repo.danh_sach_tuyen_cua_dieu_do_vien(nguoi_dung.id)


def _dung_chu_trinh(chuyen: list[dict]) -> dict:
    """Gom các chuyến của 1 chu trình (đã sắp theo giờ) thành dòng hiển thị."""
    dau = chuyen[0]
    so_co_xe = sum(1 for c in chuyen if c["xe_id"])
    return {
        "chu_trinh_id": dau["chu_trinh_id"],
        "tuyen_id": dau["tuyen_id"],
        "ma_tuyen": dau["ma_tuyen"],
        "ten_tuyen": dau["ten_tuyen"],
        "loai_xe_id": dau["loai_xe_id"],
        "ten_loai_xe": dau["ten_loai_xe"],
        "trang_thai_gan": "da_gan" if so_co_xe == len(chuyen) else ("mot_phan" if so_co_xe else "chua_gan"),
        "cac_chuyen": chuyen,
    }


def danh_sach_chu_trinh(nguoi_dung: NguoiDungHienTai, so_ngay: int = CUA_SO_MAC_DINH_NGAY) -> list[dict]:
    """Chu trình có chuyến đầu khởi hành trong `so_ngay` ngày tới (kể từ bây giờ) thuộc phạm vi người gọi, theo giờ khởi hành."""
    if not 1 <= so_ngay <= CUA_SO_TOI_DA_NGAY:
        raise GiaTriLoi(f"Cửa sổ làm việc phải từ 1 đến {CUA_SO_TOI_DA_NGAY} ngày")
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)
    bay_gio = _bay_gio()
    theo_chu_trinh: dict = {}
    for c in repo.danh_sach_chuyen_trong_cua_so(bay_gio, bay_gio + datetime.timedelta(days=so_ngay), tuyen_ids):
        theo_chu_trinh.setdefault(str(c["chu_trinh_id"]), []).append(c)
    return [_dung_chu_trinh(cac_chuyen) for cac_chuyen in theo_chu_trinh.values()]


def _khung_chu_trinh(chuyen_xet: list[dict]) -> tuple:
    """(tu_khung, den_khung, moc_truoc): cả chu trình chiếm xe từ chuyến đầu khởi hành đến chuyến cuối kết thúc, cộng khoảng
    nghỉ tối thiểu ở hai đầu; moc_truoc là giờ chuyến đầu khởi hành (xe phải đang ở điểm xuất phát từ lúc này)."""
    nghi = datetime.timedelta(minutes=KHOANG_NGHI_TOI_THIEU_PHUT)
    dau = chuyen_xet[0]["gio_khoi_hanh"]
    cuoi = max(c["gio_ket_thuc"] for c in chuyen_xet)
    return dau - nghi, cuoi + nghi, dau


def danh_gia_xe_chi_tiet(chuyen_xet: list[dict], xe: dict, lich: dict) -> list[dict]:
    """Mọi lý do xe này KHÔNG gán được cho chu trình, mỗi lý do kèm mã (`ma`) để giao diện gom nhóm/tô màu:
    khong_hoat_dong, khac_loai, tuyen_co_dinh, trung_lich, sai_vi_tri, hong_chuyen_ke_tiep. Rỗng = gán được.
    `chuyen_xet`: các chuyến cần gán, theo giờ; `lich`: kết quả repo._lich_xe của xe. Hàm thuần, không đụng DB."""
    ket_qua: list[dict] = []

    def them(ma: str, noi_dung: str) -> None:
        ket_qua.append({"ma": ma, "noi_dung": noi_dung})

    dau, cuoi = chuyen_xet[0], chuyen_xet[-1]
    if xe["trang_thai"] != "hoat_dong":
        them("khong_hoat_dong", "Xe không ở trạng thái hoạt động")
    if str(xe["loai_xe_id"]) != str(dau["loai_xe_id"]):
        them("khac_loai", f"Khác loại xe (chuyến cam kết {dau['ten_loai_xe']})")
    if xe["tuyen_id"] and str(xe["tuyen_id"]) != str(dau["tuyen_id"]):
        them("tuyen_co_dinh", f"Xe chỉ chạy cố định một tuyến khác, không chạy tuyến {dau['ten_tuyen']}")

    for c in lich["trong_khoang"]:
        them(
            "trung_lich",
            f"Trùng lịch với chuyến {c['ma']} ({_gio_vn(c['gio_khoi_hanh'])} – {_gio_vn(c['gio_ket_thuc'])}); "
            f"hai chuyến liên tiếp cần cách nhau tối thiểu {KHOANG_NGHI_TOI_THIEU_PHUT} phút",
        )

    vi_tri = vi_tri_xe(dau, xe, lich)
    if not vi_tri["dung_diem_xuat_phat"]:
        nguon = f"sau chuyến {vi_tri['chuyen_ma']}" if vi_tri["nguon"] == "sau_chuyen" else "điểm gốc của xe"
        them(
            "sai_vi_tri",
            f"Lúc {_gio_vn(dau['gio_khoi_hanh'])} xe sẽ ở {vi_tri['ten_diem']} ({nguon}), không phải {dau['ten_diem_di']} "
            f"nơi chuyến {dau['ma']} xuất phát",
        )

    if lich["sau"] and str(lich["sau"]["diem_di_id"]) != str(cuoi["diem_den_id"]):
        them(
            "hong_chuyen_ke_tiep",
            f"Sau chu trình này xe sẽ ở {cuoi['ten_diem_den']}, nhưng chuyến {lich['sau']['ma']} của xe lúc "
            f"{_gio_vn(lich['sau']['gio_khoi_hanh'])} lại xuất phát từ {lich['sau']['ten_diem_di']}",
        )
    return ket_qua


def danh_gia_xe(chuyen_xet: list[dict], xe: dict, lich: dict) -> list[str]:
    """Như danh_gia_xe_chi_tiet nhưng chỉ trả các câu lý do (rỗng = gán được)."""
    return [ly_do["noi_dung"] for ly_do in danh_gia_xe_chi_tiet(chuyen_xet, xe, lich)]


def vi_tri_xe(chuyen_dau: dict, xe: dict, lich: dict) -> dict:
    """Vị trí DỰ KIẾN của xe lúc chuyến đầu của chu trình khởi hành, suy ra từ lịch (không phải GPS): điểm đến của chuyến gần nhất
    đã gán cho xe và kết thúc trước giờ đó, chưa có thì điểm gốc của xe (NGHIEP_VU.md mục 3.3). `dung_diem_xuat_phat` = trùng điểm
    xuất phát của chuyến đầu."""
    if lich["truoc"]:
        truoc = lich["truoc"]
        diem_id, ten_diem = truoc["diem_den_id"], truoc["ten_diem_den"]
        nguon, chuyen_ma, tu_luc = "sau_chuyen", truoc["ma"], truoc["gio_ket_thuc"]
    else:
        diem_id, ten_diem = xe["diem_goc_id"], xe["ten_diem_goc"]
        nguon, chuyen_ma, tu_luc = "diem_goc", None, None
    return {
        "diem_id": diem_id,
        "ten_diem": ten_diem,
        "nguon": nguon,
        "chuyen_ma": chuyen_ma,
        "tu_luc": tu_luc,
        "dung_diem_xuat_phat": str(diem_id) == str(chuyen_dau["diem_di_id"]),
    }


def _chuyen_can_gan(chuyen: list[dict]) -> list[dict]:
    """Các chuyến còn gán được của chu trình (chưa khởi hành); báo lỗi nếu không còn chuyến nào."""
    chuyen_xet = [c for c in chuyen if c["trang_thai"] == "chua_khoi_hanh"]
    if not chuyen_xet:
        raise GiaTriLoi("Chu trình này đã khởi hành hoặc đã hủy hết, không gán xe được nữa")
    return chuyen_xet


def _tom_tat_loai_xe(id_, ma: str, ten: str, so_ghe: int, so_tang: int) -> dict:
    return {"id": id_, "ma": ma, "ten": ten, "so_ghe": so_ghe, "so_tang": so_tang}


def danh_sach_xe_cho_chu_trinh(nguoi_dung: NguoiDungHienTai, chu_trinh_id: str) -> list[dict]:
    """MỌI xe còn dùng (kể cả xe không phù hợp) kèm loại xe, vị trí dự kiến lúc khởi hành, chuyến kế tiếp, chuyến đang chiếm lịch và mọi
    lý do nếu không gán được (`ma_ly_do` song song `ly_do`). Xe gán được xếp trước, rồi xe ít lý do nhất."""
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)
    chuyen = repo.lay_chu_trinh(chu_trinh_id)
    if not chuyen:
        raise KhongTimThay("Không tìm thấy chu trình")
    _kiem_tra_thuoc_pham_vi(chuyen, tuyen_ids)
    chuyen_xet = _chuyen_can_gan(chuyen)
    dau = chuyen_xet[0]

    tu_khung, den_khung, moc_truoc = _khung_chu_trinh(chuyen_xet)
    ds_xe = repo.danh_sach_xe_de_chon()
    lich_theo_xe = repo.lich_cac_xe([x["id"] for x in ds_xe], tu_khung, den_khung, moc_truoc, [str(c["id"]) for c in chuyen])
    xe_hien_tai = {str(c["xe_id"]) for c in chuyen_xet if c["xe_id"]}
    ket_qua = []
    for xe in ds_xe:
        lich = lich_theo_xe[str(xe["id"])]
        ly_do = danh_gia_xe_chi_tiet(chuyen_xet, xe, lich)
        sau = lich["sau"]
        ket_qua.append({
            "xe_id": xe["id"],
            "bien_so": xe["bien_so"],
            "hop_le": not ly_do,
            "ly_do": [l["noi_dung"] for l in ly_do],
            "ma_ly_do": [l["ma"] for l in ly_do],
            "dang_gan": str(xe["id"]) in xe_hien_tai,
            "trang_thai_xe": xe["trang_thai"],
            "loai_xe": _tom_tat_loai_xe(xe["loai_xe_id"], xe["ma_loai_xe"], xe["ten_loai_xe"], xe["so_ghe"], xe["so_tang"]),
            "dung_loai": str(xe["loai_xe_id"]) == str(dau["loai_xe_id"]),
            "tuyen_co_dinh": {"ma": xe["ma_tuyen_co_dinh"], "ten": xe["ten_tuyen_co_dinh"]} if xe["tuyen_id"] else None,
            "vi_tri": vi_tri_xe(dau, xe, lich),
            "chuyen_ke_tiep": (
                {"ma": sau["ma"], "gio_khoi_hanh": sau["gio_khoi_hanh"], "ten_diem_di": sau["ten_diem_di"], "ten_diem_den": sau["ten_diem_den"]}
                if sau else None
            ),
            "chuyen_trung": [{"ma": c["ma"], "gio_khoi_hanh": c["gio_khoi_hanh"], "gio_ket_thuc": c["gio_ket_thuc"]} for c in lich["trong_khoang"]],
        })
    return sorted(ket_qua, key=lambda x: (not x["hop_le"], len(x["ly_do"]), x["bien_so"]))


def _so_do_va_tang(loai: dict) -> tuple[list[dict], int]:
    so_do = loai.get("so_do_ghe") or []
    return so_do, max((g["tang"] for g in so_do), default=1)


def chi_tiet_chu_trinh(nguoi_dung: NguoiDungHienTai, chu_trinh_id: str) -> dict:
    """Lộ trình của từng chuyến trong chu trình kèm giờ đến dự kiến ở từng điểm (chuyến về đi ngược các điểm, thời gian giữa 2 điểm
    liền kề giữ nguyên — đối xứng 2 chiều, NGHIEP_VU.md mục 3.1) và loại xe cam kết."""
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)
    chuyen = repo.lay_chu_trinh(chu_trinh_id)
    if not chuyen:
        raise KhongTimThay("Không tìm thấy chu trình")
    _kiem_tra_thuoc_pham_vi(chuyen, tuyen_ids)
    dau = chuyen[0]
    diem = sorted(dia_diem_repo.danh_sach_diem_theo_tuyen(str(dau["tuyen_id"])), key=lambda d: d["thu_tu"])
    tong_phut = diem[-1]["thoi_gian_du_kien_phut"] if diem else 0

    cac_chuyen = []
    for c in chuyen:
        xuoi = c["chieu"] == "xuoi"
        thu_tu_diem = diem if xuoi else list(reversed(diem))
        cac_chuyen.append({
            "id": c["id"], "ma": c["ma"], "chieu": c["chieu"], "trang_thai": c["trang_thai"],
            "gio_khoi_hanh": c["gio_khoi_hanh"], "gio_ket_thuc": c["gio_ket_thuc"],
            "diem": [
                {
                    "diem_don_tra_id": d["diem_don_tra_id"], "ten": d["ten"], "ten_khu_vuc": d["ten_khu_vuc"], "loai": d["loai"],
                    "gio_den": c["gio_khoi_hanh"] + datetime.timedelta(minutes=d["thoi_gian_du_kien_phut"] if xuoi else tong_phut - d["thoi_gian_du_kien_phut"]),
                }
                for d in thu_tu_diem
            ],
        })

    loai = xe_repo.tim_loai_xe_theo_id(str(dau["loai_xe_id"])) or {}
    so_do, so_tang = _so_do_va_tang(loai)
    return {
        "chu_trinh_id": dau["chu_trinh_id"],
        "tuyen": {"id": dau["tuyen_id"], "ma": dau["ma_tuyen"], "ten": dau["ten_tuyen"]},
        "loai_xe_cam_ket": _tom_tat_loai_xe(dau["loai_xe_id"], loai.get("ma", ""), dau["ten_loai_xe"], len(so_do), so_tang),
        "cac_chuyen": cac_chuyen,
    }


def chi_tiet_loai_xe(loai_xe_id: str) -> dict:
    """Sơ đồ ghế của một loại xe — giao diện nạp khi điều độ viên bấm "Xem sơ đồ ghế" (mỗi loại chỉ nạp một lần)."""
    loai = xe_repo.tim_loai_xe_theo_id(loai_xe_id)
    if not loai:
        raise KhongTimThay("Không tìm thấy loại xe")
    so_do, so_tang = _so_do_va_tang(loai)
    return {**_tom_tat_loai_xe(loai["id"], loai["ma"], loai["ten"], len(so_do), so_tang), "so_do_ghe": so_do}


def gan_xe(nguoi_dung: NguoiDungHienTai, chu_trinh_id: str, xe_id: str) -> dict:
    """Gán (hoặc đổi) xe cho cả chu trình. Mọi chuyến chưa khởi hành của chu trình nhận cùng xe; vi phạm quy tắc nào thì
    không chuyến nào được gán."""
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)

    def kiem_tra(chuyen: list[dict], xe: dict | None, lich_xe) -> None:
        if not chuyen:
            raise KhongTimThay("Không tìm thấy chu trình")
        _kiem_tra_thuoc_pham_vi(chuyen, tuyen_ids)
        chuyen_xet = _chuyen_can_gan(chuyen)
        if xe is None:
            raise KhongTimThay("Không tìm thấy xe")
        bay_gio = _bay_gio()
        for c in chuyen_xet:
            if c["gio_khoi_hanh"] <= bay_gio:
                raise GiaTriLoi(f"Chuyến {c['ma']} đã quá giờ khởi hành, không gán xe được nữa")
            if c["xe_thuc_te_id"]:
                raise GiaTriLoi(f"Chuyến {c['ma']} đang có xe chạy thay — xử lý ở mục đổi xe khi hỏng, không đổi xe gốc ở đây")
        tu_khung, den_khung, moc_truoc = _khung_chu_trinh(chuyen_xet)
        lich = lich_xe(tu_khung, den_khung, moc_truoc, [str(c["id"]) for c in chuyen])
        ly_do = danh_gia_xe(chuyen_xet, xe, lich)
        if ly_do:
            raise GiaTriLoi(f"Không gán được xe {xe['bien_so']}: " + "; ".join(ly_do))

    chuyen = repo.gan_xe_cho_chu_trinh(chu_trinh_id, xe_id, kiem_tra)
    return _dung_chu_trinh(chuyen)
