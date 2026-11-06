"""
================================================================================
TRIMZ.TV AUTO CRON JOB - HỆ THỐNG TỰ ĐỘNG TẢI, XÓA LOGO & GHÉP VIDEO
================================================================================
- Tự động quét phim mới từ trang chủ Trimz.tv & danh sách trong 'danh_sach_phim.txt'
- Tự động tạo thư mục riêng cho từng bộ phim trong thư mục 'Downloads'
- Tự động xóa/làm mờ logo (delogo) bằng FFmpeg theo vị trí tùy chỉnh
- Tự động ghép các tập video thành các video hoàn chỉnh tối đa 40 phút (chuẩn YouTube)
- Lưu lịch sử vào 'history.json' để không tải lại các tập đã xử lý
- Chạy ngầm định kỳ theo chu kỳ (mặc định: 30 phút / lần)
================================================================================
"""

import os
import sys
import re
import json
import time
import argparse
import subprocess
import urllib.request
import urllib.error
import html as html_lib
from datetime import datetime

# Đảm bảo console UTF-8 trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
DEFAULT_CUSTOM_FILE = os.path.join(BASE_DIR, "danh_sach_phim.txt")

# Thư mục và file nhật ký hoạt động để truy vết (Tracing log)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "auto_job.log")

def log_event(message: str, level: str = "INFO"):
    """Ghi vết sự kiện có thời gian vào logs/auto_job.log để dễ truy vết."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_msg = message.strip()
    if clean_msg:
        line = f"[{now_str}] [{level.upper():7s}] {clean_msg}\n"
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as lf:
                lf.write(line)
        except Exception:
            pass

def cleanup_merged_source_episodes(episode_list: list, merged_video_name: str, config: dict):
    """Tự động xóa các tập video ngắn nguồn sau khi đã ghép thành công vào video dài."""
    if not config.get("cleanup_source_episodes", True):
        return
    freed_bytes = 0
    deleted_count = 0
    for ep in episode_list:
        ep_path = ep.get("path")
        if ep_path and os.path.isfile(ep_path):
            try:
                sz = os.path.getsize(ep_path)
                os.remove(ep_path)
                freed_bytes += sz
                deleted_count += 1
            except Exception as e_del:
                log_event(f"Không thể xóa file ngắn {os.path.basename(ep_path)}: {e_del}", level="WARN")
    if deleted_count > 0:
        mb_freed = freed_bytes / (1024 * 1024)
        msg_clean = f"🧹 [DỌN DẸP Ổ CỨNG] Đã tự động xóa {deleted_count} video ngắn nguồn ({mb_freed:.1f} MB) sau khi ghép thành công {merged_video_name}"
        print(f"      {msg_clean}")
        log_event(msg_clean, level="CLEAN")

# Tìm công cụ FFmpeg khả dụng
def get_ffmpeg_exe() -> str:
    # 1. Thư mục tools nội bộ
    local_tool = os.path.join(BASE_DIR, "tools", "ffmpeg", "ffmpeg.exe")
    if os.path.isfile(local_tool):
        return local_tool
    
    # 2. Thư viện imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.isfile(exe):
            return exe
    except Exception:
        pass
    
    # 3. Biến môi trường PATH
    return "ffmpeg"


def sanitize_filename(name: str) -> str:
    """Loại bỏ ký tự cấm của Windows khỏi tên thư mục/file."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name)
    return re.sub(r'\s+', ' ', clean).strip()


def load_config() -> dict:
    default_config = {
        "check_interval_minutes": 30,
        "crawl_homepage": True,
        "custom_urls_file": "danh_sach_phim.txt",
        "output_dir": "Downloads",
        "cleanup_source_episodes": True,
        "delogo": {
            "enabled": True,
            "position": "top-right",
            "custom_box": {"x": 0, "y": 0, "w": 0, "h": 0}
        },
        "merge": {
            "enabled": True,
            "max_duration_minutes": 40,
            "output_folder": "Ghep_Video"
        },
        "ai_recap": {
            "enabled": True,
            "api_key": "",
            "model": "gemini-1.5-flash",
            "languages": ["vi", "en"],
            "voice_vi": "vi-VN-NamMinhNeural",
            "voice_en": "en-US-ChristopherNeural",
            "ducking_bgm_volume": 0.15,
            "ducking_voice_volume": 1.25
        },
        "youtube_upload": {
            "enabled": False,
            "client_secrets_file": "client_secrets.json",
            "token_file": "token.json",
            "privacy_status": "unlisted",
            "category_id": "1"
        },
        "max_episodes_per_show": 0
    }
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_config.update(data)
                if "delogo" in data and isinstance(data["delogo"], dict):
                    default_config["delogo"].update(data["delogo"])
                if "merge" in data and isinstance(data["merge"], dict):
                    default_config["merge"].update(data["merge"])
                if "ai_recap" in data and isinstance(data["ai_recap"], dict):
                    default_config["ai_recap"].update(data["ai_recap"])
                if "youtube_upload" in data and isinstance(data["youtube_upload"], dict):
                    default_config["youtube_upload"].update(data["youtube_upload"])
                if "channels_distribution" in data and isinstance(data["channels_distribution"], dict):
                    default_config["channels_distribution"] = data["channels_distribution"]
        except Exception as e:
            print(f"[!] Lỗi đọc file config.json: {e}. Dùng cấu hình mặc định.")
    else:
        save_config(default_config)
    return default_config


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def update_summary_tracker(history: dict):
    """Ghi bảng tóm tắt tiến độ các phim ra file logs/lich_su_tai_phim.txt để xem nhanh."""
    summary_file = os.path.join(LOG_DIR, "lich_su_tai_phim.txt")
    shows = history.get("shows", {})
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 70,
        f"  BẢNG TIẾN ĐỘ TẢI TẬP PHIM TRIMZ.TV (Cập nhật: {now_str})",
        "=" * 70,
    ]
    if not shows:
        lines.append("  Chưa có dữ liệu phim nào được tải.")
    else:
        for idx, (title, sinfo) in enumerate(shows.items(), start=1):
            last_ep = sinfo.get("last_downloaded_episode", 0)
            total_eps = sinfo.get("total_episodes_found", 0)
            status = "Hoàn tất" if last_ep >= total_eps and total_eps > 0 else "Đang cập nhật"
            updated = sinfo.get("last_updated", "")
            lines.append(f"  {idx:02d}. Phim: \"{title}\"")
            lines.append(f"      - Tiến độ: Đã tải đến tập {last_ep:03d} / {total_eps:03d} tập ({status})")
            lines.append(f"      - Link gốc: {sinfo.get('url', '')}")
            lines.append(f"      - Cập nhật lần cuối: {updated}")
            lines.append("-" * 70)
    lines.append("=" * 70)
    try:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


def load_history() -> dict:
    if os.path.isfile(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                h = json.load(f)
                if "shows" not in h:
                    h["shows"] = {}
                if "processed_urls" not in h:
                    h["processed_urls"] = []
                return h
        except Exception:
            pass
    return {"processed_urls": [], "shows": {}, "last_check": ""}


def save_history(history: dict):
    history["last_check"] = datetime.now().isoformat()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    update_summary_tracker(history)


def fetch_url(url: str, timeout: int = 15) -> str:
    """Tải mã nguồn HTML của trang web kèm giả lập User-Agent."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def get_video_dimensions(file_path: str):
    """Lấy chiều rộng và chiều cao của video bằng OpenCV hoặc fallback."""
    try:
        import cv2
        cap = cv2.VideoCapture(file_path)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return 1280, 720


def get_video_duration(ffmpeg_bin: str, file_path: str) -> float:
    """Lấy thời lượng (tính bằng giây) của video qua OpenCV hoặc FFmpeg."""
    try:
        import cv2
        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        if fps > 0 and frames > 0:
            dur = frames / fps
            if dur > 0:
                return float(dur)
    except Exception:
        pass

    try:
        cmd = [ffmpeg_bin, "-i", file_path]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
        if m:
            h, mins, s = map(float, m.groups())
            return h * 3600.0 + mins * 60.0 + s
    except Exception:
        pass

    return 0.0


def download_file(url: str, dest_path: str):
    """Tải video qua stream với thanh hiển thị tiến độ tải."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 512
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                percent = downloaded / total * 100
                mb_cur = downloaded / (1024 * 1024)
                mb_tot = total / (1024 * 1024)
                print(f"\r      -> Tải file: {percent:5.1f}% [{mb_cur:5.1f}/{mb_tot:5.1f} MB]", end="", flush=True)
        print()


def apply_delogo(ffmpeg_bin: str, input_path: str, output_path: str, delogo_cfg: dict) -> bool:
    """Xóa / làm mờ logo bằng bộ lọc delogo của FFmpeg."""
    width, height = get_video_dimensions(input_path)
    pos = delogo_cfg.get("position", "top-right").lower()
    custom_box = delogo_cfg.get("custom_box", {})

    # Tính toán tọa độ và kích thước vùng logo
    if pos == "custom" and custom_box.get("w", 0) > 0 and custom_box.get("h", 0) > 0:
        x = custom_box.get("x", 0)
        y = custom_box.get("y", 0)
        w = custom_box.get("w", 120)
        h = custom_box.get("h", 40)
    elif pos == "bottom-right":
        w = max(60, int(width * 0.16))
        h = max(30, int(height * 0.08))
        x = max(0, width - w - 16)
        y = max(0, height - h - 16)
    elif pos == "bottom-left":
        w = max(60, int(width * 0.16))
        h = max(30, int(height * 0.08))
        x = 16
        y = max(0, height - h - 16)
    elif pos == "top-left":
        w = max(60, int(width * 0.16))
        h = max(30, int(height * 0.08))
        x = 16
        y = 16
    else:  # top-right (mặc định)
        w = max(60, int(width * 0.16))
        h = max(30, int(height * 0.08))
        x = max(0, width - w - 16)
        y = 16

    filter_str = f"delogo=x={x}:y={y}:w={w}:h={h}:show=0"
    print(f"      -> Đang xóa logo (vị trí {pos}: x={x}, y={y}, w={w}, h={h})...")

    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_path,
        "-vf", filter_str,
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "faster",
        "-c:a", "copy",
        output_path
    ]

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 10240:
        return True
    else:
        print(f"      [!] Lỗi khi chạy FFmpeg delogo: {res.stderr[:200]}")
        return False


def discover_homepage_shows() -> list:
    """Tự động cào danh sách các bộ phim mới trên trang chủ Trimz.tv."""
    shows = []
    try:
        html = fetch_url("https://trimz.tv", timeout=15)
        slugs = set(re.findall(r'href=["\'](/[\w\-]+)["\']', html))
        ignored = (
            "/_", "/api", "/terms", "/privacy", "/login", "/signup",
            "/create", "/about", "/account", "/ai-anime", "/blog", "/pricing"
        )
        for s in sorted(slugs):
            if not s.startswith(ignored) and len(s) > 4:
                shows.append(f"https://trimz.tv{s}")
    except Exception as e:
        print(f"[!] Lỗi khi quét trang chủ Trimz.tv: {e}")
    return shows


def get_custom_shows(file_path: str) -> list:
    """Đọc danh sách phim chỉ định từ file text."""
    shows = []
    full_path = os.path.join(BASE_DIR, file_path) if not os.path.isabs(file_path) else file_path
    if not os.path.isfile(full_path):
        return shows
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if not line.startswith("http"):
                        line = "https://trimz.tv/" + line.lstrip("/")
                    shows.append(line)
    except Exception as e:
        print(f"[!] Lỗi đọc {file_path}: {e}")
    return shows


def extract_show_episodes(show_url: str):
    """Lấy tiêu đề phim và danh sách URL video MP4 từng tập."""
    try:
        html = fetch_url(show_url, timeout=15)
    except Exception as e:
        print(f"  [X] Không thể kết nối tới {show_url}: {e}")
        return None

    # Lấy tiêu đề phim
    title_match = re.search(r'<title>([^<]+)</title>', html)
    raw_title = title_match.group(1) if title_match else show_url.rstrip("/").split("/")[-1]
    raw_title = raw_title.split(" - Trimz")[0].split(" | Trimz")[0].split(": Watch & Create")[0].replace("Watch ", "").strip()
    safe_title = sanitize_filename(raw_title)

    # Lấy cốt truyện / mô tả phim
    desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
    if not desc_match:
        desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
    raw_desc = desc_match.group(1) if desc_match else ""
    clean_desc = html_lib.unescape(raw_desc)
    clean_desc = re.sub(r'Watch .*? on Trimz[ \t–—\-]*', '', clean_desc).strip()

    # Tìm các link MP4
    mp4_pattern = r'https://cdn\.trimz\.co/generated-videos/ms_videos/[a-zA-Z0-9_\-]+\.mp4'
    found_urls = re.findall(mp4_pattern, html)
    
    # Loại bỏ trùng lặp và giữ nguyên thứ tự
    unique_urls = []
    seen = set()
    for u in found_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    return {
        "url": show_url,
        "title": safe_title,
        "description": clean_desc,
        "episodes": unique_urls
    }


def process_single_show(show_url: str, config: dict, history: dict, ffmpeg_bin: str) -> int:
    """Tải và xóa logo cho các tập mới của một bộ phim."""
    info = extract_show_episodes(show_url)
    if not info:
        return 0

    episodes = info["episodes"]
    if not episodes:
        print(f"  [-] Phim: \"{info['title']}\" (Không tìm thấy link MP4 nào)")
        return 0

    # Giới hạn số tập nếu có cài đặt
    max_ep = config.get("max_episodes_per_show", 0)
    if max_ep > 0:
        episodes = episodes[:max_ep]

    # Thư mục riêng cho phim này
    out_base = os.path.join(BASE_DIR, config.get("output_dir", "Downloads"))
    show_dir = os.path.join(out_base, info["title"])
    os.makedirs(show_dir, exist_ok=True)

    # Lưu metadata của phim (tiêu đề, cốt truyện, URL) vào thư mục phim
    info_file = os.path.join(show_dir, "info.json")
    try:
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump({
                "title": info["title"],
                "description": info.get("description", ""),
                "url": show_url
            }, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    delogo_cfg = config.get("delogo", {})
    delogo_enabled = delogo_cfg.get("enabled", True)

    processed_set = set(history.get("processed_urls", []))
    new_downloaded = 0

    # Khởi tạo hoặc lấy bản ghi tiến độ tải của phim trong history
    show_rec = history.setdefault("shows", {}).setdefault(info["title"], {
        "url": show_url,
        "last_downloaded_episode": 0,
        "downloaded_episodes": [],
        "total_episodes_found": len(episodes),
        "last_updated": ""
    })
    show_rec["total_episodes_found"] = len(episodes)
    show_rec["url"] = show_url

    already_eps = [i for i, u in enumerate(episodes, start=1) if u in processed_set]
    new_eps = [i for i, u in enumerate(episodes, start=1) if u not in processed_set]

    # Đồng bộ các tập đã tải trước đó vào show_rec nếu chưa có
    for ep_num in already_eps:
        if ep_num not in show_rec["downloaded_episodes"]:
            show_rec["downloaded_episodes"].append(ep_num)
    if show_rec["downloaded_episodes"]:
        show_rec["downloaded_episodes"].sort()
        show_rec["last_downloaded_episode"] = max(show_rec["downloaded_episodes"])

    print(f"\n🎬 PHIM: \"{info['title']}\" ({len(episodes)} tập)")
    print(f"   📁 Thư mục lưu: {show_dir}")

    if not new_eps:
        last_ep = show_rec["last_downloaded_episode"]
        print(f"   ℹ️ ĐÃ TẢI ĐỦ: Đã tải đến tập {last_ep:03d}/{len(episodes):03d} (Không có tập mới cần tải).")
        log_event(f"Phim '{info['title']}': Đã tải đủ đến tập {last_ep:03d}/{len(episodes):03d} (Không có tập mới)", level="SKIP")
    else:
        last_done = show_rec["last_downloaded_episode"]
        print(f"   🔥 PHÁT HIỆN {len(new_eps)} TẬP MỚI: Tải từ tập {min(new_eps):03d} -> {max(new_eps):03d} (Đã có đến tập {last_done:03d})")
        log_event(f"Phim '{info['title']}': Phát hiện {len(new_eps)} tập mới (từ tập {min(new_eps):03d} đến {max(new_eps):03d})", level="INFO")

    def record_episode_success(ep_idx: int, f_path: str, v_u: str):
        nonlocal new_downloaded
        sz_mb = os.path.getsize(f_path) / (1024 * 1024) if os.path.isfile(f_path) else 0
        if ep_idx not in show_rec["downloaded_episodes"]:
            show_rec["downloaded_episodes"].append(ep_idx)
            show_rec["downloaded_episodes"].sort()
        show_rec["last_downloaded_episode"] = max(show_rec["downloaded_episodes"])
        show_rec["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history["processed_urls"].append(v_u)
        processed_set.add(v_u)
        save_history(history)
        new_downloaded += 1

        # Cập nhật info.json trong thư mục phim với thông tin chi tiết tập đã tải
        try:
            show_info_path = os.path.join(show_dir, "info.json")
            with open(show_info_path, "w", encoding="utf-8") as f_inf:
                json.dump({
                    "title": info["title"],
                    "description": info.get("description", ""),
                    "url": show_url,
                    "last_downloaded_episode": show_rec["last_downloaded_episode"],
                    "total_episodes": len(episodes),
                    "downloaded_episodes": show_rec["downloaded_episodes"],
                    "status": f"Đã tải {len(show_rec['downloaded_episodes'])}/{len(episodes)} tập",
                    "last_updated": show_rec["last_updated"]
                }, f_inf, indent=2, ensure_ascii=False)
        except Exception:
            pass

    for idx, v_url in enumerate(episodes, start=1):
        filename = f"Tap_{idx:03d}.mp4"
        final_path = os.path.join(show_dir, filename)

        # Kiểm tra nếu tập này đã xử lý trước đó
        if v_url in processed_set:
            continue

        print(f"   ▶ Đang tải Tập {idx:03d}/{len(episodes):03d} ({filename}):")
        log_event(f"Bắt đầu tải: '{info['title']}' - Tập {idx:03d}/{len(episodes):03d} ({filename})", level="DOWNLOAD")

        # Trường hợp xóa logo: Tải file tạm -> Xử lý delogo -> Xuất file đích
        if delogo_enabled:
            temp_path = os.path.join(show_dir, f".temp_{filename}")
            try:
                download_file(v_url, temp_path)
                success = apply_delogo(ffmpeg_bin, temp_path, final_path, delogo_cfg)
                if success:
                    sz_mb = os.path.getsize(final_path) / (1024 * 1024)
                    print(f"      [✓] Hoàn thành & Đã xóa logo: {filename} ({sz_mb:.2f} MB) -> Đã tải đến tập {idx:03d}/{len(episodes):03d}")
                    log_event(f"Tải và xóa logo thành công: '{info['title']}' - {filename} ({sz_mb:.2f} MB) | Đã tải đến tập {idx:03d}/{len(episodes):03d}", level="SUCCESS")
                    record_episode_success(idx, final_path, v_url)
                else:
                    # Nếu lỗi delogo thì giữ lại file gốc
                    if os.path.isfile(temp_path):
                        os.replace(temp_path, final_path)
                        print(f"      [!] Giữ lại file gốc (bỏ qua xóa logo): {filename} -> Đã tải đến tập {idx:03d}/{len(episodes):03d}")
                        log_event(f"Tải file gốc thành công: '{info['title']}' - {filename} | Đã tải đến tập {idx:03d}/{len(episodes):03d}", level="SUCCESS")
                        record_episode_success(idx, final_path, v_url)
            except Exception as e:
                print(f"      [X] Lỗi tải/xử lý tập {idx}: {e}")
            finally:
                if os.path.isfile(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        else:
            # Tải trực tiếp không cần re-encode
            try:
                download_file(v_url, final_path)
                sz_mb = os.path.getsize(final_path) / (1024 * 1024)
                print(f"      [✓] Hoàn tất tải: {filename} ({sz_mb:.2f} MB) -> Đã tải đến tập {idx:03d}/{len(episodes):03d}")
                log_event(f"Hoàn tất tải: '{info['title']}' - {filename} ({sz_mb:.2f} MB) | Đã tải đến tập {idx:03d}/{len(episodes):03d}", level="SUCCESS")
                record_episode_success(idx, final_path, v_url)
            except Exception as e:
                print(f"      [X] Lỗi tải tập {idx}: {e}")
    # Tự động ghép các tập video đã tải thành các video tối đa X phút (mặc định 40 phút)
    merge_cfg = config.get("merge", {})
    if merge_cfg.get("enabled", True):
        merge_show_episodes(show_dir, info["title"], config, ffmpeg_bin, show_desc=info.get("description", ""))

    return new_downloaded


def merge_show_episodes(show_dir: str, show_title: str, config: dict, ffmpeg_bin: str, show_desc: str = "") -> int:
    """
    Tự động ghép các tập video đã tải thành các video có thời lượng tối đa theo cấu hình (mặc định: 40 phút).
    - Tìm tất cả file Tap_XXX.mp4 trong show_dir.
    - Tính thời lượng từng tập và gom nhóm sao cho tổng thời lượng mỗi nhóm <= max_duration_minutes.
    - Dùng FFmpeg ghép không làm giảm chất lượng (stream copy), có fallback re-encode nếu cần.
    - Lưu vào thư mục con (mặc định: Ghep_Video).
    """
    if not show_desc:
        info_file = os.path.join(show_dir, "info.json")
        if os.path.isfile(info_file):
            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    idata = json.load(f)
                    show_desc = idata.get("description", "")
            except Exception:
                pass

    merge_cfg = config.get("merge", {})
    if not merge_cfg.get("enabled", True):
        return 0

    max_mins = merge_cfg.get("max_duration_minutes", 40)
    max_seconds = max_mins * 60.0
    subfolder = merge_cfg.get("output_folder", "Ghep_Video")
    target_dir = os.path.join(show_dir, subfolder) if subfolder else show_dir
    os.makedirs(target_dir, exist_ok=True)

    # 1. Quét danh sách các tập video hợp lệ (Tap_XXX.mp4)
    episodes = []
    for fname in os.listdir(show_dir):
        m = re.match(r"^Tap_(\d+)\.mp4$", fname, re.IGNORECASE)
        if m:
            fpath = os.path.join(show_dir, fname)
            if os.path.isfile(fpath) and os.path.getsize(fpath) > 102400:
                ep_num = int(m.group(1))
                episodes.append({
                    "num": ep_num,
                    "filename": fname,
                    "path": fpath
                })

    if not episodes:
        return 0

    episodes.sort(key=lambda x: x["num"])

    # Đo thời lượng cho từng tập
    for ep in episodes:
        ep["duration"] = get_video_duration(ffmpeg_bin, ep["path"])

    total_show_dur = sum(ep["duration"] for ep in episodes)
    print(f"\n🧩 [TỰ ĐỘNG GHÉP VIDEO] Phim: \"{show_title}\"")
    print(f"   - Tổng số tập đã tải: {len(episodes)} tập")
    print(f"   - Tổng thời lượng: {total_show_dur/60:.1f} phút")
    print(f"   - Giới hạn tối đa: {max_mins} phút / video ghép")

    # 2. Phân chia các tập vào từng nhóm (Part) sao cho mỗi nhóm <= max_seconds
    groups = []
    cur_group = []
    cur_dur = 0.0

    for ep in episodes:
        if cur_group and (cur_dur + ep["duration"] > max_seconds):
            groups.append({
                "episodes": cur_group,
                "duration": cur_dur,
                "start_ep": cur_group[0]["num"],
                "end_ep": cur_group[-1]["num"]
            })
            cur_group = [ep]
            cur_dur = ep["duration"]
        else:
            cur_group.append(ep)
            cur_dur += ep["duration"]

    if cur_group:
        groups.append({
            "episodes": cur_group,
            "duration": cur_dur,
            "start_ep": cur_group[0]["num"],
            "end_ep": cur_group[-1]["num"]
        })

    print(f"   - Phân chia: {len(groups)} phần (Part)")

    safe_title = sanitize_filename(show_title)
    merged_count = 0

    for part_idx, g in enumerate(groups, start=1):
        g_eps = g["episodes"]
        start_ep = g["start_ep"]
        end_ep = g["end_ep"]
        dur_mins = g["duration"] / 60.0

        # Đặt tên file xuất
        if len(groups) == 1:
            if start_ep == end_ep:
                out_name = f"{safe_title}_Full_Tap_{start_ep:03d}.mp4"
            else:
                out_name = f"{safe_title}_Full_Tap_{start_ep:03d}-{end_ep:03d}.mp4"
        else:
            if start_ep == end_ep:
                out_name = f"{safe_title}_Part_{part_idx:02d}_Tap_{start_ep:03d}.mp4"
            else:
                out_name = f"{safe_title}_Part_{part_idx:02d}_Tap_{start_ep:03d}-{end_ep:03d}.mp4"

        out_path = os.path.join(target_dir, out_name)

        print(f"\n   ▶ Part {part_idx:02d}/{len(groups):02d} (Tập {start_ep:03d} -> {end_ep:03d} | {len(g_eps)} tập | {dur_mins:.1f} phút):")

        def trigger_channel_publishing(final_video_path: str, p_start: int, p_end: int, p_dur: float):
            dist_cfg = config.get("channels_distribution", {})
            k1_cfg = dist_cfg.get("kenh_1_raw", {})
            ai_cfg = config.get("ai_recap", {})

            # BƯỚC 1: Xử lý kịch bản, lồng tiếng & xuất bản Kênh 2 (Review EN) và Kênh 3 (Review VI) TRƯỚC
            # (Vì các kênh này cần file raw_merged_video để bóc tách âm thanh và làm audio ducking)
            ai_all_ok = True
            if ai_cfg.get("enabled", True):
                ai_cfg_copy = dict(ai_cfg)
                ai_cfg_copy["full_config"] = config
                try:
                    from ai_recap_helper import process_channel_review
                    for lang in ai_cfg.get("languages", ["vi", "en"]):
                        sub_chan = "Kenh_3_Review_VI" if lang == "vi" else "Kenh_2_Review_EN"
                        chan_dir = os.path.join(target_dir, sub_chan)
                        res_vid = process_channel_review(
                            ffmpeg_bin=ffmpeg_bin,
                            raw_merged_video=final_video_path,
                            show_title=show_title,
                            show_desc=show_desc,
                            start_ep=p_start,
                            end_ep=p_end,
                            duration_mins=p_dur,
                            lang=lang,
                            out_folder=chan_dir,
                            ai_cfg=ai_cfg_copy,
                            yt_cfg=config.get("youtube_upload", {})
                        )
                        if not res_vid:
                            ai_all_ok = False
                except Exception as e_ai:
                    print(f"      [!] Lỗi khi xử lý AI Recap: {e_ai}")
                    ai_all_ok = False

            # BƯỚC 2: Tự động xuất bản Kênh 1 (Raw Full) nếu bật
            k1_published = False
            k1_needed = k1_cfg.get("youtube", {}).get("enabled", False) or k1_cfg.get("facebook", {}).get("enabled", False)
            if k1_needed:
                raw_title = f"{show_title} - Tập {p_start:03d}-{p_end:03d} (Full 1080p)" if p_start != p_end else f"{show_title} - Tập {p_start:03d} (Full 1080p)"
                raw_desc = f"Xem trọn bộ phim {show_title} (Tập {p_start} - {p_end}).\n\n{show_desc}\n\n#anime #{safe_title.lower().replace(' ', '')} #fullhd"
                k1_meta = {
                    "title": raw_title,
                    "description": raw_desc,
                    "tags": ["anime", "full hd", "phim anime", safe_title.lower()]
                }
                k1_payload = os.path.join(target_dir, f"{safe_title}_Part_{part_idx:02d}_RAW_PAYLOAD.json")
                try:
                    from publisher import publish_to_channel
                    k1_res = publish_to_channel("kenh_1_raw", final_video_path, k1_meta, config, payload_json_path=k1_payload)
                    k1_yt_ok = (k1_res.get("youtube_video_id") is not None) if k1_cfg.get("youtube", {}).get("enabled", False) else True
                    k1_fb_ok = (k1_res.get("facebook_video_id") is not None) if k1_cfg.get("facebook", {}).get("enabled", False) else True
                    k1_published = k1_yt_ok and k1_fb_ok
                except Exception as e_k1:
                    print(f"      [!] Lỗi xuất bản Kênh 1: {e_k1}")
            else:
                k1_published = True

            # BƯỚC 3: TỰ ĐỘNG XÓA FILE VIDEO DÀI GỐC CHỈ KHI TẤT CẢ KÊNH ĐỀU ĐĂNG THÀNH CÔNG
            if config.get("cleanup_published_videos", True) and k1_published and ai_all_ok:
                has_any_pub = (
                    k1_needed or
                    dist_cfg.get("kenh_2_en", {}).get("youtube", {}).get("enabled", False) or
                    dist_cfg.get("kenh_2_en", {}).get("facebook", {}).get("enabled", False) or
                    dist_cfg.get("kenh_3_vi", {}).get("youtube", {}).get("enabled", False) or
                    dist_cfg.get("kenh_3_vi", {}).get("facebook", {}).get("enabled", False)
                )
                if has_any_pub and os.path.isfile(final_video_path):
                    try:
                        sz_mb = os.path.getsize(final_video_path) / (1024 * 1024)
                        os.remove(final_video_path)
                        msg_del_raw = f"🧹 [DỌN DẸP Ổ CỨNG] Đã hoàn tất xử lý & xuất bản các kênh! Tự động xóa video dài gốc {os.path.basename(final_video_path)} ({sz_mb:.1f} MB) để nhẹ máy."
                        print(f"      {msg_del_raw}")
                        log_event(msg_del_raw, level="CLEAN")
                    except Exception as e_del_raw:
                        print(f"      [!] Không thể xóa video dài gốc: {e_del_raw}")

        # Kiểm tra nếu file ghép đã tồn tại và mới hơn tất cả các tập nguồn
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 102400:
            target_mtime = os.path.getmtime(out_path)
            if all(os.path.getmtime(e["path"]) < target_mtime for e in g_eps):
                print(f"      [✓] Đã tồn tại & mới nhất: {out_name} ({os.path.getsize(out_path)/(1024*1024):.1f} MB)")
                trigger_channel_publishing(out_path, start_ep, end_ep, dur_mins)
                cleanup_merged_source_episodes(g_eps, out_name, config)
                log_event(f"Ghép video thành công: {out_name} ({dur_mins:.1f} phút)", level="INFO")
                continue

        # Nếu chỉ có 1 tập trong nhóm: stream copy trực tiếp
        if len(g_eps) == 1:
            src_file = g_eps[0]["path"]
            try:
                cmd = [ffmpeg_bin, "-y", "-i", src_file, "-c", "copy", out_path]
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 102400:
                    print(f"      [✓] Hoàn thành: {out_name} ({os.path.getsize(out_path)/(1024*1024):.1f} MB)")
                    merged_count += 1
                    trigger_channel_publishing(out_path, start_ep, end_ep, dur_mins)
                    cleanup_merged_source_episodes(g_eps, out_name, config)
                    log_event(f"Ghép video thành công: {out_name} ({dur_mins:.1f} phút)", level="INFO")
                else:
                    print(f"      [!] Lỗi sao chép video tập {start_ep}: {res.stderr[:160]}")
            except Exception as e:
                print(f"      [X] Lỗi xuất video: {e}")
            continue

        # Trường hợp ghép nhiều tập:
        # Cách 1: Thử Concat Demuxer với stream copy (siêu nhanh, giữ nguyên 100% chất lượng)
        list_txt = os.path.join(target_dir, f".temp_concat_part_{part_idx:02d}.txt")
        try:
            with open(list_txt, "w", encoding="utf-8") as f:
                for e in g_eps:
                    clean_path = e["path"].replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{clean_path}'\n")

            cmd_demux = [
                ffmpeg_bin, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_txt,
                "-c", "copy",
                out_path
            ]
            print(f"      -> Đang ghép {len(g_eps)} tập thành 1 video (tối đa {max_mins}p)...")
            res = subprocess.run(cmd_demux, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

            if res.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 102400:
                print(f"      [✓] Ghép thành công: {out_name} ({os.path.getsize(out_path)/(1024*1024):.1f} MB | {dur_mins:.1f} phút)")
                merged_count += 1
                trigger_channel_publishing(out_path, start_ep, end_ep, dur_mins)
                cleanup_merged_source_episodes(g_eps, out_name, config)
                log_event(f"Ghép video thành công: {out_name} ({dur_mins:.1f} phút)", level="INFO")
            else:
                # Cách 2: Fallback re-encode nếu video gốc có thông số lệch nhau
                print(f"      [!] Concat copy không thành công, chuyển sang ghép & re-encode...")
                inputs = []
                filter_parts = []
                for i_idx, e in enumerate(g_eps):
                    inputs.extend(["-i", e["path"]])
                    filter_parts.append(f"[{i_idx}:v:0][{i_idx}:a:0]")
                filter_str = "".join(filter_parts) + f"concat=n={len(g_eps)}:v=1:a=1[v][a]"

                cmd_fallback = [
                    ffmpeg_bin, "-y",
                    *inputs,
                    "-filter_complex", filter_str,
                    "-map", "[v]",
                    "-map", "[a]",
                    "-c:v", "libx264",
                    "-crf", "20",
                    "-preset", "faster",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    out_path
                ]
                res_fb = subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                if res_fb.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 102400:
                    print(f"      [✓] Ghép re-encode thành công: {out_name} ({os.path.getsize(out_path)/(1024*1024):.1f} MB)")
                    merged_count += 1
                    trigger_channel_publishing(out_path, start_ep, end_ep, dur_mins)
                    cleanup_merged_source_episodes(g_eps, out_name, config)
                    log_event(f"Ghép video thành công: {out_name} ({dur_mins:.1f} phút)", level="INFO")
                else:
                    print(f"      [X] Lỗi ghép video: {res_fb.stderr[:200]}")
        except Exception as ex:
            print(f"      [X] Lỗi xử lý ghép video Part {part_idx}: {ex}")
        finally:
            if os.path.isfile(list_txt):
                try:
                    os.remove(list_txt)
                except Exception:
                    pass

    print(f"   📁 Thư mục video đã ghép: {target_dir}")
    return merged_count


def merge_all_downloaded_shows(config: dict, ffmpeg_bin: str):
    """Quét toàn bộ các thư mục phim trong Downloads và ghép video tối đa 40 phút."""
    out_base = os.path.join(BASE_DIR, config.get("output_dir", "Downloads"))
    if not os.path.isdir(out_base):
        print(f"[!] Thư mục '{out_base}' không tồn tại.")
        return

    shows = [d for d in os.listdir(out_base) if os.path.isdir(os.path.join(out_base, d))]
    if not shows:
        print("[!] Không tìm thấy thư mục phim nào trong Downloads.")
        return

    print("=" * 65)
    print("🎬 BẮT ĐẦU QUÉT & GHÉP CÁC VIDEO ĐÃ TẢI (TỐI ĐA 40 PHÚT)")
    print("=" * 65)
    total_merged = 0
    for show_title in sorted(shows):
        show_dir = os.path.join(out_base, show_title)
        has_ep = any(re.match(r"^Tap_\d+\.mp4$", f, re.IGNORECASE) for f in os.listdir(show_dir) if os.path.isfile(os.path.join(show_dir, f)))
        if has_ep:
            count = merge_show_episodes(show_dir, show_title, config, ffmpeg_bin)
            total_merged += count

    print("\n" + "=" * 65)
    print(f"🎉 HOÀN THÀNH GHÉP TẤT CẢ PHIM! Tổng số file ghép mới/cập nhật: {total_merged}")
    print("=" * 65)


def run_cycle(config: dict, history: dict, ffmpeg_bin: str, target_url: str = None) -> int:
    """Thực thi một chu kỳ quét và tải."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 65)
    print(f"🚀 BẮT ĐẦU CHU KỲ QUÉT TỰ ĐỘNG [{now_str}]")
    print("=" * 65)

    shows_to_process = []

    if target_url:
        shows_to_process.append(target_url)
    else:
        # 1. Quét danh sách phim tùy chọn từ file text
        custom_file = config.get("custom_urls_file", "danh_sach_phim.txt")
        custom_shows = get_custom_shows(custom_file)
        if custom_shows:
            print(f"[*] Tìm thấy {len(custom_shows)} phim từ file '{custom_file}'")
            shows_to_process.extend(custom_shows)

        # 2. Quét trang chủ Trimz.tv nếu bật
        if config.get("crawl_homepage", True):
            print("[*] Đang quét các phim mới trên trang chủ Trimz.tv...")
            home_shows = discover_homepage_shows()
            print(f"[+] Tìm thấy {len(home_shows)} phim trên trang chủ")
            for s in home_shows:
                if s not in shows_to_process:
                    shows_to_process.append(s)

    if not shows_to_process:
        print("[!] Không có bộ phim nào để xử lý. Vui lòng thêm link vào 'danh_sach_phim.txt'.")
        return 0

    print(f"[*] Tổng số bộ phim sẽ kiểm tra trong chu kỳ này: {len(shows_to_process)}")

    total_new = 0
    for idx, show_url in enumerate(shows_to_process, start=1):
        print(f"\n--- [{idx}/{len(shows_to_process)}] Đang kiểm tra: {show_url} ---")
        try:
            new_count = process_single_show(show_url, config, history, ffmpeg_bin)
            total_new += new_count
        except Exception as e:
            print(f"[X] Lỗi xử lý phim {show_url}: {e}")

    print("\n" + "=" * 65)
    print(f"✨ HOÀN THÀNH CHU KỲ! Đã tải mới & xử lý: {total_new} tập video.")
    print("=" * 65)
    return total_new


def main():
    parser = argparse.ArgumentParser(description="Trimz.tv Auto Cron Job - Tải, Xóa Logo & Ghép Video Tự Động")
    parser.add_argument("--once", action="store_true", help="Chạy một chu kỳ duy nhất rồi kết thúc")
    parser.add_argument("--interval", type=int, help="Ghi đè chu kỳ quét (tính bằng phút)")
    parser.add_argument("--no-delogo", action="store_true", help="Tắt tính năng xóa logo")
    parser.add_argument("--no-merge", action="store_true", help="Tắt tính năng tự động ghép video")
    parser.add_argument("--no-ai", action="store_true", help="Tắt tính năng AI tự động viết kịch bản và lồng tiếng")
    parser.add_argument("--upload-youtube", action="store_true", help="Tự động đăng video lên YouTube sau khi tạo xong")
    parser.add_argument("--gemini-key", type=str, help="Cung cấp hoặc ghi đè Gemini API Key")
    parser.add_argument("--max-duration", type=int, help="Thời lượng tối đa cho mỗi video ghép (tính bằng phút, mặc định: 40)")
    parser.add_argument("--merge-only", action="store_true", help="Chỉ thực hiện ghép các video đã tải sẵn trong Downloads mà không tải mới")
    parser.add_argument("--url", type=str, help="Chỉ quét 1 URL phim cụ thể")
    args = parser.parse_args()

    config = load_config()
    history = load_history()

    if args.interval:
        config["check_interval_minutes"] = max(1, args.interval)
    if args.no_delogo:
        config["delogo"]["enabled"] = False
    if args.no_merge:
        config["merge"]["enabled"] = False
    if args.no_ai:
        config["ai_recap"]["enabled"] = False
    if args.upload_youtube:
        config["youtube_upload"]["enabled"] = True
    if args.gemini_key:
        config["ai_recap"]["api_key"] = args.gemini_key
    if args.max_duration:
        config["merge"]["max_duration_minutes"] = max(1, args.max_duration)

    ffmpeg_bin = get_ffmpeg_exe()

    merge_status = "BẬT" if config.get("merge", {}).get("enabled", True) else "TẮT"
    merge_max_dur = config.get("merge", {}).get("max_duration_minutes", 40)
    merge_folder = config.get("merge", {}).get("output_folder", "Ghep_Video")

    ai_cfg = config.get("ai_recap", {})
    ai_status = "BẬT" if ai_cfg.get("enabled", True) else "TẮT"
    ai_model = ai_cfg.get("model", "gemini-1.5-flash")
    ai_langs = ", ".join(ai_cfg.get("languages", ["vi", "en"]))

    dist_cfg = config.get("channels_distribution", {})
    k1_yt = "BẬT" if dist_cfg.get("kenh_1_raw", {}).get("youtube", {}).get("enabled", False) else "TẮT"
    k1_fb = "BẬT" if dist_cfg.get("kenh_1_raw", {}).get("facebook", {}).get("enabled", False) else "TẮT"
    k2_yt = "BẬT" if dist_cfg.get("kenh_2_en", {}).get("youtube", {}).get("enabled", False) else "TẮT"
    k2_fb = "BẬT" if dist_cfg.get("kenh_2_en", {}).get("facebook", {}).get("enabled", False) else "TẮT"
    k3_yt = "BẬT" if dist_cfg.get("kenh_3_vi", {}).get("youtube", {}).get("enabled", False) else "TẮT"
    k3_fb = "BẬT" if dist_cfg.get("kenh_3_vi", {}).get("facebook", {}).get("enabled", False) else "TẮT"

    print("*" * 65)
    print("      TRIMZ.TV AUTO CRON JOB - TẢI, XÓA LOGO & GHÉP VIDEO      ")
    print("*" * 65)
    print(f"[*] FFmpeg Binary: {ffmpeg_bin}")
    print(f"[*] Chế độ xóa logo: {'BẬT (vị trí: ' + config['delogo']['position'] + ')' if config['delogo']['enabled'] else 'TẮT'}")
    print(f"[*] Chế độ ghép video: {merge_status} (Tối đa {merge_max_dur} phút/video -> '{merge_folder}')")
    print(f"[*] Chế độ AI Review (Gemini + TTS): {ai_status} (Model: {ai_model} | Kênh: {ai_langs})")
    print(f"[*] Phân phối Kênh 1 (Raw Phim): YouTube [{k1_yt}] | Facebook Page [{k1_fb}]")
    print(f"[*] Phân phối Kênh 2 (Review EN): YouTube [{k2_yt}] | Facebook Page [{k2_fb}]")
    print(f"[*] Phân phối Kênh 3 (Review VI): YouTube [{k3_yt}] | Facebook Page [{k3_fb}]")
    print(f"[*] Thư mục lưu: {config.get('output_dir', 'Downloads')}")
    print(f"[*] Chu kỳ kiểm tra: {config.get('check_interval_minutes', 30)} phút / lần")
    print("*" * 65)

    # Chế độ chỉ ghép các video đã tải
    if args.merge_only:
        merge_all_downloaded_shows(config, ffmpeg_bin)
        return

    # Chế độ chạy 1 lần
    if args.once or args.url:
        run_cycle(config, history, ffmpeg_bin, target_url=args.url)
        print("\n[V] Đã chạy xong lượt kiểm tra.")
        return

    # Chế độ chạy ngầm định kỳ liên tục
    interval_sec = config.get("check_interval_minutes", 30) * 60
    while True:
        try:
            run_cycle(config, history, ffmpeg_bin)
        except Exception as e:
            print(f"[!] Lỗi phát sinh trong chu kỳ: {e}")

        # Đếm ngược tới chu kỳ tiếp theo
        print(f"\n💤 Đang nghỉ {config['check_interval_minutes']} phút trước chu kỳ quét tiếp theo...")
        print("   (Bấm Ctrl+C bất cứ lúc nào để dừng job an toàn)\n")
        
        try:
            for remaining in range(interval_sec, 0, -10):
                mins, secs = divmod(remaining, 60)
                hours, mins = divmod(mins, 60)
                print(f"\r⏳ Lần quét tiếp theo sau: {hours:02d}h:{mins:02d}m:{secs:02d}s ", end="", flush=True)
                time.sleep(10)
            print()
        except KeyboardInterrupt:
            print("\n\n[!] Đã nhận tín hiệu dừng từ người dùng (Ctrl+C). Tạm biệt!")
            break


if __name__ == "__main__":
    main()
