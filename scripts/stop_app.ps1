# ==============================================================================
# CARPET STYLE & STORY MATCH - SHUTDOWN CONTROLLER
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas) - Tüm Hakları Saklıdır
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ports = @(8000, 3000)

foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($c in $conns) {
            $pId = $c.OwningProcess
            try {
                $p = Get-Process -Id $pId -ErrorAction SilentlyContinue
                if ($p) {
                    Write-Host ("   [X] Port $port (PID: $pId - $($p.ProcessName)) sonlandırılıyor...") -ForegroundColor Red
                    Stop-Process -Id $pId -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
    } else {
        Write-Host "   [i] Port $port zaten kapalı." -ForegroundColor DarkGray
    }
}
