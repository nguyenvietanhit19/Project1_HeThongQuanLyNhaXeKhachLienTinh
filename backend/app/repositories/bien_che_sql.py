"""Đoạn SQL dùng chung để đếm nhân sự HIỆU LỰC của xe (quy tắc ở app/utils/bien_che.py): dòng biên chế `dang_hoat_dong`
(cố định hoặc tạm thời) mà hồ sơ còn `dang_lam`. Nối chuỗi chỉ từ hằng cố định, không có dữ liệu người dùng."""


def cot_hieu_luc(alias_xe: str = "x") -> str:
    """Hai cột `so_tai_xe_hieu_luc`, `so_phu_xe_hieu_luc` để chèn vào danh sách SELECT của truy vấn có bảng xe tên `alias_xe`."""

    def dem(chuc_danh: str, ten_cot: str) -> str:
        return (
            "(SELECT count(*) FROM xe_nhan_su xn JOIN nhan_su_van_hanh nsx ON nsx.id = xn.nhan_su_van_hanh_id "
            f"WHERE xn.xe_id = {alias_xe}.id AND xn.trang_thai = 'dang_hoat_dong' AND nsx.trang_thai = 'dang_lam' "
            f"AND nsx.chuc_danh = '{chuc_danh}') AS {ten_cot}"
        )

    return dem("tai_xe", "so_tai_xe_hieu_luc") + ",\n           " + dem("phu_xe", "so_phu_xe_hieu_luc")
