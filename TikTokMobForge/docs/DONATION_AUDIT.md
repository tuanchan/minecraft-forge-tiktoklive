# Kiểm tra donate liên tục — 10/09/2026

**Kết luận: đường xử lý bình thường đếm đúng, nhưng hiện chưa bảo đảm không mất phần thưởng khi dồn tải hoặc ngắt kết nối.** Các kiểm thử dưới đây xác nhận cả hành vi đúng và những giới hạn còn tồn tại; test đạt không có nghĩa đã sửa cơ chế giao quà.

## Piglin hung bạo từ quà

`TikTokMobMod.spawnMobOfType` đặt `setImmuneToZombification(true)` sau khi khởi tạo mob, chỉ khi `interaction.donation()` và mob là `PiglinBrute`. Quái tự sinh, trứng spawn và Piglin hung bạo từ comment/share/follow/like không bị đổi. Áp dụng cho các con được triệu hồi sau khi nạp bản mod mới.

Đã kiểm tra bytecode Minecraft 26.2: cờ này chặn `isConverting()` và được lưu/đọc bằng `IsImmuneToZombification`, nên miễn chuyển hóa được giữ khi entity được lưu lại. Chưa kiểm tra trực tiếp bằng cách đưa mob qua cổng trong world.

## Kết quả kiểm tra quà

| Tình huống | Kết quả | Bằng chứng |
| --- | --- | --- |
| 3 người, mỗi người 20 lượt, mỗi lượt combo 3 quà × 20 mob | Bridge phát đủ 3.600 lệnh, mỗi người 1.200; mỗi lượt có một thông báo | `test_concurrent_donors_keep_all_repeat_times_amount_actions` — handler thật, đầu gửi được mock |
| Hai combo độc lập kết thúc ở 5 và 7 quà | Phát đúng `(5 + 7) × 20 = 240` lệnh; không cộng lại các gói cập nhật giữa combo | `test_combo_updates_wait_for_final_totals_for_each_donor` |
| Combo chưa gửi gói kết thúc | Chưa phát phần thưởng. Nếu mất gói cuối, bridge hiện không có cơ chế khôi phục phần này | `test_audit_unfinished_combo_has_no_reward_until_final_packet` |
| Gói kết thúc combo bị phát lại | Có thể trao trùng: chưa lọc theo ID sự kiện/combo | `test_audit_replayed_final_event_is_not_deduplicated` |
| Hàng đợi Minecraft đã có 1.000 lệnh, chưa được xử lý | Lệnh thứ 1.001, dù là donate, bị bỏ | `InteractionQueueChecks` gọi trực tiếp bộ phân tích TCP và hàng đợi thật, không mở world/listener |
| Một quà 10 phần thưởng, socket lỗi ở lần gửi thứ 4 | Chỉ gửi thành công 3; lỗi thoát khỏi vòng lặp, không có retry/lưu phần còn lại | `test_audit_socket_failure_interrupts_remaining_rewards_without_retry` |

`send_interaction()` chỉ dùng `sendall()`, không nhận xác nhận từ Minecraft. Gửi xong socket không chứng minh lệnh đã được đưa vào hàng đợi hoặc thực thi. Hàng đợi Java nằm trong RAM, nên các lệnh chưa chạy cũng không được giữ qua việc tắt tiến trình Minecraft. Các thao tác socket đồng bộ hiện chạy ngay trong callback LIVE, nên combo lớn còn có thể làm chậm việc nhận các sự kiện khác.

## Cấu hình đang dùng tại thời điểm kiểm tra

Instance: `C:\Users\ADMIN\curseforge\minecraft\Instances\live stream`.

- `max_pending_events = 1000`: giới hạn **lệnh phần thưởng**, không phải 1.000 quà. Một Glow Stick tạo 64 lệnh vật phẩm; Lucky Pig tạo 20 lệnh mob. Nếu chưa tiêu thụ lệnh nào, 16 Glow Stick đã cần 1.024 chỗ.
- `max_interactions_per_tick = 5`: tối đa khoảng 100 lệnh/giây khi server giữ 20 TPS. TPS thấp làm hàng đợi tiêu thụ chậm hơn.
- `max_mobs_per_user = 10`, `max_mobs_total = 500`, `mob_lifetime_seconds = 60`: Lucky Pig tạo 20 mob nhưng tối đa 10 mob của cùng người được giữ. Quái cũ của người đó bị xóa khi vượt ngưỡng; đây là giới hạn cấu hình, khác với mất sự kiện donate.
- `notification_queue_size = 10`, chính sách `drop_oldest`; thông báo donate dài 5 giây, khoảng nghỉ 1 giây. Dồn donate có thể làm mất chữ của lượt cũ, nhưng không hủy phần thưởng chỉ vì hàng đợi chữ đầy.

Log `2026-09-10-1.log.gz` có **172** lần `reason=limit_exceeded`; `2026-09-09-7.log.gz` có **20** lần. Đây là bằng chứng xóa mob do giới hạn mỗi người, không phải bằng chứng TikTok làm mất quà. Những kiểm thử ngắt kết nối, đầy hàng đợi và phát lại ở trên là mô phỏng offline, không khẳng định đã xảy ra trong buổi LIVE của bạn.

Vật phẩm đã được đưa thành công vào túi quà có lưu world; kiểm thử túi quà vẫn đạt về đầy hành trang, lấy một phần, phân trang và lưu/đọc. Enchant chưa có trang bị cũng tiếp tục được lưu chờ. Các hiệu ứng như sửa đồ/hồi máu có thể tác động lại lên cùng trạng thái, không nhất thiết thể hiện thành nhiều vật phẩm riêng.

## Hướng sửa cơ chế giao quà

Để bảo đảm giao quà khi dồn tải cần phối hợp: lưu hàng chờ bền vững ở bridge, gửi ngoài callback LIVE, ID riêng cho từng lệnh, xác nhận từ mod và retry có chống trao trùng. Khi mod đầy cần trả trạng thái chờ thay vì bỏ im lặng. Combo cần theo dõi ID và số lượng đã nhận để xử lý cập nhật/gói phát lại. Chỉ tăng dung lượng hàng đợi không giải quyết mất kết nối hoặc đóng game.

Phần thay đổi hành vi trong bản này là miễn chuyển hóa cho Piglin hung bạo từ quà; các cơ chế giao quà và giới hạn cấu hình trên vẫn giữ nguyên để báo cáo đúng hiện trạng.

## Chạy lại kiểm tra

```powershell
.\bridge\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\gradlew.bat --offline --no-daemon build
```

Kết quả: 22 kiểm thử Python đạt; build Java đạt, gồm `GIFT_QUEUE_AUDIT_OK`, `PENDING_ENCHANT_CHECKS_OK`, `GIFT_BAG_CHECKS_OK`. Không gửi quà thử vào LIVE hay world đang chơi.
