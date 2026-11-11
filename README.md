# PocketPane

> Bản fork từ [0xCodez/iphone-mirror-windows](https://github.com/0xCodez/iphone-mirror-windows) (GPL-3.0).
> Lộ trình phát triển: [docs/PLAN.md](docs/PLAN.md). Báo cáo các thay đổi trong bản fork: [docs/REPORT.md](docs/REPORT.md).

PocketPane biến máy tính Windows thành thiết bị nhận phản chiếu màn hình AirPlay và hiển thị iPhone của bạn trong một cửa sổ không viền, bo góc theo hình dáng iPhone, có thể nổi trên các ứng dụng khác tương tự tính năng "iPhone Mirroring" trên macOS. Hình ảnh và âm thanh được truyền không dây qua Wi-Fi mà không cần cài đặt thêm ứng dụng nào trên điện thoại. Nếu bạn kết nối iPhone qua cáp USB một lần để thiết lập WebDriverAgent, bạn còn có thể điều khiển điện thoại trực tiếp từ PC bằng chuột và bàn phím.

## Tính năng

- **Phản chiếu AirPlay không dây kèm âm thanh.** iPhone nhận diện PC như một thiết bị nhận AirPlay trong *Control Center > Screen Mirroring* (Trung tâm điều khiển > Phản chiếu màn hình). Không cần cài app trên điện thoại, không cần cáp.
- **Cửa sổ mang hình dáng iPhone.** Không viền, bo góc, tùy chọn luôn nổi trên cùng (Ghim / Pin), thay đổi kích thước linh hoạt và tự ghi nhớ vị trí cũ.
- **Tự động xoay màn hình.** Khi xoay ngang iPhone, cửa sổ trên PC cũng tự động xoay theo.
- **Chụp ảnh màn hình.** Lưu khung hình hiện tại thành file PNG (`Ctrl+S`) hoặc chép thẳng vào clipboard (`Ctrl+Shift+S`).
- **Quay màn hình.** Ghi lại cả hình ảnh lẫn âm thanh của iPhone ra file MP4 (`Ctrl+R`).
- **Toàn màn hình** (`F11`), **độ trong suốt cửa sổ**, **tùy chỉnh chất lượng luồng phát** (720p / 1080p / 1440p, 30 / 60 fps) và **bảng thông số trực tiếp** (`Ctrl+I`: độ phân giải, fps, bitrate).
- **Chạy nền gọn nhẹ.** Khởi động cùng Windows dưới khay hệ thống (cửa sổ tự hiện khi có iPhone kết nối), giữ PC không ngủ trong lúc phản chiếu, hoặc tạm ẩn PC khỏi danh sách Screen Mirroring.
- **Điều khiển bằng chuột và bàn phím qua USB (tùy chọn).** Chạm, nhấn giữ, vuốt, cuộn, gõ chữ (hỗ trợ tiếng Việt), nút Home, trình đa nhiệm (App Switcher) và tăng giảm âm lượng thông qua [WebDriverAgent](https://github.com/appium/WebDriverAgent).

## Yêu cầu hệ thống

- Windows 10 hoặc Windows 11
- [Python](https://www.python.org/downloads/) 3.11 trở lên (không bắt buộc: nếu máy chưa có, `install.bat` sẽ tự tải một bản riêng như mô tả bên dưới)
- iPhone và PC kết nối chung một mạng Wi-Fi

Nếu muốn dùng thêm tính năng điều khiển qua USB, bạn cần:

- Cáp USB kết nối iPhone với PC
- **Apple Devices** từ Microsoft Store hoặc **iTunes tải từ [apple.com](https://www.apple.com/itunes/)** (để cài dịch vụ driver USB của Apple; lưu ý Sideloadly yêu cầu bản iTunes từ `apple.com` thay vì bản Microsoft Store, và bản `apple.com` cũng dùng được cho các bản Windows cũ không cài được Apple Devices)
- Một tài khoản Apple ID (tài khoản miễn phí là đủ)

## Cài đặt

1. Tải mã nguồn về máy (**Code > Download ZIP**, hoặc `git clone`) và đặt vào một thư mục cố định, ví dụ `C:\Apps\pocketpane`.
2. Nhấp đúp vào **`install.bat`**.

`install.bat` sẽ tự động thực hiện:

- Tìm Python 3.11+ có sẵn (`python`, sau đó `py -3`; alias "python" giả của Microsoft Store sẽ tự động bị bỏ qua). Nếu máy chưa có, script sẽ tải gói Python 3.12 chính thức từ `nuget.org` (khoảng 15 MB), kiểm tra mã băm SHA-256 và giải nén vào `%LOCALAPPDATA%\PocketPane\python` mà không can thiệp vào hệ thống hay biến môi trường `PATH`.
- Tạo môi trường ảo (virtual environment) riêng tại `%LOCALAPPDATA%\PocketPane\venv`.
- Cài đặt các thư viện cần thiết từ `requirements.txt` vào môi trường ảo đó.
- Tạo shortcut **PocketPane** ngoài Desktop và trong Start Menu. Shortcut này chạy `pythonw -m iphone_mirror` từ thư mục mã nguồn nên sẽ không mở kèm cửa sổ dòng lệnh (console).

Toàn bộ quá trình cài đặt đều hỗ trợ đường dẫn có dấu tiếng Việt (ví dụ tên người dùng Windows có dấu): shortcut được tạo qua giao diện Unicode `IShellLinkW` (`tools\shortcuts.ps1`) và việc tải Python được xử lý bởi `tools\get_python.ps1`.

Nếu sau này bạn di chuyển thư mục sang nơi khác, chỉ cần chạy lại `install.bat` để cập nhật lại đường dẫn shortcut. Ngoài ra, bạn có thể chạy `run.bat` để mở ứng dụng trực tiếp không qua shortcut, và dùng `control.bat` cho công cụ hỗ trợ điều khiển USB (xem bên dưới).

## Cách sử dụng

1. Mở **PocketPane**. Một cửa sổ hình chiếc iPhone sẽ hiện ra với dòng chữ **"Waiting for iPhone"**. Dưới chân cửa sổ hiển thị địa chỉ IP của máy tính: `PC: <ips>  -  iPhone and PC must be on the same Wi-Fi`.
2. **Chỉ trong lần chạy đầu tiên:** Tường lửa Windows Defender sẽ hỏi quyền truy cập mạng cho Python. Hãy tích chọn **Private networks** rồi bấm **Allow**.
3. Đảm bảo mạng Wi-Fi trên Windows đang đặt ở chế độ **Private** (Mạng riêng): vào *Settings > Network & internet > Wi-Fi > tên mạng Wi-Fi > Network profile type > **Private***.
4. Trên iPhone, mở **Control Center > Screen Mirroring** (Trung tâm điều khiển > Phản chiếu màn hình) và chọn tên máy tính này (mặc định là tên máy; bạn có thể đổi bằng cách nhấp chuột phải > **Rename PC...**).
5. Cửa sổ sẽ hiện **"Connecting..."**, sau đó hiển thị màn hình iPhone.

Tại mỗi thời điểm chỉ có một phiên bản ứng dụng chạy: nếu bạn mở ứng dụng lần nữa, cửa sổ đang chạy sẽ được đưa lên phía trước.

## Thao tác trên cửa sổ

Di chuột vào cửa sổ để hiện **thanh công cụ phía trên**. Từ trái sang phải bao gồm:

- Nhãn hiển thị tên thiết bị, tốc độ khung hình (FPS) và trạng thái điều khiển,
- **Control** (biểu tượng bàn tay): bật hoặc tắt điều khiển USB. Màu trắng khi tắt, nhấp nháy cam khi đang khởi động, màu xanh lá khi sẵn sàng, và màu đỏ nếu gặp lỗi,
- **Home** (hình tròn),
- **Pin**: ghim cửa sổ luôn nổi trên cùng,
- **Minimize**: thu nhỏ cửa sổ,
- **Close**: đóng ứng dụng.

### Chỉ phản chiếu màn hình (tắt điều khiển – mặc định)

| Thao tác | Tác dụng |
|---|---|
| Kéo chuột trái ở bất kỳ đâu | Di chuyển cửa sổ |
| Nhấp đúp chuột (Double-click) | Chuyển đổi giữa kích thước lớn và bình thường (thoát toàn màn hình nếu đang bật) |
| `Ctrl` + con lăn chuột | Thay đổi kích thước cửa sổ |
| `Ctrl + Plus` / `Ctrl + Minus` | Thay đổi kích thước cửa sổ |
| Nhấp chuột phải | Mở menu tùy chọn |

### Khi bật điều khiển

Các thao tác dưới đây có hiệu lực khi điều khiển đã **sẵn sàng** (nút Control màu xanh lá) và màn hình iPhone đang hiển thị. Khi cửa sổ đang ở màn hình chờ, kéo chuột vẫn dùng để di chuyển cửa sổ.

| Thao tác trên vùng màn hình điện thoại | Phản hồi trên iPhone |
|---|---|
| Nhấp chuột (Click) | Chạm (Tap). Lệnh được gửi sau khoảng 0,2 giây để phân biệt với thao tác nhấp đúp |
| Nhấn giữ từ 0,5 giây trở lên mà không di chuột | Nhấn giữ (Long press) |
| Kéo chuột (Drag) | Vuốt (Swipe). Lệnh được gửi khi nhả chuột với thời lượng tương ứng thời gian kéo (giới hạn từ 0,06 – 1,5 giây) |
| Nhấp đúp chuột (Double-click) | Chạm đúp (Double tap – hai lần chạm được gửi cùng lúc để ứng dụng nhận diện đúng cử chỉ) |
| Con lăn chuột | Cuộn trang (Scroll). Các nấc lăn trong khoảng 120 ms được gộp thành một lần cuộn mượt |
| Gõ bàn phím | Nhập văn bản. Ký tự được đệm trong khoảng 80 ms; hỗ trợ `Backspace` và `Enter`. Tương thích tốt với các bộ gõ tiếng Việt (Unikey, Microsoft Vietnamese Telex) cũng như bộ gõ Trung/Nhật (IME) |
| Nhấp chuột giữa | Nút Home |
| Nút Back bên hông chuột | Quay lại (vuốt từ mép trái màn hình) |
| Kéo thanh công cụ trên cùng, hoặc `Alt` + kéo ở bất kỳ đâu | Di chuyển cửa sổ |
| `Ctrl` + con lăn chuột | Thay đổi kích thước cửa sổ |

Mỗi cú chạm hoặc nhấn giữ sẽ hiển thị hiệu ứng vòng tròn lan tỏa mờ dần tại điểm chạm; thao tác vuốt sẽ hiển thị đường kẻ mờ dần từ điểm đầu tới điểm cuối.

### Phím tắt (dùng cho cả hai chế độ)

| Phím tắt | Tác dụng |
|---|---|
| `Ctrl + H` | Màn hình chính (Home) |
| `Ctrl + J` | Trình chuyển đổi ứng dụng (App Switcher) |
| `Ctrl + B` | Quay lại (vuốt từ mép trái) |
| `Ctrl + K` | Tìm kiếm Spotlight |
| `Ctrl + N` | Trung tâm thông báo (Notification Center) |
| `Ctrl + Shift + N` | Trung tâm điều khiển (Control Center) |
| `Ctrl + L` | Khóa màn hình iPhone |
| `Ctrl + V` | Nhập văn bản từ clipboard của PC vào ô đang chọn trên iPhone (tối đa 2000 ký tự) |
| `Ctrl + Up` / `Ctrl + Down` | Tăng / giảm âm lượng iPhone |
| `Ctrl + M` | Tắt / bật tiếng phát trên PC |
| `Ctrl + U` | Bật / tắt điều khiển qua USB |
| `Ctrl + S` | Lưu ảnh chụp màn hình (độ phân giải gốc của iPhone) |
| `Ctrl + Shift + S` | Sao chép ảnh chụp màn hình vào clipboard |
| `Ctrl + R` | Bắt đầu / dừng quay màn hình ra file MP4 |
| `Ctrl + I` | Hiện / ẩn bảng thông số luồng phát |
| `F11` (`Esc` để thoát) | Chế độ toàn màn hình |
| `Ctrl + Plus` / `Ctrl + Minus` | Thay đổi kích thước cửa sổ |

Các thao tác *Home, App Switcher, Back, Spotlight, Notification Center, Control Center, Lock, Paste* và *âm lượng iPhone* tác động trực tiếp lên điện thoại nên chỉ hoạt động khi điều khiển USB đã sẵn sàng. Với *App Switcher*, ứng dụng sẽ vuốt từ cạnh dưới lên và giữ đối với iPhone dùng Face ID, hoặc nhấn đúp nút Home đối với iPhone có nút Home vật lý.

Tổ hợp `Ctrl` + con lăn chuột phóng to/thu nhỏ theo tỷ lệ quãng lăn (khoảng 6% mỗi khấc), nên thao tác cuộn mượt trên touchpad cũng thay đổi kích thước cửa sổ rất mượt.

### Menu chuột phải

| Mục menu | Tác dụng |
|---|---|
| `Control iPhone (USB)` | Bật hoặc tắt điều khiển iPhone (dạng đánh dấu chọn) |
| `Set Up iPhone Control...` | Mở cửa sổ hướng dẫn và kiểm tra từng bước thiết lập điều khiển USB (xem bên dưới) |
| `Home`, `App Switcher`, `Back`, `Spotlight`, `Notification Center`, `Control Center`, `Lock Screen` | Gửi thao tác tương ứng sang iPhone (khi đang bật điều khiển) |
| `Volume Up` / `Volume Down` | Tăng / giảm âm lượng iPhone |
| `Paste PC Clipboard` | Nhập nội dung clipboard trên PC sang iPhone |
| `Always on Top` | Giữ cửa sổ luôn nổi trên các cửa sổ khác |
| `Sound` | Phát âm thanh từ iPhone ra loa PC |
| `Full Screen` | Chế độ toàn màn hình (`F11`) |
| `Size` | Chọn kích thước cửa sổ: Small (Nhỏ), Medium (Vừa) hoặc Large (Lớn) |
| `Stream Quality` | Chọn chất lượng 720p / 1080p / 1440p và 30 / 60 fps; có hiệu lực từ lần kết nối tiếp theo |
| `Show Stream Info` | Hiển thị độ phân giải, fps, bitrate, số khung hình đã giải mã và bị rớt |
| `Opacity` | Độ trong suốt của cửa sổ: 100%, 90%, 75% hoặc 50% |
| `Keep PC Awake While Mirroring` | Ngăn Windows tự ngủ khi đang nhận hình (mặc định bật) |
| `Start with Windows` | Khởi động ẩn dưới khay hệ thống khi đăng nhập Windows; tự hiện cửa sổ khi iPhone kết nối |
| `Save Screenshot` / `Copy Screenshot` | Lưu ảnh vào `Pictures\PocketPane` / sao chép vào clipboard |
| `Record Screen` | Quay video kèm âm thanh vào `Videos\PocketPane` (định dạng MP4) |
| `Rename PC...` | Đổi tên máy tính hiển thị trong mục Screen Mirroring trên iPhone |
| `Visible in Screen Mirroring` | Bỏ chọn để ẩn PC khỏi các thiết bị iPhone (phiên đang kết nối vẫn tiếp tục chạy) |
| `Open Media Folder` | Mở thư mục chứa ảnh chụp hoặc video vừa quay |
| `Open Log` | Mở file nhật ký `%LOCALAPPDATA%\PocketPane\pocketpane.log` |
| `Quit` | Thoát ứng dụng |

Nếu bộ điều khiển gặp lỗi, ứng dụng sẽ hiển thị hộp thoại thông báo không chặn giao diện mang tiêu đề **"iPhone control"** kèm nội dung chi tiết, đồng thời cập nhật trạng thái trên thanh công cụ phía trên.

## Điều khiển qua USB (tùy chọn)

Giao thức AirPlay chỉ truyền hình ảnh và âm thanh. Để gửi thao tác chạm và phím bấm ngược về điện thoại, PocketPane giao tiếp với [WebDriverAgent](https://github.com/appium/WebDriverAgent) (WDA) — máy chủ tự động hóa mã nguồn mở của Appium xây dựng trên XCUITest của Apple, chạy như một ứng dụng nhỏ trên iPhone. PocketPane khởi chạy WDA qua cáp USB bằng [pymobiledevice3](https://github.com/doronz88/pymobiledevice3). Bạn không cần máy Mac, và với iOS 17.4 trở lên (cũng như iOS 16 trở xuống) cũng không cần quyền Quản trị viên (Administrator). Riêng iOS 17.0 – 17.3 bắt buộc phải có quyền Administrator: hãy cập nhật iOS, hoặc chạy `pymobiledevice3 remote tunneld` dưới quyền Administrator trước khi bật điều khiển.

**Cách thiết lập nhanh nhất:** nhấp chuột phải vào cửa sổ > **Set Up iPhone Control...** (hoặc bấm nút **Setup Guide** khi bật điều khiển báo lỗi). Cửa sổ này hiển thị danh sách từng bước dưới đây kèm đèn trạng thái xanh, cam hoặc đỏ và thông tin chi tiết, tự động kiểm tra lại sau mỗi vài giây trong lúc bạn thao tác trên điện thoại, đồng thời cung cấp sẵn các nút bấm hỗ trợ: *Get Apple Devices*, *Get iTunes* (cho Windows bản cũ), *Show Developer Mode*, *Download WebDriverAgent* (mở sẵn file `.ipa` trong Explorer), *Open Sideloadly* và cuối cùng là *Turn on control*. Công cụ cũng tự đọc ngày hết hạn chữ ký của WebDriverAgent (Apple ID miễn phí có hạn 7 ngày); nếu bật điều khiển khi còn dưới 2 ngày là hết hạn, ứng dụng sẽ hiện thông báo nhắc bạn cài lại.

Nếu muốn thao tác thủ công bằng dòng lệnh, hãy mở Terminal (Command Prompt hoặc PowerShell) tại thư mục mã nguồn. File `control.bat` chạy trực tiếp bằng môi trường Python riêng của ứng dụng nên không cần kích hoạt thủ công (tương đương lệnh `python -m iphone_mirror.control ...` bên trong môi trường đó):

1. **Kết nối iPhone.** Cài đặt **iTunes từ apple.com** (hoặc Apple Devices), cắm cáp kết nối iPhone với PC, mở khóa điện thoại và nhấn **Trust** (Tin cậy) khi được hỏi.
2. **Bật Chế độ nhà phát triển (Developer Mode).** Chạy lệnh:

   ```bat
   control.bat reveal-dev-mode
   ```

   Lệnh này làm hiện tùy chọn Developer Mode trong phần Cài đặt của iPhone (tùy chọn này cũng tự xuất hiện sau khi cài WebDriverAgent ở bước 4). Trên iPhone, vào *Settings > Privacy & Security > **Developer Mode*** (Cài đặt > Quyền riêng tư & Bảo mật > Chế độ nhà phát triển), gạt bật và xác nhận. Điện thoại sẽ khởi động lại; sau khi mở khóa, hãy xác nhận **Turn On** thêm một lần nữa.
3. **Tải WebDriverAgent.** Chạy lệnh:

   ```bat
   control.bat get-wda
   ```

   Lệnh sẽ tải bản WebDriverAgent dựng sẵn của Appium và lưu thành `WebDriverAgentRunner.ipa` trong thư mục `Downloads` của bạn.
4. **Cài đặt lên iPhone.** Mở [Sideloadly](https://sideloadly.io), chọn iPhone của bạn và file `WebDriverAgentRunner.ipa`, nhập Apple ID rồi nhấn Start. Sideloadly sẽ ký ứng dụng bằng Apple ID của bạn và cài vào máy. Với Apple ID **miễn phí**, chữ ký có hiệu lực trong **7 ngày**: hết hạn này bạn chỉ cần cài đè lại qua Sideloadly (tài khoản Apple Developer trả phí có hạn 1 năm).
5. **Tin cậy hồ sơ nhà phát triển.** Trên iPhone, vào *Settings > General > **VPN & Device Management*** (Cài đặt > Cài đặt chung > Quản lý VPN & thiết bị), chạm vào Apple ID của bạn dưới mục "Developer App" rồi chọn **Trust** (Tin cậy).
6. **Kiểm tra tổng thể.** Chạy lệnh:

   ```bat
   control.bat doctor
   ```

   và xử lý các mục còn báo lỗi cho đến khi tất cả đều đạt.
7. **Bật điều khiển.** Trong cửa sổ PocketPane, nhấn **Ctrl + U**, bấm vào biểu tượng bàn tay trên thanh công cụ, hoặc nhấp chuột phải > **Control iPhone (USB)**. Nút bấm sẽ nhấp nháy màu cam trong lúc khởi động WDA (lần đầu tiên sẽ tải và gắn thêm Developer Disk Image nên có thể mất khoảng một phút) và chuyển sang màu xanh lá khi sẵn sàng.

WebDriverAgent lắng nghe trên cổng `8100` của iPhone, có thể truy cập được qua cả Wi-Fi lẫn đường truyền chuyển tiếp USB (USB forward). Khi bạn bật điều khiển, ứng dụng sẽ ưu tiên tìm phiên WDA đang chạy sẵn (qua cả USB forward lẫn địa chỉ Wi-Fi của iPhone), và chỉ khởi chạy phiên mới qua USB nếu chưa có. Nhờ vậy, khi WDA đã chạy, dữ liệu điều khiển có thể đi qua Wi-Fi. Tuy nhiên bạn vẫn nên giữ cáp cắm trong quá trình sử dụng, vì vòng đời của WDA gắn liền với phiên XCUITest đã khởi chạy nó — rút cáp thường sẽ làm kết thúc phiên này.

### Các lệnh hỗ trợ

Cú pháp: `control.bat LỆNH` (hoặc `python -m iphone_mirror.control LỆNH`; thêm `--help` sau bất kỳ lệnh nào để xem chi tiết tùy chọn):

| Lệnh | Chức năng |
|---|---|
| `doctor` | Kiểm tra toàn bộ điều kiện cần thiết cho điều khiển USB, bao gồm thời hạn chữ ký WebDriverAgent (thêm `--ip ĐỊA_CHỈ` để kiểm tra cả kết nối WDA qua Wi-Fi) |
| `reveal-dev-mode` | Làm xuất hiện mục bật Developer Mode trong Cài đặt của iPhone |
| `get-wda` | Tải WebDriverAgent về dưới tên `WebDriverAgentRunner.ipa` (dùng `--out ĐƯỜNG_DẪN` nếu muốn lưu ở nơi khác) |
| `start` | Khởi chạy WebDriverAgent qua USB độc lập (không cần mở giao diện chính) và giữ chạy cho tới khi nhấn `Ctrl+C` |
| `tap X Y` | Chạm vào tọa độ `X, Y` (đơn vị point) trên phiên WDA đang chạy |
| `home` | Trở về màn hình chính (Home Screen) |
| `type TEXT` | Gõ chuỗi `TEXT` vào ô nhập liệu đang chọn (`\n` = Enter, `\b` = Backspace) |

Các lệnh `tap`, `home` và `type` mặc định gửi tới `http://127.0.0.1:8100` trừ khi bạn chỉ định `--url`.

## Xử lý sự cố

**Không thấy tên PC trong mục Screen Mirroring trên iPhone**

- Mạng Wi-Fi trên Windows phải được đặt ở chế độ **Private** (xem mục [Cách sử dụng](#cách-sử-dụng)).
- Python phải được phép đi qua tường lửa trên mạng Private: mở Start > gõ *"Allow an app through Windows Firewall"* > tìm `pythonw.exe` / `python.exe` và tích chọn cột **Private**.
- iPhone và PC phải nằm cùng mạng và cùng dải subnet. Mạng Wi-Fi khách (Guest) hoặc router bật tính năng "Client Isolation" / "AP Isolation" sẽ chặn các thiết bị nhìn thấy nhau. Bật VPN trên một trong hai thiết bị cũng có thể gây hiện tượng tương tự.
- Hãy thử khởi động lại ứng dụng để phát lại bản tin quảng bá mDNS.

**Thông báo lỗi "Could not decrypt the video"**

Tắt phản chiếu màn hình trên iPhone rồi kết nối lại. Nếu lỗi vẫn lặp lại, hãy mở file log (nhấp chuột phải > **Open Log**) và đính kèm khi gửi báo lỗi (issue).

**Thông báo "iPhone is locked"**

Chỉ cần mở khóa iPhone, hình ảnh phản chiếu sẽ tự động tiếp tục.

**Không có âm thanh**

Kiểm tra xem mục **Sound** trong menu chuột phải đã được tích chọn chưa (hoặc nhấn `Ctrl + M`), đồng thời kiểm tra thiết bị đầu ra âm thanh của Windows. Nút âm lượng trên thân máy iPhone cũng điều chỉnh trực tiếp mức âm lượng phát ra.

**Không bật được điều khiển hoặc điều khiển ngừng hoạt động**

- Chạy lệnh `control.bat doctor` (hoặc mở **Set Up iPhone Control...**, xem mục [Điều khiển qua USB](#điều-khiển-qua-usb-tùy-chọn)) và khắc phục theo hướng dẫn. Hộp thoại lỗi "iPhone control" cũng hiển thị thông báo tương tự.
- Chữ ký bằng Apple ID miễn phí sẽ hết hạn sau 7 ngày: nếu WDA đột ngột không thể khởi chạy, hãy cài đặt lại `WebDriverAgentRunner.ipa` bằng Sideloadly.
- Nếu điện thoại báo "Untrusted Developer" (Nhà phát triển chưa được tin cậy): hãy vào *Settings > General > VPN & Device Management* để bấm **Trust**.
- Các file nhật ký nằm tại `%LOCALAPPDATA%\PocketPane\*.log`: gồm `pocketpane.log` cho ứng dụng chính và `wda_runner.log` / `wda_forward.log` cho các tiến trình WebDriverAgent.

## Giới hạn

- **Không phản chiếu được nội dung có bảo vệ bản quyền (DRM).** Các ứng dụng sử dụng DRM (như Netflix, Apple TV,...) sẽ hiển thị màn hình đen. Đây là cơ chế chặn từ phía iPhone chứ không phải do phần mềm nhận.
- **Độ phân giải.** Mặc định ứng dụng yêu cầu luồng hình cao 1080 pixel từ iPhone. Để thử hình ảnh sắc nét hơn, bạn có thể chọn trong menu *Stream Quality* hoặc thoát ứng dụng, đặt `"height": 1440` trong `%LOCALAPPDATA%\PocketPane\settings.json` rồi mở lại. Nếu iPhone không kết nối được ở mức này, hãy đưa về lại `1080`.
- **Độ trễ điều khiển.** Mỗi thao tác điều khiển là một truy vấn HTTP gửi tới WebDriverAgent nên sẽ có độ trễ khoảng 100–200 ms trước khi iPhone phản hồi. Cú nhấp chuột đơn cũng chờ thêm khoảng 0,2 giây để phân biệt với nhấp đúp.
- **Không hỗ trợ kéo theo thời gian thực (live drag).** Cử chỉ vuốt chỉ được gửi đi sau khi bạn nhả nút chuột, do đó bạn không thể vừa kéo một biểu tượng vừa nhìn nó di chuyển theo con trỏ chuột, hoặc dùng để vẽ tay trực tiếp.
- **Điều khiển cần bước thiết lập ban đầu.** Yêu cầu cắm cáp USB, bật Developer Mode và cài đặt WDA qua Sideloadly (cần ký lại mỗi 7 ngày nếu dùng Apple ID miễn phí).

## Quay màn hình

Nhấn `Ctrl+R` (hoặc nhấp chuột phải > **Record Screen**) để ghi lại màn hình đang phản chiếu cùng âm thanh vào `Videos\PocketPane\iPhone <ngày> <giờ>.mp4`. Thanh công cụ phía trên sẽ hiện `REC m:ss`, và khi thanh công cụ ẩn đi vẫn có một chấm đỏ nhỏ ở góc cửa sổ. Nhấn `Ctrl+R` lần nữa để hoàn tất file quay; một thông báo sẽ cho biết đường dẫn lưu file (bấm vào thông báo để mở thư mục). Tham số `--record` cho phép tự động quay ngay khi mở ứng dụng.

Do iOS chỉ gửi khung hình khóa (keyframe) đầy đủ lúc mới bắt đầu phản chiếu, bộ ghi hình sẽ mã hóa lại các khung hình đã giải mã (chuẩn H.264, `libx264` chế độ `"ultrafast"`, tối đa 30 fps) thay vì chép nguyên luồng gốc. Nếu cấu hình PC không theo kịp, một số khung hình ghi sẽ được bỏ qua để không làm trễ hình ảnh phản chiếu trực tiếp. Khi xoay ngang/dọc iPhone, file hiện tại sẽ được đóng lại an toàn và ứng dụng tự tách sang phần mới `... (2).mp4` vì một luồng video MP4 không thể đổi kích thước khung hình giữa chừng.

## Thiết lập

File cấu hình `%LOCALAPPDATA%\PocketPane\settings.json` được tạo tự động trong lần chạy đầu tiên. Các khóa cấu hình hữu ích:

| Khóa | Mặc định | Ý nghĩa |
|---|---|---|
| `name` | tên máy tính | Tên hiển thị trên iPhone trong danh sách Screen Mirroring |
| `width`, `height` | `1920`, `1080` | Kích thước luồng video yêu cầu từ iPhone (`height` quyết định độ phân giải) |
| `fps` | `60` | Tốc độ khung hình yêu cầu từ iPhone |
| `audio` | `true` | Phát âm thanh của iPhone trên PC |
| `always_on_top` | `false` | Giữ cửa sổ luôn nổi trên các cửa sổ khác |
| `opacity` | `1.0` | Độ trong suốt của cửa sổ (`0.3` – `1.0`) |
| `keep_awake` | `true` | Giữ PC không tự ngủ trong khi đang phản chiếu |

File này cũng lưu vị trí cửa sổ và danh tính của thiết bị nhận (địa chỉ MAC ngẫu nhiên cùng khóa Ed25519). Xóa file này sẽ đặt lại toàn bộ cài đặt về mặc định và iPhone sẽ coi PC như một thiết bị nhận mới. Trong lần khởi chạy đầu tiên, nếu tìm thấy cài đặt cũ của ứng dụng gốc "iPhone Mirror" (`%LOCALAPPDATA%\iPhoneMirror\settings.json`), PocketPane sẽ tự động sao chép sang để iPhone vẫn nhận diện quen thuộc như cũ.

## Cơ chế hoạt động

- **Quảng bá dịch vụ (Discovery).** Ứng dụng quảng bá dịch vụ `_airplay._tcp` và `_raop._tcp` qua giao thức mDNS (`python-zeroconf`) kèm các bản ghi TXT mô phỏng Apple TV, giúp iPhone hiển thị PC trong mục Screen Mirroring.
- **Kết nối điều khiển phiên.** Máy chủ RTSP bất đồng bộ (`asyncio`) trên cổng TCP `7000` xử lý `GET /info`, sau đó thực hiện ghép đôi AirPlay (`pair-setup` và `pair-verify`) bằng chữ ký số Ed25519 và trao đổi khóa X25519.
- **FairPlay.** Quá trình `fp-setup` thực hiện bắt tay FairPlay SAP. Một bản chuyển đổi thuần Python từ mã nguồn mở *playfair* sẽ giải bọc khóa phiên AES 16-byte được iPhone mã hóa FairPlay gửi sang trong bước `SETUP`.
- **Video.** Luồng hình ảnh phản chiếu là H.264 truyền qua TCP, mã hóa bằng AES-128-CTR với khóa dẫn xuất từ khóa FairPlay và khóa chung `pair-verify`. PyAV (FFmpeg) giải mã ở luồng nền và co giãn khung hình khớp chính xác với kích thước điểm ảnh thực của cửa sổ.
- **Âm thanh.** Chuẩn AAC-ELD truyền qua RTP/UDP, mã hóa AES-CBC, được giải mã bằng PyAV và phát ra loa qua thư viện `sounddevice`.
- **Giao diện cửa sổ.** PySide6 (Qt) vẽ cửa sổ không viền, nền trong suốt, bo góc tròn cùng khung máy, màn hình chờ và thanh nút bấm điều khiển.
- **Điều khiển USB.** `pymobiledevice3` tìm iPhone qua `usbmux`, kiểm tra Developer Mode, gắn Developer Disk Image, khởi chạy WebDriverAgent dưới dạng bài kiểm thử XCUITest (trên iOS 17+ đi qua userspace tunnel) và chuyển tiếp một cổng nội bộ trên PC vào cổng `8100` của WDA. Thao tác chuột và bàn phím được chuyển thành các lời gọi HTTP tới WDA (chạm, vuốt, nhập chữ, bấm nút cứng).

## Phát triển

Sử dụng môi trường ảo của ứng dụng (`%LOCALAPPDATA%\PocketPane\venv\Scripts\python.exe`) hoặc bất kỳ bản Python 3.11+ nào đã cài `requirements.txt`, và chạy các lệnh từ thư mục gốc của kho mã nguồn:

```bat
rem Chạy bộ kiểm thử FairPlay (đối chiếu với 21 phiên ghi mẫu)
python tests/test_fairplay.py

rem Kiểm thử client WebDriverAgent
python tests/test_wda.py

rem Mô phỏng toàn bộ phiên AirPlay mà không cần iPhone thật hay mạng Wi-Fi:
rem thiết bị nhận chỉ lắng nghe trên 127.0.0.1:7100 và không phát mDNS
python -m iphone_mirror --local
rem Mở cửa sổ dòng lệnh thứ hai: chạy iPhone giả lập thực hiện ghép đôi, FairPlay
rem rồi truyền luồng video H.264 mã hóa cùng âm báo AAC (tham số: host port số_giây)
python tools/fake_iphone.py 127.0.0.1 7100
```

Cờ `--local` cũng bỏ qua kiểm tra chạy đơn phiên (single-instance) và dùng file cấu hình tách biệt, nhờ đó có thể chạy song song với ứng dụng PocketPane bình thường. Các tùy chọn dòng lệnh khác:

| Tùy chọn | Ý nghĩa |
|---|---|
| `--port N` | Cổng RTSP (mặc định `7000`, hoặc `7100` khi dùng `--local`) |
| `--control` | Tự động bật điều khiển iPhone (USB / WebDriverAgent) ngay khi mở |
| `--record` | Tự động quay màn hình lưu vào `Videos\PocketPane` ngay khi mở |
| `--tray` | Khởi động ẩn dưới khay hệ thống; chỉ hiện cửa sổ khi có iPhone kết nối |
| `--grab DIR` | Lưu ảnh chụp PNG của cửa sổ mỗi 2 giây vào thư mục `DIR` |
| `--quit-after N` | Tự động thoát sau `N` giây |

### Khóa bản quyền

Ứng dụng yêu cầu nhập khóa kích hoạt (license key) trong lần mở đầu tiên và lưu vào `settings.json` (chế độ `--local` không yêu cầu khóa). Để tạo khóa mới, chạy lệnh:

```bat
.venv\Scripts\python tools\make_key.py "Tên người dùng" --days 365
```

(tham số `--days` là tùy chọn; nếu bỏ qua, khóa sẽ có hiệu lực vĩnh viễn). Khóa được ký bằng khóa bí mật lưu tại `%USERPROFILE%\.pocketpane\signing.key`; ứng dụng chỉ chứa khóa công khai tương ứng (`PUBLIC_KEY` trong `iphone_mirror/license.py`). Hãy sao lưu file khóa bí mật này cẩn thận và không đưa vào kho mã nguồn. Khóa bản quyền không khóa cứng theo từng máy PC, và vì mã nguồn mở nên người nắm mã nguồn có thể gỡ bỏ bước kiểm tra này nếu muốn.

### Đóng gói bản chạy độc lập

Script `build.bat` đóng gói ứng dụng bằng [PyInstaller](https://pyinstaller.org) vào thư mục `dist\PocketPane` để chạy trực tiếp trên các máy tính không cài Python:

- `PocketPane.exe`: ứng dụng chính (không hiện cửa sổ console),
- `pocketpane-control.exe`: công cụ dòng lệnh hỗ trợ điều khiển (cú pháp giống hệt `control.bat`); ứng dụng chính cũng gọi file này để chạy `pymobiledevice3`,
- `_internal\`: chứa Python runtime và các thư viện đi kèm.

Quá trình build yêu cầu có sẵn Python 3.11+ trong `PATH` và sẽ tự tạo môi trường riêng tại `.venv`. Sau khi đóng gói xong, script tự động kiểm tra sự hiện diện của plugin nền tảng Qt cũng như mọi lệnh con `pymobiledevice3` mà ứng dụng sử dụng. Bản build hiện chưa được ký số (code signing) và chưa kèm bộ cài đặt riêng.

Công cụ `tools/gen_fairplay.py` dùng để sinh lại hai file `iphone_mirror/fairplay/_tables.py` và `_garble.py` từ mã nguồn C *playfair* đi kèm trong UxPlay:

```bat
python tools/gen_fairplay.py duong\dan\toi\UxPlay\lib
```

### Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| `iphone_mirror/airplay.py` | Máy chủ RTSP, thiết lập phiên kết nối, lớp `Receiver` |
| `iphone_mirror/pairing.py` | Ghép đôi AirPlay (`pair-setup` / `pair-verify`) |
| `iphone_mirror/fairplay/` | Giao thức FairPlay SAP thuần Python (chuyển từ *playfair*) |
| `iphone_mirror/video.py` | Giải mã luồng phản chiếu và giải mã video H.264 |
| `iphone_mirror/audio.py` | Giải mã âm thanh RTP, giải mã AAC và phát ra loa |
| `iphone_mirror/discovery.py` | Quảng bá dịch vụ qua mDNS |
| `iphone_mirror/config.py` | Quản lý cấu hình và danh tính thiết bị nhận |
| `iphone_mirror/ui.py` | Giao diện cửa sổ hình chiếc iPhone |
| `iphone_mirror/record.py` | Ghi màn hình và âm thanh ra file MP4 |
| `iphone_mirror/autostart.py` | Khởi động cùng Windows (khóa registry `HKCU\...\Run`, tự cập nhật khi đổi chỗ thư mục) |
| `pocketpane.pyw` | Trình khởi chạy không console hoạt động từ mọi thư mục (dùng cho Start with Windows) |
| `iphone_mirror/control/` | Client WebDriverAgent, khởi chạy qua USB và kiểm tra thiết lập (`setup.py`) |
| `iphone_mirror/setup_window.py` | Cửa sổ hướng dẫn từng bước *Set Up iPhone Control* |
| `build.bat`, `pocketpane.spec`, `pocketpane_control.py` | Đóng gói bản chạy độc lập (PyInstaller) và điểm vào console |
| `tests/` | Bộ kiểm thử FairPlay, WDA, ghi hình và giao diện (`python -m pytest tests`) |
| `tools/` | Giả lập iPhone, trình tạo bảng FairPlay, công cụ đo hiệu năng vẽ và giải mã |

## Ghi nhận đóng góp

- [UxPlay](https://github.com/FDH2/UxPlay), [RPiPlay](https://github.com/FD-/RPiPlay) và [shairplay](https://github.com/juhovh/shairplay), cùng các tác giả của bộ mã FairPlay *playfair* đi kèm trong các dự án đó. Việc xử lý giao thức tại đây được đối chiếu kỹ với UxPlay.
- [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) hỗ trợ giao tiếp với iPhone qua kết nối USB.
- [Appium WebDriverAgent](https://github.com/appium/WebDriverAgent) hỗ trợ gửi thao tác điều khiển trên iPhone.
- [PyAV](https://github.com/PyAV-Org/PyAV) và FFmpeg phục vụ giải mã và xử lý đa phương tiện.
- [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python) xây dựng giao diện cửa sổ.
- [python-zeroconf](https://github.com/python-zeroconf/python-zeroconf) xử lý quảng bá mDNS.
- Các vector kiểm thử FairPlay được lấy từ [openairplay/airplay2-receiver](https://github.com/openairplay/airplay2-receiver) và [omarroth/doubletake](https://github.com/omarroth/doubletake).

## Giấy phép

Phân phối theo giấy phép [GPL-3.0](LICENSE). Mô-đun `iphone_mirror/fairplay/` được chuyển thể từ mã nguồn *playfair* mang giấy phép GPL-3.0 (xem [licenses/playfair-LICENSE.md](licenses/playfair-LICENSE.md)), do đó toàn bộ ứng dụng được phát hành theo giấy phép GPL-3.0.

## Miễn trừ trách nhiệm

Dự án này không liên kết, không được chứng nhận hay tài trợ bởi Apple Inc. AirPlay, iPhone, FairPlay và iOS là các nhãn hiệu thương mại của Apple Inc., đã đăng ký tại Hoa Kỳ và các quốc gia khác. Chỉ sử dụng phần mềm với thiết bị và nội dung mà bạn có quyền phản chiếu hợp pháp.
