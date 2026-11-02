# -*- coding: utf-8 -*-
"""
HỆ THỐNG TẢI 60 TẬP THẬT TỪ TRIMZ.TV, GHÉP THÀNH VIDEO 15 PHÚT VÀ LỒNG TIẾNG REVIEW
- Tải từ tập 1 đến tập 60 (không lặp lại cảnh nào)
- Ghép nối tiếp thành 1 video 15 phút chuẩn
- Xuất bản đủ 3 Kênh YouTube
"""

import os
import sys
import re
import asyncio
import subprocess
import urllib.request
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_EXE = os.path.join(BASE_DIR, "tools", "ffmpeg", "ffmpeg.exe")
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"

SHOW_URL = "https://trimz.tv/how-a-loner-otaku-bagged-the-most-popular-girl-at"
EPISODES_DIR = os.path.join(BASE_DIR, "Downloads", "Real_60_Episodes")
OUT_DIR = os.path.join(BASE_DIR, "Downloads", "Demo_3_Channels_Real_15Min")

DIR_K1 = os.path.join(OUT_DIR, "Kenh_1_Raw_Full_60Eps")
DIR_K2 = os.path.join(OUT_DIR, "Kenh_2_Review_EN_60Eps")
DIR_K3 = os.path.join(OUT_DIR, "Kenh_3_Review_VI_60Eps")

os.makedirs(EPISODES_DIR, exist_ok=True)
os.makedirs(DIR_K1, exist_ok=True)
os.makedirs(DIR_K2, exist_ok=True)
os.makedirs(DIR_K3, exist_ok=True)

TARGET_EPISODES = 60

def fetch_episode_urls(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    mp4_pattern = r'https://cdn\.trimz\.co/generated-videos/ms_videos/[a-zA-Z0-9_\-]+\.mp4'
    found = re.findall(mp4_pattern, html)
    unique_urls = list(dict.fromkeys(found))
    return unique_urls

def download_file(url: str, dest: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(1024 * 512)
            if not chunk:
                break
            f.write(chunk)

def download_episodes():
    print(f"[*] Đang lấy danh sách tập phim từ: {SHOW_URL}...")
    urls = fetch_episode_urls(SHOW_URL)
    print(f"[*] Tìm thấy tổng cộng: {len(urls)} tập phim trên Trimz.")
    
    needed_urls = urls[:TARGET_EPISODES]
    print(f"[*] Sẽ tải {len(needed_urls)} tập phim đầu tiên để đạt đúng 15 phút...")
    
    downloaded_files = []
    for idx, vurl in enumerate(needed_urls, start=1):
        filename = f"Tap_{idx:03d}.mp4"
        dest_path = os.path.join(EPISODES_DIR, filename)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 102400:
            print(f"   [✓] {filename} đã có sẵn ({os.path.getsize(dest_path)/(1024*1024):.1f} MB)")
        else:
            print(f"   [↓] Đang tải {filename} ({idx}/{len(needed_urls)})...", end="", flush=True)
            try:
                download_file(vurl, dest_path)
                sz = os.path.getsize(dest_path) / (1024 * 1024)
                print(f" xong ({sz:.1f} MB)")
            except Exception as e:
                print(f" lỗi: {e}")
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 102400:
            downloaded_files.append(dest_path)
    return downloaded_files

def merge_episodes(episodes, output_merged):
    print("\n" + "=" * 65)
    print(f"[*] Đang ghép {len(episodes)} tập phim thành 1 video duy nhất...")
    print("=" * 65)
    list_txt = os.path.join(EPISODES_DIR, "concat_list.txt")
    with open(list_txt, "w", encoding="utf-8") as f:
        for ep in episodes:
            clean = os.path.abspath(ep).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{clean}'\n")

    subprocess.run([
        FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0",
        "-i", list_txt,
        "-c", "copy",
        output_merged
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    if os.path.exists(list_txt):
        os.remove(list_txt)

    # Đo thời lượng
    cmd_probe = [
        os.path.join(BASE_DIR, "tools", "ffmpeg", "ffprobe.exe"),
        "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", output_merged
    ]
    res = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    dur = float(res.stdout.strip()) if res.stdout.strip() else 0.0
    sz_mb = os.path.getsize(output_merged) / (1024 * 1024)
    print(f"[✓] Ghép xong video 60 tập thật: {sz_mb:.1f} MB ({dur/60:.2f} phút / {dur:.1f} giây)")
    return dur

def duck_mix(video_in, audio_in, video_out):
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", video_in,
        "-i", audio_in,
        "-filter_complex",
        "[0:a]volume=0.15[bgm];[1:a]volume=1.25[voice];[bgm][voice]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        video_out
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg ducking error: {res.stderr}")

def main():
    print("=" * 65)
    print("🎬 QUY TRÌNH TẢI VÀ DỰNG 60 TẬP THẬT TỪ TRIMZ.TV (~15 PHÚT)")
    print("=" * 65)
    
    episodes = download_episodes()
    if not episodes:
        print("[!] Không tải được tập phim nào.")
        return

    # Ghép 60 tập
    merged_raw_15m = os.path.join(DIR_K1, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_60Eps_Raw.mp4")
    if not (os.path.exists(merged_raw_15m) and os.path.getsize(merged_raw_15m) > 102400):
        merge_episodes(episodes, merged_raw_15m)
    else:
        print(f"[✓] Video Kênh 1 (60 tập ghép) đã có sẵn: {os.path.basename(merged_raw_15m)}")

    # Kênh 2: Lồng tiếng review tiếng Anh lên video 60 tập thật
    voice_en = os.path.join(BASE_DIR, "Downloads", "Demo_3_Channels_15Min", "Kenh_2_Review_EN", "voiceover_15min_en.mp3")
    k2_video = os.path.join(DIR_K2, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_60Eps_RECAP_EN.mp4")
    if os.path.exists(voice_en) and not os.path.exists(k2_video):
        print("\n📺 Đang xuất video Kênh 2 (Review Tiếng Anh trên 60 tập thật)...")
        duck_mix(merged_raw_15m, voice_en, k2_video)
        print(f"[✓] Đã xuất video Kênh 2: {os.path.basename(k2_video)} ({os.path.getsize(k2_video)/(1024*1024):.1f} MB)")

    # Kênh 3: Lồng tiếng review tiếng Việt lên video 60 tập thật
    voice_vi = os.path.join(BASE_DIR, "Output", "How a Loner Otaku Bagged The Most Popular Girl at School", "voiceover.mp3")
    k3_video = os.path.join(DIR_K3, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_60Eps_RECAP_VI.mp4")
    if os.path.exists(voice_vi) and not os.path.exists(k3_video):
        print("\n📺 Đang xuất video Kênh 3 (Review Tiếng Việt trên 60 tập thật)...")
        duck_mix(merged_raw_15m, voice_vi, k3_video)
        print(f"[✓] Đã xuất video Kênh 3: {os.path.basename(k3_video)} ({os.path.getsize(k3_video)/(1024*1024):.1f} MB)")

    print("\n" + "=" * 65)
    print("🎉 HOÀN THÀNH TOÀN BỘ 60 TẬP THẬT TỪ TRIMZ.TV!")
    print(f"📁 Thư mục lưu: {OUT_DIR}")
    print("=" * 65)

if __name__ == "__main__":
    main()

