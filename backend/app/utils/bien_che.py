"""Quy tắc "xe đủ nhân sự" dùng chung (NGHIEP_VU.md mục 3.2, UC-35, UC-44).

Một xe ĐỦ nhân sự khi có đúng/ít nhất 2 tài xế và ít nhất 1 phụ xe ĐANG HOẠT ĐỘNG — tức dòng `xe_nhan_su.trang_thai = 'dang_hoat_dong'`
(cố định hoặc tạm thời) mà hồ sơ nhân sự còn `dang_lam`. Người tạm nghỉ hoặc đã nghỉ việc không được tính; người tạm thời thay chỗ người
tạm nghỉ thì được tính. Hàm thuần, không đụng DB.
"""

SO_TAI_XE_YEU_CAU = 2  # mục 3.2: mỗi xe đúng 2 tài xế (thay phiên nhau)
SO_PHU_XE_TOI_THIEU = 1


def du_nhan_su(so_tai_xe: int, so_phu_xe: int) -> bool:
    return so_tai_xe >= SO_TAI_XE_YEU_CAU and so_phu_xe >= SO_PHU_XE_TOI_THIEU


def mo_ta_thieu(so_tai_xe: int, so_phu_xe: int) -> str:
    """"thiếu 1 tài xế", "thiếu 2 tài xế và 1 phụ xe"... ; rỗng nếu đã đủ."""
    thieu = []
    if so_tai_xe < SO_TAI_XE_YEU_CAU:
        thieu.append(f"{SO_TAI_XE_YEU_CAU - so_tai_xe} tài xế")
    if so_phu_xe < SO_PHU_XE_TOI_THIEU:
        thieu.append(f"{SO_PHU_XE_TOI_THIEU - so_phu_xe} phụ xe")
    return "thiếu " + " và ".join(thieu) if thieu else ""


def can_canh_bao_thieu_nhan_su(trang_thai_xe: str, tuyen_id, so_tai_xe: int, so_phu_xe: int) -> bool:
    """Có cần cảnh báo thiếu nhân sự trên trang Xe không: xe đang hoạt động, CỐ ĐỊNH tuyến (xe dự phòng — `tuyen_id` rỗng — không cần cảnh báo
    vì nhân sự của nó điều độ viên bố trí theo từng lúc), mà chưa đủ nhân sự."""
    return trang_thai_xe == "hoat_dong" and bool(tuyen_id) and not du_nhan_su(so_tai_xe, so_phu_xe)
