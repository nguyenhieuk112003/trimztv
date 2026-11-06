# -*- coding: utf-8 -*-
"""
================================================================================
MULTI-CHANNEL & MULTI-PLATFORM PUBLISHER (YOUTUBE & FACEBOOK)
================================================================================
Điều phối xuất bản tự động theo từng Kênh / Trang độc lập:
- Kênh 1: Phim gốc (Raw Full 1080p)   -> YouTube Kênh 1 & Facebook Fanpage 1
- Kênh 2: Review Anime tiếng Anh      -> YouTube Kênh 2 & Facebook Fanpage 2
- Kênh 3: Tóm tắt Anime tiếng Việt    -> YouTube Kênh 3 & Facebook Fanpage 3
================================================================================
"""

import os
import sys
import json
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_dotenv():
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as ef:
                for line in ef:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass

load_dotenv()


def publish_to_channel(channel_key: str, video_path: str, metadata: dict, config: dict, payload_json_path: str = None) -> dict:
    """
    Tự động phân phối video vào đúng Kênh YouTube và Fanpage Facebook được cấu hình cho channel_key.
    channel_key: 'kenh_1_raw', 'kenh_2_en', 'kenh_3_vi'
    """
    results = {
        "channel_key": channel_key,
        "youtube_video_id": None,
        "youtube_url": None,
        "facebook_video_id": None,
        "facebook_url": None
    }

    if not os.path.isfile(video_path):
        print(f"[!] Không tìm thấy file video để đăng: {video_path}")
        return results

    dist_cfg = config.get("channels_distribution", {}).get(channel_key, {})
    channel_name = dist_cfg.get("name", channel_key.upper())

    print(f"\n📡 [PHÂN PHỐI ĐA NỀN TẢNG] -> {channel_name}")

    # 1. ĐĂNG LÊN YOUTUBE NẾU BẬT
    yt_cfg = dist_cfg.get("youtube", {})
    # Fallback kiểm tra cấu hình youtube_upload chung
    if not yt_cfg:
        legacy_yt = config.get("youtube_upload", {})
        if legacy_yt.get("enabled", False):
            yt_cfg = legacy_yt

    if yt_cfg.get("enabled", False):
        token_file = yt_cfg.get("token_file", f"tokens/yt_{channel_key}.json")
        secrets_file = yt_cfg.get("client_secrets_file", f"client_secrets_{channel_key}.json")
        privacy_status = yt_cfg.get("privacy_status", "unlisted")
        category_id = yt_cfg.get("category_id", "1")

        secrets_full = os.path.join(BASE_DIR, secrets_file) if not os.path.isabs(secrets_file) else secrets_file
        token_full = os.path.join(BASE_DIR, token_file) if not os.path.isabs(token_file) else token_file

        # Fallback dùng client_secrets.json nếu file riêng không tồn tại
        if not os.path.isfile(secrets_full):
            fallback_secrets = os.path.join(BASE_DIR, "client_secrets.json")
            if os.path.isfile(fallback_secrets):
                secrets_full = fallback_secrets

        if os.path.isfile(secrets_full) or os.path.isfile(token_full):
            try:
                from youtube_uploader import upload_video_to_youtube
                print(f"   🚀 Đang tải lên YouTube ({channel_name}) với token: {os.path.basename(token_full)}...")
                vid = upload_video_to_youtube(
                    video_path=video_path,
                    metadata=metadata,
                    client_secrets_file=secrets_full,
                    token_file=token_full,
                    privacy_status=privacy_status,
                    category_id=category_id
                )
                results["youtube_video_id"] = vid
                results["youtube_url"] = f"https://youtu.be/{vid}"
                metadata["youtube_video_id"] = vid
                metadata["youtube_url"] = results["youtube_url"]
            except Exception as e_yt:
                print(f"   [!] Lỗi khi upload YouTube ({channel_name}): {e_yt}")
        else:
            print(f"   [i] Bỏ qua YouTube ({channel_name}): Chưa có file secrets ({os.path.basename(secrets_full)}) hoặc token ({os.path.basename(token_full)}).")

    # 2. ĐĂNG LÊN FACEBOOK NẾU BẬT
    fb_cfg = dist_cfg.get("facebook", {})
    if fb_cfg.get("enabled", False):
        page_id = (fb_cfg.get("page_id", "").strip() or
                   os.environ.get(f"FB_PAGE_ID_{channel_key.upper()}", "").strip() or
                   os.environ.get("FB_PAGE_ID", "").strip())
        access_token = (fb_cfg.get("access_token", "").strip() or
                        os.environ.get(f"FB_ACCESS_TOKEN_{channel_key.upper()}", "").strip() or
                        os.environ.get("FB_ACCESS_TOKEN", "").strip())
        published = fb_cfg.get("published", True)

        if page_id and access_token:
            try:
                from facebook_uploader import upload_video_to_facebook
                print(f"   📘 Đang tải lên Facebook Fanpage ({channel_name}) - Page ID: {page_id}...")
                fb_vid = upload_video_to_facebook(
                    video_path=video_path,
                    metadata=metadata,
                    page_id=page_id,
                    access_token=access_token,
                    published=published
                )
                results["facebook_video_id"] = fb_vid
                results["facebook_url"] = f"https://www.facebook.com/{fb_vid}"
                metadata["facebook_video_id"] = fb_vid
                metadata["facebook_url"] = results["facebook_url"]
            except Exception as e_fb:
                print(f"   [!] Lỗi khi upload Facebook ({channel_name}): {e_fb}")
        else:
            print(f"   [i] Bỏ qua Facebook ({channel_name}): Chưa điền page_id hoặc access_token trong config.json.")

    # Cập nhật kết quả vào file JSON payload nếu có
    if payload_json_path:
        try:
            metadata["published_at"] = datetime.now().isoformat()
            metadata["distribution_results"] = results
            with open(payload_json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return results
