# PocketPane – Kế hoạch phát triển

PocketPane là fork của [0xCodez/iphone-mirror-windows](https://github.com/0xCodez/iphone-mirror-windows) (GPL-3.0).
App biến PC Windows thành AirPlay receiver, hiện màn hình iPhone trong cửa sổ hình iPhone,
có thể điều khiển iPhone qua USB + WebDriverAgent.

## 1. Nghiên cứu các app tương tự

Repo đã clone để đọc (thư mục `D:\phuongnh\_research`, không nằm trong repo này):

| Repo | Vì sao tham khảo |
|---|---|
| [Genymobile/scrcpy](https://github.com/Genymobile/scrcpy) | Chuẩn vàng về mirror + điều khiển (Android): phím tắt, ghi màn hình, clipboard, fullscreen, tắt màn hình chờ |
| [FDH2/UxPlay](https://github.com/FDH2/UxPlay) | AirPlay mirror server mã nguồn mở phổ biến nhất: ghi MP4, PIN/mật khẩu, allow/block thiết bị, chọn độ phân giải/fps, H.265 |
| [FD-/RPiPlay](https://github.com/FD-/RPiPlay) | AirPlay mirror tối giản cho Raspberry Pi |
| [openairplay/airplay2-receiver](https://github.com/openairplay/airplay2-receiver) | Receiver AirPlay 2 bằng Python |

App thương mại (theo bài review): AirServer, Reflector, LonelyScreen, 5KPlayer, ApowerMirror,
và **iPhone Mirroring của macOS** (thứ app này mô phỏng).

### Tính năng hay gặp và trạng thái trong PocketPane

| Tính năng | Có ở | Trước fork | Kế hoạch |
|---|---|---|---|
| Mirror AirPlay + âm thanh | tất cả | Có | – |
| Cửa sổ luôn ở trên, đổi kích thước, xoay | tất cả | Có | – |
| Chụp màn hình ra file | Reflector, ApowerMirror, scrcpy | Có (chỉ menu) | Phím tắt Ctrl+S, copy vào clipboard, mở thư mục |
| **Ghi màn hình ra MP4** | UxPlay `-mp4`, Reflector, ApowerMirror, scrcpy `--record` | Không | **Làm** (remux H.264, không encode lại → gần như 0% CPU) |
| **Toàn màn hình** | scrcpy F11, UxPlay `-fs`, AirServer | Không | **Làm** (F11) |
| Độ trong suốt cửa sổ | nhiều app "floating mirror" | Không | **Làm** |
| Không cho PC ngủ khi đang mirror | scrcpy `--disable-screensaver` | Không | **Làm** |
| Khởi động cùng Windows | AirServer, LonelyScreen | Không | **Làm** |
| Chọn độ phân giải / fps | UxPlay `-s`, `-fps`; AirServer | Chỉ sửa file JSON | **Làm** (menu Quality) |
| Hiện thông số stream | scrcpy `MOD+i` | Chỉ fps | **Làm** (overlay: độ phân giải, fps, bitrate) |
| Dán clipboard PC sang iPhone | scrcpy `MOD+v`, macOS | Không | **Làm** (Ctrl+V gõ chữ trong clipboard qua WDA) |
| Spotlight / Notification / Control Center | macOS (Cmd+3), scrcpy (`MOD+n`) | Không | **Làm** (cử chỉ vuốt qua WDA) |
| Khoá màn hình iPhone | scrcpy `MOD+p` | Có trong WDA client, chưa dùng | **Làm** (Ctrl+L) |
| Chuột giữa = Home, nút Back chuột = vuốt Back | scrcpy | Không | **Làm** |
| Ẩn PC khỏi danh sách Screen Mirroring | – (riêng tư) | Không | **Làm** |
| PIN / mật khẩu AirPlay | UxPlay, AirServer | Không | Để sau (cần SRP pair-setup kiểu HomeKit, khá lớn) |
| H.265 / 4K | UxPlay `-h265` | Không | Để sau (cần bit feature + parser HEVC) |
| Kéo thả file sang iPhone | macOS, scrcpy | Không | Để sau (iOS không có API push file đơn giản như adb) |
| Thông báo iPhone trên PC | macOS | Không | Không làm được qua AirPlay/WDA |

## 2. Lộ trình (mỗi bước = 1 commit)

1. **Môi trường + kế hoạch** – venv, chạy 44 test gốc, test end-to-end bằng `tools/fake_iphone.py`.
2. **Đổi tên thành PocketPane** – tên hiển thị, shortcut, thư mục dữ liệu `%LOCALAPPDATA%\PocketPane`
   (tự chuyển settings + khoá định danh cũ sang, để iPhone không thấy "thiết bị mới").
   Giữ tên package `iphone_mirror` để dễ merge code mới từ upstream.
3. **Sửa lỗi lúc thoát** – `Signal source has been deleted`, `Event loop is closed`.
4. **Tối ưu vẽ** – cache bóng đổ (shadow) thành pixmap thay vì vẽ 11 hình mỗi frame; đo trước/sau.
5. **Ghi màn hình MP4** (Ctrl+R) – remux luồng H.264 gốc, có chấm đỏ + thời lượng trên thanh bar.
6. **Chụp màn hình nâng cao** – Ctrl+S lưu, Ctrl+Shift+S copy clipboard, menu mở thư mục.
7. **Cửa sổ** – F11 toàn màn hình, độ trong suốt, khởi động cùng Windows, chống ngủ khi mirror.
8. **Chất lượng stream + overlay thông số** – menu Quality (720p/1080p/1440p, 30/60 fps), Ctrl+I.
9. **Điều khiển mở rộng** – Ctrl+V dán, Ctrl+L khoá, Ctrl+K Spotlight, Ctrl+N Notification,
   Ctrl+Shift+N Control Center, chuột giữa = Home, nút Back chuột = vuốt Back. Có test với MockWDA.
10. **Ẩn/hiện PC trong Screen Mirroring** (tạm dừng quảng bá mDNS).
11. **Tài liệu** – README, báo cáo `docs/REPORT.md`.
