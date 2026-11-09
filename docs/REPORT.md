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

## Cách chạy thử

Python chưa có trong PATH, nên `install.bat` và `run.bat` chưa dùng được ngay. Có 2 cách:

1. Chạy trực tiếp bằng venv có sẵn (không cần cài gì thêm):
   ```bat
   cd /d D:\phuongnh\pocketpane
   .venv\Scripts\pythonw.exe -m iphone_mirror
   ```
2. Hoặc cài Python từ python.org (tick "Add python.exe to PATH") rồi chạy `install.bat` như
   README hướng dẫn.

Chạy test: `.venv\Scripts\python.exe -m pytest tests`

## Cần bạn kiểm tra (với iPhone thật)

1. **Mirror qua Wi-Fi**: lần đầu, Windows Firewall sẽ hỏi; chọn Allow cho mạng Private.
2. **Ghi màn hình**: Ctrl+R, xoay máy, Ctrl+R lần nữa; mở file trong `Videos\PocketPane`.
   Máy dev này chậm (encode khoảng 16 ms/frame ở 590x1280); trên PC thường sẽ mượt hơn.
3. **Các cử chỉ điều khiển mới** (cần cài USB control theo README). Toạ độ vuốt của
   Spotlight, Notification Center, Control Center và Back được tính theo màn hình iPhone,
   nhưng mới chỉ test với WDA giả. Nếu cử chỉ nào không ăn, chỉnh trong
   `iphone_mirror/control/wda.py`.

## Để sau (lý do)

- **PIN/mật khẩu AirPlay**: cần pair-setup kiểu HomeKit (SRP), khá lớn.
- **H.265/4K**: cần bật bit feature và viết parser HEVC.
- **Kéo thả file sang iPhone**: iOS không có cách đẩy file đơn giản như `adb push`.
- **Encoder phần cứng khi ghi hình**: hiện chỉ dùng libx264. Trên máy này `h264_mf` chạy
  được nhưng không nhanh hơn, còn NVENC/QSV/AMF thì không mở được. Có thể thêm sau nếu CPU
  ghi hình thực sự là vấn đề.
