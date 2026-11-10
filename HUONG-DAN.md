# PocketPane – Hướng dẫn tiếng Việt

PocketPane biến máy tính Windows thành **màn hình nhận AirPlay**. Nó hiện màn hình iPhone trong một cửa sổ hình iPhone, bo góc, luôn nổi trên các cửa sổ khác. Hình và tiếng truyền qua Wi-Fi, **không cần cài gì trên điện thoại**.

> Bản dịch tóm tắt từ `README.md`. Nếu có chỗ nào khác nhau thì bản tiếng Anh là chuẩn.

---

## 1. Tình trạng trên máy bạn

| Mục | Tình trạng |
|---|---|
| Mã nguồn | `D:\Code\pocketpane` |
| Python dùng để chạy | Python 3.13 có sẵn trên máy |
| Môi trường riêng của app | `%LOCALAPPDATA%\PocketPane\venv` |
| Shortcut | **PocketPane** ở Desktop và Start menu |
| Điều khiển qua USB | **Chưa cài** (theo lựa chọn của bạn) |

⚠️ **Nên làm 1 lần:** bạn tự double-click `D:\Code\pocketpane\install.bat`. Lần cài trước chạy bên trong app Claude, nên Windows có thể đã chuyển môi trường Python vào thư mục riêng của Claude. Khi đó shortcut sẽ không mở được app. Tự chạy lại `install.bat` (mất vài phút) là sửa được.

---

## 2. Cách dùng (chiếu màn hình)

1. Mở **PocketPane** từ shortcut, hoặc chạy `run.bat`. Cửa sổ hiện chữ **"Waiting for iPhone"** (đang chờ iPhone). Dòng dưới cùng có ghi địa chỉ IP của PC.
2. **Chỉ lần đầu:** Windows Firewall sẽ hỏi có cho Python dùng mạng không. Tick **Private networks** rồi bấm **Allow**.
3. Đặt Wi-Fi của PC ở chế độ **Private**: Settings > Network & internet > Wi-Fi > *tên mạng* > Network profile type > **Private**.
4. Trên iPhone (cùng Wi-Fi với PC): mở **Trung tâm điều khiển > Phản chiếu màn hình** (Screen Mirroring) rồi chọn tên PC.
5. Cửa sổ hiện **"Connecting..."**, sau đó là màn hình iPhone.

Mỗi lúc chỉ chạy được một bản app. Nếu mở thêm lần nữa, app chỉ đưa cửa sổ đang có lên trước.

---

## 3. Thao tác với cửa sổ

Rê chuột vào cửa sổ để hiện **thanh trên cùng**. Từ trái sang phải: tên thiết bị và FPS, nút **Control** (hình bàn tay, dùng cho điều khiển USB), **Home**, **Ghim** (luôn nổi trên cùng), **Thu nhỏ**, **Đóng**.

| Thao tác | Tác dụng |
|---|---|
| Kéo chuột trái ở bất kỳ đâu | Di chuyển cửa sổ |
| Double-click | Chuyển qua lại giữa cỡ lớn và cỡ thường |
| Ctrl + lăn chuột / Ctrl + `+` / Ctrl + `-` | Phóng to, thu nhỏ |
| Chuột phải | Mở menu |

### Phím tắt hữu ích (dùng được khi không có USB)

| Phím | Tác dụng |
|---|---|
| Ctrl + S | Lưu ảnh chụp màn hình (vào `Pictures\PocketPane`) |
| Ctrl + Shift + S | Chép ảnh chụp vào clipboard |
| Ctrl + R | Bắt đầu / dừng quay màn hình ra file MP4 (vào `Videos\PocketPane`) |
| Ctrl + M | Tắt / bật tiếng trên PC |
| Ctrl + I | Hiện / ẩn thông số luồng hình (độ phân giải, fps, bitrate) |
| F11 (Esc để thoát) | Toàn màn hình |

Các phím Ctrl + H, J, B, K, N, L, V, Ctrl + ↑/↓ (Home, đa nhiệm, quay lại, tìm kiếm, khóa máy, dán, âm lượng...) **chỉ hoạt động khi đã bật điều khiển USB**.

### Menu chuột phải (các mục chính)

| Mục | Tác dụng |
|---|---|
| Always on Top | Luôn nổi trên các cửa sổ khác |
| Sound | Phát tiếng iPhone ra loa PC |
| Size | Cỡ nhỏ / vừa / lớn |
| Stream Quality | 720p / 1080p / 1440p, 30 / 60 fps (áp dụng từ lần kết nối sau) |
| Opacity | Độ trong suốt 100% / 90% / 75% / 50% |
| Keep PC Awake While Mirroring | Không cho PC ngủ khi đang chiếu (mặc định bật) |
| Start with Windows | Tự chạy khi đăng nhập Windows, nằm ẩn ở khay hệ thống và hiện ra khi iPhone kết nối |
| Rename PC... | Đổi tên PC hiện trên iPhone |
| Visible in Screen Mirroring | Bỏ tick để ẩn PC khỏi danh sách trên iPhone |
| Open Media Folder | Mở thư mục ảnh chụp và video |
| Open Log | Mở file log (dùng khi gặp lỗi) |
| Quit | Thoát app |

---

## 4. Xử lý sự cố

**iPhone không thấy tên PC trong Phản chiếu màn hình**
- Wi-Fi trên PC phải đặt ở **Private** (xem mục 2).
- Cho Python qua tường lửa: Start > gõ *"Allow an app through Windows Firewall"* > tìm `pythonw.exe` / `python.exe` > tick **Private**.
- iPhone và PC phải cùng mạng. Wi-Fi khách (Guest) hoặc router bật "AP isolation" sẽ chặn hai máy thấy nhau. VPN trên một trong hai máy cũng có thể gây ra chuyện này.
- Thoát app rồi mở lại.

**Báo "Could not decrypt the video"** → Tắt phản chiếu trên iPhone rồi kết nối lại.

**Báo "iPhone is locked"** → Mở khóa iPhone, hình sẽ tự chạy tiếp.

**Không có tiếng** → Kiểm tra mục **Sound** đã tick chưa (hoặc bấm Ctrl + M), và Windows có đang phát ra đúng loa không.

**Màn hình đen khi xem Netflix, Apple TV...** → Đây là nội dung có bản quyền (DRM). iPhone tự chặn, không sửa được.

---

## 5. Cài đặt (file settings.json)

File `%LOCALAPPDATA%\PocketPane\settings.json` được tạo ở lần chạy đầu. Hãy **thoát app trước khi sửa file**.

| Khóa | Mặc định | Ý nghĩa |
|---|---|---|
| `name` | tên máy | Tên hiện trên iPhone |
| `height` | `1080` | Độ phân giải. Có thể thử `1440` cho nét hơn; nếu iPhone không kết nối được thì đổi lại `1080` |
| `fps` | `60` | Số khung hình mỗi giây |
| `audio` | `true` | Phát tiếng ra PC |
| `always_on_top` | `true` | Luôn nổi trên cùng |
| `opacity` | `1.0` | Độ trong suốt (từ 0.3 đến 1) |
| `keep_awake` | `true` | Không cho PC ngủ khi đang chiếu |

Xóa file này là reset mọi thứ về mặc định. Sau đó iPhone sẽ thấy PC như một máy nhận mới.

---

## 6. Điều khiển iPhone bằng chuột / bàn phím (tùy chọn, chưa cài)

AirPlay chỉ truyền hình và tiếng. Muốn bấm, vuốt, gõ chữ trên iPhone từ PC thì cần thêm **WebDriverAgent (WDA)** chạy trên iPhone qua cáp USB. Khi nào bạn muốn dùng thì báo mình. Tóm tắt các bước:

1. Cài **iTunes tải từ apple.com** (không dùng bản Microsoft Store). Cắm cáp, mở khóa iPhone, bấm **Tin cậy** (Trust).
2. Chạy `control.bat reveal-dev-mode`. Sau đó trên iPhone vào Cài đặt > Quyền riêng tư & Bảo mật > **Chế độ nhà phát triển**, bật lên. Máy sẽ khởi động lại.
3. Chạy `control.bat get-wda`, lệnh này tải file `WebDriverAgentRunner.ipa` vào thư mục Downloads.
4. Dùng **Sideloadly** để cài file `.ipa` lên iPhone. Bước này bạn tự nhập Apple ID. Với Apple ID miễn phí, app chỉ dùng được **7 ngày**, sau đó phải cài lại.
5. Trên iPhone vào Cài đặt > Cài đặt chung > **Quản lý VPN & thiết bị** > tin cậy Apple ID của bạn.
6. Chạy `control.bat doctor` để kiểm tra, sửa đến khi mọi mục đều đạt.
7. Trong cửa sổ PocketPane bấm **Ctrl + U**. Nút bàn tay nhấp nháy cam rồi chuyển xanh là dùng được.

Khi đã bật điều khiển: click = chạm, giữ 0.5 giây = nhấn giữ, kéo = vuốt, lăn chuột = cuộn, gõ phím = nhập chữ, click chuột giữa = Home. Mỗi thao tác trễ khoảng 0.1–0.3 giây. Chưa kéo thả "trực tiếp" được: lệnh vuốt chỉ được gửi khi bạn thả chuột.

---

## 7. File log

`%LOCALAPPDATA%\PocketPane\pocketpane.log`, mở nhanh bằng chuột phải > **Open Log**. Khi gặp lỗi, gửi file này cho mình xem.
