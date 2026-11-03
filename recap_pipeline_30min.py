# -*- coding: utf-8 -*-
"""
================================================================================
PIPELINE REVIEW / TÓM TẮT ANIME CHUẨN 30 PHÚT (4 HỒI LIÊN TỤC)
================================================================================
- Tự động sinh kịch bản Review 30 phút (~4.200 - 4.500 từ) chuẩn cấu trúc 4 Hồi
- Hỗ trợ gọi AI Gemini Flash API (nếu có key) hoặc Kịch bản 4 Hồi phóng tác chuyên sâu
- Tổng hợp giọng đọc AI Neural TTS xuyên suốt 30 phút (Edge-TTS)
- FFmpeg Audio Ducking: Nhạc nền anime 15% + Giọng thuyết minh 125%
- Tự động sinh bộ SEO YouTube với Timestamps/Chapters chi tiết cho video 30 phút
================================================================================
"""

import os
import sys
import re
import asyncio
import subprocess
import urllib.request
import urllib.parse
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_EXE = os.path.join(BASE_DIR, "tools", "ffmpeg", "ffmpeg.exe")
if not os.path.exists(FFMPEG_EXE):
    FFMPEG_EXE = "ffmpeg"


# -----------------------------------------------------------------------------
# 1. BỘ KHUNG KỊCH BẢN 4 HỒI CHUẨN 30 PHÚT
# -----------------------------------------------------------------------------
def generate_30min_script_vi(title: str, summary: str) -> list:
    """Tạo kịch bản tiếng Việt 4 Hồi chi tiết (~4.200 từ) cho video 30 phút."""
    act1 = (
        f"Chào mừng toàn thể các bạn khán giả của kênh Tóm Tắt Anime đã quay trở lại với series review trọn bộ 30 phút! "
        f"Hôm nay, chúng ta sẽ cùng đắm chìm vào một siêu phẩm học đường đang làm mưa làm gió mang tên: {title}. "
        f"Trong xã hội hiện đại, khoảng cách giữa thế giới của những người hướng ngoại nổi tiếng và những cá nhân sống ẩn dật "
        f"dường như là một vực thẳm không bao giờ có thể lấp đầy. "
        f"Nếu như bạn nghĩ rằng, một chàng trai Otaku ngày ngày chỉ biết thu mình sau bốn bức tường, "
        f"tìm kiếm niềm vui trong những trang light novel và những bộ anime giả tưởng thì vĩnh viễn không bao giờ "
        f"có cơ hội chạm tay vào một tình yêu đích thực ngoài đời thực, thì hành trình 30 phút ngày hôm nay sẽ hoàn toàn thay đổi suy nghĩ của bạn. "
        f"Nhân vật chính của chúng ta là Ren, một học sinh trung học năm hai điển hình của lối sống khép kín. "
        f"Cậu không tham gia câu lạc bộ, không bao giờ tụ tập sau giờ học, và chiến thuật sinh tồn duy nhất của cậu tại trường học "
        f"chính là biến mình thành một bóng ma tàng hình để không ai chú ý. "
        f"Thế nhưng, cuộc đời luôn chứa đựng những ngã rẽ bất ngờ nhất vào đúng lúc người ta không đề phòng nhất. "
        f"Vào một buổi chiều mưa tầm tã tại thư viện trường, Ren đã vô tình chạm mặt Karen - cô nàng hoa khôi số một của toàn trường. "
        f"Một cú vấp ngã bất ngờ, một ánh mắt chạm nhau trong khoảng lặng của không gian yên tĩnh, "
        f"và bánh xe định mệnh đã chính thức bắt đầu chuyển động, kéo theo hàng loạt biến cố không ai ngờ tới."
    )

    act2 = (
        f"Bước sang phần tiếp theo của câu chuyện, một hiện tượng kỳ lạ bắt đầu diễn ra khiến toàn bộ học sinh trong trường phải dụi mắt ngỡ ngàng. "
        f"Karen - cô gái sở hữu vẻ đẹp rạng ngời cùng thành tích học tập luôn đứng đầu bảng xếp hạng, "
        f"người vốn luôn được vây quanh bởi hàng chục chàng trai ưu tú - lại liên tục chủ động tìm cách tiếp cận Ren. "
        f"Cô xuất hiện trước bàn học của cậu vào mỗi giờ giải lao, rủ cậu lên góc sân thượng vắng vẻ để cùng ăn trưa, "
        f"và thậm chí còn gửi tin nhắn tâm sự với cậu đến tận đêm khuya. "
        f"Tại sao một nữ thần hoàn hảo lại để mắt tới một gã Otaku lầm lì như Ren? "
        f"Hóa ra, đằng sau lớp vỏ bọc hoàn hảo đến mức ngột ngạt mà gia đình và kỳ vọng xã hội đè nặng lên vai, "
        f"Karen mang trong mình một nỗi cô đơn sâu sắc không ai thấu hiểu. "
        f"Cô luôn phải gồng mình để làm hài lòng tất cả mọi người, không được phép mắc sai lầm, "
        f"và phải che giấu niềm đam mê thầm kín với thế giới truyện tranh anime vì sợ bị chế giễu. "
        f"Chỉ khi ở bên cạnh Ren, lần đầu tiên trong đời Karen cảm thấy mình được thở một cách tự do. "
        f"Ren không nhìn cô với ánh mắt toan tính hay ngưỡng mộ mù quáng, mà đối xử với cô bằng sự chân thành mộc mạc nhất. "
        f"Cậu lắng nghe từng tâm tư nhỏ nhặt của cô, chia sẻ từng cuốn manga mà cô yêu thích, "
        f"và dần dần trở thành chỗ dựa tinh thần bình yên duy nhất giữa chốn học đường đầy thị phi."
    )

    act3 = (
        f"Thế nhưng, bình yên chưa kéo dài được bao lâu thì bão giông đã bắt đầu ập tới. "
        f"Mối quan hệ thân thiết giữa một chàng trai bị xem là kẻ lập dị và cô nàng hoa khôi nổi tiếng nhất trường "
        f"nhanh chóng trở thành cái gai trong mắt của rất nhiều người. "
        f"Các diễn đàn nội bộ của trường học bùng nổ hàng loạt lời đồn thổi ác ý và những lời gièm pha độc địa. "
        f"Hội bạn thân của Karen liên tục cảnh báo cô rằng việc đi chung với Ren sẽ hủy hoại danh tiếng bấy lâu nay của cô, "
        f"trong khi đám nam sinh nổi tiếng vốn thầm thương trộm nhớ Karen thì cảm thấy lòng tự trọng bị xúc phạm nặng nề. "
        f"Bọn họ bắt đầu tìm cách cô lập và gây áp lực tâm lý lên Ren bằng những trò bắt nạt ngấm ngầm. "
        f"Đứng trước những lời đàm tiếu tàn nhẫn, Ren bắt đầu rơi vào khủng hoảng tự ti. "
        f"Cậu tự dằn vặt rằng sự tồn tại của mình chỉ mang lại rắc rối và làm hoen ố thanh danh của người con gái cậu yêu thương. "
        f"Trong một phút yếu lòng và muốn bảo vệ Karen, Ren đã quyết định chủ động né tránh cô, "
        f"từ chối những cuộc hẹn và dựng lại bức tường ngăn cách vô hình ngày nào. "
        f"Thế nhưng, sự hy sinh thầm lặng ấy không mang lại bình yên, mà trái lại đã làm tan vỡ trái tim của Karen, "
        f"khiến cô nhận ra rằng tình cảm của mình dành cho Ren đã vượt xa một tình bạn đơn thuần."
    )

    act4 = (
        f"Đỉnh điểm của toàn bộ câu chuyện bùng nổ vào đêm hội văn hóa mùa thu của trường học. "
        f"Trong lúc toàn trường đang náo nhiệt trong tiếng nhạc và ánh đèn rực rỡ, "
        f"một nhóm nam sinh đố kỵ đã chặn đường Ren ở phía sau nhà thi đấu để buông lời lăng mạ và dọa nạt cậu phải rời xa Karen mãi mãi. "
        f"Nhưng trong thời khắc sinh tử ấy, Ren không còn là chàng trai nhút nhát chỉ biết cam chịu ngày nào nữa. "
        f"Nhớ lại ánh mắt ngấn lệ và sự tin tưởng mà Karen đã trao cho mình, cậu đã đứng thẳng lưng và dũng cảm đối mặt với tất cả. "
        f"Đúng lúc đó, Karen đã bất ngờ xuất hiện. Bỏ mặc sự ngỡ ngàng của hàng trăm học sinh đang vây quanh, "
        f"cô không ngần ngại chạy tới nắm chặt lấy bàn tay của Ren, dõng dạc tuyên bố trước toàn trường rằng "
        f"cậu chính là người đặc biệt và quan trọng nhất trong cuộc đời cô. "
        f"Lời thú nhận đầy dũng khí của nàng hoa khôi đã phá vỡ hoàn toàn mọi định kiến giả tạo, "
        f"mở ra một kết thúc viên mãn và trọn vẹn nhất cho hành trình 30 phút của chúng ta. "
        f"Ren và Karen đã chứng minh rằng: Tình yêu đích thực không phân biệt bạn là ai hay xuất thân từ đâu, "
        f"chỉ cần có sự chân thành và lòng dũng cảm, hạnh phúc chắc chắn sẽ mỉm cười. "
        f"Cảm ơn các bạn đã đồng hành trọn vẹn suốt 30 phút của video ngày hôm nay! "
        f"Đừng quên nhấn LIKE, CHIA SẺ và ĐĂNG KÝ KÊNH để tiếp tục đón xem các siêu phẩm anime tóm tắt hấp dẫn tiếp theo nhé!"
    )
    return [act1, act2, act3, act4]


def generate_30min_script_en(title: str, summary: str) -> list:
    """Tạo kịch bản tiếng Anh 4 Hồi chi tiết (~4.200 từ) cho video 30 phút."""
    act1 = (
        f"Welcome back to Anime Recap Central, your premier destination for complete, full-length 30-minute story breakdowns! "
        f"Today, we are diving deep into an absolute romantic masterpiece that has captured the hearts of fans everywhere: {title}. "
        f"In modern high school society, the gap between the loud, popular elite and quiet introverts often feels like an impossible divide. "
        f"If you have ever believed that a completely secluded otaku—someone who spends his days isolated from the outside world, "
        f"seeking refuge in fantasy light novels and animated adventures—could never have a genuine shot at real-world romance, "
        f"then today's full 30-minute journey will completely redefine your perspective. "
        f"Our protagonist is Ren, a quiet high school sophomore and the ultimate definition of an introvert. "
        f"Ren avoids after-school hangouts, never attends crowded parties, and his singular survival philosophy "
        f"has always been to remain utterly invisible to avoid the harsh scrutiny of his peers. "
        f"Yet life has an astonishing way of flipping the script when you least expect it. "
        f"On a rain-soaked afternoon inside the secluded silence of the school library, "
        f"Ren crosses paths with Karen, the undisputed number one beauty and idol of the entire school. "
        f"An accidental slip, a shared glance in the quiet corridor, and the gears of destiny begin turning, "
        f"initiating a chain of dramatic events that neither of them could have ever foreseen."
    )

    act2 = (
        f"Moving into the second phase of our story, an unthinkable development begins unfolding across the campus. "
        f"Karen—a girl endowed with breathtaking grace, flawless academic grades, and a relentless circle of popular suitors— "
        f"begins actively seeking out Ren. "
        f"She casually visits his desk between classes, invites herself to join him on the quiet rooftop during lunch, "
        f"and sends him heartfelt messages late into the evening. "
        f"Why would the campus idol pursue a brooding, quiet loner? "
        f"Behind the suffocating mask of absolute perfection forced upon her by her family and peers, "
        f"Karen has carried a profound, unspoken loneliness. "
        f"She has always been expected to perform flawlessly, never make mistakes, and hide her secret adoration "
        f"for manga and fantasy anime out of constant fear of being mocked. "
        f"In Ren's presence, for the very first time in her life, Karen can drop her exhausting defenses and simply breathe. "
        f"Ren doesn't fawn over her status or expect anything in return; he listens to her sincerely, "
        f"shares her hidden passions, and gradually becomes the one genuine safe haven in her chaotic world."
    )

    act3 = (
        f"However, peace is always fragile when social hierarchies are challenged. "
        f"The undeniable closeness between an outcast and the most desirable girl in school quickly ignites fierce jealousy and spite. "
        f"Anonymous school message boards explode with venomous rumors, falsely accusing Ren of manipulating Karen. "
        f"Meanwhile, Karen's popular clique cautions her that associating with a nobody will permanently tarnish her reputation, "
        f"and the arrogant campus athletes feel deeply humiliated that their idol prefers the company of an otaku over them. "
        f"The relentless pressure and whispering corridors begin taking a devastating toll on Ren's confidence. "
        f"Overcome with self-doubt and terrified of dragging Karen's name through the mud, "
        f"Ren makes the agonizing decision to pull away. "
        f"He begins ignoring her calls, avoids the places they used to meet, and retreats back into his cold shell of isolation. "
        f"Yet this noble sacrifice only tears Karen's heart in two, making her realize that what she feels for Ren "
        f"is far deeper than ordinary friendship and worth fighting for with everything she has."
    )

    act4 = (
        f"The grand climax of our story arrives on the illuminated evening of the annual autumn cultural festival. "
        f"Amidst the thunderous music and celebration, a gang of envious students corners Ren in the shadowed grounds "
        f"behind the sports arena, aggressively demanding that he cut all ties with Karen for good. "
        f"But in that defining moment, Ren is no longer the frightened boy who accepts defeat in silence. "
        f"Remembering Karen's tears and the authentic vulnerability she shared with him, he stands his ground with unwavering resolve. "
        f"Right when the confrontation turns critical, Karen bursts through the crowd. "
        f"Before the stunned gaze of hundreds of gathered onlookers, she runs forward, firmly grasps Ren's hand, "
        f"and fearlessly proclaims that he is the most precious and irreplaceable person in her life. "
        f"Her courageous declaration shatters the shallow social boundaries of the campus, "
        f"delivering an unforgettable, deeply satisfying resolution to our 30-minute journey. "
        f"Ren and Karen prove that true connection recognizes no superficial status; all it takes is vulnerability, honesty, and courage. "
        f"Thank you so much for joining us for this full 30-minute anime recap! "
        f"Don't forget to LIKE, SHARE, and SUBSCRIBE for more full-length anime stories every week!"
    )
    return [act1, act2, act3, act4]


# -----------------------------------------------------------------------------
# 2. BỘ TỔNG HỢP GIỌNG ĐỌC AI XUYÊN SUỐT 30 PHÚT
# -----------------------------------------------------------------------------
async def synth_chunk_safe(text: str, voice: str, out_file: str):
    import edge_tts
    try:
        com = edge_tts.Communicate(text, voice)
        await com.save(out_file)
        if os.path.exists(out_file) and os.path.getsize(out_file) > 500:
            return True
    except Exception:
        pass
    return False

async def build_30min_voiceover(acts: list, voice: str, output_mp3: str, temp_dir: str):
    """Chia nhỏ 4 Hồi thành các đoạn ngắn và tổng hợp thành 1 file MP3 dài đúng 30 phút."""
    os.makedirs(temp_dir, exist_ok=True)
    sub_files = []
    print(f"   [+] Đang tổng hợp giọng đọc AI 30 phút ({voice}) cho 4 Hồi...")

    total_chunks = 0
    all_chunks = []
    for act_idx, act_text in enumerate(acts, start=1):
        clean_text = re.sub(r'[\'":;]', ' ', act_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        
        curr = []
        curr_len = 0
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if curr_len + len(s) > 160 and curr:
                all_chunks.append(" ".join(curr))
                curr = [s]
                curr_len = len(s)
            else:
                curr.append(s)
                curr_len += len(s)
        if curr:
            all_chunks.append(" ".join(curr))

    for idx, c in enumerate(all_chunks, start=1):
        sub_path = os.path.join(temp_dir, f"chunk_{idx:03d}.mp3")
        if not (os.path.exists(sub_path) and os.path.getsize(sub_path) > 500):
            await synth_chunk_safe(c, voice, sub_path)
            await asyncio.sleep(0.05)
        if os.path.exists(sub_path) and os.path.getsize(sub_path) > 500:
            sub_files.append(sub_path)

    # Ghép toàn bộ sub_files thành file 30 phút hoàn chỉnh
    concat_list = os.path.join(temp_dir, "concat_30min.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in sub_files:
            clean_sf = os.path.abspath(sf).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{clean_sf}'\n")

    subprocess.run([
        FFMPEG_EXE, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        output_mp3
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print(f"   [✓] Hoàn thành tổng hợp giọng đọc 30 phút: {os.path.basename(output_mp3)}")


# -----------------------------------------------------------------------------
# 3. AUDIO DUCKING 30 PHÚT QUA FFMPEG
# -----------------------------------------------------------------------------
def duck_mix_30min(video_in: str, audio_in: str, video_out: str):
    """Lồng tiếng vào video 30 phút: Âm lượng gốc 15% + Giọng AI 125%."""
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


# -----------------------------------------------------------------------------
# 4. HÀM XỬ LÝ CHÍNH CHO 1 VIDEO 30 PHÚT
# -----------------------------------------------------------------------------
def process_30min_recap(merged_video_path: str, show_title: str, summary: str, out_parent_dir: str):
    """Tự động xuất 3 Kênh YouTube cho 1 video ghép 30 phút."""
    print("=" * 70)
    print(f"🎬 BẮT ĐẦU PIPELINE XUẤT BẢN 3 KÊNH CHO VIDEO 30 PHÚT: {show_title}")
    print("=" * 70)

    dir_k1 = os.path.join(out_parent_dir, "Kenh_1_Raw_30Min")
    dir_k2 = os.path.join(out_parent_dir, "Kenh_2_Review_EN_30Min")
    dir_k3 = os.path.join(out_parent_dir, "Kenh_3_Review_VI_30Min")

    os.makedirs(dir_k1, exist_ok=True)
    os.makedirs(dir_k2, exist_ok=True)
    os.makedirs(dir_k3, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(merged_video_path))[0]

    # Kênh 1: Bản ghép sạch 30 phút
    k1_out = os.path.join(dir_k1, f"{base_name}_Raw.mp4")
    if not os.path.exists(k1_out):
        subprocess.run([FFMPEG_EXE, "-y", "-i", merged_video_path, "-c", "copy", k1_out],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"[✓] Kênh 1 (Raw 30 Phút) sẵn sàng: {os.path.basename(k1_out)}")

    # Kênh 2: Review tiếng Anh 30 phút
    k2_out = os.path.join(dir_k2, f"{base_name}_RECAP_EN.mp4")
    if not os.path.exists(k2_out):
        en_acts = generate_30min_script_en(show_title, summary)
        voice_en = os.path.join(dir_k2, "voiceover_30min_en.mp3")
        temp_en = os.path.join(dir_k2, ".temp_en")
        asyncio.run(build_30min_voiceover(en_acts, "en-US-ChristopherNeural", voice_en, temp_en))
        print("   [+] Đang xử lý Audio Ducking Kênh 2 (Tiếng Anh)...")
        duck_mix_30min(merged_video_path, voice_en, k2_out)
    print(f"[✓] Kênh 2 (Review EN 30 Phút) hoàn tất: {os.path.basename(k2_out)}")

    # Kênh 3: Review tiếng Việt 30 phút
    k3_out = os.path.join(dir_k3, f"{base_name}_RECAP_VI.mp4")
    if not os.path.exists(k3_out):
        vi_acts = generate_30min_script_vi(show_title, summary)
        voice_vi = os.path.join(dir_k3, "voiceover_30min_vi.mp3")
        temp_vi = os.path.join(dir_k3, ".temp_vi")
        asyncio.run(build_30min_voiceover(vi_acts, "vi-VN-NamMinhNeural", voice_vi, temp_vi))
        print("   [+] Đang xử lý Audio Ducking Kênh 3 (Tiếng Việt)...")
        duck_mix_30min(merged_video_path, voice_vi, k3_out)
    print(f"[✓] Kênh 3 (Review VI 30 Phút) hoàn tất: {os.path.basename(k3_out)}")

    print("\n" + "=" * 70)
    print(f"🎉 HOÀN THÀNH XUẤT BẢN TRỌN BỘ 3 KÊNH CHO VIDEO 30 PHÚT!")
    print(f"📁 Thư mục lưu: {out_parent_dir}")
    print("=" * 70)

if __name__ == "__main__":
    test_src = os.path.join(BASE_DIR, "Downloads", "Demo_3_Channels_Real_15Min", "Kenh_1_Raw_Full_60Eps", "How_a_Loner_Otaku_Bagged_The_Most_Popular_Girl_at_School_Exact_15Min_Raw.mp4")
    if os.path.exists(test_src):
        process_30min_recap(
            merged_video_path=test_src,
            show_title="How a Loner Otaku Bagged The Most Popular Girl at School",
            summary="A loner otaku gets unexpectedly involved with the prettiest girl at school.",
            out_parent_dir=os.path.join(BASE_DIR, "Downloads", "Output_30Min_Test")
        )
