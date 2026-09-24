# Cài đặt LIVE

Mở `MO_GUI.bat` → **Cài đặt**. Trang này gồm kết nối, mob, hiển thị,
phần thưởng, giọng đọc và toàn bộ bộ chỉnh tương tác đang dùng ở tab Tương tác.
Chọn **Gán quà / phần thưởng** để mở bộ ghép quà với mob, vật phẩm hoặc hiệu ứng.

Tab **Tương tác** gom chọn mob, số lượng và chống spam vào từng nhóm. Với bình luận/chia sẻ, `1 lượt / 10 giây` nghĩa là mỗi tài khoản được tạo mob một lần rồi chờ 10 giây riêng. Hai tài khoản gửi cùng lúc đều được xử lý; bình luận không khóa chia sẻ. Áp dụng cho mọi loại mob được chọn trong nhóm. Theo dõi tạo mob theo từng lượt; tim được tích lũy riêng từng người, giữ lại phần dư cho người đó.

Bridge dùng ID tài khoản để tránh gộp hai người trùng tên hiển thị; log nhận/chặn có `user=...`. Đổi các mục TikTok cần dừng/chạy lại LIVE. Kiểm tra offline bằng `bridge\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v`; các kiểm thử có tình huống hai người gửi đồng thời và hết hạn đúng 10 giây.

## Hiển thị comment và tương tác

- Bật/tắt thông báo chung, tên người dùng và từng loại comment/share/like/follow/quà.
- Chọn hiện nội dung bình luận thay chữ Comment; giới hạn độ dài 1–96 ký tự.
- Chọn có hiện comment/share đang bị giới hạn tạo mob hay không.
- Chọn có hiện quà chưa gán phần thưởng hay không; loại này chỉ thông báo.
- Chỉnh số **thông báo** chờ, thời gian thường/donate, hiện dần, mờ dần, khoảng nghỉ.
- Chỉnh riêng màu nội dung thường, tên người dùng, donate và chữ đậm donate.
- Bật ưu tiên donate để phát sau thông báo hiện tại, trước lượt thường đang chờ.
- Khi đầy: giữ lượt đang chờ và bỏ lượt mới, hoặc bỏ lượt cũ nhất để nhận lượt mới.
  Nếu ưu tiên donate đang bật, donate có thể thay lượt thường cuối hàng;
  lượt thường mới không loại donate đang chờ. Mob/phần thưởng vẫn được xử lý.

Giới hạn hàng đợi tính theo lượt thông báo, không phải số tài khoản duy nhất.
Thời gian thường mặc định 1,5 giây, donate 4 giây, hàng đợi 100 lượt.
Màu xem thử trên web chỉ mô phỏng nội dung/màu, không phải kích thước thực trong game.
Khung xem thử lấy tỷ lệ vùng hiển thị của cửa sổ Minecraft đang mở, không tính thanh tiêu đề. Chiều cao tự thay đổi theo chiều rộng khung; khi không tìm thấy game sẽ dùng 16:9. Sau khi đổi kích thước cửa sổ game, bấm **Lấy kích thước Minecraft**. Kéo chữ để chỉnh tọa độ phần trăm; vị trí được tự động lưu. Font/cỡ chữ vẫn là mô phỏng, phụ thuộc GUI Scale và font/resource pack trong Minecraft.
Các lượt đã xếp trước khi đổi ưu tiên vẫn nằm trong hàng cũ đến khi được xử lý.

## Đọc comment

Có thể chọn giọng/model từ danh sách hoặc nhập Voice ID/Model ID trực tiếp.
Ô **Tìm giọng trong danh sách** lọc tên/ID; dùng dropdown **Chọn giọng đọc** để áp dụng. Dropdown **Chọn model đọc** cập nhật Model ID và tự động lưu. Có sẵn Flash v2.5, Turbo v2.5, Eleven v3 và Multilingual v2; khi API key có quyền `models_read`, danh sách được lấy từ tài khoản và chỉ giữ model đọc văn bản. Thông tin hỗ trợ ngôn ngữ tham khảo [danh sách model ElevenLabs](https://elevenlabs.io/docs/overview/models).

Giọng riêng được tải qua toàn bộ các trang của [API danh sách giọng](https://elevenlabs.io/docs/api-reference/voices/search). Nếu key thiếu `voices_read`, ứng dụng thử tải giọng công khai và giữ giọng hiện tại để chọn tiếp; trạng thái ngay dưới dropdown giải thích nguồn danh sách/lỗi tải. Tải danh sách không tạo âm thanh, không chứng minh mọi giọng/model đều dùng được với tài khoản. Bấm **Test giọng nói** để nghe cấu hình đã chọn.
Chỉnh âm lượng 0–1, tốc độ 0,7–1,2, độ ổn định, độ giống giọng,
biểu cảm, speaker boost, đọc tên, đọc comment bị giới hạn và độ dài tối đa.
Mã ngôn ngữ `vi`, `en`…; để trống để tự nhận diện.

- Tắt **Chọn comment mới nhất trong khoảng chờ**: đọc tuần tự, nghỉ sau mỗi câu.
  Khi đầy, bỏ câu mới đến. Tăng số comment chờ để nhận thêm.
- Bật lựa chọn này: trong khoảng chờ, chọn câu mới nhất; khi đầy, thay câu cũ nhất.
  Câu đang phát vẫn được đọc hết. Khoảng chờ 30 giây có nghĩa sẽ chọn một câu
  mới nhất trong 30 giây đó, không phải đọc tất cả các câu.

Âm lượng chỉ áp dụng cho âm thanh đọc comment của ứng dụng.
Nút Test giọng nói dùng cấu hình vừa lưu và gọi ElevenLabs thật.

## Áp dụng

Thay đổi tự động lưu sau khi ngừng chỉnh khoảng một giây, gồm ô nhập, chọn mob,
ảnh và kéo thả quà. Thanh trên cùng báo đang lưu, đã lưu hoặc lỗi; giá trị sai
không được ghi. Chạy LIVE/test sẽ đợi lưu xong để dùng đúng cấu hình mới nhất.
Cài đặt mod tự nạp khoảng mỗi giây khi world đang chạy;
cài đặt sinh mob có hiệu lực với các mob tạo tiếp theo. Chống biến mất tự nhiên
không chống chết và không bỏ giới hạn số lượng/thời gian sống.
Đổi phần TikTok hoặc giọng đọc: **Dừng → Chạy LIVE**. Đổi cổng: mở lại Minecraft.
Sau khi cập nhật mã ứng dụng, đóng panel và mở lại `MO_GUI.bat` để nạp máy chủ web mới.

Kiểm tra offline: `bridge\.venv\Scripts\python.exe tests\test_settings.py`.
Kiểm tra giao diện với Chrome và cấu hình tạm: `bridge\.venv\Scripts\python.exe tests\browser_settings_smoke.py`.

## Tab Kiểm thử

- Triệu hồi từng mob từ danh sách có tìm kiếm.
- Test riêng Like, Comment, Share, Follow; **Full spawn** chạy cả bốn loại
  với số mob mỗi tương tác đang cấu hình.
- Spam: chọn loại tương tác, 1–50 người, 1–100 vòng/người, nghỉ 0–10 giây/lệnh.
- Test từng quà đã gán hoặc toàn bộ quà, đúng loại và số lượng phần thưởng.
- Có tiến độ gửi, nhật ký và nút dừng. Mỗi bài test dùng nhóm ID mới;
  cùng một người trong bài test vẫn dùng chung ID để thử giới hạn mob/người.

Test không cần TikTok LIVE, gửi trực tiếp đến mod và không chờ mốc tim/cooldown
của bridge. Giới hạn mob và hiển thị của Minecraft vẫn áp dụng.
Tối đa 10.000 lệnh/bài test. Dừng chỉ hủy phần chưa gửi, không xóa mob đã tạo
hay lệnh đang nằm trong hàng đợi Minecraft. Tiến độ là số lệnh gửi, không phải
số mob tạo thành công; xem game và log mod để xác nhận kết quả thực tế.

Kiểm tra gửi TCP và dừng spam bằng máy nhận cục bộ:
`bridge\.venv\Scripts\python.exe tests\test_runner_checks.py`.
