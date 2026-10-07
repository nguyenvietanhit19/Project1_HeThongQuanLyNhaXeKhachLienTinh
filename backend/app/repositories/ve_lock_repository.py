"""Khóa ghế & vòng đời "đặt chỗ" của vé (UC-05, UC-08) — NGHIEP_VU.md mục 3.4, 6; DATABASE.md mục 4.

Đây là file riêng đúng như CONTRIBUTING.md mục 5.1: nơi DUY NHẤT chống bán trùng ghế. Cách làm (mục 6):
trong 1 transaction, khóa dòng `chuyen_xe` (tuần tự hóa mọi lượt đặt cùng chuyến — kể cả khi ghế chưa có vé
nào để khóa) rồi khóa các dòng `ve` đang chiếm cùng ghế và kiểm tra đoạn nửa mở `[don, tra)` có giao nhau hay
không. Ràng buộc UNIQUE đơn giản không đủ vì 1 ghế hợp lệ có nhiều vé cùng lúc nếu các chặng không giao nhau.

`hl` = thứ tự hiệu lực theo chiều chuyến (xuôi: thu_tu, ngược: −thu_tu), như tim_kiem_chuyen_repository.
File này chỉ chứa SQL + cơ chế khóa; quy tắc nghiệp vụ (ai được đặt, điểm đón/trả hợp lệ, cọc...) ở
services/dat_ve_service.py.
"""

from app.db import get_connection, release_connection
from app.utils.loi import GiaTriLoi

# Vé đang chiếm ghế: đã trả tiền, hoặc đang giữ chỗ mà chưa hết hạn (hạn NULL = "thanh toán tại quầy", không hạn).
_DANG_CHIEM_GHE = """(v.trang_thai = 'da_thanh_toan'
                       OR (v.trang_thai = 'giu_cho' AND (v.han_giu_cho_den IS NULL OR v.han_giu_cho_den > now())))"""

# Vé còn trong lượt đặt chỗ (chưa thanh toán xong, chưa hết hạn)
_DANG_GIU_CHO = "v.trang_thai = 'giu_cho' AND (v.han_giu_cho_den IS NULL OR v.han_giu_cho_den > now())"


def _thanh_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def _hl_cua_diem(cur, chuyen_id: str, diem_ids: list[str]) -> dict[str, int]:
    """thu_tu hiệu lực của các điểm trên tuyến của chuyến; điểm không thuộc tuyến thì không có trong kết quả."""
    cur.execute(
        """
        SELECT tdt.diem_don_tra_id::text AS diem_id,
               CASE WHEN c.chieu = 'xuoi' THEN tdt.thu_tu ELSE -tdt.thu_tu END AS hl
        FROM chuyen_xe c
        JOIN tuyen_diem_don_tra tdt ON tdt.tuyen_id = c.tuyen_id
        WHERE c.id = %s AND tdt.diem_don_tra_id = ANY(%s::uuid[])
        """,
        (chuyen_id, diem_ids),
    )
    return {r[0]: r[1] for r in cur.fetchall()}


def giu_ghe(
    chuyen_id: str,
    danh_sach_ghe: list[str],
    diem_don_id: str,
    diem_tra_id: str,
    khach_hang_id: str,
    gia: int,
    ma_dat_cho: str,
    han_giu_tam_phut: int,
) -> list[dict]:
    """Mốc khóa ghế (khách bấm "Tiếp tục" sau khi đã chọn điểm đón/trả): tạo `ve` trạng thái `giu_cho` cho từng ghế
    trên đúng đoạn [don, tra) khách chọn hoặc báo lỗi nếu có ghế bị người khác chiếm — tất cả trong 1 transaction, hoặc
    giữ đủ mọi ghế hoặc không giữ ghế nào. Ai bấm "Tiếp tục" trước thì giữ được ghế."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Tuần tự hóa mọi lượt đặt cùng chuyến
            cur.execute("SELECT id FROM chuyen_xe WHERE id = %s FOR UPDATE", (chuyen_id,))
            if cur.fetchone() is None:
                raise GiaTriLoi("Chuyến không tồn tại")

            # 2. Nhả các ghế giữ tạm đã quá hạn của chuyến này để không cản đường người sau
            cur.execute(
                """
                UPDATE ve SET trang_thai = 'het_han'
                WHERE chuyen_id = %s AND trang_thai = 'giu_cho'
                  AND han_giu_cho_den IS NOT NULL AND han_giu_cho_den <= now()
                """,
                (chuyen_id,),
            )

            hl = _hl_cua_diem(cur, chuyen_id, [diem_don_id, diem_tra_id])
            if diem_don_id not in hl or diem_tra_id not in hl:
                raise GiaTriLoi("Điểm đón/trả không thuộc tuyến của chuyến này")
            hl_don, hl_tra = hl[diem_don_id], hl[diem_tra_id]
            if hl_don >= hl_tra:
                raise GiaTriLoi("Điểm trả phải đứng sau điểm đón")

            # 3. Khóa + kiểm tra giao đoạn với mọi vé đang chiếm các ghế này
            cur.execute(
                f"""
                SELECT v.so_ghe
                FROM ve v
                JOIN chuyen_xe c ON c.id = v.chuyen_id
                JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = v.diem_don_id
                JOIN tuyen_diem_don_tra b ON b.tuyen_id = c.tuyen_id AND b.diem_don_tra_id = v.diem_tra_id
                WHERE v.chuyen_id = %(chuyen)s AND v.so_ghe = ANY(%(ghe)s)
                  AND {_DANG_CHIEM_GHE}
                  AND (CASE WHEN c.chieu = 'xuoi' THEN a.thu_tu ELSE -a.thu_tu END) < %(tra)s
                  AND %(don)s < (CASE WHEN c.chieu = 'xuoi' THEN b.thu_tu ELSE -b.thu_tu END)
                ORDER BY v.so_ghe
                FOR UPDATE OF v
                """,
                {"chuyen": chuyen_id, "ghe": danh_sach_ghe, "don": hl_don, "tra": hl_tra},
            )
            bi_chiem = sorted({r[0] for r in cur.fetchall()})  # FOR UPDATE không đi cùng DISTINCT nên gộp ở đây
            if bi_chiem:
                raise GiaTriLoi(f"Ghế {', '.join(bi_chiem)} đã có người chọn — vui lòng chọn ghế khác")

            # 4. Tạo vé giữ chỗ. Chưa chốt cách thanh toán nên tạm ghi 'thanh_toan_ngay' kèm hạn giữ tạm
            # (nhả ghế nếu khách bỏ dở); chọn xong cách thanh toán thì hạn được đặt lại đúng quy tắc mục 6.
            ve_tao = []
            for so_ghe in danh_sach_ghe:
                cur.execute(
                    """
                    INSERT INTO ve (chuyen_id, so_ghe, diem_don_id, diem_tra_id, khach_hang_id, gia, ma_dat_cho,
                                    loai_hinh_thanh_toan, trang_thai, han_giu_cho_den)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'thanh_toan_ngay', 'giu_cho',
                            now() + make_interval(mins => %s))
                    RETURNING id, so_ghe, gia, han_giu_cho_den
                    """,
                    (chuyen_id, so_ghe, diem_don_id, diem_tra_id, khach_hang_id, gia, ma_dat_cho, han_giu_tam_phut),
                )
                ve_tao.append(_thanh_list(cur, [cur.fetchone()])[0])
        conn.commit()
        return ve_tao
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def lay_dat_cho(ma_dat_cho: str, khach_hang_id: str) -> list[dict]:
    """Mọi vé của 1 lượt đặt chỗ thuộc đúng khách này (kèm thông tin chuyến, điểm đón/trả, giờ dự kiến tại điểm đón).
    Không trả vé của khách khác — mã đặt chỗ đoán trúng cũng không xem được."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id, v.so_ghe, v.gia, v.trang_thai, v.loai_hinh_thanh_toan, v.la_ve_dat_coc,
                       v.han_giu_cho_den, v.gio_bat_dau_dem_han, v.ma_dat_cho, v.chuyen_id, v.diem_don_id, v.diem_tra_id,
                       c.ma AS ma_chuyen, c.gio_khoi_hanh, c.tuyen_id, c.chieu, c.trang_thai AS trang_thai_chuyen,
                       lx.ten AS ten_loai_xe,
                       dd.ten AS ten_diem_don, dt.ten AS ten_diem_tra, dd.khu_vuc_id AS khu_vuc_di_id,
                       dt.khu_vuc_id AS khu_vuc_den_id,
                       c.gio_khoi_hanh + make_interval(mins =>
                           CASE WHEN c.chieu = 'xuoi' THEN a.thoi_gian_du_kien_phut
                                ELSE tong.tong_phut - a.thoi_gian_du_kien_phut END) AS gio_don_du_kien,
                       c.gio_khoi_hanh + make_interval(mins =>
                           CASE WHEN c.chieu = 'xuoi' THEN b.thoi_gian_du_kien_phut
                                ELSE tong.tong_phut - b.thoi_gian_du_kien_phut END) AS gio_den_du_kien
                FROM ve v
                JOIN chuyen_xe c ON c.id = v.chuyen_id
                JOIN loai_xe lx ON lx.id = c.loai_xe_id
                JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = v.diem_don_id
                JOIN tuyen_diem_don_tra b ON b.tuyen_id = c.tuyen_id AND b.diem_don_tra_id = v.diem_tra_id
                JOIN (SELECT tuyen_id, MAX(thoi_gian_du_kien_phut) AS tong_phut
                      FROM tuyen_diem_don_tra GROUP BY tuyen_id) tong ON tong.tuyen_id = c.tuyen_id
                WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s
                ORDER BY v.so_ghe
                """,
                (ma_dat_cho, khach_hang_id),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_diem_cua_chuyen(chuyen_id: str) -> list[dict]:
    """Mọi điểm của tuyến của chuyến, kèm `hl` theo chiều chạy thật — để kiểm tra điểm đón/trả khách chọn."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id::text AS diem_id, d.ten, d.loai, d.khu_vuc_id::text AS khu_vuc_id,
                       CASE WHEN c.chieu = 'xuoi' THEN tdt.thu_tu ELSE -tdt.thu_tu END AS hl
                FROM chuyen_xe c
                JOIN tuyen_diem_don_tra tdt ON tdt.tuyen_id = c.tuyen_id
                JOIN diem_don_tra d ON d.id = tdt.diem_don_tra_id
                WHERE c.id = %s
                ORDER BY hl
                """,
                (chuyen_id,),
            )
            return _thanh_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def tim_ma_dat_cho_con_giu(khach_hang_id: str) -> list[str]:
    """Giỏ hàng: các lượt đặt chỗ của khách còn đang giữ ghế CÓ HẠN (chưa chốt tại quầy, chưa thanh toán, chưa hết hạn),
    lượt sắp hết hạn nhất xếp trước."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ma_dat_cho FROM ve
                WHERE khach_hang_id = %s AND trang_thai = 'giu_cho'
                  AND han_giu_cho_den IS NOT NULL AND han_giu_cho_den > now()
                GROUP BY ma_dat_cho ORDER BY MIN(han_giu_cho_den)
                """,
                (khach_hang_id,),
            )
            return [r[0] for r in cur.fetchall()]
    finally:
        release_connection(conn)


def chot_thanh_toan_tai_quay(ma_dat_cho: str, khach_hang_id: str, so_ghe_chon: list[str], so_ve_con_giu: int) -> bool:
    """"Thanh toán tại quầy khi nhận vé" (mục 6) cho đúng các ghế khách đã tích: đặt thành công ngay — bỏ hạn, giữ ghế
    tới giờ khởi hành. Các ghế còn lại của lượt đặt (không tích) KHÔNG được đặt: chuyển `da_huy`, ghế mở lại ngay.
    Làm cùng 1 transaction và chỉ thành công nếu đủ `so_ve_con_giu` vé còn sống (không vé nào hết hạn/hủy giữa chừng),
    nếu không thì không đổi gì cả."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE ve v SET trang_thai = 'da_huy', gio_huy = now()
                WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO} AND v.so_ghe <> ALL(%s)
                """,
                (ma_dat_cho, khach_hang_id, so_ghe_chon),
            )
            so_nha = cur.rowcount
            cur.execute(
                f"""
                UPDATE ve v SET loai_hinh_thanh_toan = 'thanh_toan_tai_quay', han_giu_cho_den = NULL, gio_bat_dau_dem_han = NULL
                WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO} AND v.so_ghe = ANY(%s)
                """,
                (ma_dat_cho, khach_hang_id, so_ghe_chon),
            )
            so_chot = cur.rowcount
            if so_chot != len(so_ghe_chon) or so_chot + so_nha != so_ve_con_giu:
                conn.rollback()
                return False
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def bo_ghe(ma_dat_cho: str, khach_hang_id: str, so_ghe: str) -> bool:
    """Khách bấm ✕ ở 1 ghế trong lượt đặt: hủy riêng ghế đó, ghế mở lại ngay cho người khác."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE ve v SET trang_thai = 'da_huy', gio_huy = now()
                WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO} AND v.so_ghe = %s
                """,
                (ma_dat_cho, khach_hang_id, so_ghe),
            )
            xong = cur.rowcount == 1
        conn.commit()
        return xong
    finally:
        release_connection(conn)


def huy_dat_cho(ma_dat_cho: str, khach_hang_id: str) -> int:
    """UC-08: khách tự hủy giữ chỗ trước khi thanh toán — mở lại ghế. Trả số vé đã hủy."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE ve v SET trang_thai = 'da_huy', gio_huy = now()
                WHERE v.ma_dat_cho = %s AND v.khach_hang_id = %s AND {_DANG_GIU_CHO}
                """,
                (ma_dat_cho, khach_hang_id),
            )
            so_ve = cur.rowcount
        conn.commit()
        return so_ve
    finally:
        release_connection(conn)


def danh_dau_het_han_qua_han() -> int:
    """Job quét: vé giữ chỗ có hạn mà đã quá hạn → `het_han` (ghế đã mở lại từ lúc quá hạn nhờ kiểm tra hạn lúc truy
    vấn; job chỉ dọn trạng thái để không bị tính nhầm là no-show). Trả số vé đã chuyển."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ve SET trang_thai = 'het_han'
                WHERE trang_thai = 'giu_cho' AND han_giu_cho_den IS NOT NULL AND han_giu_cho_den <= now()
                """
            )
            so_ve = cur.rowcount
        conn.commit()
        return so_ve
    finally:
        release_connection(conn)
