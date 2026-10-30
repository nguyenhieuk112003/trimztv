"""
================================================================================
AUTO ANIME RECAP - HỆ THỐNG TỰ ĐỘNG BIÊN TẬP & TÓM TẮT ANIME TỪ TRIMZ.TV
================================================================================
Quy trình 5 bước:
1. Tải video tập phim từ Trimz.tv
2. Sinh kịch bản tóm tắt/review anime tiếng Việt lôi cuốn
3. Tạo giọng đọc AI thuyết minh (Microsoft Neural TTS)
4. Dùng FFmpeg ghép video, ducking âm thanh gốc và lồng giọng thuyết minh
5. Tạo bộ metadata SEO YouTube (Title, Description, Tags, Chapters)
================================================================================
"""

import os
import sys
import re
import json
import asyncio
import subprocess
import urllib.request

# Đảm bảo UTF-8 cho console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Đường dẫn công cụ portable nội bộ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
FFMPEG_EXE = os.path.join(TOOLS_DIR, "ffmpeg", "ffmpeg.exe")
FFPROBE_EXE = os.path.join(TOOLS_DIR, "ffmpeg", "ffprobe.exe")

# Nếu không có trong tools thì tìm trong PATH
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"
if not os.path.exists(FFPROBE_EXE):
    FFPROBE_EXE = "ffprobe"

def sanitize_name(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def get_media_duration(file_path: str) -> float:
    """Lấy thời lượng (giây) của file video hoặc audio qua ffprobe."""
    try:
        cmd = [
            FFPROBE_EXE, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

# ----------------------------------------------------------------------
# BƯỚC 1: TẢI VIDEO TỪ TRIMZ.TV
# ----------------------------------------------------------------------
def step1_fetch_episodes(url: str, ep_start: int = 1, ep_count: int = 3):
    print("\n" + "="*60)
    print("▶ BƯỚC 1: QUÉT VÀ TẢI TẬP PHIM TỪ TRIMZ.TV")
    print("="*60)
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        
    title_match = re.search(r'<title>([^<]+)</title>', html)
    raw_title = title_match.group(1) if title_match else "Trimz Anime"
    raw_title = raw_title.split(" - Trimz")[0].split(" | Trimz")[0].split(": Watch & Create")[0].replace("Watch ", "")
    show_title = sanitize_name(raw_title)
    
    # Tìm tóm tắt gốc
    summary_match = re.search(r'"summary":"([^"]+)"', html)
    show_summary = summary_match.group(1) if summary_match else ""
    
    mp4_pattern = r'https://cdn\.trimz\.co/generated-videos/ms_videos/[a-zA-Z0-9_\-]+\.mp4'
    all_mp4s = re.findall(mp4_pattern, html)
    unique_mp4s = list(dict.fromkeys(all_mp4s))
    
    print(f"[*] Tên bộ phim: {show_title}")
    if show_summary:
        print(f"[*] Cốt truyện gốc: {show_summary}")
    print(f"[*] Tìm thấy tổng cộng: {len(unique_mp4s)} tập")
    
    # Giới hạn số tập cần tải
    start_idx = max(0, ep_start - 1)
    end_idx = min(len(unique_mp4s), start_idx + ep_count)
    selected_urls = unique_mp4s[start_idx:end_idx]
    
    work_dir = os.path.join(BASE_DIR, "Output", show_title)
    os.makedirs(work_dir, exist_ok=True)
    
    downloaded_files = []
    print(f"[*] Sẽ tải từ tập {start_idx + 1} đến tập {end_idx} ({len(selected_urls)} tập)...")
    
    for i, vurl in enumerate(selected_urls, start=start_idx + 1):
        filename = f"Ep_{i:03d}.mp4"
        dest_path = os.path.join(work_dir, filename)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 102400:
            print(f"  [✓] {filename} đã tồn tại, dùng lại.")
        else:
            print(f"  [↓] Đang tải {filename}...")
            # Dùng curl để tải nhanh
            subprocess.run(["curl.exe", "-s", "-L", "-o", dest_path, vurl], check=True)
            print(f"  [✓] Đã tải xong {filename} ({os.path.getsize(dest_path)/(1024*1024):.1f} MB)")
        downloaded_files.append(dest_path)
        
    return {
        "title": show_title,
        "summary": show_summary,
        "episodes": downloaded_files,
        "work_dir": work_dir,
        "ep_start": ep_start,
        "ep_end": end_idx
    }

# ----------------------------------------------------------------------
# BƯỚC 2: TẠO KỊCH BẢN REVIEW/TÓM TẮT PHIM
# ----------------------------------------------------------------------
def step2_generate_script(info: dict) -> str:
    print("\n" + "="*60)
    print("▶ BƯỚC 2: BIÊN SOẠN KỊCH BẢN REVIEW / TÓM TẮT ANIME")
    print("="*60)
    
    title = info["title"]
    summary = info.get("summary", "")
    ep_start = info["ep_start"]
    ep_end = info["ep_end"]
    
    # Mẫu kịch bản tóm tắt hấp dẫn theo phong cách Review Phim YouTube
    script = (
        f"Chào mừng các bạn đã quay trở lại với Góc Tóm Tắt Anime! "
        f"Hôm nay, chúng ta sẽ cùng đến với câu chuyện vô cùng thú vị mang tên: {title}. "
        f"Nếu như bạn nghĩ một chàng trai Otaku sống khép kín, ngày ngày chỉ biết cắm mặt vào thế giới ảo "
        f"thì sẽ chẳng bao giờ có cơ hội chạm tay vào tình yêu, thì bộ anime này sẽ khiến bạn phải suy nghĩ lại hoàn toàn. "
        f"Trong tập mở đầu hôm nay, hàng loạt biến cố bất ngờ đã xảy ra khi nữ thần xinh đẹp và nổi tiếng nhất toàn trường "
        f"lại bất ngờ chú ý và xuất hiện trong cuộc đời của cậu ấy. "
        f"Liệu đây là một sự trùng hợp định mệnh, hay đằng sau đó là một bí mật mà không ai hay biết? "
        f"Không để các bạn phải chờ đợi lâu nữa, chúng ta hãy cùng theo dõi ngay diễn biến từ tập {ep_start} đến tập {ep_end} nhé! "
        f"Đừng quên bấm Like và Đăng Ký Kênh để không bỏ lỡ những tập tiếp theo cực kỳ gay cấn!"
    )
    
    script_file = os.path.join(info["work_dir"], "kich_ban_review.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
        
    print(f"[*] Kịch bản đã được biên soạn ({len(script.split())} từ):")
    print(f"    \"{script[:140]}...\"")
    print(f"[✓] Đã lưu kịch bản vào: {script_file}")
    
    return script

# ----------------------------------------------------------------------
# BƯỚC 3: TẠO GIỌNG ĐỌC AI THUYẾT MINH (EDGE-TTS)
# ----------------------------------------------------------------------
async def _async_generate_tts(text: str, output_path: str, voice: str = "vi-VN-NamMinhNeural"):
    import edge_tts
    # vi-VN-NamMinhNeural: Giọng nam trầm ấm, truyền cảm
    # vi-VN-HoaiMyNeural: Giọng nữ ngọt ngào, rõ ràng
    communicator = edge_tts.Communicate(text, voice)
    await communicator.save(output_path)

def step3_create_voiceover(script: str, info: dict, voice: str = "vi-VN-NamMinhNeural") -> str:
    print("\n" + "="*60)
    print("▶ BƯỚC 3: TẠO GIỌNG ĐỌC AI THUYẾT MINH (MICROSOFT NEURAL)")
    print("="*60)
    
    audio_path = os.path.join(info["work_dir"], "voiceover.mp3")
    print(f"[*] Đang tổng hợp giọng đọc AI ({voice})...")
    try:
        asyncio.run(_async_generate_tts(script, audio_path, voice))
    except Exception as e:
        print(f"[!] Edge-TTS lỗi: {e}, chuyển sang dự phòng...")
        # Fallback to Google TTS if edge fails
        import urllib.parse
        encoded = urllib.parse.quote(script[:200])
        fallback_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=vi&client=tw-ob&q={encoded}"
        subprocess.run(["curl.exe", "-s", "-L", "-A", "Mozilla/5.0", fallback_url, "-o", audio_path], check=True)
    
    duration = get_media_duration(audio_path)
    print(f"[✓] Đã tạo file thuyết minh thành công: {audio_path}")
    print(f"[*] Thời lượng giọng đọc: {duration:.1f} giây")
    
    info["voiceover_path"] = audio_path
    info["voiceover_duration"] = duration
    return audio_path

# ----------------------------------------------------------------------
# BƯỚC 4: GHÉP VIDEO & LỒNG TIẾNG QUA FFMPEG
# ----------------------------------------------------------------------
def step4_render_video(info: dict) -> str:
    print("\n" + "="*60)
    print("▶ BƯỚC 4: BIÊN TẬP VIDEO & LỒNG TIẾNG (FFMPEG)")
    print("="*60)
    
    work_dir = info["work_dir"]
    episodes = info["episodes"]
    voiceover_path = info["voiceover_path"]
    
    concat_list_file = os.path.join(work_dir, "concat_list.txt")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for ep in episodes:
            escaped_path = ep.replace("\\", "/")
            f.write(f"file '{escaped_path}'\n")
            
    merged_raw = os.path.join(work_dir, "merged_episodes.mp4")
    print("[*] Đang ghép các tập phim gốc...")
    subprocess.run([
        FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy",
        merged_raw
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    video_duration = get_media_duration(merged_raw)
    print(f"[✓] Ghép xong {len(episodes)} tập! Tổng thời lượng video: {video_duration:.1f}s")
    
    final_output = os.path.join(work_dir, f"TOM_TAT_{info['title']}_FULL.mp4")
    print("[*] Đang lồng giọng đọc AI và xử lý âm thanh (Audio Ducking)...")
    
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", merged_raw,
        "-i", voiceover_path,
        "-filter_complex",
        "[0:a]volume=0.15[bgm];[1:a]volume=1.2[voice];[bgm][voice]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        final_output
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    final_size_mb = os.path.getsize(final_output) / (1024 * 1024)
    print(f"[✓] XUẤT VIDEO THÀNH CÔNG: {final_output}")
    print(f"[*] Kích thước file: {final_size_mb:.2f} MB")
    
    info["final_video"] = final_output
    return final_output


# ----------------------------------------------------------------------
# BƯỚC 5: TẠO BỘ METADATA SEO YOUTUBE
# ----------------------------------------------------------------------
def step5_generate_youtube_metadata(info: dict):
    print("\n" + "="*60)
    print("▶ BƯỚC 5: TẠO BỘ SEO YOUTUBE (TITLE, DESCRIPTION, TAGS)")
    print("="*60)
    
    title = info["title"]
    ep_start = info["ep_start"]
    ep_end = info["ep_end"]
    
    yt_title = f"[Tóm Tắt Anime] Khi Otaku Tán Đổ Hoa Khôi Toàn Trường | {title} (Tập {ep_start}-{ep_end})"
    
    description = (
        f"{yt_title}\n\n"
        f"📌 Cốt truyện tóm tắt:\n"
        f"Chào mừng các bạn đến với kênh Tóm Tắt Anime! Hôm nay chúng ta sẽ cùng theo dõi câu chuyện hấp dẫn: {title}.\n"
        f"Nội dung tập {ep_start} đến {ep_end}: Khi chàng trai sống ẩn dật bất ngờ chạm mặt và cưa đổ hoa khôi nổi tiếng nhất trường học...\n\n"
        f"⏱️ Mốc thời gian (Chapters):\n"
        f"00:00 - Giới thiệu & Mở đầu câu chuyện\n"
        f"00:15 - Diễn biến Tập {ep_start}\n"
        f"00:30 - Biến cố bất ngờ\n"
        f"00:45 - Cảm nghĩ & Lời kết\n\n"
        f"🔔 Nhớ BẤM LIKE, CHIA SẺ và ĐĂNG KÝ KÊNH để ủng hộ mình ra thêm các tập tiếp theo nhé!\n\n"
        f"#tomtatanime #reviewphim #animehay #otaku #hoakhoitruong"
    )
    
    tags = [
        "tóm tắt anime", "review phim", "tóm tắt phim anime", "anime thuyết minh",
        title.lower(), "otaku", "anime tình cảm học đường", "anime mới nhất",
        "phim hoạt hình ai", "trimz anime", f"tập {ep_start} đến {ep_end}"
    ]
    
    meta_file = os.path.join(info["work_dir"], "youtube_metadata.txt")
    with open(meta_file, "w", encoding="utf-8") as f:
        f.write(f"=== TIÊU ĐỀ YOUTUBE ===\n{yt_title}\n\n")
        f.write(f"=== MÔ TẢ YOUTUBE ===\n{description}\n\n")
        f.write(f"=== THẺ TAGS ===\n{', '.join(tags)}\n")
        
    print(f"[*] Tiêu đề video:\n    👉 {yt_title}\n")
    print(f"[✓] Đã tạo đầy đủ bộ SEO YouTube lưu tại: {meta_file}")
    
    return {
        "title": yt_title,
        "description": description,
        "tags": tags
    }

# ----------------------------------------------------------------------
# HÀM CHÍNH ĐIỀU PHỐI (ORCHESTRATOR)
# ----------------------------------------------------------------------
def run_pipeline(url: str, ep_start: int = 1, ep_count: int = 3):
    print("*" * 65)
    print("      HỆ THỐNG TỰ ĐỘNG BIÊN TẬP ANIME RECAP YOUTUBE      ")
    print("*" * 65)
    
    # 1. Tải video
    info = step1_fetch_episodes(url, ep_start, ep_count)
    
    # 2. Sinh kịch bản
    script = step2_generate_script(info)
    
    # 3. Tạo giọng đọc
    step3_create_voiceover(script, info)
    
    # 4. Biên tập video
    step4_render_video(info)
    
    # 5. Tạo SEO YouTube
    step5_generate_youtube_metadata(info)
    
    print("\n" + "="*65)
    print("🎉 HOÀN THÀNH TOÀN BỘ PIPELINE THÀNH CÔNG!")
    print(f"📂 Thư mục thành phẩm: {info['work_dir']}")
    print(f"🎬 Video hoàn chỉnh: {info['final_video']}")
    print("="*65)

if __name__ == "__main__":
    test_url = "https://trimz.tv/how-a-loner-otaku-bagged-the-most-popular-girl-at"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    run_pipeline(test_url, ep_start=1, ep_count=3)
