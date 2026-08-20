# ==============================================================================
# CARPET STYLE & STORY MATCH - STARTUP CONTROLLER
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas) - Tüm Hakları Saklıdır
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Carpet Style & Story Match - Başlatıcı"

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CARPET STYLE & STORY MATCH - TEK TIKLA BAŞLATICI" -ForegroundColor Cyan
Write-Host "  Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)" -ForegroundColor DarkGray
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Ön Koşul Kontrolleri
Write-Host "[*] Sistem gereksinimleri kontrol ediliyor..." -ForegroundColor Yellow

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[HATA] Python bulunamadı! Lütfen Python'ı yükleyip PATH'e ekleyin." -ForegroundColor Red
    Write-Host ""
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-Host "[HATA] Node.js / npm bulunamadı! Lütfen Node.js'i yükleyip PATH'e ekleyin." -ForegroundColor Red
    Write-Host ""
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

Write-Host "   [OK] Python ve Node.js/npm bulundu." -ForegroundColor Green

# 2. SQLite Veritabanı ve Şema Güncelliği
Write-Host "[*] Veritabanı şeması kontrol ediliyor..." -ForegroundColor Yellow
$pyScript = @"
import sqlite3, os
for p in ['apps/api/carpet_db.sqlite', 'carpet.db']:
    if os.path.exists(p):
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cols = [c[1] for c in cur.execute('PRAGMA table_info(upload_analyses)').fetchall()]
        if cols and 'error' not in cols:
            cur.execute('ALTER TABLE upload_analyses ADD COLUMN error TEXT')
            conn.commit()
"@
python -c $pyScript 2>$null
Write-Host "   [OK] Veritabanı hazır." -ForegroundColor Green
Write-Host ""

# 3. Port Kontrolleri ve Servis Başlatma
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  SERVİSLER BAŞLATILIYOR" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# Backend Başlat
$apiConn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($apiConn) {
    Write-Host "   [i] Port 8000 zaten aktif (Mevcut API oturumu kullanılıyor)." -ForegroundColor Yellow
} else {
    Write-Host "   [*] Backend API (FastAPI) başlatılıyor (Port 8000)..." -ForegroundColor White
    $apiPath = Join-Path $rootDir "apps\api"
    Start-Process cmd.exe -ArgumentList "/k", "title Carpet API (Port 8000) & cd /d `"$apiPath`" & color 0A & python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
}

# Frontend Başlat
$webConn = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($webConn) {
    Write-Host "   [i] Port 3000 zaten aktif (Mevcut Web oturumu kullanılıyor)." -ForegroundColor Yellow
} else {
    Write-Host "   [*] Frontend Web (Next.js) başlatılıyor (Port 3000)..." -ForegroundColor White
    $webPath = Join-Path $rootDir "apps\web"
    Start-Process cmd.exe -ArgumentList "/k", "title Carpet Web (Port 3000) & cd /d `"$webPath`" & color 0E & npm run dev"
}

# 4. Servislerin Hazır Olmasını Bekle
Write-Host ""
Write-Host "[*] Servislerin yanıt vermesi bekleniyor " -NoNewline -ForegroundColor Yellow

$apiReady = $false
$webReady = $false
$timeout = 40
$start = Get-Date

while ((-not ($apiReady -and $webReady)) -and (((Get-Date) - $start).TotalSeconds -lt $timeout)) {
    if (-not $apiReady) {
        try {
            $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($res.StatusCode -eq 200) { $apiReady = $true }
        } catch {}
    }
    if (-not $webReady) {
        try {
            $res = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($res.StatusCode -eq 200) { $webReady = $true }
        } catch {}
    }
    Write-Host "." -NoNewline -ForegroundColor Yellow
    Start-Sleep -Milliseconds 800
}
Write-Host ""

if ($apiReady -and $webReady) {
    Write-Host "   [BAŞARILI] Backend API ve Frontend Web tamamen aktif!" -ForegroundColor Green
} else {
    Write-Host "   [BİLGİ] Servisler arka planda yükleniyor..." -ForegroundColor Yellow
}

# 5. Tarayıcıyı Aç
Write-Host ""
Write-Host "[*] Tarayıcı açılıyor: http://localhost:3000" -ForegroundColor Cyan
Start-Process "http://localhost:3000"

# 6. Kontrol Menüsü
while ($true) {
    Clear-Host
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  CARPET STYLE & STORY MATCH - KONTROL PANELİ" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [●] Frontend Web : http://localhost:3000" -ForegroundColor Green
    Write-Host "  [●] Backend API  : http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "  [●] Swagger Docs : http://127.0.0.1:8000/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "----------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  HIZLI İŞLEMLER:" -ForegroundColor White
    Write-Host "  [1] Web Arayüzünü Tarayıcıda Aç (http://localhost:3000)"
    Write-Host "  [2] Swagger API Dokümantasyonunu Aç (http://127.0.0.1:8000/docs)"
    Write-Host "  [3] Servisleri Durdur ve Kapat"
    Write-Host "  [4] Çıkış (Pencereleri açık bırak)"
    Write-Host "----------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ""
    $secim = Read-Host "Lütfen bir seçenek girin (1-4)"

    switch ($secim) {
        "1" { Start-Process "http://localhost:3000" }
        "2" { Start-Process "http://127.0.0.1:8000/docs" }
        "3" {
            Write-Host ""
            Write-Host "[*] Servisler durduruluyor..." -ForegroundColor Red
            & "$rootDir\scripts\stop_app.ps1"
            Write-Host "[OK] Kapatıldı." -ForegroundColor Green
            Start-Sleep -Seconds 2
            exit 0
        }
        "4" { exit 0 }
    }
}
