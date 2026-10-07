-- Mã giao dịch (vnp_TxnRef) của lần tạo đường dẫn thanh toán VNPay gần nhất cho vé.
-- Để backend tự hỏi VNPay (querydr) kết quả của lượt đang chờ thanh toán khi IPN không tới được.
ALTER TABLE ve ADD COLUMN ma_tham_chieu_vnpay TEXT NULL;
