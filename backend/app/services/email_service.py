"""Gửi email OTP qua Gmail SMTP — kế thừa nguyên cơ chế bản v1
(GiaoThongAnToan_API/routes/quen_mat_khau.py, hàm gui_mail), đã chạy ổn
định (NGHIEP_VU.md mục 2.1). Khác v1 duy nhất: đọc cấu hình qua config.py
(app/config.py) thay vì gọi os.getenv trực tiếp trong file này.

Service hạ tầng (gọi dịch vụ ngoài) — không thuộc Repository, đặt ở
services/ theo đúng ARCHITECTURE.md mục 2.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


def gui_mail(den: str, ma_xac_nhan: str, tieu_de: str = "Mã xác nhận") -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = den
        msg["Subject"] = tieu_de

        noi_dung = f"""
        <h2>Hệ thống Quản lý Nhà xe Khách</h2>
        <p>Mã xác nhận của bạn là:</p>
        <h1 style="color: #E24B4A; letter-spacing: 8px;">{ma_xac_nhan}</h1>
        <p>Mã có hiệu lực trong <strong>1 phút</strong>.</p>
        <p>Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.</p>
        """
        msg.attach(MIMEText(noi_dung, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as loi:
        print(f"Lỗi gửi mail: {loi}")
        return False
