# Báo cáo phát triển PocketPane – 09/11/2026

Repo: https://github.com/HienPhuong99/pocketpane (private) · Thư mục: `D:\phuongnh\pocketpane`

## Tóm tắt nhanh

- Đã làm xong **toàn bộ 11 bước** trong [PLAN.md](PLAN.md): **14 commit**, mỗi commit một việc
  và có ghi rõ đã làm gì.
- Bộ test tăng từ **44 lên 66 test, tất cả đều pass**. Thêm test cho ghi hình, cửa sổ (chạy
  offscreen), cử chỉ điều khiển (dùng WDA giả) và mDNS thật.
- Đã chạy end-to-end với "iPhone giả" (`tools/fake_iphone.py`, đi qua đủ quá trình
  pair/FairPlay/video/audio): mirror, ghi MP4 có tiếng, chấm đỏ REC, thoát app không lỗi.
- **Chưa thử với iPhone thật**, vì trên máy không có iPhone. Xem mục "Cần bạn kiểm tra" ở cuối.

## Những gì đã cài đặt

| Cài gì | Ở đâu | Ghi chú |
|---|---|---|
| Python 3.12.10 (bản portable từ NuGet) | `D:\tools\pynuget\tools\python.exe` | Bộ cài MSI bị lỗi 0x80070003 nên dùng gói NuGet. **Chưa thêm vào PATH** |
| Môi trường ảo (venv) và thư viện của app, kèm pytest | `D:\phuongnh\pocketpane\.venv` | PySide6 6.12, PyAV 19, pymobiledevice3 11.50… |
| Repo tham khảo: scrcpy, UxPlay, RPiPlay, airplay2-receiver | `D:\phuongnh\_research` | Chỉ để đọc, nằm ngoài repo |

## Nghiên cứu

Đã đọc tài liệu, code của scrcpy và UxPlay, cùng các bài review AirServer, Reflector,
LonelyScreen, 5KPlayer, ApowerMirror và iPhone Mirroring của macOS. Bảng so sánh tính năng
nằm trong [PLAN.md](PLAN.md).

Phát hiện quan trọng (đọc từ code UxPlay): iOS chỉ gửi keyframe lúc bắt đầu và khi đổi
định dạng. Vì vậy muốn ghi hình giữa phiên thì phải encode lại, không copy stream được.

## Các thay đổi (theo thứ tự commit)

| # | Commit | Nội dung |
|---|---|---|
| 1 | `9b4b866` | Kế hoạch và ghi chú nghiên cứu (`docs/PLAN.md`) |
| 2 | `a2fa2f6` | **Đổi tên thành PocketPane**: tiêu đề, khay hệ thống, shortcut, file .bat. Thư mục dữ liệu chuyển sang `%LOCALAPPDATA%\PocketPane`; settings cũ được chép sang một lần để iPhone vẫn nhận ra đúng máy. Tên package `iphone_mirror` giữ nguyên để dễ lấy code mới từ repo gốc |
| 3 | `8df3c2b` | **Sửa lỗi lúc thoát** khi đang mirror (`Signal source has been deleted`, `Event loop is closed`) |
| 4 | `94c7caf` | **Vẽ nhanh hơn khoảng 45%**: cache bóng đổ, font và metrics. Mỗi frame giảm từ 5.15 xuống 2.8 ms (bar ẩn) và từ 6.11 xuống 3.4 ms (bar hiện) |
| 5 | `d4d6620` | **Ghi màn hình MP4 (Ctrl+R)** có tiếng; lưu vào `Videos\PocketPane`. Khi xoay máy thì tách sang file mới; có chấm đỏ REC và đồng hồ |
| 6 | `eed3f08` | **Chụp màn hình**: Ctrl+S lưu file, Ctrl+Shift+S copy vào clipboard; menu "Open Media Folder" |
| 7 | `a21efb0` | **Toàn màn hình (F11/Esc)** |
| 8 | `11a0b58` | **Độ trong suốt cửa sổ** (100/90/75/50%) và **không cho PC ngủ khi đang mirror** |
| 9 | `902d771` | **Khởi động cùng Windows** (chạy ẩn ở khay, iPhone kết nối thì cửa sổ tự hiện) và cờ `--tray` |
| 10 | `07235ec` | **Menu chất lượng stream** (720p/1080p/1440p, 30/60 fps) và **overlay thông số (Ctrl+I)** |
| 11 | `88c13e5` | **Điều khiển thêm**: Back (Ctrl+B, nút Back chuột), Spotlight (Ctrl+K), Notification Center (Ctrl+N), Control Center (Ctrl+Shift+N), khoá máy (Ctrl+L), dán clipboard (Ctrl+V), chuột giữa = Home |
| 12 | `f48fa9a` | **Ẩn/hiện PC trong danh sách Screen Mirroring** (đã test với mDNS thật) |
| 13 | `493d4db` | Công cụ đo decode. Kết quả: pipeline video đã tối ưu sẵn (decode 3.7 ms/frame) nên không sửa |
| 14 | `abd359b` | Cập nhật README |

## Đợt 2 – Review đa agent và sửa lỗi (10/11)

Mình chạy một workflow review gồm 5 reviewer, mỗi người phụ trách một mảng:
- ghi hình;
- cửa sổ;
- input và điều khiển;
- receiver và hệ thống;
- đa luồng và chất lượng test.

Mỗi lỗi tìm được đều qua **3 skeptic độc lập cố bác bỏ**, và chỉ được giữ lại khi ít nhất 2/3
xác nhận. Kết quả: 20 cáo buộc; **18 được xác nhận** (gộp trùng còn 15, phần lớn đã tái hiện
được bằng code chạy thật); 2 bị bác. Cáo buộc có lá phiếu bị gián đoạn thì mình tự kiểm tra
và tái hiện được.

| Commit | Đã sửa |
|---|---|
| `c206381` | **Ghi hình**: (1) Nếu encoder chết (thư mục Videos không ghi được, hết đĩa) thì Ctrl+R hoặc thoát app làm **treo app vĩnh viễn**, còn UI vẫn hiện REC. Giờ app tự dừng ghi và báo lỗi. (2) **File MP4 dạng fragmented**: app bị crash, bị kill hay mất điện thì chỉ mất vài giây cuối, thay vì mất trắng cả file. (3) Audio không còn bị bỏ khi encoder chậm, và không bị lệch dần. (4) Bắt đầu ghi khi màn hình đứng yên thì vẫn ghi được |
| `3d6f09a` | **UI**: (1) Ở chế độ toàn màn hình, thanh bar không bao giờ ẩn, nên chạm vào góc trên bên phải là **thoát app**. (2) Mở cửa sổ từ khay làm mất chế độ toàn màn hình. (3) Keep-awake vẫn giữ máy thức khi iPhone đã khoá. (4) Overlay hiện số liệu cũ. (5) Nhấn chuột giữa hai lần nhanh thì mất một lần |
| `f5fd853` | **Điều khiển**: (1) Spotlight không mở được khi đang ở app nằm ngang. (2) Dán đoạn văn dài bị timeout sau 15 giây, khiến điều khiển trông như bị mất |
| `48d3513` | **mDNS**: bấm ẩn/hiện liên tục, hoặc đổi tên PC đúng lúc app đang khởi động, có thể để lại trạng thái sai. Giờ mọi thao tác chạy tuần tự trên 1 thread |
| `7191587` | **Start with Windows**: (1) Hỏng nếu đường dẫn có chữ tiếng Việt (do WScript.Shell chỉ hỗ trợ ANSI). (2) Bị cũ khi di chuyển thư mục. Giờ dùng registry `HKCU\...\Run` (hỗ trợ Unicode) cùng launcher `pocketpane.pyw`, và tự cập nhật đường dẫn mỗi lần khởi động |
| `2cf6b3e` | Thoát app đúng lúc đang khởi động thì thread airplay văng `CancelledError` |

Số test tăng từ 66 lên **76, tất cả đều pass**. Lượt chạy end-to-end với iPhone giả không có lỗi.

## Đợt 3 – Installer và CI (10/11)

| Commit | Nội dung |
|---|---|
| `322cd5e` | **`install.bat` không cần Python có sẵn**: nó thử chạy thật từng ứng viên (`python`, `py -3`, bản riêng), nên bỏ qua bản giả của Microsoft Store. Nếu không có Python, nó tải gói Python 3.12 chính thức từ nuget.org, **kiểm tra SHA-256 đã ghim**, rồi giải nén vào `%LOCALAPPDATA%\PocketPane\python`; không cài vào hệ thống, không sửa PATH. Shortcut tạo bằng API Unicode (`tools\shortcuts.ps1`), vì WScript.Shell, `tar.exe` và `curl` của Windows đều hỏng khi đường dẫn có chữ tiếng Việt |
| `f9e8bb8` | **CI bằng GitHub Actions**: chạy toàn bộ test trên Windows mỗi lần push. Lần chạy đầu xanh, 76 test pass |
| `e947383` | Sửa 5 lỗi installer mà vòng review phản biện xác nhận: (1) venv mất Python gốc không bao giờ được dựng lại; (2) đường dẫn có `&` hoặc `^` làm cài đặt hỏng; (3) Python 32-bit hoặc không có pip vẫn được chấp nhận; (4) giải nén bị ngắt giữa chừng để lại Python hỏng |

Đã test end-to-end trên chính máy này: không có Python trong PATH; thư mục `Phương Ứng dụng`
và `A&B ^x (2)`; venv mất Python gốc; Python riêng bị hỏng. Cả 4 tình huống đều cài xong,
và app cài ra chạy được với iPhone giả.

**Cách cài giờ chỉ cần double-click `install.bat`**, máy không cần có Python.

## Đợt 4 – Điều khiển iPhone dễ cài hơn (10/11)

| Commit | Nội dung |
|---|---|
| `62de11c` | Phần kiểm tra cài đặt điều khiển chuyển thành module dùng chung (`control/setup.py`). Thêm **kiểm tra hạn chữ ký WebDriverAgent**, đọc từ provisioning profile trên iPhone (Apple ID miễn phí chỉ cho 7 ngày) |
| `a59d288` | **Cửa sổ "Set Up iPhone Control"** (chuột phải > Set Up iPhone Control..., hoặc nút *Setup Guide* trong hộp thoại lỗi). Mỗi bước có đèn xanh/cam/đỏ và tự kiểm tra lại mỗi 4 giây. Có sẵn các nút: Get Apple Devices, Show Developer Mode, Download WebDriverAgent, Open Sideloadly, Turn on control. Khi bật điều khiển mà WDA còn dưới 2 ngày là hết hạn thì app báo nhắc |
| `079dbc2` | **Gõ tiếng Việt khi điều khiển**: bộ gõ Microsoft Vietnamese Telex (và IME Trung, Nhật) giờ gõ được lên iPhone. Unikey vốn đã chạy được, nay có thêm test |
| `0277bbc` | Sửa 7 lỗi mà vòng review phản biện xác nhận. Đáng kể nhất: (1) `doctor` văng traceback khi đọc hạn chữ ký bị lỗi; (2) một profile wildcard không liên quan che mất việc WDA sắp hết hạn; (3) cửa sổ setup kẹt mãi ở "Working..." hoặc vẫn chạy ngầm sau khi bấm Esc; (4) chữ đang soạn trong IME bị gửi sau cú chạm, nên rơi vào sai ô. Ngoài ra còn phát hiện một test làm sập trình thông dịch một cách âm thầm, che mất các test phía sau. Giờ **100 test pass**, đã chạy 3 lần liên tiếp |
| (mới) | Theo lựa chọn của bạn: cửa sổ giờ **mặc định là cửa sổ thường**, không còn luôn nổi trên cùng. Bật lại bằng nút Pin hoặc chuột phải > Always on Top. Các lựa chọn còn lại (giữ tên máy, 1080p 60fps, phát ra loa PC, không tự chạy, giữ trong repo) vốn đã là mặc định nên không đổi |

Không làm: **điều khiển không cần cáp** (ghép đôi qua Wi-Fi trên iOS 17+). Phần này cần có
iPhone thật để phát triển và thử, nên để sau khi bạn đã chạy được điều khiển bằng cáp.

## Đợt 5 – Tối ưu cho nhẹ và mượt (10/11)

Cách làm: đo trước, sửa chỗ tốn nhất, đo lại. Mọi con số dưới đây đo trên máy này (4 nhân,
màn hình 1366×768), lấy lần chạy tốt nhất trong nhiều lần vì máy nhiễu.

| Hạng mục | Trước | Sau | Sửa gì |
|---|---|---|---|
| Vẽ một frame, cửa sổ nhỏ (242×524) | 1,96 ms (bar hiện: 2,64) | 1,05 ms (1,07) | Bóng đổ và viền máy vẽ sẵn một lần cho mỗi cỡ cửa sổ. Frame mới chỉ vẽ lại vùng màn hình iPhone, không vẽ lại bóng và thanh trên cùng |
| Vẽ một frame, cửa sổ lớn (480×1040) | 6,0 ms | 3,6 ms | Như trên |
| Scale frame cỡ đầy đủ (886×1920) | 8,2 ms | 3,7 ms | Qt đọc thẳng vùng nhớ của ffmpeg, bỏ một lần copy cả frame |
| CPU cho mỗi frame, chạy thật với iPhone giả | 9,6–13,8 ms | 8,6–10,5 ms | Tổng của các mục trên (số này gồm cả audio và bắt tay kết nối) |
| Từ lúc chạy đến lúc cửa sổ hiện | khoảng 1,0 s | khoảng 0,5 s | Cửa sổ hiện trước, PyAV / numpy / asyncio / zeroconf nạp sau |
| Dung lượng bản `PocketPane.exe` | 299 MB | 245 MB | Bỏ phần Qt không dùng (OpenGL phần mềm, bản dịch, SVG, plugin ảnh) và `jedi` |
| RAM lúc chờ | 107 MB | 104 MB | — |
| CPU lúc chờ | 0 % | 0 % | Vốn đã tốt |

Thay đổi khác:

- **Màn hình đặt 125% / 150%**: trước đây ảnh bị lấy mẫu lại nên hơi nhoè. Giờ vùng màn hình
  iPhone nằm đúng trên pixel thật, ảnh được chép 1:1 nên nét. Ở 100% ảnh giống hệt bản cũ
  (đã so từng pixel).
- **Phóng to cửa sổ khi màn hình iPhone đứng yên**: iPhone chỉ gửi frame khi màn hình đổi, nên
  trước đây ảnh bị nhoè cho tới frame kế tiếp. Giờ frame cuối được scale lại sau 80 ms.
- **Cửa sổ ẩn hoặc thu nhỏ**: vẫn decode (H.264 cần đủ mọi frame) nhưng không scale và không
  vẽ nữa. Khi hiện lại, frame cuối được scale ngay.
- **Giao diện bận**: chỉ giữ frame mới nhất thay vì xếp hàng mọi frame (cách scrcpy làm), nên
  không dồn bộ nhớ và hình không bị trễ dần.
- Việc nhỏ: bộ đệm đọc luồng video tăng lên 1 MB (mặc định 64 KB nhỏ hơn một key frame);
  audio không tạo lại đối tượng AES cho từng gói; cảnh báo "queue full" không ghi log từng frame.

Đã thử nhưng **không dùng**: decode bằng card đồ hoạ (D3D11VA). Trên máy này CPU giảm
(7,7 → 3,8 ms/frame) nhưng mỗi frame lại chậm hơn (6,3 → 11,9 ms) vì phải chép ảnh từ card về,
nên hình trễ hơn. Cũng đã thử vẽ ảnh bằng `drawImage` thay cho brush: chậm hơn, nên giữ brush.

Sau đó chạy một vòng review phản biện (2 reviewer, mỗi lỗi qua 1 skeptic cố bác bỏ). Kết quả:
4 cáo buộc, **3 được xác nhận và tái hiện, cả 3 đều nhẹ và đã sửa**; 1 bị bác (vẫn sửa vì chỉ
tốn một dòng):

- Frame đầu của phiên được decode đúng lúc cửa sổ còn ẩn thì cửa sổ hiện ra mà chưa có hình,
  cho tới frame kế tiếp. Chỉ xảy ra khi giao diện bị đứng hơn 100 ms đúng lúc iPhone kết nối.
- Frame đầu của phiên chỉ vẽ lại vùng màn hình, nên viền đen 1 pixel quanh máy thiếu nửa ngoài
  cho tới lần vẽ lại toàn cửa sổ.
- Ở cửa sổ rất nhỏ, khung thông số (Ctrl+I) tràn ra ngoài vùng màn hình và phần tràn không
  được vẽ lại.

Test tăng từ 104 lên **111, tất cả pass**. Đã chạy end-to-end với iPhone giả bằng cả mã nguồn
lẫn bản `PocketPane.exe` mới build; 8 lệnh pymobiledevice3 mà app dùng vẫn chạy trong bản build.
**Chưa đo với iPhone thật.**

## Cách chạy thử

Double-click `install.bat` (nếu máy không có Python, nó tự tải bản riêng), rồi mở
**PocketPane** từ Desktop hoặc Start menu. Hoặc chạy bằng venv dev có sẵn:
```bat
cd /d D:\phuongnh\pocketpane
.venv\Scripts\pythonw.exe -m iphone_mirror
```

Chạy test: `.venv\Scripts\python.exe -m pytest tests`

## Việc bạn cần làm (gom về cuối, theo thứ tự)

Bạn cần iPhone, cáp USB, PC và iPhone cùng mạng Wi-Fi, cùng Apple ID của bạn (bản miễn phí là đủ).

**A. Xem màn hình iPhone (không cần cáp)**
1. Double-click `install.bat`, rồi mở **PocketPane**.
2. Windows Firewall hỏi lần đầu: tick **Private networks** rồi bấm **Allow**.
3. Trên iPhone: Control Center > Screen Mirroring > chọn tên PC.
4. Thử ghi màn hình: Ctrl+R, xoay máy, Ctrl+R lần nữa; mở file trong `Videos\PocketPane`.

**B. Điều khiển iPhone (làm một lần)**
1. Trong PocketPane: chuột phải > **Set Up iPhone Control...**. Từ đây làm theo đèn đỏ.
2. Bấm **Get Apple Devices** và cài app Apple Devices từ Microsoft Store. Nếu Store báo Windows
   quá cũ (cần Windows 10 22H2 trở lên), bấm **Get iTunes** để tải iTunes64Setup.exe từ apple.com
   rồi cài. iTunes cũng cài driver USB của Apple, nên dùng được thay cho Apple Devices.
3. Cắm cáp, mở khóa iPhone, bấm **Trust** rồi nhập mật mã.
4. Bấm **Show Developer Mode**. Trên iPhone: Settings > Privacy & Security > Developer Mode >
   bật, máy khởi động lại; mở khóa rồi bấm **Turn On**.
5. Bấm **Download WebDriverAgent** (file `.ipa` tự hiện trong Explorer). Bấm **Open
   Sideloadly**, cài Sideloadly, kéo file `.ipa` vào, nhập Apple ID rồi bấm Start.
6. Trên iPhone: Settings > General > VPN & Device Management > Apple ID của bạn > **Trust**.
7. Khi mọi bước đã xanh, bấm **Turn on control**. Lần đầu sẽ tải thêm khoảng 1 phút.
8. Thử điều khiển: click, kéo, cuộn, gõ chữ (cả Telex), Ctrl+H (Home), Ctrl+K (Spotlight),
   Ctrl+N (Notification Center), Ctrl+B (Back), Ctrl+V (dán).
9. Mỗi 7 ngày (Apple ID miễn phí): cài lại `.ipa` bằng Sideloadly. App sẽ nhắc trước.

Nếu có bước nào không xanh, gửi mình ảnh chụp cửa sổ setup và file log (chuột phải > Open Log).

## Để sau (lý do)

- **Điều khiển không cần cáp (iOS 17+)**: cần iPhone thật để phát triển và thử.
- **PIN/mật khẩu AirPlay**: cần pair-setup kiểu HomeKit (SRP), khá lớn.
- **H.265/4K**: cần bật bit feature và viết parser HEVC.
- **Kéo thả file sang iPhone**: iOS không có cách đẩy file đơn giản như `adb push`.
- **Encoder phần cứng khi ghi hình**: hiện chỉ dùng libx264. Trên máy này `h264_mf` chạy
  được nhưng không nhanh hơn, còn NVENC/QSV/AMF thì không mở được.
