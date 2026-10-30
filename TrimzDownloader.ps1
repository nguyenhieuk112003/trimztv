# ========================================================
# Trimz.tv Auto Video Downloader (PowerShell Script)
# Tu dong quet va tai toan bo video/tap phim tu Trimz.tv
# ========================================================

param (
    [string]$Url = "",
    [string]$OutputDir = "$PSScriptRoot\Downloads",
    [string]$EpisodeRange = ""
)

function Get-CleanFileName([string]$name) {
    return ($name -replace '[\\/*?:"<>|]', '_').Trim()
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "          TRIMZ.TV VIDEO DOWNLOADER TOOL                  " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# Neu nguoi dung chua nhap URL thi yeu cau nhap
if ([string]::IsNullOrWhiteSpace($Url)) {
    $Url = Read-Host "Nhap URL phim/series tren Trimz (vi du: https://trimz.tv/ten-phim)"
}

if ([string]::IsNullOrWhiteSpace($Url)) {
    Write-Host "[!] URL khong hop le. Thoat chuong trinh." -ForegroundColor Red
    exit 1
}

$Url = $Url.Trim()
if (-not ($Url -match "^https?://")) {
    $Url = "https://trimz.tv/" + $Url.TrimStart("/")
}

Write-Host "`n[*] Dang ket noi toi: $Url ..." -ForegroundColor Green

# Tai ma nguon trang
$tempHtml = [System.IO.Path]::GetTempFileName()
try {
    curl.exe -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" -o $tempHtml $Url
    $html = Get-Content -Path $tempHtml -Raw -Encoding UTF8
}
catch {
    Write-Host "[!] Khong the tai trang web: $_" -ForegroundColor Red
    if (Test-Path $tempHtml) { Remove-Item $tempHtml -Force }
    exit 1
}
finally {
    if (Test-Path $tempHtml) { Remove-Item $tempHtml -Force }
}

if ([string]::IsNullOrWhiteSpace($html)) {
    Write-Host "[!] Khong the doc noi dung trang web." -ForegroundColor Red
    exit 1
}

# Trich xuat ten phim
$titleMatch = [regex]::Match($html, '<title>([^<]+)</title>')
$title = "Trimz_Show"
if ($titleMatch.Success) {
    $title = $titleMatch.Groups[1].Value
    $title = $title -replace ' - Trimz.*$', ''
    $title = $title -replace ' \| Trimz.*$', ''
    $title = $title -replace ': Watch & Create Shows.*$', ''
}
$safeTitle = Get-CleanFileName $title
Write-Host "[*] Ten phim: $safeTitle" -ForegroundColor Yellow

# Tim tat ca cac link video mp4 truc tiep
$mp4Regex = [regex]::Matches($html, 'https://cdn\.trimz\.co/generated-videos/ms_videos/[a-zA-Z0-9_\-]+\.mp4')
$videoUrls = @()
$seen = New-Object System.Collections.Generic.HashSet[string]

foreach ($m in $mp4Regex) {
    $vUrl = $m.Value
    if ($seen.Add($vUrl)) {
        $videoUrls += $vUrl
    }
}

if ($videoUrls.Count -eq 0) {
    Write-Host "[!] Khong tim thay link video MP4 nao tren trang nay." -ForegroundColor Red
    Write-Host "Goi y: Hay kiem tra lai duong dan link chi tiet cua phim/series (vi du: https://trimz.tv/slug-phim)" -ForegroundColor Yellow
    exit 1
}

Write-Host "[+] Tim thay tong cong $($videoUrls.Count) tap phim!" -ForegroundColor Green

# Thu muc luu video
$showFolder = Join-Path $OutputDir $safeTitle
if (-not (Test-Path $showFolder)) {
    New-Item -ItemType Directory -Path $showFolder -Force | Out-Null
}
Write-Host "[*] Thu muc luu: $showFolder`n" -ForegroundColor Gray

# Lua chon tap can tai
if ([string]::IsNullOrWhiteSpace($EpisodeRange)) {
    Write-Host "Chon che do tai:" -ForegroundColor Cyan
    Write-Host "  [1] Tai toan bo $($videoUrls.Count) tap (go 'all' hoac an Enter)"
    Write-Host "  [2] Tai theo khoang (vi du: 1-10)"
    Write-Host "  [3] Tai cac tap cu the (vi du: 1,3,5)"
    Write-Host "  [4] Xuat danh sach link ra file text (de dan vao IDM)"
    $choice = Read-Host "Nhap lua chon cua ban (Mac dinh la 'all')"
    if ([string]::IsNullOrWhiteSpace($choice)) {
        $EpisodeRange = "all"
    } else {
        $EpisodeRange = $choice.Trim()
    }
}

if ($EpisodeRange -eq "4") {
    $txtPath = Join-Path $showFolder "links.txt"
    $videoUrls | Set-Content -Path $txtPath -Encoding UTF8
    Write-Host "`n[V] Da xuat $($videoUrls.Count) link vao: $txtPath" -ForegroundColor Green
    Write-Host "Ban co the mo IDM -> Tasks -> Import -> From text file de tai nhanh!" -ForegroundColor Yellow
    exit 0
}

# Xac dinh danh sach chi so can tai
$downloadIndices = @()
if ($EpisodeRange -eq "1" -or $EpisodeRange.ToLower() -eq "all") {
    for ($i = 0; $i -lt $videoUrls.Count; $i++) { $downloadIndices += $i }
}
elseif ($EpisodeRange -match "^\s*(\d+)\s*-\s*(\d+)\s*$") {
    $start = [Math]::Max(1, [int]$Matches[1])
    $end = [Math]::Min($videoUrls.Count, [int]$Matches[2])
    for ($i = $start; $i -le $end; $i++) { $downloadIndices += ($i - 1) }
}
else {
    $parts = $EpisodeRange -split "[,;\s]+"
    foreach ($p in $parts) {
        if ($p -match "^\d+$") {
            $num = [int]$p
            if ($num -ge 1 -and $num -le $videoUrls.Count) {
                $downloadIndices += ($num - 1)
            }
        }
    }
}

if ($downloadIndices.Count -eq 0) {
    Write-Host "[!] Khong co tap hop le nao duoc chon." -ForegroundColor Red
    exit 1
}

Write-Host "`n[*] Bat dau tai $($downloadIndices.Count) tap..." -ForegroundColor Green
$count = 0
$totalToDownload = $downloadIndices.Count

foreach ($idx in $downloadIndices) {
    $count++
    $epNum = $idx + 1
    $epFormatted = $epNum.ToString("D3")
    $fileName = "Tap_${epFormatted}.mp4"
    $destPath = Join-Path $showFolder $fileName
    $vUrl = $videoUrls[$idx]

    Write-Host "[$count/$totalToDownload] Dang tai Tap $epNum..." -ForegroundColor Cyan

    if (Test-Path $destPath) {
        $existingSize = (Get-Item $destPath).Length
        if ($existingSize -gt 102400) {
            Write-Host "    -> Tap $epNum da ton tai ($([Math]::Round($existingSize / 1MB, 2)) MB), bo qua." -ForegroundColor DarkGray
            continue
        }
    }

    # Tai ve qua curl voi tien trinh
    curl.exe -L -# -o $destPath $vUrl

    if (Test-Path $destPath) {
        $sizeMB = [Math]::Round((Get-Item $destPath).Length / 1MB, 2)
        Write-Host "    -> [OK] Hoan thanh: $fileName ($sizeMB MB)" -ForegroundColor Green
    } else {
        Write-Host "    -> [X] Loi khi tai Tap $epNum" -ForegroundColor Red
    }
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  TAT CA CAC TAP DA DUOC TAI VE THANH CONG!              " -ForegroundColor Yellow
Write-Host "  Thu muc: $showFolder" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
