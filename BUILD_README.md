# Build mod và GUI

- Chạy `build.bat`: build mod, sao lưu JAR cũ vào `TikTokMobForge/release/backups/deploy-*`, rồi chép JAR mới vào `mods` của thư mục Minecraft trong cài đặt GUI. Script kiểm tra nội dung JAR và SHA256 sau khi chép; lỗi sẽ trả mã thoát khác 0.
- Script chọn `gui_state.json` được lưu gần nhất giữa GUI mã nguồn, GUI bản publish và GUI đã cài tại `%LOCALAPPDATA%/Programs/TikTokMobForge/app/GUI`. Đường dẫn cài đặt và thư mục đích được in trước khi build.
- Muốn chỉ định chính xác cấu hình: `build.bat -GuiStatePath "C:\duong-dan\GUI\gui_state.json"`.
- Chạy `pushlih.bat` để tạo GUI WinForms và bộ cài mới. GUI nằm tại `TikTokMobForge/artifacts/desktop/TikTokMobForge.Desktop.exe`; bộ cài nằm trong `TikTokMobForge/artifacts/installer`.
- Khởi động lại Minecraft để nạp mod mới. Nếu Minecraft đang khóa JAR, đóng game rồi chạy lại `build.bat`.
