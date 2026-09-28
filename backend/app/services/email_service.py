"""Gửi email OTP — trước dùng Gmail SMTP thô (kế thừa bản v1), đã đổi sang
Brevo API (HTTPS) vì SMTP thô bị chặn/timeout khi deploy lên Render free
tier: Render không hỗ trợ egress IPv6 ("Network is unreachable" khi DNS
Gmail trả về địa chỉ IPv6), và sau khi ép IPv4 vẫn bị Google âm thầm
timeout kết nối SMTP trực tiếp từ dải IP cloud/hosting (biện pháp chống
spam của Google, không liên quan gì tới code). Gửi qua HTTPS (cổng 443)
tránh được cả 2 vấn đề trên vì chính app cũng chạy HTTPS.

Service hạ tầng (gọi dịch vụ ngoài) — không thuộc Repository, đặt ở
services/ theo đúng ARCHITECTURE.md mục 2.
"""

import json
import urllib.error
import urllib.request

from app.config import BREVO_API_KEY, BREVO_SENDER_EMAIL

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def gui_mail(den: str, ma_xac_nhan: str, tieu_de: str = "Mã xác nhận") -> bool:
    noi_dung = f"""
    <h2>Hệ thống Quản lý Nhà xe Khách</h2>
    <p>Mã xác nhận của bạn là:</p>
    <h1 style="color: #E24B4A; letter-spacing: 8px;">{ma_xac_nhan}</h1>
    <p>Mã có hiệu lực trong <strong>1 phút</strong>.</p>
    <p>Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.</p>
    """

    payload = json.dumps(
        {
            "sender": {"email": BREVO_SENDER_EMAIL, "name": "GoBus"},
            "to": [{"email": den}],
            "subject": tieu_de,
            "htmlContent": noi_dung,
        }
    ).encode("utf-8")

    yeu_cau = urllib.request.Request(
        BREVO_API_URL,
        data=payload,
        method="POST",
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(yeu_cau, timeout=15) as res:
            return 200 <= res.status < 300
    except urllib.error.HTTPError as loi:
        # Brevo tra ve chi tiet loi (VD sender chua xac thuc) trong body
        print(f"Lỗi gửi mail: HTTP {loi.code} - {loi.read().decode(errors='replace')}")
        return False
    except Exception as loi:
        print(f"Lỗi gửi mail: {loi}")
        return False
