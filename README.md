# HỆ THỐNG TỰ ĐỘNG HÓA TẢI, XÓA LOGO & GHÉP VIDEO TRIMZ.TV (AUTO CRON JOB)

Hệ thống con job tự động hóa toàn diện giúp:
1. **Tự động quét & lấy video**: Tự động cào toàn bộ các bộ phim mới trên trang chủ [Trimz.tv](https://trimz.tv) kết hợp đọc danh sách phim do bạn chỉ định từ file `danh_sach_phim.txt`.
2. **Tự động xóa / làm mờ logo**: Tích hợp bộ lọc FFmpeg `delogo` loại bỏ watermark/logo mà không làm mất góc nhìn của video. Có thể chỉnh vị trí góc (trên-phải, dưới-phải, tùy chỉnh pixel) hoặc tắt/bật tùy ý.
3. **Tự động ghép video tối đa 40 phút**: Sau khi tải và xóa logo, hệ thống tự động tính toán thời lượng từng tập và ghép các tập lại với nhau thành các phần (Part 1, Part 2...) với **thời lượng mỗi video tối đa 40 phút** (chuẩn tỷ lệ vàng đăng YouTube). Nếu toàn bộ phim dưới 40 phút, tất cả sẽ được ghép thành 1 video Full duy nhất.
4. **Tự động phân loại thư mục**:
   - Các tập riêng lẻ sau khi xóa logo lưu tại: `Downloads/<Tên_Phim>/Tap_001.mp4`, `Tap_002.mp4`...
   - Các video ghép hoàn chỉnh sẵn sàng đăng YouTube lưu tại: `Downloads/<Tên_Phim>/Ghep_Video/<Tên_Phim>_Part_01_Tap_001-004.mp4`...
5. **Cơ chế chống trùng lặp (Deduplication)**: Lưu vết toàn bộ video đã tải vào file `history.json` và kiểm tra timestamp file ghép. Tuyệt đối không tải lại hoặc ghép lại các file đã xử lý.
6. **Vận hành ngầm định kỳ**: Tự động lặp lại theo chu kỳ định sẵn (mặc định: 30 phút một lần) kèm đồng hồ đếm ngược trực quan.

---

## 🚀 HƯỚNG DẪN SỬ DỤNG NHANH

### Cách 1: Chạy vòng lặp tự động định kỳ (Khuyên dùng)
- Click đúp vào file **`Chay_Job_Tu_Dong.bat`**.
- Job sẽ bắt đầu quét trang chủ Trimz.tv và file danh sách, tự động tải các tập phim mới, xóa logo và **tự động ghép video tối đa 40 phút** vào thư mục `Ghep_Video`.
- Sau khi xong 1 chu kỳ, màn hình sẽ hiển thị đồng hồ đếm ngược và tự động chạy lại ở chu kỳ tiếp theo (bấm `Ctrl + C` để dừng an toàn).

### Cách 2: Chạy kiểm tra 1 lần duy nhất
- Click đúp vào file **`Chay_Job_1_Lan.bat`** (hoặc chạy lệnh: `python TrimzAutoJob.py --once`).

### Cách 3: Ghép ngay các video đã tải (Không cần tải lại)
- Click đúp vào file **`Ghep_Video_Da_Tai.bat`** (hoặc chạy lệnh: `python TrimzAutoJob.py --merge-only`).
- Hệ thống sẽ quét toàn bộ các phim đã tải trong thư mục `Downloads/` và ghép lại thành các video tối đa 40 phút ngay lập tức.

### Cách 4: Tải siêu tốc không re-encode (Giữ nguyên video gốc & ghép)
- Click đúp vào file **`Chay_Job_Khong_Xoa_Logo.bat`** (hoặc chạy lệnh: `python TrimzAutoJob.py --no-delogo`).
- Tốc độ tải về sẽ đạt tối đa băng thông mạng vì không cần xử lý FFmpeg delogo.

---

## ⚙️ CẤU HÌNH HỆ THỐNG (`config.json`)

Bạn có thể mở file `config.json` để tùy chỉnh thông số theo nhu cầu:

```json
{
  "check_interval_minutes": 30,
  "crawl_homepage": true,
  "custom_urls_file": "danh_sach_phim.txt",
  "output_dir": "Downloads",
  "delogo": {
    "enabled": true,
    "position": "top-right",
    "custom_box": {
      "x": 0,
      "y": 0,
      "w": 0,
      "h": 0
    }
  },
  "merge": {
    "enabled": true,
    "max_duration_minutes": 40,
    "output_folder": "Ghep_Video"
  },
  "max_episodes_per_show": 0
}
```

### Giải thích các tham số:
- `check_interval_minutes`: Thời gian nghỉ giữa các chu kỳ quét (tính bằng phút).
- `crawl_homepage`: `true` nếu muốn tự động quét tất cả các phim mới xuất hiện trên trang chủ Trimz.tv.
- `custom_urls_file`: Đường dẫn file chứa các link phim chỉ định (`danh_sach_phim.txt`).
- `output_dir`: Tên thư mục gốc lưu các tập phim tải về (`Downloads`).
- `delogo`:
  - `enabled`: `true` để bật tính năng xóa logo, `false` để tắt.
  - `position`: Vị trí đặt logo cần xóa (`"top-right"`, `"bottom-right"`, `"top-left"`, `"bottom-left"`, `"custom"`).
- `merge`:
  - `enabled`: `true` để tự động ghép các tập video lại với nhau, `false` để tắt.
  - `max_duration_minutes`: Thời lượng tối đa cho mỗi video sau khi ghép (mặc định: `40` phút).
  - `output_folder`: Thư mục con lưu trữ video ghép (mặc định: `"Ghep_Video"`).
- `max_episodes_per_show`: Giới hạn số tập cần tải cho mỗi bộ phim (`0` = tải tất cả các tập).

---

## 📁 CẤU TRÚC FILE VÀ THƯ MỤC

- `TrimzAutoJob.py`: Mã nguồn Python cốt lõi của con job tự động.
- `config.json`: Cấu hình chu kỳ, chế độ xóa logo, ghép video, thư mục lưu.
- `danh_sach_phim.txt`: Danh sách các link phim Trimz cần tải thêm theo ý muốn.
- `history.json`: Ghi nhận các video đã xử lý để tránh tải trùng lặp.
- `Downloads/`: Nơi lưu trữ video sau khi tải và xử lý:
  - `Downloads/<Tên_Phim>/Tap_001.mp4`: Các tập riêng lẻ đã xóa logo.
  - `Downloads/<Tên_Phim>/Ghep_Video/`: Các file video đã ghép hoàn chỉnh (tối đa 40 phút / file) sẵn sàng đăng YouTube.
- `Chay_Job_Tu_Dong.bat`: Phím tắt chạy con job lặp định kỳ trên Windows (Tải + Xóa logo + Ghép video).
- `Chay_Job_1_Lan.bat`: Phím tắt chạy quét 1 lần duy nhất.
- `Ghep_Video_Da_Tai.bat`: Phím tắt quét và ghép các video đã tải trong máy thành các phần tối đa 40 phút.
- `Chay_Job_Khong_Xoa_Logo.bat`: Phím tắt chạy tải video gốc tốc độ cao.
