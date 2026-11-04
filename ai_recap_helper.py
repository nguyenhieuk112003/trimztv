# -*- coding: utf-8 -*-
"""
================================================================================
AI RECAP HELPER - REVIEW ANIME XUYÊN SUỐT TOÀN BỘ VIDEO (FULL-LENGTH NARRATION)
================================================================================
- Tính toán độ dài video và sinh kịch bản phủ kín 100% thời lượng từ đầu đến cuối
- Chia nhỏ câu chuyện thành các Hồi (Acts) liền mạch, đào sâu tình tiết và cao trào
- Tạo giọng đọc AI tự nhiên (Microsoft Neural TTS qua edge-tts) với cơ chế retry bền bỉ
- Chèn khoảng đệm tự nhiên (musical pause) giữa các hồi để nhạc nền anime tỏa sáng
- Trộn âm thanh chuyên nghiệp (Audio Ducking: BGM 15% + Voice 125%)
- Tự động tạo Timestamp Chapters và bộ SEO YouTube hoàn chỉnh
================================================================================
"""

import os
import sys
import re
import json
import time
import asyncio
import subprocess
import urllib.request
import urllib.error
import urllib.parse

def load_dotenv():
    base = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(base, ".env")
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

# Đảm bảo console UTF-8 trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def upload_gemini_file(api_key: str, file_path: str, mime_type: str = "audio/mp3", display_name: str = None) -> dict:
    """
    Tải file âm thanh/video lên Google Gemini File API qua Resumable Upload protocol.
    Trả về thông tin file gồm: name ('files/...'), uri ('https://...'), state ('ACTIVE').
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Không tìm thấy file để upload lên Gemini: {file_path}")

    file_size = os.path.getsize(file_path)
    display_name = display_name or os.path.basename(file_path)

    # Bước 1: Khởi tạo phiên Resumable Upload
    init_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
    init_headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": mime_type,
        "Content-Type": "application/json"
    }
    init_body = json.dumps({"file": {"display_name": display_name}}).encode("utf-8")
    req = urllib.request.Request(init_url, data=init_body, headers=init_headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            upload_url = resp.headers.get("x-goog-upload-url") or resp.headers.get("X-Goog-Upload-URL")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Lỗi khởi tạo Gemini File API ({e.code}): {err_body}")

    if not upload_url:
        raise RuntimeError("Không nhận được upload_url từ Gemini File API.")

    # Bước 2: Tải dữ liệu nhị phân lên upload_url
    upload_headers = {
        "Content-Length": str(file_size),
        "X-Goog-Upload-Offset": "0",
        "X-Goog-Upload-Command": "upload, finalize"
    }
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    req_upload = urllib.request.Request(upload_url, data=file_bytes, headers=upload_headers, method="POST")
    try:
        with urllib.request.urlopen(req_upload, timeout=180) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data.get("file", {})
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Lỗi tải file lên Gemini ({e.code}): {err_body}")


def delete_gemini_file(api_key: str, file_name: str):
    """Xóa file tạm trên Gemini File API sau khi phân tích xong để giải phóng dung lượng."""
    if not file_name:
        return
    try:
        clean_name = file_name.lstrip("/")
        url = f"https://generativelanguage.googleapis.com/v1beta/{clean_name}?key={api_key}"
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, timeout=15):
            pass
    except Exception:
        pass


def extract_audio_for_analysis(ffmpeg_bin: str, video_path: str, out_audio_path: str) -> bool:
    """
    Bóc tách âm thanh từ video sang MP3 mono 24kHz 48kbps để AI phân tích.
    Dung lượng siêu nhẹ (~10MB cho 30-40 phút), chuyển đổi trong 1-2 giây.
    """
    try:
        cmd = [
            ffmpeg_bin, "-y",
            "-i", video_path,
            "-vn",
            "-ac", "1",
            "-ar", "24000",
            "-c:a", "libmp3lame",
            "-b:a", "48k",
            out_audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        return res.returncode == 0 and os.path.isfile(out_audio_path) and os.path.getsize(out_audio_path) > 1024
    except Exception as e:
        print(f"      [!] Lỗi khi bóc tách âm thanh phân tích: {e}")
        return False


def call_gemini_api(api_key: str, prompt: str, model: str = "gemini-flash-latest",
                    file_uri: str = None, file_mime_type: str = "audio/mp3",
                    timeout: int = 120, max_retries: int = 4) -> str:
    """Gọi trực tiếp Google Gemini REST API kèm cơ chế tự động thử lại (Retry and Backoff) và đổi model dự phòng."""
    if not api_key:
        raise ValueError("Chưa cấu hình GEMINI_API_KEY.")

    raw_candidates = [model, "gemini-3.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]
    candidate_models = []
    for m in raw_candidates:
        if m and m not in candidate_models:
            candidate_models.append(m)

    parts = []
    if file_uri:
        parts.append({
            "file_data": {
                "mime_type": file_mime_type,
                "file_uri": file_uri
            }
        })
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    last_error = None
    for cur_model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{cur_model}:generateContent?key={api_key}"
        for attempt in range(1, max_retries + 1):
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        c_parts = candidates[0]["content"].get("parts", [])
                        if c_parts:
                            return c_parts[0].get("text", "")
                    return ""
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {e.code}: {err_msg}"
                if e.code == 404:
                    print(f"      [!] Model '{cur_model}' không khả dụng (404), chuyển sang model tiếp theo...")
                    break
                if e.code in (429, 500, 502, 503, 504):
                    if attempt < max_retries:
                        wait_sec = 2 ** attempt
                        print(f"      [!] Gemini '{cur_model}' bận ({e.code}), thử lại sau {wait_sec}s (lần {attempt}/{max_retries})...")
                        time.sleep(wait_sec)
                        continue
                    else:
                        print(f"      [!] Model '{cur_model}' quá tải sau {max_retries} lần, chuyển sang model dự phòng...")
                        break
                raise RuntimeError(f"Lỗi Gemini API ({e.code}): {err_msg}")
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    wait_sec = 2 ** attempt
                    print(f"      [!] Lỗi kết nối Gemini '{cur_model}' ({e}), thử lại sau {wait_sec}s...")
                    time.sleep(wait_sec)
                    continue
                else:
                    print(f"      [!] Model '{cur_model}' lỗi sau {max_retries} lần, chuyển model dự phòng...")
                    break

    raise RuntimeError(f"Không thể kết nối Gemini API sau khi thử các model: {last_error}")


def clean_gemini_json(raw_text: str) -> str:
    """Loại bỏ markdown code blocks để trích xuất JSON sạch."""
    clean = raw_text.strip()
    clean = re.sub(r'^```json\s*', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^```\s*$', '', clean, flags=re.MULTILINE).strip()
    return clean


def get_audio_duration(ffmpeg_bin: str, file_path: str) -> float:
    """Đo thời lượng file audio bằng FFmpeg."""
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


# -----------------------------------------------------------------------------
# BƯỚC 1: SINH KỊCH BẢN REVIEW XUYÊN SUỐT TOÀN BỘ VIDEO (FULL LENGTH)
# -----------------------------------------------------------------------------
def generate_full_storyline(api_key: str, show_title: str, show_desc: str,
                            start_ep: int, end_ep: int, duration_mins: float,
                            language: str = "vi", model: str = "gemini-flash-latest",
                            source_audio_path: str = None) -> dict:
    """
    Sinh kịch bản tóm tắt anime dài, chia nhiều Hồi (Acts) tương ứng với thời lượng video.
    Nếu có file âm thanh gốc (source_audio_path), Gemini sẽ nghe trực tiếp để viết kịch bản
    khớp 100% với lời thoại và tình tiết thật của phim, không bị bịa kịch bản.
    Tốc độ nói: ~145 từ/phút (VI) hoặc ~155 từ/phút (EN).
    """
    words_per_min = 145 if language == "vi" else 155
    total_target_words = max(350, int(duration_mins * words_per_min))

    # Tính số hồi (mỗi hồi ~400-500 từ tương ứng ~3 phút nói)
    if duration_mins <= 3.5:
        num_acts = 1
    else:
        num_acts = max(2, int(round(duration_mins / 3.0)))

    words_per_act = int(total_target_words / num_acts)
    print(f"      📝 Mục tiêu kịch bản xuyên suốt: {total_target_words} từ chia thành {num_acts} Hồi (mỗi hồi ~{words_per_act} từ)...")

    # Tải file âm thanh lên Gemini File API nếu có
    file_info = None
    file_uri = None
    file_name = None

    if source_audio_path and os.path.isfile(source_audio_path) and os.path.getsize(source_audio_path) > 1024:
        sz_mb = os.path.getsize(source_audio_path) / (1024 * 1024)
        print(f"      🎧 Đang tải âm thanh gốc ({sz_mb:.1f} MB) lên Gemini File API để phân tích lời thoại thực tế...")
        clean_title_sub = re.sub(r'[^\w\-_.]', '_', show_title)
        try:
            file_info = upload_gemini_file(api_key, source_audio_path, mime_type="audio/mp3", display_name=f"Audio_{clean_title_sub}")
            file_uri = file_info.get("uri")
            file_name = file_info.get("name")
            print(f"      [✓] Gemini đã nạp âm thanh thành công! Đang nghe và phân tích cốt truyện thực tế...")
        except Exception as e_up:
            print(f"      [!] Không thể upload âm thanh lên Gemini File API ({e_up}). Sẽ dùng tóm tắt văn bản thay thế.")

    try:
        # Trường hợp video ngắn (<= 3 hồi): Sinh toàn bộ trong 1 prompt
        if num_acts <= 3:
            if language == "vi":
                audio_notice = (
                    "BẠN ĐANG ĐƯỢC CUNG CẤP VÀ LẮNG NGHE TOÀN BỘ FILE ÂM THANH THỰC TẾ CỦA BỘ ANIME NÀY.\n"
                    "QUY TẮC BẮT BUỘC:\n"
                    "1. LẮNG NGHE KỸ FILE ÂM THANH: Toàn bộ lời thoại nhân vật, sự kiện, cao trào và tình huống đều nằm trong file âm thanh này.\n"
                    "2. BÁM SÁT 100% CỐT TRUYỆN THỰC TẾ: Tuyệt đối không tự bịa đặt câu chuyện khác. Kịch bản review phải kể lại đúng những gì các nhân vật đang nói và trải qua trong phim.\n"
                ) if file_uri else ""

                prompt = f"""Bạn là một chuyên gia biên kịch video YouTube chuyên về "Tóm Tắt Anime / Review Phim" với hàng triệu view.
{audio_notice}Thông tin bộ anime:
- Tên phim: {show_title}
- Cốt truyện tham khảo: {show_desc or 'Anime lôi cuốn về tình cảm học đường, biến cố bất ngờ.'}
- Phân đoạn: Tóm tắt từ Tập {start_ep} đến Tập {end_ep} (Video dài {duration_mins:.1f} phút).

YÊU CẦU ĐẶC BIỆT: Kịch bản phải ĐỌC XUYÊN SUỐT TOÀN BỘ VIDEO ({duration_mins:.1f} phút), tổng cộng khoảng {total_target_words} từ.
Chia thành đúng {num_acts} Hồi liên tiếp:
- Hồi 1 (Mở đầu & Biến cố khởi đầu): Hook giật gân, xuất thân nhân vật, tình huống bất ngờ.
- Hồi giữa: Diễn biến kịch tính, sự phát triển tình cảm, hiểu lầm, xung đột gay cấn theo đúng lời thoại phim.
- Hồi cuối: Đỉnh điểm cao trào, tháo gỡ nút thắt, kết thúc và lời kêu gọi Like/Subscribe.

LƯU Ý: Lời thuyết minh phải là văn bản thuần chữ để AI đọc (TTS). KHÔNG chứa ký hiệu [nhạc nền], (cười), *cảnh quay*.

TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON NHƯ SAU:
{{
  "youtube_title": "Tiêu đề YouTube giật gân chuẩn SEO",
  "youtube_description": "Mô tả video kèm tóm tắt và hashtag",
  "youtube_tags": ["tag1", "tag2", "tag3"],
  "acts": [
    {{
      "act_number": 1,
      "title": "Tên hồi 1",
      "narration": "Lời thuyết minh chi tiết cho hồi 1 (~{words_per_act} từ)..."
    }}
  ]
}}
"""
            else:
                audio_notice_en = (
                    "YOU ARE LISTENING TO THE ACTUAL AUDIO TRACK OF THIS ANIME.\n"
                    "CRITICAL RULES (NO HALLUCINATIONS):\n"
                    "1. LISTEN CAREFULLY TO THE ATTACHED AUDIO: Character dialogues, emotional reactions, and plot twists are all in this audio.\n"
                    "2. 100% FAITHFUL RECAP: Do not invent unrelated storylines. Accurately recount the actual events and conversations occurring in this anime.\n"
                ) if file_uri else ""

                prompt = f"""You are an elite YouTube Anime Recap scriptwriter creating viral, high-retention anime summaries.
{audio_notice_en}Show Details:
- Title: {show_title}
- Premise: {show_desc or 'An engaging anime full of drama, romance, and plot twists.'}
- Episode Range: Episodes {start_ep} to {end_ep} (Total video duration: {duration_mins:.1f} minutes).

SPECIAL REQUIREMENT: The narration MUST COVER THE ENTIRE VIDEO DURATION ({duration_mins:.1f} minutes), total ~{total_target_words} words.
Split into exactly {num_acts} sequential Acts:
- Act 1: Hook, character backgrounds, inciting incident.
- Middle Acts: Rising tensions, romantic developments, conflicts, plot twists.
- Final Act: Climax, resolution, and outro call-to-action (Like & Subscribe).

CRITICAL: Pure spoken voiceover text for TTS. NO stage directions like [Music], (Laughs), [Scene change].

RETURN ONLY VALID JSON:
{{
  "youtube_title": "Clickable high-CTR title",
  "youtube_description": "Description with summary and hashtags",
  "youtube_tags": ["tag1", "tag2", "tag3"],
  "acts": [
    {{
      "act_number": 1,
      "title": "Act 1 title",
      "narration": "Full narration script for Act 1 (~{words_per_act} words)..."
    }}
  ]
}}
"""
            raw_res = call_gemini_api(api_key, prompt, model, file_uri=file_uri)
            clean_json = clean_gemini_json(raw_res)
            try:
                parsed = json.loads(clean_json)
                if parsed.get("acts"):
                    return parsed
            except Exception:
                pass

        # Trường hợp video dài (> 3 hồi): Dùng quy trình 2 bước (Lập dàn ý các hồi -> Sinh chi tiết từng hồi)
        print("      📋 Video dài: Đang tạo dàn ý các Hồi với Gemini (lắng nghe tình tiết từ âm thanh thật)...")
        if language == "vi":
            audio_guide = "Hãy lắng nghe toàn bộ file âm thanh thật để nắm rõ cốt truyện, lời thoại và diễn biến của phim. Tuyệt đối không bịa đặt." if file_uri else ""
            outline_prompt = f"""Bạn là biên kịch anime recap YouTube chuyên nghiệp. {audio_guide}
Hãy lập dàn ý {num_acts} Hồi bám sát 100% tình tiết thật cho bộ anime:
Tên: {show_title}
Cốt truyện tham khảo: {show_desc}
Video dài: {duration_mins:.1f} phút (Tập {start_ep} đến {end_ep}).

YÊU CẦU:
1. Chia câu chuyện thành đúng {num_acts} Hồi tuần tự theo thời gian.
2. Với mỗi Hồi, mô tả chi tiết các sự kiện, câu thoại chính và tình tiết kịch tính thực sự xảy ra.

Trả về JSON:
{{
  "youtube_title": "Tiêu đề YouTube cuốn hút",
  "youtube_description": "Mô tả YouTube",
  "youtube_tags": ["tag1", "tag2"],
  "acts_plan": [
    {{"act_number": 1, "title": "Tên hồi 1", "key_events": "Sự kiện, câu thoại và biến cố chính diễn ra..."}}
  ]
}}
"""
        else:
            audio_guide_en = "Listen to the attached audio carefully to understand real character dialogues and actual plot twists. Do not fabricate." if file_uri else ""
            outline_prompt = f"""You are an elite YouTube Anime Recap scriptwriter. {audio_guide_en}
Create an outline of {num_acts} sequential Acts faithfully reflecting actual plot events:
Title: {show_title}
Reference Premise: {show_desc}
Video duration: {duration_mins:.1f} minutes (Episodes {start_ep} to {end_ep}).

RETURN VALID JSON:
{{
  "youtube_title": "High CTR Title",
  "youtube_description": "YouTube Description",
  "youtube_tags": ["tag1", "tag2"],
  "acts_plan": [
    {{"act_number": 1, "title": "Act 1 Title", "key_events": "Key dialogue, actions, and real events occurring..."}}
  ]
}}
"""
        raw_outline = call_gemini_api(api_key, outline_prompt, model, file_uri=file_uri)
        try:
            outline_data = json.loads(clean_gemini_json(raw_outline))
        except Exception:
            outline_data = {
                "youtube_title": f"[Tóm Tắt Anime] {show_title} (Tập {start_ep}-{end_ep})",
                "youtube_description": f"{show_title}\n#animerecap",
                "youtube_tags": ["anime recap", show_title.lower()],
                "acts_plan": [{"act_number": i, "title": f"Hồi {i}", "key_events": f"Diễn biến phần {i}"} for i in range(1, num_acts + 1)]
            }

        acts_list = []
        acts_plan = outline_data.get("acts_plan", [])
        if not acts_plan:
            acts_plan = [{"act_number": i, "title": f"Hồi {i}", "key_events": f"Diễn biến phần {i}"} for i in range(1, num_acts + 1)]

        # Sinh chi tiết từng Hồi theo chuỗi liền mạch
        prev_summary = "Bắt đầu câu chuyện"
        for item in acts_plan:
            act_num = item.get("act_number", len(acts_list) + 1)
            act_title = item.get("title", f"Hồi {act_num}")
            key_events = item.get("key_events", "")

            print(f"      ✍️ Đang viết Hồi {act_num}/{len(acts_plan)}: \"{act_title}\" (~{words_per_act} từ)...")
            act_prompt = f"""Bạn đang viết kịch bản thuyết minh video Review Anime cho YouTube:
Phim: {show_title}
Đang viết: Hồi {act_num}/{len(acts_plan)}: "{act_title}"
Nội dung chính hồi này (tình tiết thật): {key_events}
Bối cảnh trước đó: {prev_summary}
Ngôn ngữ: {'TIẾNG VIỆT' if language == 'vi' else 'ENGLISH'}

YÊU CẦU:
1. Viết đúng khoảng {words_per_act} từ, kể chuyện cực kỳ chi tiết, lôi cuốn, bám sát các sự kiện trên, đào sâu biểu cảm và lời thoại nhân vật.
2. {'Nếu là Hồi cuối, nhớ thêm lời kêu gọi người xem nhấn Like, Đăng ký kênh.' if act_num == len(acts_plan) else 'Kết thúc hồi này mở ra tình huống tò mò dẫn sang hồi sau.'}
3. Thuần chữ đọc TTS, KHÔNG chứa [nhạc], (cười), chỉ thị hình ảnh.

Chỉ xuất ra đoạn văn bản thuyết minh thuần túy của Hồi này:
"""
            act_text = call_gemini_api(api_key, act_prompt, model).strip()
            act_text = re.sub(r'^```.*?\n', '', act_text, flags=re.MULTILINE)
            act_text = re.sub(r'```$', '', act_text, flags=re.MULTILINE).strip()

            acts_list.append({
                "act_number": act_num,
                "title": act_title,
                "narration": act_text
            })
            prev_summary = f"Kết thúc hồi {act_num} với diễn biến: {act_title}"

        return {
            "youtube_title": outline_data.get("youtube_title", f"[Review Anime] {show_title}"),
            "youtube_description": outline_data.get("youtube_description", ""),
            "youtube_tags": outline_data.get("youtube_tags", []),
            "acts": acts_list
        }
    finally:
        # Xóa file audio tạm trên Gemini File API để giữ sạch storage
        if file_name:
            print("      🧹 Đang dọn dẹp file âm thanh tạm trên Gemini API...")
            delete_gemini_file(api_key, file_name)


def generate_recap_content(api_key: str, show_title: str, show_desc: str,
                           start_ep: int, end_ep: int, duration_mins: float = 10.0,
                           language: str = "vi", model: str = "gemini-flash-latest",
                           source_audio_path: str = None) -> dict:
    """Wrapper tương thích ngược cho AutoAnimeRecap.py."""
    data = generate_full_storyline(
        api_key=api_key,
        show_title=show_title,
        show_desc=show_desc,
        start_ep=start_ep,
        end_ep=end_ep,
        duration_mins=duration_mins,
        language=language,
        model=model,
        source_audio_path=source_audio_path
    )
    acts = data.get("acts", [])
    full_narration = "\n\n".join(a.get("narration", "") for a in acts if a.get("narration"))
    return {
        "youtube_title": data.get("youtube_title", f"[Review Anime] {show_title}"),
        "youtube_description": data.get("youtube_description", ""),
        "youtube_tags": data.get("youtube_tags", []),
        "narration": full_narration,
        "acts": acts
    }


# -----------------------------------------------------------------------------
# BƯỚC 2: TỔNG HỢP GIỌNG ĐỌC BỀN BỈ (EDGE-TTS + RETRY)
# -----------------------------------------------------------------------------
async def synth_single_chunk(text: str, voice: str, out_file: str) -> bool:
    import edge_tts
    try:
        com = edge_tts.Communicate(text, voice)
        await com.save(out_file)
        if os.path.isfile(out_file) and os.path.getsize(out_file) > 500:
            return True
    except Exception:
        pass

    # Thử giọng dự phòng nếu giọng chính gặp sự cố
    try:
        fallback = "vi-VN-HoaiMyNeural" if "vi-VN" in voice else "en-US-GuyNeural"
        com = edge_tts.Communicate(text, fallback)
        await com.save(out_file)
        if os.path.isfile(out_file) and os.path.getsize(out_file) > 500:
            return True
    except Exception:
        pass

    # Fallback Google Translate TTS
    try:
        tl = "vi" if "vi-VN" in voice else "en"
        enc = urllib.parse.quote(text[:180])
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={tl}&client=tw-ob&q={enc}"
        subprocess.run(["curl.exe", "-s", "-L", "-A", "Mozilla/5.0", url, "-o", out_file], check=True)
        return os.path.isfile(out_file) and os.path.getsize(out_file) > 200
    except Exception:
        return False


async def synth_text_chunked(ffmpeg_bin: str, text: str, voice: str, out_file: str, temp_prefix: str) -> bool:
    """Tách văn bản thành các câu nhỏ (<180 ký tự) để tổng hợp TTS mượt mà không lỗi."""
    clean = re.sub(r'[\'":;]', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()

    sentences = re.split(r'(?<=[.!?])\s+', clean)
    chunks = []
    curr = []
    curr_len = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if curr_len + len(s) > 180 and curr:
            chunks.append(" ".join(curr))
            curr = [s]
            curr_len = len(s)
        else:
            curr.append(s)
            curr_len += len(s)
    if curr:
        chunks.append(" ".join(curr))

    sub_files = []
    for idx, c in enumerate(chunks):
        sub_path = f"{temp_prefix}_c{idx:03d}.mp3"
        ok = await synth_single_chunk(c, voice, sub_path)
        if ok:
            sub_files.append(sub_path)
        await asyncio.sleep(0.04)

    if not sub_files:
        return False

    concat_list = f"{temp_prefix}_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in sub_files:
            clean_sf = os.path.abspath(sf).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{clean_sf}'\n")

    subprocess.run([
        ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        out_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    if os.path.isfile(concat_list):
        try:
            os.remove(concat_list)
        except Exception:
            pass
    for sf in sub_files:
        if os.path.isfile(sf):
            try:
                os.remove(sf)
            except Exception:
                pass

    return os.path.isfile(out_file) and os.path.getsize(out_file) > 1024


# -----------------------------------------------------------------------------
# BƯỚC 3: GHÉP CÁC HỒI & TẠO KHOẢNG NGHỈ ÂM NHẠC TỰ NHIÊN (MUSICAL BREATHERS)
# -----------------------------------------------------------------------------
def build_continuous_narration_audio(ffmpeg_bin: str, acts: list, voice: str,
                                     target_total_sec: float, out_full_mp3: str,
                                     temp_dir: str) -> tuple:
    """
    1. Tổng hợp âm thanh từng Hồi
    2. Đo độ dài và tính khoảng nghỉ nhạc đệm giữa các Hồi
    3. Ghép nối thành 1 dải âm thanh hoàn chỉnh phủ kín toàn bộ thời lượng video
    """
    act_audio_files = []
    chapters_timeline = []
    current_time_sec = 0.0

    print(f"      🎙️ Đang tổng hợp giọng đọc AI ({voice}) cho {len(acts)} Hồi...")

    for idx, act in enumerate(acts, start=1):
        act_text = act.get("narration", "").strip()
        act_title = act.get("title", f"Hồi {idx}")
        if not act_text:
            continue

        act_mp3 = os.path.join(temp_dir, f".temp_act_{idx:02d}.mp3")
        temp_p = os.path.join(temp_dir, f".t_act_{idx:02d}")

        print(f"         ▶ Hồi {idx:02d}/{len(acts):02d} ({len(act_text.split())} từ)...", end="", flush=True)
        ok = asyncio.run(synth_text_chunked(ffmpeg_bin, act_text, voice, act_mp3, temp_p))
        if ok:
            dur = get_audio_duration(ffmpeg_bin, act_mp3)
            print(f" xong ({dur/60:.1f} phút)")
            act_audio_files.append((act_mp3, dur, act_title))
        else:
            print(" [!] Lỗi tổng hợp hồi này.")

    if not act_audio_files:
        return False, []

    # Tính khoảng nghỉ âm nhạc giữa các Hồi để vừa khớp thời lượng video
    total_voice_sec = sum(d for _, d, _ in act_audio_files)
    remaining_sec = max(0.0, target_total_sec - total_voice_sec)
    num_gaps = len(act_audio_files)
    gap_sec = min(8.0, remaining_sec / max(1, num_gaps)) if num_gaps > 0 else 0.0

    print(f"      ⏱️ Tổng thời lượng giọng nói: {total_voice_sec/60:.1f} phút / Video: {target_total_sec/60:.1f} phút")
    if gap_sec > 0.5:
        print(f"      🎵 Chèn khoảng đệm âm nhạc tự nhiên: {gap_sec:.1f} giây giữa mỗi Hồi...")

    # Tạo file silence nếu cần
    gap_mp3 = None
    if gap_sec >= 1.0:
        gap_mp3 = os.path.join(temp_dir, ".temp_silence_gap.mp3")
        subprocess.run([
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", f"{gap_sec:.2f}",
            "-c:a", "libmp3lame", "-b:a", "192k",
            gap_mp3
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Lập danh sách nối âm thanh kèm Chapters
    concat_list = os.path.join(temp_dir, ".temp_full_concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for idx, (fpath, dur, atitle) in enumerate(act_audio_files):
            # Ghi nhận mốc thời gian YouTube Chapters
            mins_part = int(current_time_sec // 60)
            secs_part = int(current_time_sec % 60)
            chapters_timeline.append(f"{mins_part:02d}:{secs_part:02d} - {atitle}")

            clean_path = os.path.abspath(fpath).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{clean_path}'\n")
            current_time_sec += dur

            # Chèn khoảng nghỉ giữa các hồi (trừ hồi cuối)
            if gap_mp3 and os.path.isfile(gap_mp3) and idx < len(act_audio_files) - 1:
                clean_gap = os.path.abspath(gap_mp3).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{clean_gap}'\n")
                current_time_sec += gap_sec

    # Nối tất cả các Hồi thành 1 file MP3 xuyên suốt
    subprocess.run([
        ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        out_full_mp3
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Dọn dẹp file tạm
    if os.path.isfile(concat_list):
        try:
            os.remove(concat_list)
        except Exception:
            pass
    if gap_mp3 and os.path.isfile(gap_mp3):
        try:
            os.remove(gap_mp3)
        except Exception:
            pass
    for fpath, _, _ in act_audio_files:
        if os.path.isfile(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

    return True, chapters_timeline


# -----------------------------------------------------------------------------
# BƯỚC 4: AUDIO DUCKING VÀ XUẤT VIDEO REVIEW HOÀN CHỈNH
# -----------------------------------------------------------------------------
def apply_audio_ducking(ffmpeg_bin: str, video_in: str, audio_voice: str, video_out: str,
                        bgm_vol: float = 0.15, voice_vol: float = 1.25) -> bool:
    """
    Audio Ducking:
    - [0:a] Nhạc nền gốc giảm còn bgm_vol (15%)
    - [1:a] Giọng thuyết minh AI tăng voice_vol (125%)
    - amix: Trộn 2 luồng, thời lượng giữ theo video gốc
    - -c:v copy: Siêu tốc, không làm suy giảm chất lượng hình ảnh
    """
    filter_complex = f"[0:a]volume={bgm_vol:.2f}[bgm];[1:a]volume={voice_vol:.2f}[voice];[bgm][voice]amix=inputs=2:duration=first[aout]"
    cmd = [
        ffmpeg_bin, "-y",
        "-i", video_in,
        "-i", audio_voice,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        video_out
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return res.returncode == 0 and os.path.isfile(video_out) and os.path.getsize(video_out) > 10240


# -----------------------------------------------------------------------------
# ĐIỀU PHỐI CHÍNH: XUẤT BẢN VIDEO REVIEW FULL 100% THỜI LƯỢNG
# -----------------------------------------------------------------------------
def process_channel_review(ffmpeg_bin: str, raw_merged_video: str, show_title: str, show_desc: str,
                           start_ep: int, end_ep: int, duration_mins: float,
                           lang: str, out_folder: str, ai_cfg: dict, yt_cfg: dict = None) -> str:
    """
    Xử lý tạo video review đọc xuyên suốt từ đầu đến cuối:
    1. Gemini tạo dàn ý và viết kịch bản đủ số từ phủ kín thời lượng
    2. Edge-TTS tổng hợp giọng đọc từng hồi bền bỉ
    3. Ghép nối tạo khoảng đệm âm nhạc tự nhiên
    4. Audio Ducking xuất video thành phẩm
    5. Xuất file SEO YouTube kèm Chapters, Tuyên bố bản quyền, và file JSON payload
    6. Tự động đăng lên YouTube nếu bật tính năng youtube_upload
    """
    os.makedirs(out_folder, exist_ok=True)
    lang_upper = lang.upper()
    prefix = f"{show_title}_Tap_{start_ep:03d}-{end_ep:03d}" if start_ep != end_ep else f"{show_title}_Tap_{start_ep:03d}"
    clean_prefix = re.sub(r'[\\/*?:"<>|]', "_", prefix)

    out_video = os.path.join(out_folder, f"{clean_prefix}_RECAP_{lang_upper}.mp4")
    out_meta = os.path.join(out_folder, f"{clean_prefix}_SEO_{lang_upper}.txt")
    out_json = os.path.join(out_folder, f"{clean_prefix}_YOUTUBE_PAYLOAD_{lang_upper}.json")

    # Nếu đã tạo rồi thì bỏ qua
    if os.path.isfile(out_video) and os.path.getsize(out_video) > 102400:
        print(f"      [✓] Video Review {lang_upper} đã tồn tại: {os.path.basename(out_video)}")
        return out_video

    api_key = ai_cfg.get("api_key", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(f"      [!] Bỏ qua tạo video Review {lang_upper}: Chưa cấu hình GEMINI_API_KEY trong config.json.")
        return ""

    model = ai_cfg.get("model", "gemini-flash-latest")
    print(f"\n      🌟 [REVIEW TOÀN BỘ PHIM - {lang_upper}] Phim: \"{show_title}\" ({duration_mins:.1f} phút)")

    # Bóc tách âm thanh thực tế từ video để AI phân tích nếu có file video
    temp_source_audio = os.path.join(out_folder, f".temp_audio_analysis_{clean_prefix}.mp3")
    source_audio_path = None
    if os.path.isfile(raw_merged_video) and os.path.getsize(raw_merged_video) > 10240:
        print(f"      🎵 Đang bóc tách âm thanh từ video để AI lắng nghe lời thoại thật...")
        ok_ext = extract_audio_for_analysis(ffmpeg_bin, raw_merged_video, temp_source_audio)
        if ok_ext:
            source_audio_path = temp_source_audio

    # 1. Sinh kịch bản nhiều Hồi bằng Gemini
    try:
        content = generate_full_storyline(
            api_key=api_key,
            show_title=show_title,
            show_desc=show_desc,
            start_ep=start_ep,
            end_ep=end_ep,
            duration_mins=duration_mins,
            language=lang,
            model=model,
            source_audio_path=source_audio_path
        )
    except Exception as e:
        print(f"      [X] Lỗi khi sinh kịch bản Gemini: {e}")
        return ""
    finally:
        if temp_source_audio and os.path.isfile(temp_source_audio):
            try:
                os.remove(temp_source_audio)
            except Exception:
                pass

    acts = content.get("acts", [])
    if not acts:
        print(f"      [!] Không nhận được các Hồi kịch bản hợp lệ.")
        return ""

    # Chọn giọng đọc
    if lang == "vi":
        voice = ai_cfg.get("voice_vi", "vi-VN-NamMinhNeural")
    else:
        voice = ai_cfg.get("voice_en", "en-US-ChristopherNeural")

    # 2. Xây dựng dải âm thanh xuyên suốt phủ kín video
    full_audio_path = os.path.join(out_folder, f".temp_full_narration_{lang}.mp3")
    target_sec = duration_mins * 60.0

    ok_audio, chapters = build_continuous_narration_audio(ffmpeg_bin, acts, voice, target_sec, full_audio_path, out_folder)
    if not ok_audio or not os.path.isfile(full_audio_path):
        print(f"      [!] Lỗi khi tổng hợp dải âm thanh toàn diện.")
        return ""

    # 3. Audio Ducking ghép vào video gốc
    bgm_vol = ai_cfg.get("ducking_bgm_volume", 0.15)
    voice_vol = ai_cfg.get("ducking_voice_volume", 1.25)
    print(f"      🎬 Đang thực hiện Audio Ducking vào video ({duration_mins:.1f} phút)...")
    duck_ok = apply_audio_ducking(ffmpeg_bin, raw_merged_video, full_audio_path, out_video, bgm_vol, voice_vol)

    # Xóa file audio tạm
    if os.path.isfile(full_audio_path):
        try:
            os.remove(full_audio_path)
        except Exception:
            pass

    if duck_ok:
        sz_mb = os.path.getsize(out_video) / (1024 * 1024)
        print(f"      🎉 [THÀNH CÔNG] ĐÃ XUẤT VIDEO REVIEW {lang_upper} XUYÊN SUỐT: {os.path.basename(out_video)} ({sz_mb:.1f} MB)")

        # 4. Biên soạn Tiêu đề, Mô tả hoàn chỉnh và Thẻ Tags
        yt_title = content.get("youtube_title", f"[Review Anime] {show_title}")
        raw_desc = content.get("youtube_description", "").strip()
        tags = content.get("youtube_tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        chapters_text = "\n".join(chapters) if chapters else "00:00 - Tóm Tắt Trọn Bộ"
        hashtags = "#tomtatanime #reviewphim #animehay #animerecap" if lang == "vi" else "#animerecap #animereview #anime #fullrecap"
        disclaimer = (
            "⚠️ Bản quyền / Copyright Disclaimer:\n"
            "Under Section 107 of the Copyright Act 1976, allowance is made for 'fair use' for purposes such as criticism, comment, news reporting, teaching, scholarship, and research. "
            "All video and audio materials belong to their respective copyright holders."
        )

        full_description = (
            f"{yt_title}\n\n"
            f"📌 Cốt truyện tóm tắt:\n{raw_desc}\n\n"
            f"⏱️ Mốc thời gian (Chapters):\n{chapters_text}\n\n"
            f"🔔 Đừng quên bấm LIKE và ĐĂNG KÝ KÊNH để ủng hộ mình ra thêm các phần tiếp theo nhé!\n\n"
            f"{hashtags}\n\n"
            f"{disclaimer}"
        ) if lang == "vi" else (
            f"{yt_title}\n\n"
            f"📌 Story Overview:\n{raw_desc}\n\n"
            f"⏱️ Timestamps (Chapters):\n{chapters_text}\n\n"
            f"🔔 Don't forget to LIKE & SUBSCRIBE for more full-length anime recaps!\n\n"
            f"{hashtags}\n\n"
            f"{disclaimer}"
        )

        # 5. Ghi file SEO YouTube TXT
        with open(out_meta, "w", encoding="utf-8") as f:
            f.write(f"=== TIÊU ĐỀ YOUTUBE ({lang_upper}) ===\n")
            f.write(yt_title + "\n\n")
            f.write(f"=== MÔ TẢ YOUTUBE HOÀN CHỈNH ({lang_upper}) ===\n")
            f.write(full_description + "\n\n")
            f.write("=== THẺ TAGS YOUTUBE ===\n")
            f.write(", ".join(tags) + "\n\n")
            f.write("=== TOÀN BỘ KỊCH BẢN THUYẾT MINH TỪ ĐẦU ĐẾN CUỐI ===\n")
            for a in acts:
                f.write(f"\n--- {a.get('title', 'Hồi')} ---\n")
                f.write(a.get("narration", "") + "\n")

        # 6. Ghi file JSON YouTube Payload chuẩn cho Uploader
        privacy_status = yt_cfg.get("privacy_status", "unlisted") if yt_cfg else "unlisted"
        category_id = yt_cfg.get("category_id", "1") if yt_cfg else "1"
        payload_data = {
            "video_path": os.path.abspath(out_video),
            "title": yt_title,
            "description": full_description,
            "tags": tags,
            "privacy_status": privacy_status,
            "category_id": category_id
        }
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload_data, f, indent=2, ensure_ascii=False)

        print(f"      [✓] Đã tạo bộ SEO YouTube & Chapters: {os.path.basename(out_meta)}")
        print(f"      [✓] Đã tạo file cấu hình đăng: {os.path.basename(out_json)}")

        # 7. Tự động phân phối đa nền tảng (YouTube Channel & Facebook Fanpage tương ứng)
        chan_key = "kenh_3_vi" if lang == "vi" else "kenh_2_en"
        full_config = ai_cfg.get("full_config")
        if not full_config:
            full_config = {"channels_distribution": {}, "youtube_upload": yt_cfg or {}}

        try:
            from publisher import publish_to_channel
            publish_to_channel(chan_key, out_video, payload_data, full_config, payload_json_path=out_json)
        except Exception as e_pub:
            print(f"      [!] Lỗi khi tự động phân phối ({chan_key}): {e_pub}")

        return out_video

    return ""
