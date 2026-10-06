# Nhiệm vụ

Mở lại GUI, vào **Nhiệm vụ** rồi thêm **Đào kim cương** hoặc **Giết mob**. Các thay đổi tự lưu; Minecraft đọc lại cấu hình khi đang trong world.

- Kim cương: mỗi khối quặng thường hoặc quặng đá sâu đào thành công trong sinh tồn tính 1, không nhân theo Gia tài. Đặt/đào lại quặng vẫn tính một lượt đào.
- Giết mob: `*` tính tổng mọi loại; chọn ID mob để đếm riêng loại đó. Có thể bật chỉ tính mob do mod triệu hồi. Tính mạng do người chơi trực tiếp hạ hoặc bắn; không tính mob tự chết, bị dọn bằng hiệu ứng tool hoặc do thú nuôi hạ.
- Số mốc chia đều thanh tiến độ từ 1 đến 100. Ví dụ mục tiêu 100 và 10 mốc tạo 10 đoạn bằng nhau, mỗi đoạn tương ứng 10 tiến độ. Mốc chỉ dùng để theo dõi trực quan, không tự phát quà.
- Mỗi nhiệm vụ có mục tiêu, công tắc, mức trừ khi chết theo điểm hoặc phần trăm tiến độ dương hiện có (làm tròn lên). Trừ theo điểm và quà có thể đưa tiến độ xuống số âm, không giới hạn ở 0; thanh sẽ rỗng nhưng nhãn vẫn hiện số âm. Tiến độ tối đa bằng mục tiêu; hoàn thành không tự trao vật phẩm hay lặp lại. Bị trừ có thể tiếp tục làm lại.
- Tiến độ riêng từng UUID người chơi, lưu cùng thế giới Minecraft, giữ qua chết/hồi sinh và mở lại world. Đổi loại mob hoặc bấm đặt lại bắt đầu bộ đếm mới. Tắt/bật và đổi kiểu hiển thị giữ tiến độ.
- 2D: kéo thanh trong khung 16:9 hoặc nhập vị trí X/Y và kích thước.
- 3D: nhìn vào bảng rồi giữ G để kéo, G + cuộn đổi cỡ, G + Shift + cuộn đổi khoảng cách, F ghim/bỏ ghim. X ẩn đến khi bật lại nhiệm vụ hoặc vào lại world. Dùng chung chuyển động và cài đặt kiểu bảng ghim.
- Giao diện giết mob dùng `gietmod.png` làm nền, `iconkiemkc.png` bên trái và zombie bên phải. Giao diện đào kim cương đặt cuốc bên trái, quặng bên phải và icon kim cương làm điểm nhấn. Cả 2D và 3D dùng thanh cyan chia mốc.
- Trong **Quà tặng**, chọn **Trừ tiến độ nhiệm vụ**, chọn một nhiệm vụ hoặc tất cả và số điểm trừ mỗi lượt. Số lượng và combo quà nhân số lượt, có thể trừ xuống số âm. Quà áp dụng cho người chơi nhận tương tác theo cơ chế hiện có của mod.

Cấu hình: `<Minecraft>/config/tiktokmob-missions.json`. Tối đa 32 nhiệm vụ. Trạng thái GUI đọc từ `tiktokmob-missions-state.json`; đây là bản xem, không phải dữ liệu lưu tiến độ của world.

Kiểm tra tự động: `gradlew.bat build`, `python -m unittest discover -s tests -p test_missions.py`, `python tests/browser_missions_smoke.py`. Kiểm tra trình duyệt dùng cấu hình tạm. Atlas gel có thể tạo lại bằng `python scripts/capture_mission_gel.py`.

Cần khởi động lại Minecraft sau khi thay JAR. Kiểm tra trực tiếp trong world: đào cả hai loại quặng, giết đúng/sai loại mob, chết với mức trừ, gửi quà test, mở lại world và kiểm tra bảng 2D/3D.
