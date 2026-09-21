"""Unit tests cho phân hệ Kế toán & Hoàn tiền — hoan_tien_service.py.
"""Unit tests toàn diện cho phân hệ Kế toán & Hoàn tiền — hoan_tien_service.py.

Kiểm tra:
- UC-21: Tự động hoàn tiền khi hủy chuyến vì sự cố khách quan (vé da_huy)
- UC-22: Kế toán duyệt chuyển khoản thủ công (lưu vết ngân hàng)
- UC-43: Tự động hoàn tiền khi sự cố lỗi nhà xe >= 3 tiếng (vé VẪN da_thanh_toan)
- UC-39: Báo cáo tài chính doanh thu kế toán
- Idempotency & xử lý lỗi nghiệp vụ
Bao gồm toàn bộ kịch bản chuẩn và các trường hợp ngoại lệ (Edge Cases):
- TC-01: Vé online (VNPay) tự động hoàn qua cổng thanh toán
- TC-02: Vé tiền mặt đưa vào hàng đợi chờ Kế toán duyệt thủ công
- TC-03: Cổng thanh toán online báo lỗi -> Fallback an toàn sang chờ xử lý thủ công
- TC-04: Ngoại lệ vé không tồn tại trong hệ thống
- TC-05: Ngoại lệ hoàn trùng lặp (Idempotency) -> Trả về bản ghi đã tạo, không tạo mới
- TC-06: Hoàn số tiền tùy chỉnh vs mặc định 100% giá vé
- TC-07: UC-21 Hủy chuyến do sự cố khách quan -> vé sang da_huy và hoàn 100%
- TC-08: UC-21 Chuyến không có vé nào -> Xử lý êm, trả về danh sách rỗng
- TC-09: UC-22 Kế toán duyệt chuyển khoản thủ công thành công, lưu vết ngân hàng
- TC-10: UC-22 Ngoại lệ bản ghi hoàn tiền không tồn tại
- TC-11: UC-22 Ngoại lệ duyệt lại bản ghi không ở trạng thái 'cho_xu_ly'
- TC-12: UC-22 Ngoại lệ thiếu thông tin STK, tên ngân hàng hoặc tên chủ tài khoản
- TC-13: UC-22 Ngoại lệ cập nhật CSDL thất bại
- TC-14: UC-43 Tự động hoàn tiền khi sự cố lỗi nhà xe >= 3 tiếng
- TC-15: UC-43 Nghiệp vụ cốt lõi: Vé VẪN GIỮ NGUYÊN da_thanh_toan (không bị hủy)
- TC-16: UC-43 Job chạy lại lần 2 không hoàn trùng vé đã được xử lý
- TC-17: UC-43 Không có chuyến nào gặp sự cố -> trả về 0 vé hoàn
- TC-18: UC-39 Thống kê doanh thu tài chính tính toán đúng Doanh thu thuần
- TC-19: UC-39 Thống kê theo khoảng thời gian tu_ngay, den_ngay
"""

from unittest.mock import patch, MagicMock
from uuid import uuid4
import pytest

from app.services import hoan_tien_service
from app.utils.loi import GiaTriLoi


@pytest.fixture
def mau_ve_tien_mat():
    return {
        "id": str(uuid4()),
        "chuyen_id": str(uuid4()),
        "so_ghe": "A01",
        "gia": 250000,
        "ma_dat_cho": "DAT001",
        "phuong_thuc_thanh_toan": "tien_mat",
        "ma_giao_dich_cong_thanh_toan": None,
        "trang_thai": "da_thanh_toan",
        "khach_hang_id": str(uuid4()),
    }


@pytest.fixture
def mau_ve_vnpay():
    return {
        "id": str(uuid4()),
        "chuyen_id": str(uuid4()),
        "so_ghe": "B02",
        "gia": 300000,
        "ma_dat_cho": "DAT002",
        "phuong_thuc_thanh_toan": "chuyen_khoan",
        "ma_giao_dich_cong_thanh_toan": "VNP12345678",
        "trang_thai": "da_thanh_toan",
        "khach_hang_id": str(uuid4()),
    }


# ====================================================================
# 1. Kiểm tra tạo hoàn tiền độc lập & cổng online
# 1. Kiểm tra tạo hoàn tiền độc lập & cổng online (Core Engine)
# ====================================================================

@patch("app.services.hoan_tien_service.repo.tim_ve_theo_id")
def test_tao_hoan_tien_ve_khong_ton_tai(mock_tim_ve):
def test_tc04_tao_hoan_tien_ve_khong_ton_tai(mock_tim_ve):
    """TC-04: Vé không tồn tại trong DB -> Báo lỗi GiaTriLoi."""
    mock_tim_ve.return_value = None
    with pytest.raises(GiaTriLoi) as exc_info:
        hoan_tien_service.tao_hoan_tien("ve-khong-ton-tai", "bat_kha_khang_khong_hoan_thanh")
    assert "không tồn tại" in str(exc_info.value)


@patch("app.services.hoan_tien_service.repo.tim_ve_theo_id")
@patch("app.services.hoan_tien_service.repo.tim_theo_ve_id")
def test_tao_hoan_tien_idempotent(mock_tim_hoan, mock_tim_ve, mau_ve_tien_mat):
    """Nếu đã có bản ghi hoàn tiền trước đó, trả về bản ghi cũ tránh hoàn tiền 2 lần."""
def test_tc05_tao_hoan_tien_idempotent(mock_tim_hoan, mock_tim_ve, mau_ve_tien_mat):
    """TC-05: Nếu đã có bản ghi hoàn tiền trước đó, trả về bản ghi cũ tránh hoàn trùng lặp."""
    mock_tim_ve.return_value = mau_ve_tien_mat
    ban_ghi_da_co = {
        "id": str(uuid4()),
        "ve_id": mau_ve_tien_mat["id"],
        "so_tien": 250000,
        "trang_thai": "cho_xu_ly",
    }
    mock_tim_hoan.return_value = ban_ghi_da_co

    ket_qua = hoan_tien_service.tao_hoan_tien(mau_ve_tien_mat["id"], "loi_nha_xe_giua_duong")
    assert ket_qua["id"] == ban_ghi_da_co["id"]


@patch("app.services.hoan_tien_service.repo.tim_ve_theo_id")
@patch("app.services.hoan_tien_service.repo.tim_theo_ve_id")
@patch("app.services.hoan_tien_service.repo.tao_hoan_tien")
def test_tao_hoan_tien_vnpay_tu_dong(mock_tao_hoan, mock_tim_hoan, mock_tim_ve, mau_ve_vnpay):
    """Khách trả online qua VNPay -> tự động hoàn qua cổng thanh toán."""
def test_tc01_tao_hoan_tien_vnpay_tu_dong(mock_tao_hoan, mock_tim_hoan, mock_tim_ve, mau_ve_vnpay):
    """TC-01: Khách trả online qua VNPay -> tự động hoàn qua cổng, sinh mã giao dịch hoàn."""
    mock_tim_ve.return_value = mau_ve_vnpay
    mock_tim_hoan.return_value = None
    mock_tao_hoan.side_effect = lambda **kwargs: kwargs

    ket_qua = hoan_tien_service.tao_hoan_tien(mau_ve_vnpay["id"], "bat_kha_khang_khong_hoan_thanh")
    assert ket_qua["trang_thai"] == "da_hoan_tu_dong"
    assert ket_qua["ma_giao_dich_hoan_tien"] is not None
    assert ket_qua["so_tien"] == 300000


@patch("app.services.hoan_tien_service.repo.tim_ve_theo_id")
@patch("app.services.hoan_tien_service.repo.tim_theo_ve_id")
@patch("app.services.hoan_tien_service.repo.tao_hoan_tien")
def test_tao_hoan_tien_tien_mat_cho_ke_toan(mock_tao_hoan, mock_tim_hoan, mock_tim_ve, mau_ve_tien_mat):
    """Khách trả tiền mặt -> chuyển trạng thái 'cho_xu_ly' để Kế toán gọi điện xin STK."""
def test_tc02_tao_hoan_tien_tien_mat_cho_ke_toan(mock_tao_hoan, mock_tim_hoan, mock_tim_ve, mau_ve_tien_mat):
    """TC-02: Khách trả tiền mặt -> chuyển trạng thái 'cho_xu_ly' để Kế toán gọi điện xin STK."""
    mock_tim_ve.return_value = mau_ve_tien_mat
    mock_tim_hoan.return_value = None
    mock_tao_hoan.side_effect = lambda **kwargs: kwargs

    ket_qua = hoan_tien_service.tao_hoan_tien(mau_ve_tien_mat["id"], "hoan_truoc_gio_chay")
    assert ket_qua["trang_thai"] == "cho_xu_ly"
    assert ket_qua["ma_giao_dich_hoan_tien"] is None
    assert ket_qua["so_tien"] == 250000


@patch("app.services.hoan_tien_service.repo.tim_ve_theo_id")
@patch("app.services.hoan_tien_service.repo.tim_theo_ve_id")
@patch("app.services.hoan_tien_service.repo.tao_hoan_tien")
def test_tc03_tao_hoan_tien_vnpay_that_bai_fallback_cho_xu_ly(mock_tao_hoan, mock_tim_hoan, mock_tim_ve):
    """TC-03: Vé online nhưng cổng thanh toán trả về lỗi -> Fallback sang 'cho_xu_ly' để Kế toán duyệt."""
    ve_loi = {
        "id": str(uuid4()),
        "gia": 400000,
        "phuong_thuc_thanh_toan": "chuyen_khoan",
        "ma_giao_dich_cong_thanh_toan": "FAIL_GATEWAY_TIMEOUT",
        "khach_hang_id": str(uuid4()),
    }
    mock_tim_ve.return_value = ve_loi
    mock_tim_hoan.return_value = None
    mock_tao_hoan.side_effect = lambda **kwargs: kwargs

    ket_qua = hoan_tien_service.tao_hoan_tien(ve_loi["id"], "loi_nha_xe_giua_duong")
    assert ket_qua["trang_thai"] == "cho_xu_ly"
    assert ket_qua["ma_giao_dich_hoan_tien"] is None


@patch("app.services.hoan_tien_service.repo.tim_ve_theo_id")
@patch("app.services.hoan_tien_service.repo.tim_theo_ve_id")
@patch("app.services.hoan_tien_service.repo.tao_hoan_tien")
def test_tc06_tao_hoan_tien_so_tien_tuy_chinh(mock_tao_hoan, mock_tim_hoan, mock_tim_ve, mau_ve_tien_mat):
    """TC-06: Hoàn số tiền tùy chỉnh khác giá vé."""
    mock_tim_ve.return_value = mau_ve_tien_mat
    mock_tim_hoan.return_value = None
    mock_tao_hoan.side_effect = lambda **kwargs: kwargs

    ket_qua = hoan_tien_service.tao_hoan_tien(mau_ve_tien_mat["id"], "loi_nha_xe_giua_duong", so_tien=180000)
    assert ket_qua["so_tien"] == 180000


# ====================================================================
# 2. UC-21: Hủy chuyến sự cố khách quan & Hoàn vé 100%
# ====================================================================

@patch("app.services.hoan_tien_service.repo.tim_ve_da_thanh_toan_theo_chuyen")
@patch("app.services.hoan_tien_service.repo.cap_nhat_ve_da_huy")
@patch("app.services.hoan_tien_service.tao_hoan_tien")
def test_xu_ly_hoan_tien_chuyen_bi_huy_uc21(mock_tao_hoan, mock_cap_nhat_huy, mock_tim_ve, mau_ve_tien_mat, mau_ve_vnpay):
    """UC-21: Mọi vé da_thanh_toan trên chuyến bị hủy đều chuyển sang da_huy và hoàn 100%."""
def test_tc07_xu_ly_hoan_tien_chuyen_bi_huy_uc21(mock_tao_hoan, mock_cap_nhat_huy, mock_tim_ve, mau_ve_tien_mat, mau_ve_vnpay):
    """TC-07: Mọi vé da_thanh_toan trên chuyến bị hủy đều chuyển sang da_huy và hoàn 100%."""
    mock_tim_ve.return_value = [mau_ve_tien_mat, mau_ve_vnpay]
    mock_tao_hoan.side_effect = lambda ve_id, ly_do, so_tien: {"ve_id": ve_id, "ly_do": ly_do, "so_tien": so_tien}

    chuyen_id = str(uuid4())
    ds_hoan = hoan_tien_service.xu_ly_hoan_tien_chuyen_bi_huy(chuyen_id)

    assert len(ds_hoan) == 2
    assert mock_cap_nhat_huy.call_count == 2
    for item in ds_hoan:
        assert item["ly_do"] == "bat_kha_khang_khong_hoan_thanh"


@patch("app.services.hoan_tien_service.repo.tim_ve_da_thanh_toan_theo_chuyen")
@patch("app.services.hoan_tien_service.repo.cap_nhat_ve_da_huy")
@patch("app.services.hoan_tien_service.tao_hoan_tien")
def test_tc08_xu_ly_hoan_tien_chuyen_rong_uc21(mock_tao_hoan, mock_cap_nhat_huy, mock_tim_ve):
    """TC-08: Chuyến không có vé nào -> Trả về mảng rỗng an toàn."""
    mock_tim_ve.return_value = []
    chuyen_id = str(uuid4())
    ds_hoan = hoan_tien_service.xu_ly_hoan_tien_chuyen_bi_huy(chuyen_id)

    assert len(ds_hoan) == 0
    mock_cap_nhat_huy.assert_not_called()
    mock_tao_hoan.assert_not_called()


# ====================================================================
# 3. UC-22: Kế toán duyệt chuyển khoản thủ công
# ====================================================================

@patch("app.services.hoan_tien_service.repo.tim_theo_id")
@patch("app.services.hoan_tien_service.repo.cap_nhat_chuyen_khoan_thu_cong")
@patch("app.services.hoan_tien_service.repo.tim_ve_theo_id")
def test_duyet_hoan_tien_thu_cong_thanh_cong(mock_tim_ve, mock_cap_nhat, mock_tim_hoan):
def test_tc09_duyet_hoan_tien_thu_cong_thanh_cong(mock_tim_ve, mock_cap_nhat, mock_tim_hoan):
    """TC-09: Duyệt chuyển khoản thủ công thành công kèm lưu vết đối soát ngân hàng."""
    hoan_id = str(uuid4())
    nhan_vien_id = str(uuid4())
    mock_tim_hoan.return_value = {
        "id": hoan_id,
        "ve_id": str(uuid4()),
        "so_tien": 500000,
        "trang_thai": "cho_xu_ly",
    }
    mock_cap_nhat.return_value = {
        "id": hoan_id,
        "trang_thai": "da_hoan_chuyen_khoan_thu_cong",
        "so_tai_khoan_nhan": "123456789",
        "ten_ngan_hang_nhan": "Vietcombank",
        "ten_chu_tai_khoan_nhan": "NGUYEN VAN A",
    }
    mock_tim_ve.return_value = {"khach_hang_id": str(uuid4())}

    thong_tin_nhan = {
        "so_tai_khoan_nhan": "123456789",
        "ten_ngan_hang_nhan": "Vietcombank",
        "ten_chu_tai_khoan_nhan": "NGUYEN VAN A",
    }
    ket_qua = hoan_tien_service.duyet_hoan_tien_thu_cong(hoan_id, nhan_vien_id, thong_tin_nhan)

    assert ket_qua["trang_thai"] == "da_hoan_chuyen_khoan_thu_cong"
    assert ket_qua["so_tai_khoan_nhan"] == "123456789"


@patch("app.services.hoan_tien_service.repo.tim_theo_id")
def test_duyet_hoan_tien_thu_cong_sai_trang_thai(mock_tim_hoan):
    """Khoản tiền đã hoàn tự động hoặc đã duyệt trước đó thì không được duyệt lại."""
def test_tc10_duyet_hoan_tien_thu_cong_khong_ton_tai(mock_tim_hoan):
    """TC-10: ID hoàn tiền không có trong hệ thống -> Báo lỗi GiaTriLoi."""
    mock_tim_hoan.return_value = None
    with pytest.raises(GiaTriLoi) as exc_info:
        hoan_tien_service.duyet_hoan_tien_thu_cong(
            str(uuid4()),
            str(uuid4()),
            {
                "so_tai_khoan_nhan": "12345",
                "ten_ngan_hang_nhan": "MB",
                "ten_chu_tai_khoan_nhan": "A",
            },
        )
    assert "không tồn tại" in str(exc_info.value)


@patch("app.services.hoan_tien_service.repo.tim_theo_id")
def test_tc11_duyet_hoan_tien_thu_cong_sai_trang_thai(mock_tim_hoan):
    """TC-11: Khoản tiền đã hoàn tự động hoặc đã duyệt trước đó -> Không được duyệt lại."""
    hoan_id = str(uuid4())
    mock_tim_hoan.return_value = {
        "id": hoan_id,
        "trang_thai": "da_hoan_tu_dong",
    }
    with pytest.raises(GiaTriLoi) as exc_info:
        hoan_tien_service.duyet_hoan_tien_thu_cong(
            hoan_id,
            str(uuid4()),
            {
                "so_tai_khoan_nhan": "12345",
                "ten_ngan_hang_nhan": "MB",
                "ten_chu_tai_khoan_nhan": "A",
            },
        )
    assert "không ở trạng thái chờ xử lý" in str(exc_info.value)


@patch("app.services.hoan_tien_service.repo.tim_theo_id")
def test_duyet_hoan_tien_thu_cong_thieu_thong_tin(mock_tim_hoan):
def test_tc12_duyet_hoan_tien_thu_cong_thieu_thong_tin(mock_tim_hoan):
    """TC-12: Thiếu STK/Ngân hàng/Chủ TK -> Báo lỗi."""
    hoan_id = str(uuid4())
    mock_tim_hoan.return_value = {
        "id": hoan_id,
        "trang_thai": "cho_xu_ly",
    }
    with pytest.raises(GiaTriLoi) as exc_info:
        hoan_tien_service.duyet_hoan_tien_thu_cong(
            hoan_id,
            str(uuid4()),
            {
                "so_tai_khoan_nhan": "",
                "so_tai_khoan_nhan": "   ",  # Chỉ có khoảng trắng
                "ten_ngan_hang_nhan": "MB",
                "ten_chu_tai_khoan_nhan": "A",
            },
        )
    assert "Bắt buộc cung cấp đầy đủ" in str(exc_info.value)


@patch("app.services.hoan_tien_service.repo.tim_theo_id")
@patch("app.services.hoan_tien_service.repo.cap_nhat_chuyen_khoan_thu_cong")
def test_tc13_duyet_hoan_tien_thu_cong_cap_nhat_db_that_bai(mock_cap_nhat, mock_tim_hoan):
    """TC-13: Trường hợp cập nhật DB trả về None -> Báo lỗi GiaTriLoi."""
    hoan_id = str(uuid4())
    mock_tim_hoan.return_value = {
        "id": hoan_id,
        "trang_thai": "cho_xu_ly",
    }
    mock_cap_nhat.return_value = None  # DB update fail

    with pytest.raises(GiaTriLoi) as exc_info:
        hoan_tien_service.duyet_hoan_tien_thu_cong(
            hoan_id,
            str(uuid4()),
            {
                "so_tai_khoan_nhan": "12345678",
                "ten_ngan_hang_nhan": "MB",
                "ten_chu_tai_khoan_nhan": "NGUYEN VAN B",
            },
        )
    assert "thất bại" in str(exc_info.value)


# ====================================================================
# 4. UC-43: Tự động hoàn tiền sự cố >= 3 tiếng nhưng KHÔNG hủy vé
# ====================================================================

@patch("app.services.hoan_tien_service.repo.tim_chuyen_gap_su_co_nha_xe_qua_3_tieng")
@patch("app.services.hoan_tien_service.repo.tim_ve_da_thanh_toan_theo_chuyen")
@patch("app.services.hoan_tien_service.repo.tim_theo_ve_id")
@patch("app.services.hoan_tien_service.tao_hoan_tien")
@patch("app.services.hoan_tien_service.repo.cap_nhat_ve_da_huy")
def test_quet_va_hoan_tien_su_co_qua_3_tieng_uc43(
def test_tc14_tc15_quet_va_hoan_tien_su_co_qua_3_tieng_uc43(
    mock_cap_nhat_huy, mock_tao_hoan, mock_tim_theo_ve, mock_tim_ve, mock_tim_chuyen, mau_ve_tien_mat
):
    """UC-43: Hoàn tiền tự động cho khách nhưng vé VẪN GIỮ NGUYÊN da_thanh_toan (không gọi cap_nhat_ve_da_huy)."""
    """TC-14 & TC-15: Hoàn tiền tự động cho khách nhưng vé VẪN GIỮ NGUYÊN da_thanh_toan (không gọi cap_nhat_ve_da_huy)."""
    chuyen_id = str(uuid4())
    mock_tim_chuyen.return_value = [{"id": chuyen_id}]
    mock_tim_ve.return_value = [mau_ve_tien_mat]
    mock_tim_theo_ve.return_value = None  # Chưa từng được hoàn

    so_ve = hoan_tien_service.quet_va_hoan_tien_su_co_qua_3_tieng()

    assert so_ve == 1
    mock_tao_hoan.assert_called_once_with(
        ve_id=mau_ve_tien_mat["id"],
        ly_do="tu_dong_hoan_qua_3_tieng",
        so_tien=mau_ve_tien_mat["gia"],
    )
    # Tuyệt đối không được hủy vé
    mock_cap_nhat_huy.assert_not_called()


@patch("app.services.hoan_tien_service.repo.tim_chuyen_gap_su_co_nha_xe_qua_3_tieng")
@patch("app.services.hoan_tien_service.repo.tim_ve_da_thanh_toan_theo_chuyen")
@patch("app.services.hoan_tien_service.repo.tim_theo_ve_id")
@patch("app.services.hoan_tien_service.tao_hoan_tien")
def test_tc16_quet_hoan_tien_da_co_ban_ghi_khong_hoan_lai(
    mock_tao_hoan, mock_tim_theo_ve, mock_tim_ve, mock_tim_chuyen, mau_ve_tien_mat
):
    """TC-16: Khi job chạy lại, vé đã có bản ghi hoàn tiền từ trước sẽ được bỏ qua."""
    chuyen_id = str(uuid4())
    mock_tim_chuyen.return_value = [{"id": chuyen_id}]
    mock_tim_ve.return_value = [mau_ve_tien_mat]
    mock_tim_theo_ve.return_value = {"id": str(uuid4()), "trang_thai": "da_hoan_tu_dong"}  # Đã hoàn rồi

    so_ve = hoan_tien_service.quet_va_hoan_tien_su_co_qua_3_tieng()
    assert so_ve == 0
    mock_tao_hoan.assert_not_called()


@patch("app.services.hoan_tien_service.repo.tim_chuyen_gap_su_co_nha_xe_qua_3_tieng")
def test_tc17_quet_hoan_tien_khong_co_chuyen_su_co(mock_tim_chuyen):
    """TC-17: Không có chuyến nào gặp sự cố quá 3 tiếng -> Trả về 0 an toàn."""
    mock_tim_chuyen.return_value = []
    so_ve = hoan_tien_service.quet_va_hoan_tien_su_co_qua_3_tieng()
    assert so_ve == 0


# ====================================================================
# 5. UC-39: Báo cáo Thống kê Doanh thu Kế toán
# ====================================================================

@patch("app.services.hoan_tien_service.repo.thong_ke_tai_chinh_tong_hop")
def test_thong_ke_doanh_thu_ke_toan(mock_thong_ke):
def test_tc18_tc19_thong_ke_doanh_thu_ke_toan(mock_thong_ke):
    """TC-18 & TC-19: Doanh thu thuần = (Vé + Hàng) - Tiền hoàn, hỗ trợ lọc theo ngày."""
    mock_thong_ke.return_value = {
        "tong_doanh_thu_ve": 10000000,
        "tong_doanh_thu_gui_hang": 2500000,
        "tong_tien_hoan_ve": 1500000,
        "doanh_thu_thuan": 11000000,
        "so_luong_ve_da_ban": 40,
        "so_luong_don_hang": 15,
        "so_luot_hoan_tien": 5,
        "so_luot_cho_xu_ly": 1,
    }

    bao_cao = hoan_tien_service.thong_ke_doanh_thu_ke_toan("2026-09-01", "2026-09-20")
    assert bao_cao["doanh_thu_thuan"] == 11000000
    assert bao_cao["tong_tien_hoan_ve"] == 1500000

    mock_thong_ke.assert_called_once_with(tu_ngay="2026-09-01", den_ngay="2026-09-20")
