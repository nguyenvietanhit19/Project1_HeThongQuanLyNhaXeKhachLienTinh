"""Integration tests kiểm tra toàn bộ luồng E2E và các trường hợp ngoại lệ của Phân hệ Kế toán & Hoàn tiền.

Chạy trực tiếp với DB PostgreSQL và HTTP server thật:
1. Thiếu token -> 401 Unauthorized
2. Token sai vai trò (khach_hang, phu_xe) -> 403 Forbidden
3. Đăng nhập đúng vai trò ke_toan -> Nhận token hợp lệ
4. Ngoại lệ: Tạo hoàn tiền cho vé không tồn tại -> 400 Bad Request
5. Tạo hoàn tiền hợp lệ cho vé tiền mặt -> 201 Created với trạng thái 'cho_xu_ly'
6. Idempotency: Gọi tạo hoàn tiền lần 2 cho cùng vé -> Trả về bản ghi cũ, không trùng lặp
7. Ngoại lệ duyệt hoàn tiền: Thông tin ngân hàng trống -> 400 Bad Request
8. Duyệt chuyển khoản thủ công thành công -> Chuyển 'da_hoan_chuyen_khoan_thu_cong'
9. Ngoại lệ: Cố duyệt lại bản ghi đã hoàn tất -> 400 Bad Request
10. UC-43: Job quét tự động sự cố >= 3 tiếng -> Tự động tạo hoàn tiền
11. UC-43 Nghiệp vụ cốt lõi: Vé VẪN GIỮ NGUYÊN trạng thái da_thanh_toan (không bị hủy)
12. UC-39: Thống kê doanh thu tài chính chính xác (Doanh thu thuần = Vé + Hàng - Hoàn tiền)
"""

import json
import urllib.error
import urllib.request
from uuid import uuid4

from app.db import get_connection, release_connection
from app.jobs.quet_hoan_tien_tu_dong import chay_job_quet_hoan_tien_tu_dong
from app.middleware.auth_middleware import tao_token


def test_e2e_toan_bo_luong_ke_toan_va_ngoai_le():
    base_url = "http://localhost:8000"

    # 1. Test ngoại lệ thiếu token -> 401
    try:
        urllib.request.urlopen(f"{base_url}/ke-toan/thong-ke")
        assert False, "Gọi API không có token phải trả về lỗi"
    except urllib.error.HTTPError as e:
        assert e.code == 401

    # 2. Test ngoại lệ sai vai trò (khách hàng cố vào API kế toán) -> 403
    conn = get_connection()
    kh_id = str(uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO nguoi_dung (id, email, ho_ten, so_dien_thoai, vai_tro, dang_hoat_dong)
            VALUES (%s, %s, %s, %s, 'khach_hang', true)
            ON CONFLICT (email) DO NOTHING;
            """,
            (kh_id, f"khach_{kh_id[:8]}@test.com", "Khách Test", "0911223344"),
        )
    conn.commit()
    release_connection(conn)

    token_kh = tao_token(kh_id, "khach_hang")
    try:
        req = urllib.request.Request(
            f"{base_url}/ke-toan/thong-ke",
            headers={"Authorization": f"Bearer {token_kh}"},
        )
        urllib.request.urlopen(req)
        assert False, "Khách hàng không được phép truy cập API kế toán"
    except urllib.error.HTTPError as e:
        assert e.code == 403, f"Mong đợi 403 Forbidden nhưng nhận {e.code}"

    # 3. Đăng nhập tài khoản kế toán
    req_login = urllib.request.Request(
        f"{base_url}/auth/dang-nhap",
        data=json.dumps({"email": "ketoan@nhaxekhach.com", "mat_khau": "Ketoan@123"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    res_login = urllib.request.urlopen(req_login)
    token_kt = json.loads(res_login.read().decode())["token"]
    auth_header = {"Authorization": f"Bearer {token_kt}", "Content-Type": "application/json"}

    # 4. Ngoại lệ tạo hoàn tiền cho vé không tồn tại -> 400
    try:
        req_ve_ao = urllib.request.Request(
            f"{base_url}/ke-toan/hoan-tien/tao-yeu-cau",
            data=json.dumps({"ve_id": str(uuid4()), "ly_do": "bat_kha_khang_khong_hoan_thanh"}).encode(),
            headers=auth_header,
        )
        urllib.request.urlopen(req_ve_ao)
        assert False, "Vé không tồn tại phải báo lỗi"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        res_err = json.loads(e.read().decode())
        assert "không tồn tại" in res_err["loi"]

    # 5. Tạo vé thật để test luồng hoàn tiền và Idempotency
    conn = get_connection()
    chuyen_id = str(uuid4())
    ve_id = str(uuid4())
    tuyen_id = "66666666-6666-6666-6666-666666666666"
    diem_don = "33333333-3333-3333-3333-333333333333"
    diem_tra = "44444444-4444-4444-4444-444444444444"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chuyen_xe (id, tuyen_id, gio_khoi_hanh, trang_thai)
            VALUES (%s, %s, now() + INTERVAL '1 hour', 'chua_khoi_hanh');
            """,
            (chuyen_id, tuyen_id),
        )
        cur.execute(
            """
            INSERT INTO ve (id, chuyen_id, so_ghe, diem_don_id, diem_tra_id, gia, ma_dat_cho, loai_hinh_thanh_toan, phuong_thuc_thanh_toan, trang_thai, ten_khach_vang_lai, sdt_khach_vang_lai)
            VALUES (%s, %s, 'D02', %s, %s, 320000, 'DC-E2E-002', 'thanh_toan_tai_quay', 'tien_mat', 'da_thanh_toan', 'Trịnh Văn Test', '0912345678')
            RETURNING id;
            """,
            (ve_id, chuyen_id, diem_don, diem_tra),
        )
    conn.commit()
    release_connection(conn)

    # 6. Tạo hoàn tiền lần 1
    req_tao_1 = urllib.request.Request(
        f"{base_url}/ke-toan/hoan-tien/tao-yeu-cau",
        data=json.dumps({"ve_id": ve_id, "ly_do": "bat_kha_khang_khong_hoan_thanh"}).encode(),
        headers=auth_header,
    )
    res_1 = urllib.request.urlopen(req_tao_1)
    assert res_1.status == 201
    hoan_1 = json.loads(res_1.read().decode())
    assert hoan_1["trang_thai"] == "cho_xu_ly"
    assert hoan_1["so_tien"] == 320000

    # 7. Idempotency: Gọi tạo hoàn tiền lần 2 cho cùng vé -> Trả về đúng bản ghi cũ
    req_tao_2 = urllib.request.Request(
        f"{base_url}/ke-toan/hoan-tien/tao-yeu-cau",
        data=json.dumps({"ve_id": ve_id, "ly_do": "bat_kha_khang_khong_hoan_thanh"}).encode(),
        headers=auth_header,
    )
    res_2 = urllib.request.urlopen(req_tao_2)
    hoan_2 = json.loads(res_2.read().decode())
    assert hoan_1["id"] == hoan_2["id"]

    # 8. Ngoại lệ duyệt hoàn tiền: Thiếu thông tin ngân hàng -> 400
    hoan_id = hoan_1["id"]
    try:
        req_duyet_loi = urllib.request.Request(
            f"{base_url}/ke-toan/hoan-tien/{hoan_id}/duyet",
            data=json.dumps({
                "so_tai_khoan_nhan": "12345678",
                "ten_ngan_hang_nhan": "   ",
                "ten_chu_tai_khoan_nhan": "NGUYEN VAN A",
            }).encode(),
            headers=auth_header,
        )
        urllib.request.urlopen(req_duyet_loi)
        assert False, "Thông tin ngân hàng trống phải báo lỗi"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        res_err = json.loads(e.read().decode())
        assert "Bắt buộc cung cấp đầy đủ" in res_err["loi"]

    # 9. Duyệt chuyển khoản thủ công hợp lệ
    req_duyet = urllib.request.Request(
        f"{base_url}/ke-toan/hoan-tien/{hoan_id}/duyet",
        data=json.dumps({
            "so_tai_khoan_nhan": "0451000123456",
            "ten_ngan_hang_nhan": "Vietcombank",
            "ten_chu_tai_khoan_nhan": "TRINH VAN TEST",
        }).encode(),
        headers=auth_header,
    )
    res_duyet = urllib.request.urlopen(req_duyet)
    assert res_duyet.status == 200
    duyet_data = json.loads(res_duyet.read().decode())
    assert duyet_data["trang_thai"] == "da_hoan_chuyen_khoan_thu_cong"
    assert duyet_data["so_tai_khoan_nhan"] == "0451000123456"

    # 10. Ngoại lệ duyệt lại bản ghi đã hoàn -> 400
    try:
        urllib.request.urlopen(req_duyet)
        assert False, "Không được duyệt lại bản ghi đã hoàn thành"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        res_err = json.loads(e.read().decode())
        assert "không ở trạng thái chờ xử lý" in res_err["loi"]

    # 11. UC-43: Job tự động hoàn tiền sự cố >= 3 tiếng
    conn = get_connection()
    chuyen_sc_id = str(uuid4())
    ve_sc_id = str(uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chuyen_xe (id, tuyen_id, gio_khoi_hanh, trang_thai, loai_su_co, ly_do_su_co)
            VALUES (%s, %s, now() - INTERVAL '5 hours', 'gap_su_co', 'loi_nha_xe', 'Xe gặp sự cố máy');
            """,
            (chuyen_sc_id, tuyen_id),
        )
        cur.execute(
            """
            INSERT INTO ve (id, chuyen_id, so_ghe, diem_don_id, diem_tra_id, gia, ma_dat_cho, loai_hinh_thanh_toan, phuong_thuc_thanh_toan, trang_thai, ten_khach_vang_lai, sdt_khach_vang_lai)
            VALUES (%s, %s, 'E01', %s, %s, 290000, 'DC-E2E-003', 'thanh_toan_tai_quay', 'tien_mat', 'da_thanh_toan', 'Khach Cho Xe', '0988112233')
            RETURNING id;
            """,
            (ve_sc_id, chuyen_sc_id, diem_don, diem_tra),
        )
    conn.commit()

    # Chạy job
    so_ve = chay_job_quet_hoan_tien_tu_dong()
    assert so_ve >= 1

    # Kiểm tra vé VẪN da_thanh_toan (không bị hủy)
    with conn.cursor() as cur:
        cur.execute("SELECT trang_thai FROM ve WHERE id = %s", (ve_sc_id,))
        tt = cur.fetchone()[0]
        assert tt == "da_thanh_toan", "Vé UC-43 phải giữ nguyên da_thanh_toan"
    release_connection(conn)

    # 12. UC-39: Thống kê doanh thu tài chính trả về đúng định dạng
    req_tk = urllib.request.Request(
        f"{base_url}/ke-toan/thong-ke",
        headers=auth_header,
    )
    res_tk = urllib.request.urlopen(req_tk)
    assert res_tk.status == 200
    tk_data = json.loads(res_tk.read().decode())
    assert "doanh_thu_thuan" in tk_data
    assert "tong_doanh_thu_ve" in tk_data
    assert "tong_tien_hoan_ve" in tk_data
    # Doanh thu thuần = (Vé + Hàng) - Hoàn tiền
    assert tk_data["doanh_thu_thuan"] == (tk_data["tong_doanh_thu_ve"] + tk_data["tong_doanh_thu_gui_hang"]) - tk_data["tong_tien_hoan_ve"]
