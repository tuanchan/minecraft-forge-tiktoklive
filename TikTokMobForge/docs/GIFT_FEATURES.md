# Quà đặc biệt, vị trí thông báo và túi quà

Mở lại `MO_GUI.bat`, vào **Quà tặng**, chọn nhóm **Đặc biệt** và gán phần thưởng cho quà TikTok. Cấu hình cũ được giữ nguyên; các phần thưởng mới chưa tự gán vào quà đang có.

- **Enchant FULL giáp**: món đang mặc nhận ngay. Ô trống giữ quà chờ riêng: mặc mũ trước thì mũ nhận, áo/quần/giày tiếp tục đợi món đầu tiên ở từng ô. Sau khi ô đó nhận xong, thay món khác không nhận lại từ cùng quà.
- **Enchant FULL vũ khí tay chính**: vũ khí đang cầm nhận ngay; nếu tay trống hoặc cầm đồ khác, quà chờ vũ khí phù hợp đầu tiên ở tay chính. Gồm kiếm, rìu, giáo, chùy, đinh ba, cung và nỏ theo tag trang bị của Minecraft.
- **Cấp enchant**: `0` lấy cấp tối đa tự nhiên riêng của mỗi enchant; `1–255` áp cùng cấp được chọn. Không hạ enchant đang cao hơn. Gồm cả enchant xung khắc nếu từng enchant dùng được cho món đồ, nhưng không thêm lời nguyền. Mức độ cộng dồn tác dụng vẫn do Minecraft xử lý.
- **Sửa giáp**, **sửa đồ đang cầm**, **hồi đầy máu và thức ăn**, **tặng 1–255 cấp kinh nghiệm**.

Enchant còn chờ được lưu theo UUID trong world, giữ nguyên cấp đã tặng qua chết/hồi sinh và thoát vào lại. Mỗi quà giáp chờ đủ bốn ô; quà vũ khí chờ một lần ở tay chính. Chat báo số ô còn chờ khi nhận quà và khi trang bị được enchant. Sửa đồ vẫn tác động ngay lên trang bị hiện tại. Số lượng và cấp là hai thông số riêng. Nút test sử dụng đúng cấp đã lưu như quà LIVE.

Trong **Cài đặt → Hàng đợi hiển thị**, sửa ngang/dọc/cỡ chữ từng loại Like, Comment, Share, Follow hoặc Quà tặng. Tick các loại rồi dùng **Áp dụng cho đã tick**, hoặc dùng **Áp dụng cho tất cả**. Khung xem thử cho phép kéo thông báo của loại đang chọn. Tọa độ là phần trăm khoảng trống khả dụng, nên 100% vẫn giữ thông báo trong màn hình. Mod tự nạp cấu hình khoảng mỗi giây; tên người xem, màu, thời lượng, fade và ưu tiên donate vẫn áp dụng.

Quà vật phẩm từ mọi phần thưởng đi vào **túi quà**. Nhấn **B** trong game (đổi phím được trong Controls), hoặc mở hành trang và bấm `iconbaggift.png` ở góc dưới phải. Giao diện dùng khung rương Minecraft, mỗi trang có 45 ô và hiển thị hành trang bên dưới để xem chỗ trống; không đặt giới hạn số trang. Hành trang ở màn hình này chỉ để xem. Chữ thông báo HUD có nền trong suốt.

- Bấm ô để chuyển tối đa một stack vào hành trang. Không đủ chỗ thì chỉ lấy phần vừa chỗ; phần còn lại ở túi, kể cả chế độ Creative.
- Túi chỉ cho lấy ra, không có thao tác bỏ đồ vào. Rút đồ kiểm tra phía server và gắn với UUID người chơi.
- Túi lưu trong SavedData của world, tách khỏi thực thể người chơi nên không rơi khi chết. World khác có túi riêng. Đồ đã rút ra chịu luật chết/rơi đồ thông thường của world.
- Enchant, hiệu ứng và mob áp dụng trực tiếp; chúng không phải vật phẩm để đưa vào túi.

Piglin hung bạo (`minecraft:piglin_brute`) được triệu hồi bởi quà mới có miễn chuyển hóa thành Piglin thây ma ở Overworld/các chiều không gian khác. Chỉ áp dụng cho mob tạo mới sau khi nạp bản mod này, không thay đổi quái tự nhiên hoặc quái từ các tương tác thường.

Xem [kiểm tra donate liên tục](DONATION_AUDIT.md) để phân biệt mất lệnh khi hàng đợi đầy/ngắt kết nối, mất thông báo HUD và quái bị xóa theo giới hạn mỗi người.

Cài JAR mới từ `release/tiktokmob-1.0.0.jar` bằng nút **Cài/Cập nhật mod**, rồi khởi động lại Minecraft và GUI/bridge. Bản mới cần mod ở cả client và server để đồng bộ HUD/túi; bridge mới bổ sung loại thông báo trong giao thức nên phải cập nhật cùng mod.

Kiểm tra offline: `gradlew.bat build` gồm `verifyGiftBag` (lưu/đọc ItemStack thật, đầy kho, lấy một phần, chống rút lặp, phân trang và cách ly UUID). Test Python và trình duyệt dùng cấu hình tạm, không gửi quà LIVE.
