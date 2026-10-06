# TikTok Mob LIVE - Forge 26.2

## Chỉnh trong Minecraft và đồng bộ GUI

Nhấn **F8** khi đang chơi, hoặc mở **ESC / hành trang → TikTok · Cài đặt**.
Menu có 5 nhóm: Giới hạn, Theo dõi, Bình luận, Chia sẻ và Lượt thích; đủ 24 thông số
về số mob, vòng đời, khoảng sinh, hàng đợi, đếm ngược, mốc tim và thời gian chờ riêng.
Nút **Chọn** mở danh sách mob có tìm theo tên hoặc ID. Màn hình nhỏ có phân trang.
Nhấn **Lưu** để áp dụng; **Nạp lại** bỏ bản nháp và lấy cài đặt mới nhất.

Game và GUI dùng chung `<thư mục Minecraft>/config/tiktokmob.json`.
GUI tự nhận thay đổi khoảng 1,5 giây; game nhận cấu hình ngoài GUI khoảng 1 giây.
Bridge đọc quy tắc tương tác mới trước sự kiện kế tiếp, không cần ngắt LIVE.
Các ô đang sửa được giữ lại; khi lưu chỉ cập nhật trường đã sửa, khóa file khi ghi
để tránh hai phía ghi đè các trường khác. Mob mới dùng vòng đời/khoảng sinh vừa lưu.
Chủ world single-player hoặc OP được lưu cài đặt từ game.

Sau lần cập nhật mã này, mở lại GUI, Minecraft và bridge một lần để nạp bản mới.
Những lần chỉnh các thông số trên sau đó không cần khởi động lại.

## Cập nhật quà TikTok và quà chưa gán

Trong tab **Ghép quà với phần thưởng**, bấm **Cập nhật quà và ảnh TikTok**.
GUI dùng bộ tải ở `tooltt/TikTokGiftDownloader_v2/TikTokGiftDownloader`, lấy catalog
theo tài khoản trong Cài đặt, tải ảnh thật theo Gift ID và hiện tiến độ ngay trong tab.
Quà mới xuất hiện tự động để chọn; các phần thưởng đã gán được giữ nguyên.
Lỗi mạng giữ kho cũ; ảnh thiếu có thể tải lại bằng cùng nút. Công cụ chỉ lấy catalog,
không mở thêm kết nối WebSocket nhận donate. Nếu không lấy được phòng, hãy thử khi tài khoản đang LIVE.

Đã bổ sung 24 quà giá thấp từ 1–30 xu trong `bridge/common_gifts.json`, ghép với
thức ăn, tài nguyên và trang bị Minecraft. Ảnh phần thưởng lấy từ tài nguyên Minecraft;
ảnh TikTok lấy từ URL do catalog trả về. Cấu hình đang dùng được sao lưu trong `bridge/backups`.
Icon khiên dùng ảnh inventory từ [Minecraft Item Gallery](https://github.com/TinyTank800/MinecraftAllImages),
lưu tại `web/assets/minecraft-items` cùng nguồn và giấy phép.

Vào **Cài đặt → Hiệu ứng quà → Quà chưa có trong danh sách đã gán** để chọn:

- **Chỉ cảm ơn** (mặc định): vẫn dùng luồng GIF/giọng cảm ơn đang bật, không phát thưởng.
- **Cảm ơn và tặng phần thưởng mặc định**: chọn vật phẩm, mob hoặc hiệu ứng, số lượng và cấp.

Phần thưởng mặc định chỉ dành cho quà chưa gán, không cộng thêm vào các quà có quy tắc riêng.
Ghép đúng Gift ID; quy tắc cũ chưa có ID dùng tên. Không ghép quà lạ theo giá xu.
Combo chỉ phát thưởng khi kết thúc, số lượng tính theo tổng số quà trong combo.
Mở lại `..\MO_GUI.bat` sau khi cập nhật mã; **Dừng → Chạy LIVE** để nạp quy tắc mới.
Thay đổi này dùng giao thức mod hiện có, không cần build/cài lại JAR.

## VOICEVOX cảm ơn quà và GIF

Mở lại `..\MO_GUI.bat`, vào **VOICEVOX / Cảm ơn quà**. Khi nhận quà, bridge
đọc câu cảm ơn tiếng Nhật bằng VOICEVOX, đồng thời hiện GIF → avatar TikTok →
tên người tặng → số quà → câu cảm ơn theo chiều dọc, không có panel nền đen.
Có 7 câu trong dropdown, chế độ ngẫu nhiên và ô tự nhập tiếng Nhật.
Mẫu mặc định là **THANKIU ONICHANN~~** (`サンキュー、お兄ちゃーん！`).
Chọn nhân vật hoặc nhập ID giọng VOICEVOX trực tiếp trong cùng tab.
GIF mặc định chọn ngẫu nhiên từ mọi file `.gif` trong `web/assets/GIF`;
có thể tắt ngẫu nhiên để dùng file cụ thể. Thêm GIF rồi bấm **Nạp lại GIF**.
Combo được cảm ơn khi kết thúc; quà chưa gán phần thưởng cũng được cảm ơn.
Các lượt được xếp hàng tuần tự. Hàng cảm ơn đầy chỉ bỏ lượt hiển thị mới,
không ảnh hưởng phần thưởng Minecraft.

Giọng comment chọn riêng tại **Cài đặt → Giọng comment** (Adam/ElevenLabs hoặc
giọng tiếng Việt). Các thông số comment đã lưu được giữ lại; cấu hình cũ chọn
VOICEVOX cho comment được chuyển về ElevenLabs. Lời cảm ơn chờ câu đang đọc
kết thúc, không cắt hoặc nói chồng lên comment. Tắt đọc comment vẫn dùng được
VOICEVOX cảm ơn quà. Câu cảm ơn được tổng hợp một lần rồi dùng lại trong phiên.

Tab VOICEVOX có bật/tắt giọng và GIF độc lập, âm lượng riêng, vị trí, kích thước,
thời gian hiển thị và số lượt chờ. Avatar thiếu/lỗi tải sẽ thay bằng chữ đầu tên.
GIF được vẽ trực tiếp trong HUD Minecraft, hoạt động cả toàn màn hình và
Game Capture. Khung xem trước cho phép kéo để chỉnh ngang/dọc (0–100%).
Kích thước phóng cả GIF, avatar và chữ, tính theo khung game rộng 1920px;
Minecraft tự co theo cửa sổ thực tế, không phụ thuộc GUI Scale.
Bridge chờ HUD xác nhận đã hiển thị rồi mới phát giọng. Không có world/mod mới,
hoặc HUD bị tắt bằng F1, test sẽ báo rõ không nhận được xác nhận sau 15 giây.

Bấm **Test VOICEVOX + GIF + tên mẫu** khi LIVE đã dừng để thử, hoặc chạy
`bridge\.venv\Scripts\python.exe -X utf8 bridge\bridge.py --test-gift-alert`
từ thư mục dự án. **Phải mở world Minecraft có mod mới và bật HUD trước khi test.**
Test không gửi phần thưởng hoặc tạo mob. Avatar thật chỉ có
khi nhận sự kiện người tặng; test dùng tên và ảnh đại diện mặc định.
`RUN_BRIDGE.bat` tự cài Pillow khi cần. Đổi cấu hình rồi **Dừng → Chạy LIVE**
để áp dụng. Bản HUD mới cần cài JAR trong `release` và khởi động lại Minecraft
một lần; các lần đổi câu/GIF/vị trí sau đó chỉ cần chạy lại bridge.

Dữ liệu ảnh tạm được tạo tại `%LOCALAPPDATA%/TikTokMobForge/gift-alerts/<id>`.
Minecraft chỉ nhận ID sự kiện, đọc các khung PNG cục bộ rồi giải phóng texture
sau khi hết thời gian. Tính năng dành cho bridge và Minecraft chạy cùng máy.

**Cài đặt** gồm 9 tab con: Kết nối, Mob, Hàng thông báo, Nội dung hiển thị,
Vị trí, Hiệu ứng quà, Giọng comment, Hàng đọc comment và Chống spam.
Chuyển tab giữ nguyên dữ liệu và mọi chỉnh sửa tiếp tục tự lưu sau 1 giây.

## Bảng điều khiển tiếng Việt

Chạy `..\MO_GUI.bat` nằm ngay cạnh thư mục dự án `TikTokMobForge` để mở bảng điều khiển. GUI cho phép:

- chỉnh tài khoản TikTok, ElevenLabs API key, giọng/model/ngôn ngữ, tốc độ, độ ổn định,
  độ giống giọng, phong cách, hàng đợi và khoảng nghỉ giữa hai bình luận;
- chọn mob và số lượng triệu hồi trong 4 khối riêng cho Like, Comment, Share và Follow;
- mỗi khối triệu hồi có ô tìm kiếm riêng theo tiếng Việt, nhóm mob hoặc Minecraft ID;
- tìm kiếm toàn bộ mob bằng tên tiếng Việt, được chia thành Thân thiện, Trung lập và Thù địch;
- chỉnh giới hạn mob, thời gian tồn tại, khoảng cách/vị trí sinh, tốc độ xử lý sự kiện;
- tự đồng bộ danh mục quà đang có trong phòng LIVE và gán quà vào 7 dòng phần thưởng rõ ràng;
- kéo-thả hoặc nhấp đúp để gán năm quà 1 xu, một quà 100 xu và một quà 1000 xu;
- vẫn có ô nâng cao để tìm và đổi sang hiệu ứng, mob, vũ khí hoặc giáp khác;
- chỉnh thời gian hiệu ứng, tim vàng, số mũi tên và cấp hiệu ứng Universe;
- lưu cấu hình, chạy/dừng TikTok LIVE, test giọng, test mob và đọc log ngay trong GUI.

Nút **Lưu toàn bộ** ghi cấu hình bridge vào `bridge/config.json`, API key vào
`bridge/.env` và cấu hình mod vào `<thư mục Minecraft>/config/tiktokmob.json`.
Mod tự nạp lại thông số khoảng mỗi giây. Riêng khi đổi cổng kết nối, hãy khởi động
lại Minecraft và bridge. Log bridge nằm trong `bridge/logs`, log GUI nằm trong
`GUI/logs`, còn log mod có thể lọc trực tiếp từ tab **Nhật ký**.

Tùy chọn **Tiếp tục chạy Minecraft khi chuyển sang cửa sổ GUI** ghi
`pauseOnLostFocus:false` vào `options.txt`. Bộ đếm mob trong mod cũng dùng thời gian
thực, vì vậy sẽ không còn đứng ở 02:57 khi người dùng Alt+Tab sang GUI.

Danh sách quà TikTok thay đổi theo tài khoản, khu vực và từng phòng LIVE nên không
được ghi cứng. Sau khi kết nối LIVE, bridge tải danh mục hiện hành vào
`bridge/discovered_gifts.json`; GUI tự làm mới danh sách khoảng mỗi 2 giây. Trong
tab **Quà tặng**, chọn đúng dòng cùng giá xu rồi kéo quà vào dòng đó (hoặc chọn dòng
và nhấp đúp quà). Mỗi quà chỉ được dùng một lần. Bấm **Lưu toàn bộ** để áp dụng.

Mặc định 7 phần thưởng là:

- 1 xu: 1 tim vàng;
- 1 xu: 1 kiếm sắt;
- 1 xu: 1 cúp sắt;
- 1 xu: trọn bộ giáp sắt;
- 1 xu: 16 mũi tên;
- 100 xu: 64 táo vàng;
- 1000 xu: trọn bộ giáp Netherite.

Bấm **Cài/Cập nhật mod** để chép JAR mới vào thư mục `mods`, rồi khởi động lại Minecraft.

## Đọc comment TikTok bằng giọng AI

Bridge dùng SDK Python chính thức của ElevenLabs để tự đọc comment TikTok. Sao chép
`bridge/.env.example` thành `bridge/.env`, sau đó thay giá trị
`ELEVENLABS_API_KEY` bằng API key ElevenLabs của bạn. Khi chạy
`bridge/START_TIKTOK.bat`, chương trình ưu tiên giọng Adam nếu tài khoản có quyền
sử dụng; nếu không có Adam, chương trình tự chọn một giọng mặc định khả dụng.

Các tùy chọn TTS nằm trong `bridge/config.json`. Đặt `tts_enabled` thành `false`
để tắt đọc comment. API key chỉ nằm trong `bridge/.env` và file này đã được loại
khỏi Git.

Mặc định dự án dùng tài khoản `@_deadchan`, nhưng có thể đổi ngay trong GUI.

- Follow: mặc định tạo Creeper mang tên người follow.
- Đủ số like đã đặt: mặc định tạo Skeleton mang tên người tương tác.
- Comment: mặc định tạo Zombie mang tên người bình luận.
- Share: mặc định tạo Enderman mang tên người chia sẻ.

Loại mob, số mob mỗi lần và mốc like đều có thể đổi trong tab **Triệu hồi**.

## Cài nhanh trên Windows

1. Cài Minecraft Java 26.2, Forge 65.1.3 và JDK 25.
2. Chạy `BUILD_MOD.bat`.
3. Chép `release\tiktokmob-1.0.0.jar` vào `%APPDATA%\.minecraft\mods`.
4. Mở Minecraft bằng profile Forge 26.2 rồi vào một world.
5. Chạy `..\MO_GUI.bat`, chọn đúng thư mục Minecraft rồi bấm **Lưu toàn bộ**.
6. Dùng **Test triệu hồi** để kiểm tra, sau đó bấm **Chạy TikTok LIVE**.

Python 3.10 trở lên là bắt buộc; lần chạy đầu `START_TIKTOK.bat` sẽ tự cài thư viện cần thiết.

Nếu không dùng GUI, vẫn có thể sửa `bridge\config.json` và chạy các file BAT cũ trong
thư mục `bridge`. Cổng `9876` chỉ mở trên máy cục bộ.

TikTokLive là API không chính thức nên có thể cần cập nhật khi TikTok thay đổi hệ thống LIVE.

## Tài liệu và cấu trúc thư mục

Xem [mục lục tài liệu và sơ đồ thư mục](docs/README.md).

