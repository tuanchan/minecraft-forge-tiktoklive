TikTok LIVE Gift Downloader v2

Đã sửa lỗi đứng ở "Đang kết nối TikTok LIVE...":
- Không mở WebSocket nếu chỉ cần tải catalog quà.
- Bỏ bước is_live() dễ treo.
- Có timeout 12 giây lấy Room ID và 20 giây lấy gift list.
- Có API fallback nếu TikTok không trả Room ID từ HTML.

Cách chạy:
1. Cài Python 3.11+.
2. Double-click run.bat.
3. Nhập username TikTok.
4. Chọn thư mục lưu.
5. Bấm "TẢI TOÀN BỘ QUÀ".

Kết quả:
- images/: ảnh từng gift
- gifts.json
- gifts.csv
- raw_gift_info.json
