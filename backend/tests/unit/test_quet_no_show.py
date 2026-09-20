"""Unit test cho jobs/quet_no_show.py (UC-14) — giả lập Repository."""

from app.jobs import quet_no_show as job


def test_chay_danh_dau_khong_den_cho_moi_ve(monkeypatch):
    ve_list = [{"id": "ve-1", "khach_hang_id": None}, {"id": "ve-2", "khach_hang_id": "kh-1"}]
    monkeypatch.setattr(job.ve_repo, "tim_ve_qua_gio_len_xe", lambda x_phut: ve_list)
    danh_dau = []
    monkeypatch.setattr(job.ve_repo, "danh_dau_khong_den", lambda vid: danh_dau.append(vid))
    monkeypatch.setattr(job.ve_repo, "dem_vi_pham_no_show", lambda kh, ngay: 0)
    job.chay()
    assert danh_dau == ["ve-1", "ve-2"]


def test_chay_khong_kiem_tra_vi_pham_neu_ve_vang_lai(monkeypatch):
    """Vé vãng lai (khach_hang_id None) không có tài khoản để đếm/khóa."""
    monkeypatch.setattr(job.ve_repo, "tim_ve_qua_gio_len_xe", lambda x_phut: [{"id": "ve-1", "khach_hang_id": None}])
    monkeypatch.setattr(job.ve_repo, "danh_dau_khong_den", lambda vid: None)
    da_dem = []
    monkeypatch.setattr(job.ve_repo, "dem_vi_pham_no_show", lambda kh, ngay: da_dem.append(kh))
    job.chay()
    assert da_dem == []


def test_chay_khoa_khi_du_nguong_vi_pham(monkeypatch):
    monkeypatch.setattr(job.ve_repo, "tim_ve_qua_gio_len_xe", lambda x_phut: [{"id": "ve-1", "khach_hang_id": "kh-1"}])
    monkeypatch.setattr(job.ve_repo, "danh_dau_khong_den", lambda vid: None)
    monkeypatch.setattr(job.ve_repo, "dem_vi_pham_no_show", lambda kh, ngay: job.NGUONG_SO_LAN_VI_PHAM)
    khoa = []
    monkeypatch.setattr(job.ho_so_repo, "khoa_thanh_toan_tai_quay", lambda kh: khoa.append(kh))
    job.chay()
    assert khoa == ["kh-1"]


def test_chay_khong_khoa_khi_chua_du_nguong(monkeypatch):
    monkeypatch.setattr(job.ve_repo, "tim_ve_qua_gio_len_xe", lambda x_phut: [{"id": "ve-1", "khach_hang_id": "kh-1"}])
    monkeypatch.setattr(job.ve_repo, "danh_dau_khong_den", lambda vid: None)
    monkeypatch.setattr(job.ve_repo, "dem_vi_pham_no_show", lambda kh, ngay: job.NGUONG_SO_LAN_VI_PHAM - 1)
    khoa = []
    monkeypatch.setattr(job.ho_so_repo, "khoa_thanh_toan_tai_quay", lambda kh: khoa.append(kh))
    job.chay()
    assert khoa == []
