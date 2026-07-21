param(
    [switch]$SkipExtract,
    [switch]$SkipPdf
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
