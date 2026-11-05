"""Job nhắc chuyến chưa gán xe + tự chuyển 'đang hoãn' (UC-44 ⏱) — thay repo/thông báo bằng bản giả, chỉ kiểm tra quy tắc."""

import datetime
from zoneinfo import ZoneInfo

from app.jobs import quet_chuyen_chua_co_xe as job

VN = ZoneInfo("Asia/Ho_Chi_Minh")
BAY_GIO = datetime.datetime(2030, 1, 9, 17, 0, tzinfo=datetime.timezone.utc)  # 00:00 ngày 10 giờ VN


def chuyen(id_, gio_khoi_hanh, chu_trinh_id="ct-1", tuyen_id="t-1"):
    return {"id": id_, "ma": f"MA-{id_}", "chu_trinh_id": chu_trinh_id, "tuyen_id": tuyen_id, "ten_tuyen": "Hà Nội – Sapa", "gio_khoi_hanh": gio_khoi_hanh}


class Gia:
    """Gom các bản giả: thông báo đã gửi, lịch sử nhận (để thử chống gửi trùng)."""

    def __init__(self, monkeypatch, chuyen_sap_toi=(), chuyen_vua_hoan=(), nguoi_nhan=("ddv-1",), khach=("kh-1",)):
        self.da_gui = []
        self.da_nhan = set()
        da_goi_hoan = self.da_goi_hoan = []
        monkeypatch.setattr(job.repo, "chuyen_chua_gan_xe_sap_toi", lambda tu, den: list(chuyen_sap_toi))
        monkeypatch.setattr(job.repo, "danh_dau_dang_hoan_chuyen_qua_gio", lambda bay_gio, tu: da_goi_hoan.append((bay_gio, tu)) or list(chuyen_vua_hoan))
        monkeypatch.setattr(job.dieu_do_service, "nguoi_nhan_thong_bao_cua_tuyen", lambda tuyen_id: list(nguoi_nhan))
        monkeypatch.setattr(job.nguoi_dung_repo, "danh_sach_id_theo_vai_tro", lambda vai_tro, chi_dang_hoat_dong=False: ["ql-1"])
        monkeypatch.setattr(job.thong_bao_repo, "da_co_thong_bao_giong", lambda nguoi_id, noi_dung: (nguoi_id, noi_dung) in self.da_nhan)
        monkeypatch.setattr(job.ve_repo, "tim_khach_hang_dang_hoat_dong_theo_chuyen", lambda chuyen_id: [{"khach_hang_id": k} for k in khach])

        def gui(nguoi_id, noi_dung, **kw):
            self.da_gui.append((nguoi_id, noi_dung, kw.get("duong_dan")))
            self.da_nhan.add((nguoi_id, noi_dung))

        monkeypatch.setattr(job.thong_bao, "gui", gui)


def test_noi_dung_nhac_hai_muc_khac_nhau():
    c = [chuyen("a", BAY_GIO + datetime.timedelta(hours=20))]
    thuong = job.noi_dung_nhac(c, datetime.timedelta(hours=20))
    khan = job.noi_dung_nhac(c, datetime.timedelta(hours=5))
    assert thuong != khan and khan.startswith("KHẨN") and not thuong.startswith("KHẨN")


def test_noi_dung_nhac_doi_gio_lon_sang_ngay():
    c = [chuyen("a", BAY_GIO + datetime.timedelta(hours=20))]
    assert "dưới 2 ngày" in job.noi_dung_nhac(c, datetime.timedelta(hours=20))
    assert "dưới 6 giờ" in job.noi_dung_nhac(c, datetime.timedelta(hours=5))


def test_nhac_gui_cho_dieu_do_vien_phu_trach_kem_duong_dan(monkeypatch):
    gia = Gia(monkeypatch, chuyen_sap_toi=[chuyen("a", BAY_GIO + datetime.timedelta(hours=20))])
    assert job.nhac_chua_gan_xe(BAY_GIO) == 1
    assert [(n, d) for n, _, d in gia.da_gui] == [("ddv-1", "/nhan-vien/dieu-do/gan-xe.html?chu_trinh=ct-1")]  # bấm vào thông báo nhảy tới đúng chu trình


def test_nhac_gom_hai_chuyen_cung_chu_trinh_thanh_mot_thong_bao(monkeypatch):
    gia = Gia(monkeypatch, chuyen_sap_toi=[chuyen("di", BAY_GIO + datetime.timedelta(hours=20)), chuyen("ve", BAY_GIO + datetime.timedelta(hours=27))])
    assert job.nhac_chua_gan_xe(BAY_GIO) == 1 and len(gia.da_gui) == 1


def test_nhac_khong_gui_trung_nhung_gui_them_khi_vao_muc_khan(monkeypatch):
    gia = Gia(monkeypatch, chuyen_sap_toi=[chuyen("a", BAY_GIO + datetime.timedelta(hours=20))])
    job.nhac_chua_gan_xe(BAY_GIO)
    assert job.nhac_chua_gan_xe(BAY_GIO) == 0 and len(gia.da_gui) == 1  # lần chạy sau cùng mức: không báo lại
    # 15 giờ sau chuyến còn 5 giờ → mức khẩn có nội dung khác → báo thêm đúng 1 lần
    gia2 = Gia(monkeypatch, chuyen_sap_toi=[chuyen("a", BAY_GIO + datetime.timedelta(hours=20))])
    job.nhac_chua_gan_xe(BAY_GIO)
    sau = BAY_GIO + datetime.timedelta(hours=15)
    assert job.nhac_chua_gan_xe(sau) == 1 and gia2.da_gui[-1][1].startswith("KHẨN")


def test_nhac_nhieu_dieu_do_vien_cung_tuyen_moi_nguoi_mot_thong_bao(monkeypatch):
    gia = Gia(monkeypatch, chuyen_sap_toi=[chuyen("a", BAY_GIO + datetime.timedelta(hours=20))], nguoi_nhan=("ddv-1", "ddv-2"))
    assert job.nhac_chua_gan_xe(BAY_GIO) == 2
    assert sorted(n for n, _, _ in gia.da_gui) == ["ddv-1", "ddv-2"]


def test_nhac_loi_o_mot_chu_trinh_khong_chan_chu_trinh_khac(monkeypatch):
    gia = Gia(monkeypatch, chuyen_sap_toi=[chuyen("a", BAY_GIO + datetime.timedelta(hours=20), "ct-a", "t-loi"), chuyen("b", BAY_GIO + datetime.timedelta(hours=21), "ct-b", "t-ok")])

    def nguoi_nhan(tuyen_id):
        if tuyen_id == "t-loi":
            raise RuntimeError("hỏng")
        return ["ddv-1"]

    monkeypatch.setattr(job.dieu_do_service, "nguoi_nhan_thong_bao_cua_tuyen", nguoi_nhan)
    assert job.nhac_chua_gan_xe(BAY_GIO) == 1 and len(gia.da_gui) == 1


def test_chuyen_sang_dang_hoan_bao_dieu_do_vien_quan_ly_va_khach(monkeypatch):
    gia = Gia(monkeypatch, chuyen_vua_hoan=[chuyen("a", BAY_GIO - datetime.timedelta(minutes=2))], khach=("kh-1", "kh-2"))
    assert job.chuyen_sang_dang_hoan(BAY_GIO) == 1
    nguoi = sorted(n for n, _, _ in gia.da_gui)
    assert nguoi == ["ddv-1", "kh-1", "kh-2", "ql-1"]
    noi_dung_khach = next(nd for n, nd, _ in gia.da_gui if n == "kh-1")
    assert "hoàn 100%" in noi_dung_khach
    assert next(nd for n, nd, _ in gia.da_gui if n == "ddv-1").count("ĐANG HOÃN") == 1
    assert {d for n, _, d in gia.da_gui if n != "kh-1" and n != "kh-2"} == {"/nhan-vien/dieu-do/gan-xe.html?chu_trinh=ct-1"}  # thông báo cho cán bộ có đường dẫn tới chu trình


def test_chi_hoan_chuyen_qua_gio_trong_12_gio_gan_day(monkeypatch):
    gia = Gia(monkeypatch)
    job.chuyen_sang_dang_hoan(BAY_GIO)
    assert gia.da_goi_hoan == [(BAY_GIO, BAY_GIO - datetime.timedelta(hours=12))]


def test_khong_co_chuyen_vua_hoan_thi_khong_gui_gi(monkeypatch):
    gia = Gia(monkeypatch)
    assert job.chay(BAY_GIO) == (0, 0) and gia.da_gui == []


def test_chay_tra_ve_so_nhac_va_so_hoan(monkeypatch):
    Gia(monkeypatch, chuyen_sap_toi=[chuyen("a", BAY_GIO + datetime.timedelta(hours=20))], chuyen_vua_hoan=[chuyen("b", BAY_GIO - datetime.timedelta(minutes=1), "ct-b")])
    assert job.chay(BAY_GIO) == (1, 1)
