# Minecraft Forge TikTok LIVE

Kết nối TikTok LIVE với Minecraft Forge 26.2: nhận quà, sinh mob, phát vật phẩm và hiệu ứng, đọc bình luận, hiển thị thông báo và quản lý bằng GUI tiếng Việt.

## Thành phần

- `TikTokMobForge/src`: mã Java của mod Forge và các kiểm tra.
- `TikTokMobForge/bridge`: bridge TikTok LIVE và TTS bằng Python.
- `TikTokMobForge/GUI`, `TikTokMobForge/web`: backend và giao diện quản lý.
- `TikTokMobForge/Desktop`: ứng dụng WinForms/WebView2.
- `TikTokMobForge/scripts`, `TikTokMobForge/tests`: công cụ build, đóng gói và kiểm tra.

## Chạy từ mã nguồn

1. Cài Minecraft với Forge **26.2-65.1.3**, Python **3.10+** và JDK **25**.
2. Chạy `MO_GUI.bat`, chọn thư mục Minecraft và cấu hình tài khoản TikTok trong GUI rồi lưu.
3. Chạy `build.bat` để build và chép mod vào instance đã chọn, sau đó khởi động lại Minecraft.
4. Mở thế giới Minecraft và kết nối LIVE trong GUI.

Nếu chạy bridge trực tiếp, sao chép `TikTokMobForge/bridge/config.example.json` thành `config.json` trong cùng thư mục rồi chỉnh tài khoản/cấu hình. Khi dùng ElevenLabs, sao chép `.env.example` thành `.env` và nhập khóa riêng trên máy.

Chạy `TikTokMobForge/BUILD_MOD.bat` nếu chỉ cần build JAR. Chạy `pushlih.bat` để đóng gói GUI và bộ cài; yêu cầu .NET SDK 9 và Inno Setup theo script. Xem [hướng dẫn build](BUILD_README.md), [hướng dẫn dự án](TikTokMobForge/README.md) và [GUI desktop](TikTokMobForge/Desktop/README.md).

## Dữ liệu cục bộ

Git không lưu khóa API, `.env`, cấu hình riêng, lịch sử người xem, môi trường Python, cache, log hay sản phẩm build. Các quy tắc quà mặc định và tài nguyên giao diện nằm trong mã nguồn.
