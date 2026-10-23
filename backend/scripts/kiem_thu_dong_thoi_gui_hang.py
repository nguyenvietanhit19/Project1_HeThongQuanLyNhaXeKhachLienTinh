"""Kiểm thử ĐỒNG THỜI các thao tác gửi hàng trên PostgreSQL thật (KE_HOACH_SUA_GUI_HANG.md A3).

Unit test giả repository nên không chứng minh được tranh chấp giữa 2 transaction. Script này
gọi thẳng các hàm repository (nơi đặt điều kiện trạng thái / khóa dòng) từ 2 luồng, mỗi luồng
1 kết nối riêng. Để 2 transaction chắc chắn chồng nhau, một kết nối "cổng" giữ khóa dòng trước,
đợi cả 2 luồng cùng bị chặn ở khóa đó rồi mới nhả (xem `_chay_cung_luc`). Lặp nhiều vòng:

    1. 2 nhân viên cùng giao 1 đơn            → đúng 1 bên thành công
    2. Hủy đơn đúng lúc phụ xe chất hàng       → đúng 1 bên thành công, dữ liệu không lai
    3. Ghi liên hệ đúng lúc giao               → giao luôn thành công; liên hệ chỉ ghi nếu xong TRƯỚC giao
    4. 2 nhân viên cùng hủy 1 đơn              → đúng 1 bên thành công, hoàn tiền 1 lần
    5. 2 request tạo đơn cùng Idempotency-Key  → 1 đơn duy nhất, cả 2 nhận cùng đơn

Chạy trên DB LOCAL (đã có dữ liệu từ seed_gui_hang_demo.py):

    docker compose exec backend python scripts/kiem_thu_dong_thoi_gui_hang.py [so_vong]

Đơn thử được đánh dấu `ten_nguoi_gui = 'A3 DONG THOI'` và xóa hết khi kết thúc (kể cả khi lỗi).
"""

import os
import random
import sys
import threading
import time
from collections import Counter
from urllib.parse import urlparse
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import DATABASE_URL  # noqa: E402
from app.db import get_connection, release_connection  # noqa: E402
from app.repositories import don_hang_repository as repo  # noqa: E402

DANH_DAU = "A3 DONG THOI"
SO_VONG = int(sys.argv[1]) if len(sys.argv) > 1 else 30
# Bên nào thắng ở mỗi vòng — nếu chỉ 1 bên luôn thắng thì 2 luồng chưa thật sự chồng nhau.
KET_CUC: Counter = Counter()


def _sql(cau_lenh: str, tham_so: tuple = (), lay: str | None = None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(cau_lenh, tham_so)
            kq = cur.fetchone() if lay == "mot" else cur.fetchall() if lay == "het" else None
        conn.commit()
        return kq
    finally:
        release_connection(conn)


def _chuan_bi() -> dict:
    """Lấy 1 văn phòng gửi, 1 văn phòng nhận có >= 2 nhân viên, tuyến nối 2 điểm, 1 chuyến của tuyến."""
    hang = _sql(
        """SELECT h.van_phong_id::text, array_agg(nd.id::text ORDER BY nd.email)
           FROM ho_so_can_bo_diem h JOIN nguoi_dung nd ON nd.id = h.nguoi_dung_id
           WHERE nd.vai_tro = 'nhan_vien_gui_hang' AND nd.dang_hoat_dong
           GROUP BY h.van_phong_id""",
        lay="het",
    )
    nhan = next(((vp, nv) for vp, nv in hang if len(nv) >= 2), None)
    if not nhan:
        sys.exit("Cần 1 văn phòng có >= 2 nhân viên gửi hàng — chạy seed_gui_hang_demo.py trước.")
    for vp_gui, nv_gui in hang:
        if vp_gui == nhan[0]:
            continue
        tuyen = repo.tim_cac_tuyen_qua_hai_diem(vp_gui, nhan[0])
        if not tuyen:
            continue
        chuyen = _sql("SELECT id::text FROM chuyen_xe WHERE tuyen_id = %s LIMIT 1", (str(tuyen[0]["id"]),), "mot")
        if not chuyen:
            continue
        loai = _sql("SELECT id::text FROM loai_hang WHERE NOT la_hang_cam LIMIT 1", lay="mot")
        return {
            "vp_gui": vp_gui, "nv_gui": nv_gui, "vp_nhan": nhan[0], "nv_nhan": nhan[1],
            "tuyen": str(tuyen[0]["id"]), "chuyen": chuyen[0], "loai": loai[0],
        }
    sys.exit("Không tìm được cặp văn phòng có tuyến + chuyến — chạy seed_gui_hang_demo.py trước.")


def _du_lieu_don(ctx: dict, phuong_thuc: str = "nguoi_gui_tra_truoc", khoa: str | None = None) -> dict:
    tra_truoc = phuong_thuc == "nguoi_gui_tra_truoc"
    return {
        "ma_van_don": f"A3-{uuid4().hex[:12].upper()}", "tuyen_id": ctx["tuyen"],
        "diem_gui_id": ctx["vp_gui"], "diem_nhan_id": ctx["vp_nhan"], "loai_hang_id": ctx["loai"],
        "can_nang_kg": 1, "dai_cm": None, "rong_cm": None, "cao_cm": None, "gia_cuoc": 50000,
        "ten_nguoi_gui": DANH_DAU, "sdt_nguoi_gui": "0912345678",
        "ten_nguoi_nhan": DANH_DAU, "sdt_nguoi_nhan": "0987654321",
        "phuong_thuc_thanh_toan": phuong_thuc, "nhan_vien_gui_id": ctx["nv_gui"][0],
        "da_thu_tien": tra_truoc, "nhan_vien_thu_id": ctx["nv_gui"][0] if tra_truoc else None,
        "khoa_chong_trung": khoa,
    }


def _tao_don(ctx: dict, trang_thai: str = "cho_van_chuyen") -> str:
    don_id = str(repo.tao_don_hang(_du_lieu_don(ctx))["id"])
    if trang_thai == "cho_lay":
        _sql("UPDATE don_hang SET trang_thai = 'cho_lay', chuyen_id = %s, thoi_gian_den_diem_nhan = now() WHERE id = %s",
             (ctx["chuyen"], don_id))
    return don_id


class KhongChongNhau(Exception):
    """Các luồng không cùng bị chặn ở khóa cổng → vòng đó không chứng minh được gì."""


def _so_phien_dang_cho_khoa() -> int:
    return _sql(
        """SELECT count(*) FROM pg_stat_activity
           WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()""",
        lay="mot",
    )[0]


def _chay_cung_luc(giu_khoa, *viec):
    """Chạy các hàm sao cho transaction của chúng THẬT SỰ chồng nhau.

    Chỉ dùng Barrier thì luồng nào tới DB trước thường đã commit xong trước khi luồng kia bắt đầu
    (đo thử: 1 bên thắng 50/50 vòng). Ở đây một kết nối "cổng" giữ khóa trước (`giu_khoa(cur)`),
    các luồng chạy tới và bị chặn ở đúng khóa đó; chỉ khi pg_stat_activity thấy đủ N phiên đang
    chờ mới nhả cổng (rollback). Thứ tự khởi động các luồng đảo ngẫu nhiên để bên nào cũng có lúc thắng.
    Trả về list kết quả (hoặc exception) theo đúng thứ tự `viec`."""
    cong = get_connection()
    kq: list = [None] * len(viec)

    def chay(i, f):
        try:
            kq[i] = f()
        except Exception as exc:  # noqa: BLE001 — ghi lại để kiểm tra, không làm chết luồng
            kq[i] = exc

    try:
        with cong.cursor() as cur:
            giu_khoa(cur)
        thu_tu = random.sample(range(len(viec)), len(viec))
        luong = {i: threading.Thread(target=chay, args=(i, viec[i])) for i in thu_tu}
        for i in thu_tu:
            luong[i].start()
            time.sleep(0.02)  # để luồng vào hàng đợi khóa theo đúng thứ tự khởi động
        han = time.monotonic() + 5
        while _so_phien_dang_cho_khoa() < len(viec):
            if time.monotonic() > han:
                cong.rollback()
                for t in luong.values():
                    t.join()
                raise KhongChongNhau(f"chỉ {_so_phien_dang_cho_khoa()}/{len(viec)} luồng chờ khóa")
            time.sleep(0.01)
    finally:
        cong.rollback()
        release_connection(cong)
    for t in luong.values():
        t.join()
    return kq


def _khoa_dong_don(don: str):
    return lambda cur: cur.execute("SELECT 1 FROM don_hang WHERE id = %s FOR UPDATE", (don,))


def _loi_bat_ngo(kq) -> list:
    return [x for x in kq if isinstance(x, Exception) and not isinstance(x, repo.DonKhongConChoLay)]


# ---------------------------------------------------------------------
# Các tình huống — mỗi hàm trả None nếu đúng, chuỗi mô tả nếu sai
# ---------------------------------------------------------------------

def tinh_huong_giao_giao(ctx):
    don = _tao_don(ctx, "cho_lay")
    kq = _chay_cung_luc(
        _khoa_dong_don(don),
        lambda: repo.cap_nhat_giao_hang(don, ctx["nv_nhan"][0], ctx["vp_nhan"]),
        lambda: repo.cap_nhat_giao_hang(don, ctx["nv_nhan"][1], ctx["vp_nhan"]),
    )
    if _loi_bat_ngo(kq):
        return f"lỗi bất ngờ {_loi_bat_ngo(kq)}"
    if sum(x is not None for x in kq) != 1:
        return f"{sum(x is not None for x in kq)} bên thành công"
    KET_CUC["giao", "nhân viên 1 thắng" if kq[0] is not None else "nhân viên 2 thắng"] += 1
    nguoi = _sql("SELECT nhan_vien_nhan_id::text FROM don_hang WHERE id = %s", (don,), "mot")[0]
    thang = ctx["nv_nhan"][0] if kq[0] is not None else ctx["nv_nhan"][1]
    return None if nguoi == thang else "người giao ghi trong DB khác bên thành công"


def tinh_huong_huy_chat(ctx):
    don = _tao_don(ctx)
    kq = _chay_cung_luc(
        _khoa_dong_don(don),
        lambda: repo.huy_don(don, ctx["nv_gui"][0], ctx["vp_gui"], "khach_doi_y", None),
        lambda: repo.cap_nhat_chat_hang_len_chuyen(don, ctx["chuyen"]),
    )
    if _loi_bat_ngo(kq):
        return f"lỗi bất ngờ {_loi_bat_ngo(kq)}"
    if sum(x is not None for x in kq) != 1:
        return f"{sum(x is not None for x in kq)} bên thành công"
    KET_CUC["huy_chat", "hủy thắng" if kq[0] is not None else "chất thắng"] += 1
    tt, chuyen, ly_do = _sql("SELECT trang_thai, chuyen_id::text, ly_do_huy FROM don_hang WHERE id = %s", (don,), "mot")
    if kq[0] is not None:
        return None if (tt, chuyen, ly_do) == ("da_huy", None, "khach_doi_y") else f"hủy thắng nhưng DB: {tt}, {chuyen}, {ly_do}"
    return None if (tt, chuyen, ly_do) == ("da_len_xe", ctx["chuyen"], None) else f"chất thắng nhưng DB: {tt}, {chuyen}, {ly_do}"


def tinh_huong_lien_he_giao(ctx):
    don = _tao_don(ctx, "cho_lay")
    kq = _chay_cung_luc(
        _khoa_dong_don(don),
        lambda: repo.ghi_lien_he(don, ctx["nv_nhan"][1], "nguoi_nhan", "da_lien_he", None, True, [], None),
        lambda: repo.cap_nhat_giao_hang(don, ctx["nv_nhan"][0], ctx["vp_nhan"]),
    )
    if _loi_bat_ngo(kq):
        return f"lỗi bất ngờ {_loi_bat_ngo(kq)}"
    if kq[1] is None:
        return "giao hàng bị chặn (liên hệ không được chặn giao)"
    so_lien_he = _sql("SELECT count(*) FROM lich_su_lien_he_don_hang WHERE don_hang_id = %s", (don,), "mot")[0]
    lien_he_ok = not isinstance(kq[0], Exception)
    KET_CUC["lien_he", "liên hệ kịp trước giao" if lien_he_ok else "liên hệ bị chặn (đã giao)"] += 1
    if lien_he_ok != (so_lien_he == 1):
        return f"liên hệ {'thành công' if lien_he_ok else 'bị chặn'} nhưng có {so_lien_he} dòng lịch sử"
    return None


def tinh_huong_huy_huy(ctx):
    don = _tao_don(ctx)
    kq = _chay_cung_luc(
        _khoa_dong_don(don),
        lambda: repo.huy_don(don, ctx["nv_gui"][0], ctx["vp_gui"], "khach_doi_y", None),
        lambda: repo.huy_don(don, ctx["nv_gui"][-1], ctx["vp_gui"], "nhap_sai_thong_tin", None),
    )
    if _loi_bat_ngo(kq):
        return f"lỗi bất ngờ {_loi_bat_ngo(kq)}"
    if sum(x is not None for x in kq) != 1:
        return f"{sum(x is not None for x in kq)} bên thành công"
    ly_do, hoan = _sql("SELECT ly_do_huy, so_tien_hoan FROM don_hang WHERE id = %s", (don,), "mot")
    KET_CUC["huy_huy", "lần hủy 1 thắng" if kq[0] is not None else "lần hủy 2 thắng"] += 1
    mong = "khach_doi_y" if kq[0] is not None else "nhap_sai_thong_tin"
    return None if (ly_do, int(hoan or 0)) == (mong, 50000) else f"DB: {ly_do}, hoàn {hoan}"


def tinh_huong_tao_cung_khoa(ctx):
    khoa = f"a3-{uuid4().hex}"

    def giu_khoa_chong_trung(cur):
        # Cổng chèn trước 1 dòng cùng khóa nhưng chưa commit: INSERT của 2 luồng chờ ở unique index.
        d = _du_lieu_don(ctx, "cod_nguoi_nhan_tra", khoa)
        cur.execute(
            """INSERT INTO don_hang (ma_van_don, tuyen_id, diem_gui_id, diem_nhan_id, loai_hang_id, can_nang_kg,
                   gia_cuoc, ten_nguoi_gui, sdt_nguoi_gui, ten_nguoi_nhan, sdt_nguoi_nhan,
                   phuong_thuc_thanh_toan, nhan_vien_gui_id, trang_thai, khoa_chong_trung)
               VALUES (%(ma_van_don)s, %(tuyen_id)s, %(diem_gui_id)s, %(diem_nhan_id)s, %(loai_hang_id)s,
                   %(can_nang_kg)s, %(gia_cuoc)s, %(ten_nguoi_gui)s, %(sdt_nguoi_gui)s, %(ten_nguoi_nhan)s,
                   %(sdt_nguoi_nhan)s, %(phuong_thuc_thanh_toan)s, %(nhan_vien_gui_id)s, 'cho_van_chuyen',
                   %(khoa_chong_trung)s)""",
            d,
        )

    kq = _chay_cung_luc(
        giu_khoa_chong_trung,
        lambda: repo.tao_don_hang(_du_lieu_don(ctx, "cod_nguoi_nhan_tra", khoa)),
        lambda: repo.tao_don_hang(_du_lieu_don(ctx, "cod_nguoi_nhan_tra", khoa)),
    )
    if _loi_bat_ngo(kq):
        return f"lỗi bất ngờ {_loi_bat_ngo(kq)}"
    so_don = _sql("SELECT count(*) FROM don_hang WHERE khoa_chong_trung = %s", (khoa,), "mot")[0]
    if so_don != 1:
        return f"{so_don} đơn cùng khóa"
    return None if str(kq[0]["id"]) == str(kq[1]["id"]) else "2 request nhận 2 đơn khác nhau"


TINH_HUONG = [
    ("2 nhân viên cùng giao 1 đơn", tinh_huong_giao_giao, "giao"),
    ("Hủy đơn đúng lúc phụ xe chất hàng", tinh_huong_huy_chat, "huy_chat"),
    ("Ghi liên hệ đúng lúc giao", tinh_huong_lien_he_giao, "lien_he"),
    ("2 nhân viên cùng hủy 1 đơn", tinh_huong_huy_huy, "huy_huy"),
    ("2 request tạo đơn cùng Idempotency-Key", tinh_huong_tao_cung_khoa, None),
]


def _mot_vong(ham, ctx) -> str | None:
    try:
        return ham(ctx)
    except KhongChongNhau as exc:
        return f"không chồng nhau: {exc}"


def main():
    host = urlparse(DATABASE_URL or "").hostname or ""
    if host not in ("db", "localhost", "127.0.0.1"):
        sys.exit(f"Từ chối chạy: DATABASE_URL trỏ tới '{host}', script này chỉ dành cho DB local.")

    ctx = _chuan_bi()
    co_loi = False
    try:
        for ten, ham, nhom in TINH_HUONG:
            loi = [(v, l) for v in range(1, SO_VONG + 1) if (l := _mot_vong(ham, ctx))]
            co_loi |= bool(loi)
            phan_bo = ", ".join(f"{k[1]} {n}" for k, n in sorted(KET_CUC.items()) if k[0] == nhom)
            print(f"{'OK  ' if not loi else 'SAI '} {ten}: {SO_VONG - len(loi)}/{SO_VONG} vòng đúng"
                  + (f"  ({phan_bo})" if phan_bo else ""))
            for v, l in loi[:5]:
                print(f"       vòng {v}: {l}")
    finally:
        _sql("DELETE FROM don_hang WHERE ten_nguoi_gui = %s", (DANH_DAU,))
    sys.exit(1 if co_loi else 0)


if __name__ == "__main__":
    main()
