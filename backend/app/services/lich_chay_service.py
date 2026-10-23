"""Lịch chạy định kỳ — UC-18, NGHIEP_VU.md mục 3.5. Lịch luôn đi theo CẶP (1 lịch chiều đi + 1 lịch chiều về
cùng tuyến) để không còn chuyến 1 chiều mà thiếu chiều kia. Quản lý chủ động sinh chuyen_xe cho cả cặp trong 1 khoảng
ngày cụ thể — KHÔNG có job nền tự động: bấm "Sinh chuyến" mỗi khi cần thêm.

Mỗi chu kỳ của cặp: xe xuất bến chiều đi ngày D, tới nơi sau đúng thời gian chạy của tuyến, nghỉ tối thiểu
KHOANG_NGHI_TOI_THIEU_PHUT rồi mới chạy chiều về vào đúng giờ quản lý đã nhập; chiều về rơi vào ngày D + ngay_lech.
"""

import datetime
import math
from zoneinfo import ZoneInfo

import psycopg2.errors

from app.repositories import chuyen_xe_repository as chuyen_xe_repo
from app.repositories import dia_diem_repository as dia_diem_repo
from app.repositories import lich_chay_repository as repo
from app.repositories import xe_repository as xe_repo
from app.services import gia_ve_service
from app.utils.loi import GiaTriLoi

MUI_GIO_VN = ZoneInfo("Asia/Ho_Chi_Minh")
SO_NGAY_TOI_DA_MOI_LAN = 180  # chặn nhỡ tay chọn khoảng quá dài, VD gõ nhầm năm
KHOANG_NGHI_TOI_THIEU_PHUT = 30  # xe tới nơi rồi tối thiểu bao lâu mới được chạy chiều về


def _kiem_tra_loai_xe(loai_xe_id: str) -> None:
    if not xe_repo.tim_loai_xe_theo_id(loai_xe_id):
        raise GiaTriLoi("Loại xe không tồn tại")


def _bao_loi_neu_trung(tuyen_id: str, chieu: str, gio_khoi_hanh, loai_xe_id: str, tru_id: str | None = None) -> None:
    if repo.tim_trung(tuyen_id, chieu, gio_khoi_hanh, loai_xe_id, tru_id):
        ten = "chiều đi" if chieu == "xuoi" else "chiều về"
        raise GiaTriLoi(f"Đã có lịch {ten} cùng tuyến, giờ khởi hành và loại xe này")


def _phut_trong_ngay(gio: datetime.time) -> int:
    return gio.hour * 60 + gio.minute


def tinh_ngay_lech(gio_xuoi: datetime.time, gio_nguoc: datetime.time, tong_phut: int) -> int:
    """Số ngày chiều về lệch sau chiều đi: ít nhất để xe tới nơi (giờ đi + thời gian chạy) rồi nghỉ đủ
    KHOANG_NGHI_TOI_THIEU_PHUT trước giờ khởi hành chiều về. 0 = cùng ngày."""
    can_den = _phut_trong_ngay(gio_xuoi) + tong_phut + KHOANG_NGHI_TOI_THIEU_PHUT
    return max(0, math.ceil((can_den - _phut_trong_ngay(gio_nguoc)) / 1440))


def _dinh_dang_gio(phut: int) -> str:
    return f"{(phut // 60) % 24:02d}:{phut % 60:02d}"


def kiem_tra_gio_cap(gio_xuoi: datetime.time, gio_nguoc: datetime.time, tong_phut: int) -> None:
    """Chiều đi kết thúc ngay trong ngày thì chiều về cũng phải chạy trong ngày đó, từ lúc xe nghỉ đủ
    KHOANG_NGHI_TOI_THIEU_PHUT trở đi. Chiều đi qua nửa đêm thì độ lệch ngày do tinh_ngay_lech lo."""
    den = _phut_trong_ngay(gio_xuoi) + tong_phut
    som_nhat = den + KHOANG_NGHI_TOI_THIEU_PHUT
    if den < 1440 and som_nhat < 1440 and _phut_trong_ngay(gio_nguoc) < som_nhat:
        raise GiaTriLoi(
            f"Chiều đi kết thúc lúc {_dinh_dang_gio(den)} (trong ngày) nên chiều về phải khởi hành "
            f"cùng ngày, từ {_dinh_dang_gio(som_nhat)} trở đi (xe nghỉ tối thiểu {KHOANG_NGHI_TOI_THIEU_PHUT} phút)"
        )


def _tong_phut(tuyen_id: str) -> int:
    tong = repo.tong_phut_tuyen(tuyen_id)
    if not tong:
        raise GiaTriLoi("Tuyến này chưa có thời gian chạy dự kiến giữa các điểm dừng")
    return tong


def _gio_tu_phut(phut: int) -> datetime.time:
    return datetime.time((phut // 60) % 24, phut % 60)


def xem_truoc_cap(tuyen_id: str, gio_xuoi: datetime.time, gio_nguoc: datetime.time) -> dict:
    """Dữ liệu cho form tạo cặp: giờ xe tới nơi và chiều về lệch mấy ngày."""
    if not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến không tồn tại")
    tong = _tong_phut(tuyen_id)
    kiem_tra_gio_cap(gio_xuoi, gio_nguoc, tong)
    den = _phut_trong_ngay(gio_xuoi) + tong
    return {
        "tong_phut": tong,
        "gio_den": _gio_tu_phut(den),
        "ngay_den_lech": den // 1440,
        "ngay_lech": tinh_ngay_lech(gio_xuoi, gio_nguoc, tong),
    }


def _dung_cap(lich_cua_cap: list[dict]) -> dict:
    xuoi = next(l for l in lich_cua_cap if l["chieu"] == "xuoi")
    nguoc = next(l for l in lich_cua_cap if l["chieu"] == "nguoc")
    den = _phut_trong_ngay(xuoi["gio_khoi_hanh"]) + (xuoi["tong_phut"] or 0)
    return {
        "cap_id": xuoi["cap_id"],
        "tuyen_id": xuoi["tuyen_id"],
        "ma_tuyen": xuoi["ma_tuyen"],
        "ten_tuyen": xuoi["ten_tuyen"],
        "tong_phut": xuoi["tong_phut"],
        "ngay_lech": nguoc["ngay_lech"],
        "he_so_gia": xuoi["he_so_gia"],
        "dang_ap_dung": xuoi["dang_ap_dung"] and nguoc["dang_ap_dung"],
        "so_chuyen_da_sinh": xuoi["so_chuyen_da_sinh"] + nguoc["so_chuyen_da_sinh"],
        "gio_den_chieu_di": _gio_tu_phut(den),
        "ngay_den_lech": den // 1440,
        "xuoi": xuoi,
        "nguoc": nguoc,
    }


def _lay_cap(cap_id: str) -> list[dict]:
    lich = repo.lich_cua_cap(cap_id)
    if len(lich) != 2:
        raise GiaTriLoi("Không tìm thấy cặp lịch chạy")
    return lich


def tao_cap_lich_chay(tuyen_id: str, xuoi: dict, nguoc: dict, he_so_gia=1) -> dict:
    """xuoi/nguoc: {gio_khoi_hanh, loai_xe_id}. Tạo đồng thời cả 2 lịch hoặc không tạo gì."""
    if not dia_diem_repo.tim_tuyen_theo_id(tuyen_id):
        raise GiaTriLoi("Tuyến không tồn tại")
    # Lập lịch không cần giá vé; thiếu giá vé chỉ chặn bước sinh chuyến (xem sinh_chuyen_cho_cac_cap)
    tong = _tong_phut(tuyen_id)
    if xuoi["loai_xe_id"] != nguoc["loai_xe_id"]:
        raise GiaTriLoi("Chiều đi và chiều về của 1 cặp phải dùng cùng loại xe")
    _kiem_tra_loai_xe(xuoi["loai_xe_id"])
    for chieu, lich in (("xuoi", xuoi), ("nguoc", nguoc)):
        _bao_loi_neu_trung(tuyen_id, chieu, lich["gio_khoi_hanh"], lich["loai_xe_id"])

    kiem_tra_gio_cap(xuoi["gio_khoi_hanh"], nguoc["gio_khoi_hanh"], tong)
    ngay_lech = tinh_ngay_lech(xuoi["gio_khoi_hanh"], nguoc["gio_khoi_hanh"], tong)
    cap_id = repo.tao_cap(tuyen_id, xuoi, nguoc, ngay_lech, he_so_gia)
    return _dung_cap(repo.lich_cua_cap(cap_id))


def danh_sach_cap(tuyen_id: str | None = None) -> list[dict]:
    theo_cap: dict = {}
    for lich in repo.danh_sach(tuyen_id):
        theo_cap.setdefault(lich["cap_id"], []).append(lich)
    cac_cap = [_dung_cap(v) for v in theo_cap.values() if len(v) == 2]
    khoang_gia_theo_tuyen: dict = {}
    for cap in cac_cap:
        tid = str(cap["tuyen_id"])
        if tid not in khoang_gia_theo_tuyen:
            khoang_gia_theo_tuyen[tid] = gia_ve_service.khoang_ngay_co_gia(tid)
        khoang = khoang_gia_theo_tuyen[tid]
        cap["sinh_chuyen_tu_ngay"] = khoang[0] if khoang else None
        # chuyến về chạy sau chuyến đi `ngay_lech` ngày nên chuyến đi phải sớm hơn ngày cuối bộ giá chừng đó để cả chu kỳ còn trong bộ
        cap["sinh_chuyen_den_ngay"] = khoang[1] - datetime.timedelta(days=cap["ngay_lech"]) if khoang else None
    return sorted(cac_cap, key=lambda c: (c["ten_tuyen"], c["xuoi"]["gio_khoi_hanh"]))


def sua_lich_chay(lich_id: str, gio_khoi_hanh, loai_xe_id: str) -> dict:
    """Sửa giờ 1 chiều trong cặp (loại xe đổi thì đổi cho cả cặp); độ lệch ngày tự tính lại theo giờ mới."""
    lich = repo.tim_theo_id(lich_id)
    if not lich:
        raise GiaTriLoi("Không tìm thấy lịch chạy")
    cap = _lay_cap(str(lich["cap_id"]))
    _kiem_tra_loai_xe(loai_xe_id)
    for l in cap:
        gio_l = gio_khoi_hanh if l["id"] == lich_id else l["gio_khoi_hanh"]
        _bao_loi_neu_trung(str(l["tuyen_id"]), l["chieu"], gio_l, loai_xe_id, tru_id=l["id"])

    # Cặp đã sinh chuyến thì khóa sửa: chuyến cũ giữ nguyên giờ/loại xe cũ nên lịch và chuyến sẽ lệch nhau, và những
    # ngày đã có chuyến sẽ không được sinh lại theo lịch mới. Muốn đổi: ngừng áp dụng cặp này + tạo cặp mới.
    so_da_sinh = sum(l["so_chuyen_da_sinh"] for l in cap)
    if so_da_sinh > 0:
        raise GiaTriLoi(
            f"Cặp lịch này đã sinh {so_da_sinh} chuyến nên không sửa được — "
            "hãy ngừng áp dụng cặp này rồi tạo cặp mới"
        )
    gio = {l["chieu"]: l["gio_khoi_hanh"] for l in cap}
    gio[lich["chieu"]] = gio_khoi_hanh
    tong = _tong_phut(str(lich["tuyen_id"]))
    kiem_tra_gio_cap(gio["xuoi"], gio["nguoc"], tong)
    ngay_lech = tinh_ngay_lech(gio["xuoi"], gio["nguoc"], tong)
    repo.sua(lich_id, gio_khoi_hanh, loai_xe_id, str(lich["cap_id"]), ngay_lech)
    return _dung_cap(repo.lich_cua_cap(str(lich["cap_id"])))


def doi_he_so_gia_cap(cap_id: str, he_so_gia) -> dict:
    """Hệ số giá luôn sửa được (kể cả cặp đã sinh chuyến) vì mỗi chuyến đã chốt hệ số riêng lúc sinh: hệ số mới chỉ áp dụng
    cho chuyến sinh sau đó."""
    _lay_cap(cap_id)
    repo.doi_he_so_gia_cap(cap_id, he_so_gia)
    return _dung_cap(repo.lich_cua_cap(cap_id))


def doi_ap_dung_cap(cap_id: str, dang_ap_dung: bool) -> dict:
    _lay_cap(cap_id)
    # dang_ap_dung = false chỉ ngừng sinh chuyến mới cho cả cặp, không hủy/đụng các chuyến đã sinh
    repo.doi_ap_dung_cap(cap_id, dang_ap_dung)
    return _dung_cap(repo.lich_cua_cap(cap_id))


def xoa_cap(cap_id: str) -> None:
    _lay_cap(cap_id)
    try:
        repo.xoa_cap(cap_id)
    except psycopg2.errors.ForeignKeyViolation:
        raise GiaTriLoi("Không thể xóa: cặp lịch này đã sinh chuyến — hãy ngừng áp dụng thay vì xóa")


def _kiem_tra_trong_khoang_bo_gia(lich_cap: dict, tu_ngay: datetime.date, den_ngay: datetime.date) -> None:
    """Chỉ được sinh chuyến trong khoảng ngày của các bộ giá vé của tuyến; chuyến về lệch +N ngày nên ngày chuyến đi tối đa
    là ngày cuối bộ giá mới nhất trừ N (cả chu kỳ phải nằm trong bộ giá)."""
    ten = lich_cap["xuoi"]["ten_tuyen"]
    khoang = gia_ve_service.khoang_ngay_co_gia(str(lich_cap["xuoi"]["tuyen_id"]))
    if khoang is None:
        raise GiaTriLoi(f"Tuyến {ten} chưa có bộ giá vé nên chưa sinh chuyến được — hãy tạo bộ giá (mục Giá vé)")
    dau, cuoi = khoang
    lech = lich_cap["nguoc"]["ngay_lech"]
    toi_da = cuoi - datetime.timedelta(days=lech)
    if tu_ngay < dau:
        raise GiaTriLoi(f"Tuyến {ten} có bộ giá vé đầu tiên bắt đầu từ ngày {dau.strftime('%d/%m/%Y')} nên chưa sinh chuyến trước ngày đó được")
    if den_ngay > toi_da:
        raise GiaTriLoi(
            f"Tuyến {ten} chỉ sinh được đến ngày {toi_da.strftime('%d/%m/%Y')} "
            f"(bộ giá vé mới nhất kết thúc ngày {cuoi.strftime('%d/%m/%Y')}"
            + (f"; chuyến về chạy sau chuyến đi {lech} ngày" if lech else "")
            + ") — hãy kéo dài bộ giá hoặc tạo bộ giá mới nối tiếp"
        )


def sinh_chuyen_cho_cac_cap(cap_ids: list[str], tu_ngay: datetime.date, den_ngay: datetime.date) -> dict:
    """UC-18 — sinh chuyen_xe cho các cặp được chọn: mỗi ngày D trong khoảng, chiều đi chạy ngày D còn chiều về chạy
    ngày D + ngay_lech của cặp (nên ngày đầu không có chuyến về buổi sáng còn chiều về của ngày cuối có thể rơi sau
    `den_ngay`; lần sinh kế tiếp nối liền vì ngày đã có chuyến được bỏ qua). Toàn bộ trong 1 giao dịch.
    Chu kỳ nào có chuyến đi đã quá giờ hiện tại thì bỏ cả chu kỳ (không sinh chuyến đi lẫn chuyến về của nó).
    Trả về số chuyến mới sinh / số chuyến đã có sẵn (bị bỏ qua) của từng chiều và số chu kỳ bị bỏ vì quá giờ."""
    if not cap_ids:
        raise GiaTriLoi("Hãy chọn ít nhất 1 cặp lịch chạy")
    if tu_ngay > den_ngay:
        raise GiaTriLoi("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")
    hom_nay = datetime.datetime.now(MUI_GIO_VN).date()
    if tu_ngay < hom_nay:
        raise GiaTriLoi("Không thể sinh chuyến cho ngày trong quá khứ")
    if (den_ngay - tu_ngay).days + 1 > SO_NGAY_TOI_DA_MOI_LAN:
        raise GiaTriLoi(f"Mỗi lần chỉ sinh tối đa {SO_NGAY_TOI_DA_MOI_LAN} ngày — hãy chia nhỏ khoảng ngày")

    bay_gio = datetime.datetime.now(MUI_GIO_VN)
    ke_hoach = []
    so_chu_ky_qua_gio = 0
    for cap_id in dict.fromkeys(cap_ids):
        lich_cap = {l["chieu"]: l for l in _lay_cap(cap_id)}
        for lich in lich_cap.values():
            if not lich["dang_ap_dung"]:
                raise GiaTriLoi(f"Cặp lịch tuyến {lich['ten_tuyen']} đã ngừng áp dụng — hãy bật lại trước khi sinh chuyến")
        _kiem_tra_trong_khoang_bo_gia(lich_cap, tu_ngay, den_ngay)
        ngay = tu_ngay
        while ngay <= den_ngay:
            # gio_khoi_hanh lưu TIMESTAMPTZ nhưng session Postgres mặc định Etc/UTC — gắn múi giờ VN tường minh
            gio_di = datetime.datetime.combine(ngay, lich_cap["xuoi"]["gio_khoi_hanh"], tzinfo=MUI_GIO_VN)
            if gio_di <= bay_gio:
                # Chuyến đi của chu kỳ này đã quá giờ → bỏ cả chu kỳ, kể cả chuyến về đi kèm (nếu không sẽ thừa 1 chuyến về lẻ)
                so_chu_ky_qua_gio += 1
            else:
                for lich in lich_cap.values():
                    ngay_chay = ngay + datetime.timedelta(days=lich["ngay_lech"])
                    gio = datetime.datetime.combine(ngay_chay, lich["gio_khoi_hanh"], tzinfo=MUI_GIO_VN)
                    # chu_ky: chuyến đi ngày D và chuyến về ngày D + ngay_lech của cùng 1 cặp là 1 chu trình (điều độ viên gán xe cho cả hai)
                    ke_hoach.append({"lich": lich, "ngay": ngay_chay, "gio_khoi_hanh": gio, "chu_ky": (str(lich["cap_id"]), ngay)})
            ngay += datetime.timedelta(days=1)

    # Mỗi ngày khởi hành của các chuyến sắp sinh (cả chuyến về lệch ngày) phải có bộ giá vé đầy đủ áp dụng, nếu không
    # chuyến đó không có giá nên khách không thấy
    ngay_theo_tuyen: dict[str, dict] = {}
    for muc in ke_hoach:
        thong_tin = ngay_theo_tuyen.setdefault(str(muc["lich"]["tuyen_id"]), {"ten": muc["lich"]["ten_tuyen"], "ngay": set()})
        thong_tin["ngay"].add(muc["ngay"])
    for tuyen_id, thong_tin in ngay_theo_tuyen.items():
        thieu = gia_ve_service.ngay_chua_co_gia(tuyen_id, list(thong_tin["ngay"]))
        if thieu:
            ds = ", ".join(n.strftime("%d/%m/%Y") for n in thieu[:4]) + (" …" if len(thieu) > 4 else "")
            raise GiaTriLoi(
                f"Tuyến {thong_tin['ten']} chưa có bộ giá vé đầy đủ áp dụng cho ngày {ds} nên chưa sinh chuyến được — "
                "hãy tạo bộ giá (mục Giá vé) có ngày áp dụng không muộn hơn ngày đầu tiên đó"
            )

    tong = {"xuoi": {"moi": 0, "da_co": 0}, "nguoc": {"moi": 0, "da_co": 0}}
    for muc in chuyen_xe_repo.sinh_nhieu_chuyen_tu_lich(ke_hoach):
        tong[muc["lich"]["chieu"]]["moi" if muc["da_sinh"] else "da_co"] += 1
    return {
        "so_chuyen_di_moi_sinh": tong["xuoi"]["moi"],
        "so_chuyen_ve_moi_sinh": tong["nguoc"]["moi"],
        "so_chuyen_di_da_co_san": tong["xuoi"]["da_co"],
        "so_chuyen_ve_da_co_san": tong["nguoc"]["da_co"],
        "so_chu_ky_bo_qua_do_qua_gio": so_chu_ky_qua_gio,
    }
