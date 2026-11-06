# -*- coding: utf-8 -*-
"""
================================================================================
AUTO ANIME THUMBNAIL GENERATOR (HIGH CTR 16:9 - 1280x720)
CÔNG CỤ TỰ ĐỘNG TẠO ẢNH BÌA THUMBNAIL BẮT MẮT TỪ CẢNH CAO TRÀO CỦA PHIM ANIME
================================================================================
1. Tự động quét và chọn lọc CẢNH CAO TRÀO (Climax Scene) gay cấn, mãn nhãn nhất:
   - Quét qua nhiều mốc thời gian chiến đấu, biến cố, cận cảnh nhân vật
   - Đánh giá Độ tương phản (Contrast), Độ rực rỡ màu sắc (Vibrancy Saturation), 
     và Mật độ chi tiết hành động (Edge Density) để chọn ra khung hình đỉnh cao nhất.
   - Tự động bỏ qua các cảnh tối đen (black fade) hoặc nhạt nhòa.
2. Bộ lọc Anime Vivid:
   - Tăng tương phản (+25%), độ rực rỡ màu sắc (+30%) và độ nét (+20%).
3. Bố cục High CTR chuẩn YouTube / Facebook Anime Review:
   - Cảnh cao trào anime ở trung tâm và bên phải hiển thị 100% độ sáng, sắc nét.
   - Lớp phủ tối chuyển màu mềm mại (Directional Vignette) ở góc dưới bên trái 
     để tên phim luôn nổi bật và dễ đọc.
   - Viền sáng Neon đỏ cam (Glow Border) bao quanh thumbnail.
   - Huy hiệu Thể loại (Category Pill Badge) và Huy hiệu Số tập (Episode Badge).
   - Tiêu đề Typography 3D tiếng Việt viền đen dày kết hợp đổ bóng sâu.
================================================================================
"""

import os
import re
import sys
import subprocess
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageStat

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_system_font(size: int):
    """Chọn font chữ Windows hỗ trợ tiếng Việt có dấu chuẩn xác."""
    candidates = [
        "C:\\Windows\\Fonts\\arialbd.ttf",      # Arial Bold (chuẩn nhất cho tiếng Việt)
        "C:\\Windows\\Fonts\\tahomabd.ttf",     # Tahoma Bold
        "C:\\Windows\\Fonts\\calibrib.ttf",     # Calibri Bold
        "C:\\Windows\\Fonts\\segoeuib.ttf",     # Segoe UI Bold
    ]
    for font_path in candidates:
        if os.path.isfile(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_video_duration(ffmpeg_bin: str, video_path: str) -> float:
    """Đo thời lượng video bằng FFmpeg."""
    try:
        cmd = [ffmpeg_bin, "-i", video_path]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
        if m:
            h, mins, s = map(float, m.groups())
            return h * 3600.0 + mins * 60.0 + s
    except Exception:
        pass
    return 0.0


def score_climax_frame(img: Image.Image) -> float:
    """
    Tính điểm hấp dẫn / cao trào của 1 khung hình anime:
    - Độ tương phản (contrast): Đánh giá tương phản sáng/tối gay cấn
    - Độ rực rỡ màu sắc (saturation): Màu anime tươi sáng, phép thuật, hiệu ứng
    - Mật độ chi tiết cạnh (edge density): Chi tiết hành động, biểu cảm khuôn mặt
    - Loại bỏ các khung hình tối đen hoặc bị mờ trắng (fade-in / fade-out)
    """
    try:
        stat = ImageStat.Stat(img)
        mean_lum = sum(stat.mean) / 3.0
        # Loại bỏ khung hình quá tối (<25) hoặc quá chói/trắng (>240)
        if mean_lum < 25.0 or mean_lum > 240.0:
            return -1.0

        std_dev = sum(stat.stddev) / 3.0
        hsv = img.convert("HSV")
        sat_mean = ImageStat.Stat(hsv).mean[1]
        edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
        edge_mean = ImageStat.Stat(edges).mean[0]

        # Điểm cao trào tổng hợp (Climax Score)
        return (std_dev * 0.35) + (sat_mean * 0.35) + (edge_mean * 0.30)
    except Exception:
        return 0.0


def extract_best_climax_frame(ffmpeg_bin: str, video_path: str, out_frame_path: str, show_dir: str = None) -> bool:
    """
    Tự động dò tìm và trích xuất CẢNH CAO TRÀO gay cấn nhất từ video:
    - Quét qua 8 - 12 mốc thời gian trải đều theo các phân cảnh kịch tính
    - Chấm điểm từng khung hình và chọn ra cảnh đẹp nhất
    - Nếu video_path chưa tồn tại, tự động tìm kiếm các tập video nguồn trong show_dir
    """
    target_video = None
    if video_path and os.path.isfile(video_path) and os.path.getsize(video_path) > 102400:
        target_video = video_path
    elif show_dir and os.path.isdir(show_dir):
        # Tìm các video Tap_*.mp4 trong thư mục phim
        for fname in sorted(os.listdir(show_dir)):
            if re.match(r"^Tap_\d+\.mp4$", fname, re.IGNORECASE):
                f_p = os.path.join(show_dir, fname)
                if os.path.isfile(f_p) and os.path.getsize(f_p) > 102400:
                    target_video = f_p
                    break

    if not target_video:
        return False

    duration = get_video_duration(ffmpeg_bin, target_video)
    if duration <= 1.0:
        duration = 30.0

    # Phân bổ các mốc lấy mẫu ở các đoạn cao trào (giữa và gần cuối video)
    ratios = [0.18, 0.30, 0.45, 0.58, 0.70, 0.78, 0.85, 0.92]
    candidate_times = [max(1.0, min(duration - 1.0, duration * r)) for r in ratios]

    best_score = -1.0
    best_img = None
    temp_extract = out_frame_path + ".temp_seek.jpg"

    for t_sec in candidate_times:
        try:
            cmd = [
                ffmpeg_bin, "-y",
                "-ss", f"{t_sec:.2f}",
                "-i", target_video,
                "-vframes", "1",
                "-q:v", "2",
                temp_extract
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.isfile(temp_extract) and os.path.getsize(temp_extract) > 2048:
                cur_img = Image.open(temp_extract).convert("RGB")
                score = score_climax_frame(cur_img)
                if score > best_score:
                    best_score = score
                    if best_img:
                        best_img.close()
                    best_img = cur_img.copy()
                cur_img.close()
        except Exception:
            continue
        finally:
            if os.path.isfile(temp_extract):
                try:
                    os.remove(temp_extract)
                except Exception:
                    pass

    if best_img:
        best_img.save(out_frame_path, format="JPEG", quality=95)
        best_img.close()
        return True

    return False


def download_poster_image(poster_url: str, out_path: str) -> bool:
    """Tải ảnh poster chính thức từ Trimz.tv làm phương án dự phòng."""
    if not poster_url:
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(poster_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp, open(out_path, "wb") as f:
            f.write(resp.read())
        return os.path.isfile(out_path) and os.path.getsize(out_path) > 2048
    except Exception:
        return False


def wrap_text(text: str, max_chars: int = 24) -> list:
    """Chia nhỏ tiêu đề dài thành tối đa 2 dòng cân đối."""
    words = text.strip().split()
    if not words:
        return []
    lines = []
    cur = []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) >= max_chars and len(lines) < 1:
            lines.append(" ".join(cur))
            cur = []
    if cur:
        lines.append(" ".join(cur))
    return lines[:2]


def generate_anime_thumbnail(
    ffmpeg_bin: str,
    video_path: str,
    title: str,
    badge_text: str = "TẬP 1 - FULL HD",
    category_label: str = "REVIEW ANIME",
    out_thumbnail_path: str = "thumbnail.jpg",
    poster_url: str = None
) -> str:
    """
    Tạo ảnh thumbnail 1280x720 hoàn chỉnh lấy từ CẢNH CAO TRÀO của video.
    """
    TARGET_W, TARGET_H = 1280, 720
    out_dir = os.path.dirname(os.path.abspath(out_thumbnail_path))
    os.makedirs(out_dir, exist_ok=True)
    temp_frame = os.path.join(out_dir, f".temp_climax_{os.path.basename(out_thumbnail_path)}")

    base_img = None

    # Thư mục gốc chứa video (dùng để tìm các tập ngắn nếu video ghép chưa xong)
    show_dir = os.path.dirname(os.path.abspath(video_path)) if video_path else out_dir
    parent_dir = os.path.dirname(show_dir)

    # 1. Trích xuất CẢNH CAO TRÀO từ video thành phẩm hoặc các tập nguồn
    if extract_best_climax_frame(ffmpeg_bin, video_path, temp_frame, show_dir=show_dir):
        try:
            base_img = Image.open(temp_frame).convert("RGB")
        except Exception:
            pass

    # Nếu chưa tìm thấy trong show_dir, thử quét thư mục cha (Downloads/<Tên_Phim>)
    if base_img is None and parent_dir and os.path.isdir(parent_dir):
        if extract_best_climax_frame(ffmpeg_bin, None, temp_frame, show_dir=parent_dir):
            try:
                base_img = Image.open(temp_frame).convert("RGB")
            except Exception:
                pass

    # 2. Nếu không trích xuất được từ video thì tải ảnh Poster chính thức từ web Trimz
    if base_img is None and poster_url:
        if download_poster_image(poster_url, temp_frame):
            try:
                base_img = Image.open(temp_frame).convert("RGB")
            except Exception:
                pass

    # 3. Fallback: Nếu hoàn toàn không có video hay ảnh thì tạo nền gradient
    if base_img is None:
        base_img = Image.new("RGB", (TARGET_W, TARGET_H), color=(20, 24, 38))

    # Xóa file tạm
    if os.path.isfile(temp_frame):
        try:
            os.remove(temp_frame)
        except Exception:
            pass

    # --- BƯỚC 1: Căn chỉnh tỷ lệ 16:9 (Cover crop) ---
    img_w, img_h = base_img.size
    target_ratio = TARGET_W / TARGET_H
    img_ratio = img_w / img_h

    if img_ratio > target_ratio:
        new_w = int(img_h * target_ratio)
        left = (img_w - new_w) // 2
        base_img = base_img.crop((left, 0, left + new_w, img_h))
    else:
        new_h = int(img_w / target_ratio)
        top = (img_h - new_h) // 2
        base_img = base_img.crop((0, top, img_w, top + new_h))

    base_img = base_img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)

    # --- BƯỚC 2: Tăng cường rực rỡ màu sắc & độ tương phản phong cách Anime Vivid ---
    base_img = ImageEnhance.Contrast(base_img).enhance(1.25)
    base_img = ImageEnhance.Color(base_img).enhance(1.30)
    base_img = ImageEnhance.Sharpness(base_img).enhance(1.20)

    # --- BƯỚC 3: Lớp phủ tối chuyển màu mềm mại (Directional Vignette) ---
    # Chỉ làm tối vùng đặt chữ (góc dưới bên trái), giữ 100% độ sáng cho cảnh nhân vật bên phải!
    overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))

    # Gradient đáy bên trái (nơi hiển thị tiêu đề)
    for y in range(TARGET_H - 300, TARGET_H):
        alpha_y = ((y - (TARGET_H - 300)) / 300.0)
        for x in range(0, TARGET_W):
            alpha_x = max(0.0, 1.0 - (x / 900.0))
            final_alpha = int(220 * alpha_y * alpha_x)
            if final_alpha > 0:
                overlay.putpixel((x, y), (0, 0, 0, final_alpha))

    # Gradient góc trên bên trái (nơi hiển thị nhãn thể loại)
    for y in range(0, 120):
        alpha_y = 1.0 - (y / 120.0)
        for x in range(0, 400):
            alpha_x = 1.0 - (x / 400.0)
            final_alpha = int(140 * alpha_y * alpha_x)
            if final_alpha > 0:
                overlay.putpixel((x, y), (0, 0, 0, final_alpha))

    base_img = Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base_img)

    # --- BƯỚC 4: Vẽ đường viền sáng bắt mắt bao quanh Thumbnail (Glow Border) ---
    border_color = (255, 60, 60)  # Đỏ cam rực rỡ phong cách anime
    border_width = 8
    draw.rectangle([(0, 0), (TARGET_W - 1, TARGET_H - 1)], outline=border_color, width=border_width)

    # --- BƯỚC 5: Vẽ nhãn Category Pill Badge (góc trên bên trái) ---
    cat_font = get_system_font(26)
    cat_text = f"● {category_label.upper()}"
    bbox_cat = draw.textbbox((0, 0), cat_text, font=cat_font)
    cat_w = bbox_cat[2] - bbox_cat[0]
    cat_h = bbox_cat[3] - bbox_cat[1]

    cat_x, cat_y = 36, 32
    pad_x, pad_y = 18, 8
    draw.rounded_rectangle(
        [(cat_x, cat_y), (cat_x + cat_w + pad_x * 2, cat_y + cat_h + pad_y * 2)],
        radius=12,
        fill=(229, 9, 20)  # Đỏ nổi bật
    )
    draw.text((cat_x + pad_x, cat_y + pad_y - 2), cat_text, fill=(255, 255, 255), font=cat_font)

    # --- BƯỚC 6: Vẽ Huy hiệu Số tập / Chất lượng (Góc dưới bên phải) ---
    badge_font = get_system_font(28)
    badge_str = badge_text.upper()
    bbox_b = draw.textbbox((0, 0), badge_str, font=badge_font)
    b_w = bbox_b[2] - bbox_b[0]
    b_h = bbox_b[3] - bbox_b[1]

    pad_bx, pad_by = 20, 10
    total_bw = b_w + pad_bx * 2
    total_bh = b_h + pad_by * 2
    b_x = TARGET_W - total_bw - 36
    b_y = TARGET_H - total_bh - 32

    # Nền badge vàng cam với viền đen
    draw.rounded_rectangle(
        [(b_x, b_y), (b_x + total_bw, b_y + total_bh)],
        radius=12,
        fill=(255, 185, 0),
        outline=(0, 0, 0),
        width=3
    )
    draw.text((b_x + pad_bx, b_y + pad_by - 2), badge_str, fill=(0, 0, 0), font=badge_font)

    # --- BƯỚC 7: Vẽ Tiêu đề Anime (Typography 3D, viền đen dày, chữ vàng rực rỡ) ---
    title_lines = wrap_text(title.upper(), max_chars=22)
    title_font = get_system_font(54)

    start_y = TARGET_H - 240 if len(title_lines) > 1 else TARGET_H - 180
    for line in title_lines:
        line_bbox = draw.textbbox((0, 0), line, font=title_font)
        line_h = line_bbox[3] - line_bbox[1]
        line_x = 36

        # Hiệu ứng đổ bóng 3D
        draw.text((line_x + 4, start_y + 4), line, fill=(0, 0, 0), font=title_font)
        # Chữ chính viền đen dày
        draw.text(
            (line_x, start_y),
            line,
            fill=(255, 235, 0),  # Vàng rực rỡ
            font=title_font,
            stroke_width=6,
            stroke_fill=(0, 0, 0)
        )
        start_y += line_h + 18

    # --- BƯỚC 8: Lưu ảnh xuất bản chất lượng cao 95% ---
    base_img.save(out_thumbnail_path, format="JPEG", quality=95)
    return out_thumbnail_path
