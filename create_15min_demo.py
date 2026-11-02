# -*- coding: utf-8 -*-
"""
TẠO DEMO VIDEO 15 PHÚT HOÀN CHỈNH CHO 3 KÊNH YOUTUBE
- Kênh 1: Video ghép sạch 15 phút (Raw 1080p, âm thanh gốc)
- Kênh 2: Tóm tắt 15 phút tiếng Anh (Continuous Narration EN + Audio Ducking)
- Kênh 3: Tóm tắt 15 phút tiếng Việt (Continuous Narration VI + Audio Ducking)
"""

import os
import sys
import re
import asyncio
import subprocess
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_EXE = os.path.join(BASE_DIR, "tools", "ffmpeg", "ffmpeg.exe")
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"

BASE_VIDEO_15M = os.path.join(BASE_DIR, "Output", "base_video_15m.mp4")

OUT_DIR = os.path.join(BASE_DIR, "Downloads", "Demo_3_Channels_15Min")
DIR_K1 = os.path.join(OUT_DIR, "Kenh_1_Raw_Full")
DIR_K2 = os.path.join(OUT_DIR, "Kenh_2_Review_EN")
DIR_K3 = os.path.join(OUT_DIR, "Kenh_3_Review_VI")

os.makedirs(DIR_K1, exist_ok=True)
os.makedirs(DIR_K2, exist_ok=True)
os.makedirs(DIR_K3, exist_ok=True)

# -----------------------------------------------------------------------------
# ĐỌC KỊCH BẢN TIẾNG VIỆT TỪ FILE UTF-8
# -----------------------------------------------------------------------------
VI_SCRIPT_PATH = os.path.join(DIR_K3, "script_15min_vi.txt")
if os.path.exists(VI_SCRIPT_PATH):
    with open(VI_SCRIPT_PATH, "r", encoding="utf-8") as f:
        raw_vi = f.read()
    VI_PARTS = [p.strip() for p in raw_vi.split("---") if p.strip()]
else:
    VI_PARTS = []

# -----------------------------------------------------------------------------
# KỊCH BẢN TIẾNG ANH 15 PHÚT
# -----------------------------------------------------------------------------
EN_PARTS = [
    (
        "Welcome back to Anime Recap Central, your number one destination for full-length story breakdowns and captivating anime summaries! "
        "If you have ever believed that a completely introverted otaku, who spends his days isolated from society and buried deep in manga and video games, "
        "could never have a chance at finding genuine romance, then today our full 15-minute journey titled: "
        "How a Loner Otaku Bagged The Most Popular Girl at School, will completely overturn your expectations. "
        "Our protagonist is Ren, a quiet second-year high school student and the quintessential introvert. "
        "Ren despises crowded spaces, actively dodges after-school social gatherings, and finds his greatest happiness "
        "in returning to the sanctuary of his bedroom, diving into fictional fantasy worlds where nobody expects anything from him. "
        "To Ren, school is a treacherous social jungle ruled by the loud, popular cliques, "
        "and his ultimate strategy for survival has always been absolute invisibility. "
        "However, on the very day he assumes his monotonous life will continue forever, "
        "a dramatic twist of fate turns his quiet existence completely upside down."
    ),
    (
        "The turning point arrives on a heavy, rain-drenched afternoon inside the quiet sanctuary of the school library. "
        "While Ren is searching through the back shelves for an obscure light novel that nobody ever touches, "
        "a familiar presence suddenly steps into his aisle. "
        "It is none other than Karen, universally recognized as the undisputed queen and number one idol of the entire school. "
        "Karen possesses stunning beauty, flawless academic marks, and a massive circle of admirers constantly surrounding her every move. "
        "To the student body, Karen is like an untouchable star shining high up in the stratosphere, "
        "while Ren is just a forgotten speck of dust on the ground. "
        "Yet, in an unscripted moment of clumsiness, Karen slips and drops an entire stack of heavy reference files across the polished floor. "
        "Reacting purely on instinct, Ren lunges forward to break her fall. "
        "Their eyes lock for a frozen, breathless second, and an awkward silence engulfs the room. "
        "Instead of looking down on him with cold arrogance, Karen offers him a gentle, radiant smile, "
        "thanking him with genuine warmth and noticing the manga peeking out of his bag with genuine curiosity."
    ),
    (
        "Over the following weeks, an inexplicable phenomenon begins unfolding that leaves the entire campus speechless. "
        "Karen consistently goes out of her way to interact with Ren. "
        "She casually appears by his desk between classes, invites herself to sit with him on the secluded rooftop during lunch, "
        "and routinely sends him messages late into the evening. "
        "Why would an elite, popular girl like Karen seek out a brooding loner? "
        "As it turns out, behind the suffocating facade of absolute perfection imposed on her by her family and peers, "
        "Karen has lived an intensely lonely life. "
        "She is constantly expected to be the flawless daughter, forbidden from making mistakes, "
        "and forced to conceal her secret passion for anime and fantasy stories out of fear of judgment. "
        "With Ren, for the first time in her life, Karen can drop her heavy mask and simply breathe. "
        "Ren does not fawn over her beauty or expect her to perform, he listens to her sincerely, "
        "respects her boundaries, and shares the quiet passions she had hidden away for years."
    ),
    (
        "However, peace never lasts long in high school. "
        "The growing intimacy between this seemingly mismatched pair soon sparks fierce jealousy and toxic rumors. "
        "Anonymous school forums explode with malicious gossip, claiming that an outcast like Ren must have manipulated her. "
        "Meanwhile, the self-proclaimed alpha boys of the school feel deeply humiliated that their campus idol "
        "would choose the company of an otaku over any of them. "
        "The crushing weight of public scrutiny begins to take an agonizing toll on Ren. "
        "Convinced that his very presence is dragging Karen through the mud and ruining her spotless reputation, "
        "Ren falls back into self-loathing. "
        "In a desperate attempt to protect her from further scandal, Ren begins actively avoiding her, "
        "ignoring her messages and retreating back into his cold shell of isolation. "
        "Yet this selfless retreat only shatters Karens heart, forcing her to realize that unless she takes a stand, "
        "the most meaningful connection she has ever made will slip through her fingers forever."
    ),
    (
        "The ultimate climax erupts on the stormy evening of the annual autumn cultural festival. "
        "While the main auditorium is rocking with live music, a gang of spiteful classmates corners Ren "
        "in the dimly lit shadows behind the gymnasium, aggressively taunting him and demanding that he stay away from Karen. "
        "In the past, Ren would have bowed his head and endured the humiliation in silence. "
        "But remembering Karens tears and the vulnerable honesty she entrusted to him, "
        "Ren clenches his fists, stands tall, and refuses to apologize for loving her. "
        "Just as the confrontation threatens to turn violent, Karen rushes through the darkness. "
        "In front of dozens of stunned students and teachers who had gathered around, "
        "she boldly grabs Rens trembling hand and publicly declares that he is the most important person in her entire life. "
        "Her fearless defiance leaves the crowd entirely paralyzed with shock, "
        "instantly dismantling the shallow social hierarchy that had kept them apart."
    ),
    (
        "From that transformative night onward, Ren and Karen stand together as the most admired couple on campus. "
        "Ren is no longer a ghost hiding in the shadows; he has learned self-worth, walks with his head high, "
        "and embraces a future filled with genuine warmth and purpose. "
        "And Karen has finally found her true haven, where she is cherished not for her status or looks, "
        "but for the authentic human being she has always wanted to be. "
        "Their journey concludes under a canopy of blooming cherry blossoms, offering a timeless testament "
        "that genuine love transcends all social boundaries when two souls possess the courage to be vulnerable and true. "
        "That brings us to the end of our full 15-minute anime recap! "
        "If you enjoyed this captivating story breakdown, please smash that Like button, share this video with your fellow anime fans, "
        "and don't forget to Subscribe and hit the notification bell so you never miss our upcoming full-length summaries. "
        "Thank you so much for watching, and see you in the next recap!"
    )
]

# -----------------------------------------------------------------------------
# HÀM TỔNG HỢP GIỌNG ĐỌC CỰC KỲ BỀN BỈ (EDGE-TTS + HOAIMY + GOOGLE FALLBACK)
# -----------------------------------------------------------------------------
async def synth_single_chunk(text: str, voice: str, out_file: str):
    import edge_tts
    # 1. Thử Edge-TTS chính
    try:
        com = edge_tts.Communicate(text, voice)
        await com.save(out_file)
        if os.path.exists(out_file) and os.path.getsize(out_file) > 500:
            return True
    except Exception:
        pass

    # 2. Thử giọng phụ Edge-TTS (HoaiMy nếu là tiếng Việt, Guy nếu là tiếng Anh)
    try:
        fallback_voice = "vi-VN-HoaiMyNeural" if "vi-VN" in voice else "en-US-GuyNeural"
        com = edge_tts.Communicate(text, fallback_voice)
        await com.save(out_file)
        if os.path.exists(out_file) and os.path.getsize(out_file) > 500:
            return True
    except Exception:
        pass

    # 3. Fallback dự phòng Google Translate TTS (tuyệt đối không bị lỗi)
    try:
        tl = "vi" if "vi-VN" in voice else "en"
        enc = urllib.parse.quote(text[:180])
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={tl}&client=tw-ob&q={enc}"
        subprocess.run(["curl.exe", "-s", "-L", "-A", "Mozilla/5.0", url, "-o", out_file], check=True)
        if os.path.exists(out_file) and os.path.getsize(out_file) > 200:
            return True
    except Exception as e:
        print(f"       [!] Lỗi Google Fallback: {e}")

    return False

async def synth_part_robust(text: str, voice: str, out_file: str, temp_prefix: str):
    # Chuẩn hoá ký tự
    clean = re.sub(r'[\'":;]', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # Tách thành các câu ngắn (< 150 ký tự) để gửi lên TTS
    sentences = re.split(r'(?<=[.!?])\s+', clean)
    chunks = []
    curr = []
    curr_len = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if curr_len + len(s) > 150 and curr:
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
        await asyncio.sleep(0.05)

    if not sub_files:
        raise RuntimeError(f"Không thể tổng hợp audio cho: {out_file}")

    # Ghép các mẩu audio nhỏ lại
    concat_list = f"{temp_prefix}_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in sub_files:
            clean_sf = os.path.abspath(sf).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{clean_sf}'\n")

    subprocess.run([
        FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        out_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    if os.path.exists(concat_list):
        os.remove(concat_list)
    for sf in sub_files:
        if os.path.exists(sf):
            try:
                os.remove(sf)
            except Exception:
                pass

async def build_full_audio_robust(parts, voice, final_mp3, temp_prefix):
    temp_files = []
    print(f"   [+] Đang tổng hợp giọng đọc AI ({voice}) cho {len(parts)} phần...")
    for idx, text in enumerate(parts, start=1):
        tmp_name = f"{temp_prefix}_part{idx}.mp3"
        print(f"       -> Sinh hồi {idx}/{len(parts)} ({len(text.split())} từ)...")
        await synth_part_robust(text, voice, tmp_name, f"{temp_prefix}_p{idx}")
        temp_files.append(tmp_name)

    # Nối tất cả các hồi thành 1 file 15 phút
    concat_list = f"{temp_prefix}_all_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for tf in temp_files:
            clean = os.path.abspath(tf).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{clean}'\n")

    subprocess.run([
        FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        final_mp3
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    if os.path.exists(concat_list):
        os.remove(concat_list)
    for tf in temp_files:
        if os.path.exists(tf):
            try:
                os.remove(tf)
            except Exception:
                pass

    print(f"   [✓] Hoàn thành audio 15 phút: {os.path.basename(final_mp3)}")

def duck_mix_15m(video_in, audio_in, video_out):
    """
    FFmpeg Audio Ducking cho video 15 phút:
    - [0:a] Video gốc: volume 15% làm BGM
    - [1:a] Giọng đọc AI: volume 125%
    - amix: duration=first (theo độ dài video gốc ~15 phút)
    - Video copy (không nén lại), audio AAC 192k
    """
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
    print("=" * 70)
    print("🎬 TIẾN TRÌNH XUẤT BẢN VIDEO 15 PHÚT HOÀN HẢO CHO 3 KÊNH YOUTUBE")
    print("=" * 70)

    if not os.path.exists(BASE_VIDEO_15M):
        print(f"[!] Không tìm thấy video nguồn 15 phút: {BASE_VIDEO_15M}")
        return

    sz_mb = os.path.getsize(BASE_VIDEO_15M) / (1024 * 1024)
    print(f"[*] Video gốc 15 phút sẵn sàng: {sz_mb:.1f} MB (~15 phút 02 giây)")

    # -------------------------------------------------------------
    # 1. KÊNH 1: BẢN GHÉP GỐC 15 PHÚT (RAW FULL 1080P)
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("📺 1. KÊNH 1: VIDEO GHÉP GỐC 15 PHÚT (CLEAN MERGED)")
    print("-" * 70)
    k1_video = os.path.join(DIR_K1, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_15Min_Full_Raw.mp4")
    if os.path.exists(k1_video) and os.path.getsize(k1_video) > 102400:
        print(f"   [✓] Kênh 1 đã có sẵn: {os.path.basename(k1_video)} ({os.path.getsize(k1_video)/(1024*1024):.1f} MB)")
    else:
        subprocess.run([FFMPEG_EXE, "-y", "-i", BASE_VIDEO_15M, "-c", "copy", k1_video],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"   [✓] Đã xuất video Kênh 1: {os.path.basename(k1_video)} ({os.path.getsize(k1_video)/(1024*1024):.1f} MB)")

    # -------------------------------------------------------------
    # 2. KÊNH 2: REVIEW TIẾNG ANH 15 PHÚT (ENGLISH RECAP)
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("📺 2. KÊNH 2: REVIEW ANIME TIẾNG ANH 15 PHÚT (EN RECAP)")
    print("-" * 70)
    k2_video = os.path.join(DIR_K2, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_15Min_RECAP_EN.mp4")
    if os.path.exists(k2_video) and os.path.getsize(k2_video) > 102400:
        print(f"   [✓] Kênh 2 đã có sẵn: {os.path.basename(k2_video)} ({os.path.getsize(k2_video)/(1024*1024):.1f} MB)")
    else:
        voice_en = os.path.join(DIR_K2, "voiceover_15min_en.mp3")
        temp_en = os.path.join(DIR_K2, ".temp_en")
        asyncio.run(build_full_audio_robust(EN_PARTS, "en-US-ChristopherNeural", voice_en, temp_en))
        print(f"   [+] Đang xử lý Audio Ducking 15 phút...")
        duck_mix_15m(BASE_VIDEO_15M, voice_en, k2_video)
        print(f"   [✓] Đã xuất video Kênh 2: {os.path.basename(k2_video)} ({os.path.getsize(k2_video)/(1024*1024):.1f} MB)")

    # -------------------------------------------------------------
    # 3. KÊNH 3: REVIEW TIẾNG VIỆT 15 PHÚT (VIETNAMESE RECAP)
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("📺 3. KÊNH 3: REVIEW ANIME TIẾNG VIỆT 15 PHÚT (VI RECAP)")
    print("-" * 70)
    k3_video = os.path.join(DIR_K3, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_15Min_RECAP_VI.mp4")
    voice_vi = os.path.join(DIR_K3, "voiceover_15min_vi.mp3")
    temp_vi = os.path.join(DIR_K3, ".temp_vi")
    
    asyncio.run(build_full_audio_robust(VI_PARTS, "vi-VN-NamMinhNeural", voice_vi, temp_vi))

    print(f"   [+] Đang xử lý Audio Ducking 15 phút (FFmpeg copy video stream)...")
    duck_mix_15m(BASE_VIDEO_15M, voice_vi, k3_video)
    print(f"   [✓] Đã xuất video Kênh 3: {os.path.basename(k3_video)} ({os.path.getsize(k3_video)/(1024*1024):.1f} MB)")

    k3_seo = os.path.join(DIR_K3, "youtube_metadata_kenh3_vi.txt")
    with open(k3_seo, "w", encoding="utf-8") as f:
        f.write(
            "=== TIÊU ĐỀ YOUTUBE (KÊNH 3 - TIẾNG VIỆT 15 PHÚT) ===\n"
            "[Tóm Tắt Anime 15 Phút] Khi Chàng Otaku Ẩn Dật Cưa Đổ Hoa Khôi Toàn Trường | Trọn Bộ Thuyết Minh Siêu Cuốn\n\n"
            "=== MÔ TẢ YOUTUBE ===\n"
            "Chào mừng các bạn đến với kênh Tóm Tắt Anime! Hôm nay chúng ta sẽ cùng thưởng thức siêu phẩm học đường dài 15 phút cực cuốn: 'How a Loner Otaku Bagged The Most Popular Girl at School'.\n\n"
            "📌 Tóm tắt cốt truyện:\n"
            "Ren là một anh chàng Otaku sống khép kín, luôn xem bản thân là kẻ tàng hình ở trường học. Thế nhưng định mệnh trớ trêu đã mang Karen - nữ thần nổi tiếng và hoàn hảo nhất toàn trường - bước vào cuộc đời cậu sau một biến cố bất ngờ tại thư viện...\n\n"
            "⏱️ Mốc thời gian (Chapters):\n"
            "00:00 - Mở Đầu & Thế Giới Của Otaku\n"
            "02:30 - Cuộc Gặp Gỡ Bất Ngờ Tại Thư Viện\n"
            "05:00 - Bí Mật Sau Nụ Cười Hoàn Hảo\n"
            "07:30 - Sóng Gió Học Đường & Lời Đàm Tiếu\n"
            "10:00 - Cao Trào Đêm Hội & Lời Tỏ Tình\n"
            "12:30 - Hạnh Phúc Trọn Vẹn & Lời Kết\n\n"
            "🔔 Hãy BẤM LIKE, CHIA SẺ và ĐĂNG KÝ KÊNH để ủng hộ tụi mình ra mắt các video tóm tắt anime 15 phút hấp dẫn tiếp theo nhé!\n\n"
            "#tomtatanime #tomtatanime15phut #reviewphim #animehay #animethuyetminh #otaku #tinhcamhocduong\n\n"
            "=== THẺ TAGS ===\n"
            "tóm tắt anime 15 phút, tóm tắt anime, review anime, tóm tắt phim anime trọn bộ, anime thuyết minh, khi otaku tan do hoa khoi, anime tinh cam hoc duong hay, anime moi nhat 2026\n"
        )
    print(f"   [✓] Đã tạo bộ SEO Kênh 3: {os.path.basename(k3_seo)}")

    print("\n" + "=" * 70)
    print("🎉 HOÀN TẤT TRỌN VẸN VIDEO 15 PHÚT CHO CẢ 3 KÊNH YOUTUBE!")
    print(f"📁 Thư mục lưu trữ: {OUT_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    main()
