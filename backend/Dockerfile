FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chạy migration truoc moi lan khoi dong container (ARCHITECTURE.md muc 8),
# roi moi start server bang && - server khong khoi dong neu migration loi.
# --batch: khong hoi xac nhan (khong co TTY o production). --no-config-file:
# khong tim/tao yoyo.ini (file nay chi dung cho dev local, xem .gitignore).
CMD ["sh", "-c", "yoyo apply --batch --no-config-file --database \"$DATABASE_URL\" ./migrations && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
