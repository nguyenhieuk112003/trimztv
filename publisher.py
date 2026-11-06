# -*- coding: utf-8 -*-
"""
================================================================================
MULTI-CHANNEL & MULTI-PLATFORM PUBLISHER (YOUTUBE & FACEBOOK)
================================================================================
Điều phối xuất bản tự động theo từng Kênh / Trang độc lập:
- Kênh 1: Phim gốc (Raw Full 1080p)   -> YouTube Kênh 1 & Facebook Fanpage 1
- Kênh 2: Review Anime tiếng Anh      -> YouTube Kênh 2 & Facebook Fanpage 2
- Kênh 3: Tóm tắt Anime tiếng Việt    -> YouTube Kênh 3 & Facebook Fanpage 3
Tích hợp:
- Tự động thử lại (Retry & Backoff) khi gặp lỗi mạng/kết nối
- Khôi phục trạng thái (Checkpointed state): nền tảng nào đã đăng xong thì bỏ qua,
  chỉ đăng nốt nền tảng bị lỗi, tuyệt đối không đăng trùng
- Quy tắc an toàn thép: chỉ xóa video khi TẤT CẢ các nền tảng được bật đều thành công 100%
================================================================================
"""

import os
import sys
import json
import time
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

    # Khôi phục trạng thái xuất bản trước đó từ file payload (nếu đã có lần thử trước)
    if payload_json_path and os.path.isfile(payload_json_path):
        try:
            with open(payload_json_path, "r", encoding="utf-8") as f_prev:
                prev_data = json.load(f_prev)
                prev_res = prev_data.get("distribution_results", {})
                if prev_res.get("youtube_video_id"):
                    results["youtube_video_id"] = prev_res["youtube_video_id"]
                    results["youtube_url"] = prev_res.get("youtube_url")
                if prev_res.get("facebook_video_id"):
                    results["facebook_video_id"] = prev_res["facebook_video_id"]
                    results["facebook_url"] = prev_res.get("facebook_url")
        except Exception:
            pass

    dist_cfg = config.get("channels_distribution", {}).get(channel_key, {})
    channel_name = dist_cfg.get("name", channel_key.upper())

    # Tìm kiếm ảnh Thumbnail tùy chỉnh nếu có
    thumb_path = metadata.get("thumbnail_path")
    if not thumb_path or not os.path.isfile(thumb_path):
        v_dir = os.path.dirname(video_path)
        v_base = os.path.splitext(os.path.basename(video_path))[0]
        for candidate_name in [
            f"{v_base}_thumbnail.jpg",
            f"{v_base}_THUMBNAIL.jpg",
            f"{v_base}_THUMBNAIL_VI.jpg",
            f"{v_base}_THUMBNAIL_EN.jpg",
            "thumbnail.jpg"
        ]:
            c_path = os.path.join(v_dir, candidate_name)
            if os.path.isfile(c_path):
                thumb_path = os.path.abspath(c_path)
                break

    print(f"\n📡 [PHÂN PHỐI ĐA NỀN TẢNG] -> {channel_name}")

    # 1. ĐĂNG LÊN YOUTUBE NẾU BẬT
    yt_cfg = dist_cfg.get("youtube", {})
    if not yt_cfg:
        legacy_yt = config.get("youtube_upload", {})
        if legacy_yt.get("enabled", False):
            yt_cfg = legacy_yt

    if results.get("youtube_video_id"):
        print(f"   [✓] YouTube ({channel_name}): Đã đăng thành công trước đó (ID: {results['youtube_video_id']}), bỏ qua không đăng lại.")
    elif yt_cfg.get("enabled", False):
        token_file = yt_cfg.get("token_file", f"tokens/yt_{channel_key}.json")
        secrets_file = yt_cfg.get("client_secrets_file", f"client_secrets_{channel_key}.json")
        privacy_status = yt_cfg.get("privacy_status", "unlisted")
        category_id = yt_cfg.get("category_id", "1")

        secrets_full = os.path.join(BASE_DIR, secrets_file) if not os.path.isabs(secrets_file) else secrets_file
        token_full = os.path.join(BASE_DIR, token_file) if not os.path.isabs(token_file) else token_file

        if not os.path.isfile(secrets_full):
            fallback_secrets = os.path.join(BASE_DIR, "client_secrets.json")
            if os.path.isfile(fallback_secrets):
                secrets_full = fallback_secrets

        if os.path.isfile(secrets_full) or os.path.isfile(token_full):
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    from youtube_uploader import upload_video_to_youtube
                    print(f"   🚀 Đang tải lên YouTube ({channel_name}) với token: {os.path.basename(token_full)} (lần {attempt}/{max_retries})...")
                    vid = upload_video_to_youtube(
                        video_path=video_path,
                        metadata=metadata,
                        client_secrets_file=secrets_full,
                        token_file=token_full,
                        privacy_status=privacy_status,
                        category_id=category_id,
                        thumbnail_path=thumb_path
                    )
                    results["youtube_video_id"] = vid
                    results["youtube_url"] = f"https://youtu.be/{vid}"
                    metadata["youtube_video_id"] = vid
                    metadata["youtube_url"] = results["youtube_url"]
                    break
                except Exception as e_yt:
                    if attempt < max_retries:
                        wait_sec = 5 * attempt
                        print(f"   [!] Lỗi khi upload YouTube ({channel_name}): {e_yt}. Tự động thử lại sau {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        print(f"   [X] Thất bại sau {max_retries} lần thử upload YouTube ({channel_name}): {e_yt}")
        else:
            print(f"   [i] Bỏ qua YouTube ({channel_name}): Chưa có file secrets ({os.path.basename(secrets_full)}) hoặc token ({os.path.basename(token_full)}).")

    # 2. ĐĂNG LÊN FACEBOOK NẾU BẬT
    fb_cfg = dist_cfg.get("facebook", {})
    if results.get("facebook_video_id"):
        print(f"   [✓] Facebook ({channel_name}): Đã đăng thành công trước đó (ID: {results['facebook_video_id']}), bỏ qua không đăng lại.")
    elif fb_cfg.get("enabled", False):
        page_id = (fb_cfg.get("page_id", "").strip() or
                   os.environ.get(f"FB_PAGE_ID_{channel_key.upper()}", "").strip() or
                   os.environ.get("FB_PAGE_ID", "").strip())
        access_token = (fb_cfg.get("access_token", "").strip() or
                        os.environ.get(f"FB_ACCESS_TOKEN_{channel_key.upper()}", "").strip() or
                        os.environ.get("FB_ACCESS_TOKEN", "").strip())
        published = fb_cfg.get("published", True)

        if page_id and access_token:
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    from facebook_uploader import upload_video_to_facebook
                    print(f"   📘 Đang tải lên Facebook Fanpage ({channel_name}) - Page ID: {page_id} (lần {attempt}/{max_retries})...")
                    fb_vid = upload_video_to_facebook(
                        video_path=video_path,
                        metadata=metadata,
                        page_id=page_id,
                        access_token=access_token,
                        published=published,
                        thumbnail_path=thumb_path
                    )
                    results["facebook_video_id"] = fb_vid
                    results["facebook_url"] = f"https://www.facebook.com/{fb_vid}"
                    metadata["facebook_video_id"] = fb_vid
                    metadata["facebook_url"] = results["facebook_url"]
                    break
                except Exception as e_fb:
                    if attempt < max_retries:
                        wait_sec = 5 * attempt
                        print(f"   [!] Lỗi khi upload Facebook ({channel_name}): {e_fb}. Tự động thử lại sau {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        print(f"   [X] Thất bại sau {max_retries} lần thử upload Facebook ({channel_name}): {e_fb}")
        else:
            print(f"   [i] Bỏ qua Facebook ({channel_name}): Chưa điền page_id hoặc access_token trong config.json.")

    # Cập nhật kết quả vào file JSON payload nếu có để ghi nhớ trạng thái
    if payload_json_path:
        try:
            metadata["published_at"] = datetime.now().isoformat()
            metadata["distribution_results"] = results
            with open(payload_json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # 3. TỰ ĐỘNG XÓA FILE VIDEO DÀI SAU KHI ĐĂNG THÀNH CÔNG NẾU BẬT CẤU HÌNH DỌN DẸP
    if config.get("cleanup_published_videos", True):
        yt_is_on = yt_cfg.get("enabled", False)
        fb_is_on = fb_cfg.get("enabled", False)
        if yt_is_on or fb_is_on:
            yt_ok = (results["youtube_video_id"] is not None) if yt_is_on else True
            fb_ok = (results["facebook_video_id"] is not None) if fb_is_on else True

            if yt_ok and fb_ok and channel_key != "kenh_1_raw":
                if os.path.isfile(video_path):
                    try:
                        sz_mb = os.path.getsize(video_path) / (1024 * 1024)
                        os.remove(video_path)
                        print(f"   🧹 [DỌN DẸP Ổ CỨNG] Đã đăng thành công cả YouTube & Facebook ({channel_name})! Tự động xóa {os.path.basename(video_path)} ({sz_mb:.1f} MB) để nhẹ máy.")
                    except Exception as e_del:
                        print(f"   [!] Không thể xóa video {os.path.basename(video_path)}: {e_del}")
                if thumb_path and os.path.isfile(thumb_path):
                    try:
                        os.remove(thumb_path)
                    except Exception:
                        pass
            elif not (yt_ok and fb_ok):
                yt_status_str = "✓ Thành công" if yt_ok else "✗ Chưa xong"
                fb_status_str = "✓ Thành công" if fb_ok else "✗ Chưa xong"
                print(f"   🔒 [BẢO TỒN VIDEO] Chưa hoàn tất tất cả nền tảng bật (YouTube: {yt_status_str} | Facebook: {fb_status_str}).")
                print(f"      -> Giữ nguyên file {os.path.basename(video_path)} trên ổ cứng để tự động thử lại ở chu kỳ tiếp theo!")

    return results
