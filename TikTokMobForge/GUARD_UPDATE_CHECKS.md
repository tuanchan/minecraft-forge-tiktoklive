# Cập nhật ngày 22/09/2026

## Bổ sung: chờ hồi sinh

Khi người nhận chết, hàng gameplay giữ nguyên và tạm dừng mob, vật phẩm, hiệu ứng, thông báo. Các mob đang chờ tìm vị trí cũng chỉ thử sinh lại khi chủ nhân còn sống. Sau khi hồi sinh, xử lý tiếp theo tốc độ mỗi tick đã cấu hình. Thông báo đang hiện được ẩn và dừng thời gian khi chết; GIF dùng heartbeat để không hết hạn chờ sau 15 giây và tiếp tục sau hồi sinh. Giới hạn dung lượng hàng đợi hiện có vẫn áp dụng.

Kiểm tra bổ sung đạt: build Forge và các check Java; hàng 1.000 sự kiện giữ nguyên qua 1.200 tick chờ rồi lấy đúng phần tử đầu khi hồi sinh; 6 test media Python gồm chờ hồi sinh giả lập 60 giây và timeout khi Minecraft không phản hồi. Đã đồng bộ Python/JAR vào bản desktop, bản AppData và instance `live stream`, có backup và đối chiếu hash. Chưa kiểm thử trực tiếp thao tác chết/hồi sinh trong world.

- Người sắt do tool triệu hồi: không nhắm/đánh người chơi; chặn sát thương có nguồn từ người chơi, kể cả đạn do người chơi bắn. Mob khác vẫn gây sát thương bình thường. Theo người chơi, đánh mob đang nhắm người chơi, tìm chỗ đứng an toàn để teleport khi xa hơn 10 block hoặc khác chiều không gian. Tag chủ nhân được lưu theo entity. Chỉ áp dụng người sắt được triệu hồi từ bản mới.
- Bộ đếm chết: đọc thống kê Minecraft của từng người chơi, hiển thị góc trái; bật/tắt bằng Cài đặt → Mob hoặc F8 trong game. Đồng bộ mỗi giây, giữ số đếm khi hồi sinh/mở lại world.
- Mob donate: không tính vào giới hạn mỗi người/toàn world, không bị chọn để xóa khi hạ giới hạn, không hết hạn và bật persistence. Vẫn có thể bị giết. Hàng đợi sự kiện và tốc độ xử lý mỗi tick vẫn hoạt động như trước.
- Follow: lưu SQLite theo kênh và ID tài khoản; mỗi tài khoản chỉ nhận thưởng follow một lần, kể cả mở lại bridge. Ghi nhận người đã follow qua thông tin join/comment nếu TikTok gửi trạng thái. Không thể xác định lịch sử trước khi tool ghi nhận nếu TikTok không cung cấp thông tin đó.
- TTS: đọc `.env` UTF-8 có BOM và ưu tiên khóa vừa lưu; khi không có khóa ElevenLabs tự dùng giọng Việt Edge, có thông báo rõ trong log. Không sao chép khóa giữa các bản cài.

## Xác minh

- Forge: `BUILD SUCCESSFUL`; các check Java đạt, gồm 10.001 donation không tính vào giới hạn và chỉ chọn mob thường để xóa.
- Năm test mới Python đạt: lưu lịch sử qua khởi động lại, tách kênh, người follow cũ, handler follow thực với sự kiện giả lập, TTS thiếu khóa, bật/tắt bộ đếm.
- Giao diện thật qua Chrome headless: lưu/bật/tắt/reload bộ đếm; desktop/mobile không tràn ngang, không lỗi JavaScript. Đã mở xem ảnh kết quả.
- TEST GIỌNG thực trên bản nguồn: ElevenLabs tạo và phát xong âm thanh, exit 0.
- TEST GIỌNG thực trên bản đã cài AppData: thiếu khóa → tự dùng giọng Việt; tạo và phát xong âm thanh, exit 0.
- Bộ regression tổng chạy 108 test: còn 8 failures và 19 errors. Các lỗi gồm mock Client thiếu `_asyncio_loop`, danh sách control động và kỳ vọng giá trị/số lượng test không khớp cấu hình hiện tại. Không coi toàn bộ suite là đạt. Chi tiết: `logs/regression-guard.log`.
- Chưa xác minh AI, teleport, sát thương và HUD trong world Minecraft đang chạy; chưa kiểm thử follow bằng một phiên TikTok LIVE thật.

## File chạy

Đã đồng bộ các file runtime thay đổi vào `artifacts/desktop/app` và `%LOCALAPPDATA%/Programs/TikTokMobForge/app`; giữ nguyên cấu hình và `.env`. Đã chép JAR mới vào `C:/Users/ADMIN/curseforge/minecraft/Instances/live stream/mods/tiktokmob-1.0.0.jar`, hash khớp bản release. Bản cũ được lưu dưới `artifacts/backup-before-guard`.

Đóng/mở lại tool và Minecraft để tiến trình nạp mã mới. Chưa tạo lại bộ installer.
