# Tài liệu dự án

Các lệnh và đường dẫn trong tài liệu được tính từ thư mục gốc `TikTokMobForge/`.

- [Cài đặt](SETTINGS.md)
- [Tính năng quà tặng](GIFT_FEATURES.md)
- [Chọn loại và cấp phù phép](ENCHANT_GUIDE.md)
- [Kiểm tra donate](DONATION_AUDIT.md)
- [Hướng dẫn túi hộ vệ](GUARD_BAG_GUIDE.md)
- [Kiểm tra hộ vệ](GUARD_UPDATE_CHECKS.md)
- [Kiểm tra dọn sét](LIGHTNING_CLEANUP_CHECKS.md)
- [Kiểm tra các mốc tương tác](MILESTONES_CHECKS.md)
- [Kiểm tra tùy chọn phần thưởng](REWARD_OPTIONS_CHECKS.md)
- [Lịch sử thay đổi](changelog.txt)

## Cấu trúc thư mục

| Thư mục | Nội dung |
| --- | --- |
| `src/` | Mã nguồn mod Minecraft |
| `Desktop/` | Ứng dụng Windows |
| `GUI/`, `web/`, `bridge/` | Giao diện, tài nguyên và kết nối TikTok |
| `scripts/`, `tests/` | Công cụ build, đóng gói và kiểm tra |
| `docs/` | Hướng dẫn và ghi nhận kiểm tra |
| `release/` | Mod JAR để cài vào Minecraft |
| `artifacts/desktop/` | Bản ứng dụng đã đóng gói hiện tại |
| `artifacts/installer/` | Bộ cài Windows |
| `runtime/`, `tooltt/` | VOICEVOX và công cụ phụ trợ |
| `backups/` | Bản sao lưu và hồ sơ dọn thư mục |

Các file BAT ở thư mục gốc là điểm chạy nhanh. Thư mục `build/`, `bin/`,
`Desktop/bin/`, `Desktop/obj/` và `__pycache__/` có thể xuất hiện lại khi build hoặc chạy.

Đợt dọn ngày 2026-10-01 gom đầu ra cũ vào
`backups/cleanup-20261001/files/`. Đây là di chuyển, chưa giải phóng dung lượng.
Danh sách nằm trong `backups/cleanup-20261001/manifest.json`;
đường dẫn trong danh sách là vị trí gốc để khôi phục khi cần.
