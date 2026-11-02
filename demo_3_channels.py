"""
DEMO 3 KÊNH YOUTUBE - ANIME RECAP PIPELINE
1. Kênh 1: Video ghép sạch, âm thanh gốc (Raw Full 1080p)
2. Kênh 2: Review tiếng Anh (English Voiceover AI + Audio Ducking + English SEO)
3. Kênh 3: Review tiếng Việt (Vietnamese Voiceover AI + Audio Ducking + Vietnamese SEO)
"""

import os
import sys
import asyncio
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_EXE = os.path.join(BASE_DIR, "tools", "ffmpeg", "ffmpeg.exe")
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"

SOURCE_VIDEO = os.path.join(
    BASE_DIR,
    "Output",
    "How a Loner Otaku Bagged The Most Popular Girl at School",
    "merged_episodes.mp4"
)

OUT_DIR = os.path.join(BASE_DIR, "Downloads", "Demo_3_Channels")
DIR_K1 = os.path.join(OUT_DIR, "Kenh_1_Raw_Full")
DIR_K2 = os.path.join(OUT_DIR, "Kenh_2_Review_EN")
DIR_K3 = os.path.join(OUT_DIR, "Kenh_3_Review_VI")

os.makedirs(DIR_K1, exist_ok=True)
os.makedirs(DIR_K2, exist_ok=True)
os.makedirs(DIR_K3, exist_ok=True)

# ------------------------------------------------------------------
# KỊCH BẢN MẪU ĐƯỢC THIẾT KẾ CHUẨN HOÁ
# ------------------------------------------------------------------
SCRIPT_EN = (
    "Welcome back to Anime Recap Central! Today, we're diving into a captivating story: "
    "How a Loner Otaku Bagged The Most Popular Girl at School. "
    "What happens when a completely introverted otaku, who believes he'll never have a chance at love, "
    "suddenly catches the eye of the prettiest and most popular girl on campus? "
    "In these opening episodes, a string of unexpected events flips his quiet life upside down. "
    "Is this pure destiny, or is there a hidden secret waiting to be uncovered? "
    "Sit back, grab some popcorn, and let's jump straight into the story! "
    "Make sure to smash that Like button and Subscribe so you never miss the next part!"
)

SCRIPT_VI = (
    "Chào mừng các bạn đã quay trở lại với Review Anime Siêu Cấp! "
    "Hôm nay, chúng ta sẽ cùng khám phá một siêu phẩm học đường cực cuốn: "
    "How a Loner Otaku Bagged The Most Popular Girl at School. "
    "Nếu bạn nghĩ một chàng trai Otaku sống khép kín thì vĩnh viễn không thể chạm tay vào tình yêu, "
    "thì bộ anime này sẽ khiến bạn phải suy nghĩ lại hoàn toàn. "
    "Ngay trong những tập mở đầu, hàng loạt biến cố bất ngờ đã xảy ra khi nữ thần xinh đẹp và nổi tiếng nhất trường "
    "lại bất ngờ bước vào cuộc đời của cậu ấy. "
    "Liệu đây là sự trùng hợp định mệnh, hay đằng sau đó là một bí mật mà không ai hay biết? "
    "Hãy cùng theo dõi trọn vẹn diễn biến ngay sau đây, "
    "và đừng quên nhấn Like cùng Đăng Ký Kênh để không bỏ lỡ những tập tiếp theo cực kỳ gay cấn nhé!"
)

async def generate_tts(text: str, voice: str, out_file: str):
    import edge_tts
    print(f"   [+] Đang tạo giọng đọc AI: {voice}...")
    com = edge_tts.Communicate(text, voice)
    await com.save(out_file)
    print(f"   [✓] Đã tạo xong audio: {os.path.basename(out_file)}")

def duck_and_mix(video_in: str, audio_in: str, video_out: str):
    """
    FFmpeg Audio Ducking:
    - [0:a] Video gốc: giảm âm lượng còn 15% (volume=0.15) làm nền (BGM)
    - [1:a] Giọng đọc AI: khuếch đại 125% (volume=1.25)
    - amix: trộn 2 luồng audio, thời lượng giữ theo video gốc (duration=first)
    - Video stream giữ nguyên không nén lại (stream copy - siêu nhanh)
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
        raise RuntimeError(f"FFmpeg error: {res.stderr}")

def main():
    print("=" * 65)
    print("🎬 KHỞI CHẠY DEMO XUẤT BẢN 3 KÊNH YOUTUBE TỪ 1 VIDEO NGUỒN")
    print("=" * 65)

    if not os.path.exists(SOURCE_VIDEO):
        print(f"[!] Không tìm thấy video nguồn tại: {SOURCE_VIDEO}")
        return

    src_size = os.path.getsize(SOURCE_VIDEO) / (1024 * 1024)
    print(f"[*] Video gốc: {os.path.basename(SOURCE_VIDEO)} ({src_size:.1f} MB)")

    # -------------------------------------------------------------
    # 1. KÊNH 1: BẢN GHÉP GỐC (RAW 1080P)
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print("📺 1. XỬ LÝ CHO KÊNH 1: VIDEO GHÉP GỐC (CLEAN MERGED)")
    print("-" * 65)
    k1_video = os.path.join(DIR_K1, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_Full_Ep01-03.mp4")
    
    # Dùng FFmpeg stream copy để tạo bản sạch
    subprocess.run([FFMPEG_EXE, "-y", "-i", SOURCE_VIDEO, "-c", "copy", k1_video],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"   [✓] Đã xuất video Kênh 1: {os.path.basename(k1_video)}")

    k1_seo = os.path.join(DIR_K1, "youtube_metadata_kenh1.txt")
    with open(k1_seo, "w", encoding="utf-8") as f:
        f.write(
            "=== TIÊU ĐỀ YOUTUBE (KÊNH 1) ===\n"
            "How a Loner Otaku Bagged The Most Popular Girl at School | Full Episodes 1-3 [Full HD]\n\n"
            "=== MÔ TẢ YOUTUBE ===\n"
            "Watch How a Loner Otaku Bagged The Most Popular Girl at School Episodes 1 to 3 uninterrupted.\n"
            "Enjoy the story in original high quality sound and video.\n\n"
            "⏱️ Chapters:\n"
            "00:00 - Episode 1\n"
            "00:15 - Episode 2\n"
            "00:30 - Episode 3\n\n"
            "#anime #fullepisode #trimz #romance #otaku\n"
        )
    print(f"   [✓] Đã tạo bộ SEO Kênh 1: {os.path.basename(k1_seo)}")

    # -------------------------------------------------------------
    # 2. KÊNH 2: REVIEW TIẾNG ANH (ENGLISH RECAP)
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print("📺 2. XỬ LÝ CHO KÊNH 2: REVIEW ANIME TIẾNG ANH (EN RECAP)")
    print("-" * 65)
    voice_en = os.path.join(DIR_K2, "voiceover_en.mp3")
    asyncio.run(generate_tts(SCRIPT_EN, "en-US-ChristopherNeural", voice_en))

    k2_video = os.path.join(DIR_K2, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_RECAP_EN.mp4")
    print(f"   [+] Đang xử lý Audio Ducking & ghép lồng tiếng Anh...")
    duck_and_mix(SOURCE_VIDEO, voice_en, k2_video)
    print(f"   [✓] Đã xuất video Kênh 2: {os.path.basename(k2_video)} ({os.path.getsize(k2_video)/(1024*1024):.1f} MB)")

    k2_script_file = os.path.join(DIR_K2, "script_en.txt")
    with open(k2_script_file, "w", encoding="utf-8") as f:
        f.write(SCRIPT_EN)

    k2_seo = os.path.join(DIR_K2, "youtube_metadata_kenh2_en.txt")
    with open(k2_seo, "w", encoding="utf-8") as f:
        f.write(
            "=== YOUTUBE TITLE (CHANNEL 2 - ENGLISH) ===\n"
            "[Anime Recap] When A Loner Otaku Dates The Prettiest Girl In School! | Episodes 1-3 Full Recap\n\n"
            "=== YOUTUBE DESCRIPTION ===\n"
            "Welcome to Anime Recap Central! In today's video, we recap the story of 'How a Loner Otaku Bagged The Most Popular Girl at School'.\n\n"
            "📌 Plot Overview:\n"
            "A secluded otaku boy unexpectedly finds himself becoming the center of attention for the most gorgeous girl in the entire school. Here is what happens from Episode 1 to 3...\n\n"
            "⏱️ Timestamps / Chapters:\n"
            "00:00 - Introduction & Premise\n"
            "00:15 - Episode 1-2 Key Moments\n"
            "00:30 - The Big Turning Point\n"
            "00:40 - Outro & What's Next\n\n"
            "🔔 Don't forget to LIKE, SHARE, and SUBSCRIBE for more daily anime recaps!\n\n"
            "#AnimeRecap #AnimeSummary #RomanceAnime #Otaku #AnimeReview\n\n"
            "=== TAGS ===\n"
            "anime recap, anime summary, anime explained, english anime recap, how a loner otaku bagged the most popular girl at school recap, best romance anime, anime review 2026\n"
        )
    print(f"   [✓] Đã tạo kịch bản & bộ SEO Kênh 2: {os.path.basename(k2_seo)}")

    # -------------------------------------------------------------
    # 3. KÊNH 3: REVIEW TIẾNG VIỆT (VIETNAMESE RECAP)
    # -------------------------------------------------------------
    print("\n" + "-" * 65)
    print("📺 3. XỬ LÝ CHO KÊNH 3: REVIEW ANIME TIẾNG VIỆT (VI RECAP)")
    print("-" * 65)
    voice_vi = os.path.join(DIR_K3, "voiceover_vi.mp3")
    asyncio.run(generate_tts(SCRIPT_VI, "vi-VN-NamMinhNeural", voice_vi))

    k3_video = os.path.join(DIR_K3, "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_RECAP_VI.mp4")
    print(f"   [+] Đang xử lý Audio Ducking & ghép lồng tiếng Việt...")
    duck_and_mix(SOURCE_VIDEO, voice_vi, k3_video)
    print(f"   [✓] Đã xuất video Kênh 3: {os.path.basename(k3_video)} ({os.path.getsize(k3_video)/(1024*1024):.1f} MB)")

    k3_script_file = os.path.join(DIR_K3, "script_vi.txt")
    with open(k3_script_file, "w", encoding="utf-8") as f:
        f.write(SCRIPT_VI)

    k3_seo = os.path.join(DIR_K3, "youtube_metadata_kenh3_vi.txt")
    with open(k3_seo, "w", encoding="utf-8") as f:
        f.write(
            "=== TIÊU ĐỀ YOUTUBE (KÊNH 3 - TIẾNG VIỆT) ===\n"
            "[Tóm Tắt Anime] Khi Otaku Ẩn Dật Tán Đổ Hoa Khôi Toàn Trường | Trọn Bộ Tập 1-3 Thuyết Minh\n\n"
            "=== MÔ TẢ YOUTUBE ===\n"
            "Chào mừng các bạn đến với kênh Review Anime! Hôm nay chúng ta sẽ cùng thưởng thức siêu phẩm học đường cực cuốn: 'How a Loner Otaku Bagged The Most Popular Girl at School'.\n\n"
            "📌 Tóm tắt nội dung:\n"
            "Câu chuyện kể về chàng trai Otaku sống thu mình bất ngờ được cô gái xinh đẹp, nổi tiếng nhất trường chủ động tiếp cận. Liệu tình yêu bất ngờ này có phải là định mệnh hay còn uẩn khúc gì đằng sau?\n\n"
            "⏱️ Mốc thời gian (Chapters):\n"
            "00:00 - Giới thiệu & Mở đầu câu chuyện\n"
            "00:15 - Diễn biến kịch tính Tập 1 - 2\n"
            "00:30 - Bước ngoặt bất ngờ\n"
            "00:40 - Đánh giá & Kết thúc\n\n"
            "🔔 Hãy BẤM LIKE và ĐĂNG KÝ KÊNH để ủng hộ tụi mình ra mắt các video tóm tắt anime mới nhất nhé!\n\n"
            "#tomtatanime #reviewanime #reviewphim #animethuyetminh #otaku #animehocduong\n\n"
            "=== THẺ TAGS ===\n"
            "tóm tắt anime, review anime, tóm tắt phim anime, anime thuyết minh, review phim anime, khi otaku tan do hoa khoi, anime tinh cam hoc duong hay, anime moi nhat\n"
        )
    print(f"   [✓] Đã tạo kịch bản & bộ SEO Kênh 3: {os.path.basename(k3_seo)}")

    print("\n" + "=" * 65)
    print("🎉 HOÀN TẤT DEMO CHO CẢ 3 KÊNH YOUTUBE!")
    print(f"📁 Toàn bộ sản phẩm được lưu tại:\n   {OUT_DIR}")
    print("=" * 65)

if __name__ == "__main__":
    main()

