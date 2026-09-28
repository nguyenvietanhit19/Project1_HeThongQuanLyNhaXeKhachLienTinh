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

# Cloudinary — lưu ảnh hồ sơ nhân sự vận hành (UC-47, NGHIEP_VU.md mục 8.9,
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
