# Kiểm tra quà phù phép — 2026-10-02

- `gradlew --no-daemon build`: đạt, gồm `SELECTED_ENCHANT_CHECKS_OK` và các kiểm tra cũ của mod.
- `test_enchant_options`: 3 test đạt; đủ 43 loại, lưu/tải lại, payload LIVE/test giống nhau,
  số lượt theo lượng quà, chống trùng loại, giới hạn cấp, giữ giao thức FULL cũ.
- `test_settings.SettingsTests.test_enchant_levels_and_positions_roundtrip`: đạt sau khi cố định
  `amount=1` trong dữ liệu mẫu, thay vì phụ thuộc số lượng quà trong cấu hình mặc định của người dùng.
- `test_reward_options`: 3 test đạt.
- `browser_reward_options_smoke.py`: đạt, gồm kiểm tra enchant qua Chrome và HTTP backend thật:
  tìm phần thưởng, tìm loại, chỉnh số loại/cấp, lời nguyền, tự lưu, tải lại và trở về FULL.
- Ảnh kiểm tra: `tests/artifacts/enchant-options.png`.

Bộ `test_settings` tổng thể vẫn có các lỗi ngoài phần enchant: bộ kiểm kê control chưa ghi nhận
các control động `notification_display_modes`, `gift_actions`, `event_images`; ba test sự kiện
dùng client mô phỏng thiếu `_asyncio_loop`. Không thay đổi logic LIVE để xử lý những lỗi fixture này.

Kiểm tra Java dùng registry thật và dữ liệu trang bị mô phỏng; chưa kiểm tra nhận quà LIVE
hoặc thao tác trong world Minecraft đang chạy. Cần khởi động lại Minecraft để nạp JAR mới.
