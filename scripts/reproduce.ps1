param(
    [switch]$SkipExtract,
    [switch]$SkipPdf,
    [switch]$RefreshMap
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = if (Test-Path (Join-Path $repoRoot ".venv\Scripts\python.exe")) {
    Join-Path $repoRoot ".venv\Scripts\python.exe"
} else {
    "python"
}
Push-Location $repoRoot
try {
    $currentMap = Join-Path $repoRoot "dashboard-web\public\data\indonesia-adm1-current.geojson"
    if ($RefreshMap -or -not (Test-Path $currentMap)) {
        & $python "work\fetch_current_province_geojson.py"
    }
    if (-not $SkipExtract) {
        & $python "work\extract_bps_panel.py"
    }
    & $python "work\analyze_poverty_panel.py"
    & $python "work\prepare_site_data.py"
    if (-not $SkipPdf) {
        & $python "work\create_analysis_report.py"
    }
    Write-Host "Reproduksi selesai. Data website dan artefak analisis telah diperbarui."
}
finally {
    Pop-Location
}
