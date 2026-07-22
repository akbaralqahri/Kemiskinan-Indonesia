from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from statistics import mean

from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "dashboard-web" / "app" / "data" / "dashboard-data.json"
ANALYSIS_PATH = ROOT / "data" / "processed" / "poverty_analysis.json"
GEO_PATH = ROOT / "dashboard-web" / "public" / "data" / "indonesia-adm1-current.geojson"
CHART_DIR = ROOT / "tmp" / "pdfs" / "charts"
OUTPUT_PATH = ROOT / "output" / "pdf" / "laporan_analisis_kemiskinan_indonesia_2015_2026.pdf"
PUBLIC_OUTPUT_PATH = ROOT / "dashboard-web" / "public" / "downloads" / OUTPUT_PATH.name

NAVY = "#102F4F"
INK = "#263238"
MUTED = "#66706B"
CREAM = "#F6F0E5"
PAPER = "#FFFCF7"
ORANGE = "#D85D32"
GREEN = "#789B8A"
LIGHT_GREEN = "#DDE8E2"
GOLD = "#C79A47"
GRID = "#D8D0C4"
RED = "#B84A3A"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


DATA = load_json(DATA_PATH)
ANALYSIS = load_json(ANALYSIS_PATH)
CHART_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def register_fonts():
    candidates = {
        "Arial": Path("C:/Windows/Fonts/arial.ttf"),
        "Arial-Bold": Path("C:/Windows/Fonts/arialbd.ttf"),
        "Georgia": Path("C:/Windows/Fonts/georgia.ttf"),
        "Georgia-Bold": Path("C:/Windows/Fonts/georgiab.ttf"),
    }
    for name, path in candidates.items():
        if path.exists():
            pdfmetrics.registerFont(TTFont(name, str(path)))


register_fonts()


def pil_font(size: int, bold: bool = False):
    path = Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf")
    return ImageFont.truetype(str(path), size=size)


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), str(text), font=font)
    return box[2] - box[0], box[3] - box[1]


def fit_text(draw, text, max_width, size=30, bold=False, minimum=18):
    while size > minimum:
        font = pil_font(size, bold)
        if text_size(draw, text, font)[0] <= max_width:
            return font
        size -= 1
    return pil_font(minimum, bold)


def blank_canvas(width=1800, height=950):
    image = PILImage.new("RGB", (width, height), PAPER)
    return image, ImageDraw.Draw(image)


def save_chart(image, filename):
    path = CHART_DIR / filename
    image.save(path, "PNG", optimize=True)
    return path


def draw_chart_title(draw, title, subtitle=None, width=1800):
    draw.text((80, 50), title, font=pil_font(40, True), fill=NAVY)
    if subtitle:
        draw.text((80, 106), subtitle, font=pil_font(24), fill=MUTED)
    draw.line((80, 150, width - 80, 150), fill=GRID, width=2)


def national_trend_chart():
    rows = DATA["national_trend"]
    image, draw = blank_canvas()
    draw_chart_title(draw, "Tren kemiskinan nasional", "Maret 2015-2025 | Persen penduduk miskin")
    x0, y0, x1, y1 = 130, 210, 1710, 790
    values = [r["poverty_rate_pct"] for r in rows]
    ymin, ymax = math.floor(min(values) - 0.5), math.ceil(max(values) + 0.5)
    for v in range(ymin, ymax + 1):
        y = y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)
        draw.line((x0, y, x1, y), fill=GRID, width=2)
        draw.text((55, y - 14), f"{v}%", font=pil_font(22), fill=MUTED)
    points = []
    for i, row in enumerate(rows):
        x = x0 + i / (len(rows) - 1) * (x1 - x0)
        y = y1 - (row["poverty_rate_pct"] - ymin) / (ymax - ymin) * (y1 - y0)
        points.append((x, y))
        draw.text((x - 28, y1 + 25), str(row["year"]), font=pil_font(19), fill=MUTED)
    draw.line(points, fill=ORANGE, width=8, joint="curve")
    for x, y in points:
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=ORANGE, outline=PAPER, width=3)
    for i in [0, len(rows) - 1]:
        x, y = points[i]
        label = f"{values[i]:.2f}%"
        draw.rounded_rectangle((x - 52, y - 62, x + 52, y - 20), radius=10, fill=NAVY)
        draw.text((x - 43, y - 55), label, font=pil_font(23, True), fill="white")
    delta = values[-1] - values[0]
    draw.rounded_rectangle((1210, 175, 1710, 260), radius=18, fill=LIGHT_GREEN)
    draw.text((1240, 190), f"Perubahan: {delta:.2f} poin persen", font=pil_font(27, True), fill=NAVY)
    return save_chart(image, "01_tren_nasional.png")


ISO_TO_PROVINCE = {
    "ID-BA": "Bali", "ID-NB": "Nusa Tenggara Barat", "ID-BT": "Banten",
    "ID-JT": "Jawa Tengah", "ID-JB": "Jawa Barat", "ID-KT": "Kalimantan Tengah",
    "ID-KS": "Kalimantan Selatan", "ID-KB": "Kalimantan Barat", "ID-ST": "Sulawesi Tengah",
    "ID-GO": "Gorontalo", "ID-SA": "Sulawesi Utara", "ID-SN": "Sulawesi Selatan",
    "ID-SG": "Sulawesi Tenggara", "ID-SR": "Sulawesi Barat", "ID-AC": "Aceh",
    "ID-BE": "Bengkulu", "ID-JA": "Jambi", "ID-LA": "Lampung", "ID-RI": "Riau",
    "ID-SB": "Sumatera Barat", "ID-SS": "Sumatera Selatan", "ID-SU": "Sumatera Utara",
    "ID-NT": "Nusa Tenggara Timur", "ID-MA": "Maluku", "ID-MU": "Maluku Utara",
    "ID-JI": "Jawa Timur", "ID-BB": "Kepulauan Bangka Belitung", "ID-KR": "Kepulauan Riau",
    "ID-PA": "Papua", "ID-PB": "Papua Barat", "ID-KI": "Kalimantan Timur",
    "ID-KU": "Kalimantan Utara", "ID-YO": "DI Yogyakarta", "ID-JK": "DKI Jakarta",
}


def poverty_color(value):
    stops = [4, 7, 10, 13, 16, 19]
    palette = ["#DDE8E2", "#C5D7CD", "#9FB9AA", "#D7AA83", "#CA7957", "#B84A3A"]
    for stop, color in zip(stops, palette):
        if value <= stop:
            return color
    return palette[-1]


def flatten_positions(geometry):
    coords = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        return [coords]
    return coords


def spatial_map_chart():
    geo = load_json(GEO_PATH)
    values = {r["province"]: r["poverty_rate_pct"] for r in DATA["panel"] if r["year"] == 2025}
    image, draw = blank_canvas(width=1800, height=1050)
    draw_chart_title(draw, "Sebaran spasial kemiskinan 2025", "Persentase penduduk miskin menurut 38 provinsi terkini")
    map_box = (80, 190, 1720, 820)
    lon_min, lon_max, lat_min, lat_max = 94.5, 141.5, -11.5, 6.5
    mx0, my0, mx1, my1 = map_box
    scale_x = (mx1 - mx0) / (lon_max - lon_min)
    scale_y = (my1 - my0) / (lat_max - lat_min)
    scale = min(scale_x, scale_y)
    used_w = (lon_max - lon_min) * scale
    used_h = (lat_max - lat_min) * scale
    ox = mx0 + ((mx1 - mx0) - used_w) / 2
    oy = my0 + ((my1 - my0) - used_h) / 2

    def project(pair):
        lon, lat = pair[:2]
        return (ox + (lon - lon_min) * scale, oy + (lat_max - lat) * scale)

    for feature in geo["features"]:
        province = feature["properties"].get("province", feature["properties"].get("shapeName"))
        value = values.get(province)
        fill = poverty_color(value) if value is not None else "#E8E3D9"
        for polygon in flatten_positions(feature["geometry"]):
            if not polygon:
                continue
            outer = [project(p) for p in polygon[0]]
            if len(outer) >= 3:
                draw.polygon(outer, fill=fill, outline=NAVY)
                draw.line(outer + [outer[0]], fill=NAVY, width=2)
            for hole in polygon[1:]:
                points = [project(p) for p in hole]
                if len(points) >= 3:
                    draw.polygon(points, fill=PAPER)
    legend_x, legend_y = 440, 875
    legend_items = list(zip(["<=4", "4-7", "7-10", "10-13", "13-16", ">16"], ["#DDE8E2", "#C5D7CD", "#9FB9AA", "#D7AA83", "#CA7957", "#B84A3A"]))
    for i, (label, color) in enumerate(legend_items):
        x = 305 + i * 185
        draw.rectangle((x, legend_y, x + 55, legend_y + 30), fill=color, outline=GRID)
        draw.text((x + 65, legend_y + 1), label, font=pil_font(21), fill=INK)
    draw.text((80, 960), "Sumber geometri: BIG, layer Area Batas Wilayah Administrasi Provinsi; disederhanakan untuk visualisasi.", font=pil_font(23), fill=MUTED)
    return save_chart(image, "02_peta_2025.png")


def disparity_chart():
    rows = sorted(
        [row for row in DATA["panel"] if row["year"] == 2025 and row["poverty_rate_pct"] is not None],
        key=lambda row: row["poverty_rate_pct"],
        reverse=True,
    )
    selected = rows[:5] + list(reversed(rows[-5:]))
    image, draw = blank_canvas(width=1800, height=1050)
    draw_chart_title(draw, "Provinsi dengan tingkat tertinggi dan terendah", "Maret 2025 | persen")
    x0, x1 = 590, 1650
    y = 205
    max_v = max(r["poverty_rate_pct"] for r in selected)
    for idx, row in enumerate(selected):
        if idx == 5:
            y += 35
            draw.line((80, y - 15, 1720, y - 15), fill=GRID, width=2)
        province = row["province"]
        value = row["poverty_rate_pct"]
        font = fit_text(draw, province, 450, 28, True)
        draw.text((80, y), province, font=font, fill=INK)
        bar_w = value / max_v * (x1 - x0)
        color = ORANGE if idx < 5 else GREEN
        draw.rounded_rectangle((x0, y + 1, x0 + bar_w, y + 35), radius=12, fill=color)
        draw.text((x0 + bar_w + 18, y + 2), f"{value:.2f}%", font=pil_font(25, True), fill=NAVY)
        y += 72
    return save_chart(image, "03_kesenjangan_2025.png")


def correlation_chart():
    rows = ANALYSIS["eda_correlations"]
    image, draw = blank_canvas(width=1800, height=1180)
    draw_chart_title(draw, "Dua cara membaca korelasi", "Pooled membandingkan provinsi; within menilai perubahan di provinsi yang sama")
    x0, x1 = 730, 1690
    y0, row_h = 220, 84
    for tick in [-1, -0.5, 0, 0.5, 1]:
        x = x0 + (tick + 1) / 2 * (x1 - x0)
        draw.line((x, y0 - 25, x, y0 + row_h * len(rows) - 25), fill=GRID if tick else NAVY, width=3 if tick == 0 else 1)
        draw.text((x - 18, 175), f"{tick:g}", font=pil_font(20), fill=MUTED)
    for i, row in enumerate(rows):
        y = y0 + i * row_h
        friendly_names = {
            "lag_pdrb_pc_growth_pct": "Pertumbuhan PDRB/kapita (t-1)",
            "lag_food_share_pct": "Pangsa konsumsi pangan (t-1)",
        }
        label = friendly_names.get(row["feature_code"], row["feature_name"].replace(" t-1", " (t-1)"))
        font = fit_text(draw, label, 600, 25, False)
        draw.text((80, y - 14), label, font=font, fill=INK)
        pooled = row["pooled_pearson_r"]
        within = row["within_province_r"]
        xp = x0 + (pooled + 1) / 2 * (x1 - x0)
        xw = x0 + (within + 1) / 2 * (x1 - x0)
        draw.line((xp, y, xw, y), fill="#AFA79B", width=6)
        draw.ellipse((xp - 10, y - 10, xp + 10, y + 10), fill=ORANGE)
        draw.rectangle((xw - 10, y - 10, xw + 10, y + 10), fill=GREEN)
    draw.ellipse((80, 1080, 100, 1100), fill=ORANGE)
    draw.text((115, 1075), "Pooled", font=pil_font(22, True), fill=INK)
    draw.rectangle((275, 1080, 295, 1100), fill=GREEN)
    draw.text((310, 1075), "Within province", font=pil_font(22, True), fill=INK)
    draw.text((850, 1075), "Perbedaan tanda adalah sinyal heterogenitas, bukan kontradiksi data.", font=pil_font(22), fill=MUTED)
    return save_chart(image, "04_korelasi.png")


def coefficient_chart():
    rows = sorted(ANALYSIS["ridge_coefficients"], key=lambda r: r["absolute_coefficient"], reverse=True)
    image, draw = blank_canvas(width=1800, height=1130)
    draw_chart_title(draw, "Bobot prediktif model Ridge", "Koefisien terstandar | bukan ukuran dampak kausal")
    xzero, maxw = 1040, 610
    max_abs = max(r["absolute_coefficient"] for r in rows)
    y = 220
    for row in rows:
        value = row["standardized_coefficient"]
        label = row["feature_name"]
        font = fit_text(draw, label, 660, 25)
        draw.text((80, y), label, font=font, fill=INK)
        width = abs(value) / max_abs * maxw
        if value >= 0:
            draw.rounded_rectangle((xzero, y, xzero + width, y + 34), radius=10, fill=ORANGE)
            tx = xzero + width + 16
        else:
            draw.rounded_rectangle((xzero - width, y, xzero, y + 34), radius=10, fill=GREEN)
            tx = xzero - width - 92
        draw.text((tx, y + 1), f"{value:+.2f}", font=pil_font(22, True), fill=NAVY)
        y += 78
    draw.line((xzero, 185, xzero, 1010), fill=NAVY, width=3)
    return save_chart(image, "05_koefisien.png")


def benchmark_chart():
    rows = sorted(DATA["benchmark"], key=lambda r: r["mae"])
    image, draw = blank_canvas(width=1800, height=900)
    draw_chart_title(draw, "Akurasi model pada data yang belum dilihat", "Walk-forward validation 2022-2025 | lebih kecil lebih baik")
    x0, x1 = 760, 1650
    max_v = max(r["mae"] for r in rows) * 1.1
    y = 225
    for i, row in enumerate(rows):
        name = row["model_name"].replace(" + ", " + ")
        font = fit_text(draw, name, 620, 27, i == 0)
        draw.text((80, y), name, font=font, fill=NAVY if i == 0 else INK)
        bar_w = row["mae"] / max_v * (x1 - x0)
        draw.rounded_rectangle((x0, y, x0 + bar_w, y + 42), radius=12, fill=ORANGE if i == 0 else "#B7C8BF")
        draw.text((x0 + bar_w + 16, y + 4), f"MAE {row['mae']:.3f}", font=pil_font(24, True), fill=NAVY)
        y += 105
    best = rows[0]
    draw.rounded_rectangle((80, 770, 1720, 845), radius=16, fill=LIGHT_GREEN)
    draw.text((110, 792), f"Model terpilih: {best['model_name']} | RMSE {best['rmse']:.3f} | MAPE {best['mape_pct']:.2f}% | R2 {best['r2']:.3f}", font=pil_font(27, True), fill=NAVY)
    return save_chart(image, "06_benchmark.png")


def cv_scatter_chart():
    rows = DATA["cv_predictions"]
    image, draw = blank_canvas(width=1300, height=1050)
    draw_chart_title(draw, "Aktual vs prediksi", "128 observasi validasi 2022-2025", width=1300)
    x0, y0, x1, y1 = 150, 230, 1190, 900
    max_v = math.ceil(max(max(r["actual_poverty_rate_pct"], r["predicted_poverty_rate_pct"]) for r in rows))
    min_v = math.floor(min(min(r["actual_poverty_rate_pct"], r["predicted_poverty_rate_pct"]) for r in rows))
    for tick in range(min_v, max_v + 1, 3):
        x = x0 + (tick - min_v) / (max_v - min_v) * (x1 - x0)
        y = y1 - (tick - min_v) / (max_v - min_v) * (y1 - y0)
        draw.line((x, y0, x, y1), fill=GRID, width=1)
        draw.line((x0, y, x1, y), fill=GRID, width=1)
        draw.text((x - 12, y1 + 18), str(tick), font=pil_font(19), fill=MUTED)
        draw.text((95, y - 12), str(tick), font=pil_font(19), fill=MUTED)
    draw.line((x0, y1, x1, y0), fill=NAVY, width=4)
    for row in rows:
        x = x0 + (row["actual_poverty_rate_pct"] - min_v) / (max_v - min_v) * (x1 - x0)
        y = y1 - (row["predicted_poverty_rate_pct"] - min_v) / (max_v - min_v) * (y1 - y0)
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=ORANGE, outline=PAPER)
    draw.text((500, 970), "Aktual (%)", font=pil_font(24, True), fill=INK)
    draw.text((25, 535), "Prediksi", font=pil_font(22, True), fill=INK)
    return save_chart(image, "07_cv_scatter.png")


def forecast_chart():
    rows = sorted(DATA["forecast"], key=lambda r: r["forecast_poverty_rate_pct"], reverse=True)[:10]
    image, draw = blank_canvas(width=1800, height=1150)
    draw_chart_title(draw, "Proyeksi indikatif 2026", "10 nilai prediksi tertinggi | titik biru 2025, titik oranye proyeksi, garis = interval 80%")
    x0, x1 = 670, 1680
    vmax = 20
    for tick in range(0, 21, 5):
        x = x0 + tick / vmax * (x1 - x0)
        draw.line((x, 200, x, 1020), fill=GRID, width=2)
        draw.text((x - 15, 1040), f"{tick}%", font=pil_font(21), fill=MUTED)
    y = 225
    for row in rows:
        province = row["province"]
        font = fit_text(draw, province, 520, 26, True)
        draw.text((80, y - 13), province, font=font, fill=INK)
        xa = x0 + row["actual_2025_pct"] / vmax * (x1 - x0)
        xf = x0 + row["forecast_poverty_rate_pct"] / vmax * (x1 - x0)
        xl = x0 + row["lower_80_pct"] / vmax * (x1 - x0)
        xu = x0 + row["upper_80_pct"] / vmax * (x1 - x0)
        draw.line((xl, y, xu, y), fill=GREEN, width=10)
        draw.ellipse((xa - 10, y - 10, xa + 10, y + 10), fill=NAVY)
        draw.ellipse((xf - 12, y - 12, xf + 12, y + 12), fill=ORANGE, outline=PAPER, width=2)
        draw.text((xf + 18, y - 12), f"{row['forecast_poverty_rate_pct']:.2f}%", font=pil_font(21, True), fill=ORANGE)
        y += 80
    draw.rounded_rectangle((80, 1080, 1720, 1135), radius=12, fill="#F4E5DA")
    draw.text((105, 1094), "Peringatan: proyeksi eksperimental, bukan angka resmi BPS dan bukan target kebijakan.", font=pil_font(24, True), fill=RED)
    return save_chart(image, "08_forecast.png")


def convergence_chart():
    rows = sorted(DATA["trend_distribution"], key=lambda row: row["year"])
    image, draw = blank_canvas(width=1800, height=900)
    draw_chart_title(draw, "Konvergensi antarprovinsi", "Standar deviasi P0 pada 32 provinsi dengan batas stabil")
    x0, y0, x1, y1 = 150, 220, 1690, 730
    values = [row["std_dev_pct"] for row in rows]
    ymin, ymax = math.floor(min(values) * 10) / 10 - 0.2, math.ceil(max(values) * 10) / 10 + 0.2
    for idx in range(5):
        value = ymin + idx / 4 * (ymax - ymin)
        y = y1 - (value - ymin) / (ymax - ymin) * (y1 - y0)
        draw.line((x0, y, x1, y), fill=GRID, width=2)
        draw.text((55, y - 13), f"{value:.1f}", font=pil_font(21), fill=MUTED)
    points = []
    for idx, row in enumerate(rows):
        x = x0 + idx / (len(rows) - 1) * (x1 - x0)
        y = y1 - (row["std_dev_pct"] - ymin) / (ymax - ymin) * (y1 - y0)
        points.append((x, y))
        draw.text((x - 26, y1 + 26), str(row["year"]), font=pil_font(18), fill=MUTED)
    draw.line(points, fill=GREEN, width=8, joint="curve")
    for x, y in points:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=GREEN, outline=PAPER, width=2)
    for index in [0, len(points) - 1]:
        x, y = points[index]
        label = f"{values[index]:.2f} pp"
        draw.rounded_rectangle((x - 58, y - 58, x + 72, y - 18), radius=9, fill=NAVY)
        draw.text((x - 46, y - 52), label, font=pil_font(21, True), fill="white")
    reduction = 1 - values[-1] / values[0]
    draw.rounded_rectangle((1170, 170, 1690, 245), radius=16, fill=LIGHT_GREEN)
    draw.text((1200, 190), f"Dispersi menyempit {reduction * 100:.1f}%", font=pil_font(27, True), fill=NAVY)
    return save_chart(image, "09_konvergensi.png")


def province_diagnostic_chart():
    rows = sorted(DATA["province_diagnostics"], key=lambda row: row["mae_pp"], reverse=True)[:12]
    image, draw = blank_canvas(width=1800, height=1120)
    draw_chart_title(draw, "Provinsi dengan error validasi terbesar", "MAE model rekomendasi pada empat tahun uji, 2022-2025")
    x0, x1 = 650, 1650
    max_value = max(row["mae_pp"] for row in rows) * 1.15
    y = 210
    for row in rows:
        font = fit_text(draw, row["province"], 500, 25, True)
        draw.text((80, y), row["province"], font=font, fill=INK)
        width = row["mae_pp"] / max_value * (x1 - x0)
        draw.rounded_rectangle((x0, y, x0 + width, y + 32), radius=10, fill=ORANGE)
        draw.text((x0 + width + 15, y), f"{row['mae_pp']:.3f} pp", font=pil_font(22, True), fill=NAVY)
        draw.text((1390, y + 38), f"maks. {row['maximum_absolute_error_pp']:.2f} ({row['worst_test_year']})", font=pil_font(17), fill=MUTED)
        y += 71
    draw.rounded_rectangle((80, 1060, 1720, 1110), radius=10, fill="#F4E5DA")
    draw.text((105, 1072), "Error tinggi menandai wilayah yang membutuhkan interval, pemeriksaan lokal, dan pemantauan lebih ketat.", font=pil_font(22, True), fill=RED)
    return save_chart(image, "10_diagnostik_provinsi.png")


def risk_matrix_chart():
    rows = DATA["forecast"]
    image, draw = blank_canvas(width=1800, height=1000)
    draw_chart_title(draw, "Matriks risiko proyeksi 2026", "Sumbu X = level proyeksi | sumbu Y = perubahan dari 2025 | ukuran titik = selisih antarmodel")
    x0, y0, x1, y1 = 180, 210, 1690, 820
    xmin = math.floor(min(row["forecast_poverty_rate_pct"] for row in rows) - 1)
    xmax = math.ceil(max(row["forecast_poverty_rate_pct"] for row in rows) + 1)
    ymin = min(-0.8, math.floor(min(row["change_vs_2025_pp"] for row in rows) * 10) / 10 - 0.1)
    ymax = 0.3

    def x(value):
        return x0 + (value - xmin) / (xmax - xmin) * (x1 - x0)

    def y(value):
        return y1 - (value - ymin) / (ymax - ymin) * (y1 - y0)

    draw.rectangle((x(12), y0, x1, y1), fill="#F2D9CF")
    draw.rectangle((x(10), y0, x(12), y1), fill="#F3E5C9")
    for tick in range(xmin, xmax + 1, 2):
        draw.line((x(tick), y0, x(tick), y1), fill=GRID, width=1)
        draw.text((x(tick) - 14, y1 + 20), f"{tick}%", font=pil_font(19), fill=MUTED)
    for tick in [ymin, -0.5, -0.25, 0.0, ymax]:
        if ymin <= tick <= ymax:
            draw.line((x0, y(tick), x1, y(tick)), fill=NAVY if tick == 0 else GRID, width=3 if tick == 0 else 1)
            draw.text((90, y(tick) - 12), f"{tick:+.2f}", font=pil_font(19), fill=MUTED)
    palette = {"Lebih rendah": GREEN, "Menengah": GOLD, "Tinggi": "#C77C55", "Sangat tinggi": RED}
    labelled = {"Nusa Tenggara Timur", "Maluku", "Aceh", "Bali", "DI Yogyakarta"}
    for row in rows:
        px, py = x(row["forecast_poverty_rate_pct"]), y(row["change_vs_2025_pp"])
        radius = 8 + min(9, row["model_spread_pp"] * 4)
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=palette[row["risk_tier"]], outline=PAPER, width=2)
        if row["province"] in labelled:
            draw.text((px + 12, py - 12), row["province"], font=pil_font(17, True), fill=NAVY)
    legend_y = 910
    for idx, (label, color) in enumerate(palette.items()):
        lx = 320 + idx * 300
        draw.ellipse((lx, legend_y, lx + 22, legend_y + 22), fill=color)
        draw.text((lx + 34, legend_y - 1), label, font=pil_font(19), fill=INK)
    return save_chart(image, "11_matriks_risiko.png")


CHARTS = {
    "trend": national_trend_chart(),
    "map": spatial_map_chart(),
    "disparity": disparity_chart(),
    "correlation": correlation_chart(),
    "coefficient": coefficient_chart(),
    "benchmark": benchmark_chart(),
    "scatter": cv_scatter_chart(),
    "forecast": forecast_chart(),
    "convergence": convergence_chart(),
    "diagnostics": province_diagnostic_chart(),
    "risk": risk_matrix_chart(),
}


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverKicker", fontName="Arial-Bold", fontSize=9, leading=12, textColor=HexColor(ORANGE), spaceAfter=8, tracking=2))
styles.add(ParagraphStyle(name="CoverTitle", fontName="Georgia-Bold", fontSize=30, leading=35, textColor=HexColor(NAVY), spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", fontName="Arial", fontSize=12, leading=18, textColor=HexColor(MUTED), spaceAfter=16))
styles.add(ParagraphStyle(name="Kicker", fontName="Arial-Bold", fontSize=8, leading=11, textColor=HexColor(ORANGE), spaceAfter=5, tracking=1.5))
styles.add(ParagraphStyle(name="ReportTitle", fontName="Georgia-Bold", fontSize=21, leading=26, textColor=HexColor(NAVY), spaceAfter=8))
styles.add(ParagraphStyle(name="Lead", fontName="Arial", fontSize=10.2, leading=15, textColor=HexColor(MUTED), spaceAfter=12))
styles.add(ParagraphStyle(name="BodyID", fontName="Arial", fontSize=9.2, leading=14, textColor=HexColor(INK), spaceAfter=8))
styles.add(ParagraphStyle(name="BodySmall", fontName="Arial", fontSize=8, leading=11.5, textColor=HexColor(INK), spaceAfter=5))
styles.add(ParagraphStyle(name="H2ID", fontName="Arial-Bold", fontSize=11, leading=15, textColor=HexColor(NAVY), spaceBefore=7, spaceAfter=5))
styles.add(ParagraphStyle(name="Metric", fontName="Georgia-Bold", fontSize=20, leading=23, textColor=HexColor(NAVY), alignment=TA_CENTER))
styles.add(ParagraphStyle(name="MetricLabel", fontName="Arial", fontSize=7.5, leading=10, textColor=HexColor(MUTED), alignment=TA_CENTER))
styles.add(ParagraphStyle(name="Quote", fontName="Georgia", fontSize=12, leading=18, textColor=HexColor(NAVY), leftIndent=12, rightIndent=12, spaceBefore=8, spaceAfter=8))
styles.add(ParagraphStyle(name="Source", fontName="Arial", fontSize=7.2, leading=10.2, textColor=HexColor(MUTED), spaceAfter=4))


def P(text, style="BodyID"):
    return Paragraph(text, styles[style])


def page_title(kicker, title, lead):
    return [P(kicker.upper(), "Kicker"), P(title, "ReportTitle"), P(lead, "Lead"), HRFlowable(width="100%", thickness=0.7, color=HexColor(GRID), spaceAfter=10)]


def image_flow(path, width_mm):
    with PILImage.open(path) as im:
        ratio = im.height / im.width
    width = width_mm * mm
    return Image(str(path), width=width, height=width * ratio)


def metric_card(value, label, bgcolor=LIGHT_GREEN):
    table = Table([[P(value, "Metric")], [P(label, "MetricLabel")]], colWidths=[51 * mm], rowHeights=[14 * mm, 13 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(bgcolor)),
        ("BOX", (0, 0), (-1, -1), 0.6, HexColor(GRID)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def data_table(data, widths, header=True, font_size=7.4):
    wrapped = []
    for r_idx, row in enumerate(data):
        style = ParagraphStyle(
            name=f"T{r_idx}", fontName="Arial-Bold" if header and r_idx == 0 else "Arial",
            fontSize=font_size, leading=font_size + 3, textColor=colors.white if header and r_idx == 0 else HexColor(INK),
        )
        wrapped.append([Paragraph(str(cell), style) for cell in row])
    table = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, HexColor(GRID)),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), HexColor(NAVY)))
        if len(data) > 1:
            commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor(PAPER), HexColor("#F2EEE6")]))
    table.setStyle(TableStyle(commands))
    return table


def on_page(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(HexColor(GRID))
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 282 * mm, 192 * mm, 282 * mm)
        canvas.setFont("Arial", 7.5)
        canvas.setFillColor(HexColor(MUTED))
        canvas.drawString(18 * mm, 10 * mm, "Analisis Kemiskinan Indonesia 2015-2026")
        canvas.drawRightString(192 * mm, 10 * mm, str(doc.page))
    canvas.restoreState()


trend = DATA["national_trend"]
rate_2015, rate_2025 = trend[0]["poverty_rate_pct"], trend[-1]["poverty_rate_pct"]
poor_2015, poor_2025 = trend[0]["poor_population_thousand"], trend[-1]["poor_population_thousand"]
ranked = sorted(
    [row for row in DATA["panel"] if row["year"] == 2025 and row["poverty_rate_pct"] is not None],
    key=lambda row: row["poverty_rate_pct"],
    reverse=True,
)
changes = sorted(ANALYSIS["eda_changes"], key=lambda r: r["change_2015_2025_pp"])
benchmark = sorted(DATA["benchmark"], key=lambda r: r["mae"])
best = benchmark[0]
naive = next(row for row in benchmark if row["model_code"] == "naive_lag1")
forecast = sorted(DATA["forecast"], key=lambda r: r["forecast_poverty_rate_pct"], reverse=True)
avg_forecast = mean(r["forecast_poverty_rate_pct"] for r in forecast)
avg_actual = mean(r["actual_2025_pct"] for r in forecast)
moran = DATA["spatial_analysis"]
convergence = DATA["convergence"]


story = []

# Cover
story += [Spacer(1, 18 * mm), P("LAPORAN ANALISIS", "CoverKicker"), P("Kemiskinan Indonesia<br/>2015-2026", "CoverTitle")]
story += [P("Tren, kesenjangan spasial, faktor terkait, evaluasi model, dan proyeksi provinsi", "CoverSub")]
story += [Spacer(1, 6 * mm), image_flow(CHARTS["map"], 174), Spacer(1, 5 * mm)]
cover_band = Table([[P("DATA OBSERVASI", "MetricLabel"), P("CAKUPAN MODEL", "MetricLabel"), P("STATUS PROYEKSI", "MetricLabel")],
                    [P("2015-2025", "Metric"), P("32 provinsi", "Metric"), P("Eksperimental", "Metric")]], colWidths=[58 * mm] * 3)
cover_band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor(LIGHT_GREEN)), ("BOX", (0, 0), (-1, -1), 0.7, HexColor(GRID)), ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor(GRID)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
story += [cover_band, Spacer(1, 8 * mm), P("Disusun dari tabel BPS dan panel indikator provinsi. Proyeksi 2026 bukan angka resmi BPS.", "Source"), PageBreak()]

# Executive summary
story += page_title("01 / Ringkasan", "Temuan utama", "Kemiskinan menurun kuat secara nasional, tetapi jarak antarprovinsi masih lebar dan persistensi tahun sebelumnya menjadi sinyal prediktif terbesar.")
story += [Table([[metric_card(f"{rate_2025:.2f}%", "Kemiskinan nasional 2025"), metric_card(f"{rate_2025-rate_2015:.2f} pp", "Perubahan sejak 2015", "#F4E5DA"), metric_card(f"{best['mae']:.3f} pp", "MAE validasi model")]], colWidths=[58 * mm] * 3, hAlign="LEFT"), Spacer(1, 5 * mm)]
story += [P("Inti pembacaan", "H2ID")]
story += [P(f"1. Tingkat kemiskinan nasional turun dari <b>{rate_2015:.2f}%</b> pada Maret 2015 menjadi <b>{rate_2025:.2f}%</b> pada Maret 2025. Jumlah penduduk miskin turun dari sekitar <b>{poor_2015/1000:.2f} juta</b> menjadi <b>{poor_2025/1000:.2f} juta</b> orang."),
          P(f"2. Pada peta 38 provinsi tahun 2025, tingkat tertinggi terdapat di <b>{ranked[0]['province']} ({ranked[0]['poverty_rate_pct']:.2f}%)</b>; tingkat terendah di <b>{ranked[-1]['province']} ({ranked[-1]['poverty_rate_pct']:.2f}%)</b>. Perbedaan ini menunjukkan masalah spasial yang tidak tertangkap oleh angka nasional saja."),
          P("3. IPM, PDRB per kapita, sanitasi, dan air minum cenderung berasosiasi negatif dengan kemiskinan. Namun tanda korelasi dapat berubah ketika membandingkan provinsi dan ketika mengikuti provinsi yang sama dari waktu ke waktu. Ini alasan dashboard menampilkan dua jenis korelasi."),
          P(f"4. Model terbaik adalah <b>{best['model_name']}</b>. Pada walk-forward validation 2022-2025, MAE sebesar <b>{best['mae']:.3f} poin persen</b>, MAPE <b>{best['mape_pct']:.2f}%</b>, dan R2 <b>{best['r2']:.3f}</b>."),
          P(f"5. Rata-rata sederhana proyeksi 2026 untuk 32 provinsi adalah <b>{avg_forecast:.2f}%</b>, dibanding <b>{avg_actual:.2f}%</b> pada 2025. Proyeksi ini harus dibaca sebagai skenario dasar, bukan target atau angka resmi.")]
story += [Spacer(1, 3 * mm), Table([[P("Kesimpulan kerja", "H2ID")], [P("Prioritas analisis sebaiknya bergeser dari pertanyaan 'apakah kemiskinan turun?' ke 'provinsi mana yang tertinggal, faktor apa yang bergerak bersama kemiskinan di wilayah tersebut, dan seberapa pasti proyeksinya?'")]], colWidths=[174 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor(CREAM)), ("BOX", (0, 0), (-1, -1), 0.7, HexColor(GOLD)), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)])), PageBreak()]

# Problem and research questions
story += page_title("02 / Masalah", "Masalah yang hendak dijawab", "Angka nasional memberi arah umum, tetapi belum menunjukkan ketimpangan wilayah, mekanisme yang berkaitan, maupun tingkat ketidakpastian proyeksi.")
problem_rows = [
    ["Masalah", "Mengapa penting", "Jawaban yang dicari"],
    ["Rata-rata menyembunyikan variasi", "Kemajuan nasional dapat berjalan bersama kantong kemiskinan tinggi.", "Tren, peringkat, dan peta 38 provinsi."],
    ["Batas wilayah berubah", "Pemekaran Papua dapat menciptakan perbandingan waktu yang tidak setara.", "Pisahkan semesta 38, 34, dan 32 provinsi."],
    ["Korelasi agregat menyesatkan", "Pola antarprovinsi dapat berbeda dari perubahan di provinsi yang sama.", "Bandingkan korelasi pooled dan within."],
    ["Prediksi tanpa benchmark", "Model kompleks belum tentu lebih baik daripada nilai tahun lalu.", "Uji rolling-origin terhadap naive dan tren."],
]
story += [data_table(problem_rows, [44 * mm, 63 * mm, 67 * mm], font_size=7.5), Spacer(1, 5 * mm)]
story += [P("Pertanyaan penelitian", "H2ID"),
          P("1. Bagaimana tingkat dan jumlah penduduk miskin berubah pada 2015-2025, termasuk ketika pandemi?"),
          P("2. Provinsi mana yang tertinggal, apakah kesenjangan menyempit, dan apakah nilai tinggi/rendah membentuk pola spasial?"),
          P("3. Faktor sosial-ekonomi apa yang konsisten bergerak bersama kemiskinan setelah perbedaan tetap antarprovinsi dikurangi?"),
          P("4. Apakah model multivariat mengungguli baseline sederhana, dan provinsi mana yang paling sulit diprediksi?"),
          P("5. Apa skenario dasar 2026, wilayah prioritas pemantauan, dan batas penggunaannya?"),
          Spacer(1, 4 * mm),
          Table([[P("Tujuan keluaran", "H2ID")], [P("Menghasilkan dashboard web yang dapat dieksplorasi, data siap unduh, model yang divalidasi secara temporal, dan laporan analisis yang membedakan temuan, kesimpulan, rekomendasi, serta keterbatasan.")]], colWidths=[174 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor(LIGHT_GREEN)), ("BOX", (0, 0), (-1, -1), 0.7, HexColor(GREEN)), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)])), PageBreak()]

# Data
story += page_title("03 / Data", "Apa yang dianalisis?", "Dataset menggabungkan kemiskinan Maret dengan indikator sosial-ekonomi yang tersedia sebelum tahun target, sehingga alur prediksi tidak memakai informasi dari masa depan.")
data_rows = [
    ["Komponen", "Periode / unit", "Peran dalam analisis"],
    ["Kemiskinan", "2015-2025, provinsi", "Target: persentase penduduk miskin; jumlah penduduk miskin untuk konteks."],
    ["Pasar kerja", "TPT dan TPAK Agustus t-1", "Mewakili tekanan dan partisipasi pasar kerja sebelum target Maret tahun t."],
    ["Pembangunan manusia", "IPM t-1", "Ringkasan kesehatan, pendidikan, dan standar hidup."],
    ["Ekonomi daerah", "PDRB per kapita dan pertumbuhan t-1", "Mewakili kapasitas dan dinamika ekonomi wilayah."],
    ["Layanan dasar", "Sanitasi dan air minum t-1", "Mewakili kondisi dasar rumah tangga."],
    ["Struktur konsumsi", "Pangsa pangan t-1", "Indikator tekanan kesejahteraan rumah tangga."],
]
story += [data_table(data_rows, [36 * mm, 44 * mm, 94 * mm], font_size=7.8), Spacer(1, 5 * mm)]
universe_rows = [["Semesta", "Periode", "Digunakan untuk", "Alasan"]]
for item in DATA["universe_summary"]:
    universe_rows.append([str(item["province_n"]), item["period"], item["purpose"], item["reason"]])
story += [P("Mengapa ada 38, 34, dan 32 provinsi?", "H2ID"), data_table(universe_rows, [18 * mm, 27 * mm, 55 * mm, 74 * mm], font_size=6.9),
          P("Penanganan simbol BPS", "H2ID")]
legend_rows = [["Simbol", "Arti", "Perlakuan analitis"]]
for item in DATA["data_legend"][:8]:
    legend_rows.append([item["symbol"], item["displayed_meaning"], item["numeric_handling"] + ". " + item["note"]])
story += [data_table(legend_rows, [17 * mm, 48 * mm, 109 * mm], font_size=7.1), Spacer(1, 3 * mm), P("Prinsip terpenting: simbol data tidak tersedia tidak pernah diubah menjadi nol. Imputasi fitur, bila diperlukan, dilakukan hanya dari bagian data pelatihan pada setiap fold validasi.", "Source"), PageBreak()]

# Trend
story += page_title("04 / Tren", "Satu dekade penurunan, dengan gangguan di tengah jalan", "Angka nasional memperlihatkan arah jangka panjang yang membaik, tetapi seri tidak turun secara lurus setiap tahun.")
story += [image_flow(CHARTS["trend"], 174), Spacer(1, 4 * mm)]
best_change = changes[0]
story += [P(f"Dari 2015 hingga 2025, penurunan nasional mencapai <b>{rate_2015-rate_2025:.2f} poin persen</b> atau sekitar <b>{(rate_2015-rate_2025)/rate_2015*100:.1f}%</b> secara relatif. Pada kelompok 32 provinsi, perbaikan terbesar terjadi di <b>{best_change['province']}</b>, turun <b>{abs(best_change['change_2015_2025_pp']):.2f} poin persen</b>."),
          P("Kenaikan sekitar masa pandemi mengingatkan bahwa tren kemiskinan sensitif terhadap guncangan. Karena itu model menyertakan dummy 2020, tetapi tetap tidak menganggap pandemi sebagai satu-satunya penjelas."),
          P("Cara membaca", "H2ID"), P("Gunakan grafik nasional untuk arah umum. Untuk keputusan wilayah, lanjutkan ke peta dan peringkat provinsi karena rata-rata nasional dapat menyembunyikan kesenjangan besar."), PageBreak()]

story += page_title("05 / Kesenjangan", "Apakah provinsi bergerak mendekat?", "Konvergensi deskriptif menguji apakah sebaran tingkat kemiskinan antarprovinsi menyempit, tanpa mengklaim hubungan sebab-akibat.")
story += [image_flow(CHARTS["convergence"], 174), Spacer(1, 4 * mm)]
story += [P(f"Standar deviasi P0 pada 32 provinsi stabil turun dari <b>{convergence['std_dev_2015_pct']:.2f}</b> menjadi <b>{convergence['std_dev_2025_pct']:.2f} poin persen</b>, atau menyempit sekitar <b>{(1-convergence['std_dev_2025_pct']/convergence['std_dev_2015_pct'])*100:.1f}%</b>."),
          P(f"Regresi deskriptif perubahan 2015-2025 terhadap tingkat awal menghasilkan slope <b>{convergence['beta_slope_change_on_initial']:.3f}</b> dan korelasi <b>{convergence['initial_level_change_correlation']:.3f}</b>. Tanda negatif berarti provinsi dengan kemiskinan awal lebih tinggi cenderung mencatat penurunan lebih besar."),
          P("Namun konvergensi tidak berarti kesenjangan selesai. Rentang 2025 masih lebar dan hasil ini sensitif terhadap semesta wilayah serta tidak mengukur kedalaman kemiskinan."), PageBreak()]

# Spatial
story += page_title("06 / Spasial", "Kesenjangan antarprovinsi masih menonjol", "Peta koroplet membuat pola geografis terlihat: warna lebih gelap berarti persentase penduduk miskin lebih tinggi.")
story += [image_flow(CHARTS["map"], 174), Spacer(1, 3 * mm), P(f"Global Moran's I 2025 sebesar <b>{moran['moran_i']:.3f}</b> dengan pseudo-p <b>{moran['pseudo_p_value_two_sided']:.3f}</b> (999 permutasi, KNN-4). Nilai positif menunjukkan provinsi dengan tingkat serupa cenderung berdekatan. Ukuran ini eksploratif dan bergantung pada definisi tetangga."), P("Peta 2025 memakai 38 batas provinsi terkini dari BIG dan disederhanakan hanya untuk visualisasi; bukan untuk penetapan batas hukum.", "Source"), PageBreak()]
story += page_title("06 / Spasial", "Siapa yang berada di ujung distribusi?", "Peringkat membantu melihat besar selisih dan melengkapi pola visual pada peta.")
story += [image_flow(CHARTS["disparity"], 174), Spacer(1, 3 * mm)]
top5 = ranked[:5]
bottom5 = list(reversed(ranked[-5:]))
spatial_table = [["Kelompok", "Provinsi", "2025"]]
for r in top5:
    spatial_table.append(["5 tertinggi", r["province"], f"{r['poverty_rate_pct']:.2f}%"])
for r in bottom5:
    spatial_table.append(["5 terendah", r["province"], f"{r['poverty_rate_pct']:.2f}%"])
story += [data_table(spatial_table, [31 * mm, 108 * mm, 35 * mm], font_size=7.4), Spacer(1, 3 * mm), P("Peringkat adalah alat prioritisasi awal. Ukuran populasi miskin, biaya intervensi, kedalaman kemiskinan, dan ketimpangan tidak tercakup dalam satu indikator P0.", "Source"), PageBreak()]

# Correlation
story += page_title("07 / Faktor terkait", "Mengapa korelasi harus dibaca dari dua sudut?", "Korelasi pooled dan within menjawab pertanyaan berbeda. Perbedaan keduanya dapat mengungkap struktur wilayah yang selama ini tersembunyi.")
story += [image_flow(CHARTS["correlation"], 174), Spacer(1, 3 * mm)]
story += [P("Contoh temuan", "H2ID"), P("IPM, PDRB per kapita, sanitasi, dan air minum sama-sama menunjukkan hubungan negatif yang lebih jelas ketika perubahan diikuti dalam provinsi yang sama. Untuk TPT dan TPAK, tanda pooled dan within berbeda. Ini dapat terjadi karena provinsi dengan struktur ekonomi berbeda tidak dapat dibandingkan seperti satu populasi homogen."),
          P("Temuan ini berguna sebagai hipotesis: efek pasar kerja mungkin bergantung pada kualitas pekerjaan, informalitas, produktivitas, dan struktur biaya hidup. Analisis lanjutan dapat menambahkan upah riil, proporsi pekerja informal, pendidikan, inflasi pangan, bantuan sosial, serta kedalaman kemiskinan."),
          P("Batas interpretasi", "H2ID"), P("Korelasi tidak membuktikan sebab-akibat. Variabel dapat bergerak bersama karena faktor ketiga, perubahan definisi, atau respons kebijakan terhadap tingkat kemiskinan."), PageBreak()]

# Coefficients
story += page_title("08 / Model", "Apa yang paling membantu prediksi?", "Koefisien Ridge menunjukkan kontribusi kondisional setelah fitur distandarkan dan dianalisis bersama.")
story += [image_flow(CHARTS["coefficient"], 174), Spacer(1, 3 * mm)]
story += [P("Kemiskinan tahun sebelumnya mendominasi karena kemiskinan bersifat persisten. IPM memberi kontribusi negatif terbesar setelah persistensi diperhitungkan. Koefisien kecil atau tanda yang tampak tidak intuitif dapat muncul akibat kolinearitas, fitur yang bergerak bersama, dan regularisasi Ridge."),
          P("Karena itu grafik ini bukan peringkat kebijakan. Besarnya koefisien prediktif tidak sama dengan besarnya dampak jika pemerintah mengubah satu indikator."), PageBreak()]

# Benchmark
story += page_title("09 / Validasi", "Model diuji seperti benar-benar meramal masa depan", "Walk-forward validation melatih model hanya pada tahun sebelum tahun uji, lalu mengulang pengujian untuk 2022, 2023, 2024, dan 2025.")
story += [image_flow(CHARTS["benchmark"], 174), Spacer(1, 3 * mm)]
metric_rows = [["Model", "MAE", "RMSE", "MAPE", "R2"]]
for r in benchmark:
    metric_rows.append([r["model_name"], f"{r['mae']:.3f}", f"{r['rmse']:.3f}", f"{r['mape_pct']:.2f}%", f"{r['r2']:.3f}"])
story += [data_table(metric_rows, [82 * mm, 22 * mm, 23 * mm, 23 * mm, 24 * mm], font_size=7.1), Spacer(1, 3 * mm), P(f"Ensemble membagi bobot 50:50 antara naive tahun sebelumnya dan Ridge. MAE-nya <b>{(1-best['mae']/naive['mae'])*100:.1f}% lebih rendah</b> daripada naive lag-1, sehingga kompleksitas tambahan memberi nilai prediktif yang terukur.", "Source"), PageBreak()]
story += page_title("09 / Validasi", "Seberapa dekat prediksi dengan aktual?", "Titik yang dekat dengan garis diagonal berarti prediksi mendekati nilai aktual.")
story += [Table([[image_flow(CHARTS["scatter"], 122), P("<b>Ringkasan error</b><br/><br/>MAE 0.353 poin persen berarti rata-rata selisih absolut sekitar sepertiga poin persentase pada 128 observasi validasi.<br/><br/>RMSE 0.476 lebih besar daripada MAE karena memberi penalti lebih tinggi pada kesalahan besar.<br/><br/>R2 0.985 menunjukkan variasi lintas provinsi dan tahun sebagian besar dapat direkonstruksi model, terutama karena persistensi kemiskinan sangat kuat.<br/><br/><b>Tetap hati-hati:</b> validasi historis tidak menjamin akurasi saat terjadi guncangan baru atau perubahan kebijakan besar.", "BodyID")]], colWidths=[124 * mm, 50 * mm], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6)])), PageBreak()]
story += page_title("09 / Validasi", "Di mana model paling sulit?", "Rata-rata nasional error tidak cukup: diagnostik per provinsi menunjukkan lokasi yang membutuhkan kehati-hatian lebih tinggi.")
story += [image_flow(CHARTS["diagnostics"], 174), Spacer(1, 3 * mm)]
top_diag = DATA["province_diagnostics"][:5]
diag_rows = [["Provinsi", "MAE", "Bias aktual-prediksi", "Error maksimum", "Tahun"]]
for row in top_diag:
    diag_rows.append([row["province"], f"{row['mae_pp']:.3f}", f"{row['bias_actual_minus_pred_pp']:+.3f}", f"{row['maximum_absolute_error_pp']:.3f}", str(row["worst_test_year"])])
story += [data_table(diag_rows, [58 * mm, 24 * mm, 38 * mm, 30 * mm, 24 * mm], font_size=7.2), Spacer(1, 3 * mm), P("Bias negatif berarti aktual rata-rata lebih rendah daripada prediksi. Hanya empat tahun uji tersedia per provinsi, sehingga hasil ini adalah sinyal pemantauan, bukan ukuran permanen kualitas model wilayah.", "Source"), PageBreak()]

# Forecast
story += page_title("10 / Proyeksi", "Skenario dasar 2026", "Model meneruskan pola terakhir dengan informasi penggerak yang tersedia hingga 2025. Interval 80% menggambarkan ketidakpastian berdasarkan error validasi historis.")
story += [image_flow(CHARTS["forecast"], 174), Spacer(1, 2 * mm)]
forecast_rows = [["Peringkat", "Provinsi", "2025", "Proyeksi 2026", "Interval 80%"]]
for r in forecast[:8]:
    forecast_rows.append([r["forecast_rank_high_to_low"], r["province"], f"{r['actual_2025_pct']:.2f}%", f"{r['forecast_poverty_rate_pct']:.2f}%", f"{r['lower_80_pct']:.2f}-{r['upper_80_pct']:.2f}%"])
story += [data_table(forecast_rows, [19 * mm, 67 * mm, 25 * mm, 31 * mm, 32 * mm], font_size=7.2), Spacer(1, 2 * mm), P("Nilai interval dapat tidak simetris karena dibangun dari distribusi residual validasi. Semua hasil berstatus experimental_nonofficial.", "Source"), PageBreak()]

story += page_title("10 / Proyeksi", "Prioritas risiko, bukan sekadar peringkat", "Matriks menggabungkan level 2026, arah perubahan dari 2025, dan perbedaan hasil antarmodel.")
story += [image_flow(CHARTS["risk"], 174), Spacer(1, 3 * mm)]
high_priority = [row for row in forecast if row["risk_tier"] in {"Tinggi", "Sangat tinggi"}]
story += [P(f"Sebanyak <b>{len(high_priority)} dari 32 provinsi model</b> berada pada kategori proyeksi tinggi atau sangat tinggi. Kategori ini ditentukan dari level P0, bukan probabilitas kejadian dan bukan klasifikasi resmi BPS."),
          P("Ukuran titik menunjukkan rentang hasil lima model. Titik yang lebih besar menandakan asumsi model lebih berpengaruh terhadap hasil, sehingga angka titik perlu dibaca bersama interval dan konteks wilayah."),
          P("Aturan prioritas", "H2ID"), P("Wilayah dengan level tinggi tetap dipantau meskipun trennya menurun. Wilayah dengan level menengah tetapi perbedaan antarmodel besar membutuhkan verifikasi data dan scenario stress test. Tidak ada provinsi yang diproyeksikan meningkat lebih dari 0,10 poin persen pada skenario dasar ini, tetapi guncangan baru tidak tercakup."), PageBreak()]

# Dashboard guide
story += page_title("11 / Dashboard", "Cara menggunakan website", "Dashboard dirancang dari ringkasan nasional menuju temuan, eksplorasi provinsi, dan akhirnya evaluasi prediksi.")
guide_rows = [
    ["Bagian", "Pertanyaan yang dijawab", "Cara membaca"],
    ["Ringkasan", "Berapa tingkat kemiskinan terbaru?", "Lihat KPI nasional, perubahan jangka panjang, dan cakupan data."],
    ["Temuan", "Apa masalah, jawaban, dan kesimpulannya?", "Baca lima temuan, konvergensi, kesimpulan, dan rekomendasi."],
    ["Tren", "Bagaimana arah 2015-2025?", "Bandingkan seri nasional dan provinsi terpilih; perhatikan gangguan pandemi."],
    ["Peta", "Di mana tingkat kemiskinan tinggi?", "Pilih tahun, arahkan kursor, dan klik provinsi untuk detail."],
    ["Peringkat", "Provinsi mana yang tertinggi/terendah?", "Gunakan bersama peta agar nilai dan pola geografis terlihat."],
    ["Faktor terkait", "Indikator apa yang bergerak bersama P0?", "Bandingkan korelasi pooled dan within, jangan simpulkan kausalitas."],
    ["Model", "Apakah prediksi layak dipakai?", "Periksa MAE, RMSE, MAPE, R2, dan model pembanding."],
    ["Proyeksi", "Apa skenario dasar 2026?", "Baca titik, interval 80%, matriks risiko, dan error provinsi."],
    ["Metodologi", "Dari mana data dan bagaimana diolah?", "Periksa sumber, timing fitur, penanganan simbol, dan batasan."],
]
story += [data_table(guide_rows, [34 * mm, 61 * mm, 79 * mm], font_size=7.3), Spacer(1, 6 * mm)]
story += [P("Urutan eksplorasi yang disarankan", "H2ID"),
          P("1. Baca tab Temuan. 2. Pilih 2025 pada peta 38 provinsi. 3. Klik provinsi yang menarik. 4. Bandingkan faktor terkait. 5. Periksa validasi, error provinsi, dan matriks risiko. 6. Unduh laporan atau JSON untuk analisis lanjutan."),
          P("Website dapat dideploy ke Vercel atau Cloudflare Workers. Panduan teknis lengkap tersedia pada file <b>dashboard-web/docs/DEPLOYMENT.md</b>."), PageBreak()]

# Limitations and next steps
story += page_title("12 / Batasan", "Apa yang belum dijawab analisis ini?", "Hasil saat ini kuat untuk deskripsi, perbandingan, dan forecasting jangka pendek. Analisis kausal dan kebutuhan kebijakan memerlukan desain tambahan.")
limits = [
    ["Batasan", "Implikasi", "Langkah lanjutan"],
    ["Target hanya P0", "Tidak menangkap kedalaman dan keparahan kemiskinan.", "Tambahkan P1, P2, Gini, garis kemiskinan, dan jumlah penduduk miskin."],
    ["32 provinsi untuk model", "Provinsi baru Papua belum punya riwayat panjang yang setara.", "Bangun seri kabupaten atau lakukan backcasting batas baru bila sumber tersedia."],
    ["Asosiasi, bukan kausalitas", "Koefisien tidak mengukur dampak program.", "Gunakan difference-in-differences, synthetic control, atau evaluasi program."],
    ["Fitur tahunan", "Guncangan bulanan seperti inflasi pangan dapat terlambat terlihat.", "Tambahkan CPI pangan, harga beras, cuaca, dan data bantuan sosial berfrekuensi tinggi."],
    ["Interval historis", "Ketidakpastian bisa terlalu sempit saat rezim berubah.", "Lakukan scenario stress test dan conformal prediction per kelompok wilayah."],
]
story += [data_table(limits, [39 * mm, 62 * mm, 73 * mm], font_size=7.2), Spacer(1, 5 * mm)]
story += [P("Agenda analisis yang paling bernilai", "H2ID"),
          P("Prioritas pertama adalah memisahkan mekanisme pasar kerja: pengangguran terbuka, informalitas, jam kerja, upah riil, dan produktivitas. Prioritas kedua adalah memasukkan kerentanan harga pangan dan cakupan perlindungan sosial. Prioritas ketiga adalah membangun model hierarkis atau spasial agar kedekatan geografis dan kesamaan struktur ekonomi ikut diperhitungkan."),
          P("Temuan baru yang layak diuji", "H2ID"),
          P("Perbedaan tanda korelasi TPT/TPAK antara pooled dan within merupakan kandidat temuan substantif. Hipotesisnya: kualitas dan produktivitas pekerjaan lebih penting daripada sekadar status bekerja. Ini belum terbukti, tetapi dapat menjadi fokus riset lanjutan."), PageBreak()]

# Conclusion and recommendations
story += page_title("13 / Kesimpulan", "Apa yang dapat disimpulkan?", "Kesimpulan merangkum bukti yang tersedia; rekomendasi di bawah adalah agenda pemantauan dan riset, bukan klaim dampak kebijakan.")
conclusion_rows = [
    ["Dimensi", "Kesimpulan"],
    ["Kemajuan nasional", f"P0 turun dari {rate_2015:.2f}% menjadi {rate_2025:.2f}%; pandemi sempat membalik arah penurunan."],
    ["Ketimpangan", f"Dispersi 32 provinsi stabil menyempit, tetapi peta 38 provinsi tetap memperlihatkan rentang {ranked[-1]['poverty_rate_pct']:.2f}% hingga {ranked[0]['poverty_rate_pct']:.2f}%."],
    ["Geografi", f"Moran's I {moran['moran_i']:.3f} menunjukkan nilai serupa mengelompok secara spasial; pendekatan lintas wilayah relevan."],
    ["Faktor terkait", "IPM, kapasitas ekonomi, sanitasi, dan air minum berasosiasi negatif; paradoks TPT/TPAK menuntut variabel kualitas kerja."],
    ["Prediksi", f"Ensemble mencapai MAE {best['mae']:.3f} pp dan memperbaiki naive sekitar {(1-best['mae']/naive['mae'])*100:.1f}%; hasil 2026 tetap eksperimental."],
]
story += [data_table(conclusion_rows, [42 * mm, 132 * mm], font_size=7.5), Spacer(1, 5 * mm)]
story += [P("Rekomendasi prioritas", "H2ID"),
          P("1. <b>Pemantauan wilayah:</b> gunakan level kemiskinan, arah perubahan, kedekatan spasial, error historis, dan selisih antarmodel secara bersamaan; jangan hanya memakai satu peringkat."),
          P("2. <b>Peningkatan data:</b> tambahkan P1, P2, Gini, inflasi pangan, harga beras, pekerja informal, upah riil, jam kerja, bantuan sosial, serta kejadian bencana."),
          P("3. <b>Pengujian substantif:</b> uji hipotesis kualitas pekerjaan dan layanan dasar dengan model hierarkis/spasial; gunakan desain kausal terpisah ketika menilai program."),
          P("4. <b>Tata kelola model:</b> perbarui forecast setelah angka 2026 tersedia, simpan versi input/model, pantau drift, dan tampilkan selalu status nonresmi serta interval ketidakpastian."),
          Spacer(1, 4 * mm),
          Table([[P("Jawaban singkat", "H2ID")], [P("Kemiskinan Indonesia membaik secara nasional dan menunjukkan tanda konvergensi, tetapi masalah tetap terkonsentrasi secara geografis. Model cukup kuat untuk sinyal dini satu tahun, bukan untuk menetapkan target atau menyimpulkan dampak kebijakan.")]], colWidths=[174 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor(CREAM)), ("BOX", (0, 0), (-1, -1), 0.8, HexColor(GOLD)), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)])), PageBreak()]

# Sources
story += page_title("14 / Referensi", "Sumber data dan catatan reproduksi", "Sumber statistik berasal dari publikasi dan tabel resmi BPS. Geometri hanya dipakai untuk visualisasi spasial.")
source_rows = [["Sumber", "Tautan"]]
for item in DATA["sources"]:
    source_rows.append([item["label"], item["url"]])
story += [data_table(source_rows, [68 * mm, 106 * mm], font_size=6.7), Spacer(1, 5 * mm)]
story += [P("Reproduksi", "H2ID"), P("Data siap tayang tersimpan pada <b>dashboard-web/app/data/dashboard-data.json</b>. Hasil analisis lengkap tersimpan pada <b>data/processed/poverty_analysis.json</b>. Model memakai walk-forward validation dan fitur t-1 untuk mencegah kebocoran waktu."),
          P("Definisi singkat", "H2ID"),
          P("P0 adalah persentase penduduk yang berada di bawah garis kemiskinan. MAE adalah rata-rata selisih absolut. RMSE memberi bobot lebih besar pada kesalahan besar. MAPE adalah error persentase absolut rata-rata. R2 mengukur proporsi variasi yang dapat dijelaskan model pada data validasi."),
          Spacer(1, 5 * mm), HRFlowable(width="100%", thickness=1, color=HexColor(GOLD), spaceBefore=6, spaceAfter=10),
          P("Laporan ini merupakan bahan analitis dan komunikasi data. Angka resmi tetap merujuk pada publikasi BPS terkait.", "Quote")]


doc = SimpleDocTemplate(
    str(OUTPUT_PATH), pagesize=A4,
    rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
    title="Analisis Kemiskinan Indonesia 2015-2026",
    author="Project Peta Kemiskinan Indonesia",
    subject="Dashboard, analisis multivariat, validasi model, dan proyeksi 2026",
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
PUBLIC_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(OUTPUT_PATH, PUBLIC_OUTPUT_PATH)
print(json.dumps({"output": str(OUTPUT_PATH), "public_output": str(PUBLIC_OUTPUT_PATH)}))
