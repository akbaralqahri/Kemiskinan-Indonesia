from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import pypdfium2 as pdfium


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "raw" / "bps_publications"
POVERTY_DIR = ROOT / "data" / "raw" / "poverty"
OUT = ROOT / "data" / "processed" / "extracted_panel.json"


PROVINCES = [
    "Aceh", "Sumatera Utara", "Sumatera Barat", "Riau", "Jambi",
    "Sumatera Selatan", "Bengkulu", "Lampung", "Kepulauan Bangka Belitung",
    "Kepulauan Riau", "DKI Jakarta", "Jawa Barat", "Jawa Tengah",
    "DI Yogyakarta", "Jawa Timur", "Banten", "Bali", "Nusa Tenggara Barat",
    "Nusa Tenggara Timur", "Kalimantan Barat", "Kalimantan Tengah",
    "Kalimantan Selatan", "Kalimantan Timur", "Kalimantan Utara",
    "Sulawesi Utara", "Sulawesi Tengah", "Sulawesi Selatan",
    "Sulawesi Tenggara", "Gorontalo", "Sulawesi Barat", "Maluku",
    "Maluku Utara", "Papua Barat", "Papua Barat Daya", "Papua",
    "Papua Selatan", "Papua Tengah", "Papua Pegunungan",
]

ALIASES = {
    "Nusa Tengggara Timur": "Nusa Tenggara Timur",
    "D.I. Yogyakarta": "DI Yogyakarta",
    "D.I Yogyakarta": "DI Yogyakarta",
}

PAPUA_REGION = {
    "Papua Barat", "Papua Barat Daya", "Papua", "Papua Selatan",
    "Papua Tengah", "Papua Pegunungan",
}

ISLAND_GROUP = {
    "Aceh": "Sumatra", "Sumatera Utara": "Sumatra", "Sumatera Barat": "Sumatra",
    "Riau": "Sumatra", "Jambi": "Sumatra", "Sumatera Selatan": "Sumatra",
    "Bengkulu": "Sumatra", "Lampung": "Sumatra", "Kepulauan Bangka Belitung": "Sumatra",
    "Kepulauan Riau": "Sumatra", "DKI Jakarta": "Jawa", "Jawa Barat": "Jawa",
    "Jawa Tengah": "Jawa", "DI Yogyakarta": "Jawa", "Jawa Timur": "Jawa",
    "Banten": "Jawa", "Bali": "Bali-Nusa Tenggara", "Nusa Tenggara Barat": "Bali-Nusa Tenggara",
    "Nusa Tenggara Timur": "Bali-Nusa Tenggara", "Kalimantan Barat": "Kalimantan",
    "Kalimantan Tengah": "Kalimantan", "Kalimantan Selatan": "Kalimantan",
    "Kalimantan Timur": "Kalimantan", "Kalimantan Utara": "Kalimantan",
    "Sulawesi Utara": "Sulawesi", "Sulawesi Tengah": "Sulawesi",
    "Sulawesi Selatan": "Sulawesi", "Sulawesi Tenggara": "Sulawesi",
    "Gorontalo": "Sulawesi", "Sulawesi Barat": "Sulawesi", "Maluku": "Maluku",
    "Maluku Utara": "Maluku", "Papua Barat": "Papua", "Papua Barat Daya": "Papua",
    "Papua": "Papua", "Papua Selatan": "Papua", "Papua Tengah": "Papua",
    "Papua Pegunungan": "Papua",
}

PUBLICATION_URLS = {
    "Statistik Indonesia 2016": "https://www.bps.go.id/id/publication/2016/06/29/7aa1e8f93b4148234a9b4bc3/statistik-indonesia-2016.html",
    "Statistik Indonesia 2019": "https://www.bps.go.id/id/publication/2019/07/04/daac1ba18cae1e90706ee58a/statistik-indonesia-2019.html",
    "Statistik Indonesia 2021": "https://www.bps.go.id/id/publication/2021/02/26/938316574c78772f27e9b477/statistik-indonesia-2021.html",
    "Statistik Indonesia 2024": "https://www.bps.go.id/id/publication/2024/02/28/c1bacde03256343b2bf769b0/statistik-indonesia-2024.html",
    "Statistik Indonesia 2026": "https://www.bps.go.id/id/publication/2026/02/27/a43f03f45543dc4e9942f44c/statistik-indonesia-2026.html",
}


def normalize_province(value: str) -> str | None:
    value = " ".join(value.strip().split())
    value = ALIASES.get(value, value)
    return value if value in PROVINCES or value == "Indonesia" else None


STATUS_SUFFIXES = ["***", "**", "*", "e", "r", "a", "b", "c"]


def classify_raw_value(value: str | None) -> tuple[str | None, str]:
    if value is None:
        return None, "missing_column"
    raw = value.strip()
    if raw == "":
        return raw, "blank"
    if raw == "...":
        return raw, "unavailable"
    if raw in {"–", "—", "-"}:
        return raw, "none_zero_or_structural"
    if raw.upper() == "NA":
        return raw, "suppressed_not_displayed"
    if raw == "~0":
        return raw, "negligible_zero"
    for suffix in STATUS_SUFFIXES:
        if raw.endswith(suffix) and any(ch.isdigit() for ch in raw[:-len(suffix)]):
            return raw, {
                "e": "estimated", "r": "revised", "*": "preliminary",
                "**": "very_preliminary", "***": "very_very_preliminary",
                "a": "rse_25_to_50_caution", "b": "rse_code_b_verify",
                "c": "nonadditive_hierarchy",
            }[suffix]
    return raw, "observed"


def parse_csv_number(value: str | None) -> float | int | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value in {"...", "-", "–", "—", "NA"}:
        return None
    if value == "~0":
        return 0
    for suffix in STATUS_SUFFIXES:
        if value.endswith(suffix) and any(ch.isdigit() for ch in value[:-len(suffix)]):
            value = value[:-len(suffix)]
            break
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return None


def page_lines(filename: str, page_number: int) -> list[str]:
    doc = pdfium.PdfDocument(str(PDF_DIR / filename))
    text = doc[page_number - 1].get_textpage().get_text_range()
    return [" ".join(line.replace("\ufffe", "").strip().split()) for line in text.splitlines() if line.strip()]


def split_province_row(line: str) -> tuple[str, str] | None:
    candidates = sorted(PROVINCES + list(ALIASES), key=len, reverse=True)
    for name in candidates:
        if line == name or line.startswith(name + " "):
            canonical = ALIASES.get(name, name)
            rest = line[len(name):].strip()
            if rest and not re.match(r"^(?:\.\.\.|[–—-]|\d)", rest):
                continue
            return canonical, rest
    if line == "Indonesia" or line.startswith("Indonesia "):
        return "Indonesia", line[len("Indonesia"):].strip()
    return None


def clean_rate_token(token: str) -> float | None:
    token = token.strip()
    if token in {"...", "-", "–", "—", "Ц", "Е"}:
        return None
    token = token.replace("−", "-")
    # PDF extraction appends superscript footnote numbers to a few 2-decimal rates.
    m = re.fullmatch(r"(-?\d+),(\d{3})", token)
    if m and m.group(2)[-1] in "123":
        token = f"{m.group(1)},{m.group(2)[:2]}"
    try:
        return float(token.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def extract_rate_rows(filename: str, page_number: int, expected: int) -> dict[str, list[float | None]]:
    rows: dict[str, list[float | None]] = {}
    pattern = re.compile(r"(?:\.\.\.|[–—]|-?\d+,\d+)")
    for line in page_lines(filename, page_number):
        parsed = split_province_row(line)
        if not parsed:
            continue
        province, rest = parsed
        tokens = pattern.findall(rest)
        if len(tokens) >= expected:
            rows[province] = [clean_rate_token(t) for t in tokens[:expected]]
    return rows


def parse_grouped_token(token: str) -> float | int | None:
    token = token.strip()
    if token in {"...", "-", "–", "—", "Ц", "Е"}:
        return None
    token = token.replace("−", "-")
    if "," in token:
        try:
            number = float(token.replace(".", "").replace(" ", "").replace(",", "."))
            return int(number) if number.is_integer() else number
        except ValueError:
            return None
    cleaned = token.replace(".", "").replace(" ", "")
    try:
        return int(cleaned)
    except ValueError:
        return None


def partition_grouped_numbers(rest: str, expected: int, min_value: int, max_value: int) -> list[float | int | None] | None:
    raw = rest.split()

    def candidates_at(index: int):
        if index >= len(raw):
            return
        token = raw[index]
        if token in {"...", "-", "–", "—", "Ц", "Е"}:
            yield index + 1, None
            return
        if "." in token or ("," in token and not re.fullmatch(r"\d{3},\d+", token)):
            value = parse_grouped_token(token)
            if value is not None and min_value <= abs(float(value)) <= max_value:
                yield index + 1, value
            return
        for size in range(1, 4):
            if index + size > len(raw):
                break
            parts = raw[index:index + size]
            if not re.fullmatch(r"-?\d+", parts[0]):
                continue
            if any(not re.fullmatch(r"\d{3}(?:,\d+)?", p) for p in parts[1:]):
                continue
            value = parse_grouped_token(" ".join(parts))
            if value is not None and min_value <= abs(float(value)) <= max_value:
                yield index + size, value

    memo: dict[tuple[int, int], list[float | int | None] | None] = {}

    def solve(index: int, remaining: int):
        key = (index, remaining)
        if key in memo:
            return memo[key]
        if remaining == 0:
            return [] if index == len(raw) else None
        for next_index, value in candidates_at(index):
            tail = solve(next_index, remaining - 1)
            if tail is not None:
                memo[key] = [value] + tail
                return memo[key]
        memo[key] = None
        return None

    return solve(0, expected)


def extract_grouped_rows(filename: str, page_number: int, expected: int, min_value: int, max_value: int) -> dict[str, list[float | int | None]]:
    rows: dict[str, list[float | int | None]] = {}
    for line in page_lines(filename, page_number):
        parsed = split_province_row(line)
        if not parsed:
            continue
        province, rest = parsed
        values = partition_grouped_numbers(rest, expected, min_value, max_value)
        if values is not None:
            rows[province] = values
    return rows


def add_indicator(indicators: list[dict], panel: dict, province: str, year: int, code: str,
                  value, unit: str, publication: str, table: str, page: int, note: str = ""):
    if province == "Indonesia" or province not in PROVINCES:
        return
    clean_value = None if value is None or (isinstance(value, float) and math.isnan(value)) else value
    indicators.append({
        "province": province,
        "year": year,
        "variable_code": code,
        "value": clean_value,
        "unit": unit,
        "publication": publication,
        "table": table,
        "pdf_page": page,
        "source_url": PUBLICATION_URLS[publication],
        "note": note,
    })
    panel[(province, year)][code] = clean_value


def add_year_series(indicators, panel, rows, years, code, unit, publication, table, page, note=""):
    for province, values in rows.items():
        for idx, year in enumerate(years):
            add_indicator(indicators, panel, province, year, code, values[idx], unit,
                          publication, table, page, note)


def load_poverty(panel: dict):
    raw_rows = []
    skipped = []
    for year in range(2015, 2026):
        path = POVERTY_DIR / f"Jumlah dan Persentase Penduduk Miskin Menurut Provinsi, {year}.csv"
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for source_row_number, row in enumerate(reader, start=2):
                province = normalize_province(row.get("Provinsi", ""))
                if not province:
                    if any((v or "").strip() for v in row.values()):
                        skipped.append({"year": year, "source_row": source_row_number,
                                        "first_cell": row.get("Provinsi", ""), "source_file": path.name})
                    continue
                geo_level = "national" if province == "Indonesia" else "province"
                for semester in ("Maret", "September"):
                    def find_raw(prefix):
                        key = next((k for k in row if k.startswith(f"{prefix} - {semester}")), None)
                        return row.get(key) if key else None

                    poverty_line_raw = find_raw("Garis Kemiskinan")
                    poor_count_raw = find_raw("Jumlah Penduduk Miskin")
                    poverty_rate_raw = find_raw("Persentase Penduduk Miskin")
                    poverty_line = parse_csv_number(poverty_line_raw)
                    poor_count = parse_csv_number(poor_count_raw)
                    poverty_rate = parse_csv_number(poverty_rate_raw)
                    poverty_line_raw, poverty_line_status = classify_raw_value(poverty_line_raw)
                    poor_count_raw, poor_count_status = classify_raw_value(poor_count_raw)
                    poverty_rate_raw, poverty_rate_status = classify_raw_value(poverty_rate_raw)
                    validation_flag = "OK_OR_MISSING"
                    validation_note = ""
                    if poverty_rate is not None and not (0 <= float(poverty_rate) <= 100):
                        validation_flag = "ERROR_RANGE"
                        validation_note = "Nilai persentase di luar 0-100; struktur baris sumber terindikasi bergeser."
                    if province == "Indonesia" and semester == "Maret" and year == 2017:
                        validation_flag = "ERROR_KNOWN_MISALIGNMENT"
                        validation_note = "CSV menyalin nilai September (10,12) ke kolom Maret; cross-check Statistik Indonesia 2026 tabel 4.6.1 memberi 10,64."
                    raw_rows.append({
                        "province": province, "year": year, "semester": semester,
                        "geo_level": geo_level, "poverty_line_rp": poverty_line,
                        "poor_population_thousand": poor_count, "poverty_rate_pct": poverty_rate,
                        "poverty_line_raw": poverty_line_raw, "poverty_line_status": poverty_line_status,
                        "poor_population_raw": poor_count_raw, "poor_population_status": poor_count_status,
                        "poverty_rate_raw": poverty_rate_raw, "poverty_rate_status": poverty_rate_status,
                        "source_file": path.name, "source_row": source_row_number,
                        "validation_flag": validation_flag, "validation_note": validation_note,
                    })
                    if semester == "Maret" and geo_level == "province":
                        panel[(province, year)]["poverty_line_rp"] = poverty_line
                        panel[(province, year)]["poor_population_thousand"] = poor_count
                        panel[(province, year)]["poverty_rate_pct"] = poverty_rate
    return raw_rows, skipped


def build():
    panel = defaultdict(dict)
    poverty_raw, skipped = load_poverty(panel)
    indicators: list[dict] = []

    # Labour market: use August observations consistently.
    labour_specs = [
        ("Statistik_Indonesia_2016.pdf", 147, 10, "Statistik Indonesia 2016", "3.2.10", {2015: (4, 9)}),
        ("Statistik_Indonesia_2019.pdf", 152, 10, "Statistik Indonesia 2019", "3.2.11", {2016: (0, 5), 2017: (2, 7), 2018: (4, 9)}),
        ("Statistik_Indonesia_2021.pdf", 159, 10, "Statistik Indonesia 2021", "3.2.11", {2019: (2, 7), 2020: (4, 9)}),
        ("Statistik_Indonesia_2024.pdf", 193, 10, "Statistik Indonesia 2024", "3.2.11", {2021: (0, 5), 2022: (2, 7), 2023: (4, 9)}),
        ("Statistik_Indonesia_2026.pdf", 224, 8, "Statistik Indonesia 2026", "3.2.11", {2024: (1, 5), 2025: (3, 7)}),
    ]
    for filename, page, expected, publication, table, mapping in labour_specs:
        rows = extract_rate_rows(filename, page, expected)
        for province, values in rows.items():
            for year, (tpt_idx, tpak_idx) in mapping.items():
                add_indicator(indicators, panel, province, year, "tpt_aug_pct", values[tpt_idx], "%", publication, table, page, "Sakernas Agustus")
                add_indicator(indicators, panel, province, year, "tpak_aug_pct", values[tpak_idx], "%", publication, table, page, "Sakernas Agustus")

    # Human Development Index.
    add_year_series(indicators, panel,
                    extract_rate_rows("Statistik_Indonesia_2021.pdf", 303, 6),
                    list(range(2015, 2021)), "hdi", "index", "Statistik Indonesia 2021", "4.6.7", 303)
    add_year_series(indicators, panel,
                    extract_rate_rows("Statistik_Indonesia_2026.pdf", 381, 5),
                    list(range(2021, 2026)), "hdi", "index", "Statistik Indonesia 2026", "4.6.7", 381,
                    "2021-2025 memakai UHH LF SP2020; seri lama berbasis SP2010 tidak dicampur tanpa flag")

    # Household infrastructure.
    san_2015 = extract_rate_rows("Statistik_Indonesia_2016.pdf", 214, 5)
    wat_2015 = extract_rate_rows("Statistik_Indonesia_2016.pdf", 215, 5)
    for province, values in san_2015.items():
        add_indicator(indicators, panel, province, 2015, "sanitation_access_pct", values[4], "%", "Statistik Indonesia 2016", "4.3.8", 214, "Konsep lama; ada jeda konsep sebelum seri backcast 2016-2020")
    for province, values in wat_2015.items():
        add_indicator(indicators, panel, province, 2015, "drinking_water_access_pct", values[4], "%", "Statistik Indonesia 2016", "4.3.9", 215, "Konsep lama; ada jeda konsep sebelum seri backcast 2016-2020")
    add_year_series(indicators, panel, extract_rate_rows("Statistik_Indonesia_2021.pdf", 269, 5), list(range(2016, 2021)),
                    "sanitation_access_pct", "%", "Statistik Indonesia 2021", "4.3.8", 269, "Konsep sanitasi layak terbaru diterapkan pada seri 2016-2020")
    add_year_series(indicators, panel, extract_rate_rows("Statistik_Indonesia_2021.pdf", 270, 5), list(range(2016, 2021)),
                    "drinking_water_access_pct", "%", "Statistik Indonesia 2021", "4.3.9", 270, "Konsep air minum layak terbaru diterapkan pada seri 2016-2020")
    add_year_series(indicators, panel, extract_rate_rows("Statistik_Indonesia_2026.pdf", 344, 5), list(range(2021, 2026)),
                    "sanitation_access_pct", "%", "Statistik Indonesia 2026", "4.3.8", 344)
    add_year_series(indicators, panel, extract_rate_rows("Statistik_Indonesia_2026.pdf", 345, 5), list(range(2021, 2026)),
                    "drinking_water_access_pct", "%", "Statistik Indonesia 2026", "4.3.9", 345)

    # Real GRDP per capita: latest available publication for each segment.
    pdrb_specs = [
        ("Statistik_Indonesia_2019.pdf", 701, 5, "Statistik Indonesia 2019", [2015, 2016, 2017, 2018], [1, 2, 3, 4]),
        ("Statistik_Indonesia_2021.pdf", 723, 5, "Statistik Indonesia 2021", [2019, 2020], [3, 4]),
        ("Statistik_Indonesia_2026.pdf", 858, 5, "Statistik Indonesia 2026", [2021, 2022, 2023, 2024, 2025], [0, 1, 2, 3, 4]),
    ]
    for filename, page, expected, publication, years, indexes in pdrb_specs:
        rows = extract_grouped_rows(filename, page, expected, 5_000, 1_000_000)
        for province, values in rows.items():
            for year, idx in zip(years, indexes):
                add_indicator(indicators, panel, province, year, "pdrb_pc_adhk2010_thousand_rp", values[idx], "thousand rupiah", publication, "15.2.6", page)

    # Total GRDP growth and per-capita GRDP growth.
    growth_specs = [
        ("Statistik_Indonesia_2019.pdf", 699, "Statistik Indonesia 2019", "pdrb_growth_pct", "15.2.4", [2015, 2016, 2017, 2018]),
        ("Statistik_Indonesia_2021.pdf", 721, "Statistik Indonesia 2021", "pdrb_growth_pct", "15.2.4", [2019, 2020]),
        ("Statistik_Indonesia_2024.pdf", 786, "Statistik Indonesia 2024", "pdrb_growth_pct", "15.2.4", [2021, 2022, 2023]),
        ("Statistik_Indonesia_2026.pdf", 856, "Statistik Indonesia 2026", "pdrb_growth_pct", "15.2.4", [2024, 2025]),
        ("Statistik_Indonesia_2019.pdf", 702, "Statistik Indonesia 2019", "pdrb_pc_growth_pct", "15.2.7", [2015, 2016, 2017, 2018]),
        ("Statistik_Indonesia_2021.pdf", 724, "Statistik Indonesia 2021", "pdrb_pc_growth_pct", "15.2.7", [2019, 2020]),
        ("Statistik_Indonesia_2024.pdf", 789, "Statistik Indonesia 2024", "pdrb_pc_growth_pct", "15.2.7", [2021, 2022, 2023]),
        ("Statistik_Indonesia_2026.pdf", 859, "Statistik Indonesia 2026", "pdrb_pc_growth_pct", "15.2.7", [2024, 2025]),
    ]
    for filename, page, publication, code, table, years in growth_specs:
        rows = extract_rate_rows(filename, page, 4)
        source_years = {
            ("Statistik_Indonesia_2019.pdf", 699): [2015, 2016, 2017, 2018],
            ("Statistik_Indonesia_2021.pdf", 721): [2017, 2018, 2019, 2020],
            ("Statistik_Indonesia_2024.pdf", 786): [2020, 2021, 2022, 2023],
            ("Statistik_Indonesia_2026.pdf", 856): [2022, 2023, 2024, 2025],
            ("Statistik_Indonesia_2019.pdf", 702): [2015, 2016, 2017, 2018],
            ("Statistik_Indonesia_2021.pdf", 724): [2017, 2018, 2019, 2020],
            ("Statistik_Indonesia_2024.pdf", 789): [2020, 2021, 2022, 2023],
            ("Statistik_Indonesia_2026.pdf", 859): [2022, 2023, 2024, 2025],
        }[(filename, page)]
        for province, values in rows.items():
            by_year = dict(zip(source_years, values))
            for year in years:
                add_indicator(indicators, panel, province, year, code, by_year.get(year), "%", publication, table, page)

    # Expenditure is available for 9 of 11 years in the selected yearbooks.
    exp_specs = [
        ("Statistik_Indonesia_2016.pdf", 542, "Statistik Indonesia 2016", [2015], [(1, 3, 5)]),
        ("Statistik_Indonesia_2019.pdf", 588, "Statistik Indonesia 2019", [2017, 2018], [(0, 2, 4), (1, 3, 5)]),
        ("Statistik_Indonesia_2021.pdf", 610, "Statistik Indonesia 2021", [2019, 2020], [(0, 2, 4), (1, 3, 5)]),
        ("Statistik_Indonesia_2024.pdf", 670, "Statistik Indonesia 2024", [2022, 2023], [(0, 2, 4), (1, 3, 5)]),
        ("Statistik_Indonesia_2026.pdf", 746, "Statistik Indonesia 2026", [2024, 2025], [(0, 2, 4), (1, 3, 5)]),
    ]
    for filename, page, publication, years, indexes in exp_specs:
        rows = extract_grouped_rows(filename, page, 6, 100_000, 10_000_000)
        for province, values in rows.items():
            for year, (food_i, nonfood_i, total_i) in zip(years, indexes):
                food, nonfood, total = values[food_i], values[nonfood_i], values[total_i]
                add_indicator(indicators, panel, province, year, "food_exp_pc_month_rp", food, "rupiah/person/month", publication, "13.1.8", page, "Susenas Maret")
                add_indicator(indicators, panel, province, year, "nonfood_exp_pc_month_rp", nonfood, "rupiah/person/month", publication, "13.1.8", page, "Susenas Maret")
                add_indicator(indicators, panel, province, year, "total_exp_pc_month_rp", total, "rupiah/person/month", publication, "13.1.8", page, "Susenas Maret")
                share = round(float(food) / float(total) * 100, 4) if food is not None and total else None
                add_indicator(indicators, panel, province, year, "food_share_pct", share, "% (derived)", publication, "Derived from 13.1.8", page, "food/total*100")

    core_codes = [
        "poverty_rate_pct", "poor_population_thousand", "tpt_aug_pct", "tpak_aug_pct",
        "hdi", "pdrb_pc_adhk2010_thousand_rp", "pdrb_growth_pct",
        "sanitation_access_pct", "drinking_water_access_pct",
    ]
    panel_rows = []
    for year in range(2015, 2026):
        for province in PROVINCES:
            values = panel[(province, year)]
            core_nonmissing = sum(values.get(code) is not None for code in core_codes)
            if province in {"Papua Barat", "Papua"}:
                territory_class = "papua_parent_boundary_changes"
            elif province in PAPUA_REGION:
                territory_class = "papua_new_province"
            else:
                territory_class = "stable32"
            row = {
                "province": province,
                "year": year,
                "island_group": ISLAND_GROUP[province],
                "territory_class": territory_class,
                "stable32_model_flag": 1 if territory_class == "stable32" else 0,
                "covid_2020_dummy": 1 if year == 2020 else 0,
                "hdi_method_break_2021plus": 1 if year >= 2021 else 0,
                "sanitation_concept_break_2016plus": 1 if year >= 2016 else 0,
                "papua_boundary_break_2023plus": 1 if province in PAPUA_REGION and year >= 2023 else 0,
            }
            for code in [
                "poverty_line_rp", "poor_population_thousand", "poverty_rate_pct",
                "tpt_aug_pct", "tpak_aug_pct", "hdi", "pdrb_pc_adhk2010_thousand_rp",
                "pdrb_growth_pct", "pdrb_pc_growth_pct", "sanitation_access_pct",
                "drinking_water_access_pct", "food_exp_pc_month_rp",
                "nonfood_exp_pc_month_rp", "total_exp_pc_month_rp", "food_share_pct",
            ]:
                row[code] = values.get(code)
            row["core_nonmissing_count"] = core_nonmissing
            row["core_complete_flag"] = 1 if core_nonmissing == len(core_codes) else 0
            panel_rows.append(row)

    coverage = []
    coverage_codes = [
        "poverty_line_rp", "poor_population_thousand", "poverty_rate_pct", "tpt_aug_pct",
        "tpak_aug_pct", "hdi", "pdrb_pc_adhk2010_thousand_rp", "pdrb_growth_pct",
        "pdrb_pc_growth_pct", "sanitation_access_pct", "drinking_water_access_pct",
        "food_exp_pc_month_rp", "nonfood_exp_pc_month_rp", "total_exp_pc_month_rp", "food_share_pct",
    ]
    for year in range(2015, 2026):
        stable = [r for r in panel_rows if r["year"] == year and r["stable32_model_flag"] == 1]
        for code in coverage_codes:
            count = sum(r.get(code) is not None for r in stable)
            coverage.append({"year": year, "variable_code": code, "nonmissing_stable32": count,
                             "expected_stable32": 32, "coverage_pct": count / 32 * 100})

    payload = {
        "generated_from": "11 local poverty CSV files plus five official BPS Statistical Yearbooks",
        "poverty_raw": poverty_raw,
        "poverty_skipped_rows": skipped,
        "indicators_long": indicators,
        "panel_rows": panel_rows,
        "coverage": coverage,
        "province_count": len(PROVINCES),
        "stable32_count": 32,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "poverty_raw_rows": len(poverty_raw),
        "indicator_rows": len(indicators),
        "panel_rows": len(panel_rows),
        "coverage_rows": len(coverage),
    }, ensure_ascii=False))


if __name__ == "__main__":
    build()
