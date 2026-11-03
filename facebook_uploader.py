# -*- coding: utf-8 -*-
"""
================================================================================
FACEBOOK AUTO UPLOADER - TỰ ĐỘNG ĐĂNG VIDEO LÊN FANPAGE QUA GRAPH API (RESUMABLE)
================================================================================
- Hỗ trợ tải video dài 15 - 40 phút lên Facebook Fanpage
- Giao thức Resumable Upload (chia nhỏ phân đoạn 4MB/chunk chống nghẽn mạng)
- Tự động gán Tiêu đề (Title), Nội dung mô tả (Description)
- Hỗ trợ nhiều Fanpage độc lập (Kênh 1 Raw, Kênh 2 Review EN, Kênh 3 Review VI)
- Trả về Facebook Video ID và Link xem trực tiếp
================================================================================
"""

import os
import sys
import json
import time
import argparse
import requests

# Đảm bảo console UTF-8 trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_API_VERSION = "v19.0"
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB / chunk


def upload_video_to_facebook(video_path: str, metadata: dict,
                             page_id: str, access_token: str,
                             published: bool = True) -> str:
    """
    Tải video lên Facebook Fanpage qua Meta Graph API bằng giao thức Resumable Upload.
    Trả về facebook_video_id nếu thành công.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")

    if not page_id or not access_token:
        raise ValueError("Chưa cung cấp page_id hoặc access_token của Facebook Fanpage.")

    file_size = os.path.getsize(video_path)
    sz_mb = file_size / (1024 * 1024)

    title = metadata.get("title", os.path.basename(video_path))
    description = metadata.get("description", "")

    endpoint = f"https://graph-video.facebook.com/{GRAPH_API_VERSION}/{page_id}/videos"

    print(f"\n📘 ĐANG TẢI VIDEO LÊN FACEBOOK FANPAGE (Page ID: {page_id})")
    print(f"   🎬 File: {os.path.basename(video_path)} ({sz_mb:.1f} MB)")
    print(f"   📌 Tiêu đề: {title[:80]}...")
    print(f"   🔒 Trạng thái xuất bản: {'Công khai' if published else 'Bản nháp'}")

    # BƯỚC 1: KHỞI TẠO PHIÊN UPLOAD (START PHASE)
    init_payload = {
        "upload_phase": "start",
        "file_size": file_size,
        "access_token": access_token
    }

    try:
        res_init = requests.post(endpoint, data=init_payload, timeout=30)
        res_init.raise_for_status()
        init_data = res_init.json()
    except Exception as e:
        err_msg = res_init.text if 'res_init' in locals() and res_init is not None else str(e)
        raise RuntimeError(f"Lỗi khởi tạo upload Facebook: {err_msg}")

    upload_session_id = init_data.get("upload_session_id")
    video_id = init_data.get("video_id")
    start_offset = int(init_data.get("start_offset", 0))
    end_offset = int(init_data.get("end_offset", min(file_size, start_offset + CHUNK_SIZE)))

    if not upload_session_id:
        raise RuntimeError(f"Facebook không trả về upload_session_id: {init_data}")

    # BƯỚC 2: TRUYỀN PHÂN ĐOẠN (TRANSFER PHASE)
    with open(video_path, "rb") as f:
        while start_offset < file_size:
            chunk_length = end_offset - start_offset
            f.seek(start_offset)
            chunk_data = f.read(chunk_length)

            transfer_payload = {
                "upload_phase": "transfer",
                "upload_session_id": upload_session_id,
                "start_offset": start_offset,
                "access_token": access_token
            }
            files = {
                "video_file_chunk": ("chunk", chunk_data, "application/octet-stream")
            }

            retries = 0
            transfer_ok = False
            while not transfer_ok and retries < 5:
                try:
                    res_trans = requests.post(endpoint, data=transfer_payload, files=files, timeout=90)
                    res_trans.raise_for_status()
                    trans_data = res_trans.json()
                    new_start = int(trans_data.get("start_offset", 0))
                    new_end = int(trans_data.get("end_offset", 0))

                    percent = min(100, int((start_offset + chunk_length) / file_size * 100))
                    print(f"\r   -> Tiến độ tải lên Facebook: {percent}% [{((start_offset + chunk_length)/(1024*1024)):.1f}/{sz_mb:.1f} MB]", end="", flush=True)

                    start_offset = new_start
                    end_offset = new_end
                    transfer_ok = True
                except Exception as e:
                    retries += 1
                    sleep_sec = 2 ** retries
                    print(f"\n   [!] Lỗi phân đoạn ({e}), thử lại lần {retries} sau {sleep_sec}s...")
                    time.sleep(sleep_sec)

            if not transfer_ok:
                raise RuntimeError(f"Thất bại sau 5 lần thử tải phân đoạn tại offset {start_offset}")

            if start_offset >= end_offset or start_offset >= file_size:
                break

    print()

    # BƯỚC 3: HOÀN TẤT VÀ XUẤT BẢN (FINISH PHASE)
    finish_payload = {
        "upload_phase": "finish",
        "upload_session_id": upload_session_id,
        "title": title,
        "description": description,
        "published": "true" if published else "false",
        "access_token": access_token
    }

    try:
        res_finish = requests.post(endpoint, data=finish_payload, timeout=60)
        res_finish.raise_for_status()
        finish_data = res_finish.json()
        if finish_data.get("success") is True:
            fb_url = f"https://www.facebook.com/{video_id}"
            print(f"   🎉 [THÀNH CÔNG] Video đã đăng lên Facebook Fanpage!")
            print(f"   👉 Link video: {fb_url}")
            return str(video_id)
        else:
            raise RuntimeError(f"Facebook finish thất bại: {finish_data}")
    except Exception as e:
        err_msg = res_finish.text if 'res_finish' in locals() and res_finish is not None else str(e)
        raise RuntimeError(f"Lỗi hoàn tất xuất bản Facebook: {err_msg}")


def main():
    parser = argparse.ArgumentParser(description="Facebook Video Uploader tự động qua Meta Graph API")
    parser.add_argument("--video", required=True, help="Đường dẫn file video (.mp4)")
    parser.add_argument("--page-id", required=True, help="ID của Facebook Fanpage")
    parser.add_argument("--token", required=True, help="Page Access Token của Fanpage")
    parser.add_argument("--metadata", help="Đường dẫn file metadata (.json hoặc .txt)")
    parser.add_argument("--title", help="Tiêu đề video nếu không dùng file metadata")
    parser.add_argument("--description", help="Mô tả video nếu không dùng file metadata")
    parser.add_argument("--draft", action="store_true", help="Lưu dạng bản nháp không công khai ngay")
    args = parser.parse_args()

    meta = {}
    if args.metadata and os.path.isfile(args.metadata):
        if args.metadata.endswith(".json"):
            with open(args.metadata, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            with open(args.metadata, "r", encoding="utf-8") as f:
                raw_text = f.read()
            import re
            m_title = re.search(r'=== TIÊU ĐỀ.*?===\s*\n(.*?)\n\n', raw_text, re.DOTALL)
            m_desc = re.search(r'=== MÔ TẢ.*?===\s*\n(.*?)\n\n===', raw_text, re.DOTALL)
            meta = {
                "title": m_title.group(1).strip() if m_title else os.path.basename(args.video),
                "description": m_desc.group(1).strip() if m_desc else ""
            }
    else:
        meta = {
            "title": args.title or os.path.basename(args.video),
            "description": args.description or ""
        }

    try:
        vid = upload_video_to_facebook(
            video_path=args.video,
            metadata=meta,
            page_id=args.page_id,
            access_token=args.token,
            published=not args.draft
        )
        print(f"\n[V] Đã hoàn tất upload Facebook Video ID: {vid}")
    except Exception as e:
        print(f"\n[X] Thất bại khi upload Facebook: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

