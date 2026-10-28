import datetime
from zoneinfo import ZoneInfo

from app.config import HAN_THANH_TOAN_NGAY_PHUT, VNPAY_CHE_DO
from app.repositories import lich_su_hoan_tien_repository as hoan_tien_repo
from app.repositories import quay_ve_repository as repo
from app.repositories import tim_kiem_chuyen_repository as chuyen_repo
from app.repositories import ve_lock_repository as lock_repo
from app.repositories import ve_thanh_toan_repository as thanh_toan_repo
from app.services import dat_ve_service, thong_bao_khach_service as thong_bao, tim_kiem_chuyen_service, vnpay_service
from app.utils.loi import CamTruyCap, GiaTriLoi, KhongTimThay
from app.utils.so_dien_thoai import chuan_hoa_so_dien_thoai

MUI_GIO = ZoneInfo("Asia/Ho_Chi_Minh")


def lay_van_phong(nguoi_dung) -> dict:
    if not nguoi_dung.van_phong_id:
        raise CamTruyCap("Tài khoản chưa được gán văn phòng phụ trách")
    vp = repo.van_phong(nguoi_dung.van_phong_id)
    if not vp:
        raise CamTruyCap("Văn phòng phụ trách không còn hợp lệ")
    return vp


def tim_chuyen(nguoi_dung, diem_di_id: str, diem_den_id: str, ngay: datetime.date) -> list[dict]:
    vp = lay_van_phong(nguoi_dung)
    if str(diem_di_id) != str(vp["khu_vuc_id"]):
        raise CamTruyCap("Điểm đi phải thuộc khu vực văn phòng của bạn")
    result = tim_kiem_chuyen_service.tim_chuyen(diem_di_id, diem_den_id, ngay)
    diem_quay = repo.thong_tin_chuyen_tai_van_phong([str(x["id"]) for x in result], str(vp["id"]), str(diem_den_id))
    doan_ve: dict[str, list[dict]] = {}
    for ve in chuyen_repo.tim_doan_ve_dang_giu(list(diem_quay)):
        doan_ve.setdefault(str(ve["chuyen_id"]), []).append(ve)
    ket_qua = []
    for chuyen in result:
        ma_chuyen = str(chuyen["id"])
        if ma_chuyen not in diem_quay:
            continue
        diem = diem_quay[ma_chuyen]
        ghe_bi_giu = tim_kiem_chuyen_service.tinh_ghe_dang_giu(
            doan_ve.get(ma_chuyen, []), diem["hl_don"], diem["hl_tra"]
        )
        ket_qua.append({
            **chuyen,
            "diem_don_id": vp["id"], "ten_diem_don": vp["ten"],
            "gio_don_du_kien": diem["gio_don_du_kien"],
            "diem_tra_id": diem["diem_tra_id"], "ten_diem_tra": diem["ten_diem_tra"],
            "gio_den_du_kien": diem["gio_den_du_kien"],
            "so_ghe_trong": max(int(chuyen["tong_ghe"]) - len(ghe_bi_giu), 0),
        })
    return ket_qua


def diem_tra(nguoi_dung, chuyen_id: str, diem_den_id: str) -> list[dict]:
    vp = lay_van_phong(nguoi_dung)
    if not repo.chuyen_co_van_phong(chuyen_id, str(vp["id"])):
        raise GiaTriLoi("Chuyến không đi qua văn phòng của bạn")
    cac_diem = lock_repo.tim_diem_cua_chuyen(chuyen_id)
    diem_don = next((d for d in cac_diem if str(d["diem_id"]) == str(vp["id"])), None)
    if not diem_don:
        raise GiaTriLoi("Văn phòng không nằm trên chuyến")
    return [
        {"diem_id": d["diem_id"], "ten": d["ten"], "loai": d["loai"]}
        for d in cac_diem
        if d["hl"] > diem_don["hl"] and d["khu_vuc_id"] == str(diem_den_id)
        and d["loai"] in ("van_phong", "diem_dung")
    ]


def so_do_ghe(nguoi_dung, chuyen_id: str, diem_den_id: str, diem_tra_id: str) -> dict:
    vp = lay_van_phong(nguoi_dung)
    if not repo.diem_hop_le(chuyen_id, str(vp["id"]), diem_tra_id):
        raise GiaTriLoi("Văn phòng hoặc điểm trả không nằm đúng thứ tự trên chuyến")
    if not repo.diem_tra_thuoc_khu_vuc(diem_tra_id, diem_den_id):
        raise GiaTriLoi("Điểm trả không thuộc khu vực đã chọn")
    detail = tim_kiem_chuyen_service.so_do_ghe_chuyen(chuyen_id, str(vp["khu_vuc_id"]), diem_den_id)
    stops = lock_repo.tim_diem_cua_chuyen(chuyen_id)
    origin = next((d for d in stops if str(d["diem_id"]) == str(vp["id"])), None)
    destination = next((d for d in stops if str(d["diem_id"]) == str(diem_tra_id)), None)
    if not origin or not destination or origin["hl"] >= destination["hl"]:
        raise GiaTriLoi("Điểm trả không đúng thứ tự trên chuyến")
    occupied = {
        v["so_ghe"]
        for v in chuyen_repo.tim_doan_ve_dang_giu([chuyen_id])
        if int(v["hl_don"]) < int(destination["hl"]) and int(v["hl_tra"]) > int(origin["hl"])
    }
    detail["so_do_ghe"] = [
        {**seat, "trang_thai": "da_co_nguoi" if seat["ma_ghe"] in occupied else "trong"}
        for seat in detail["so_do_ghe"]
    ]
    return detail


def ban_ve(nguoi_dung, du_lieu) -> dict:
    vp = lay_van_phong(nguoi_dung)
    if str(du_lieu.diem_di_id) != str(vp["khu_vuc_id"]):
        raise CamTruyCap("Điểm đi không thuộc khu vực văn phòng của bạn")
    if not repo.diem_tra_thuoc_khu_vuc(str(du_lieu.diem_tra_id), str(du_lieu.diem_den_id)):
        raise GiaTriLoi("Điểm trả không thuộc khu vực đến đã chọn")
    ghe = dat_ve_service.chuan_hoa_danh_sach_ghe(du_lieu.danh_sach_ghe)
    sdt = chuan_hoa_so_dien_thoai(du_lieu.sdt_khach)
    if not repo.diem_hop_le(str(du_lieu.chuyen_id), str(vp["id"]), str(du_lieu.diem_tra_id)):
        raise CamTruyCap("Điểm đón/trả không hợp lệ tại văn phòng này")
    if du_lieu.kenh_ban == "tai_quay" and du_lieu.phuong_thuc == "thanh_toan_tai_quay":
        raise GiaTriLoi("Bán trực tiếp cần thu tiền mặt hoặc tạo thanh toán VNPay")
    if du_lieu.kenh_ban == "hotline" and du_lieu.phuong_thuc == "tien_mat":
        raise GiaTriLoi("Đơn hotline chưa thu tiền; chọn VNPay hoặc thanh toán khi khách đến quầy")
    khach_hang_id = str(du_lieu.khach_hang_id) if du_lieu.khach_hang_id else None
    kh = repo.khach_hang_theo_sdt(sdt)
    if khach_hang_id and (not kh or str(kh["id"]) != khach_hang_id):
        raise GiaTriLoi("Số điện thoại không khớp với hồ sơ khách hàng")
    if kh:
        khach_hang_id = str(kh["id"])
        ten = kh["ho_ten"]
    else:
        khach_cu = repo.khach_vang_lai_theo_sdt(sdt)
        ten = khach_cu["ho_ten"] if khach_cu else " ".join((du_lieu.ten_khach or "").split())
        if len(ten) < 2:
            raise GiaTriLoi("Khách mới cần nhập họ tên ít nhất 2 ký tự")

    detail = tim_kiem_chuyen_service.so_do_ghe_chuyen(
        str(du_lieu.chuyen_id), str(vp["khu_vuc_id"]), str(du_lieu.diem_den_id)
    )
    seat_map = {g["ma_ghe"]: int(g["gia"]) for g in detail["so_do_ghe"]}
    if not set(ghe) <= set(seat_map):
        raise GiaTriLoi("Có ghế không thuộc sơ đồ chuyến")
    ma_dat_cho = dat_ve_service.sinh_ma_dat_cho()
    phuong_thuc = du_lieu.phuong_thuc
    created = lock_repo.tao_ve_quay(
        str(du_lieu.chuyen_id), ghe, str(vp["id"]), str(du_lieu.diem_tra_id),
        {s: seat_map[s] for s in ghe}, ma_dat_cho, str(nguoi_dung.id), khach_hang_id, ten, sdt,
        du_lieu.kenh_ban, phuong_thuc,
    )
    return {
        "ma_dat_cho": ma_dat_cho,
        "kenh_ban": du_lieu.kenh_ban,
        "tong_tien": sum(int(x["gia"]) for x in created),
        "ten_khach": created[0].get("ten_khach_vang_lai", ten),
        "ve": created,
        "trang_thai": "da_thanh_toan" if all(v["trang_thai"] == "da_thanh_toan" for v in created) else "giu_cho",
    }


def _dung_ve(v: dict) -> dict:
    now = datetime.datetime.now(MUI_GIO)
    gio_don = v["gio_don_du_kien"]
    before_cutoff = dat_ve_service.con_truoc_moc_chot(gio_don, now)
    unpaid_hold = (v["trang_thai"] == "giu_cho" and v["gio_khoi_hanh"] > now
                   and (v.get("han_giu_cho_den") is None or v["han_giu_cho_den"] > now))
    refund_allowed = v["trang_thai"] == "da_thanh_toan" and (
        v["dang_hoan"] or (v["trang_thai_chuyen"] == "gap_su_co" and v.get("loai_su_co") == "loi_nha_xe")
    )
    return {
        **v,
        "co_the_in": v["trang_thai"] == "da_thanh_toan",
        "co_the_thanh_toan": unpaid_hold and before_cutoff and v["loai_hinh_thanh_toan"] == "thanh_toan_tai_quay",
        "co_the_tao_qr": unpaid_hold and before_cutoff and v.get("kenh_ban") in ("tai_quay", "hotline"),
        "co_the_huy_giu_cho": unpaid_hold and before_cutoff and v["loai_hinh_thanh_toan"] == "thanh_toan_tai_quay",
        "co_the_huy_hoan_tien": refund_allowed,
        "ten_khach": v["ten_khach"] or "Khách vãng lai",
        "gia": int(v["gia"]),
    }


def tra_cuu(nguoi_dung, ma_dat_cho: str | None = None, sdt: str | None = None) -> list[dict]:
    vp = lay_van_phong(nguoi_dung)
    if not ma_dat_cho and not sdt:
        raise GiaTriLoi("Nhập mã đặt chỗ hoặc số điện thoại để tra cứu")
    phone = chuan_hoa_so_dien_thoai(sdt) if sdt else None
    return [_dung_ve(v) for v in repo.tra_cuu(str(vp["id"]), ma_dat_cho, phone)]


def ve_cho_thanh_toan(nguoi_dung, trang: int, kich_thuoc_trang: int) -> dict:
    vp = lay_van_phong(nguoi_dung)
    return repo.ve_cho_thanh_toan(str(vp["id"]), trang, kich_thuoc_trang)


def tim_khach_hang(sdt: str) -> dict | None:
    phone = chuan_hoa_so_dien_thoai(sdt)
    # Hồ sơ chỉ được dùng để bán vé; không trả email, vai trò hay dữ liệu xác thực.
    kh = repo.khach_hang_theo_sdt(phone)
    if kh:
        return {**kh, "nguon": "tai_khoan"}
    khach_cu = repo.khach_vang_lai_theo_sdt(phone)
    return {"id": None, "ho_ten": khach_cu["ho_ten"], "nguon": "lich_su"} if khach_cu else None


def thu_tien(nguoi_dung, ma_dat_cho: str, phuong_thuc: str) -> dict:
    vp = lay_van_phong(nguoi_dung)
    if phuong_thuc != "tien_mat":
        raise GiaTriLoi("Thanh toán QR cần tạo đường dẫn VNPay")
    tickets = repo.tra_cuu(str(vp["id"]), ma_dat_cho=ma_dat_cho)
    held = [v for v in tickets if v["trang_thai"] == "giu_cho"]
    if not held:
        raise GiaTriLoi("Không có vé giữ chỗ chưa thanh toán tại văn phòng này")
    if any(v["loai_hinh_thanh_toan"] != "thanh_toan_tai_quay" for v in held):
        raise GiaTriLoi("Lượt này đang chờ thanh toán QR; không thể ghi nhận thêm tiền mặt")
    now = datetime.datetime.now(MUI_GIO)
    if any(v.get("han_giu_cho_den") and v["han_giu_cho_den"] <= now for v in held):
        raise GiaTriLoi("Đã hết hạn giữ vé")
    if any(v["gio_khoi_hanh"] <= now for v in held):
        raise GiaTriLoi("Chuyến đã qua giờ khởi hành; vé chờ thanh toán sẽ tự hủy")
    if any(not dat_ve_service.con_truoc_moc_chot(v["gio_don_du_kien"], now) for v in held):
        raise GiaTriLoi("Đã qua thời điểm nhận thanh toán trước giờ khởi hành")
    updated = lock_repo.thanh_toan_ve_quay(ma_dat_cho, str(vp["id"]), str(nguoi_dung.id), phuong_thuc, len(held))
    if updated != len(held):
        raise GiaTriLoi("Một số vé đã thay đổi trạng thái; tải lại danh sách trước khi thu tiền")
    thong_bao.don_nhac_quay_ve(ma_dat_cho)
    return {"ma_dat_cho": ma_dat_cho, "so_ve_da_thanh_toan": updated}


def tao_link_thanh_toan_dat_cho(nguoi_dung, ma_dat_cho: str, frontend_origin: str, ip: str = "127.0.0.1") -> str:
    vp = lay_van_phong(nguoi_dung)
    # Xác thực origin trước khi đổi trạng thái đặt chỗ.
    vnpay_service.kiem_tra_origin_frontend(frontend_origin)
    now = datetime.datetime.now(datetime.timezone.utc)
    giao_dich = thanh_toan_repo.bat_dau_thanh_toan_qr_quay(
        ma_dat_cho, str(vp["id"]), vnpay_service.tao_ma_giao_dich(ma_dat_cho, now), HAN_THANH_TOAN_NGAY_PHUT,
    )
    return vnpay_service.tao_url_thanh_toan(
        ma_dat_cho, giao_dich["tong_tien"], giao_dich["han_thanh_toan"],
        frontend_origin, ip, now, giao_dich["ma_giao_dich"],
        noi_dung=f"Thanh toan luot ve xe {ma_dat_cho}", tra_ve_quay_ve=True,
    )


def tao_link_thanh_toan(nguoi_dung, ve_id: str, frontend_origin: str, ip: str = "127.0.0.1") -> str:
    vp = lay_van_phong(nguoi_dung)
    v = repo.ve_va_chuyen(ve_id, str(vp["id"]))
    if not v:
        raise KhongTimThay("Không tìm thấy vé thuộc văn phòng này")
    return tao_link_thanh_toan_dat_cho(nguoi_dung, v["ma_dat_cho"], frontend_origin, ip)


def huy_dat_cho(nguoi_dung, ma_dat_cho: str) -> dict:
    vp = lay_van_phong(nguoi_dung)
    tickets = repo.tra_cuu(str(vp["id"]), ma_dat_cho=ma_dat_cho)
    if not tickets or any(v["trang_thai"] != "giu_cho" for v in tickets):
        raise GiaTriLoi("Chỉ có thể hủy lượt đặt còn giữ chỗ chưa thanh toán")
    if any(v["loai_hinh_thanh_toan"] != "thanh_toan_tai_quay" for v in tickets):
        raise GiaTriLoi("Lượt đang thanh toán QR sẽ tự hết hạn; vui lòng chờ kết quả giao dịch")
    now = datetime.datetime.now(MUI_GIO)
    if any(not dat_ve_service.con_truoc_moc_chot(v["gio_don_du_kien"], now) for v in tickets):
        raise GiaTriLoi("Đã qua thời điểm hủy giữ chỗ")
    count = lock_repo.huy_ve_quay(ma_dat_cho, str(vp["id"]), len(tickets))
    if count != len(tickets):
        raise GiaTriLoi("Trạng thái vé vừa thay đổi; vui lòng tải lại")
    return {"ma_dat_cho": ma_dat_cho, "so_ve_da_huy": count}


def huy_ve_hoan_tien(nguoi_dung, ve_id: str, ly_do: str | None = None) -> dict:
    vp = lay_van_phong(nguoi_dung)
    v = repo.ve_va_chuyen(ve_id, str(vp["id"]))
    if not v:
        raise KhongTimThay("Không tìm thấy vé thuộc văn phòng này")
    if v["trang_thai"] != "da_thanh_toan" or not (
        v["dang_hoan"] or (v["trang_thai_chuyen"] == "gap_su_co" and v.get("loai_su_co") == "loi_nha_xe")
    ):
        raise GiaTriLoi("Vé không đủ điều kiện hủy nhận hoàn tiền")
    reason = "loi_nha_xe_giua_duong" if v["trang_thai_chuyen"] == "gap_su_co" else "hoan_truoc_gio_chay"
    refund = hoan_tien_repo.huy_ve_quay_va_tao_hoan_tien(str(v["id"]), reason)
    if (
        refund["trang_thai"] == "cho_xu_ly"
        and v.get("phuong_thuc_thanh_toan") == "chuyen_khoan"
        and v.get("ma_tham_chieu_vnpay")
        and v.get("ma_giao_dich_cong_thanh_toan")
        and vnpay_service.la_giao_dich_cua_ve(v["ma_tham_chieu_vnpay"])
        and VNPAY_CHE_DO == "sandbox"
    ):
        result = vnpay_service.hoan_tien_toan_phan(
            v["ma_tham_chieu_vnpay"], int(v["gia"]), v["ma_giao_dich_cong_thanh_toan"], str(nguoi_dung.id)
        )
        if result and result.get("vnp_ResponseCode") == "00" and result.get("vnp_TransactionStatus") == "00":
            hoan_tien_repo.cap_nhat_da_hoan_tu_dong(str(refund["id"]), str(result.get("vnp_TransactionNo", "")))
            refund["trang_thai"] = "da_hoan_tu_dong"
    message = "Đã hoàn tiền qua VNPay." if refund["trang_thai"] == "da_hoan_tu_dong" else "Yêu cầu hoàn tiền đã được ghi nhận; kế toán sẽ xử lý."
    return {"ma_ve": v["ma_ve"], "trang_thai": "da_huy", "trang_thai_hoan": refund["trang_thai"], "thong_bao": message}


def _kiem_tra_khoang_thong_ke(tu_ngay: datetime.date, den_ngay: datetime.date) -> None:
    if den_ngay < tu_ngay:
        raise GiaTriLoi("Ngày kết thúc phải sau hoặc bằng ngày bắt đầu")
    if (den_ngay - tu_ngay).days > 366:
        raise GiaTriLoi("Khoảng thống kê tối đa là 1 năm")


def thong_ke(nguoi_dung, tu_ngay: datetime.date, den_ngay: datetime.date, ma_ve: str | None = None) -> dict:
    _kiem_tra_khoang_thong_ke(tu_ngay, den_ngay)
    vp = lay_van_phong(nguoi_dung)
    ma_ve = ma_ve.strip() if ma_ve else None
    return repo.thong_ke(str(vp["id"]), tu_ngay, den_ngay, ma_ve or None)


def lich_su_ban_ve(
    nguoi_dung,
    tu_ngay: datetime.date,
    den_ngay: datetime.date,
    trang: int = 1,
    kich_thuoc_trang: int = 20,
    ma_ve: str | None = None,
) -> dict:
    _kiem_tra_khoang_thong_ke(tu_ngay, den_ngay)
    vp = lay_van_phong(nguoi_dung)
    ma_ve = ma_ve.strip() if ma_ve else None
    return repo.lich_su_ban_ve(str(vp["id"]), tu_ngay, den_ngay, trang, kich_thuoc_trang, ma_ve or None)


def ve_da_huy(nguoi_dung, ngay: datetime.date, trang: int = 1, kich_thuoc_trang: int = 20) -> dict:
    vp = lay_van_phong(nguoi_dung)
    return repo.ve_da_huy(str(vp["id"]), ngay, trang, kich_thuoc_trang)


def ve_theo_trang_thai(nguoi_dung, trang_thai: str, tu_ngay: datetime.date,
                       den_ngay: datetime.date, trang: int = 1,
                       kich_thuoc_trang: int = 20, ma_ve: str | None = None) -> dict:
    _kiem_tra_khoang_thong_ke(tu_ngay, den_ngay)
    if trang_thai not in ("giu_cho", "da_huy"):
        raise GiaTriLoi("Trạng thái vé không hợp lệ")
    vp = lay_van_phong(nguoi_dung)
    return repo.ve_theo_trang_thai(str(vp["id"]), trang_thai, tu_ngay, den_ngay,
                                   trang, kich_thuoc_trang, ma_ve.strip() or None if ma_ve else None)


def bieu_do_doanh_thu(nguoi_dung, tu_ngay: datetime.date, den_ngay: datetime.date,
                      ma_ve: str | None = None) -> dict:
    _kiem_tra_khoang_thong_ke(tu_ngay, den_ngay)
    vp = lay_van_phong(nguoi_dung)
    nhom = "day" if (den_ngay - tu_ngay).days <= 45 else "month"
    rows = repo.bieu_do_doanh_thu(str(vp["id"]), tu_ngay, den_ngay,
                                  ma_ve.strip() or None if ma_ve else None, nhom)
    by_date = {row["moc"]: row for row in rows}
    current = tu_ngay if nhom == "day" else tu_ngay.replace(day=1)
    end = den_ngay if nhom == "day" else den_ngay.replace(day=1)
    points = []
    while current <= end:
        row = by_date.get(current, {})
        points.append({"moc": current.isoformat(), "so_ve": int(row.get("so_ve") or 0),
                       "doanh_thu": int(row.get("doanh_thu") or 0)})
        if nhom == "day":
            current += datetime.timedelta(days=1)
        else:
            current = (current.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return {"nhom": "ngay" if nhom == "day" else "thang", "diem": points}


def tra_cuu_hoan_tien(nguoi_dung, ma_dat_cho: str | None = None, sdt: str | None = None) -> list[dict]:
    vp = lay_van_phong(nguoi_dung)
    phone = chuan_hoa_so_dien_thoai(sdt) if sdt else None
    return repo.danh_sach_hoan_tien(str(vp["id"]), ma_dat_cho, phone)
