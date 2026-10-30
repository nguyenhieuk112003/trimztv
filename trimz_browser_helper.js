// ========================================================
// Trimz.tv Browser Helper Script
// Cách dùng: Khi đang mở trang phim trên https://trimz.tv/
// Bấm F12 -> chọn Console -> Dán đoạn mã này vào và Enter!
// ========================================================

(function () {
  const html = document.documentElement.innerHTML;
  const mp4Regex = /https:\/\/cdn\.trimz\.co\/generated-videos\/ms_videos\/[a-zA-Z0-9_\-]+\.mp4/g;
  const matches = html.match(mp4Regex) || [];
  const uniqueUrls = [...new Set(matches)];

  if (uniqueUrls.length === 0) {
    alert("Không tìm thấy link video MP4 nào trên trang này! Hãy mở trang chi tiết của bộ phim.");
    return;
  }

  // Tiêu đề phim
  const title = (document.title || "Trimz_Video").split(" - ")[0].split(" | ")[0].replace(/[\\/*?:"<>|]/g, "_").trim();

  // Tạo khung giao diện nổi (Floating panel)
  let existing = document.getElementById("trimz-downloader-panel");
  if (existing) existing.remove();

  const panel = document.createElement("div");
  panel.id = "trimz-downloader-panel";
  panel.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 999999;
    background: #18181b;
    color: #fff;
    border: 1px solid #3f3f46;
    border-radius: 12px;
    padding: 16px 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
    min-width: 300px;
  `;

  panel.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
      <strong style="color:#22c55e; font-size: 15px;">🎬 Trimz Video Downloader</strong>
      <button id="trimz-close-btn" style="background:none; border:none; color:#a1a1aa; cursor:pointer; font-size:16px;">✕</button>
    </div>
    <div style="font-size:13px; color:#e4e4e7; margin-bottom: 8px;"><b>Phim:</b> ${title}</div>
    <div style="font-size:13px; color:#a1a1aa; margin-bottom: 14px;">Tìm thấy: <b style="color:#22c55e;">${uniqueUrls.length}</b> tập (MP4 trực tiếp)</div>
    <div style="display:flex; flex-direction:column; gap:8px;">
      <button id="trimz-copy-all" style="background:#2563eb; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-weight:500;">📋 Sao chép ${uniqueUrls.length} link (Dán vào IDM)</button>
      <button id="trimz-download-txt" style="background:#4b5563; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-weight:500;">💾 Tải file links.txt</button>
      <button id="trimz-download-first" style="background:#16a34a; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-weight:500;">⬇️ Tải Tập 1 (MP4)</button>
    </div>
  `;

  document.body.appendChild(panel);

  document.getElementById("trimz-close-btn").onclick = () => panel.remove();

  // Copy all links
  document.getElementById("trimz-copy-all").onclick = () => {
    navigator.clipboard.writeText(uniqueUrls.join("\n")).then(() => {
      alert(`Đã sao chép ${uniqueUrls.length} link MP4 vào bộ nhớ tạm! Bạn có thể dán vào IDM để tải.`);
    });
  };

  // Download links.txt
  document.getElementById("trimz-download-txt").onclick = () => {
    const blob = new Blob([uniqueUrls.join("\n")], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${title}_links.txt`;
    a.click();
  };

  // Download episode 1 directly
  document.getElementById("trimz-download-first").onclick = () => {
    const a = document.createElement("a");
    a.href = uniqueUrls[0];
    a.download = `${title}_Tap_001.mp4`;
    a.target = "_blank";
    a.click();
  };
})();
