# TikTok Mob Forge — WinForms

- Chạy `TikTokMobForge.Desktop.exe` trong thư mục bản publish. Python và .NET được đóng gói kèm. Giữ nguyên thư mục `app` bên cạnh EXE.
- Bản cài `TikTokMobForge-Setup-1.1.0.exe` tạo shortcut và cài WebView2 nếu thiếu (cần Internet cho bước đó).
- Khung và thanh tiêu đề chuẩn WinForms, không có toolbar phụ bên dưới. Bấm Sao chép ảnh panel trong Panel LIVE để sao chép toàn bộ panel nền trắng, rồi Ctrl+V để dán.
- Panel LIVE có mục Người xem LIVE dùng icon `viewer.png`, hiển thị mob, số mob mỗi người và chu kỳ tạo mob theo cấu hình View.
- Ảnh vật phẩm dùng bộ inventory Minecraft Java 26.2 đã đóng gói theo ID, dùng được offline; không đoán texture theo tên. Nguồn và mã kiểm tra nằm trong `app/web/assets/minecraft-inventory/manifest.json`, giấy phép đi kèm trong cùng thư mục. Sáu vật phẩm có component (sách phù phép, thuốc, mũi tên hiệu ứng, súp đáng ngờ) dùng ảnh đại diện được ghi rõ trong manifest.
- Ảnh sao chép không chứa các nút Chỉnh sửa; các nút hiện lại trên GUI sau khi sao chép.
- Panel tương tác dùng nền trắng/chữ đen. Panel quà xếp số lượng → phần thưởng → icon quà theo cấu hình hiện có; rê chuột lên ô để đọc tên.
- Trong Cài đặt → Vị trí thông báo, chọn từng loại Like, Comment, Share, Follow, View, Quà tặng: kiểu cũ / giữa màn hình / chat trong game. Nút Áp dụng cho tất cả đổi cả sáu loại. Thay đổi tự lưu, giữ nguyên tọa độ cũ.
- Cần dùng JAR mới `app/release/tiktokmob-1.0.0.jar` trong thư mục `mods` của instance Forge 26.2 để có các kiểu hiển thị mới. Đóng Minecraft trước khi thay JAR.
- GIF cảm ơn quà có cấu hình riêng, tiếp tục hoạt động cùng cách hiển thị thông báo đã chọn.
- Đóng cửa sổ sẽ lưu cấu hình. LIVE đang chạy tiếp tục chạy nền; muốn ngừng LIVE hãy bấm Dừng trước khi đóng.
- Bản publish dùng cấu hình đã lưu khi chạy BAT làm mặc định: quà đã gán, tương tác, giọng đọc, hiển thị, cài đặt mod và ảnh tùy chỉnh. Mỗi lần publish xuất lại `GUI/default_profile.json`. API key, mật khẩu và token không được đóng gói; nhập riêng trên máy cài. Đường dẫn Minecraft dùng lại nếu tồn tại, nếu không sẽ chọn thư mục mặc định trên máy mới.
- Khi EXE còn nằm trong checkout mã nguồn, ứng dụng dùng cấu hình của checkout để giữ nguyên các tương tác đã thiết lập. Khi cài đặt hoặc chuyển nguyên thư mục publish ra ngoài checkout, ứng dụng dùng thư mục `app` đi kèm.
- Log khởi động: `app/GUI/logs/gui_startup.log`.

## Quà chơi khăm

Trong Quà tặng → Đặc biệt, kéo hiệu ứng vào dòng quà đã chọn hoặc nhấp đúp để gán. Có 10 lựa chọn kèm ảnh: gà (1 xu), mạng nhện 5 giây (5 xu), bí ngô (10 xu), Slowness II 10 giây (20 xu), dịch chuyển 5–10 block (50 xu), Creeper (100 xu), đe rơi (200 xu), xáo hotbar (500 xu), tiếng Warden (1.000 xu), Troll Box (quà lớn). Mức xu chỉ là gợi ý; ứng dụng vẫn nhận diện quà theo Gift ID, không tự thay các gán quà cũ.

- Gà/Creeper dùng cùng giới hạn và thời gian tồn tại của mob do tool tạo.
- Mạng nhện đặt ở ô không khí dưới chân, tự dọn sau 5 giây và khi đóng server bình thường. Nếu chân nằm trong block/nước, dùng chậm chạp 5 giây để không thay block đó.
- Bí ngô đội đến khi người chơi tháo ra; mũ cũ được chuyển vào túi quà F8.
- Dịch chuyển chỉ chọn vị trí trống có nền trong phạm vi 5–10 block; báo trong chat nếu không tìm được chỗ.
- Đe rơi cách ngang khoảng 2,5 block, từ độ cao 5 block, có thể gây sát thương tối đa 4 tim và biến mất khi chạm đất.
- Hotbar xáo 9 ô, giữ nguyên vật phẩm. Warden chỉ phát tiếng gầm, không tạo Warden thật.
- Troll Box chọn 3 hiệu ứng khác nhau từ 9 loại trên trong cùng lượt xử lý.
- Mọi Creeper được tạo bởi bản tool này, kể cả Creeper tích điện sau đó, nổ vẫn gây sát thương nhưng không phá block. Dấu nhận diện được lưu cùng mob. Creeper tự nhiên không bị đổi; không sửa gamerule mobGriefing.

## Build từ mã nguồn

Chạy `pushlih.bat` ở thư mục gốc. Cần .NET SDK 9, JDK 25, Inno Setup 6 và môi trường `bridge/.venv` đã cài `requirements.txt`. Script build mod bằng `assemble`, publish WinForms self-contained win-x64, đóng gói Python và tạo installer. Không chạy test.

`pushlih.bat -SkipInstaller` chỉ build/publish. Đầu ra tại `artifacts/desktop`, installer tại `artifacts/installer`.
