# -*- coding: utf-8 -*-
"""
================================================================================
YOUTUBE AUTO UPLOADER - TỰ ĐỘNG ĐĂNG VIDEO LÊN YOUTUBE QUA API V3
================================================================================
- Tự động xác thực OAuth 2.0 (lưu phiên vào token.json, chỉ cần đăng nhập 1 lần)
- Tự động gán Tiêu đề, Mô tả đầy đủ Chapters, Thẻ Tags chuẩn SEO
- Upload phân đoạn resumable upload (chống đứt mạng giữa chừng với video lớn)
- Hỗ trợ chế độ đăng: 'private' (Riêng tư), 'unlisted' (Không công khai), 'public' (Công khai)
================================================================================
"""

import os
import sys
import json
import time
import argparse
import http.client
import httplib2
import random

# Đảm bảo console UTF-8 trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Thử lại nếu gặp lỗi mạng tạm thời
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine
)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]


def get_authenticated_service(client_secrets_file: str = "client_secrets.json", token_file: str = "token.json"):
    """
    Xác thực tài khoản YouTube qua OAuth 2.0.
    Nếu đã có token.json hợp lệ thì tái sử dụng mà không cần mở trình duyệt lại.
    """
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    secrets_path = os.path.join(BASE_DIR, client_secrets_file) if not os.path.isabs(client_secrets_file) else client_secrets_file
    token_path = os.path.join(BASE_DIR, token_file) if not os.path.isabs(token_file) else token_file

    token_dir = os.path.dirname(token_path)
    if token_dir:
        os.makedirs(token_dir, exist_ok=True)

    creds = None
    if os.path.isfile(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"[!] Lỗi đọc {os.path.basename(token_path)}: {e}")

    # Nếu token chưa có hoặc hết hạn, tiến hành đăng nhập / refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
            except Exception as e:
                print(f"[!] Không thể làm mới token ({os.path.basename(token_path)}): {e}. Cần đăng nhập lại...")
                creds = None

        if not creds:
            if not os.path.isfile(secrets_path):
                raise FileNotFoundError(
                    f"Không tìm thấy file '{client_secrets_file}'. "
                    f"Vui lòng tải file OAuth Client ID từ Google Cloud Console và đặt vào: {secrets_path}"
                )
            print(f"[*] Đang mở trình duyệt để xác thực cho kênh YouTube ({os.path.basename(token_path)})...")
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print(f"[✓] Đã lưu phiên đăng nhập YouTube vào: {token_path}")

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)


def upload_video_to_youtube(video_path: str, metadata: dict,
                            client_secrets_file: str = "client_secrets.json",
                            token_file: str = "token.json",
                            privacy_status: str = "unlisted",
                            category_id: str = "1",
                            thumbnail_path: str = None) -> str:
    """
    Tải video lên YouTube kèm Tiêu đề, Mô tả, Tags tự động.
    Trả về YouTube Video ID nếu thành công.
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Không tìm thấy file video: {video_path}")

    youtube = get_authenticated_service(client_secrets_file, token_file)

    title = metadata.get("title", os.path.basename(video_path))
    if len(title) > 100:
        title = title[:97] + "..."

    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    # Giới hạn tags hợp lệ
    valid_tags = []
    total_tag_len = 0
    for t in tags:
        if total_tag_len + len(t) < 480:
            valid_tags.append(t)
            total_tag_len += len(t) + 1

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": valid_tags,
            "categoryId": str(category_id)
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    sz_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"\n🚀 ĐANG TẢI VIDEO LÊN YOUTUBE: {os.path.basename(video_path)} ({sz_mb:.1f} MB)")
    print(f"   📌 Tiêu đề: {title}")
    print(f"   🏷️ Số thẻ tags: {len(valid_tags)}")
    print(f"   🔒 Trạng thái đăng: {privacy_status.upper()}")

    # Chunk size: 5MB (5 * 1024 * 1024)
    media = MediaFileUpload(video_path, chunksize=5 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    error = None
    retry = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                print(f"\r   -> Tiến độ tải lên YouTube: {percent}%", end="", flush=True)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"Lỗi HTTP {e.resp.status}: {e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"Lỗi mạng: {e}"

        if error:
            print(f"\n   [!] Gặp sự cố: {error}")
            retry += 1
            if retry > 5:
                raise RuntimeError("Đã thử lại 5 lần thất bại khi upload YouTube.")
            sleep_sec = random.random() * (2 ** retry)
            print(f"   ⏳ Thử lại sau {sleep_sec:.1f} giây...")
            time.sleep(sleep_sec)
            error = None

    print()
    if response and "id" in response:
        video_id = response["id"]
        yt_url = f"https://youtu.be/{video_id}"
        print(f"   🎉 [THÀNH CÔNG] Video đã được đăng lên YouTube!")
        print(f"   👉 Link xem: {yt_url}")

        if thumbnail_path and os.path.isfile(thumbnail_path):
            try:
                print(f"   🖼️ Đang tải ảnh Thumbnail lên YouTube...")
                thumb_body = MediaFileUpload(thumbnail_path, mimetype="image/jpeg", resumable=True)
                youtube.thumbnails().set(videoId=video_id, media_body=thumb_body).execute()
                print(f"   [✓] YouTube: Cài đặt Thumbnail thành công!")
            except Exception as e_th:
                print(f"   [!] Lỗi cài đặt YouTube Thumbnail: {e_th}")

        return video_id
    else:
        raise RuntimeError(f"Upload hoàn tất nhưng không nhận được video ID: {response}")


def main():
    parser = argparse.ArgumentParser(description="YouTube Video Uploader tự động kèm Title, Description, Tags")
    parser.add_argument("--video", help="Đường dẫn file video cần tải lên (.mp4)")
    parser.add_argument("--metadata", help="Đường dẫn file JSON metadata (_YOUTUBE_METADATA.json) hoặc file TXT")
    parser.add_argument("--title", help="Tiêu đề video nếu không dùng file metadata")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="unlisted", help="Trạng thái xuất bản (mặc định: unlisted)")
    parser.add_argument("--category", default="1", help="ID chuyên mục (1: Film & Animation, 24: Entertainment)")
    parser.add_argument("--token", default="token.json", help="Đường dẫn file token đăng nhập YouTube (vd: tokens/yt_k1.json)")
    parser.add_argument("--secrets", default="client_secrets.json", help="Đường dẫn file client_secrets.json")
    parser.add_argument("--thumbnail", help="Đường dẫn file ảnh Thumbnail tùy chỉnh (.jpg/.png)")
    parser.add_argument("--auth-only", action="store_true", help="Chỉ đăng nhập và lưu token cho kênh mà không tải video")
    args = parser.parse_args()

    # Chế độ chỉ đăng nhập xác thực kênh
    if args.auth_only:
        print(f"[*] Bắt đầu xác thực cho kênh YouTube: {args.token}")
        try:
            get_authenticated_service(client_secrets_file=args.secrets, token_file=args.token)
            print(f"[✓] Đã xác thực thành công cho kênh: {args.token}!")
        except Exception as e:
            print(f"[X] Lỗi xác thực kênh: {e}")
            sys.exit(1)
        return

    if not args.video:
        print("[!] Vui lòng cung cấp đường dẫn video bằng tham số --video.")
        sys.exit(1)

    meta = {}
    if args.metadata and os.path.isfile(args.metadata):
        if args.metadata.endswith(".json"):
            with open(args.metadata, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            with open(args.metadata, "r", encoding="utf-8") as f:
                raw_text = f.read()
            # Bóc tách đơn giản từ file TXT
            m_title = re.search(r'=== TIÊU ĐỀ YOUTUBE.*?===\s*\n(.*?)\n\n', raw_text, re.DOTALL)
            m_desc = re.search(r'=== MÔ TẢ YOUTUBE.*?===\s*\n(.*?)\n\n===', raw_text, re.DOTALL)
            m_tags = re.search(r'=== THẺ TAGS.*?===\s*\n(.*?)\n\n', raw_text, re.DOTALL)
            meta = {
                "title": m_title.group(1).strip() if m_title else os.path.basename(args.video),
                "description": m_desc.group(1).strip() if m_desc else "",
                "tags": [t.strip() for t in m_tags.group(1).split(",") if t.strip()] if m_tags else []
            }
    elif args.title:
        meta = {"title": args.title, "description": "", "tags": []}

    try:
        thumb_to_use = args.thumbnail or meta.get("thumbnail_path")
        vid = upload_video_to_youtube(
            video_path=args.video,
            metadata=meta,
            client_secrets_file=args.secrets,
            token_file=args.token,
            privacy_status=args.privacy,
            category_id=args.category,
            thumbnail_path=thumb_to_use
        )
        print(f"\n[V] Đã hoàn tất upload video ID: {vid}")
    except Exception as e:
        print(f"\n[X] Thất bại khi upload: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
