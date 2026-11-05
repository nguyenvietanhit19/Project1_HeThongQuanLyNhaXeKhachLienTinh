-- Hoàn tác "đã lên xe"/"đã xuống xe" khi phụ xe bấm nhầm (UC-12/UC-13).
-- Chạy SAU 20261006_0900. `gio_hoan_tac` != NULL nghĩa là phụ xe đã tự tay xử lý vé này,
-- job no-show (UC-14) bỏ qua để không đánh dấu "không đến" đè lên thao tác hoàn tác.

ALTER TABLE ve ADD COLUMN IF NOT EXISTS gio_hoan_tac TIMESTAMPTZ NULL;
