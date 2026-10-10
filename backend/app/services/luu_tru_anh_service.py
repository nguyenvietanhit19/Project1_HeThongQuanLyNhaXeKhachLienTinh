"""Upload/xóa ảnh trên Cloudinary — phục vụ ảnh hồ sơ nhân sự vận hành
(UC-49, NGHIEP_VU.md mục 8.9) và ảnh giấy tờ (bằng lái, giấy khám sức
khỏe — UC-49/50). Xem quyết định dùng lại Cloudinary ở
NHAP_QUAN_LY_NHAN_SU.md mục 3.0 và cấu trúc bảng ở database_quanLyNhanSu.md
mục 1/2.

Service hạ tầng (gọi dịch vụ ngoài) — không thuộc Repository, đặt ở
services/ theo đúng ARCHITECTURE.md mục 2 (cùng nhóm với email_service.py).
File này CHỈ lo việc kỹ thuật (tải lên/sinh URL xem/xóa) — không tự quyết
định khi nào được phép upload, ảnh của ai, hay ghi nhật ký: những việc đó
thuộc về Service nghiệp vụ gọi tới đây (VD ho_so_nhan_su_service.py, chưa
viết), đúng nguyên tắc tách lớp của dự án.

Quan trọng — lưu `public_id`, KHÔNG lưu URL cố định vào DB: ảnh tải lên
bằng delivery kiểu `authenticated` (Cloudinary bắt buộc URL có chữ ký mới
xem được, không phải URL public ai đoán cũng ra) — hợp với dữ liệu nhạy
cảm như CCCD/giấy tờ. Vì vậy:
  - `nhan_su_van_hanh.anh_ho_so` / `giay_to_nhan_su.anh_giay_to` nên lưu
    `public_id` mà tai_anh_len() trả về, KHÔNG lưu URL.
  - Mỗi lần cần hiển thị ảnh (VD trả về cho frontend), gọi lay_url_xem()
    để lấy URL có chữ ký — không cache/lưu lại URL này.
"""

import uuid

import cloudinary
import cloudinary.uploader
import cloudinary.utils

from app.config import CLOUDINARY_URL

cloudinary.config(cloudinary_url=CLOUDINARY_URL)

# Thư mục trên Cloudinary — tách riêng ảnh chân dung và ảnh giấy tờ cho dễ quản lý,
# không liên quan tới cấu trúc bảng trong DB.
THU_MUC_ANH_HO_SO = "nha_xe/nhan_su/ho_so"
THU_MUC_ANH_GIAY_TO = "nha_xe/nhan_su/giay_to"


def tai_anh_len(du_lieu_anh: bytes, thu_muc: str) -> str | None:
    """Upload 1 ảnh lên Cloudinary, trả về `public_id` để Service nghiệp vụ
    lưu vào DB (KHÔNG trả URL — xem docstring đầu file).

    `du_lieu_anh`: nội dung file ảnh dạng bytes (đọc từ UploadFile của
    FastAPI, VD `await file.read()`).
    `thu_muc`: 1 trong 2 hằng số THU_MUC_ANH_* ở trên.

    Trả `None` nếu upload thất bại — Service gọi hàm này tự quyết định có
    raise LoiHeThong hay không (giống cách mat_khau_service.py xử lý kết
    quả bool của gui_mail() ở email_service.py), file này không tự raise
    lỗi nghiệp vụ.
    """
    try:
        ket_qua = cloudinary.uploader.upload(
            du_lieu_anh,
            folder=thu_muc,
            public_id=str(uuid.uuid4()),  # tự sinh — không dùng tên file gốc (tránh trùng tên, ký tự lạ)
            type="authenticated",  # bắt buộc có chữ ký mới xem được — dữ liệu nhạy cảm
            resource_type="image",
        )
        return ket_qua["public_id"]
    except Exception as loi:
        print(f"Lỗi upload ảnh lên Cloudinary: {loi}")
        return None


def lay_url_xem(public_id: str) -> str:
    """Sinh URL có chữ ký để xem 1 ảnh đã upload — Cloudinary chỉ trả ảnh
    khi chữ ký đúng, chặn được việc đoán mò URL ngẫu nhiên.

    Lưu ý: chữ ký này KHÔNG tự hết hạn theo thời gian (khác cơ chế OTP/JWT
    đang dùng trong dự án). Muốn có URL tự hết hạn thật cần bật thêm tính
    năng "Token-based authentication" riêng của Cloudinary (cấu hình thêm
    ở Dashboard, chưa kiểm tra có nằm trong free tier hay không) — CHƯA
    làm ở bản này, để mức bảo vệ đơn giản (chữ ký cố định) là đủ cho quy
    mô BTL.
    """
    url, _ = cloudinary.utils.cloudinary_url(
        public_id,
        type="authenticated",
        resource_type="image",
        sign_url=True,
    )
    return url


def xoa_anh(public_id: str) -> bool:
    """Xóa 1 ảnh khỏi Cloudinary theo `public_id` — gọi khi nhân sự thay
    ảnh mới (VD gia hạn giấy tờ, ảnh cũ không còn cần giữ) để tránh tồn
    rác trên free tier.

    Trả `False` nếu xóa thất bại — Service gọi tự quyết định có coi là
    lỗi nghiêm trọng hay bỏ qua (ảnh rác không ảnh hưởng vận hành ngay).
    """
    try:
        ket_qua = cloudinary.uploader.destroy(public_id, type="authenticated", resource_type="image")
        return ket_qua.get("result") == "ok"
    except Exception as loi:
        print(f"Lỗi xóa ảnh trên Cloudinary: {loi}")
        return False
