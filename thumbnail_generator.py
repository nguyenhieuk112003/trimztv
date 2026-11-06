# -*- coding: utf-8 -*-
"""
================================================================================
AUTO ANIME THUMBNAIL GENERATOR (HIGH CTR 16:9 - 1280x720)
================================================================================
Tự động tạo ảnh Thumbnail chuẩn Review Anime bắt mắt với:
- Khung hình 1080p sắc nét trích xuất từ video hoặc ảnh poster gốc Trimz.tv
- Bộ lọc tăng cường màu sắc & độ tương phản cho anime
- Dải chuyển màu tối (Vignette gradient) bảo đảm chữ luôn nổi bật
- Nhãn thể loại (Category Pill Badge), Tên phim giật gân (Typography 3D viền đen)
- Huy hiệu số tập & độ phân giải (TẬP XX - YY | FULL HD)
================================================================================
"""

import os
import re
import sys
import subprocess
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Chọn font chữ Windows hỗ trợ tiếng Việt có dấu chuẩn xác
def get_system_font(size: int):
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


def extract_video_frame(ffmpeg_bin: str, video_path: str, out_frame_path: str, seek_sec: float = 30.0) -> bool:
    """Trích xuất 1 khung hình sắc nét từ video tại thời điểm seek_sec."""
    try:
        cmd = [
            ffmpeg_bin, "-y",
            "-ss", str(seek_sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_frame_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        return res.returncode == 0 and os.path.isfile(out_frame_path) and os.path.getsize(out_frame_path) > 1024
    except Exception as e:
        print(f"      [!] Lỗi trích xuất frame thumbnail: {e}")
        return False


def download_poster_image(poster_url: str, out_path: str) -> bool:
    """Tải ảnh poster chính thức từ Trimz.tv."""
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
    category_label: str = "TÓM TẮT ANIME",
    out_thumbnail_path: str = "thumbnail.jpg",
    poster_url: str = None
) -> str:
    """
    Tạo ảnh thumbnail 1280x720 hoàn chỉnh và lưu vào out_thumbnail_path.
    Trả về đường dẫn file ảnh thumbnail.
    """
    TARGET_W, TARGET_H = 1280, 720
    temp_frame = os.path.join(os.path.dirname(out_thumbnail_path) or ".", ".temp_thumb_raw.jpg")

    base_img = None

    # Cách 1: Thử trích xuất khung hình từ video (ở giây thứ 45 hoặc 20% video)
    if video_path and os.path.isfile(video_path):
        if extract_video_frame(ffmpeg_bin, video_path, temp_frame, seek_sec=45.0):
            try:
                base_img = Image.open(temp_frame).convert("RGB")
            except Exception:
                pass

    # Cách 2: Nếu không trích xuất được frame thì tải poster chính thức từ web
    if base_img is None and poster_url:
        if download_poster_image(poster_url, temp_frame):
            try:
                base_img = Image.open(temp_frame).convert("RGB")
            except Exception:
                pass

    # Cách 3: Fallback tạo hình nền gradient anime nếu cả 2 cách trên không có
    if base_img is None:
        base_img = Image.new("RGB", (TARGET_W, TARGET_H), color=(20, 24, 38))

    # Xóa file frame tạm
    if os.path.isfile(temp_frame):
        try:
            os.remove(temp_frame)
        except Exception:
            pass

    # 1. Căn chỉnh tỷ lệ 16:9 (Cover crop)
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

    # 2. Tăng cường độ tương phản và màu sắc anime
    enhancer_contrast = ImageEnhance.Contrast(base_img)
    base_img = enhancer_contrast.enhance(1.15)
    enhancer_color = ImageEnhance.Color(base_img)
    base_img = enhancer_color.enhance(1.20)

    # 3. Tạo lớp phủ dải chuyển màu tối (Dark gradient) phía dưới và phía trên
    overlay = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Gradient tối phía dưới (để chữ title nổi bật)
    for y in range(TARGET_H - 320, TARGET_H):
        alpha = int(220 * ((y - (TARGET_H - 320)) / 320.0))
        draw_overlay.line([(0, y), (TARGET_W, y)], fill=(0, 0, 0, alpha))

    # Gradient tối nhẹ phía trên (để badge category nổi bật)
    for y in range(0, 160):
        alpha = int(140 * (1.0 - (y / 160.0)))
        draw_overlay.line([(0, y), (TARGET_W, y)], fill=(0, 0, 0, alpha))

    base_img = Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base_img)

    # 4. Vẽ đường viền sáng bắt mắt bao quanh Thumbnail (Glow Border)
    border_color = (255, 77, 77)  # Đỏ cam rực rỡ
    border_width = 8
    draw.rectangle([(0, 0), (TARGET_W - 1, TARGET_H - 1)], outline=border_color, width=border_width)

    # 5. Vẽ nhãn Category Pill Badge (góc trên bên trái)
    cat_font = get_system_font(26)
    cat_text = f"● {category_label.upper()}"
    bbox_cat = draw.textbbox((0, 0), cat_text, font=cat_font)
    cat_w = bbox_cat[2] - bbox_cat[0]
    cat_h = bbox_cat[3] - bbox_cat[1]

    cat_x, cat_y = 36, 32
    pad_x, pad_y = 16, 8
    draw.rounded_rectangle(
        [(cat_x, cat_y), (cat_x + cat_w + pad_x * 2, cat_y + cat_h + pad_y * 2)],
        radius=12,
        fill=(229, 9, 20)  # Đỏ nổi bật
    )
    draw.text((cat_x + pad_x, cat_y + pad_y - 2), cat_text, fill=(255, 255, 255), font=cat_font)

    # 6. Vẽ Tiêu đề Anime (Typography 3D, viền đen dày, chữ vàng/trắng)
    title_lines = wrap_text(title.upper(), max_chars=22)
    title_font = get_system_font(56)

    # Tính toán tọa độ đặt tiêu đề (ở nửa dưới)
    start_y = TARGET_H - 260 if len(title_lines) > 1 else TARGET_H - 200
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
            fill=(255, 230, 0),  # Vàng rực rỡ
            font=title_font,
            stroke_width=6,
            stroke_fill=(0, 0, 0)
        )
        start_y += line_h + 18

    # 7. Vẽ Huy hiệu Số tập / Chất lượng (Góc dưới bên phải)
    badge_font = get_system_font(30)
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
        radius=14,
        fill=(255, 180, 0),
        outline=(0, 0, 0),
        width=3
    )
    draw.text((b_x + pad_bx, b_y + pad_by - 2), badge_str, fill=(0, 0, 0), font=badge_font)

    # 8. Lưu ảnh xuất bản chất lượng cao
    os.makedirs(os.path.dirname(os.path.abspath(out_thumbnail_path)), exist_ok=True)
    base_img.save(out_thumbnail_path, format="JPEG", quality=95)
    return out_thumbnail_path
