"""Gửi email OTP qua Gmail SMTP — kế thừa nguyên cơ chế bản v1
(GiaoThongAnToan_API/routes/quen_mat_khau.py, hàm gui_mail), đã chạy ổn
định (NGHIEP_VU.md mục 2.1). Khác v1 duy nhất: đọc cấu hình qua config.py
(app/config.py) thay vì gọi os.getenv trực tiếp trong file này.

Service hạ tầng (gọi dịch vụ ngoài) — không thuộc Repository, đặt ở
services/ theo đúng ARCHITECTURE.md mục 2.
"""

import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


class _SMTPQuaIPv4(smtplib.SMTP):
    """Render free tier không hỗ trợ egress IPv6 — smtplib mặc định để
    socket.create_connection() tự chọn địa chỉ DNS trả về, ưu tiên IPv6
    nếu có, gây lỗi "[Errno 101] Network is unreachable" khi gọi Gmail
    SMTP. Ghi đè _get_socket() để chỉ phân giải + kết nối qua IPv4, vẫn
    giữ nguyên self._host (= "smtp.gmail.com") cho STARTTLS xác thực
    đúng tên miền trên chứng chỉ TLS (không dùng thẳng IP)."""

    def _get_socket(self, host, port, timeout):
        dia_chi_ipv4 = socket.gethostbyname(host)
        return socket.create_connection((dia_chi_ipv4, port), timeout, self.source_address)


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

        with _SMTPQuaIPv4(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as loi:
        print(f"Lỗi gửi mail: {loi}")
        return False
