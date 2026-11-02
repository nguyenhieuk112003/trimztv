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
from datetime import datetime

# Đảm bảo console UTF-8 trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
DEFAULT_CUSTOM_FILE = os.path.join(BASE_DIR, "danh_sach_phim.txt")

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
        except Exception as e:
            print(f"[!] Lỗi đọc file config.json: {e}. Dùng cấu hình mặc định.")
    else:
        save_config(default_config)
    return default_config


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_history() -> dict:
    if os.path.isfile(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed_urls": [], "last_check": ""}


def save_history(history: dict):
    history["last_check"] = datetime.now().isoformat()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


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

    delogo_cfg = config.get("delogo", {})
    delogo_enabled = delogo_cfg.get("enabled", True)

    processed_set = set(history.get("processed_urls", []))
    new_downloaded = 0

    print(f"\n🎬 PHIM: \"{info['title']}\" ({len(episodes)} tập)")
    print(f"   📁 Thư mục lưu: {show_dir}")

    for idx, v_url in enumerate(episodes, start=1):
        filename = f"Tap_{idx:03d}.mp4"
        final_path = os.path.join(show_dir, filename)

        # Kiểm tra nếu tập này đã xử lý trước đó
        if v_url in processed_set and os.path.isfile(final_path) and os.path.getsize(final_path) > 102400:
            continue

        print(f"   ▶ Tập {idx:03d}/{len(episodes):03d} ({filename}):")

        # Trường hợp xóa logo: Tải file tạm -> Xử lý delogo -> Xuất file đích
        if delogo_enabled:
            temp_path = os.path.join(show_dir, f".temp_{filename}")
            try:
                download_file(v_url, temp_path)
                success = apply_delogo(ffmpeg_bin, temp_path, final_path, delogo_cfg)
                if success:
                    print(f"      [✓] Hoàn thành & Đã xóa logo: {filename} ({os.path.getsize(final_path)/(1024*1024):.2f} MB)")
                    history["processed_urls"].append(v_url)
                    processed_set.add(v_url)
                    save_history(history)
                    new_downloaded += 1
                else:
                    # Nếu lỗi delogo thì giữ lại file gốc
                    if os.path.isfile(temp_path):
                        os.replace(temp_path, final_path)
                        print(f"      [!] Giữ lại file gốc (bỏ qua xóa logo): {filename}")
                        history["processed_urls"].append(v_url)
                        processed_set.add(v_url)
                        save_history(history)
                        new_downloaded += 1
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
                print(f"      [✓] Hoàn tất tải: {filename} ({os.path.getsize(final_path)/(1024*1024):.2f} MB)")
                history["processed_urls"].append(v_url)
                processed_set.add(v_url)
                save_history(history)
                new_downloaded += 1
            except Exception as e:
                print(f"      [X] Lỗi tải tập {idx}: {e}")
    # Tự động ghép các tập video đã tải thành các video tối đa X phút (mặc định 40 phút)
    merge_cfg = config.get("merge", {})
    if merge_cfg.get("enabled", True):
        merge_show_episodes(show_dir, info["title"], config, ffmpeg_bin)

    return new_downloaded


def merge_show_episodes(show_dir: str, show_title: str, config: dict, ffmpeg_bin: str) -> int:
    """
    Tự động ghép các tập video đã tải thành các video có thời lượng tối đa theo cấu hình (mặc định: 40 phút).
    - Tìm tất cả file Tap_XXX.mp4 trong show_dir.
    - Tính thời lượng từng tập và gom nhóm sao cho tổng thời lượng mỗi nhóm <= max_duration_minutes.
    - Dùng FFmpeg ghép không làm giảm chất lượng (stream copy), có fallback re-encode nếu cần.
    - Lưu vào thư mục con (mặc định: Ghep_Video).
    """
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

        # Kiểm tra nếu file ghép đã tồn tại và mới hơn tất cả các tập nguồn
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 102400:
            target_mtime = os.path.getmtime(out_path)
            if all(os.path.getmtime(e["path"]) < target_mtime for e in g_eps):
                print(f"      [✓] Đã tồn tại & mới nhất: {out_name} ({os.path.getsize(out_path)/(1024*1024):.1f} MB)")
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
    if args.max_duration:
        config["merge"]["max_duration_minutes"] = max(1, args.max_duration)

    ffmpeg_bin = get_ffmpeg_exe()

    merge_status = "BẬT" if config.get("merge", {}).get("enabled", True) else "TẮT"
    merge_max_dur = config.get("merge", {}).get("max_duration_minutes", 40)
    merge_folder = config.get("merge", {}).get("output_folder", "Ghep_Video")

    print("*" * 65)
    print("      TRIMZ.TV AUTO CRON JOB - TẢI, XÓA LOGO & GHÉP VIDEO      ")
    print("*" * 65)
    print(f"[*] FFmpeg Binary: {ffmpeg_bin}")
    print(f"[*] Chế độ xóa logo: {'BẬT (vị trí: ' + config['delogo']['position'] + ')' if config['delogo']['enabled'] else 'TẮT'}")
    print(f"[*] Chế độ ghép video: {merge_status} (Tối đa {merge_max_dur} phút/video -> '{merge_folder}')")
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
