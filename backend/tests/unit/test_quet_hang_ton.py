"""Unit test cho jobs/quet_hang_ton.py (UC-46) — giả lập Service."""

from unittest.mock import patch
from app.jobs import quet_hang_ton


def test_chay_job_quet_hang_ton():
    with patch("app.jobs.quet_hang_ton.quet_canh_bao_va_chuyen_hang_ton") as mock_quet:
        mock_quet.return_value = {
            "so_don_canh_bao_7_ngay": 3,
            "so_don_chuyen_ton_14_ngay": 1,
        }
        res = quet_hang_ton.chay_job_quet_hang_ton()
        assert res["so_don_canh_bao_7_ngay"] == 3
        assert res["so_don_chuyen_ton_14_ngay"] == 1
        mock_quet.assert_called_once()


def test_chay_job_quet_hang_ton_khong_co_don():
    with patch("app.jobs.quet_hang_ton.quet_canh_bao_va_chuyen_hang_ton") as mock_quet:
        mock_quet.return_value = {
            "so_don_canh_bao_7_ngay": 0,
            "so_don_chuyen_ton_14_ngay": 0,
        }
        res = quet_hang_ton.chay_job_quet_hang_ton()
        assert res["so_don_canh_bao_7_ngay"] == 0
        assert res["so_don_chuyen_ton_14_ngay"] == 0
        mock_quet.assert_called_once()
