"""Kiểm tra + chuẩn hóa số điện thoại Việt Nam — dùng cho đăng ký và sửa hồ sơ khách hàng.

SĐT chỉ là thông tin hồ sơ (không dùng đăng nhập, không xác minh SMS — NGHIEP_VU.md mục 2.1) nhưng nhân viên
quầy vé tra vé theo SĐT (mục 8.4) nên phải lưu 1 dạng thống nhất: bỏ khoảng trắng/dấu chấm/gạch/ngoặc, đổi đầu
`+84`/`84` thành `0`. Hợp lệ khi là:
  - số di động: 0 + 1 trong các đầu 3/5/7/8/9 + 8 chữ số (đủ 10 số), VD 0912345678
  - số bàn: 02 + 9 chữ số (đủ 11 số, gồm mã vùng), VD 02438251234

QUAN TRỌNG: quy tắc này phải khớp 100% với frontend/shared/so-dien-thoai.js — sửa 1 bên phải sửa bên kia
(backend vẫn kiểm tra lại, frontend chỉ để báo lỗi sớm).
"""

import re

from app.utils.loi import GiaTriLoi

_DI_DONG = re.compile(r"0[35789]\d{8}")
_SO_BAN = re.compile(r"02\d{9}")


def chuan_hoa_so_dien_thoai(so: str | None) -> str:
    gon = re.sub(r"[\s.\-()]", "", so or "")
    if not gon:
        raise GiaTriLoi("Vui lòng nhập số điện thoại")
    if gon.startswith("+84"):
        gon = "0" + gon[3:]
    elif gon.startswith("84") and len(gon) in (11, 12):
        gon = "0" + gon[2:]
    if not (_DI_DONG.fullmatch(gon) or _SO_BAN.fullmatch(gon)):
        raise GiaTriLoi("Số điện thoại không hợp lệ — nhập số di động 10 chữ số, VD 0912345678")
    return gon
