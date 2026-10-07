"""API Router cho phân hệ Gửi hàng — NGHIEP_VU.md mục 10 & mục 8.5.

Route chỉ nhận request, kiểm tra quyền qua dependency yeu_cau_vai_tro,
xác định phạm vi văn phòng, gọi gui_hang_service và trả response.

Phân quyền theo ma trận use case (mục 11):
- Thao tác tại quầy (UC-23/24/25: tạo đơn, giao hàng, ghi liên hệ) — CHỈ
  nhan_vien_gui_hang, luôn ở văn phòng được gán trong hồ sơ.
- Xem (hàng đến, tra cứu, danh sách đơn) — thêm quan_ly (toàn hệ thống,
  cần để xử lý/thanh lý hàng tồn theo UC-25).
- Thống kê (UC-39) — thêm quan_ly_nhan_su (toàn hệ thống).
Chất/dỡ hàng của phụ xe (UC-26/27/28) nằm ở routes/phu_xe.py.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Query, status

from app.middleware.auth_middleware import NguoiDungHienTai, yeu_cau_vai_tro
from app.schemas.don_hang_schema import (
    BaoCaoSuCoHangResponse,
    CapNhatLienHeRequest,
    DanhSachDonHangResponse,
    DonHangResponse,
    DonHangTraCuuCongKhaiResponse,
    GiaoHangRequest,
    GoiYKhachResponse,
    LichSuChinhSuaResponse,
    LichSuLienHeResponse,
    LichSuTrangThaiResponse,
    LoaiHangResponse,
    PhuongThucThanhToan,
    SuaThongTinLienHeRequest,
    TaoDonHangRequest,
    TrangThaiDonHang,
)
from app.services import gui_hang_service
from app.utils.loi import CamTruyCap

router = APIRouter(prefix="/gui-hang", tags=["gui-hang"])

VAI_TRO_TOAN_HE_THONG = ("quan_ly", "quan_ly_nhan_su")

QuyenThaoTacQuay = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("nhan_vien_gui_hang"))]
QuyenXemGuiHang = Annotated[NguoiDungHienTai, Depends(yeu_cau_vai_tro("nhan_vien_gui_hang", "quan_ly"))]
QuyenThongKe = Annotated[
    NguoiDungHienTai, Depends(yeu_cau_vai_tro("nhan_vien_gui_hang", "quan_ly", "quan_ly_nhan_su"))
]


def _pham_vi_van_phong(nguoi_dung: NguoiDungHienTai, diem_yeu_cau: UUID | str | None = None) -> str | None:
    """Nhân viên bị giới hạn ở văn phòng trong hồ sơ; quản lý xem toàn hệ thống
    (None) hoặc 1 văn phòng tùy chọn."""
    if nguoi_dung.vai_tro in VAI_TRO_TOAN_HE_THONG:
        return str(diem_yeu_cau) if diem_yeu_cau else None
    if not nguoi_dung.van_phong_id:
        raise CamTruyCap("Tài khoản chưa được gán văn phòng phụ trách")
    if diem_yeu_cau and str(diem_yeu_cau) != str(nguoi_dung.van_phong_id):
        raise CamTruyCap("Không có quyền thao tác tại văn phòng này")
    return str(nguoi_dung.van_phong_id)


def _hom_nay() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


# ====================================================================
# 1. Danh mục & Tạo đơn tại quầy (UC-23)
# ====================================================================

@router.get("/loai-hang", response_model=list[LoaiHangResponse])
def lay_danh_sach_loai_hang(nguoi_dung: QuyenXemGuiHang):
    """Danh mục loại hàng (kèm cờ hàng cấm để giao diện hiển thị và từ chối)."""
    return gui_hang_service.lay_danh_sach_loai_hang()


@router.get("/van-phong-cua-toi")
def lay_van_phong_cua_toi(nguoi_dung: QuyenThaoTacQuay):
    """Văn phòng nhân viên đang được gán (mục 10.4.1 bước 1: điểm gửi tự xác định theo tài khoản)."""
    return gui_hang_service.lay_van_phong(_pham_vi_van_phong(nguoi_dung))


@router.get("/diem-nhan-kha-dung")
def lay_diem_nhan_kha_dung(nguoi_dung: QuyenThaoTacQuay):
    """UC-23 bước 2: khu vực → văn phòng nhận có tuyến nối với văn phòng mình."""
    return gui_hang_service.lay_diem_nhan_kha_dung(_pham_vi_van_phong(nguoi_dung))


@router.get("/tuyen-phu-hop")
def lay_danh_sach_tuyen_phu_hop(
    nguoi_dung: QuyenThaoTacQuay,
    diem_nhan_id: UUID = Query(..., description="ID văn phòng nhận"),
):
    """UC-23 bước 3: các tuyến đi qua văn phòng mình (điểm gửi) và văn phòng nhận."""
    return gui_hang_service.lay_tuyen_phu_hop(_pham_vi_van_phong(nguoi_dung), str(diem_nhan_id))


@router.post("/tao-don", response_model=DonHangResponse, status_code=status.HTTP_201_CREATED)
def tao_don_hang(
    du_lieu: TaoDonHangRequest,
    nguoi_dung: QuyenThaoTacQuay,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
    ] = None,
):
    """UC-23: Nhân viên quầy tạo đơn gửi hàng theo tuyến, nhập cước và in biên nhận.

    Header `Idempotency-Key` (tùy chọn): gửi lại cùng khóa sẽ nhận lại đơn đã tạo.
    """
    diem_gui_id = _pham_vi_van_phong(nguoi_dung, du_lieu.diem_gui_id)
    return gui_hang_service.tao_don_hang(
        du_lieu, nhan_vien_id=nguoi_dung.id, diem_gui_id=diem_gui_id, khoa_chong_trung=idempotency_key,
    )


@router.get("/goi-y-khach", response_model=list[GoiYKhachResponse])
def goi_y_khach(
    nguoi_dung: QuyenThaoTacQuay,
    sdt: str = Query(..., pattern=r"^[0-9]{10,11}$"),
    vai_tro: Literal["gui", "nhan"] = Query(..., description="SĐT đang nhập là của người gửi hay người nhận"),
):
    """Gợi ý họ tên theo SĐT từ các đơn cũ của văn phòng mình."""
    return gui_hang_service.goi_y_khach(sdt, vai_tro, _pham_vi_van_phong(nguoi_dung))


# ====================================================================
# 2. Danh sách & Tra cứu đơn
# ====================================================================

@router.get("/don-hang", response_model=DanhSachDonHangResponse)
def lay_danh_sach_don(
    nguoi_dung: QuyenXemGuiHang,
    huong: Literal["gui", "nhan", "tat_ca"] = Query("gui", description="Đơn gửi đi / gửi tới / cả hai"),
    diem_id: UUID | None = Query(None, description="Chỉ quản lý: văn phòng cần xem"),
    trang_thai: TrangThaiDonHang | None = Query(None),
    phuong_thuc_thanh_toan: PhuongThucThanhToan | None = Query(None),
    tu_khoa: str | None = Query(None, max_length=100, description="Mã vận đơn, tên hoặc SĐT người gửi/nhận"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Danh sách đơn của văn phòng (phân trang phía server)."""
    return gui_hang_service.lay_danh_sach_don(
        _pham_vi_van_phong(nguoi_dung, diem_id),
        huong=huong,
        trang_thai=trang_thai,
        phuong_thuc_thanh_toan=phuong_thuc_thanh_toan,
        tu_khoa=tu_khoa,
        limit=limit,
        offset=offset,
    )


@router.get("/noi-bo/tra-cuu/{ma_van_don}", response_model=DonHangResponse)
def tra_cuu_noi_bo(ma_van_don: str, nguoi_dung: QuyenXemGuiHang):
    """Tra cứu đầy đủ 1 đơn theo mã — nhân viên chỉ thấy đơn gửi đi/gửi tới văn phòng mình."""
    return gui_hang_service.tra_cuu_noi_bo(ma_van_don, _pham_vi_van_phong(nguoi_dung))


@router.get("/tra-cuu-sdt", response_model=list[DonHangResponse])
def tra_cuu_theo_sdt(
    nguoi_dung: QuyenXemGuiHang,
    sdt: str = Query(..., pattern=r"^[0-9]{10,11}$", description="Số điện thoại người gửi hoặc người nhận"),
    muc_dich: Literal["giao", "tat_ca"] = Query("tat_ca", description="'giao': chỉ đơn chờ giao tại văn phòng mình"),
):
    """Tra theo SĐT (mục 10.3.1 điểm 5: người nhận quên mã vận đơn)."""
    return gui_hang_service.tra_cuu_theo_sdt(sdt, _pham_vi_van_phong(nguoi_dung), muc_dich)


@router.get("/tra-cuu/{ma_van_don}", response_model=DonHangTraCuuCongKhaiResponse)
def tra_cuu_cong_khai(ma_van_don: str):
    """Tra cứu công khai theo mã vận đơn — chỉ trả thông tin hành trình, không lộ tên/SĐT."""
    return gui_hang_service.tra_cuu_theo_ma_van_don(ma_van_don)


# ====================================================================
# 3. Hàng đến & Giao hàng cho người nhận (UC-24)
# ====================================================================

@router.get("/hang-den", response_model=list[DonHangResponse])
def lay_hang_den(
    nguoi_dung: QuyenXemGuiHang,
    diem_id: UUID | None = Query(None, description="Chỉ quản lý: văn phòng nhận cần xem"),
):
    """Hàng sắp đến / chờ lấy / hàng tồn tại văn phòng nhận (mục 10.4.2 bước 1, UC-25)."""
    return gui_hang_service.lay_hang_den(_pham_vi_van_phong(nguoi_dung, diem_id))


@router.post("/giao-hang", response_model=DonHangResponse)
def giao_hang(du_lieu: GiaoHangRequest, nguoi_dung: QuyenThaoTacQuay):
    """UC-24: Bàn giao hàng cho người nhận tại quầy (thu COD nếu có)."""
    return gui_hang_service.xac_nhan_giao_hang(
        du_lieu.ma_van_don,
        nhan_vien_nhan_id=nguoi_dung.id,
        van_phong_id=_pham_vi_van_phong(nguoi_dung),
        xac_nhan_da_thu=du_lieu.xac_nhan_da_thu,
    )


@router.get("/don-hang/{don_hang_id}/su-co", response_model=list[BaoCaoSuCoHangResponse])
def lay_bao_cao_su_co(don_hang_id: UUID, nguoi_dung: QuyenXemGuiHang):
    """UC-28 bước 2: báo cáo thất lạc/hư hỏng của phụ xe trên đơn này."""
    return gui_hang_service.lay_bao_cao_su_co(str(don_hang_id), _pham_vi_van_phong(nguoi_dung))


# ====================================================================
# 4. Liên hệ người nhận / người gửi & Hàng chờ lâu (mục 10.3.1, UC-25)
# ====================================================================

@router.post("/don-hang/{don_hang_id}/lien-he", response_model=DonHangResponse)
def ghi_ket_qua_lien_he(don_hang_id: UUID, du_lieu: CapNhatLienHeRequest, nguoi_dung: QuyenThaoTacQuay):
    """Lưu kết quả gọi người nhận / người gửi, hoặc báo quản lý xử lý hàng tồn."""
    return gui_hang_service.ghi_ket_qua_lien_he(
        str(don_hang_id),
        nguoi_dung_id=nguoi_dung.id,
        van_phong_id=_pham_vi_van_phong(nguoi_dung),
        doi_tuong=du_lieu.doi_tuong,
        ket_qua=du_lieu.ket_qua,
        ghi_chu=du_lieu.ghi_chu,
    )


@router.get("/don-hang/{don_hang_id}/lich-su-lien-he", response_model=list[LichSuLienHeResponse])
def lay_lich_su_lien_he(don_hang_id: UUID, nguoi_dung: QuyenXemGuiHang):
    return gui_hang_service.lay_lich_su_lien_he(str(don_hang_id), _pham_vi_van_phong(nguoi_dung))


@router.put("/don-hang/{don_hang_id}/thong-tin-lien-he", response_model=DonHangResponse)
def sua_thong_tin_lien_he(don_hang_id: UUID, du_lieu: SuaThongTinLienHeRequest, nguoi_dung: QuyenThaoTacQuay):
    """Sửa tên/SĐT người gửi, người nhận khi đơn chưa giao (ghi nhật ký chỉnh sửa)."""
    return gui_hang_service.sua_thong_tin_lien_he(
        str(don_hang_id), nguoi_dung.id, _pham_vi_van_phong(nguoi_dung), du_lieu
    )


@router.get("/don-hang/{don_hang_id}/lich-su-chinh-sua", response_model=list[LichSuChinhSuaResponse])
def lay_lich_su_chinh_sua(don_hang_id: UUID, nguoi_dung: QuyenXemGuiHang):
    return gui_hang_service.lay_lich_su_chinh_sua(str(don_hang_id), _pham_vi_van_phong(nguoi_dung))


@router.get("/don-hang/{don_hang_id}/lich-su-trang-thai", response_model=list[LichSuTrangThaiResponse])
def lay_lich_su_trang_thai(don_hang_id: UUID, nguoi_dung: QuyenXemGuiHang):
    return gui_hang_service.lay_lich_su_trang_thai(str(don_hang_id), _pham_vi_van_phong(nguoi_dung))


# ====================================================================
# 5. Thống kê & Đối soát tiền (UC-39)
# ====================================================================

@router.get("/thong-ke")
def thong_ke_hang(
    nguoi_dung: QuyenThongKe,
    diem_id: UUID | None = Query(None, description="Văn phòng cần xem (quản lý để trống = toàn hệ thống)"),
    tu_ngay: date | None = Query(None, description="Mặc định: 30 ngày gần nhất"),
    den_ngay: date | None = Query(None, description="Mặc định: hôm nay"),
):
    """UC-39: số đơn, hàng tồn và tiền thu tại văn phòng trong khoảng ngày."""
    den = den_ngay or _hom_nay()
    tu = tu_ngay or (den - timedelta(days=29))
    return gui_hang_service.thong_ke_hang_tai_diem(_pham_vi_van_phong(nguoi_dung, diem_id), tu, den)


@router.get("/thong-ke-theo-ngay")
def thong_ke_hang_theo_ngay(
    nguoi_dung: QuyenThongKe,
    so_ngay: int = Query(7, description="Khoảng 7, 14 hoặc 30 ngày"),
    diem_id: UUID | None = Query(None),
):
    return gui_hang_service.thong_ke_hang_theo_ngay(_pham_vi_van_phong(nguoi_dung, diem_id), so_ngay)


@router.get("/doi-soat")
def doi_soat_tien(
    nguoi_dung: QuyenThongKe,
    diem_id: UUID | None = Query(None),
    tu_ngay: date | None = Query(None, description="Mặc định: hôm nay"),
    den_ngay: date | None = Query(None, description="Mặc định: hôm nay"),
):
    """Tiền mặt từng nhân viên đã thu (trả trước + COD) — đối soát két cuối ca."""
    den = den_ngay or _hom_nay()
    tu = tu_ngay or den
    return gui_hang_service.doi_soat_tien(_pham_vi_van_phong(nguoi_dung, diem_id), tu, den)
