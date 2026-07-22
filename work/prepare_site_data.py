from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "data" / "processed" / "extracted_panel.json"
ANALYSIS = ROOT / "data" / "processed" / "poverty_analysis.json"
OUTPUT = ROOT / "dashboard-web" / "app" / "data" / "dashboard-data.json"
PUBLIC_OUTPUT = ROOT / "dashboard-web" / "public" / "downloads" / "dashboard-data.json"


with EXTRACTED.open("r", encoding="utf-8") as handle:
    extracted = json.load(handle)
with ANALYSIS.open("r", encoding="utf-8") as handle:
    analysis = json.load(handle)


panel_columns = [
    "province", "year", "island_group", "territory_class", "stable32_model_flag",
    "poor_population_thousand", "poverty_rate_pct", "tpt_aug_pct", "tpak_aug_pct",
    "hdi", "pdrb_pc_adhk2010_thousand_rp", "pdrb_growth_pct",
    "sanitation_access_pct", "drinking_water_access_pct", "food_share_pct",
]

panel = [
    {column: row.get(column) for column in panel_columns}
    for row in extracted["panel_rows"]
]

overall_benchmark = sorted(
    [row for row in analysis["model_benchmark"] if row["evaluation_scope"] == "overall_2022_2025"],
    key=lambda row: row["mae_rank"],
)

recommended_code = analysis["methodology"]["recommended_model_code"]
recommended_cv = [
    row for row in analysis["cv_predictions"] if row["model_code"] == recommended_code
]

national_trend = [
    {"year": 2015, "poverty_rate_pct": 11.22, "poor_population_thousand": 28592.83},
    {"year": 2016, "poverty_rate_pct": 10.86, "poor_population_thousand": 28005.39},
    {"year": 2017, "poverty_rate_pct": 10.64, "poor_population_thousand": 27771.22},
    {"year": 2018, "poverty_rate_pct": 9.82, "poor_population_thousand": 25949.80},
    {"year": 2019, "poverty_rate_pct": 9.41, "poor_population_thousand": 25144.72},
    {"year": 2020, "poverty_rate_pct": 9.78, "poor_population_thousand": 26424.02},
    {"year": 2021, "poverty_rate_pct": 10.14, "poor_population_thousand": 27542.77},
    {"year": 2022, "poverty_rate_pct": 9.54, "poor_population_thousand": 26161.16},
    {"year": 2023, "poverty_rate_pct": 9.36, "poor_population_thousand": 25898.55},
    {"year": 2024, "poverty_rate_pct": 9.03, "poor_population_thousand": 25219.20},
    {"year": 2025, "poverty_rate_pct": 8.47, "poor_population_thousand": 23854.56},
]

sources = [
    {
        "label": "Tabel Statistik BPS — Kemiskinan menurut provinsi",
        "url": "https://www.bps.go.id/id/statistics-table/3/UkVkWGJVZFNWakl6VWxKVFQwWjVWeTlSZDNabVFUMDkjMw==/jumlah-dan-persentase-penduduk-miskin-menurut-provinsi--2023.html?year=2025",
    },
    {
        "label": "Statistik Indonesia 2016",
        "url": "https://www.bps.go.id/id/publication/2016/06/29/7aa1e8f93b4148234a9b4bc3/statistik-indonesia-2016.html",
    },
    {
        "label": "Statistik Indonesia 2019",
        "url": "https://www.bps.go.id/id/publication/2019/07/04/daac1ba18cae1e90706ee58a/statistik-indonesia-2019.html",
    },
    {
        "label": "Statistik Indonesia 2021",
        "url": "https://www.bps.go.id/id/publication/2021/02/26/938316574c78772f27e9b477/statistik-indonesia-2021.html",
    },
    {
        "label": "Statistik Indonesia 2024",
        "url": "https://www.bps.go.id/id/publication/2024/02/28/c1bacde03256343b2bf769b0/statistik-indonesia-2024.html",
    },
    {
        "label": "Statistik Indonesia 2026",
        "url": "https://www.bps.go.id/id/publication/2026/02/27/a43f03f45543dc4e9942f44c/statistik-indonesia-2026.html",
    },
    {
        "label": "geoBoundaries Indonesia ADM1 (batas historis 34 provinsi, tahun referensi 2017)",
        "url": "https://www.geoboundaries.org/api/current/gbOpen/IDN/ADM1/",
    },
    {
        "label": "Badan Informasi Geospasial — Area Batas Wilayah Administrasi Provinsi (38 provinsi)",
        "url": "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_WILAYAH/MapServer/12",
    },
]

payload = {
    "meta": {
        "title": "Peta Kemiskinan Indonesia",
        "data_period": "2015–2025",
        "forecast_year": 2026,
        "last_updated": "22 Juli 2026",
        "model_universe": "32 provinsi dengan batas stabil sepanjang 2015–2025",
        "map_note": "Peta 2015–2023 memakai 34 batas historis; peta 2024–2025 memakai 38 batas provinsi terkini dari BIG.",
        "report_download": "/downloads/laporan_analisis_kemiskinan_indonesia_2015_2026.pdf",
        "data_download": "/downloads/dashboard-data.json",
        **analysis["methodology"],
    },
    "national_trend": national_trend,
    "panel": panel,
    "forecast": analysis["forecast_2026"],
    "benchmark": overall_benchmark,
    "cv_predictions": recommended_cv,
    "province_diagnostics": analysis["province_diagnostics"],
    "correlations": analysis["eda_correlations"],
    "coefficients": analysis["ridge_coefficients"],
    "trend_distribution": analysis["eda_trend"],
    "changes": analysis["eda_changes"],
    "convergence": analysis["convergence"],
    "forecast_summary": analysis["forecast_summary"],
    "spatial_analysis": analysis["spatial_analysis"],
    "universe_summary": analysis["universe_summary"],
    "key_findings": analysis["key_findings"],
    "data_legend": analysis["data_legend"],
    "sources": sources,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(OUTPUT, PUBLIC_OUTPUT)

print(json.dumps({
    "output": str(OUTPUT),
    "public_output": str(PUBLIC_OUTPUT),
    "bytes": OUTPUT.stat().st_size,
    "panel_rows": len(panel),
}))
