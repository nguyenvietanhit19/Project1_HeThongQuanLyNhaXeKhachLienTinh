"""Kiểm tra file ảnh tải lên (ảnh hồ sơ, ảnh giấy tờ nhân sự) — KE_HOACH_CLOUDINARY.md, quyết định 4.

Quy tắc: tối đa 5MB, chỉ JPEG / PNG / WebP, xác định theo NỘI DUNG THẬT của file (chữ ký đầu file, "magic bytes") chứ
không tin đuôi file hay Content-Type do client tự khai (kẻ xấu đổi tên `virus.exe` thành `anh.jpg` rất dễ).

Hàm chỉ KIỂM TRA, không đọc / ghi gì ngoài bộ nhớ; vi phạm thì ném GiaTriLoi (HTTP 400) kèm thông báo tiếng Việt.
"""

from app.utils.loi import GiaTriLoi

KICH_THUOC_TOI_DA_BYTE = 5 * 1024 * 1024  # 5MB


def nhan_dien_dinh_dang(du_lieu: bytes) -> str | None:
    """'jpeg' | 'png' | 'webp' theo chữ ký đầu file; None nếu không phải 3 loại này."""
    if du_lieu[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if du_lieu[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if du_lieu[:4] == b"RIFF" and du_lieu[8:12] == b"WEBP":
        return "webp"
    return None


def kiem_tra_file_anh(du_lieu: bytes) -> str:
    """Trả về định dạng ('jpeg' | 'png' | 'webp') nếu hợp lệ, ngược lại ném GiaTriLoi."""
    if not du_lieu:
        raise GiaTriLoi("File ảnh rỗng")
    if len(du_lieu) > KICH_THUOC_TOI_DA_BYTE:
        raise GiaTriLoi(f"Ảnh quá lớn, tối đa {KICH_THUOC_TOI_DA_BYTE // (1024 * 1024)}MB")
    dinh_dang = nhan_dien_dinh_dang(du_lieu)
    if dinh_dang is None:
        raise GiaTriLoi("Chỉ nhận ảnh JPEG, PNG hoặc WebP")
    return dinh_dang
