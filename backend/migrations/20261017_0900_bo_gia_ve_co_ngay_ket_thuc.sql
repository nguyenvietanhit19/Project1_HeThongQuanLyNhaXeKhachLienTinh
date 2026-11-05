-- Bộ giá vé luôn có NGÀY KẾT THÚC (bắt buộc) và các bộ của 1 tuyến nối liền nhau (bộ sau bắt đầu ngày liền sau ngày kết thúc
-- của bộ trước — Service đảm bảo). Sinh chuyến chỉ được trong khoảng của các bộ.
-- Dữ liệu cũ: bộ có bộ kế tiếp thì kết thúc ở ngày liền trước bộ đó (đúng như cách hiểu cũ); bộ cuối thì kết thúc sau 90 ngày
-- kể từ ngày áp dụng hoặc ở ngày của chuyến xa nhất đã sinh, tùy ngày nào muộn hơn.
ALTER TABLE bo_gia_ve ADD COLUMN ap_dung_den DATE;

UPDATE bo_gia_ve b SET ap_dung_den = COALESCE(
    (SELECT n.ap_dung_tu - 1 FROM bo_gia_ve n
     WHERE n.tuyen_id = b.tuyen_id AND n.ap_dung_tu > b.ap_dung_tu ORDER BY n.ap_dung_tu LIMIT 1),
    GREATEST(
        b.ap_dung_tu + 90,
        COALESCE((SELECT max((c.gio_khoi_hanh AT TIME ZONE 'Asia/Ho_Chi_Minh')::date) FROM chuyen_xe c WHERE c.tuyen_id = b.tuyen_id),
                 b.ap_dung_tu + 90)
    )
);

ALTER TABLE bo_gia_ve ALTER COLUMN ap_dung_den SET NOT NULL;
ALTER TABLE bo_gia_ve ADD CONSTRAINT bo_gia_ve_ket_thuc_khong_truoc_bat_dau CHECK (ap_dung_den >= ap_dung_tu);
