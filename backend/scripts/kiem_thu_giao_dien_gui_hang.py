"""Kiểm thử tự động GIAO DIỆN role nhân viên gửi hàng — chạy các ca của QUY_TRINH_TEST_GUI_HANG.md trên trình duyệt thật.

Playwright điều khiển Microsoft Edge (chạy ẩn). Chạy trên MÁY (không chạy trong container), cần:
  - Docker đang chạy backend + db (http://localhost:8000), đã `yoyo apply` migration
  - VS Code Live Server đang phục vụ frontend ở http://127.0.0.1:5501 (cổng trong .vscode/settings.json)
  - `.\\.venv\\Scripts\\pip install -r backend/scripts/requirements-kiem-thu-giao-dien.txt` (1 lần)

Cách chạy (từ thư mục gốc dự án):
    .\\.venv\\Scripts\\python backend/scripts/kiem_thu_giao_dien_gui_hang.py khoi      # bộ [Khói], ~1 phút
    .\\.venv\\Scripts\\python backend/scripts/kiem_thu_giao_dien_gui_hang.py day-du    # các ca còn lại, ~4 phút
    .\\.venv\\Scripts\\python backend/scripts/kiem_thu_giao_dien_gui_hang.py tat-ca    # cả hai
Thêm `--hien` để xem trình duyệt chạy, `--anh <thư mục>` để chọn nơi lưu ảnh chụp / CSV (mặc định thư mục tạm).

CHỈ DÙNG CHO DB LOCAL: đầu mỗi bộ, script chạy lại `seed_gui_hang_demo.py` (xóa và tạo lại đơn demo), tạo 1 tài khoản tạm
(xóa khi xong), sinh token quản lý trong container, đổi rồi trả lại mật khẩu tài khoản demo Yên Bái, và khởi động lại backend
(ca I2). Dữ liệu demo bị các ca test thay đổi — muốn test tay sau đó thì seed lại.
Mã thoát: 0 = mọi ca đạt, 1 = có ca lỗi.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

FE = "http://127.0.0.1:5501"
BE = "http://localhost:8000"
MK = "GuiHang@123"
REPO = str(Path(__file__).resolve().parents[2])
_tham_so = argparse.ArgumentParser(description="Kiểm thử tự động giao diện gửi hàng")
_tham_so.add_argument("bo", choices=["khoi", "day-du", "tat-ca"], help="bộ ca cần chạy")
_tham_so.add_argument("--hien", action="store_true", help="hiện cửa sổ trình duyệt")
_tham_so.add_argument("--anh", help="thư mục lưu ảnh chụp / file tải về")
THAM_SO = _tham_so.parse_args()
ANH = Path(THAM_SO.anh or Path(tempfile.gettempdir()) / "kiem_thu_giao_dien_gui_hang" / datetime.now().strftime("%Y%m%d-%H%M%S"))
ANH.mkdir(parents=True, exist_ok=True)
KQ: list[tuple[str, str, str]] = []
CONSOLE: list[str] = []
MA: dict[str, str] = {}
MO_TA = {  # khóa → câu mô tả của đơn trong output seed_gui_hang_demo.py
    "md_cho_xep_tra_truoc": "thử HỦY ĐƠN (hoàn 100.000đ)",
    "md_cho_xep_cod": "Chờ xếp xe, người nhận trả cước — hủy thì không hoàn tiền",
    "md_cho_xep_2_ngay": "Chờ xếp xe đã 2 ngày",
    "md_da_huy_hom_nay": "Đã hủy hôm nay, đã hoàn 95.000đ",
    "md_su_co": "Sắp đến nhưng chuyến GẶP SỰ CỐ (sạt lở)",
    "lc_cho_xep": "thử HỦY ĐƠN (hoàn 110.000đ)",
    "lc_dang_hoan": "Sắp đến nhưng chuyến ĐANG HOÃN",
    "lc_xe_dang_chay": "rồi DỠ HÀNG để thấy thông báo real-time",
    "lc_de_vo_tren_xe": "Sắp đến (xe 24B-888.01), hàng dễ vỡ, COD",
    "lc_cho_goi_bao": "Vừa tới, CHỜ GỌI BÁO",
    "lc_goi_truot": "Vừa tới, đã gọi 1 lần không được, COD",
    "lc_hu_hong": "Chờ lấy, có BÁO CÁO HƯ HỎNG",
    "lc_cod_55": "Chờ lấy, đã báo người nhận, COD 55.000đ",
    "lc_giao_tra_truoc": "Chờ lấy, đã báo, trả trước — thử GIAO HÀNG",
    "lc_sua_sdt": "Đã SỬA SĐT người nhận",
    "lc_7_da_bao": "Chờ quá 7 NGÀY, đã từng báo người nhận",
    "lc_7_chua_bao": "Chờ quá 7 NGÀY, CHƯA từng báo được",
    "lc_ton_16": "HÀNG TỒN (16 ngày), không liên hệ được ai",
    "lc_ton_thoa_thuan": "HÀNG TỒN đã thỏa thuận với người gửi",
    "lc_24h_da_nhac": "ĐÃ NHẮC 24h",
    "lc_da_giao": "Đã giao hôm nay, thu COD 75.000đ",
}


# ------------------------------------------------------------------ tiện ích
def ca(ma: str, ten: str):
    def boc(fn):
        def chay(*a, **kw):
            t0 = time.time()
            try:
                ghi = fn(*a, **kw) or ""
                KQ.append((ma, "ĐẠT", f"{ten}. {ghi}".strip()))
            except BoQua as e:
                KQ.append((ma, "BỎ QUA", f"{ten}: {e}"))
            except Exception as e:  # noqa: BLE001
                KQ.append((ma, "LỖI", f"{ten}: {type(e).__name__}: {str(e).splitlines()[0][:300]}"))
                traceback.print_exc()
                for p in a:
                    if isinstance(p, Page):
                        try:
                            p.screenshot(path=str(ANH / f"{ma}_LOI.png"), full_page=True)
                        except Exception:  # noqa: BLE001
                            pass
                        break
            print(f"  {ma} xong ({time.time() - t0:.1f}s) → {KQ[-1][1]}", flush=True)
            for p in a:  # mỗi ca bắt đầu sạch: đóng modal còn mở
                if isinstance(p, Page):
                    try:
                        dong_het_modal(p)
                    except Exception:  # noqa: BLE001
                        pass
        return chay
    return boc


class BoQua(Exception):
    pass


def docker(*lenh: str, timeout=300) -> str:
    r = subprocess.run(["docker", "compose", *lenh], cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    return r.stdout + r.stderr


def py_backend(code: str) -> str:
    return docker("exec", "-T", "backend", "python", "-c", code)


def api(method, path, token=None, body=None, loi_ok=False):
    req = urllib.request.Request(BE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        if not loi_ok:
            raise AssertionError(f"{method} {path} → {e.code} {e.read()[:200]!r}") from None
        return e.code, json.loads(e.read() or b"null")


def token_dang_nhap(email, mk=MK):
    return api("POST", "/auth/dang-nhap", body={"email": email, "mat_khau": mk})[1]["token"]


def dong_het_modal(page: Page):
    page.evaluate("document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'))")


def chon(page: Page, sel: str, chua: str):
    nhan = [t for t in page.locator(f"{sel} option").all_inner_texts() if chua.lower() in t.lower()]
    assert nhan, f"{sel} không có lựa chọn chứa '{chua}'"
    page.select_option(sel, label=nhan[0])


def dang_nhap(page: Page, email: str, mk: str = MK):
    page.goto(f"{FE}/nhan-vien/dang-nhap.html")
    page.evaluate("localStorage.clear(); sessionStorage.clear()")
    page.goto(f"{FE}/nhan-vien/dang-nhap.html")
    page.fill("#email", email)
    page.fill("#mat_khau", mk)
    page.click("#form-dang-nhap button[type=submit]")
    page.wait_for_url(re.compile(r"/gui-hang/"), timeout=15000)
    page.wait_for_selector("#nv-sidebar [data-tab]", timeout=15000)
    page.wait_for_load_state("networkidle")


def vao_bang_token(page: Page, token: str, vai_tro: str, ho_ten: str):
    page.goto(f"{FE}/nhan-vien/dang-nhap.html")
    page.evaluate("([t, v, h]) => { localStorage.clear(); localStorage.setItem('token', t); localStorage.setItem('vai_tro', v); localStorage.setItem('ho_ten', h); }",
                  [token, vai_tro, ho_ten])
    page.goto(f"{FE}/nhan-vien/gui-hang/index.html")
    page.wait_for_load_state("networkidle")


def mo_tab(page: Page, tab: str):
    dong_het_modal(page)
    page.click(f"#nv-sidebar [data-tab='{tab}']")
    expect(page.locator(f"#tab-{tab}")).to_have_class(re.compile(r"\bactive\b"))
    page.wait_for_load_state("networkidle")


def toast_cuoi(page: Page, chua: str = "", timeout=8000) -> str:
    page.wait_for_function(
        "c => [...document.querySelectorAll('#toastContainer .toast-item')].some(t => t.innerText.includes(c))", arg=chua, timeout=timeout)
    return [t for t in page.locator("#toastContainer .toast-item").all_inner_texts() if chua in t][-1].replace("\n", " ")


def xoa_toast(page: Page):
    page.evaluate("document.querySelectorAll('#toastContainer .toast-item').forEach(t => t.remove())")


def dong_hang_den(page: Page, ma: str):
    page.fill("#inputTraCuuGiao", ma)
    page.wait_for_function("m => document.querySelector('#tbodyHangDen').innerText.includes(m)", arg=ma, timeout=8000)
    return page.locator("#tbodyHangDen tr", has_text=ma)


def dong_don_gui(page: Page, ma: str):
    mo_tab(page, "don-gui")
    page.fill("#inputTuKhoaDonGui", ma)
    page.wait_for_function("m => { const r = document.querySelectorAll('#tbodyDonGui tr'); return r.length === 1 && r[0].innerText.includes(m); }",
                           arg=ma, timeout=8000)
    return page.locator("#tbodyDonGui tr").first


def chi_tiet(page: Page, ma: str) -> str:
    dong_het_modal(page)
    page.evaluate("m => moChiTietDon(m)", ma)
    expect(page.locator("#modalChiTietDon")).to_have_class(re.compile("active"), timeout=8000)
    page.wait_for_function("m => document.querySelector('#ctMaVanDon').innerText.trim() === m", arg=ma)
    page.wait_for_timeout(600)  # lịch sử tải sau
    return page.locator("#modalChiTietDon").inner_text()


def so(page: Page, sel: str) -> int:
    return int(re.sub(r"[^\d-]", "", page.locator(sel).inner_text()) or 0)


# ================================================================== A. Quyền
@ca("A2", "Phụ xe mở thẳng trang gửi hàng → báo không có quyền, bị đăng xuất")
def a2(page: Page):
    hop_thoai = []
    page.once("dialog", lambda d: (hop_thoai.append(d.message), d.accept()))
    vao_bang_token(page, token_dang_nhap("phuxe.guihang@demo.nhaxe.vn", "PhuXe@123"), "phu_xe", "Phụ xe")
    page.wait_for_url(re.compile("dang-nhap"), timeout=8000)
    assert hop_thoai and "không có quyền" in hop_thoai[0], hop_thoai
    assert page.evaluate("localStorage.getItem('token')") is None, "token vẫn còn"
    return hop_thoai[0]


@ca("A3", "Quản lý: chỉ xem — không có tab Tiếp nhận, có ô chọn văn phòng, không có nút thao tác")
def a3(page: Page, tk_ql: str):
    vao_bang_token(page, tk_ql, "quan_ly", "Quản lý gốc")
    page.wait_for_selector("#selectVanPhongXem")
    tabs = page.locator("#nv-sidebar [data-tab]").evaluate_all("els => els.map(e => e.dataset.tab)")
    assert "tao-don" not in tabs, tabs
    mo_tab(page, "hang-den")
    page.wait_for_selector("#tbodyHangDen tr")
    nut = page.locator("#tbodyHangDen [data-hanh-dong]").count()
    mo_tab(page, "don-gui")
    page.wait_for_selector("#tbodyDonGui tr")
    nut += page.locator("#tbodyDonGui [data-hanh-dong='huy-don'], #tbodyDonGui [data-hanh-dong='sua-lien-he']").count()
    page.screenshot(path=str(ANH / "A3_quan_ly.png"), full_page=True)
    assert nut == 0, f"còn {nut} nút thao tác"
    vp = page.locator("#selectVanPhongXem option").all_inner_texts()
    return f"Tab: {tabs}; ô văn phòng có {len(vp)} lựa chọn"


@ca("A4", "Tài khoản gửi hàng chưa gán văn phòng → màn chặn, vẫn đăng xuất được")
def a4(page: Page, tk_tam: str):
    vao_bang_token(page, tk_tam, "nhan_vien_gui_hang", "Tam Chua Gan")
    expect(page.locator(".blocking-card")).to_contain_text("chưa được gán văn phòng", timeout=8000)
    assert not page.locator("#nv-sidebar .nv-sidebar__nav").is_visible(), "menu tab vẫn hiện"
    page.screenshot(path=str(ANH / "A4.png"))
    page.click("#nv-tk-nut")
    page.click("#nv-tk-dang-xuat")
    page.click("#btnXacNhanDangXuat")
    page.wait_for_url(re.compile("dang-nhap"), timeout=8000)


@ca("A5", "Tài khoản của tôi: sửa họ tên, đổi mật khẩu (rồi trả lại như cũ)")
def a5(page: Page):
    dang_nhap(page, "guihang.yenbai@demo.nhaxe.vn")
    page.click("#nv-tk-nut")
    page.click("#nv-tk-mo-ho-so")
    expect(page.locator("#modalTaiKhoan")).to_have_class(re.compile("active"))
    page.wait_for_selector("#tkNoiDung [data-truong='ho_ten']")
    ten_cu = page.locator("#tkNoiDung [data-truong='ho_ten'] .tk-gia-tri").inner_text()
    page.click("#tkNoiDung [data-truong='ho_ten'] [data-hanh='sua']")
    page.fill("#tk-o-ho_ten", "Hà Minh Đức Test")
    page.click("#tkNoiDung [data-truong='ho_ten'] [data-hanh='luu']")
    expect(page.locator("#nv-tk-ho-ten")).to_have_text("Hà Minh Đức Test", timeout=8000)
    # đổi mật khẩu: nhập lại sai → báo lỗi; đúng → thành công
    page.click("#tk-mo-doi-mk")
    page.fill("#tk-mk-cu", MK); page.fill("#tk-mk-moi", "GuiHang@456"); page.fill("#tk-mk-lai", "khac")
    page.click("#tk-form-mk button[type=submit]")
    expect(page.locator("#tk-loi-mk")).to_contain_text("chưa khớp")
    page.fill("#tk-mk-lai", "GuiHang@456")
    page.click("#tk-form-mk button[type=submit]")
    expect(page.locator("#tkNoiDung")).to_contain_text("Đổi mật khẩu thành công", timeout=8000)
    tk_moi = token_dang_nhap("guihang.yenbai@demo.nhaxe.vn", "GuiHang@456")
    # trả lại
    api("PUT", "/auth/doi-mat-khau", tk_moi, {"mat_khau_cu": "GuiHang@456", "mat_khau_moi": MK})
    api("PUT", "/auth/toi", tk_moi, {"ho_ten": ten_cu})
    token_dang_nhap("guihang.yenbai@demo.nhaxe.vn")
    return f"đã trả lại họ tên '{ten_cu}' và mật khẩu cũ"


@ca("A6", "Đăng xuất khi đang nhập dở form tạo đơn → hộp xác nhận có cảnh báo")
def a6(page: Page):
    mo_tab(page, "tao-don")
    page.fill("#ten_nguoi_nhan", "Đang nhập dở")
    page.click("#nv-tk-nut")
    page.click("#nv-tk-dang-xuat")
    expect(page.locator("#modalDangXuat")).to_have_class(re.compile("active"))
    expect(page.locator("#dxCanhBao")).to_be_visible()
    canh_bao = page.locator("#dxCanhBao").inner_text()
    page.click("#btnODaiDangXuat")
    page.fill("#ten_nguoi_nhan", "")
    return canh_bao[:120]


# ================================================================== B. Tạo đơn
def dien(page: Page, kv: str, vp: str, cuoc="50000", kg="2", cod=False, ten_nhan="Nguoi Nhan Test", sdt_gui="0901234567"):
    mo_tab(page, "tao-don")
    page.evaluate("datLaiFormTaoDon()")
    page.fill("#ten_nguoi_gui", "Nguoi Gui Test")
    page.fill("#sdt_nguoi_gui", sdt_gui)
    page.fill("#ten_nguoi_nhan", ten_nhan)
    page.fill("#sdt_nguoi_nhan", "0907654321")
    chon(page, "#khu_vuc_den", kv)
    page.wait_for_function("document.querySelector('#diem_nhan_id').options.length > 1")
    chon(page, "#diem_nhan_id", vp)
    page.wait_for_function("!document.querySelector('#tuyen_id').disabled")
    chon(page, "#loai_hang_id", "thông thường")
    page.fill("#can_nang_kg", kg)
    page.fill("#gia_cuoc", cuoc)
    page.check(f"input[name=phuong_thuc_thanh_toan][value={'cod_nguoi_nhan_tra' if cod else 'nguoi_gui_tra_truoc'}]")
    if not cod:
        page.check("#xacNhanDaThuTruoc")


def dem_don_md(tk_md) -> int:
    return api("GET", "/gui-hang/don-hang?huong=gui&limit=1", tk_md)[1]["total"]


@ca("B3", "Mỹ Đình → Lào Cai có 2 tuyến, chưa chọn tuyến thì không tạo được")
def b3(page: Page):
    mo_tab(page, "tao-don")
    page.evaluate("datLaiFormTaoDon()")
    chon(page, "#khu_vuc_den", "Lào Cai")
    page.wait_for_function("document.querySelector('#diem_nhan_id').options.length > 1")
    chon(page, "#diem_nhan_id", "Trung tâm Lào Cai")
    page.wait_for_function("!document.querySelector('#tuyen_id').disabled")
    tuyen = [t for t in page.locator("#tuyen_id option").all_inner_texts() if "chọn" not in t.lower()]
    assert len(tuyen) == 2, tuyen
    assert page.locator("#tuyen_id").input_value() == "", "tự chọn sẵn 1 tuyến"
    page.fill("#ten_nguoi_gui", "A"); page.fill("#sdt_nguoi_gui", "0901234567"); page.fill("#ten_nguoi_nhan", "B")
    page.fill("#sdt_nguoi_nhan", "0907654321"); chon(page, "#loai_hang_id", "thông thường")
    page.fill("#can_nang_kg", "1"); page.fill("#gia_cuoc", "30000"); page.check("#xacNhanDaThuTruoc")
    xoa_toast(page)
    page.click("#btnTaoDon")
    t = toast_cuoi(page, "tuyến")
    assert "active" not in page.locator("#modalXacNhanTaoDon").get_attribute("class")
    return f"Tuyến: {tuyen}; {t[:80]}"


@ca("B7", "Dữ liệu sai bị chặn ngay trên form (SĐT, tên rỗng, cước, cân nặng, kích thước)")
def b7(page: Page):
    sai = []
    for ten, sua in [("SĐT 9 số", ("#sdt_nguoi_nhan", "090765432")), ("SĐT có chữ", ("#sdt_nguoi_gui", "09012abc67")),
                     ("tên người nhận rỗng", ("#ten_nguoi_nhan", "   ")), ("cước 0", ("#gia_cuoc", "0")),
                     ("cước âm", ("#gia_cuoc", "-5000")), ("cân nặng 0", ("#can_nang_kg", "0")), ("dài âm", ("#dai_cm", "-3"))]:
        dien(page, "Yên Bái", "Yên Bái")
        page.fill(*sua)
        xoa_toast(page)
        page.click("#btnTaoDon")
        page.wait_for_timeout(500)
        mo = "active" in (page.locator("#modalXacNhanTaoDon").get_attribute("class") or "")
        if mo:
            sai.append(ten)
            dong_het_modal(page)
    assert not sai, f"không bị chặn: {sai}"
    return "7/7 trường hợp bị chặn, không mở hộp xác nhận"


@ca("B8", "Nhập SĐT khách quen → tự điền họ tên")
def b8(page: Page, sdt_quen: str, ten_quen: str):
    mo_tab(page, "tao-don")
    page.evaluate("datLaiFormTaoDon()")
    page.fill("#sdt_nguoi_gui", sdt_quen)
    expect(page.locator("#ten_nguoi_gui")).to_have_value(ten_quen, timeout=5000)
    page.evaluate("datLaiFormTaoDon()")
    return f"{sdt_quen} → {ten_quen}"


@ca("B9", "Bấm xác nhận tạo đơn 2 lần thật nhanh → chỉ 1 đơn")
def b9(page: Page, tk_md: str):
    truoc = dem_don_md(tk_md)
    dien(page, "Yên Bái", "Yên Bái", cuoc="31000", ten_nhan="Bam Hai Lan")
    page.click("#btnTaoDon")
    expect(page.locator("#modalXacNhanTaoDon")).to_have_class(re.compile("active"))
    page.evaluate("() => { const b = document.querySelector('#btnXacNhanTaoDon'); b.click(); b.click(); }")
    expect(page.locator("#modalBienNhan")).to_have_class(re.compile("active"), timeout=10000)
    page.wait_for_timeout(1500)
    sau = dem_don_md(tk_md)
    assert sau - truoc == 1, f"tạo {sau - truoc} đơn"
    return "đúng 1 đơn mới"


@ca("B10", "Mất mạng lúc bấm tạo đơn, F5 → hỏi lại đúng nội dung, tạo lại chỉ 1 đơn")
def b10(page: Page, tk_md: str):
    truoc = dem_don_md(tk_md)
    dien(page, "Yên Bái", "Yên Bái", cuoc="32000", ten_nhan="Mat Mang F5")
    page.click("#btnTaoDon")
    page.route("**/gui-hang/tao-don", lambda r: r.abort("internetdisconnected"))
    page.click("#btnXacNhanTaoDon")
    toast_cuoi(page, "Không tạo được đơn")
    page.unroute("**/gui-hang/tao-don")
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator("#modalXacNhanTaoDon")).to_have_class(re.compile("active"), timeout=10000)
    nd = page.locator("#xnNoiDung").inner_text()
    assert "CHƯA được tạo" in nd and "Mat Mang F5" in nd and "32.000" in nd, nd[:300]
    page.screenshot(path=str(ANH / "B10_hoi_lai.png"))
    page.click("#btnXacNhanTaoDon")
    expect(page.locator("#modalBienNhan")).to_have_class(re.compile("active"), timeout=10000)
    dong_het_modal(page)
    page.reload(); page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
    assert "active" not in (page.locator("#modalXacNhanTaoDon").get_attribute("class") or ""), "F5 lần 2 vẫn hỏi lại"
    assert dem_don_md(tk_md) - truoc == 1, "số đơn mới khác 1"
    return "hộp xác nhận khôi phục đúng nội dung + nhắc CHƯA được tạo; tạo lại → 1 đơn"


@ca("B11", "Tên chứa thẻ HTML hiện nguyên chữ")
def b11(page: Page):
    dien(page, "Yên Bái", "Yên Bái", cuoc="33000", ten_nhan="<b>Lan</b><img src=x onerror=alert(1)>")
    page.click("#btnTaoDon")
    page.click("#btnXacNhanTaoDon")
    expect(page.locator("#modalBienNhan")).to_have_class(re.compile("active"), timeout=10000)
    txt = page.locator("#bnNguoiNhan").inner_text()
    so_the = page.locator("#bnNguoiNhan b, #bnNguoiNhan img").count()
    dong_het_modal(page)
    assert "<b>Lan</b>" in txt and so_the == 0, f"text={txt!r}, thẻ thật={so_the}"
    return f"hiển thị: {txt[:60]}"


# ================================================================== C. Đơn gửi đi
@ca("C2", "Lọc theo trạng thái / hình thức / từ khóa, nút Đặt lại")
def c2(page: Page):
    mo_tab(page, "don-gui")
    tong = so(page, "#stat-don-gui-count")
    sai = []
    for tt, nhan in [("cho_van_chuyen", "Chờ xếp xe"), ("da_huy", "Đã hủy"), ("da_giao", "Đã giao")]:
        page.select_option("#selectTrangThaiDonGui", tt)
        page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)
        badges = page.locator("#tbodyDonGui td.text-center .badge-status, #tbodyDonGui td:nth-child(6)").all_inner_texts()
        if not badges or any(nhan.lower() not in b.lower() for b in badges[:10]):
            sai.append(f"{tt}: {badges[:3]}")
    page.select_option("#selectTrangThaiDonGui", "")
    page.select_option("#selectThanhToanDonGui", "cod_nguoi_nhan_tra")
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)
    cod = page.locator("#tbodyDonGui tr").all_inner_texts()
    if any("trả trước" in r.lower() for r in cod):
        sai.append("lọc COD còn đơn trả trước")
    page.click("#btnDatLaiDonGui")
    page.wait_for_load_state("networkidle")
    assert not sai, sai
    return f"tổng {tong} đơn; lọc 3 trạng thái + COD đúng"


@ca("C3", "Xuất CSV đơn gửi đi")
def c3(page: Page):
    mo_tab(page, "don-gui")
    with page.expect_download(timeout=15000) as dl:
        page.click("#btnXuatCsvDonGui")
    f = dl.value
    duong = ANH / f.suggested_filename
    f.save_as(duong)
    noi_dung = duong.read_bytes()
    dong = noi_dung.decode("utf-8-sig").splitlines()
    assert noi_dung.startswith(b"\xef\xbb\xbf"), "thiếu BOM UTF-8 (Excel sẽ lỗi font)"
    assert "Mã vận đơn" in dong[0], dong[0]
    return f"{f.suggested_filename}: {len(dong) - 1} dòng, có BOM UTF-8"


@ca("C4", "In lại biên nhận và nhãn từ danh sách")
def c4(page: Page):
    dong = dong_don_gui(page, MA["md_cho_xep_2_ngay"])
    dong.locator("[data-hanh-dong='in-bien-nhan']").click()
    expect(page.locator("#modalBienNhan")).to_have_class(re.compile("active"))
    assert page.locator("#bnMaVanDon").inner_text().strip() == MA["md_cho_xep_2_ngay"]
    dong_het_modal(page)
    dong.locator("[data-hanh-dong='in-nhan']").click()
    expect(page.locator("#modalNhanDan")).to_have_class(re.compile("active"))
    assert page.locator("#ndMaVanDon").inner_text().strip() == MA["md_cho_xep_2_ngay"]
    page.fill("#inputTuKhoaDonGui", "")


@ca("C5", "Tra mã đơn Chờ xếp xe → chi tiết cảnh báo chưa tới, có hành trình")
def c5(page: Page):
    mo_tab(page, "hang-den")
    page.fill("#inputTraCuuGiao", MA["md_cho_xep_2_ngay"])
    page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalChiTietDon")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#ctCanhBao")).to_contain_text("chưa tới văn phòng nhận")
    expect(page.locator("#ctLichSu")).to_contain_text("Tiếp nhận đơn", timeout=5000)


@ca("C6", "VP Yên Bái tra đơn không liên quan → bị từ chối")
def c6(page: Page):
    mo_tab(page, "hang-den")
    xoa_toast(page)
    page.fill("#inputTraCuuGiao", MA["md_cho_xep_tra_truoc"])
    page.press("#inputTraCuuGiao", "Enter")
    t = toast_cuoi(page, "Không tìm thấy đơn")
    assert "active" not in (page.locator("#modalChiTietDon").get_attribute("class") or "")
    page.fill("#inputTraCuuGiao", "")
    return t[:120]


# ================================================================== D. Hủy đơn
def mo_huy(page: Page, ma: str):
    dong = dong_don_gui(page, ma)
    dong.locator("[data-hanh-dong='huy-don']").click()
    expect(page.locator("#modalHuyDon")).to_have_class(re.compile("active"))


@ca("D2", "Hủy đơn COD → hoàn 0đ, không in phiếu hoàn")
def d2(page: Page):
    mo_huy(page, MA["md_cho_xep_cod"])
    hoan = page.locator("#hdHoanTien").inner_text()
    assert "Không hoàn" in hoan, hoan
    page.check("input[name=ly_do_huy][value=khach_doi_y]"); page.check("#hdDaTraHang")
    xoa_toast(page)
    page.click("#btnXacNhanHuyDon")
    t = toast_cuoi(page, "Đã hủy đơn")
    page.wait_for_timeout(500)
    assert "active" not in (page.locator("#modalPhieuHuy").get_attribute("class") or ""), "vẫn mở phiếu hoàn"
    return t[:100]


@ca("D3", "Lý do 'Khác' bỏ trống ghi chú → bắt buộc ghi chú; chưa tích đã trả hàng → chặn")
def d3(page: Page, ma: str):
    mo_huy(page, ma)
    page.check("input[name=ly_do_huy][value=khac]"); page.check("#hdDaTraHang")
    xoa_toast(page)
    page.click("#btnXacNhanHuyDon")
    t1 = toast_cuoi(page, "Thiếu ghi chú")
    page.fill("#hdGhiChu", "thử"); page.uncheck("#hdDaTraHang")
    xoa_toast(page)
    page.click("#btnXacNhanHuyDon")
    t2 = toast_cuoi(page, "Chưa xác nhận")
    assert "active" in page.locator("#modalHuyDon").get_attribute("class")
    return f"{t1[:50]} | {t2[:50]}"


@ca("D4", "Hủy vì nhập sai → phiếu có nút Tạo lại đơn, form điền sẵn người gửi/nhận/hàng")
def d4(page: Page, ma: str):
    mo_huy(page, ma)
    page.check("input[name=ly_do_huy][value=nhap_sai_thong_tin]"); page.check("#hdDaTraHang")
    page.click("#btnXacNhanHuyDon")
    expect(page.locator("#modalPhieuHuy")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#btnTaoLaiDon")).to_be_visible()
    page.click("#btnTaoLaiDon")
    expect(page.locator("#tab-tao-don")).to_have_class(re.compile("active"))
    ten = page.locator("#ten_nguoi_nhan").input_value()
    kg = page.locator("#can_nang_kg").input_value()
    loai = page.locator("#loai_hang_id").input_value()
    vp = page.locator("#diem_nhan_id").input_value()
    page.evaluate("datLaiFormTaoDon()")
    assert ten and kg and loai and not vp, f"tên={ten}, kg={kg}, loại={loai}, văn phòng={vp}"
    return f"điền sẵn người nhận '{ten}', {kg} kg; văn phòng nhận để trống chọn lại"


@ca("D5", "Đơn đang trên xe không có nút hủy; gọi API hủy → bị chặn")
def d5(page: Page, tk_md: str, ma_tren_xe: str, id_tren_xe: str):
    dong = dong_don_gui(page, ma_tren_xe)
    assert dong.locator("[data-hanh-dong='huy-don']").count() == 0, "còn nút hủy"
    code, body = api("POST", f"/gui-hang/don-hang/{id_tren_xe}/huy", tk_md, {"ly_do": "khach_doi_y"}, loi_ok=True)
    page.fill("#inputTuKhoaDonGui", "")
    assert code == 400, (code, body)
    return f"API → {code}: {body.get('loi', body)}"


@ca("D6", "VP Lào Cai không hủy được đơn của Mỹ Đình (API → 403)")
def d6(tk_lc: str, id_md: str):
    code, body = api("POST", f"/gui-hang/don-hang/{id_md}/huy", tk_lc, {"ly_do": "khach_doi_y"}, loi_ok=True)
    assert code == 403, (code, body)
    return f"{code}: {body.get('loi', body)}"


@ca("D7", "Chi tiết đơn đã hủy: lý do, người hủy, tiền hoàn; không có nút giao/sửa/hủy")
def d7(page: Page):
    nd = chi_tiet(page, MA["md_da_huy_hom_nay"])
    nut = page.locator("#ctHanhDong button").all_inner_texts()
    assert "Hủy lúc" in nd and "Lý do hủy" in nd and "95.000" in nd, nd[:400]
    assert not any(k in " ".join(nut) for k in ("Giao", "Sửa", "Hủy đơn", "Liên hệ")), nut
    return f"nút: {nut}"


# ================================================================== E. Sửa tên / SĐT
@ca("E1", "Sửa chính tả tên người nhận → không bắt lý do, có nhật ký")
def e1(page: Page):
    dong = dong_don_gui(page, MA["md_cho_xep_2_ngay"])
    dong.locator("[data-hanh-dong='sua-lien-he']").click()
    expect(page.locator("#modalSuaLienHe")).to_have_class(re.compile("active"))
    ten = page.locator("#slTenNhan").input_value()
    page.fill("#slTenNhan", ten + " Sửa")
    xoa_toast(page)
    page.click("#btnLuuSuaLienHe")
    toast_cuoi(page, "Đã cập nhật")
    nd = chi_tiet(page, MA["md_cho_xep_2_ngay"])
    assert "Lịch sử chỉnh sửa" in nd and "Sửa" in nd, nd[-300:]
    page.fill("#inputTuKhoaDonGui", "")


@ca("E2", "Mỹ Đình đổi SĐT người nhận đơn đang ở Lào Cai → bắt lý do; Lào Cai nhận tin real-time, đơn về 'Chưa báo'")
def e2(md: Page, lc: Page):
    mo_tab(lc, "hang-den")
    xoa_toast(lc)
    dong = dong_don_gui(md, MA["lc_sua_sdt"])
    dong.locator("[data-hanh-dong='sua-lien-he']").click()
    md.fill("#slSdtNhan", "0911222333")
    xoa_toast(md)
    md.click("#btnLuuSuaLienHe")
    toast_cuoi(md, "Thiếu lý do")
    md.fill("#slLyDo", "Người gửi gọi báo số mới (test tự động)")
    md.click("#btnLuuSuaLienHe")
    toast_cuoi(md, "Đã cập nhật")
    tin = toast_cuoi(lc, MA["lc_sua_sdt"], timeout=10000)
    assert "số mới" in tin, tin
    lc.wait_for_timeout(800)
    hang = dong_hang_den(lc, MA["lc_sua_sdt"]).inner_text()
    lc.fill("#inputTraCuuGiao", "")
    md.fill("#inputTuKhoaDonGui", "")
    assert "Chưa báo" in hang, hang[:200]
    return tin[:160]


@ca("E3", "Nhật ký sửa SĐT: số cũ → số mới, người sửa, lý do")
def e3(page: Page):
    nd = chi_tiet(page, MA["lc_sua_sdt"])
    assert "0911222333" in nd and "lý do" in nd.lower(), nd[-400:]


@ca("E4", "Đơn đã giao / đã hủy không có nút sửa")
def e4(page: Page):
    for ma in (MA["md_da_huy_hom_nay"],):
        dong = dong_don_gui(page, ma)
        assert dong.locator("[data-hanh-dong='sua-lien-he']").count() == 0, f"{ma} còn nút sửa"
    page.fill("#inputTuKhoaDonGui", "")
    page.select_option("#selectTrangThaiDonGui", "da_giao")
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(300)
    so_nut = page.locator("#tbodyDonGui [data-hanh-dong='sua-lien-he']").count()
    page.select_option("#selectTrangThaiDonGui", "")
    assert so_nut == 0, f"{so_nut} đơn đã giao còn nút sửa"


# ================================================================== F. Hàng đến / giao
@ca("F2", "Đơn trên chuyến gặp sự cố / đang hoãn: nhãn cảnh báo + 'Hàng sẽ tới trễ', không có nút Giao")
def f2(md: Page, lc: Page):
    mo_tab(md, "hang-den")
    a = dong_hang_den(md, MA["md_su_co"])
    ta = a.inner_text()
    mo_tab(lc, "hang-den")
    b = dong_hang_den(lc, MA["lc_dang_hoan"])
    tb = b.inner_text()
    ok = ("sự cố" in ta and "tới trễ" in ta and a.locator("[data-hanh-dong='giao']").count() == 0
          and "hoãn" in tb and "tới trễ" in tb and b.locator("[data-hanh-dong='giao']").count() == 0)
    md.fill("#inputTraCuuGiao", ""); lc.fill("#inputTraCuuGiao", "")
    assert ok, f"sự cố: {ta[:150]} || hoãn: {tb[:150]}"


@ca("F4", "Gọi người nhận không được → ghi lịch sử, vẫn ở Cần gọi báo")
def f4(page: Page):
    dong = dong_hang_den(page, MA["lc_goi_truot"])
    dong.locator("[data-hanh-dong='lien-he']").click()
    page.locator("#lhLuaChon label", has_text="Gọi người nhận không được").click()
    page.click("#btnLuuLienHe")
    page.wait_for_function("document.querySelectorAll('#lhLichSu li').length >= 2", timeout=8000)
    dong_het_modal(page)
    page.wait_for_load_state("networkidle")
    t = dong_hang_den(page, MA["lc_goi_truot"]).inner_text()
    page.fill("#inputTraCuuGiao", "")
    assert "Chưa báo" in t, t[:150]


@ca("F6", "Giao đơn COD: chưa tích đã thu → chặn; tích → giao được")
def f6(page: Page):
    page.fill("#inputTraCuuGiao", MA["lc_cod_55"]); page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalGiaoHangCOD")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#ghThanhToan")).to_contain_text("55.000")
    page.check("#chkKiemTraKienHang")
    xoa_toast(page)
    page.click("#btnXacNhanGiaoHang")
    toast_cuoi(page, "Chưa xác nhận thu cước")
    page.check("#chkXacNhanThuCOD")
    page.click("#btnXacNhanGiaoHang")
    expect(page.locator("#modalPhieuXuatKho")).to_have_class(re.compile("active"), timeout=8000)
    return page.locator("#pxTienThu").inner_text().strip()


@ca("F7", "Giao đơn có báo cáo hư hỏng → modal hiện khung cảnh báo")
def f7(page: Page):
    page.fill("#inputTraCuuGiao", MA["lc_hu_hong"]); page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalGiaoHangCOD")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#ghSuCo")).to_be_visible(timeout=5000)
    t = page.locator("#ghSuCo").inner_text()
    page.screenshot(path=str(ANH / "F7.png"))
    return t.replace("\n", " ")[:150]


@ca("F8", "Nhập SĐT người nhận → danh sách đơn chờ giao của SĐT đó")
def f8(page: Page, sdt: str, ma: str):
    page.fill("#inputTraCuuGiao", sdt); page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalKetQuaSdt")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#ksDanhSach")).to_contain_text(ma)
    assert page.locator("#ksDanhSach [data-hanh-dong='giao-tu-sdt']").count() >= 1


@ca("F9", "Mã đơn còn trên xe / đã giao / sai → báo đúng lý do, không giao")
def f9(page: Page):
    kq = []
    for ma, mong in [(MA["lc_de_vo_tren_xe"], "chưa tới"), (MA["lc_da_giao"], "đã giao")]:
        dong_het_modal(page)
        page.fill("#inputTraCuuGiao", ma); page.press("#inputTraCuuGiao", "Enter")
        expect(page.locator("#modalChiTietDon")).to_have_class(re.compile("active"), timeout=8000)
        cb = page.locator("#ctCanhBao").inner_text()
        assert mong in cb.lower(), f"{ma}: {cb}"
        assert "active" not in (page.locator("#modalGiaoHangCOD").get_attribute("class") or "")
        kq.append(cb[:60])
    dong_het_modal(page)
    xoa_toast(page)
    page.fill("#inputTraCuuGiao", "DH-00000000-ZZZZZZ"); page.press("#inputTraCuuGiao", "Enter")
    kq.append(toast_cuoi(page, "Không tìm thấy")[:60])
    page.fill("#inputTraCuuGiao", "")
    return " | ".join(kq)


@ca("F10", "Gõ mã viết thường vẫn tìm ra")
def f10(page: Page):
    page.fill("#inputTraCuuGiao", MA["lc_24h_da_nhac"].lower()); page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalGiaoHangCOD")).to_have_class(re.compile("active"), timeout=8000)
    assert page.locator("#ghMaVanDon").inner_text().strip() == MA["lc_24h_da_nhac"]
    page.fill("#inputTraCuuGiao", "")


@ca("F11", "VP Mỹ Đình tra đơn giao ở Lào Cai → 'giao tại văn phòng khác', không giao")
def f11(page: Page):
    mo_tab(page, "hang-den")
    page.fill("#inputTraCuuGiao", MA["lc_7_da_bao"]); page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalChiTietDon")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#ctCanhBao")).to_contain_text("văn phòng khác")
    assert "Giao" not in " ".join(page.locator("#ctHanhDong button").all_inner_texts())
    page.fill("#inputTraCuuGiao", "")


# ================================================================== G. Hàng chờ lâu
@ca("G1", "Tab Hàng chờ lâu: đơn quá 7 ngày + hàng tồn, cột từng/chưa từng báo, đếm ngược")
def g1(page: Page):
    mo_tab(page, "hang-ton")
    page.wait_for_selector("#tbodyHangTon tr")
    t = page.locator("#tbodyHangTon").inner_text()
    n = page.locator("#tbodyHangTon tr").count()
    page.screenshot(path=str(ANH / "G1.png"), full_page=True)
    assert "Từng báo được" in t and "Chưa từng báo được" in t and "Hàng tồn" in t, t[:300]
    return f"{n} đơn"


@ca("G2", "Quá 7 ngày, đã từng báo → việc cần làm: gọi lại người nhận")
def g2(page: Page):
    mo_tab(page, "hang-den")
    t = dong_hang_den(page, MA["lc_7_da_bao"]).inner_text()
    page.fill("#inputTraCuuGiao", "")
    assert "Gọi lại người nhận" in t, t[:200]


@ca("G3", "Quá 7 ngày, chưa từng báo → gọi người gửi; modal có lựa chọn báo quản lý")
def g3(page: Page):
    dong = dong_hang_den(page, MA["lc_7_chua_bao"])
    assert "Gọi người gửi" in dong.inner_text()
    dong.locator("[data-hanh-dong='lien-he']").click()
    expect(page.locator("#lhLuaChon")).to_contain_text("báo quản lý")
    dong_het_modal(page); page.fill("#inputTraCuuGiao", "")


@ca("G4", "Hàng tồn không liên hệ được ai → báo quản lý; quản lý nhận thông báo")
def g4(page: Page, tk_ql: str):
    dong = dong_hang_den(page, MA["lc_ton_16"])
    dong.locator("[data-hanh-dong='lien-he']").click()
    page.locator("#lhLuaChon label", has_text="báo quản lý").click()
    page.fill("#lhGhiChu", "Test tự động: gọi người gửi 3 lần không được")
    page.click("#btnLuuLienHe")
    toast_cuoi(page, "Đã gửi thông báo tới quản lý")
    dong_het_modal(page); page.fill("#inputTraCuuGiao", "")
    tb = api("GET", "/thong-bao/cua-toi?limit=10", tk_ql)[1]["items"]
    assert any(MA["lc_ton_16"] in t["noi_dung"] for t in tb), "quản lý không có thông báo"


@ca("G5", "Đơn chờ lấy dưới 7 ngày: không có lựa chọn báo quản lý")
def g5(page: Page):
    dong = dong_hang_den(page, MA["lc_24h_da_nhac"])
    dong.locator("[data-hanh-dong='lien-he']").click()
    t = page.locator("#lhLuaChon").inner_text()
    dong_het_modal(page); page.fill("#inputTraCuuGiao", "")
    assert "quản lý" not in t, t


@ca("G6", "'Đã liên hệ được người gửi' bỏ trống ghi chú → bắt ghi hướng xử lý")
def g6(page: Page):
    dong = dong_hang_den(page, MA["lc_7_chua_bao"])
    dong.locator("[data-hanh-dong='lien-he']").click()
    page.locator("#lhLuaChon label", has_text="Đã liên hệ được người gửi").click()
    page.fill("#lhGhiChu", "")
    xoa_toast(page)
    page.click("#btnLuuLienHe")
    t = toast_cuoi(page, "Thiếu hướng xử lý")
    dong_het_modal(page); page.fill("#inputTraCuuGiao", "")
    return t[:80]


@ca("G7", "Giao hàng tồn đã thỏa thuận (COD 60.000đ)")
def g7(page: Page):
    page.fill("#inputTraCuuGiao", MA["lc_ton_thoa_thuan"]); page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalGiaoHangCOD")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#ghHangTon")).to_be_visible()
    page.check("#chkKiemTraKienHang"); page.check("#chkXacNhanThuCOD")
    page.click("#btnXacNhanGiaoHang")
    expect(page.locator("#modalPhieuXuatKho")).to_have_class(re.compile("active"), timeout=8000)
    page.fill("#inputTraCuuGiao", "")


@ca("G8", "Chạy job: tin nhắc 24h / cảnh báo 7 ngày lên chuông; chạy lần 2 không nhắc trùng")
def g8(page: Page):
    # Chạy job bằng lệnh riêng = tiến trình khác backend → chỉ ghi thông báo vào DB, không đẩy real-time.
    # Kiểm tra trên chuông sau khi tải lại trang.
    lenh = "from app.jobs.quet_hang_ton import chay_job_quet_hang_ton as j; print(j())"
    kq1 = eval(py_backend(lenh).strip().splitlines()[-1])  # noqa: S307 — dict in ra từ job
    page.reload(); page.wait_for_load_state("networkidle")
    page.click("#nvBellBtn")
    page.wait_for_timeout(800)
    chuong = page.locator("#nvBellList").inner_text()
    page.click("#nvBellBtn")
    if kq1["so_don_nhac_goi_bao_24h"]:
        assert "hơn 1 ngày" in chuong, "chuông không có tin nhắc 24 giờ"
    if kq1["so_don_canh_bao_7_ngay"]:
        assert "7 ngày" in chuong, "chuông không có tin cảnh báo 7 ngày"
    kq2 = eval(py_backend(lenh).strip().splitlines()[-1])  # noqa: S307
    assert not any(kq2.values()), f"lần 2 vẫn xử lý: {kq2}"
    return f"lần 1 {kq1} → có trên chuông; lần 2 {kq2}"


@ca("G9", "Xuất CSV hàng tồn")
def g9(page: Page):
    mo_tab(page, "hang-ton")
    with page.expect_download(timeout=15000) as dl:
        page.click("#btnXuatCsvHangTon")
    duong = ANH / dl.value.suggested_filename
    dl.value.save_as(duong)
    dau = duong.read_text(encoding="utf-8-sig").splitlines()
    assert all(c in dau[0] for c in ("SĐT người nhận", "SĐT người gửi", "Số ngày chờ", "Đã từng báo")), dau[0]
    return f"{len(dau) - 1} dòng"


# ================================================================== H. Phụ xe
@ca("H2", "Phụ xe hoàn tác dỡ khi Lào Cai chưa gọi báo → Lào Cai nhận 'đừng gọi báo'")
def h2(lc: Page, tk_px: str, don: dict):
    mo_tab(lc, "hang-den")
    xoa_toast(lc)
    api("POST", f"/phu-xe/chuyen/{don['chuyen_id']}/toi-diem", tk_px, {"diem_don_tra_id": str(don["diem_nhan_id"])})
    api("POST", f"/phu-xe/don-hang/{don['id']}/do-hang", tk_px)
    toast_cuoi(lc, "vừa tới văn phòng")
    api("POST", f"/phu-xe/don-hang/{don['id']}/hoan-tac-do-hang", tk_px, {"chuyen_id": str(don["chuyen_id"])})
    tin = toast_cuoi(lc, "hoàn tác", timeout=10000)
    assert "đừng gọi báo" in tin, tin
    return tin[:150]


@ca("H3", "Lào Cai đã gọi báo → phụ xe không hoàn tác dỡ được")
def h3(lc: Page, tk_px: str, tk_lc: str, don: dict):
    api("POST", f"/phu-xe/don-hang/{don['id']}/do-hang", tk_px)
    api("POST", f"/gui-hang/don-hang/{don['id']}/lien-he", tk_lc, {"doi_tuong": "nguoi_nhan", "ket_qua": "da_lien_he"})
    code, body = api("POST", f"/phu-xe/don-hang/{don['id']}/hoan-tac-do-hang", tk_px, {"chuyen_id": str(don["chuyen_id"])}, loi_ok=True)
    assert code == 400 and "đã gọi báo" in body.get("loi", ""), (code, body)
    return body["loi"]


@ca("H4", "Phụ xe báo hư hỏng đơn trên xe → Lào Cai nhận real-time, quản lý có thông báo")
def h4(lc: Page, tk_px: str, tk_ql: str, id_don: str, ma: str):
    mo_tab(lc, "hang-den")
    xoa_toast(lc)
    api("POST", f"/phu-xe/don-hang/{id_don}/bao-that-lac", tk_px, {"mo_ta": "Test tự động: góc thùng bị ướt", "loai": "hu_hong"})
    tin = toast_cuoi(lc, ma, timeout=10000)
    tb = api("GET", "/thong-bao/cua-toi?limit=10", tk_ql)[1]["items"]
    assert any(ma in t["noi_dung"] for t in tb), "quản lý không nhận"
    return tin[:150]


# ================================================================== I. Thông báo
@ca("I1", "Chuông: số chưa đọc; bấm thông báo có mã đơn → đã đọc + mở chi tiết")
def i1(page: Page):
    page.reload(); page.wait_for_load_state("networkidle")
    badge = page.locator("#nvBellBadge")
    truoc = int(badge.inner_text()) if badge.is_visible() else 0
    page.click("#nvBellBtn")
    item = page.locator("#nvBellList .nv-bell__item.chua-doc[data-ma]:not([data-ma=''])").first
    item.wait_for(timeout=5000)
    ma = item.get_attribute("data-ma")
    item.click()
    expect(page.locator("#modalChiTietDon")).to_have_class(re.compile("active"), timeout=8000)
    expect(page.locator("#ctMaVanDon")).to_have_text(ma)
    page.wait_for_timeout(800)
    sau = int(badge.inner_text()) if badge.is_visible() else 0
    assert sau == truoc - 1, f"chưa đọc {truoc} → {sau}"
    return f"chưa đọc {truoc} → {sau}, mở {ma}"


@ca("I2", "Khởi động lại backend → trang tự nối lại, tin sau đó có trên chuông")
def i2(lc: Page, tk_px_lay_lai, id_don: str, ma: str):
    mo_tab(lc, "hang-den")
    docker("restart", "backend")
    for _ in range(60):
        try:
            urllib.request.urlopen(BE + "/docs", timeout=2); break
        except Exception:  # noqa: BLE001
            time.sleep(1)
    api("POST", f"/phu-xe/don-hang/{id_don}/bao-that-lac", tk_px_lay_lai(), {"mo_ta": "Test tự động sau khi khởi động lại backend", "loai": "hu_hong"})
    t0 = time.time()
    # Tin phát ra lúc trang chưa nối lại WebSocket: trang tải lại chuông khi nối lại (hoặc poll 60 giây) — không hiện toast.
    lc.wait_for_function("m => document.querySelector('#nvBellList').innerText.includes(m) && document.querySelector('#nvBellList').innerText.includes('khởi động lại')",
                         arg=ma, timeout=75000)
    return f"tin có trên chuông sau {time.time() - t0:.0f}s"


# ================================================================== J. Thống kê
@ca("J3", "Đối soát hôm nay: tổng = thu − hoàn, có dòng tiền hoàn")
def j3(page: Page):
    mo_tab(page, "thong-ke")
    page.click("#tkPreset [data-so-ngay='1']")
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(500)
    hang = page.locator("#tbodyDoiSoat tr").all_inner_texts()
    tong = so(page, "#tkDoiSoatTong"); hoan = abs(so(page, "#tkDoiSoatHoan"))
    tung = []
    for r in hang:
        tien = [int(re.sub(r"\D", "", x)) for x in re.findall(r"[\d.]+ đ(?!ơn)", r)]
        if len(tien) >= 4:
            assert tien[0] + tien[1] - tien[2] == tien[3], f"dòng sai: {r}"
            tung.append(tien[3])
    assert sum(tung) == tong and hoan > 0, f"tổng dòng {sum(tung)} ≠ {tong}, hoàn {hoan}"
    return f"{len(hang)} nhân viên, tổng {tong:,}, hoàn {hoan:,}"


@ca("J4", "Từ ngày > đến ngày → báo lỗi")
def j4(page: Page):
    page.fill("#tkTuNgay", "2026-11-10"); page.fill("#tkDenNgay", "2026-11-01")
    xoa_toast(page)
    page.dispatch_event("#tkDenNgay", "change")
    t = toast_cuoi(page, "Khoảng ngày không hợp lệ")
    page.click("#tkPreset [data-so-ngay='1']")
    return t[:80]


@ca("J5", "Xuất CSV đối soát")
def j5(page: Page):
    with page.expect_download(timeout=15000) as dl:
        page.click("#btnXuatCsvDoiSoat")
    duong = ANH / dl.value.suggested_filename
    dl.value.save_as(duong)
    dong = duong.read_text(encoding="utf-8-sig").splitlines()
    assert dong[-1].startswith("TỔNG") or dong[-1].startswith('"TỔNG'), dong[-1]
    return f"{dl.value.suggested_filename}, {len(dong) - 2} nhân viên"


@ca("J6", "Quản lý: thống kê toàn hệ thống ≥ thống kê 1 văn phòng")
def j6(page: Page, tk_ql: str):
    vao_bang_token(page, tk_ql, "quan_ly", "Quản lý gốc")
    mo_tab(page, "thong-ke")
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(500)
    toan = so(page, "#tkTongGuiDi")
    chon(page, "#selectVanPhongXem", "Mỹ Đình")
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
    md = so(page, "#tkTongGuiDi")
    chon(page, "#selectVanPhongXem", "Toàn hệ thống")
    assert toan >= md and md > 0, (toan, md)
    return f"toàn hệ thống {toan} đơn gửi, Mỹ Đình {md}"


# ================================================================== K. Giao diện
@ca("K", "4 cỡ màn hình: không cuộn ngang; sidebar thu gọn nhớ sau F5; ≤880 thanh ngang; menu/chuông không tràn")
def k(page: Page):
    ghi = []
    for w, h in [(1920, 1080), (1100, 800), (880, 900), (400, 860)]:
        page.set_viewport_size({"width": w, "height": h})
        for tab in ("hang-den", "don-gui", "thong-ke", "tao-don"):
            mo_tab(page, tab)
            tran = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            assert tran <= 1, f"{w}px tab {tab} cuộn ngang {tran}px"
        page.screenshot(path=str(ANH / f"K_{w}.png"), full_page=False)
        sb = page.locator("#nv-sidebar").bounding_box()
        if w <= 880:
            assert sb["width"] >= w - 2 and sb["height"] < 200, f"{w}px sidebar {sb}"
            page.click("#nvBellBtn")
            p = page.locator("#nvBellPanel").bounding_box()
            assert p["x"] >= -1 and p["x"] + p["width"] <= w + 1, f"{w}px chuông tràn {p}"
            page.click("#nvBellBtn")
            page.click("#nv-tk-nut")
            m = page.locator("#nv-tk-menu").bounding_box()
            assert m["x"] >= -1 and m["x"] + m["width"] <= w + 1, f"{w}px menu tài khoản tràn {m}"
            page.keyboard.press("Escape")
        ghi.append(f"{w}px ok")
    page.set_viewport_size({"width": 1100, "height": 800})
    page.click("#nv-sidebar-thu-gon")
    page.reload(); page.wait_for_load_state("networkidle")
    thu_gon = "is-thu-gon" in (page.locator("#nv-sidebar").get_attribute("class") or "")
    page.click("#nv-sidebar-mo-rong")
    assert thu_gon, "thu gọn không được nhớ sau F5"
    page.set_viewport_size({"width": 1440, "height": 900})
    return ", ".join(ghi) + "; thu gọn nhớ sau F5"


@ca("K5", "Bản in chỉ có phiếu, không có sidebar")
def k5(page: Page):
    dong = dong_don_gui(page, MA["md_cho_xep_2_ngay"])
    dong.locator("[data-hanh-dong='in-bien-nhan']").click()
    expect(page.locator("#modalBienNhan")).to_have_class(re.compile("active"))
    # Giống inPhanTu() nhưng không mở hộp in thật
    page.evaluate("document.querySelector('#modalBienNhan .print-area').classList.add('print-target'); document.body.classList.add('dang-in')")
    page.emulate_media(media="print")
    sb = page.locator("#nv-sidebar").is_visible()
    phieu = page.locator("#modalBienNhan .print-area").is_visible()
    page.emulate_media(media="screen")
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    page.fill("#inputTuKhoaDonGui", "")
    assert not sb and phieu, f"sidebar hiện={sb}, phiếu hiện={phieu}"


# ================================================================== P. API
@ca("P", "API: không token 401, quản lý tạo đơn 403, khai văn phòng khác 403, Lào Cai→Sa Pa 400, tra cứu công khai không lộ tên/SĐT")
def p_api(tk_ql, tk_lc, ids):
    ghi = []
    code, _ = api("GET", "/gui-hang/hang-den", None, loi_ok=True); assert code == 401, code; ghi.append("401")
    code, _ = api("GET", "/gui-hang/hang-den", "abc.def.ghi", loi_ok=True); assert code == 401, code
    body = {"tuyen_id": ids["tuyen"], "diem_gui_id": ids["lc"], "diem_nhan_id": ids["md"], "loai_hang_id": ids["loai"],
            "can_nang_kg": 1, "gia_cuoc": 30000, "ten_nguoi_gui": "A", "sdt_nguoi_gui": "0901234567", "ten_nguoi_nhan": "B",
            "sdt_nguoi_nhan": "0907654321", "phuong_thuc_thanh_toan": "nguoi_gui_tra_truoc", "xac_nhan_da_thu": True}
    code, _ = api("POST", "/gui-hang/tao-don", tk_ql, body, loi_ok=True); assert code == 403, code; ghi.append("403")
    code, b = api("POST", "/gui-hang/tao-don", tk_lc, {**body, "diem_gui_id": ids["md"], "diem_nhan_id": ids["yb"]}, loi_ok=True)
    assert code in (400, 403), (code, b); ghi.append(f"{code} {b.get('loi', '')[:40]}")
    code, b = api("POST", "/gui-hang/tao-don", tk_lc, {**body, "diem_nhan_id": ids["sp"], "tuyen_id": ids["tuyen_sp"]}, loi_ok=True)
    assert code == 400 and "khu vực khác" in b.get("loi", ""), (code, b); ghi.append(f"400 {b['loi'][:40]}")
    code, b = api("GET", f"/gui-hang/tra-cuu/{MA['lc_7_da_bao']}", loi_ok=True)
    lo = [k for k in ("ten_nguoi_gui", "sdt_nguoi_gui", "ten_nguoi_nhan", "sdt_nguoi_nhan") if k in b]
    assert code == 200 and not lo, (code, lo); ghi.append("công khai không lộ tên/SĐT")
    return "; ".join(ghi)


# ================================================================== Bộ [Khói]
@ca("A1", "Đăng nhập NV Mỹ Đình, sidebar 5 mục, topbar đúng văn phòng")
def k_a1(page: Page):
    dang_nhap(page, "guihang.mydinh@demo.nhaxe.vn")
    muc = page.locator("#nv-sidebar [data-tab]").all_inner_texts()
    assert len(muc) == 5, f"sidebar có {len(muc)} mục: {muc}"
    expect(page.locator("#nv-topbar")).to_contain_text("Mỹ Đình")
    page.screenshot(path=str(ANH / "A1.png"))


@ca("B1", "Tạo đơn trả trước tới VP Yên Bái, in biên nhận + nhãn")
def k_b1(page: Page) -> str:
    dien(page, "Yên Bái", "Yên Bái", cuoc="50000", kg="3", ten_nhan="Nhan Tra Truoc")
    page.click("#btnTaoDon")
    expect(page.locator("#modalXacNhanTaoDon")).to_have_class(re.compile("active"))
    xn = page.locator("#xnNoiDung").inner_text()
    assert "50.000" in xn and "Yên Bái" in xn, f"hộp xác nhận thiếu thông tin: {xn[:200]}"
    page.click("#btnXacNhanTaoDon")
    expect(page.locator("#modalBienNhan")).to_have_class(re.compile("active"), timeout=10000)
    ma = page.locator("#bnMaVanDon").inner_text().strip()
    assert ma.startswith("DH-") and "Yên Bái" in page.locator("#bnDiemNhan").inner_text()
    page.screenshot(path=str(ANH / "B1_bien_nhan.png"))
    page.click("#btnChuyenSangNhan")
    expect(page.locator("#modalNhanDan")).to_have_class(re.compile("active"))
    assert page.locator("#ndMaVanDon").inner_text().strip() == ma
    return f"Mã {ma}"


@ca("B2", "Tạo đơn COD tới VP Sa Pa (không có ô đã thu)")
def k_b2(page: Page) -> str:
    dien(page, "Lào Cai", "Sa Pa", cuoc="70000", kg="2", cod=True, ten_nhan="Nhan COD")
    assert not page.locator("#xacNhanThuTruocWrap").is_visible(), "ô 'đã thu' vẫn hiện với COD"
    page.click("#btnTaoDon")
    page.click("#btnXacNhanTaoDon")
    expect(page.locator("#modalBienNhan")).to_have_class(re.compile("active"), timeout=10000)
    tt = page.locator("#bnThanhToan").inner_text()
    ma = page.locator("#bnMaVanDon").inner_text().strip()
    assert "nhận" in tt.lower(), f"biên nhận không ghi người nhận trả: {tt}"
    return f"Mã {ma}, thanh toán: {tt.strip()}"


@ca("B4", "Không có khu vực của văn phòng mình; điểm dừng Km 140 không bao giờ là điểm nhận")
def k_b4(page: Page) -> str:
    mo_tab(page, "tao-don")
    kv = [k_ for k_ in page.locator("#khu_vuc_den option").all_inner_texts() if "Chọn" not in k_]
    assert not any("Hà Nội" in k_ for k_ in kv), f"có khu vực Hà Nội: {kv}"
    tat_ca_vp = []
    for k_ in kv:
        page.select_option("#khu_vuc_den", label=k_)
        page.wait_for_function("document.querySelector('#diem_nhan_id').options.length > 1")
        tat_ca_vp += page.locator("#diem_nhan_id option").all_inner_texts()
    assert not any("Km 140" in v or "Điểm dừng" in v for v in tat_ca_vp), tat_ca_vp
    return f"Khu vực: {kv}"


@ca("B5", "Hàng cấm hiện trong danh sách nhưng bị khóa, không chọn được")
def k_b5(page: Page) -> str:
    mo_tab(page, "tao-don")
    cam = page.locator("#loai_hang_id option", has_text="cấm")
    assert cam.count() >= 1, "danh sách loại hàng không hiện hàng cấm để đối chiếu"
    assert all(cam.nth(i).is_disabled() for i in range(cam.count())), "có hàng cấm chọn được"
    return cam.first.inner_text()


@ca("B6", "Trả trước nhưng không tích 'đã thu' thì không cho xác nhận")
def k_b6(page: Page) -> str:
    dien(page, "Yên Bái", "Yên Bái", cuoc="40000", kg="1", ten_nhan="Nhan Chua Thu")
    page.uncheck("#xacNhanDaThuTruoc")
    xoa_toast(page)
    page.click("#btnTaoDon")
    t = toast_cuoi(page, "đã thu")
    assert "active" not in (page.locator("#modalXacNhanTaoDon").get_attribute("class") or ""), "vẫn mở hộp xác nhận"
    return t[:100]


@ca("C1", "Đơn gửi đi: 2 đơn vừa tạo ở đầu danh sách")
def k_c1(page: Page, ma_moi: list[str]):
    assert len(ma_moi) == 2, f"B1/B2 chưa tạo đủ 2 đơn ({ma_moi}) nên không kiểm được"
    mo_tab(page, "don-gui")
    page.wait_for_selector("#tbodyDonGui tr")
    dau = page.locator("#tbodyDonGui tr").first.inner_text() + page.locator("#tbodyDonGui tr").nth(1).inner_text()
    for ma in ma_moi:
        assert ma in dau, f"{ma} không nằm ở 2 dòng đầu"


@ca("D1", "Hủy đơn trả trước, hoàn 100.000đ, in phiếu hoàn")
def k_d1(page: Page) -> str:
    mo_huy(page, MA["md_cho_xep_tra_truoc"])
    hoan = page.locator("#hdHoanTien").inner_text()
    assert "100.000" in hoan, f"số tiền hoàn hiển thị: {hoan}"
    page.check("input[name=ly_do_huy][value=khach_doi_y]")
    page.check("#hdDaTraHang")
    page.click("#btnXacNhanHuyDon")
    expect(page.locator("#modalPhieuHuy")).to_have_class(re.compile("active"), timeout=10000)
    tien = page.locator("#phTienHoan").inner_text()
    page.screenshot(path=str(ANH / "D1_phieu_hoan.png"))
    page.fill("#inputTuKhoaDonGui", "")
    assert "100.000" in tien, tien
    return f"Phiếu hoàn: {tien.strip()}"


@ca("J1", "Thống kê: doanh thu = trả trước + COD − hoàn")
def k_j1(page: Page) -> str:
    mo_tab(page, "thong-ke")
    page.wait_for_function("document.querySelector('#tkDoanhThu').innerText.trim() !== '' && !/^[-–—]+$/.test(document.querySelector('#tkDoanhThu').innerText.trim())")
    dt, tt, cod, hoan = so(page, "#tkDoanhThu"), so(page, "#tkTienTraTruoc"), so(page, "#tkTienCod"), abs(so(page, "#tkTienHoan"))
    assert dt == tt + cod - hoan, f"doanh thu {dt} ≠ {tt} + {cod} − {hoan}"
    return f"{dt:,} = {tt:,} + {cod:,} − {hoan:,}"


@ca("F1", "Hàng đến: chip nhóm có số đếm, bấm chip lọc đúng nhóm")
def k_f1(page: Page) -> str:
    dang_nhap(page, "guihang.laocai@demo.nhaxe.vn")
    mo_tab(page, "hang-den")
    page.wait_for_selector("#tbodyHangDen tr")
    chips = page.locator("#chipsHangDen .quick-filter-chip")
    for i in range(chips.count()):
        chips.nth(i).click()
        expect(chips.nth(i)).to_have_class(re.compile("active"))
    nhan = chips.all_inner_texts()
    chips.first.click()
    return " | ".join(n.replace("\n", " ") for n in nhan)


@ca("F3", "Ghi 'Đã gọi báo được người nhận' → đơn sang Chờ lấy, nhãn Đã báo")
def k_f3(page: Page):
    dong = dong_hang_den(page, MA["lc_cho_goi_bao"])
    dong.locator("[data-hanh-dong='lien-he']").click()
    expect(page.locator("#modalLienHe")).to_have_class(re.compile("active"))
    page.locator("#lhLuaChon label", has_text="Đã gọi báo được người nhận").click()
    page.fill("#lhGhiChu", "Test tự động — hẹn chiều lấy")
    page.click("#btnLuuLienHe")
    expect(page.locator("#lhLichSu")).to_contain_text("Đã báo được người nhận", timeout=10000)
    dong_het_modal(page)
    page.wait_for_load_state("networkidle")
    expect(page.locator("#tbodyHangDen tr", has_text=MA["lc_cho_goi_bao"])).to_contain_text("Đã báo")
    page.fill("#inputTraCuuGiao", "")


@ca("F5", "Giao đơn trả trước qua ô tra cứu: chưa tích kiểm hàng thì chặn, tích rồi giao + in phiếu")
def k_f5(page: Page):
    page.fill("#inputTraCuuGiao", MA["lc_giao_tra_truoc"])
    page.press("#inputTraCuuGiao", "Enter")
    expect(page.locator("#modalGiaoHangCOD")).to_have_class(re.compile("active"), timeout=10000)
    page.click("#btnXacNhanGiaoHang")
    assert "active" in page.locator("#modalGiaoHangCOD").get_attribute("class"), "giao được khi chưa tích kiểm hàng"
    page.check("#chkKiemTraKienHang")
    page.click("#btnXacNhanGiaoHang")
    expect(page.locator("#modalPhieuXuatKho")).to_have_class(re.compile("active"), timeout=10000)
    dong_het_modal(page)
    page.fill("#inputTraCuuGiao", "")
    # danh sách tải lại sau khi giao — chờ tới khi đơn biến mất (không kiểm ngay kẻo bắt nhầm bản cũ)
    page.wait_for_function("m => !document.querySelector('#tbodyHangDen').innerText.includes(m)", arg=MA["lc_giao_tra_truoc"], timeout=8000)


@ca("H1", "Phụ xe tới Lào Cai + dỡ hàng (API) → VP Lào Cai nhận thông báo real-time")
def k_h1(page: Page, tk_px: str, don: dict) -> str:
    mo_tab(page, "hang-den")
    xoa_toast(page)
    api("POST", f"/phu-xe/chuyen/{don['chuyen_id']}/toi-diem", tk_px, {"diem_don_tra_id": str(don["diem_nhan_id"])})
    api("POST", f"/phu-xe/don-hang/{don['id']}/do-hang", tk_px)
    tin = toast_cuoi(page, MA["lc_xe_dang_chay"], timeout=10000)
    page.screenshot(path=str(ANH / "H1_toast.png"))
    page.wait_for_function("m => document.querySelector('#tbodyHangDen').innerText.includes(m)", arg=MA["lc_xe_dang_chay"], timeout=10000)
    return tin[:150]


# ================================================================== chạy
def chuan_bi() -> dict:
    """Seed lại dữ liệu demo, đọc mã vận đơn theo mô tả, đăng nhập lấy token."""
    print("Seed lại dữ liệu demo...", flush=True)
    seed = docker("exec", "-T", "backend", "python", "scripts/seed_gui_hang_demo.py", timeout=600)
    (ANH / "seed_out.txt").write_text(seed, encoding="utf-8")
    if "Đã tạo dữ liệu demo" not in seed:
        sys.exit(f"Seed thất bại:\n{seed[-1500:]}")
    for khoa, mo_ta in MO_TA.items():
        dong = next((d for d in seed.splitlines() if mo_ta in d), None)
        if not dong:
            sys.exit(f"Không thấy đơn '{mo_ta}' trong output seed — seed_gui_hang_demo.py đã đổi mô tả?")
        MA[khoa] = re.search(r"DH-\d{8}-[0-9A-F]{6}", dong).group()
    tk = {"md": token_dang_nhap("guihang.mydinh@demo.nhaxe.vn"), "lc": token_dang_nhap("guihang.laocai@demo.nhaxe.vn"),
          "px": token_dang_nhap("phuxe.guihang@demo.nhaxe.vn", "PhuXe@123")}
    return tk


def tra(ma: str, tk: str) -> dict:
    return api("GET", f"/gui-hang/noi-bo/tra-cuu/{ma}", tk)[1]


def mo_trinh_duyet(p):
    tr = p.chromium.launch(channel="msedge", headless=not THAM_SO.hien)

    def trang(ten):
        pg = tr.new_context(viewport={"width": 1440, "height": 900}, locale="vi-VN", accept_downloads=True).new_page()
        pg.on("console", lambda m: m.type == "error" and CONSOLE.append(f"[{ten}] {m.text[:200]}"))
        pg.on("pageerror", lambda e: CONSOLE.append(f"[{ten} pageerror] {e}"))
        pg.on("dialog", lambda d: d.accept())
        return pg
    return tr, trang


def chay_khoi(p):
    tk = chuan_bi()
    tr, trang = mo_trinh_duyet(p)
    pg = trang("khoi")
    k_a1(pg)
    ma_moi = []
    for fn in (k_b1, k_b2):
        n = len(KQ)
        fn(pg)
        m = re.search(r"DH-\d{8}-[0-9A-F]{6}", KQ[n][2]) if KQ[n][1] == "ĐẠT" else None
        if m:
            ma_moi.append(m.group())
    k_b4(pg); k_b5(pg); k_b6(pg); k_c1(pg, ma_moi); k_d1(pg); k_j1(pg)
    k_f1(pg); k_f3(pg); k_f5(pg)
    k_h1(pg, tk["px"], tra(MA["lc_xe_dang_chay"], tk["lc"]))
    tr.close()


def chay_day_du(p):
    tk = chuan_bi()
    tk_md, tk_lc, tk_px = tk["md"], tk["lc"], tk["px"]
    # Token quản lý sinh trong container (repo không có mật khẩu quản lý gốc) + tài khoản gửi hàng tạm chưa gán văn phòng
    ra = py_backend("""
from app.db import get_connection, release_connection
from app.middleware.auth_middleware import tao_token
from app.services.mat_khau_service import _pwd_context
c = get_connection(); cur = c.cursor()
cur.execute("SELECT id::text FROM nguoi_dung WHERE vai_tro='quan_ly' AND dang_hoat_dong ORDER BY ngay_tao LIMIT 1"); ql = cur.fetchone()[0]
cur.execute("DELETE FROM nguoi_dung WHERE email='tam.chua.gan.vp@demo.nhaxe.vn'")
cur.execute("INSERT INTO nguoi_dung (email, mat_khau, ho_ten, so_dien_thoai, vai_tro, da_xac_nhan) VALUES (%s,%s,%s,%s,'nhan_vien_gui_hang',true) RETURNING id::text",
            ('tam.chua.gan.vp@demo.nhaxe.vn', _pwd_context.hash('Tam@12345'), 'Tam Chua Gan', '0911999888'))
tam = cur.fetchone()[0]; c.commit(); release_connection(c)
print('TOKEN', tao_token(ql, 'quan_ly'), tao_token(tam, 'nhan_vien_gui_hang'))
""")
    tk_ql, tk_tam = re.search(r"TOKEN (\S+) (\S+)", ra).groups()

    don_md = api("GET", "/gui-hang/don-hang?huong=gui&limit=100", tk_md)[1]["items"]
    tren_xe = next(d for d in don_md if d["trang_thai"] == "da_len_xe" and d["trang_thai_chuyen"] == "dang_chay")
    quen = next(d for d in don_md if d["trang_thai"] == "da_giao")
    don_lc_xe = tra(MA["lc_xe_dang_chay"], tk_lc)
    don_de_vo = tra(MA["lc_de_vo_tren_xe"], tk_lc)
    cod55 = tra(MA["lc_cod_55"], tk_lc)
    vp_ids = {vp["ten"]: vp["id"] for kv in api("GET", "/gui-hang/diem-nhan-kha-dung", tk_md)[1] for vp in kv["van_phong"]}
    ids = {"lc": str(don_lc_xe["diem_nhan_id"]), "md": str(don_lc_xe["diem_gui_id"]),
           "yb": next(v for k_, v in vp_ids.items() if "Yên Bái" in k_),
           "sp": next(v for k_, v in vp_ids.items() if "Sa Pa" in k_),
           "loai": next(l_["id"] for l_ in api("GET", "/gui-hang/loai-hang", tk_lc)[1] if not l_["la_hang_cam"])}
    ids["tuyen"] = api("GET", f"/gui-hang/tuyen-phu-hop?diem_nhan_id={ids['md']}", tk_lc)[1][0]["id"]
    ids["tuyen_sp"] = api("GET", f"/gui-hang/tuyen-phu-hop?diem_nhan_id={ids['sp']}", tk_md)[1][0]["id"]

    tr, trang = mo_trinh_duyet(p)
    try:
        tam, ql, md, lc, yb = trang("tam"), trang("ql"), trang("md"), trang("lc"), trang("yb")
        print("A. Quyền", flush=True)
        a2(tam); a3(ql, tk_ql); a4(tam, tk_tam); a5(yb); a6(yb)
        dang_nhap(md, "guihang.mydinh@demo.nhaxe.vn"); dang_nhap(lc, "guihang.laocai@demo.nhaxe.vn")
        print("B. Tạo đơn", flush=True)
        b3(md); b7(md); b8(md, quen["sdt_nguoi_gui"], quen["ten_nguoi_gui"]); b9(md, tk_md); b10(md, tk_md); b11(md)
        print("C. Đơn gửi đi", flush=True)
        c2(md); c3(md); c4(md); c5(md); c6(yb)
        print("D. Hủy đơn", flush=True)
        moi = api("GET", "/gui-hang/don-hang?huong=gui&trang_thai=cho_van_chuyen&limit=50", tk_md)[1]["items"]
        tao_test = [d["ma_van_don"] for d in moi if d["ten_nguoi_nhan"] in ("Bam Hai Lan", "Mat Mang F5")] or [MA["md_cho_xep_2_ngay"]]
        d2(md); d3(md, tao_test[0]); d4(md, tao_test[-1])
        d5(md, tk_md, tren_xe["ma_van_don"], str(tren_xe["id"]))
        d6(tk_lc, str(tra(MA["md_cho_xep_2_ngay"], tk_md)["id"])); d7(md)
        print("E. Sửa SĐT", flush=True)
        e1(md); e2(md, lc); e3(lc); e4(md)
        print("F. Hàng đến / giao", flush=True)
        f2(md, lc); mo_tab(lc, "hang-den")
        f4(lc); f8(lc, cod55["sdt_nguoi_nhan"], MA["lc_cod_55"]); f6(lc); f7(lc); f9(lc); f10(lc); f11(md)
        print("G. Hàng chờ lâu", flush=True)
        g1(lc); g2(lc); g3(lc); g4(lc, tk_ql); g5(lc); g6(lc); g7(lc); g8(lc); g9(lc)
        print("H. Phụ xe", flush=True)
        h2(lc, tk_px, don_lc_xe); h3(lc, tk_px, tk_lc, don_lc_xe)
        h4(lc, tk_px, tk_ql, str(don_de_vo["id"]), MA["lc_de_vo_tren_xe"])
        print("I, J, K, P", flush=True)
        i1(lc); j3(md); j4(md); j5(md); j6(ql, tk_ql); k(md); k5(md); p_api(tk_ql, tk_lc, ids)
        i2(lc, lambda: token_dang_nhap("phuxe.guihang@demo.nhaxe.vn", "PhuXe@123"), str(don_de_vo["id"]), MA["lc_de_vo_tren_xe"])
    finally:
        tr.close()
        py_backend("""
from app.db import get_connection, release_connection
c = get_connection(); cur = c.cursor()
cur.execute("DELETE FROM nguoi_dung WHERE email='tam.chua.gan.vp@demo.nhaxe.vn'"); c.commit(); release_connection(c)
""")


def main():
    if not re.match(r"http://(localhost|127\.0\.0\.1)[:/]", BE):
        sys.exit("Chỉ chạy với backend local.")
    try:
        urllib.request.urlopen(BE + "/docs", timeout=5)
    except Exception:  # noqa: BLE001
        sys.exit(f"Backend chưa chạy ở {BE} — bật Docker rồi `docker compose up -d`.")
    try:
        urllib.request.urlopen(FE + "/nhan-vien/dang-nhap.html", timeout=5)
    except Exception:  # noqa: BLE001
        sys.exit(f"Frontend chưa chạy ở {FE} — mở VS Code, bấm Go Live (Live Server).")

    print(f"Ảnh chụp / file tải về: {ANH}", flush=True)
    with sync_playwright() as p:
        if THAM_SO.bo in ("khoi", "tat-ca"):
            print("\n===== Bộ [Khói] =====", flush=True)
            chay_khoi(p)
        if THAM_SO.bo in ("day-du", "tat-ca"):
            print("\n===== Các ca còn lại =====", flush=True)
            chay_day_du(p)

    print("\n================ KẾT QUẢ ================")
    for ma, kq, mo_ta in KQ:
        print(f"{ma:<4} {kq:<6} {mo_ta}")
    so_loi = sum(k_ == "LỖI" for _, k_, _ in KQ)
    print(f"\nĐạt {sum(k_ == 'ĐẠT' for _, k_, _ in KQ)} / Lỗi {so_loi} / Bỏ qua {sum(k_ == 'BỎ QUA' for _, k_, _ in KQ)} — tổng {len(KQ)}")
    print(f"Ảnh chụp ca lỗi (*_LOI.png) và file tải về: {ANH}")
    if CONSOLE:
        print(f"Lỗi Console trình duyệt ({len(set(CONSOLE))}, gồm cả lỗi cố ý gây ra như mất mạng ở B10, 403/400 ở ca chặn):")
        for l_ in dict.fromkeys(CONSOLE):
            print("  ", l_[:200])
    sys.exit(1 if so_loi else 0)


if __name__ == "__main__":
    main()
