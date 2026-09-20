"""Cơ chế khóa ghế chống bán trùng — DATABASE.md mục 4, NGHIEP_VU.md mục 6.

QUAN TRỌNG (CONTRIBUTING.md mục 5.1):
- File này do Người 2 sở hữu duy nhất.
- Tách riêng khỏi ve_repository.py để viết integration test riêng (bắt buộc
  chạy trên Postgres thật vì SELECT ... FOR UPDATE không mock được).
- PR đụng vào file này bắt buộc 2 người review (CONTRIBUTING.md mục 7.2).

Thuật toán chống trùng ghế theo chặng (mục 6 NGHIEP_VU.md):
  - Biểu diễn hành trình mỗi vé bằng khoảng [thu_tu(diem_don), thu_tu(diem_tra))
  - 2 vé trên cùng (chuyen_id, so_ghe) được phép cùng tồn tại khi và chỉ khi
    khoảng [don, tra) của chúng KHÔNG giao nhau:
      ve_moi.tra <= ve_cu.don  HOẶC  ve_cu.tra <= ve_moi.don
  - Giao nhau (bị chặn) khi: ve_moi.don < ve_cu.tra AND ve_cu.don < ve_moi.tra
"""

from app.db import get_connection, release_connection
from app.utils.loi import GiaTriLoi


def _kiem_tra_overlap(don_moi: int, tra_moi: int, ve_hien_co: list[dict]) -> bool:
    """Kiểm tra xem đoạn [don_moi, tra_moi) có giao với bất kỳ vé nào không.

    Trả về True nếu bị overlap (không thể đặt), False nếu được phép.
    Tách thành hàm riêng để unit test không cần DB (tests/unit/test_overlap_ghe.py).
    """
    for ve in ve_hien_co:
        don_cu = ve["don_thu_tu"]
        tra_cu = ve["tra_thu_tu"]
        # Giao nhau khi: don_moi < tra_cu AND don_cu < tra_moi
        if don_moi < tra_cu and don_cu < tra_moi:
            return True
    return False


def khoa_va_kiem_tra_trung_ghe(
    chuyen_id: str,
    so_ghe: str,
    diem_don_id: str,
    diem_tra_id: str,
    tuyen_id: str,
    conn,    # Nhận conn từ ngoài — bắt buộc dùng chung transaction với INSERT ve
) -> None:
    """Khóa dòng và kiểm tra overlap chặng — phải gọi trong transaction.

    Args:
        chuyen_id: UUID chuyến xe.
        so_ghe: Số ghế cần kiểm tra (VD "A1").
        diem_don_id: UUID điểm đón khách muốn đặt.
        diem_tra_id: UUID điểm trả khách muốn đặt.
        tuyen_id: UUID tuyến của chuyến — cần để JOIN lấy thu_tu.
        conn: Connection đang trong transaction — KHÔNG commit ở đây.

    Raises:
        GiaTriLoi: Nếu ghế đã bị giữ cho đoạn giao nhau.
    """
    with conn.cursor() as cur:
        # Bước 1: Lấy thu_tu của điểm đón/trả mà khách muốn đặt
        cur.execute(
            """
            SELECT
                tdd_don.thu_tu AS don_thu_tu,
                tdd_tra.thu_tu AS tra_thu_tu
            FROM tuyen_diem_don_tra tdd_don
            JOIN tuyen_diem_don_tra tdd_tra
                ON tdd_tra.tuyen_id = %s AND tdd_tra.diem_don_tra_id = %s
            WHERE tdd_don.tuyen_id = %s AND tdd_don.diem_don_tra_id = %s
            """,
            (tuyen_id, diem_tra_id, tuyen_id, diem_don_id),
        )
        row = cur.fetchone()
        if not row:
            raise GiaTriLoi("Điểm đón hoặc điểm trả không hợp lệ cho tuyến này")
        don_moi, tra_moi = row[0], row[1]
        if don_moi >= tra_moi:
            raise GiaTriLoi("Điểm đón phải đứng trước điểm trả theo thứ tự tuyến")

        # Bước 2: SELECT ... FOR UPDATE — khóa tất cả vé active trên (chuyen_id, so_ghe)
        # KHÔNG dùng UNIQUE constraint vì 1 ghế hợp lệ có nhiều vé (mục 0 DATABASE.md)
        cur.execute(
            """
            SELECT
                v.id,
                tdd_don.thu_tu AS don_thu_tu,
                tdd_tra.thu_tu AS tra_thu_tu
            FROM ve v
            JOIN tuyen_diem_don_tra tdd_don
                ON tdd_don.tuyen_id = %s AND tdd_don.diem_don_tra_id = v.diem_don_id
            JOIN tuyen_diem_don_tra tdd_tra
                ON tdd_tra.tuyen_id = %s AND tdd_tra.diem_don_tra_id = v.diem_tra_id
            WHERE v.chuyen_id = %s
              AND v.so_ghe    = %s
              AND v.trang_thai IN ('giu_cho', 'da_thanh_toan')
            FOR UPDATE
            """,
            (tuyen_id, tuyen_id, chuyen_id, so_ghe),
        )
        ve_hien_co = [
            {"don_thu_tu": r[1], "tra_thu_tu": r[2]}
            for r in cur.fetchall()
        ]

        # Bước 3: Kiểm tra overlap — tách hàm riêng để unit test được
        if _kiem_tra_overlap(don_moi, tra_moi, ve_hien_co):
            raise GiaTriLoi(f"Ghế {so_ghe} đã có người giữ cho đoạn này")
