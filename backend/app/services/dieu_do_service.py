"""Điều độ viên gán xe theo CHU TRÌNH (chuyến đi + chuyến về cùng `chu_trinh_id`) — UC-44, DIEU_DO_VIEN_THEO_TUYEN_DE_XUAT.md.

Phạm vi: chu trình thuộc điều độ viên được `quan_ly` phân công phụ trách TUYẾN đó (bảng dieu_do_vien_tuyen); quản lý thay được mọi tuyến.
Gán xe cho chu trình thì cả hai chuyến nhận cùng xe trong 1 giao dịch. Cửa sổ làm việc mặc định 3 ngày tới.
Kiểm tra mọi quy tắc (loại xe, trạng thái xe, tuyến cố định, trùng lịch, đúng vị trí, chuyến kế tiếp) nằm ở `danh_gia_xe` —
dùng chung cho danh sách xe gợi ý (hiện mọi lý do) và lúc gán thật (chặn nếu còn lý do nào).
"""

import datetime
import logging
from zoneinfo import ZoneInfo

from app.middleware.auth_middleware import NguoiDungHienTai
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import dieu_do_repository as repo
from app.repositories import nguoi_dung_repository as nguoi_dung_repo
from app.repositories import nhan_su_van_hanh_repository as nhan_su_repo
from app.repositories import phan_cong_dieu_do_repository as phan_cong_repo
from app.repositories import ve_repository as ve_repo
from app.repositories import xe_repository as xe_repo
from app.services import thong_bao_khach_service as thong_bao
from app.services.lich_chay_service import KHOANG_NGHI_TOI_THIEU_PHUT
from app.utils import bien_che
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay

logger = logging.getLogger(__name__)
MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
DUONG_DAN_GAN_XE = "/nhan-vien/dieu-do/gan-xe.html"
NGUONG_NHAC_CHUA_GAN_XE_GIO = 48  # NGHIEP_VU.md mục 3.5: chuyến còn ≤48 tiếng mà chưa gán xe thì nhắc
NGUONG_KHAN_CHUA_GAN_XE_GIO = 6  # còn ≤6 tiếng: mức khẩn (nhắc thêm một lần nữa, hiện đỏ)
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


def con_lai_dang_chu(khoang: datetime.timedelta) -> str:
    """Thời gian còn lại dạng dễ đọc: từ 1 ngày trở lên tính theo ngày ("1 ngày 13 giờ", "2 ngày"), dưới 1 ngày theo giờ phút
    ("17 giờ 21 phút", "6 giờ", "45 phút") — không để số giờ lớn như "37 giờ"."""
    phut = max(int(khoang.total_seconds() // 60), 0)
    gio, le = divmod(phut, 60)
    ngay, gio = divmod(gio, 24)
    if ngay:
        return f"{ngay} ngày" + (f" {gio} giờ" if gio else "")
    if gio:
        return f"{gio} giờ" + (f" {le:02d} phút" if le else "")
    return f"{le} phút"


def duong_dan_chu_trinh(chu_trinh_id) -> str:
    """Đường dẫn của thông báo: mở trang Gán xe và nhảy tới đúng thẻ chu trình (không có chu trình thì chỉ mở trang)."""
    return f"{DUONG_DAN_GAN_XE}?chu_trinh={chu_trinh_id}" if chu_trinh_id else DUONG_DAN_GAN_XE


def can_chu_y_chu_trinh(chuyen: list[dict], bay_gio: datetime.datetime, nhan_su_xe: dict[str, tuple[int, int]] | None = None) -> list[dict]:
    """Những việc điều độ viên cần xử lý ở 1 chu trình (`chuyen` đã sắp theo giờ), mỗi việc {ma, muc_do, noi_dung, ma_chuyen, gio_khoi_hanh}
    (chuyến liên quan và giờ khởi hành của nó — giao diện tự tính "còn bao lâu"), nặng nhất trước.
    `nhan_su_xe`: {xe_id: (số tài xế, số phụ xe) đang hoạt động}; có thì thêm việc "xe thiếu nhân sự" cho xe đang chạy chuyến (xe thay nếu có).
    Chỉ xét chuyến còn `chua_khoi_hanh`. Mức độ: khan (làm ngay) > canh_bao > thong_tin. Hàm thuần, không đụng DB."""
    ket_qua: list[dict] = []
    da_co: set[str] = set()

    for c in chuyen:
        if c["trang_thai"] != "chua_khoi_hanh":
            continue

        def them(ma: str, muc_do: str, noi_dung: str, c=c) -> None:
            if ma not in da_co:  # mỗi loại việc chỉ nêu 1 lần cho cả chu trình (chuyến sớm nhất gặp trước)
                da_co.add(ma)
                ket_qua.append({"ma": ma, "muc_do": muc_do, "noi_dung": noi_dung, "ma_chuyen": c["ma"], "gio_khoi_hanh": c["gio_khoi_hanh"]})

        if not c["xe_id"]:
            if c["dang_hoan"]:
                them("dang_hoan", "khan", f"Chuyến {c['ma']} đang hoãn: đã quá giờ khởi hành mà chưa có xe — gán xe ngay")
            else:
                con = c["gio_khoi_hanh"] - bay_gio
                if con <= datetime.timedelta(hours=NGUONG_NHAC_CHUA_GAN_XE_GIO):
                    khan = con <= datetime.timedelta(hours=NGUONG_KHAN_CHUA_GAN_XE_GIO)
                    them("chua_gan_sap_toi", "khan" if khan else "canh_bao", f"Chưa gán xe cho chuyến {c['ma']}")
            continue
        if c["xe_thuc_te_id"]:
            if c["trang_thai_xe_thuc_te"] != "hoat_dong":
                them("xe_hong", "khan", f"Xe chạy thay {c['bien_so_xe_thuc_te']} không còn hoạt động — cần thay xe khác")
            elif c["trang_thai_xe"] == "hoat_dong":
                them("xe_goc_san_sang", "thong_tin", f"Xe gốc {c['bien_so_xe']} đã hoạt động lại — có thể trả chu trình về xe gốc")
        elif c["trang_thai_xe"] != "hoat_dong":
            them("xe_hong", "khan", f"Xe {c['bien_so_xe']} đang không hoạt động (bảo trì) — cần thay xe cho chu trình")
        if nhan_su_xe is not None:
            xe_chay = str(c["xe_thuc_te_id"] or c["xe_id"])
            tai_xe, phu_xe = nhan_su_xe.get(xe_chay, (0, 0))
            if not bien_che.du_nhan_su(tai_xe, phu_xe):
                bien_so = c["bien_so_xe_thuc_te"] if c["xe_thuc_te_id"] else c["bien_so_xe"]
                them("xe_thieu_nhan_su", "canh_bao", f"Xe {bien_so} đang {bien_che.mo_ta_thieu(tai_xe, phu_xe)} — báo quản lý bổ sung biên chế hoặc đổi xe")
        if c["co_canh_bao_xung_dot_vi_tri"]:
            them("canh_bao_vi_tri", "canh_bao", f"Chuyến trước của xe gặp sự cố, xe có thể không kịp tới điểm xuất phát của chuyến {c['ma']} — kiểm tra lại")
    thu_tu = {"khan": 0, "canh_bao": 1, "thong_tin": 2}
    return sorted(ket_qua, key=lambda v: thu_tu[v["muc_do"]])


def _dung_chu_trinh(chuyen: list[dict], bay_gio: datetime.datetime | None = None, nhan_su_xe: dict[str, tuple[int, int]] | None = None) -> dict:
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
        "can_chu_y": can_chu_y_chu_trinh(chuyen, bay_gio or _bay_gio(), nhan_su_xe),
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
    xe_ids = {str(c["xe_thuc_te_id"] or c["xe_id"]) for ds in theo_chu_trinh.values() for c in ds if c["xe_thuc_te_id"] or c["xe_id"]}
    nhan_su_xe = nhan_su_repo.dem_hieu_luc_theo_xe(sorted(xe_ids))
    return [_dung_chu_trinh(cac_chuyen, bay_gio, nhan_su_xe) for cac_chuyen in theo_chu_trinh.values()]


def _khung_chu_trinh(chuyen_xet: list[dict]) -> tuple:
    """(tu_khung, den_khung, moc_truoc): cả chu trình chiếm xe từ chuyến đầu khởi hành đến chuyến cuối kết thúc, cộng khoảng
    nghỉ tối thiểu ở hai đầu; moc_truoc là giờ chuyến đầu khởi hành (xe phải đang ở điểm xuất phát từ lúc này)."""
    nghi = datetime.timedelta(minutes=KHOANG_NGHI_TOI_THIEU_PHUT)
    dau = chuyen_xet[0]["gio_khoi_hanh"]
    cuoi = max(c["gio_ket_thuc"] for c in chuyen_xet)
    return dau - nghi, cuoi + nghi, dau


def danh_gia_xe_chi_tiet(chuyen_xet: list[dict], xe: dict, lich: dict) -> list[dict]:
    """Mọi lý do xe này KHÔNG gán được cho chu trình, mỗi lý do kèm mã (`ma`) để giao diện gom nhóm/tô màu:
    khong_hoat_dong, thieu_nhan_su, khac_loai, tuyen_co_dinh, trung_lich, sai_vi_tri, hong_chuyen_ke_tiep. Rỗng = gán được.
    Xe chưa đủ nhân sự (2 tài xế + ≥1 phụ xe đang hoạt động, app/utils/bien_che.py) KHÔNG gán được chuyến — kể cả xe dự phòng.
    `chuyen_xet`: các chuyến cần gán, theo giờ; `lich`: kết quả repo._lich_xe của xe. Hàm thuần, không đụng DB."""
    ket_qua: list[dict] = []

    def them(ma: str, noi_dung: str) -> None:
        ket_qua.append({"ma": ma, "noi_dung": noi_dung})

    dau, cuoi = chuyen_xet[0], chuyen_xet[-1]
    if xe["trang_thai"] != "hoat_dong":
        them("khong_hoat_dong", "Xe không ở trạng thái hoạt động")
    if not bien_che.du_nhan_su(xe["so_tai_xe_hieu_luc"], xe["so_phu_xe_hieu_luc"]):
        them(
            "thieu_nhan_su",
            f"Xe chưa đủ nhân sự ({bien_che.mo_ta_thieu(xe['so_tai_xe_hieu_luc'], xe['so_phu_xe_hieu_luc'])}) — nhờ quản lý bổ sung biên chế",
        )
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


def _chuyen_can_thay_xe(chuyen: list[dict]) -> list[dict]:
    """Các chuyến của chu trình mà xe chạy thay (UC-20) áp dụng: còn chưa khởi hành VÀ đã có xe gốc. Báo lỗi nếu không có chuyến nào."""
    chuyen_xet = [c for c in chuyen if c["trang_thai"] == "chua_khoi_hanh" and c["xe_id"]]
    if not chuyen_xet:
        raise GiaTriLoi("Chu trình chưa có xe gốc hoặc đã khởi hành hết — không có chuyến nào để thay xe (chưa có xe thì dùng Gán xe)")
    return chuyen_xet


def danh_sach_xe_cho_chu_trinh(nguoi_dung: NguoiDungHienTai, chu_trinh_id: str, che_do: str = "gan") -> list[dict]:
    """MỌI xe còn dùng (kể cả xe không phù hợp) kèm loại xe, vị trí dự kiến lúc khởi hành, chuyến kế tiếp, chuyến đang chiếm lịch và mọi
    lý do nếu không gán được (`ma_ly_do` song song `ly_do`). Xe gán được xếp trước, rồi xe ít lý do nhất.
    `che_do` = "gan" (gán/đổi xe gốc) hoặc "thay" (chọn xe chạy thay khi xe gốc hỏng, UC-20: xe gốc không nằm trong danh sách, và
    `dang_gan` đánh dấu xe đang chạy thay)."""
    if che_do not in ("gan", "thay"):
        raise GiaTriLoi("Chế độ chọn xe không hợp lệ")
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)
    chuyen = repo.lay_chu_trinh(chu_trinh_id)
    if not chuyen:
        raise KhongTimThay("Không tìm thấy chu trình")
    _kiem_tra_thuoc_pham_vi(chuyen, tuyen_ids)
    chuyen_xet = _chuyen_can_gan(chuyen) if che_do == "gan" else _chuyen_can_thay_xe(chuyen)
    dau = chuyen_xet[0]

    tu_khung, den_khung, moc_truoc = _khung_chu_trinh(chuyen_xet)
    ds_xe = repo.danh_sach_xe_de_chon()
    if che_do == "thay":
        xe_goc = {str(c["xe_id"]) for c in chuyen_xet}
        ds_xe = [x for x in ds_xe if str(x["id"]) not in xe_goc]
        xe_hien_tai = {str(c["xe_thuc_te_id"]) for c in chuyen_xet if c["xe_thuc_te_id"]}
    else:
        xe_hien_tai = {str(c["xe_id"]) for c in chuyen_xet if c["xe_id"]}
    lich_theo_xe = repo.lich_cac_xe([x["id"] for x in ds_xe], tu_khung, den_khung, moc_truoc, [str(c["id"]) for c in chuyen])
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
            "nhan_su": {"tai_xe": xe["so_tai_xe_hieu_luc"], "phu_xe": xe["so_phu_xe_hieu_luc"], "du": bien_che.du_nhan_su(xe["so_tai_xe_hieu_luc"], xe["so_phu_xe_hieu_luc"])},
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
            if c["gio_khoi_hanh"] <= bay_gio and not c["dang_hoan"]:  # chuyến đang hoãn (quá giờ mà chưa có xe) vẫn gán được
                raise GiaTriLoi(f"Chuyến {c['ma']} đã quá giờ khởi hành, không gán xe được nữa")
            if c["xe_thuc_te_id"]:
                raise GiaTriLoi(f"Chuyến {c['ma']} đang có xe chạy thay — hãy trả về xe gốc trước rồi mới đổi xe gốc")
        tu_khung, den_khung, moc_truoc = _khung_chu_trinh(chuyen_xet)
        lich = lich_xe(tu_khung, den_khung, moc_truoc, [str(c["id"]) for c in chuyen])
        ly_do = danh_gia_xe(chuyen_xet, xe, lich)
        if ly_do:
            raise GiaTriLoi(f"Không gán được xe {xe['bien_so']}: " + "; ".join(ly_do))

    chuyen = repo.gan_xe_cho_chu_trinh(chu_trinh_id, xe_id, kiem_tra)
    return _dung_chu_trinh(chuyen)


# ---------------------------------------------------------
# UC-20: xe hỏng → xe khác chạy thay; sửa xong thì trả về xe gốc
# ---------------------------------------------------------
def _bao_khach_doi_xe(chuyen: list[dict], noi_dung_theo_chuyen) -> None:
    """Báo từng khách có vé còn hiệu lực trên các chuyến vừa đổi xe. Lỗi gửi không làm hỏng thao tác (đã ghi DB)."""
    for c in chuyen:
        try:
            for khach in ve_repo.tim_khach_hang_dang_hoat_dong_theo_chuyen(str(c["id"])):
                thong_bao.gui(khach["khach_hang_id"], noi_dung_theo_chuyen(c))
        except Exception:  # noqa: BLE001
            logger.exception("Không báo được khách về việc đổi xe chuyến %s", c["id"])


def thay_xe(nguoi_dung: NguoiDungHienTai, chu_trinh_id: str, xe_id: str, ly_do: str | None = None) -> dict:
    """UC-20: cho `xe_id` chạy thay các chuyến chưa khởi hành (đã có xe gốc) của chu trình. Xe gốc giữ nguyên để sau trả lại được.
    Vi phạm quy tắc nào (cùng `danh_gia_xe` như lúc gán) thì không chuyến nào được đổi. Khách có vé được báo biển số xe mới."""
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)
    ly_do = (ly_do or "").strip()[:200]

    def kiem_tra(chuyen: list[dict], xe: dict | None, lich_xe) -> None:
        if not chuyen:
            raise KhongTimThay("Không tìm thấy chu trình")
        _kiem_tra_thuoc_pham_vi(chuyen, tuyen_ids)
        chuyen_xet = _chuyen_can_thay_xe(chuyen)
        if xe is None:
            raise KhongTimThay("Không tìm thấy xe")
        if str(xe["id"]) in {str(c["xe_id"]) for c in chuyen_xet}:
            raise GiaTriLoi("Đây chính là xe gốc của chu trình — muốn dùng lại xe gốc thì chọn Trả về xe gốc")
        bay_gio = _bay_gio()
        for c in chuyen_xet:
            if c["gio_khoi_hanh"] <= bay_gio:
                raise GiaTriLoi(f"Chuyến {c['ma']} đã quá giờ khởi hành, không đổi xe được nữa")
        tu_khung, den_khung, moc_truoc = _khung_chu_trinh(chuyen_xet)
        lich = lich_xe(tu_khung, den_khung, moc_truoc, [str(c["id"]) for c in chuyen])
        vi_pham = danh_gia_xe(chuyen_xet, xe, lich)
        if vi_pham:
            raise GiaTriLoi(f"Không cho xe {xe['bien_so']} chạy thay được: " + "; ".join(vi_pham))

    chuyen = repo.thay_xe_cho_chu_trinh(chu_trinh_id, xe_id, kiem_tra)
    da_doi = [c for c in chuyen if c["trang_thai"] == "chua_khoi_hanh" and c["xe_thuc_te_id"]]
    bien_so_moi = da_doi[0]["bien_so_xe_thuc_te"] if da_doi else ""
    _bao_khach_doi_xe(
        da_doi,
        lambda c: f"Chuyến {c['ma']} ({_gio_vn(c['gio_khoi_hanh'])}) đổi sang xe biển số {bien_so_moi}" + (f". Lý do: {ly_do}" if ly_do else ""),
    )
    return _dung_chu_trinh(chuyen)


def tra_xe_goc(nguoi_dung: NguoiDungHienTai, chu_trinh_id: str) -> dict:
    """UC-20 (gán lại xe gốc): bỏ xe chạy thay, các chuyến chưa khởi hành của chu trình chạy lại bằng xe gốc — chỉ khi xe gốc đã hoạt động
    lại và phù hợp lịch/vị trí như khi gán mới."""
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)

    def kiem_tra(chuyen: list[dict], xe_goc: dict | None, lich_xe) -> None:
        if not chuyen:
            raise KhongTimThay("Không tìm thấy chu trình")
        _kiem_tra_thuoc_pham_vi(chuyen, tuyen_ids)
        chuyen_xet = [c for c in chuyen if c["trang_thai"] == "chua_khoi_hanh" and c["xe_thuc_te_id"]]
        if not chuyen_xet or xe_goc is None:
            raise GiaTriLoi("Chu trình này không có xe nào đang chạy thay")
        bay_gio = _bay_gio()
        for c in chuyen_xet:
            if c["gio_khoi_hanh"] <= bay_gio:
                raise GiaTriLoi(f"Chuyến {c['ma']} đã quá giờ khởi hành, không đổi xe được nữa")
        tu_khung, den_khung, moc_truoc = _khung_chu_trinh(chuyen_xet)
        lich = lich_xe(tu_khung, den_khung, moc_truoc, [str(c["id"]) for c in chuyen])
        vi_pham = danh_gia_xe(chuyen_xet, xe_goc, lich)
        if vi_pham:
            raise GiaTriLoi(f"Chưa trả về xe gốc {xe_goc['bien_so']} được: " + "; ".join(vi_pham))

    truoc = [c for c in repo.lay_chu_trinh(chu_trinh_id) if c["trang_thai"] == "chua_khoi_hanh" and c["xe_thuc_te_id"]]
    chuyen = repo.tra_xe_goc_cho_chu_trinh(chu_trinh_id, kiem_tra)
    bien_so_goc = truoc[0]["bien_so_xe"] if truoc else ""
    _bao_khach_doi_xe(
        [c for c in chuyen if c["id"] in {t["id"] for t in truoc}],
        lambda c: f"Chuyến {c['ma']} ({_gio_vn(c['gio_khoi_hanh'])}) chạy lại bằng xe biển số {bien_so_goc}",
    )
    return _dung_chu_trinh(chuyen)


# ---------------------------------------------------------
# Thống kê tổng quan
# ---------------------------------------------------------
SO_NGAY_QUA_THONG_KE = 7  # "chuyến gần đây" tính 7 ngày vừa qua


def _tinh_gan(ct: dict) -> str:
    """Một chu trình rơi vào đúng MỘT nhóm: dang_hoan (có chuyến đang hoãn) > da_gan > chua_gan (gồm gán một phần)."""
    if any(c["dang_hoan"] for c in ct["cac_chuyen"]):
        return "dang_hoan"
    return "da_gan" if ct["trang_thai_gan"] == "da_gan" else "chua_gan"


def _dem_nhom(cac_chu_trinh: list[dict]) -> dict:
    kq = {"so_chu_trinh": len(cac_chu_trinh), "da_gan": 0, "chua_gan": 0, "dang_hoan": 0}
    for ct in cac_chu_trinh:
        kq[_tinh_gan(ct)] += 1
    return kq


def thong_ke_tong_quan(nguoi_dung: NguoiDungHienTai, so_ngay: int = CUA_SO_MAC_DINH_NGAY) -> dict:
    """Tổng quan cho điều độ viên trong `so_ngay` ngày tới: tình trạng gán xe (tổng, theo tuyến, theo ngày), việc cần chú ý, đội xe và
    chuyến 7 ngày qua. Số liệu chu trình lấy từ đúng danh sách của trang Gán xe nên luôn khớp với trang đó; đội xe là toàn hệ thống
    (xe dùng chung), còn lại chỉ tính phạm vi tuyến của người gọi."""
    cac_chu_trinh = danh_sach_chu_trinh(nguoi_dung, so_ngay)
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)
    bay_gio = _bay_gio()
    den = bay_gio + datetime.timedelta(days=so_ngay)

    tong = _dem_nhom(cac_chu_trinh)
    tong.update({
        "so_chuyen": sum(len(ct["cac_chuyen"]) for ct in cac_chu_trinh),
        "dang_chay_thay": sum(1 for ct in cac_chu_trinh if any(c["xe_thuc_te_id"] for c in ct["cac_chuyen"])),
        "viec_khan": sum(1 for ct in cac_chu_trinh if any(v["muc_do"] == "khan" for v in ct["can_chu_y"])),
        "viec_can_chu_y": sum(len(ct["can_chu_y"]) for ct in cac_chu_trinh),
        "su_co_dang_xay_ra": len(repo.danh_sach_chuyen_gap_su_co(tuyen_ids)),
    })

    theo_tuyen = []
    for t in danh_sach_tuyen_phu_trach(nguoi_dung):  # tuyến chưa có chu trình nào vẫn hiện (số 0) để thấy đủ phạm vi phụ trách
        nhom = [ct for ct in cac_chu_trinh if str(ct["tuyen_id"]) == str(t["id"])]
        theo_tuyen.append({"tuyen_id": t["id"], "ma_tuyen": t["ma"], "ten_tuyen": t["ten"], **_dem_nhom(nhom)})
    theo_tuyen.sort(key=lambda x: (-(x["chua_gan"] + x["dang_hoan"]), x["ma_tuyen"]))

    theo_ngay_map: dict = {}
    for ct in cac_chu_trinh:
        p = ct["cac_chuyen"][0]["gio_khoi_hanh"].astimezone(MUI_GIO_VN).date()
        theo_ngay_map.setdefault(p, []).append(ct)
    theo_ngay = [{"ngay": ngay, **_dem_nhom(ds)} for ngay, ds in sorted(theo_ngay_map.items())]

    xe_thay = {str(c["xe_thuc_te_id"]) for ct in cac_chu_trinh for c in ct["cac_chuyen"] if c["xe_thuc_te_id"]}
    doi_xe = {**repo.thong_ke_doi_xe(bay_gio, den), "dang_chay_thay": len(xe_thay)}

    gan_day = repo.dem_chuyen_theo_trang_thai(bay_gio - datetime.timedelta(days=SO_NGAY_QUA_THONG_KE), bay_gio, tuyen_ids)
    chuyen_gan_day = {
        "so_ngay": SO_NGAY_QUA_THONG_KE,
        "hoan_thanh": gan_day.get("hoan_thanh", 0),
        "dang_chay": gan_day.get("dang_chay", 0),
        "gap_su_co": gan_day.get("gap_su_co", 0),
        "da_huy": gan_day.get("da_huy", 0),
    }
    return {"so_ngay": so_ngay, "tong": tong, "theo_tuyen": theo_tuyen, "theo_ngay": theo_ngay, "doi_xe": doi_xe, "chuyen_gan_day": chuyen_gan_day}


# ---------------------------------------------------------
# Sự cố đang xảy ra + người nhận thông báo của tuyến
# ---------------------------------------------------------
def danh_sach_su_co(nguoi_dung: NguoiDungHienTai) -> list[dict]:
    """Chuyến đang gặp sự cố (xe còn dọc đường, chưa xử lý xong) thuộc phạm vi người gọi — để hiện ở "Cần chú ý"."""
    tuyen_ids = _pham_vi_tuyen(nguoi_dung)
    return [
        {
            "chuyen_id": c["id"], "chu_trinh_id": c["chu_trinh_id"], "ma": c["ma"], "ma_tuyen": c["ma_tuyen"], "ten_tuyen": c["ten_tuyen"],
            "gio_khoi_hanh": c["gio_khoi_hanh"], "bien_so_xe": c["bien_so_xe_thuc_te"] or c["bien_so_xe"],
            "loai_su_co": c["loai_su_co"], "ly_do_su_co": c["ly_do_su_co"],
        }
        for c in repo.danh_sach_chuyen_gap_su_co(tuyen_ids)
    ]


def nguoi_nhan_thong_bao_cua_tuyen(tuyen_id: str) -> list[str]:
    """Điều độ viên phụ trách tuyến; tuyến chưa có ai thì mọi điều độ viên đang hoạt động; không có điều độ viên nào thì quản lý —
    để thông báo không bị bỏ sót (cùng quy tắc với báo sự cố, chuyen_xe_service._bao_dieu_do_vien_su_co)."""
    nguoi_nhan = phan_cong_repo.danh_sach_id_dieu_do_vien_cua_tuyen(tuyen_id)
    if not nguoi_nhan:
        nguoi_nhan = nguoi_dung_repo.danh_sach_id_theo_vai_tro("dieu_do_vien", chi_dang_hoat_dong=True)
    if not nguoi_nhan:
        nguoi_nhan = nguoi_dung_repo.danh_sach_id_theo_vai_tro("quan_ly", chi_dang_hoat_dong=True)
    return nguoi_nhan
