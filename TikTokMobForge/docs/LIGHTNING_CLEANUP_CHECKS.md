# Quà sấm sét và dọn mob tool

Trong tab **Quà tặng**, chọn phần thưởng **Sấm sét vào người chơi** hoặc **Dọn quái tool**. Chưa tự đổi các quà TikTok đã gán của người dùng.

## Sấm sét

- `lightning_player`: mặc định 5 tia, nghỉ 1 giây giữa hai tia.
- Sửa **Số tia sét mỗi đợt** và **Nghỉ giữa các tia** ngay dưới dòng quà. Ô số lượng quà là số đợt; combo cũng cộng thêm đợt. Các đợt nối tiếp theo từng người chơi.
- Mỗi tia lấy vị trí hiện tại của người chơi, không kiểm tra bầu trời/mái che. Bolt hiển thị và phát âm thanh; sát thương sét vanilla được áp trực tiếp một lần vào người chơi, không đánh lan vào các mob bên cạnh.
- Nhịp tính theo tick máy chủ, làm tròn lên; 0 giây nghĩa là mỗi tick (khoảng 0,05 giây ở 20 TPS). Số tia nhận số nguyên dương tới giới hạn biểu diễn Java, không giới hạn tùy ý 100 tia.
- Khi chết, chuỗi tạm chờ hồi sinh; chuyển chiều tiếp tục bám người chơi mới. Rời server hoặc dừng server hủy chuỗi. Miễn nhiễm của chế độ sáng tạo vẫn theo Minecraft.

## Dọn quái tool

- `clear_tool_mobs`: quét mob đang tải ở tất cả các chiều, chỉ nhận dấu `tiktokmob:summoned` hoặc `tiktokmob:donation`.
- Giữ người chơi, golem sắt/golem tuyết và chó sói của tool. Mob tự nhiên không bị tác động; mob tool khác, kể cả mèo tool, được dọn theo yêu cầu chỉ loại trừ golem/chó.
- Gọi cơ chế kill của Minecraft, không chỉ xóa hình ảnh. Mỗi mob đã chết được ghi chat: `[TikTok] Người tặng đã giết Tên mob (Loại mob)`. Tên người giết ở đây là nickname người tặng quà kích hoạt, không phải tên streamer.
- Mob trong chunk chưa tải từ lần chơi cũ không được nạp cưỡng bức để quét. Mob hiện do tool theo dõi vốn có cơ chế giữ chunk hoạt động.

## Kiểm tra và cài đặt

- `test_lightning_cleanup.py`: 2 tests PASS; lưu/đọc, dữ liệu gửi LIVE và nút test, số lượng × combo, kiểm tra đầu vào.
- `test_reward_options.py`: 3 tests PASS; không làm hỏng các tùy chọn quà trước đó.
- `browser_lightning_cleanup_smoke.py`: PASS; Chrome thật + backend/cấu hình tạm; nhãn tiếng Việt, nhập số tia/khoảng nghỉ, tự lưu, tải lại, hai mục phần thưởng.
- `gradlew.bat --offline --no-daemon build`: **BUILD SUCCESSFUL**, gồm `LIGHTNING_CLEANUP_OK` và các kiểm tra hiện có.
- Đã kiểm tra các class mới trong JAR và `META-INF/mods.toml`.
- JAR build, `release/tiktokmob-1.0.0.jar` và instance `C:/Users/ADMIN/curseforge/minecraft/Instances/live stream/mods/tiktokmob-1.0.0.jar` cùng SHA-256: `CF20CA08E7A7095763C8AFBE9CA4BBFE7D243B85B903EBDB443047952D1AA8D5`.
- Bản cũ được lưu tại `release/backups/lightning-cleanup-20260928-002953/`.
- Ảnh giao diện: `../temp/lightning-gift-options.png`.

Chưa kiểm thử gameplay trực tiếp. Khởi động lại Minecraft và GUI/bridge, thử sét trong nhà với 7 tia/0,25 giây; sau đó tạo zombie/creeper tool, mob tự nhiên, golem và chó tool rồi kích hoạt dọn quái để kiểm tra kết quả cùng chat.
