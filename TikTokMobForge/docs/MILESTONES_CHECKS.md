# Mốc tương tác / xu cả phòng LIVE

- Mở lại GUI và dừng/chạy lại bridge LIVE một lần để nạp mã mới. Không thay đổi Java/JAR.
- Tab **Tương tác**: tim, follow, bình luận, chia sẻ có công tắc riêng; thêm nhiều mốc, chọn mob/vật phẩm/hiệu ứng và số lượng cho từng mốc.
- Tab **Quà tặng**: bật mốc xu, mặc định đang tắt. Xu cộng từ `diamond_count × repeat_count`, chỉ khi combo kết thúc. Giá không biết không được tự đoán.
- Cộng chung cả phòng. Mỗi mốc lặp độc lập: mốc 100, nhận 250 thì đạt hai lần và giữ 50. Hai mốc 100 và 250 cùng tồn tại thì mỗi mốc có phần thưởng riêng.
- Tương tác riêng từng người giữ nguyên: tim tích lũy theo tài khoản, follow chống nhận trùng, comment/share có số lượng và thời gian chờ riêng. Các ô cấu hình và thẻ panel riêng đều được khôi phục.
- Mốc tổng LIVE chạy bổ sung: cùng một sự kiện có thể trao thưởng cá nhân và thưởng mốc tổng. Phần thưởng xu cộng thêm vào phần thưởng của từng quà đã gán.
- Tắt mốc một loại chỉ ngừng đếm/triệu hồi phần tổng, không tắt phần thưởng cá nhân hay quà đã gán. Sửa cấu hình mốc hoặc bật/tắt bắt đầu lại bộ đếm tổng của loại đó và hủy phần thưởng tổng loại đó còn chờ gửi.
- Dừng/chạy lại LIVE bắt đầu bộ đếm mới; reconnect tự động trong cùng tiến trình giữ tiến độ. Follow giữ cơ chế chống nhận trùng tài khoản đã có. Bình luận/chia sẻ đều cộng mốc tổng; thời gian chờ cá nhân vẫn áp dụng cho thưởng riêng và thông báo/TTS.
- Panel và nguồn link LIVE Studio dùng thanh Glass/Gel màu Sunset theo https://codepen.io/simeydotme/pen/bNEaqmb, gradient và bóng đổ tương ứng. Tiến độ cập nhật 500 ms, nội suy 420 ms. Ảnh xem thử: `../temp/milestone-panel.png`. Chưa đối chiếu pixel tuyệt đối với CodePen.
- Mốc vượt lớn được giữ trong hàng đợi, gửi tối đa 100 phần thưởng mỗi lượt xử lý; phần còn lại gửi tiếp. Lỗi kết nối giữ phần chưa gửi trong bộ nhớ. Giao thức TCP hiện tại không có xác nhận xử lý từ Minecraft, nên chưa bảo đảm exactly-once khi kết nối đứt sau khi ghi socket.

## Kiểm chứng 2026-09-28

- `python -m unittest discover -s tests -p test_milestones.py`: 8 tests PASS; gồm handler thật với sự kiện giả lập, thưởng cá nhân hoạt động khi mốc bật lẫn tắt, tim từng người không cộng lẫn, giới hạn comment/share riêng, thưởng quà và xu song song, nhiều vòng, phần dư, hàng đợi và lỗi gửi.
- `python tests/browser_milestones_smoke.py`: PASS; Chrome thật + HTTP backend + cấu hình tạm. Kiểm tra thêm mốc, bật xu, tự lưu, tải lại, giá trị progress và link riêng.
- `python tests/browser_live_panel_smoke.py`: PASS; hai browser profile riêng, cập nhật nội dung/ngoại hình, sao chép link, tải lại.
- Kiểm tra cú pháp Python/JS: PASS.
- Lần chạy rộng `test_settings.py` còn 5 lỗi: 3 fake client thiếu `_asyncio_loop`, danh sách trường UI động thiếu 3 tên, fixture số lượng quà lấy 10 từ profile nhưng mong đợi 1. Chưa chỉnh bộ kiểm tra cũ trong thay đổi này; kiểm tra handler mới dùng client giả lập đã cách ly vòng chạy và cấu hình.
- Chưa kiểm chứng với TikTok LIVE thật hoặc triệu hồi trong thế giới Minecraft đang chạy.
