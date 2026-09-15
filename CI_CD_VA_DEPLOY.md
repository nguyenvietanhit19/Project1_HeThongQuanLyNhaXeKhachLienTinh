# CI/CD và Quy trình Deploy — giải thích cho người chưa từng làm

File này giải thích **khái niệm và cách làm việc**, dành cho thành viên chưa từng làm việc nhóm chuyên nghiệp hay deploy thật bao giờ. Nếu bạn đã hiểu các khái niệm này rồi, xem `ARCHITECTURE.md` để biết chi tiết kỹ thuật (file YAML cụ thể, cấu hình từng nền tảng...).

---

## 1. GitHub Actions (`.github/workflows/`) là gì

**Tưởng tượng thế này**: Bình thường, sau khi sửa code xong, bạn phải tự tay chạy thử app xem có lỗi không. Đó là việc bạn tự làm, mỗi lần sửa code lại phải tự làm lại — dễ quên, dễ bỏ sót.

**GitHub Actions giống như bạn thuê được 1 "robot trợ lý" sống trên GitHub.** Robot không làm gì cho tới khi có 1 sự kiện xảy ra mà bạn đã dặn trước — ví dụ "mỗi khi có người đẩy code mới lên" hoặc "mỗi khi có người tạo Pull Request". Lúc đó robot tự động:
1. Tải code mới về (chạy trên máy chủ của GitHub, không tốn máy của bạn).
2. Làm những việc bạn đã dặn — ví dụ: chạy thử toàn bộ test đã viết sẵn.
3. Báo kết quả ngay trên GitHub — dấu ✔ xanh nếu ổn, dấu ❌ đỏ nếu có lỗi.

File `.yml` trong `.github/workflows/` chính là **"tờ hướng dẫn"** bạn viết cho robot: khi nào làm, và làm gì.

### Tại sao cần — kịch bản cụ thể

Bạn A sửa `auth_middleware.py` để thêm 1 kiểm tra quyền mới. Bạn A tự chạy thử vài chức năng mình quan tâm, thấy ổn, push code, merge vào `main`. Nhưng thay đổi đó vô tình làm hỏng chức năng "nhân viên nhận việc" mà bạn B đang phụ trách — bạn A không biết vì không nghĩ tới việc test lại phần đó. Vài ngày sau, bạn B kéo code mới về, thấy chức năng mình lỗi, mất công dò xem lỗi từ đâu.

**Có CI thì khác**: ngay khi bạn A tạo Pull Request, robot tự chạy toàn bộ test (kể cả phần của bạn B) — nếu có gì hỏng, GitHub báo đỏ ngay trên PR đó, **trước khi merge vào `main`**. Bạn A biết ngay và sửa luôn lúc đó.

Lý do cốt lõi: việc "code có chạy đúng không" không nên phụ thuộc vào trí nhớ/sự cẩn thận của từng người mỗi lần merge — nên để máy kiểm tra tự động, giống nhau, không quên, mỗi lần đều như nhau. Con người dồn sức vào việc máy không làm được (đọc hiểu logic, review thiết kế).

### Ví dụ file thật (khi đã có test để chạy)

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI

on:
  pull_request:              # chạy mỗi khi có Pull Request
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest    # GitHub tự cấp 1 máy ảo tạm thời
    steps:
      - uses: actions/checkout@v4                     # tải code của PR về
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r backend/requirements.txt   # cài dependency
      - run: pytest backend/tests/unit                 # chạy test
```

Đọc theo thứ tự: "khi nào" (`on: pull_request`) → "chạy trên máy gì" (`runs-on`) → "làm các bước gì theo thứ tự" (`steps`). Không cần nhớ hết cú pháp ngay, cứ copy mẫu này và chỉnh khi cần.

---

## 2. Deploy: vừa dev local vừa deploy, không phải "làm xong mới deploy"

### Hai "nơi" code của bạn tồn tại

- **Local (máy của bạn)**: nơi viết code, thử nghiệm, được phép chạy lỗi thoải mái vì chỉ mình bạn thấy.
- **Production (bản đã deploy)**: bản chạy thật trên Render/Vercel, có địa chỉ web thật, ai cũng vào xem được (giảng viên, người dùng thử...).

### Vòng lặp thực tế (lặp lại rất nhiều lần suốt project, không phải làm 1 lần)

```
1. Sửa/thêm code ở máy local, tự chạy thử thấy ổn
2. Đẩy code lên GitHub
3. Robot CI tự kiểm tra (phần 1 ở trên)
4. Nếu ổn, merge vào main
5. Render/Vercel thấy main vừa đổi → tự động deploy bản mới
6. Quay lại bước 1, tiếp tục sửa tính năng khác
```

Render và Vercel đều có sẵn tính năng "tự deploy khi có push vào `main`" trong dashboard của họ — kết nối thẳng tới GitHub repo, không cần tự viết thêm workflow deploy riêng. Bạn chỉ cần bật nó lên 1 lần.

### Tại sao không nên đợi "làm xong hết mới deploy 1 lần"

Đây là lỗi rất dễ mắc và khá nguy hiểm: **code chạy ổn ở máy bạn không có nghĩa là nó sẽ chạy ổn khi deploy thật.** Có nhiều thứ chỉ lộ ra khi deploy:
- Quên set biến môi trường trên Render (JWT secret, DB connection string...).
- Backend không kết nối được tới Supabase vì sai connection string.
- CORS chặn frontend (Vercel) không gọi được backend (Render).
- Docker build lỗi vì thiếu 1 dòng trong Dockerfile.

Nếu đợi đến sát ngày bảo vệ đồ án mới deploy lần đầu tiên, phát hiện lỗi lúc đó sẽ **không còn đủ thời gian sửa**.

### Việc nên làm đầu tiên khi bắt tay viết lại

Deploy 1 bản **cực kỳ đơn giản** trước — chỉ cần 1 API trả về `"OK"` và kết nối thử tới Postgres trên Supabase. Deploy thử lên Render, kiểm tra chạy được thật trên internet chưa. Việc này xác nhận toàn bộ "đường ống" đã thông:

```
Docker build → Render chạy được → kết nối tới Supabase → Vercel gọi được backend
```

**Xác nhận xong đường ống này rồi mới bắt đầu dồn công sức viết tính năng phức tạp lên trên.** Sau đó mỗi tính năng làm xong cứ đẩy lên, tự động deploy tiếp theo vòng lặp ở trên — không phải lo nghĩ lại từ đầu mỗi lần.

---

## 3. Tóm tắt nhanh

| Câu hỏi | Trả lời ngắn |
|---|---|
| `.github/workflows/` dùng để làm gì? | Tự động chạy kiểm tra (test) mỗi khi có Pull Request, để bắt lỗi trước khi merge vào `main` |
| Ai chạy các lệnh đó? | Máy chủ của GitHub (miễn phí, có giới hạn số phút/tháng nhưng đủ dùng cho BTL) |
| Có cần tự viết workflow để deploy không? | Không bắt buộc — Render/Vercel có sẵn tính năng tự deploy khi push vào `main`, chỉ cần bật trong dashboard |
| Dev xong hết mới deploy, hay vừa dev vừa deploy? | **Vừa dev vừa deploy**, lặp lại nhiều lần suốt project — deploy sớm ngay từ bản đơn giản nhất để phát hiện lỗi deploy sớm |
| Việc đầu tiên nên làm khi bắt đầu viết lại? | Deploy 1 API "Hello World" + kết nối DB thử trước, xác nhận đường ống hoạt động, rồi mới viết tính năng thật |
