# PocketPane – Kế hoạch thành app chuyên nghiệp có thu phí

Lập ngày 10/11/2026. Dựa trên mã nguồn hiện tại (commit `a2ee28b`), `docs/PLAN.md`, `docs/REPORT.md`
và tra cứu giá đối thủ cùng ngày. Phần pháp lý là nhận định kỹ thuật, **không phải tư vấn luật**.

## 1. Kết luận nhanh

- **Bán được, nhưng không bán được theo kiểu "phần mềm đóng, khoá bằng license key".** Toàn bộ app
  là GPL-3.0 (fork từ repo GPL, lõi FairPlay là code GPL, `pymobiledevice3` cũng GPL). GPL cho
  phép thu tiền, nhưng người mua có quyền nhận mã nguồn và phát lại miễn phí.
- **Đường ngắn nhất tới đồng tiền đầu tiên:** giữ GPL, bán *bản chính thức đã ký, tự cập nhật*
  trên **Microsoft Store** (giống Krita: mã nguồn mở GPL, miễn phí trên web, có phí trên Store).
  Store lo ký số, cập nhật, thanh toán, dùng thử và thuế, nên không phải tự viết hệ thống license.
- **Thứ đáng tiền nhất của app** không phải mirror (đã có UxPlay, 5KPlayer miễn phí) mà là
  *"iPhone Mirroring cho Windows": cửa sổ hình điện thoại + điều khiển bằng chuột phím*. Hiện phần
  điều khiển là phần khó cài nhất (7 bước, dòng lệnh, ký lại mỗi 7 ngày). Đầu tư vào đây trước.
- **Việc số 1 trước khi làm bất cứ gì:** thử với iPhone thật. `REPORT.md` ghi rõ mọi thứ mới chỉ
  chạy với iPhone giả (`tools/fake_iphone.py`).

## 2. Hiện trạng

| Mảng | Đang có | Còn thiếu để gọi là "chuyên nghiệp" |
|---|---|---|
| Lõi mirror | AirPlay + âm thanh, xoay, 720p–1440p, 30/60 fps | Chưa kiểm chứng trên iPhone thật; chưa có PIN, H.265, giải mã bằng GPU |
| Cửa sổ | Hình iPhone, nổi trên cùng, toàn màn hình, độ trong suốt, khay hệ thống | Chưa có hộp thoại Cài đặt (phải sửa `settings.json`), chỉ có tiếng Anh |
| Ghi hình | MP4 có tiếng, ảnh chụp | Chỉ libx264 (tốn CPU), tách file khi xoay |
| Điều khiển | Chạm, vuốt, gõ, Home, Spotlight… qua USB + WebDriverAgent | Cài bằng dòng lệnh + Sideloadly, hết hạn 7 ngày, trễ 100–200 ms, không kéo-thả trực tiếp |
| Cài đặt | `install.bat` tự tải Python, tạo shortcut | Không phải bộ cài thật: chưa ký số, tường lửa hỏi về `pythonw.exe`, không gỡ cài được từ Settings |
| Cập nhật | Không có | Cần tự cập nhật |
| Chất lượng | 76 test, CI trên Windows, đã qua 2 vòng review | Chưa có báo lỗi từ người dùng, chưa có số liệu sử dụng |
| Kinh doanh | Không có | Trang giới thiệu, giá, thanh toán, EULA, chính sách riêng tư, kênh hỗ trợ |

Quy mô: khoảng 5.000 dòng Python, 1 người làm. Đủ nhỏ để một người duy trì.

## 3. Ba rào cản phải xử lý trước khi thu tiền

### 3.1 Giấy phép GPL-3.0 (chắc chắn, không tránh được)

- Nguồn GPL trong app: code gốc của 0xCodez (`airplay.py`, `ui.py`…), bản port playfair
  (`iphone_mirror/fairplay/`), thư viện `pymobiledevice3`. Cần kiểm tra thêm: bản FFmpeg đi kèm
  PyAV có libx264 (GPL).
- Hệ quả: phát hành bản nhị phân cho ai thì phải đưa mã nguồn tương ứng cho người đó. Repo GitHub
  đang **private** – khi bắt đầu bán nên chuyển public cho đơn giản.
- Khoá license trong code là vô nghĩa về kỹ thuật: ai cũng được phép xoá và build lại. Vì vậy
  **đừng tốn công chống crack**; bán sự tiện lợi (cài một cú, đã ký, tự cập nhật, có hỗ trợ).

### 3.2 FairPlay và Apple (rủi ro thật, có tiền lệ)

- Lõi giải mã dùng playfair, code dịch ngược giao thức của Apple. Bán thương mại làm tăng mức độ
  bị chú ý. Tiền lệ: AirServer, Reflector bán receiver AirPlay cho Windows hơn 10 năm nay.
- Giảm rủi ro: không đụng tới nội dung DRM (Netflix… vẫn đen, giữ nguyên như vậy); không dùng
  logo Apple; sẵn sàng tinh thần bị gỡ khỏi một kênh bán; **hỏi luật sư sở hữu trí tuệ trước khi
  chi tiền quảng cáo lớn**.

### 3.3 Nhãn hiệu

- Không đưa "iPhone", "AirPlay" vào tên app, icon, tên miền. Tên "PocketPane" ổn. Mô tả kiểu
  "mirror your iPhone on Windows" là dùng mô tả, chấp nhận được; giữ dòng disclaimer.
- Khung cửa sổ: dùng khung điện thoại trung tính, tránh sao chép chi tiết nhận diện của iPhone
  (Dynamic Island, tỉ lệ bo góc y hệt) trong ảnh quảng cáo.

## 4. Định vị, khách hàng, giá

**Định vị:** "iPhone Mirroring cho Windows" – xem và điều khiển iPhone ngay trên PC, trong một cửa
sổ nhỏ nổi cạnh công việc. Microsoft Phone Link không mirror được màn hình iPhone; tính năng
iPhone Mirroring của Apple chỉ có trên Mac.

**Khách hàng, theo thứ tự ưu tiên:**

1. Người dùng Windows + iPhone muốn trả lời tin nhắn, xem OTP, dùng app điện thoại mà không cầm máy.
2. Lập trình viên / QA / người làm nội dung: quay demo app, chụp màn hình có khung máy.
3. Lớp học, phòng họp: chiếu iPhone lên PC (cần PIN và nhiều máy cùng lúc – làm sau).

**Giá đối thủ (tra ngày 10/11/2026, cần kiểm tra lại trên trang chính thức trước khi chốt):**

| App | Giá | Điều khiển iPhone? |
|---|---|---|
| UxPlay, 5KPlayer | Miễn phí | Không |
| Reflector 4 | khoảng 18–20 USD, mua một lần | Không |
| AirServer | mua một lần (một nguồn ghi 19,99 USD, chưa xác nhận) | Không |
| Tenorshare Phone Mirror | 39,95 USD / năm | Chủ yếu Android |
| iMyFone MirrorTo | 59,99 USD trọn đời | Có quảng cáo, chủ yếu Android |
| ApowerMirror | khoảng 29,95 USD / tháng | Có quảng cáo, chủ yếu Android |

**Đề xuất giá:** mua một lần **19 USD** (Việt Nam khoảng 299.000 đ), dùng thử đầy đủ 7–14 ngày.
Mirror-only thì khó đòi cao hơn Reflector; khi phần điều khiển cài được trong 5 phút thì nâng lên
29 USD. Chưa nên làm thuê bao: app không có chi phí máy chủ, người mua nhóm này ghét thuê bao.

## 5. Mô hình kinh doanh

| | A. Mã nguồn mở, bán bản chính thức | B. Tách lõi GPL, giao diện đóng | C. Miễn phí + ủng hộ |
|---|---|---|---|
| Cách làm | Giữ GPL. Bán bản đã ký trên Store; ai muốn miễn phí thì tự build | Xin tác giả gốc cấp phép thương mại (hoặc viết lại phần của họ); chạy FairPlay và pymobiledevice3 thành tiến trình GPL riêng | GitHub Sponsors |
| Công sức | Thấp | Cao (viết lại ~1.800 dòng UI/receiver hoặc đàm phán), cần luật sư | Gần 0 |
| Rủi ro | Có người phát lại bản miễn phí | Vùng xám GPL, vẫn còn rủi ro FairPlay | Gần như không có thu |
| Khi nào chọn | **Bây giờ** | Khi A đã có doanh thu đều và bị bản lậu ăn mất rõ rệt | Nếu chỉ muốn làm cho vui |

**Khuyến nghị: A.** Kiểm chứng xem có người trả tiền không trong 2–3 tháng rồi mới tính B.

**Kênh bán:**

1. **Microsoft Store (bắt đầu ở đây).** Đăng ký nhà phát triển cá nhân đã miễn phí từ 09/2025; gói
   MSIX được Microsoft ký miễn phí và tự cập nhật; Store có sẵn thanh toán và dùng thử. AirServer
   cũng bán ở đây. Cần kiểm tra: Store có trả tiền về tài khoản ở Việt Nam không, và mức phí.
2. **Bán trực tiếp (để sau).** Cần chứng thư ký số OV (vài trăm USD/năm – Azure Artifact Signing
   chưa nhận cá nhân ngoài Mỹ/Canada), một bên Merchant of Record (Paddle, Lemon Squeezy) lo thuế,
   và tự viết cập nhật + license. Chỉ làm khi Store đã chứng minh có nhu cầu.

## 6. Lộ trình

Ước lượng cho 1 người làm bán thời gian cùng Claude; con số chỉ để xếp thứ tự, không phải cam kết.

### Giai đoạn 0 – Kiểm chứng (khoảng 1 tuần)

- Thử với iPhone thật: ít nhất 3 máy / 3 phiên bản iOS khác nhau. Mirror 30 phút, xoay, khoá/mở,
  ghi hình, PC ngủ rồi thức, đổi Wi-Fi.
- Thử phần điều khiển USB theo README trên 1 máy; ghi lại từng chỗ bị kẹt.
- Đưa cho 5 người không rành kỹ thuật tự cài. Đếm số người cài xong không cần hỏi.
- Nhắn tác giả gốc (0xCodez): báo về fork, hỏi thái độ với việc bán bản build.
- **Xong khi:** mirror ổn định trên cả 3 máy; có danh sách lỗi thật; đã chọn mô hình (trang
  `chon-thuong-mai.html`).

### Giai đoạn 1 – Thành sản phẩm cài được (2–3 tuần)

1. **(Xong 10/11 – `build.bat`)** Đóng gói thành `PocketPane.exe` (PyInstaller, kèm sẵn Python và
   thư viện) → tường lửa hỏi đúng tên "PocketPane", không còn `pythonw.exe`, không tải gì lúc cài.
   Còn lại: giảm dung lượng (hiện 285 MB), icon và thông tin phiên bản cho file exe, bộ cài.
2. Gói MSIX cho Store: khai báo luật tường lửa (chỉ mạng Private) trong manifest; đổi "Start with
   Windows" từ registry Run sang StartupTask; kiểm tra đường dẫn `%LOCALAPPDATA%` và tiến trình
   con của điều khiển USB khi chạy trong gói.
3. Hộp thoại Cài đặt thay cho việc sửa `settings.json`.
4. Màn hình lần chạy đầu: tự kiểm tra mạng Private, tường lửa, cùng subnet, VPN – thay cho mục
   Troubleshooting dài trong README. Đây là nguồn yêu cầu hỗ trợ lớn nhất.
5. Tiếng Việt + tiếng Anh (Qt Linguist có sẵn trong PySide6).
6. Nút "Gửi báo cáo lỗi": đóng gói log thành file zip để người dùng tự gửi. Không thu thập tự động.
7. Icon, tên, ảnh chụp, khung điện thoại trung tính.
- **Xong khi:** máy Windows sạch cài từ một file, mirror được trong dưới 2 phút, không mở README.

### Giai đoạn 2 – Thu tiền (1–2 tuần)

1. Tài khoản Microsoft Store, hồ sơ thuế/thanh toán, đặt giá + dùng thử.
2. Trang giới thiệu 1 trang (video 30 giây, 3 ảnh, nút tới Store, FAQ).
3. EULA ngắn, chính sách riêng tư ("app không gửi dữ liệu đi đâu"), trang ghi công mã nguồn mở,
   chuyển repo sang public.
4. Kênh hỗ trợ: một địa chỉ email + GitHub Issues. Chưa cần hơn.
- **Xong khi:** người lạ mua được, cài được, và bạn nhận được tiền thử nghiệm.

### Giai đoạn 3 – Tính năng đáng tiền (4–6 tuần, làm theo thứ tự)

1. **Trình hướng dẫn cài điều khiển ngay trong app**: thay `control.bat` + 7 bước README bằng các
   màn hình "Tiếp theo", tự chạy `doctor`, tự nhắc trước khi chữ ký 7 ngày hết hạn.
2. **Kéo-thả trực tiếp và giảm trễ**: gửi chuỗi chạm liên tục thay vì gửi một lần khi thả chuột.
3. **Thử nghiệm 3 ngày: điều khiển qua Bluetooth** (PC giả làm chuột/bàn phím Bluetooth của
   iPhone → không cáp, không Developer Mode, không ký lại). Chưa chắc làm được: hệ điều hành
   thường giữ riêng dịch vụ HID. Nếu được thì đây là lợi thế lớn nhất; nếu không thì dừng.
4. **PIN AirPlay** – cần cho văn phòng, trường học (ai cùng Wi-Fi cũng chiếu lên được là lỗ hổng).
5. **Giải mã bằng GPU** (D3D11VA qua FFmpeg) và encoder phần cứng khi ghi hình.
6. **Ghi hình có khung máy**, cắt đầu/cuối, xuất GIF – cho nhóm làm nội dung.
- **Xong khi:** người mới bật được điều khiển trong 10 phút; tỉ lệ dùng thử → mua đo được.

### Giai đoạn 4 – Mở rộng (chỉ khi đã có doanh thu)

- Nhiều iPhone cùng lúc; iPad; H.265/4K.
- Android qua scrcpy (giấy phép Apache-2.0, kèm được) → "một app cho mọi điện thoại".
- Giấy phép theo nhóm cho trường học / công ty; bán trực tiếp ngoài Store; cân nhắc mô hình B.

## 7. Không làm

- Chống crack, làm rối mã, kiểm tra license online – vô ích dưới GPL.
- Hệ thống tài khoản, máy chủ riêng, đồng bộ đám mây.
- Vượt DRM (Netflix, Apple TV) – rủi ro pháp lý trực tiếp.
- Bản macOS/Linux – macOS đã có sẵn tính năng này, Linux đã có UxPlay.
- Thông báo iPhone trên PC, kéo thả file – không làm được qua AirPlay/WDA (đã ghi trong `PLAN.md`).
- Thu thập dữ liệu sử dụng tự động – app nhìn thấy màn hình điện thoại, người dùng rất nhạy cảm.

## 8. Chi phí và chỉ số

| Khoản | Chi phí |
|---|---|
| Microsoft Store | 0 đ đăng ký; phí trên mỗi đơn (cần kiểm tra mức hiện hành) |
| Tên miền + trang giới thiệu | khoảng 12 USD/năm, host tĩnh miễn phí |
| iPhone để thử | mượn; về lâu dài nên có 1 máy cũ chạy iOS cũ |
| Tư vấn luật | trước khi chi quảng cáo lớn hoặc chuyển sang mô hình B |

Mục tiêu 3 tháng sau khi lên Store: **100 người mua**, tỉ lệ dùng thử → mua trên 3%, dưới 1 yêu
cầu hỗ trợ cho mỗi 10 lượt cài. Không đạt 30 người mua thì dừng đầu tư thêm, giữ làm dự án mở.

## 9. Rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| iOS mới làm hỏng AirPlay hoặc WDA | Cao, lặp lại hằng năm | Thử bản beta iOS mỗi mùa hè; theo dõi UxPlay và pymobiledevice3; không hứa "hỗ trợ trọn đời" |
| Apple yêu cầu gỡ | Thấp–vừa | Mục 3.2; không phụ thuộc một kênh bán duy nhất về lâu dài |
| Có người phát lại miễn phí | Vừa | Chấp nhận; thắng bằng bản chính thức tiện hơn |
| Điều khiển quá khó cài → hoàn tiền | Cao | Giai đoạn 3 mục 1; mô tả trung thực trên Store rằng điều khiển cần cáp và cài thêm |
| MSIX không hợp với mDNS / USB / tự khởi động | Vừa | Thử sớm ở Giai đoạn 1 mục 2; phương án dự phòng là bộ cài thường + chứng thư OV |
| Một người làm, hỗ trợ quá tải | Vừa | Màn hình tự chẩn đoán mạng; FAQ; giới hạn phạm vi |

## 10. Việc của tuần này

1. Mở `chon-thuong-mai.html`, chọn và dán kết quả vào chat.
2. Thử mirror với iPhone thật và báo kết quả (kèm log nếu lỗi).
3. Claude bắt đầu Giai đoạn 1 mục 1: đóng gói `PocketPane.exe`.

## Nguồn tra cứu

- Giá Reflector 4: https://www.capterra.com/p/246704/Reflector-4/
- AirServer mua một lần: https://support.airserver.com/en/support/solutions/articles/43000512398
- ApowerMirror: https://www.getapp.com/collaboration-software/a/apowermirror
- iMyFone MirrorTo: https://www.sourceforge.net/software/product/iMyFone-MirrorTo
- Tenorshare Phone Mirror: https://www.filehorse.com/download-tenorshare-phone-mirror/
- Microsoft Store miễn phí đăng ký cá nhân: https://blogs.windows.com/windowsdeveloper/2025/09/10/free-developer-registration-for-individual-developers-on-microsoft-store/
- Azure Artifact Signing giới hạn quốc gia: https://learn.microsoft.com/azure/artifact-signing/quickstart
