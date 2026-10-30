"""
Trimz.tv Video Downloader (Python)
Tải video và series phim tự động từ Trimz.tv
"""

import os
import re
import sys
import urllib.request

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def download_video(url: str, dest_path: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
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
                print(f"\r    Tiến độ: {percent:.1f}% ({downloaded / (1024*1024):.1f}/{total / (1024*1024):.1f} MB)", end="", flush=True)
        print()

def main():
    print("=" * 55)
    print("         TRIMZ.TV VIDEO DOWNLOADER (PYTHON)        ")
    print("=" * 55)

    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = input("Nhập URL phim trên Trimz (ví dụ https://trimz.tv/ten-phim): ").strip()

    if not target_url:
        print("[!] URL không hợp lệ.")
        return

    if not target_url.startswith("http"):
        target_url = "https://trimz.tv/" + target_url.lstrip("/")

    print(f"\n[*] Đang kết nối tới: {target_url} ...")
    req = urllib.request.Request(target_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[!] Lỗi khi tải trang: {e}")
        return

    # Trích xuất tiêu đề
    title_match = re.search(r'<title>([^<]+)</title>', html)
    title = "Trimz_Show"
    if title_match:
        title = title_match.group(1).split(" - Trimz")[0].split(" | Trimz")[0].split(": Watch & Create Shows")[0]
    safe_title = sanitize_filename(title)
    print(f"[*] Tiêu đề: {safe_title}")

    # Tìm các link MP4
    mp4_pattern = r'https://cdn\.trimz\.co/generated-videos/ms_videos/[a-zA-Z0-9_\-]+\.mp4'
    found_urls = re.findall(mp4_pattern, html)
    video_urls = []
    seen = set()
    for u in found_urls:
        if u not in seen:
            seen.add(u)
            video_urls.append(u)

    if not video_urls:
        print("[!] Không tìm thấy video MP4 nào. Vui lòng kiểm tra lại link.")
        return

    print(f"[+] Tìm thấy tổng cộng {len(video_urls)} tập phim!")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads", safe_title)
    os.makedirs(output_dir, exist_ok=True)
    print(f"[*] Thư mục lưu: {output_dir}\n")

    print("Chọn chế độ:")
    print(f"  [1] Tải tất cả {len(video_urls)} tập (gõ 'all' hoặc Enter)")
    print("  [2] Tải khoảng tập (ví dụ: 1-10)")
    print("  [3] Tải tập cụ thể (ví dụ: 1,3,5)")
    print("  [4] Xuất danh sách link ra file text (để nạp vào IDM)")

    choice = input("Lựa chọn của bạn: ").strip() or "all"

    if choice == "4":
        txt_file = os.path.join(output_dir, "links.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("\n".join(video_urls))
        print(f"[V] Đã xuất danh sách vào: {txt_file}")
        return

    indices = []
    if choice == "1" or choice.lower() == "all":
        indices = list(range(len(video_urls)))
    elif "-" in choice:
        try:
            start_s, end_s = choice.split("-")
            start = max(1, int(start_s))
            end = min(len(video_urls), int(end_s))
            indices = list(range(start - 1, end))
        except Exception:
            indices = list(range(len(video_urls)))
    else:
        for p in re.split(r'[,;\s]+', choice):
            if p.isdigit():
                idx = int(p) - 1
                if 0 <= idx < len(video_urls):
                    indices.append(idx)

    for i, idx in enumerate(indices, 1):
        ep_num = idx + 1
        filename = f"Tap_{ep_num:03d}.mp4"
        dest_path = os.path.join(output_dir, filename)
        v_url = video_urls[idx]

        print(f"[{i}/{len(indices)}] Đang tải Tập {ep_num} ({filename})...")
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 102400:
            print(f"    -> Đã tồn tại, bỏ qua.")
            continue

        try:
            download_video(v_url, dest_path)
            print(f"    -> [OK] Hoàn thành ({os.path.getsize(dest_path) / (1024*1024):.2f} MB)")
        except Exception as e:
            print(f"    -> [X] Lỗi: {e}")

    print("\n[V] ĐÃ HOÀN TẤT TẢI VIDEO!")

if __name__ == "__main__":
    main()
