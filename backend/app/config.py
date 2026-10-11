import hashlib
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "").split(",") if o]

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Cloudinary — lưu ảnh hồ sơ nhân sự vận hành (UC-49, NGHIEP_VU.md mục 8.9,
# xem NHAP_QUAN_LY_NHAN_SU.md mục 3.0). SDK Cloudinary tự đọc biến này nếu
# gọi cloudinary.config() không tham số, nhưng khai báo lại ở đây cho nhất
# quán với mọi biến môi trường khác trong file này (đọc qua config.py,
# không gọi os.getenv rải rác trong services/) — xem luu_tru_anh_service.py.
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")
# Brevo API (HTTPS) — gửi mã OTP, thay cho SMTP thô sau khi phát hiện
# Render free tier + Gmail chặn/timeout kết nối SMTP trực tiếp từ IP cloud
# (xem lịch sử commit email_service.py).
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")

# Đặt vé online (UC-05, NGHIEP_VU.md mục 3.4, 6, 9) — mặc định theo tài liệu; chưa có bảng cấu hình tham số
# nên để hằng số ở đây (quan_ly chưa chỉnh được qua giao diện).
HAN_GIU_TAM_PHUT = 10  # ghế khóa từ lúc khách bấm "Tiếp tục" (sau khi chọn điểm đón/trả) tới lúc chốt cách thanh toán; hết thì tự nhả ghế
HAN_THANH_TOAN_NGAY_PHUT = 5  # mục 6 — tính từ lúc tới màn thanh toán, chỉ cho "thanh toán ngay"
NGUONG_GIA_TRI_DAT_COC = 600000  # mục 3.4 — lô ≥2 vé có tổng giá trị > ngưỡng này thì bắt buộc đặt cọc online
TY_LE_DAT_COC = 0.5
X_PHUT_CHOT_LEN_XE = 5  # mục 7/8.2 điểm 6 — mốc chốt hủy giữ chỗ = giờ tại điểm đón − X phút (cùng giá trị job no-show)
SO_GHE_TOI_DA_MOI_LAN_DAT = 10
HAN_DE_DUNG_TRE_IPN_PHUT = 2  # giữ vé thêm ngần này phút sau hạn của cổng thanh toán để IPN (đi qua mạng) tới kịp
NHAC_TRUOC_GIO_DON_PHUT = 120  # nhắc khách "sắp đến giờ đi" khi còn chừng này phút tới giờ đón (NGHIEP_VU.md mục 8.1 điểm 4)

# Cổng thanh toán VNPay (UC-05 nhánh "thanh toán ngay", NGHIEP_VU.md mục 6).
#   VNPAY_CHE_DO = "gia_lap" (mặc định): cổng giả lập tự làm để demo — vẫn ký/kiểm tra chữ ký HMAC-SHA512 và gọi IPN
#                  đúng như VNPay; trang thanh toán giả nằm ở frontend/khach-hang/cong-thanh-toan-gia.html.
#   VNPAY_CHE_DO = "sandbox": dùng VNPay sandbox thật — khi đó PHẢI đặt VNPAY_TMN_CODE + VNPAY_HASH_SECRET (lấy qua
#                  email sau khi đăng ký sandbox.vnpayment.vn/devreg) trong biến môi trường, KHÔNG đưa vào git.
# (`or` thay cho tham số mặc định của getenv vì .env.example để sẵn các dòng `VNPAY_...=` rỗng — chuỗi rỗng coi như chưa đặt)
# (`or` thay cho tham số mặc định của getenv vì .env.example để sẵn các dòng `VNPAY_...=` rỗng — chuỗi rỗng coi như chưa đặt)
VNPAY_CHE_DO = os.getenv("VNPAY_CHE_DO") or "gia_lap"
VNPAY_TMN_CODE = os.getenv("VNPAY_TMN_CODE") or "DEMOTMN1"
VNPAY_URL = os.getenv("VNPAY_URL") or "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
# API truy vấn giao dịch (querydr): backend tự hỏi VNPay kết quả, dùng khi IPN không tới được (VD sandbox chưa khai báo được IPN)
VNPAY_API_URL = os.getenv("VNPAY_API_URL") or "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
# Chế độ giả lập không có khóa thật: sinh khóa từ JWT_SECRET để không phải đặt thêm biến và không có khóa cố định trong code.
VNPAY_HASH_SECRET = os.getenv("VNPAY_HASH_SECRET") or hashlib.sha256(((JWT_SECRET or "") + "|vnpay-gia-lap").encode()).hexdigest()
