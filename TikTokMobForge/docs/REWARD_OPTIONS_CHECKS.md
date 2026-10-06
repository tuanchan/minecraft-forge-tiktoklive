# Túi quà và tùy chỉnh quà

- Túi quà dùng thao tác container của Minecraft cho 36 ô đồ bên dưới: nhấc/đặt, chia stack, kéo chia, phím số và phím mở túi (mặc định E) để đóng. Các ô quà bên trên chỉ cho bấm nhận, không nhận đồ gửi vào. Đồ đang cầm được Minecraft xử lý khi đóng container.
- Bí ngô: mặc định 10 giây; mũ gốc được giữ trong SavedData của world, gồm độ bền, tên và enchant. Hết hạn trả lại mũ; nếu người chơi đã đội mũ khác thì mũ gốc về Túi quà. Thoát/chết cũng kết thúc hiệu ứng. Quà clear túi vẫn xóa cả mũ đang được giữ.
- TNT: mặc định 4 giây, chỉnh 0,1–3600 giây cho từng quà.
- Đe: khoảng cách ngang 0–64 block; 0 là ngay đầu. Các lượt nhận xếp hàng, rơi cách nhau 10 tick khi người chơi còn hoạt động; chọn vị trí trống cao 2–5 block. Nếu không có vị trí trống thì chỉ phát âm thanh. Hàng đợi kết thúc khi chết/thoát.
- Bay: 1–2048 block mỗi lượt, mặc định 96; mỗi lượt cộng vào đích bay hiện tại và kéo dài thời hạn chuyến bay. Trong trần kín có thể bay thêm để ra chỗ trống.
- Tơ nhện: bán kính ngang 0–16 block, mặc định 0 (ô chân); thời gian mặc định 5 giây, chỉnh 0,1–3600 giây. Chỉ đặt vào không khí trên mặt phẳng ngang chân, không thay công trình; hết hạn khôi phục các ô tơ còn nguyên. Lượt chồng lên nhau giữ thời hạn dài hơn.

Các ô chỉnh nằm ngay dưới phần thưởng tương ứng trong tab **Quà tặng**. Mở lại GUI để nạp backend mới; mở lại Minecraft để nạp JAR mới.

## Bằng chứng kiểm tra

- `build_mod.ps1`: `BUILD SUCCESSFUL`, gồm `REWARD_OPTIONS_OK` và các kiểm tra túi quà, enchant, chuyển động, guard.
- `test_reward_options`, `test_player_gifts`, `test_guard_rewards`, `test_fast_gifts`: 11 test đạt khi chạy với `PYTHONIOENCODING=utf-8`.
- `browser_reward_options_smoke.py`: đủ 6 ô, sửa giá trị, tự lưu và nạp lại đạt. Ảnh `tests/artifacts/reward-options.png` đã được kiểm tra trực quan.
- Chạy thêm `test_settings` còn 5 lỗi: 3 test giả lập client thiếu `_asyncio_loop`, 1 test danh sách control động và 1 test số lượt quà enchant. Bộ kiểm tra Python mở rộng chưa đạt toàn bộ.
- Bản build, release và `C:/Users/ADMIN/curseforge/minecraft/Instances/live stream/mods/tiktokmob-1.0.0.jar` có cùng SHA-256: `33F5E38319A0C695DBDCB1B6D5E079AC28DFC14F3C4DFDBB59FCABDCFD58047A`. JAR cũ đã được sao lưu trong `backups/reward-options-*`.
- Chưa kiểm tra trực tiếp thao tác trong Minecraft hoặc quà từ TikTok LIVE thật.
