from app.db import get_connection, release_connection


def _rows(cur, rows=None):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in (rows if rows is not None else cur.fetchall())]


def van_phong(van_phong_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT d.id, d.ten, d.dia_chi, d.khu_vuc_id, kv.ten AS ten_khu_vuc
                   FROM diem_don_tra d JOIN khu_vuc kv ON kv.id = d.khu_vuc_id
                   WHERE d.id = %s AND d.loai = 'van_phong'""",
                (van_phong_id,),
            )
            rows = _rows(cur)
            return rows[0] if rows else None
    finally:
        release_connection(conn)


def khu_vuc_co_van_phong(van_phong_id: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT kv.id, kv.ten, kv.tinh_thanh
                   FROM khu_vuc kv
                   JOIN diem_don_tra d ON d.khu_vuc_id = kv.id AND d.loai = 'van_phong'
                   JOIN tuyen_diem_don_tra td ON td.diem_don_tra_id = d.id
                   WHERE EXISTS (
                       SELECT 1 FROM tuyen_diem_don_tra mytd
                       WHERE mytd.tuyen_id = td.tuyen_id AND mytd.diem_don_tra_id = %s
                   )
                   ORDER BY kv.tinh_thanh, kv.ten""",
                (van_phong_id,),
            )
            return _rows(cur)
    finally:
        release_connection(conn)


def chuyen_co_van_phong(chuyen_id: str, van_phong_id: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT 1 FROM chuyen_xe c
                   JOIN tuyen_diem_don_tra td ON td.tuyen_id = c.tuyen_id
                   WHERE c.id = %s AND td.diem_don_tra_id = %s""",
                (chuyen_id, van_phong_id),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def khach_hang(khach_hang_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ho_ten, so_dien_thoai FROM nguoi_dung WHERE id = %s AND vai_tro = 'khach_hang' AND dang_hoat_dong",
                (khach_hang_id,),
            )
            rows = _rows(cur)
            return rows[0] if rows else None
    finally:
        release_connection(conn)


def khach_hang_theo_sdt(sdt: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ho_ten, so_dien_thoai FROM nguoi_dung WHERE vai_tro = 'khach_hang' AND so_dien_thoai = %s AND dang_hoat_dong LIMIT 1",
                (sdt,),
            )
            rows = _rows(cur)
            return rows[0] if rows else None
    finally:
        release_connection(conn)


def khach_vang_lai_theo_sdt(sdt: str) -> dict | None:
    """Lấy tên từ vé đã thanh toán gần nhất, hoặc lượt giữ chỗ gần nhất."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT BTRIM(v.ten_khach_vang_lai) AS ho_ten
                   FROM ve v
                   WHERE v.sdt_khach_vang_lai = %s
                     AND NULLIF(BTRIM(v.ten_khach_vang_lai), '') IS NOT NULL
                   ORDER BY CASE WHEN v.gio_thanh_toan IS NOT NULL THEN 0 ELSE 1 END,
                            v.ngay_tao DESC, v.id DESC
                   LIMIT 1""",
                (sdt,),
            )
            rows = _rows(cur)
            return rows[0] if rows else None
    finally:
        release_connection(conn)


def diem_hop_le(chuyen_id: str, van_phong_id: str, diem_tra_id: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT 1
                   FROM chuyen_xe c
                   JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = %s
                   JOIN tuyen_diem_don_tra b ON b.tuyen_id = c.tuyen_id AND b.diem_don_tra_id = %s
                   JOIN diem_don_tra d ON d.id = b.diem_don_tra_id
                   WHERE c.id = %s AND d.loai IN ('van_phong', 'diem_dung')
                     AND ((c.chieu = 'xuoi' AND a.thu_tu < b.thu_tu)
                       OR (c.chieu = 'nguoc' AND a.thu_tu > b.thu_tu))""",
                (van_phong_id, diem_tra_id, chuyen_id),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def diem_tra_thuoc_khu_vuc(diem_tra_id: str, khu_vuc_id: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM diem_don_tra WHERE id = %s AND khu_vuc_id = %s", (diem_tra_id, khu_vuc_id))
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def tra_cuu(van_phong_id: str, ma_dat_cho: str | None = None, sdt: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT v.id, v.ma_ve, v.ma_dat_cho, v.so_ghe, v.gia, v.trang_thai, v.gio_huy,
                          v.phuong_thuc_thanh_toan, v.loai_hinh_thanh_toan, v.han_giu_cho_den,
                          v.ma_tham_chieu_vnpay, v.ma_giao_dich_cong_thanh_toan,
                          COALESCE(nd.ho_ten, v.ten_khach_vang_lai, '') AS ten_khach,
                          COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai, '') AS sdt_khach,
                          c.id AS chuyen_id, c.ma AS ma_chuyen, c.gio_khoi_hanh,
                          c.trang_thai AS trang_thai_chuyen, c.dang_hoan, c.loai_su_co,
                          tu.ten AS ten_tuyen, lx.ten AS ten_loai_xe, x.bien_so,
                          dd.ten AS ten_diem_don, dt.ten AS ten_diem_tra,
                          c.gio_khoi_hanh + make_interval(mins =>
                              CASE WHEN c.chieu = 'xuoi' THEN a.thoi_gian_du_kien_phut
                                   ELSE tong.tong_phut - a.thoi_gian_du_kien_phut END) AS gio_don_du_kien,
                          c.gio_khoi_hanh + make_interval(mins =>
                              CASE WHEN c.chieu = 'xuoi' THEN b.thoi_gian_du_kien_phut
                                   ELSE tong.tong_phut - b.thoi_gian_du_kien_phut END) AS gio_den_du_kien,
                          ht.id AS hoan_tien_id, ht.so_tien AS so_tien_hoan,
                          ht.ly_do AS ly_do_hoan, ht.trang_thai AS trang_thai_hoan,
                          ht.thoi_gian_xac_dinh, ht.thoi_gian_hoan_xong
                   FROM ve v
                   LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                   JOIN chuyen_xe c ON c.id = v.chuyen_id
                   JOIN tuyen tu ON tu.id = c.tuyen_id
                   JOIN loai_xe lx ON lx.id = c.loai_xe_id
                   LEFT JOIN xe x ON x.id = COALESCE(c.xe_thuc_te_id, c.xe_id)
                   JOIN diem_don_tra dd ON dd.id = v.diem_don_id
                   JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                   JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = v.diem_don_id
                   JOIN tuyen_diem_don_tra b ON b.tuyen_id = c.tuyen_id AND b.diem_don_tra_id = v.diem_tra_id
                   JOIN (SELECT tuyen_id, MAX(thoi_gian_du_kien_phut) AS tong_phut
                         FROM tuyen_diem_don_tra GROUP BY tuyen_id) tong ON tong.tuyen_id = c.tuyen_id
                   LEFT JOIN lich_su_hoan_tien ht ON ht.ve_id = v.id
                   WHERE v.diem_don_id = %s
                     AND (%s IS NULL OR v.ma_dat_cho = %s)
                     AND (%s IS NULL OR COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) = %s)
                   ORDER BY v.ngay_tao DESC, v.so_ghe
                   LIMIT 100""",
                (van_phong_id, ma_dat_cho, ma_dat_cho, sdt, sdt),
            )
            return _rows(cur)
    finally:
        release_connection(conn)


def ve_cho_thanh_toan(van_phong_id: str, trang: int, kich_thuoc_trang: int) -> dict:
    """Liệt kê từng vé còn ở trạng thái giữ chỗ của văn phòng, không giới hạn theo ngày lập vé."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM ve WHERE diem_don_id = %s AND trang_thai = 'giu_cho'",
                (van_phong_id,),
            )
            tong_so = cur.fetchone()[0]
            cur.execute(
                """SELECT v.id, v.ma_ve, v.ma_dat_cho, v.so_ghe, v.gia, v.ngay_tao,
                          v.han_giu_cho_den, v.loai_hinh_thanh_toan,
                          COALESCE(kh.ho_ten, v.ten_khach_vang_lai, '') AS ten_khach,
                          COALESCE(kh.so_dien_thoai, v.sdt_khach_vang_lai, '') AS sdt_khach,
                          c.ma AS ma_chuyen, c.gio_khoi_hanh,
                          don.ten AS ten_diem_don, tra.ten AS ten_diem_tra
                   FROM ve v
                   JOIN chuyen_xe c ON c.id = v.chuyen_id
                   JOIN diem_don_tra don ON don.id = v.diem_don_id
                   JOIN diem_don_tra tra ON tra.id = v.diem_tra_id
                   LEFT JOIN nguoi_dung kh ON kh.id = v.khach_hang_id
                   WHERE v.diem_don_id = %s AND v.trang_thai = 'giu_cho'
                   ORDER BY v.ngay_tao DESC, v.id DESC
                   LIMIT %s OFFSET %s""",
                (van_phong_id, kich_thuoc_trang, (trang - 1) * kich_thuoc_trang),
            )
            return {"tong_so": tong_so, "trang": trang, "kich_thuoc_trang": kich_thuoc_trang, "ve": _rows(cur)}
    finally:
        release_connection(conn)


def thong_ke(van_phong_id: str, tu_ngay, den_ngay, ma_ve: str | None = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FILTER (WHERE v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den'))::int AS so_ve_da_ban,
                          COALESCE(SUM(v.gia) FILTER (WHERE v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den')), 0)::bigint AS doanh_thu,
                          COUNT(*) FILTER (WHERE v.trang_thai = 'giu_cho')::int AS so_ve_cho_thanh_toan,
                          COUNT(*) FILTER (WHERE v.trang_thai = 'da_huy')::int AS so_ve_da_huy,
                          COUNT(*) FILTER (WHERE v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den') AND v.phuong_thuc_thanh_toan = 'tien_mat')::int AS so_ve_tien_mat,
                          COUNT(*) FILTER (WHERE v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den') AND v.phuong_thuc_thanh_toan = 'chuyen_khoan')::int AS so_ve_chuyen_khoan,
                          COUNT(*) FILTER (WHERE v.kenh_ban = 'tai_quay')::int AS so_ve_tai_quay,
                          COUNT(*) FILTER (WHERE v.kenh_ban = 'hotline')::int AS so_ve_hotline
                   FROM ve v
                   WHERE v.diem_don_id = %s
                     AND v.ngay_tao >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
                     AND v.ngay_tao < ((%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
                     AND (%s::text IS NULL OR v.ma_ve ILIKE %s::text)""",
                (van_phong_id, tu_ngay, den_ngay, ma_ve, f"%{ma_ve}%" if ma_ve else None),
            )
            return _rows(cur)[0]
    finally:
        release_connection(conn)


def lich_su_ban_ve(van_phong_id: str, tu_ngay, den_ngay, trang: int, kich_thuoc_trang: int, ma_ve: str | None = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            dieu_kien = """v.diem_don_id = %s
                AND v.trang_thai IN ('da_thanh_toan', 'da_len_xe', 'da_xuong_xe', 'khong_den')
                AND v.ngay_tao >= (%s::date::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
                AND v.ngay_tao < ((%s::date + 1)::timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh')
                AND (%s::text IS NULL OR v.ma_ve ILIKE %s::text)"""
            mau_ma_ve = f"%{ma_ve}%" if ma_ve else None
            tham_so = (van_phong_id, tu_ngay, den_ngay, ma_ve, mau_ma_ve)
            cur.execute(f"SELECT COUNT(*) FROM ve v WHERE {dieu_kien}", tham_so)
            tong_so = cur.fetchone()[0]
            cur.execute(
                f"""SELECT v.id, v.ma_ve, v.ma_dat_cho, v.ngay_tao, v.gio_thanh_toan,
                           v.so_ghe, v.gia, v.trang_thai, v.phuong_thuc_thanh_toan,
                           v.kenh_ban, COALESCE(kh.ho_ten, v.ten_khach_vang_lai, '') AS ten_khach,
                           COALESCE(kh.so_dien_thoai, v.sdt_khach_vang_lai, '') AS sdt_khach,
                           nv.ho_ten AS nhan_vien_ban, c.ma AS ma_chuyen, c.gio_khoi_hanh,
                           don.ten AS ten_diem_don, tra.ten AS ten_diem_tra
                    FROM ve v
                    JOIN chuyen_xe c ON c.id = v.chuyen_id
                    JOIN diem_don_tra don ON don.id = v.diem_don_id
                    JOIN diem_don_tra tra ON tra.id = v.diem_tra_id
                    LEFT JOIN nguoi_dung kh ON kh.id = v.khach_hang_id
                    LEFT JOIN nguoi_dung nv ON nv.id = v.nhan_vien_ban_id
                    WHERE {dieu_kien}
                    ORDER BY v.ngay_tao DESC, v.id DESC
                    LIMIT %s OFFSET %s""",
                (*tham_so, kich_thuoc_trang, (trang - 1) * kich_thuoc_trang),
            )
            return {"tong_so": tong_so, "trang": trang, "kich_thuoc_trang": kich_thuoc_trang, "ve": _rows(cur)}
    finally:
        release_connection(conn)


def danh_sach_hoan_tien(van_phong_id: str, ma_dat_cho: str | None = None, sdt: str | None = None) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ht.id, ht.ve_id, v.ma_ve, v.ma_dat_cho, ht.so_tien, ht.ly_do,
                          ht.trang_thai, ht.thoi_gian_xac_dinh, ht.thoi_gian_hoan_xong
                   FROM lich_su_hoan_tien ht
                   JOIN ve v ON v.id = ht.ve_id
                   LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                   WHERE v.diem_don_id = %s
                     AND (%s IS NULL OR v.ma_dat_cho = %s)
                     AND (%s IS NULL OR COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai) = %s)
                   ORDER BY ht.thoi_gian_xac_dinh DESC LIMIT 100""",
                (van_phong_id, ma_dat_cho, ma_dat_cho, sdt, sdt),
            )
            return _rows(cur)
    finally:
        release_connection(conn)


def ve_va_chuyen(ve_id: str, van_phong_id: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT v.id, v.ma_ve, v.ma_dat_cho, v.so_ghe, v.gia, v.trang_thai,
                          v.phuong_thuc_thanh_toan, v.han_giu_cho_den,
                          v.ma_tham_chieu_vnpay, v.ma_giao_dich_cong_thanh_toan,
                          COALESCE(nd.ho_ten, v.ten_khach_vang_lai, '') AS ten_khach,
                          COALESCE(nd.so_dien_thoai, v.sdt_khach_vang_lai, '') AS sdt_khach,
                          c.ma AS ma_chuyen, c.gio_khoi_hanh, c.trang_thai AS trang_thai_chuyen,
                          c.dang_hoan, c.loai_su_co, tu.ten AS ten_tuyen,
                          lx.ten AS ten_loai_xe, x.bien_so, dd.ten AS ten_diem_don, dt.ten AS ten_diem_tra,
                          c.gio_khoi_hanh + make_interval(mins =>
                              CASE WHEN c.chieu = 'xuoi' THEN a.thoi_gian_du_kien_phut
                                   ELSE tong.tong_phut - a.thoi_gian_du_kien_phut END) AS gio_don_du_kien,
                          c.gio_khoi_hanh + make_interval(mins =>
                              CASE WHEN c.chieu = 'xuoi' THEN b.thoi_gian_du_kien_phut
                                   ELSE tong.tong_phut - b.thoi_gian_du_kien_phut END) AS gio_den_du_kien,
                          ht.id AS hoan_tien_id, ht.so_tien AS so_tien_hoan,
                          ht.ly_do AS ly_do_hoan, ht.trang_thai AS trang_thai_hoan,
                          ht.thoi_gian_xac_dinh, ht.thoi_gian_hoan_xong
                   FROM ve v LEFT JOIN nguoi_dung nd ON nd.id = v.khach_hang_id
                   JOIN chuyen_xe c ON c.id = v.chuyen_id JOIN tuyen tu ON tu.id = c.tuyen_id
                   JOIN loai_xe lx ON lx.id = c.loai_xe_id
                   LEFT JOIN xe x ON x.id = COALESCE(c.xe_thuc_te_id, c.xe_id)
                   JOIN diem_don_tra dd ON dd.id = v.diem_don_id JOIN diem_don_tra dt ON dt.id = v.diem_tra_id
                   JOIN tuyen_diem_don_tra a ON a.tuyen_id = c.tuyen_id AND a.diem_don_tra_id = v.diem_don_id
                   JOIN tuyen_diem_don_tra b ON b.tuyen_id = c.tuyen_id AND b.diem_don_tra_id = v.diem_tra_id
                   JOIN (SELECT tuyen_id, MAX(thoi_gian_du_kien_phut) AS tong_phut
                         FROM tuyen_diem_don_tra GROUP BY tuyen_id) tong ON tong.tuyen_id = c.tuyen_id
                   LEFT JOIN lich_su_hoan_tien ht ON ht.ve_id = v.id
                   WHERE v.id = %s AND v.diem_don_id = %s""",
                (ve_id, van_phong_id),
            )
            result = _rows(cur)
            return result[0] if result else None
    finally:
        release_connection(conn)
