"""Tìm kiếm chuyến xe công khai — UC-04.

Logic nghiệp vụ tìm chuyến theo cặp khu_vuc + ngày (mục 3.4 bước 1–3
NGHIEP_VU.md). Điểm đón hợp lệ = van_phong thuộc khu_vuc đi, đứng trước
ít nhất 1 điểm thuộc khu_vuc đến — khớp định nghĩa "tuyến đi qua cả 2
khu_vuc theo đúng chiều".
"""

import datetime

from app.db import get_connection, release_connection


def _row_to_dict(cur, row):
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _rows_to_list(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


def tim_chuyen(diem_di_id: str, diem_den_id: str, ngay_di: datetime.date) -> list[dict]:
    """UC-04 bước 2: Tìm mọi chuyến chạy đúng ngày và đi qua cặp khu_vuc.

    Điều kiện (mục 3.4 bước 1 NGHIEP_VU.md):
    - Có ít nhất 1 diem_don_tra loại 'van_phong' thuộc khu_vuc điểm đi
      nằm trong tuyến (van_phong vì điểm đón phải là văn phòng, mục 3.1).
    - Có ít nhất 1 diem_don_tra (van_phong hoặc diem_dung) thuộc khu_vuc điểm đến
      đứng SAU điểm đón trên (thu_tu lớn hơn).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT
                    cx.id,
                    cx.tuyen_id,
                    t.ten                      AS ten_tuyen,
                    lx.ten                     AS loai_xe_ten,
                    lx.he_so_gia,
                    x.bien_so,
                    cx.gio_khoi_hanh,
                    cx.trang_thai,
                    cx.dang_hoan,
                    cx.loai_xe_id,
                    -- Số ghế trống: tính gần đúng ở đây, Service sẽ tính chính xác hơn
                    -- nếu cần. Trả về tổng ghế - vé active để hiển thị nhanh.
                    (
                        SELECT COUNT(DISTINCT ghe_val)
                        FROM jsonb_array_elements_text(lx.so_do_ghe) AS ghe_val
                    ) - (
                        SELECT COUNT(DISTINCT v2.so_ghe)
                        FROM ve v2
                        WHERE v2.chuyen_id = cx.id
                          AND v2.trang_thai IN ('giu_cho', 'da_thanh_toan')
                    )                          AS so_ghe_trong,
                    -- Giá từ: gia_goc * he_so_gia của loại xe (mục 3.1 NGHIEP_VU.md)
                    COALESCE(
                        (
                            SELECT ROUND(gv.gia_goc * lx.he_so_gia)
                            FROM gia_ve gv
                            WHERE gv.tuyen_id = cx.tuyen_id
                              AND gv.diem_di_id  = %s
                              AND gv.diem_den_id = %s
                              AND (gv.ap_dung_tu IS NULL OR gv.ap_dung_tu <= CURRENT_DATE)
                              AND (gv.ap_dung_den IS NULL OR gv.ap_dung_den >= CURRENT_DATE)
                            ORDER BY gv.ap_dung_tu DESC NULLS LAST
                            LIMIT 1
                        ),
                        0
                    )                          AS gia_tu
                FROM chuyen_xe cx
                JOIN tuyen t ON t.id = cx.tuyen_id
                JOIN loai_xe lx ON lx.id = cx.loai_xe_id
                LEFT JOIN xe x ON x.id = COALESCE(cx.xe_thuc_te_id, cx.xe_id)
                -- Điều kiện 1: tuyến có điểm đón van_phong thuộc khu_vuc đi
                WHERE EXISTS (
                    SELECT 1
                    FROM tuyen_diem_don_tra tdd_don
                    JOIN diem_don_tra ddt_don
                        ON ddt_don.id = tdd_don.diem_don_tra_id
                    WHERE tdd_don.tuyen_id = cx.tuyen_id
                      AND ddt_don.khu_vuc_id = %s
                      AND ddt_don.loai = 'van_phong'
                      -- Điều kiện 2: phải có điểm đến đứng SAU điểm đón
                      AND EXISTS (
                          SELECT 1
                          FROM tuyen_diem_don_tra tdd_den
                          JOIN diem_don_tra ddt_den
                              ON ddt_den.id = tdd_den.diem_don_tra_id
                          WHERE tdd_den.tuyen_id = cx.tuyen_id
                            AND ddt_den.khu_vuc_id = %s
                            AND tdd_den.thu_tu > tdd_don.thu_tu
                      )
                )
                -- Lọc đúng ngày
                AND DATE(cx.gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh') = %s
                AND cx.trang_thai NOT IN ('hoan_thanh', 'da_huy')
                ORDER BY cx.gio_khoi_hanh
                """,
                (diem_di_id, diem_den_id, diem_di_id, diem_den_id, ngay_di),
            )
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)


def lay_so_do_ghe(chuyen_id: str, diem_di_id: str, diem_den_id: str) -> dict | None:
    """UC-04 bước 4: Lấy sơ đồ ghế + trạng thái ghế cho 1 chuyến cụ thể.

    Tính trạng thái ghế theo đoạn RỘNG NHẤT (mục 3.4 bước 3 NGHIEP_VU.md):
    - don_thu_tu = thu_tu nhỏ nhất của van_phong thuộc khu_vuc đi trong tuyến
    - tra_thu_tu = thu_tu lớn nhất của điểm bất kỳ thuộc khu_vuc đến trong tuyến
    Ghế "đã giữ" = có vé active overlap đoạn rộng này.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Lấy thông tin chuyến + sơ đồ ghế
            cur.execute(
                """
                SELECT cx.id, cx.tuyen_id, lx.ten AS loai_xe_ten, lx.so_do_ghe,
                       cx.gio_khoi_hanh, cx.trang_thai, cx.dang_hoan
                FROM chuyen_xe cx
                JOIN loai_xe lx ON lx.id = cx.loai_xe_id
                WHERE cx.id = %s
                """,
                (chuyen_id,),
            )
            chuyen = _row_to_dict(cur, cur.fetchone())
            if not chuyen:
                return None

            tuyen_id = chuyen["tuyen_id"]

            # Đoạn rộng nhất: thu_tu nhỏ nhất của van_phong khu_vuc đi
            cur.execute(
                """
                SELECT MIN(tdd.thu_tu) AS don_thu_tu
                FROM tuyen_diem_don_tra tdd
                JOIN diem_don_tra ddt ON ddt.id = tdd.diem_don_tra_id
                WHERE tdd.tuyen_id = %s
                  AND ddt.khu_vuc_id = %s
                  AND ddt.loai = 'van_phong'
                """,
                (tuyen_id, diem_di_id),
            )
            don_row = cur.fetchone()
            don_thu_tu = don_row[0] if don_row else None

            # Thu_tu lớn nhất của điểm bất kỳ khu_vuc đến
            cur.execute(
                """
                SELECT MAX(tdd.thu_tu) AS tra_thu_tu
                FROM tuyen_diem_don_tra tdd
                JOIN diem_don_tra ddt ON ddt.id = tdd.diem_don_tra_id
                WHERE tdd.tuyen_id = %s
                  AND ddt.khu_vuc_id = %s
                """,
                (tuyen_id, diem_den_id),
            )
            tra_row = cur.fetchone()
            tra_thu_tu = tra_row[0] if tra_row else None

            if don_thu_tu is None or tra_thu_tu is None:
                return None

            # Ghế đã bị giữ trong đoạn rộng này
            cur.execute(
                """
                SELECT DISTINCT v.so_ghe
                FROM ve v
                JOIN tuyen_diem_don_tra tdd_don
                    ON tdd_don.tuyen_id = %s AND tdd_don.diem_don_tra_id = v.diem_don_id
                JOIN tuyen_diem_don_tra tdd_tra
                    ON tdd_tra.tuyen_id = %s AND tdd_tra.diem_don_tra_id = v.diem_tra_id
                WHERE v.chuyen_id = %s
                  AND v.trang_thai IN ('giu_cho', 'da_thanh_toan')
                  -- Overlap với đoạn rộng [don_thu_tu, tra_thu_tu)
                  AND tdd_don.thu_tu < %s
                  AND %s < tdd_tra.thu_tu
                """,
                (tuyen_id, tuyen_id, chuyen_id, tra_thu_tu, don_thu_tu),
            )
            ghe_da_chon = [r[0] for r in cur.fetchall()]

            # Điểm đón hợp lệ (chỉ van_phong thuộc khu_vuc đi)
            cur.execute(
                """
                SELECT ddt.id, ddt.ten, ddt.dia_chi, ddt.loai,
                       tdd.thu_tu, tdd.thoi_gian_du_kien_phut
                FROM tuyen_diem_don_tra tdd
                JOIN diem_don_tra ddt ON ddt.id = tdd.diem_don_tra_id
                WHERE tdd.tuyen_id = %s
                  AND ddt.khu_vuc_id = %s
                  AND ddt.loai = 'van_phong'
                ORDER BY tdd.thu_tu
                """,
                (tuyen_id, diem_di_id),
            )
            diem_don_hop_le = _rows_to_list(cur, cur.fetchall())

            # Điểm trả hợp lệ (van_phong + diem_dung thuộc khu_vuc đến, đứng sau điểm đón)
            cur.execute(
                """
                SELECT ddt.id, ddt.ten, ddt.dia_chi, ddt.loai,
                       tdd.thu_tu, tdd.thoi_gian_du_kien_phut
                FROM tuyen_diem_don_tra tdd
                JOIN diem_don_tra ddt ON ddt.id = tdd.diem_don_tra_id
                WHERE tdd.tuyen_id = %s
                  AND ddt.khu_vuc_id = %s
                  AND tdd.thu_tu > %s
                ORDER BY tdd.thu_tu
                """,
                (tuyen_id, diem_den_id, don_thu_tu),
            )
            diem_tra_hop_le = _rows_to_list(cur, cur.fetchall())

            return {
                **chuyen,
                "ghe_da_chon": ghe_da_chon,
                "diem_don_hop_le": diem_don_hop_le,
                "diem_tra_hop_le": diem_tra_hop_le,
            }
    finally:
        release_connection(conn)


def lay_danh_sach_khu_vuc() -> list[dict]:
    """Lấy danh sách khu_vuc cho dropdown tìm kiếm (UC-04 bước 1)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ten, tinh_thanh FROM khu_vuc ORDER BY tinh_thanh, ten"
            )
            return _rows_to_list(cur, cur.fetchall())
    finally:
        release_connection(conn)
