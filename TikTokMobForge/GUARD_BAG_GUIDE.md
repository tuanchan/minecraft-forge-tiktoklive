# Túi chó và golem donate

- Donate chó/chó giáp hoặc iron golem cấp vật phẩm điều khiển cùng icon `summomdog.png` / `sumongoblem.png`. Nếu đã có trong hành trang hoặc túi quà thì không cấp trùng. Hành trang đầy: lấy vật phẩm từ túi quà.
- Cầm vật phẩm, chuột phải để thu hồi nhóm cùng loại do chính người chơi sở hữu; chuột phải lần nữa để gọi lại. Chó và golem có túi riêng. Vật phẩm không chứa quái nên vứt vật phẩm không làm mất dữ liệu quái.
- Thu hồi lưu NBT của từng con trong SavedData của world: tên donate, UUID, máu, giáp và các dữ liệu entity. Thoát world, đổi dimension hoặc chết không xóa túi.
- Gọi lại chỉ lấy con đã thêm thành công vào world ra khỏi túi. Thiếu vị trí an toàn: số còn lại tiếp tục ở trong túi; di chuyển ra nơi rộng rồi bấm lại.
- Thu hồi áp dụng cho quái đang được nạp trong các dimension; không thu hồi quái đang cưỡi/chở entity. Quái chết không được hồi sinh.
- Khi chết, vật phẩm điều khiển được chuyển khỏi danh sách đồ rơi vào túi quà rồi trả vào hành trang khi hồi sinh/đăng nhập. `keepInventory` vẫn giữ vật phẩm theo Minecraft. Phím vứt đồ vẫn hoạt động; donate mới cùng loại cấp lại nếu không còn vật phẩm trong hành trang/túi quà.
- Thu hồi và gọi lại có khói Minecraft và tiếng dịch chuyển. Chuột phải vào không khí, block hoặc entity đều dùng được; có khoảng chờ 10 tick chống bấm lặp.
- Creeper do tool triệu hồi không nhận sát thương/đẩy lùi từ vụ nổ của creeper do tool triệu hồi khác. Sát thương lên người chơi và các loại mob khác giữ cơ chế hiện có.
- Menu GUI dùng hai icon này cho iron golem, wolf và armored_wolf; vật phẩm trong Minecraft cũng dùng hai icon này.

## Kiểm tra

`build_mod.ps1` chạy build và các Java checks. `GuardBagChecks` kiểm tra lưu/đọc NBT, số lượng, dữ liệu tên/máu/giáp, tách chủ sở hữu/loại quái, dữ liệu còn lại sau triệu hồi một phần và serialization vật phẩm.

Các checks này không phải kiểm thử trong world. Cần kiểm tra tương tác thực: donate hai tên khác nhau → gây sát thương cho vệ sĩ → thu hồi → lưu/thoát/vào world → triệu hồi; thử chết với keepInventory tắt/bật, tự vứt item rồi donate mới, thử hai creeper tool cạnh nhau và thử triệu hồi ở nơi chật.

JAR phát hành: `release/tiktokmob-1.0.0.jar`. Cài JAR mới vào instance Minecraft rồi khởi động lại Minecraft để nạp mã và texture mới.
