# Hướng dẫn quy trình làm việc (dành cho người mới, chưa quen Git/Docker/deploy)

File này giải thích **cách thao tác cụ thể** hàng ngày — khác với `CONTRIBUTING.md` (nói **ai làm domain nào, tại sao chia vậy**). Đọc `CONTRIBUTING.md` trước để biết mình thuộc domain nào, rồi đọc file này để biết **làm từng bước ra sao**.

---

## 1. Chuẩn bị máy — chỉ làm 1 lần khi mới clone repo

```bash
git clone https://github.com/nguyenvietanhit19/Project1_HeThongQuanLyNhaXeKhachLienTinh.git
cd Project1_HeThongQuanLyNhaXeKhachLienTinh
cp backend/.env.example backend/.env
```

Mở `backend/.env` vừa tạo ra, điền giá trị thật:
- `JWT_SECRET`: gõ bừa 1 chuỗi dài ngẫu nhiên (không cần nhớ).
- `SMTP_USER`/`SMTP_PASSWORD`: để trống được nếu chưa cần test gửi email — hỏi trưởng nhóm nếu cần dùng Gmail chung của dự án.
- Các dòng còn lại giữ nguyên mặc định.

**File `.env` này không bao giờ commit lên Git** (đã bị `.gitignore` chặn) — mỗi người tự tạo riêng trên máy mình, không copy qua lại, không đẩy lên GitHub.

Dựng backend + database (Docker tự tải Postgres về, tự tạo database rỗng — không cần tự cài Postgres):

```bash
docker-compose up -d
docker-compose exec backend yoyo apply --database "$DATABASE_URL" ./migrations
```

Kiểm tra chạy đúng: mở trình duyệt vào `http://localhost:8000/docs` — thấy trang Swagger hiện ra là backend đã sống.

---

## 2. Vòng lặp làm việc — lặp lại cho MỖI UC bạn nhận

Ví dụ cụ thể: bạn nhận làm UC-05.

### Bước 1 — Nhận việc trên GitHub

Vào tab **Issues** → mở đúng thẻ UC-05 → bấm **"Assign yourself"**. Từ giờ mọi người biết UC-05 đang có người làm.

### Bước 2 — Lấy code mới nhất, tạo nhánh riêng

```bash
git checkout main
git pull
git checkout -b feature/<ten-ban>-uc05-dat-ve
```

### Bước 3 — Code theo kiểu "lát mỏng", không cần làm xong 100% mới chạy thử

1. Viết schema Pydantic trước (hình dạng request/response).
2. Viết route trả dữ liệu giả (hardcode) → thử ngay ở `/docs`.
3. Nối frontend gọi route giả đó → thấy chạy trên trình duyệt.
4. Quay lại viết logic thật (Service + Repository) đằng sau route.

Nếu cần gọi hàm của domain khác (VD gọi `chuyen_xe_service` của người 4) mà người đó chưa code xong — tự viết tạm 1 hàm giả đúng chữ ký đã thống nhất, ghi `# TODO`, không phải ngồi chờ.

### Bước 4 — Commit thường xuyên, không cần "đẹp"

```bash
git add .
git commit -m "them schema dat ve"
# ... code tiếp ...
git commit -m "route tra du lieu gia"
# ... nhiều commit nhỏ khác ...
```

Không cần lo commit lộn xộn — cuối cùng khi merge PR sẽ dùng **Squash and merge**, gộp hết thành 1 commit sạch trên `main` (xem mục 4).

### Bước 5 — Đẩy lên GitHub, mở Pull Request (PR)

```bash
git push origin feature/<ten-ban>-uc05-dat-ve
```

Vào GitHub, bấm **"Compare & pull request"** (nút vàng GitHub tự hiện cho đúng nhánh vừa push) → điền tiêu đề → **"Create pull request"**.

Ngay lúc này, robot CI (`backend-ci.yml`) tự chạy test — chờ vài giây/phút xem tab **"Checks"** báo ✔ hay ❌.

### Bước 6 — Xin review

Ở cột phải PR, mục **"Reviewers"** → bấm bánh răng ⚙️ → chọn 1 người trong nhóm → họ nhận được thông báo, vào PR bấm **"Files changed" → "Review changes" → Approve**.

### Bước 7 — Merge

CI xanh + có người approve → nút **"Squash and merge"** sáng lên → bấm → nhánh tự xóa (đã bật auto-delete).

### Bước 8 — Dọn dẹp, đóng Issue, qua UC tiếp theo

```bash
git checkout main
git pull
```

Đóng Issue UC-05 trên GitHub (hoặc ghi `Closes #<số>` trong mô tả PR để GitHub tự đóng lúc merge). Quay lại Bước 1 với UC tiếp theo.

---

## 3. Vài khái niệm hay gây nhầm — hiểu 1 lần là đủ

### Pull Request (PR) là gì

Giống "giơ tờ nháp lên xin cả nhóm đọc trước khi dán vào sổ chung" — bạn không code thẳng vào `main`, mà code ở nhánh riêng, mở PR xin merge, có CI kiểm tra + người khác đọc duyệt trước khi code thật sự vào `main`.

### Cùng sửa 1 file không có nghĩa là bị conflict

Git chỉ báo conflict khi 2 người **sửa đúng cùng dòng** — nếu bạn sửa hàm A, người khác sửa hàm B trong cùng 1 file, git tự ghép sạch, không hỏi gì cả. Đây là lý do quy tắc "mỗi bảng/file có đúng 1 chủ" ở `CONTRIBUTING.md` giúp giảm conflict thật sự.

### Squash and merge là gì

1 trong 3 cách GitHub gộp code — gộp **toàn bộ commit lặt vặt trên nhánh của bạn thành đúng 1 commit** trên `main`. Nhờ vậy `main` luôn sạch (`git log` thấy đúng 1 dòng = 1 UC), và bạn được thoải mái commit lộn xộn trên nhánh riêng.

### CI tự chạy khác với "bắt buộc phải xanh mới merge được"

- CI chạy tự động do khai báo `on: pull_request` trong file `backend-ci.yml` — chạy ngay khi mở PR, không liên quan gì tới cài đặt bảo vệ nhánh.
- Muốn CI đỏ thì **không merge được** (chặn thật) thì phải bật riêng "Require status checks to pass before merging" trong Settings → Branches — đây là bước bảo vệ nhánh `main`, khác hẳn việc CI có chạy hay không.

### Trưởng nhóm có thể "vượt rào" — người khác thì không

Trưởng nhóm (chủ repo) mặc định được phép bấm **"Merge without waiting for requirements to be met (bypass rules)"** khi thật sự cần (VD PR đầu tiên chưa ai kịp review) — 4 thành viên còn lại không có quyền này, luôn phải có người approve mới merge được.

---

## 4. Khi cần thêm bảng/cột mới trong database — viết migration, không tự sửa DB tay

### Nguyên tắc

Mỗi thay đổi cấu trúc database (thêm bảng, thêm cột...) viết thành **1 file `.sql` mới** trong `backend/migrations/`, đặt tên theo thời điểm: `20260920_1000_tao_bang_chuyen_xe.sql`. Không tự tay vào database sửa trực tiếp — vì máy mỗi người + Supabase (production) là 3 nơi khác nhau, chỉ có cách này mới giữ chúng giống hệt nhau.

### Các bước

1. Xem đúng cấu trúc cột cần tạo trong `DATABASE.md` (mục tương ứng bảng của domain bạn).
2. Tạo file mới trong `backend/migrations/`, viết câu `CREATE TABLE`/`ALTER TABLE` (xem file `20260917_0900_tao_bang_nguoi_dung.sql` làm mẫu).
3. Chạy thử local: `docker-compose exec backend yoyo apply --database "$DATABASE_URL" ./migrations` — chỉ file mới sẽ chạy, các file cũ được bỏ qua (yoyo tự nhớ đã chạy rồi).
4. Commit + mở PR như bình thường.

### Quy tắc vàng: KHÔNG sửa lại file migration đã merge vào `main`

Nếu phát hiện thiếu cột, viết **file mới** để `ALTER TABLE` thêm vào — không quay lại sửa file cũ, vì đồng đội đã chạy bản cũ trên máy họ, sửa lại sẽ khiến các máy lệch nhau.

### Lưu ý thứ tự

Nếu bảng của bạn tham chiếu (`FOREIGN KEY`) tới bảng của người khác (VD `chuyen_xe` của người 4 trỏ tới `tuyen` của trưởng nhóm), bảng bị tham chiếu phải có migration chạy **trước** — khớp đúng thứ tự phụ thuộc ở mục 3 `CONTRIBUTING.md`.

---

## 5. Xem dữ liệu trong database — dùng pgAdmin (hoặc công cụ tương tự)

Kết nối vào Postgres đang chạy trong Docker (phải đang `docker-compose up` mới kết nối được):

| Ô kết nối | Giá trị |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Maintenance database | `nha_xe` |
| Username | `postgres` |
| Password | `postgres_dev_only` |

Xem bảng theo đường dẫn: `Servers → (tên bạn đặt) → Databases → nha_xe → Schemas → public → Tables`.
