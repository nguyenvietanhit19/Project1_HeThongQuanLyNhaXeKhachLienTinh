Test ở đây chạy trên Postgres thật, không mock — chạy `docker-compose up` trước, rồi `pytest backend/tests/integration`.

Đặc biệt quan trọng cho `ve_repository.py` (khóa dòng + kiểm tra overlap chống trùng ghế, `NGHIEP_VU.md` mục 6) — logic này không mock được, xem `ARCHITECTURE.md` mục 3.
