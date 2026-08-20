# ==============================================================================
# CARPET STYLE & STORY MATCH - DESKTOP SHORTCUT CREATOR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas) - Tüm Hakları Saklıdır
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$rootDir = Split-Path -Parent $PSScriptRoot
$ws = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$targetBat = Join-Path $rootDir "baslat.bat"
$shortcutPath = Join-Path $desktop "Carpet Style & Story Match.lnk"

$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetBat
$shortcut.WorkingDirectory = $rootDir
$shortcut.Description = "Carpet Style & Story Match Platform Başlatıcı"
$shortcut.Save()

Write-Host "[BAŞARILI] Masaüstü kısayolu oluşturuldu: $shortcutPath" -ForegroundColor Green
