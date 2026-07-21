import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, "$1")), "..");
const DATA_PATH = path.join(ROOT, "data", "processed", "extracted_panel.json");
const ANALYSIS_PATH = path.join(ROOT, "data", "processed", "poverty_analysis.json");
const OUTPUT_DIR = path.join(ROOT, "output", "spreadsheets", "poverty_analysis_2015_2026");
const OUTPUT_PATH = path.join(OUTPUT_DIR, "analisis_dan_forecast_kemiskinan_indonesia_2015_2026.xlsx");
const PREVIEW_DIR = path.join(OUTPUT_DIR, "previews");

const data = JSON.parse(await fs.readFile(DATA_PATH, "utf8"));
const analysis = JSON.parse(await fs.readFile(ANALYSIS_PATH, "utf8"));
const wb = Workbook.create();

const COLORS = {
  navy: "#17365D", blue: "#1F4E78", teal: "#0F6B78", green: "#548235",
  orange: "#F4B183", paleBlue: "#D9EAF7", paleGreen: "#E2F0D9",
  paleOrange: "#FCE4D6", paleRed: "#F4CCCC", gray: "#E7E6E6",
  darkGray: "#595959", white: "#FFFFFF", yellow: "#FFF2CC",
};

function colLetter(n) {
  let s = "";
  while (n > 0) {
    n -= 1;
    s = String.fromCharCode(65 + (n % 26)) + s;
    n = Math.floor(n / 26);
  }
  return s;
}

function writeBlock(sheet, startRow, startCol, headers, objects) {
  const matrix = [headers, ...objects.map((obj) => headers.map((h) => obj[h] ?? null))];
  const range = sheet.getRangeByIndexes(startRow, startCol, matrix.length, headers.length);
  range.values = matrix;
  return { range, rows: objects.length, cols: headers.length };
}

function styleTitle(range) {
  range.format.fill = COLORS.navy;
  range.format.font = { bold: true, color: COLORS.white, size: 18 };
  range.format.verticalAlignment = "center";
  range.format.rowHeight = 36;
}

function styleSection(range) {
  range.format.fill = COLORS.paleBlue;
  range.format.font = { bold: true, color: COLORS.navy, size: 12 };
  range.format.borders = { preset: "outside", style: "thin", color: "#A6A6A6" };
}

function styleHeader(range) {
  range.format.fill = COLORS.blue;
  range.format.font = { bold: true, color: COLORS.white, size: 10 };
  range.format.wrapText = true;
  range.format.verticalAlignment = "center";
  range.format.horizontalAlignment = "center";
  range.format.rowHeight = 34;
  range.format.borders = { preset: "all", style: "thin", color: "#B4C6E7" };
}

function styleBlock(sheet, startRow, startCol, headers, rowCount, widths = {}) {
  styleHeader(sheet.getRangeByIndexes(startRow, startCol, 1, headers.length));
  const used = sheet.getRangeByIndexes(startRow, startCol, rowCount + 1, headers.length);
  used.format.borders = { preset: "inside", style: "thin", color: "#E7E6E6" };
  used.format.font = { name: "Aptos", size: 9 };
  for (let i = 0; i < headers.length; i++) {
    const col = colLetter(startCol + i + 1);
    sheet.getRange(`${col}:${col}`).format.columnWidth = widths[headers[i]] ?? 15;
  }
}

function styleDataSheet(sheet, headers, rowCount, widths = {}, freezeCols = 2) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(Math.min(freezeCols, headers.length));
  styleBlock(sheet, 0, 0, headers, rowCount, widths);
}

function addTableAt(sheet, address, name) {
  return sheet.tables.add(address, true, name);
}

function addMainTable(sheet, headers, rowCount, name) {
  addTableAt(sheet, `A1:${colLetter(headers.length)}${rowCount + 1}`, name);
}

const dashboard = wb.worksheets.add("Dashboard_Seed");
const legendSheet = wb.worksheets.add("Data_Legend");
const inventory = wb.worksheets.add("Inventaris");
const panelSheet = wb.worksheets.add("Panel_March");
const modelPanelSheet = wb.worksheets.add("Model_Panel_Lag1");
const trendSheet = wb.worksheets.add("EDA_Tren");
const driverSheet = wb.worksheets.add("EDA_Driver");
const benchmarkSheet = wb.worksheets.add("Model_Benchmark");
const cvSheet = wb.worksheets.add("CV_Predictions");
const forecastSheet = wb.worksheets.add("Forecast_2026");
const povertySheet = wb.worksheets.add("Poverty_Raw");
const indicatorsSheet = wb.worksheets.add("Indicators_Long");
const qcSheet = wb.worksheets.add("QC_Coverage");
const sourcesSheet = wb.worksheets.add("Sources");

// Dashboard seed: concise entry point for a future interactive dashboard.
dashboard.showGridLines = false;
dashboard.freezePanes.freezeRows(1);
dashboard.mergeCells("A1:N1");
dashboard.getRange("A1").values = [["Analisis dan Forecast Kemiskinan Indonesia, 2015–2026"]];
styleTitle(dashboard.getRange("A1:N1"));
dashboard.mergeCells("A3:N3");
dashboard.getRange("A3").values = [["Ruang lingkup dan prinsip waktu"]];
styleSection(dashboard.getRange("A3:N3"));
dashboard.mergeCells("A4:N5");
dashboard.getRange("A4").values = [[
  "Target adalah persentase penduduk miskin Maret. Model memakai 32 provinsi dengan batas stabil dan seluruh indikator substantif pada t-1, sehingga TPT Agustus atau indikator tahunan tidak bocor ke target Maret tahun yang sama. Forecast 2026 bersifat eksperimental dan bukan angka resmi BPS."
]];
dashboard.getRange("A4:N5").format = {
  fill: "#F7FAFC", wrapText: true, verticalAlignment: "top",
  borders: { preset: "outside", style: "thin", color: "#B4C6E7" },
  font: { name: "Aptos", size: 10, color: COLORS.darkGray },
};

const kpis = [
  { range: "A7:C7", value: "A8:C9", label: "Provinsi model", formula: "=COUNTA(Forecast_2026!A2:A33)", format: "0" },
  { range: "D7:F7", value: "D8:F9", label: "Observasi training", formula: "=COUNTA(Model_Panel_Lag1!A2:A321)", format: "0" },
  { range: "G7:I7", value: "G8:I9", label: "MAE rolling-CV", formula: "=Model_Benchmark!I2", format: "0.000\" pp\"" },
  { range: "J7:N7", value: "J8:N9", label: "Model rekomendasi", formula: "=Model_Benchmark!D2", format: "General" },
];
for (const kpi of kpis) {
  dashboard.mergeCells(kpi.range);
  dashboard.mergeCells(kpi.value);
  dashboard.getRange(kpi.range.split(":")[0]).values = [[kpi.label]];
  dashboard.getRange(kpi.range).format = { fill: COLORS.gray, font: { bold: true, color: COLORS.darkGray, size: 10 }, horizontalAlignment: "center", verticalAlignment: "center" };
  dashboard.getRange(kpi.value.split(":")[0]).formulas = [[kpi.formula]];
  dashboard.getRange(kpi.value).format = { fill: COLORS.paleGreen, font: { bold: true, color: COLORS.navy, size: kpi.label === "Model rekomendasi" ? 12 : 17 }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, numberFormat: kpi.format, borders: { preset: "outside", style: "thin", color: "#A9D18E" } };
}

dashboard.mergeCells("A11:N11");
dashboard.getRange("A11").values = [["Temuan awal yang layak diuji lebih lanjut"]];
styleSection(dashboard.getRange("A11:N11"));
const corrByCode = Object.fromEntries(analysis.eda_correlations.map((r) => [r.feature_code, r]));
const findings = [
  ["1", "Persistensi kuat", `Korelasi P0(t-1) dengan P0(t) = ${corrByCode.lag_poverty_rate_pct.pooled_pearson_r.toFixed(3)}; perubahan kemiskinan cenderung bertahap.`],
  ["2", "Sinyal struktural", `Dalam-provinsi, IPM (${corrByCode.lag_hdi.within_province_r.toFixed(3)}), PDRB/kapita (${corrByCode.lag_log_pdrb_pc.within_province_r.toFixed(3)}), sanitasi (${corrByCode.lag_sanitation_access_pct.within_province_r.toFixed(3)}), dan air minum (${corrByCode.lag_drinking_water_access_pct.within_province_r.toFixed(3)}) berasosiasi negatif dengan P0.`],
  ["3", "Kandidat paradoks agregasi", `TPT tampak negatif secara pooled (${corrByCode.lag_tpt_aug_pct.pooled_pearson_r.toFixed(3)}) tetapi positif dalam-provinsi (${corrByCode.lag_tpt_aug_pct.within_province_r.toFixed(3)}). Struktur antarprovinsi dapat membalik kesimpulan agregat.`],
  ["4", "Batas interpretasi", "Korelasi dan koefisien model bersifat prediktif/deskriptif, bukan bukti dampak kausal."],
];
dashboard.getRange("A13:N16").values = findings.map((r) => [r[0], r[1], ...Array(12).fill(null)]);
for (let row = 13; row <= 16; row++) {
  dashboard.mergeCells(`C${row}:N${row}`);
  dashboard.getRange(`C${row}`).values = [[findings[row - 13][2]]];
  dashboard.getRange(`A${row}:N${row}`).format = { fill: row % 2 ? "#F7FAFC" : COLORS.paleBlue, wrapText: true, verticalAlignment: "center", borders: { preset: "bottom", style: "thin", color: "#D9E2F3" }, font: { name: "Aptos", size: 9 } };
  dashboard.getRange(`A${row}`).format.font = { bold: true, color: COLORS.blue };
  dashboard.getRange(`B${row}`).format.font = { bold: true, color: COLORS.navy };
  dashboard.getRange(`A${row}:N${row}`).format.rowHeight = 35;
}

const nationalTrend = [
  [2015, 11.22, 28592.83], [2016, 10.86, 28005.39], [2017, 10.64, 27771.22],
  [2018, 9.82, 25949.80], [2019, 9.41, 25144.72], [2020, 9.78, 26424.02],
  [2021, 10.14, 27542.77], [2022, 9.54, 26161.16], [2023, 9.36, 25898.55],
  [2024, 9.03, 25219.20], [2025, 8.47, 23854.56],
];
dashboard.getRange("A34:C45").values = [["Tahun", "P0 Indonesia (%)", "Penduduk miskin (ribu)"], ...nationalTrend];
styleHeader(dashboard.getRange("A34:C34"));
dashboard.getRange("B35:B45").format.numberFormat = "0.00";
dashboard.getRange("C35:C45").format.numberFormat = "#,##0.00";
const overallBench = analysis.model_benchmark.filter((r) => r.evaluation_scope === "overall_2022_2025").sort((a, b) => a.mae_rank - b.mae_rank);
const shortModelNames = { ensemble_naive_ridge: "Ensemble", ridge_lag_drivers: "Ridge lag + driver", province_linear_trend: "Tren provinsi", naive_lag1: "Naive lag-1", ridge_drivers_only: "Ridge driver" };
dashboard.getRange("J34:K39").values = [["Model", "MAE"], ...overallBench.map((r) => [shortModelNames[r.model_code], r.mae])];
styleHeader(dashboard.getRange("J34:K34"));
dashboard.getRange("K35:K39").format.numberFormat = "0.000";
const nationalChart = dashboard.charts.add("line", dashboard.getRange("A34:B45"));
nationalChart.setPosition("A18", "G31");
nationalChart.title = "Tren P0 Indonesia — Maret";
nationalChart.hasLegend = false;
nationalChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
nationalChart.yAxis = { numberFormatCode: "0.0", min: 7, max: 13 };
const modelChart = dashboard.charts.add("bar", dashboard.getRange("J34:K39"));
modelChart.setPosition("H18", "N31");
modelChart.title = "MAE Rolling-CV 2022–2025 (lebih kecil lebih baik)";
modelChart.hasLegend = false;
modelChart.yAxis = { numberFormatCode: "0.00", min: 0, max: 0.7 };
dashboard.mergeCells("A47:N49");
dashboard.getRange("A47").values = [[
  "Peringatan: forecast 2026 adalah simulasi analitik, menggunakan input 2025 yang sebagian masih berstatus sementara/sangat sementara. Interval 80% berasal dari residual out-of-sample dan tidak mencakup seluruh risiko perubahan kebijakan, bencana, harga pangan, atau revisi data."
]];
dashboard.getRange("A47:N49").format = { fill: COLORS.yellow, font: { bold: true, color: "#7F6000", size: 10 }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: "#BF9000" } };
for (let c = 1; c <= 14; c++) dashboard.getRange(`${colLetter(c)}:${colLetter(c)}`).format.columnWidth = c === 2 ? 21 : 13;

// Data legend and observed status counts.
const legendHeaders = ["symbol", "displayed_meaning", "numeric_handling", "quality_status", "model_action", "note"];
writeBlock(legendSheet, 0, 0, legendHeaders, analysis.data_legend);
styleDataSheet(legendSheet, legendHeaders, analysis.data_legend.length, {
  symbol: 10, displayed_meaning: 42, numeric_handling: 21, quality_status: 28, model_action: 64, note: 58,
}, 1);
legendSheet.getRange(`B2:F${analysis.data_legend.length + 1}`).format.wrapText = true;
legendSheet.getRange(`A2:F${analysis.data_legend.length + 1}`).format.rowHeight = 42;
addMainTable(legendSheet, legendHeaders, analysis.data_legend.length, "tblDataLegend");
const qualityHeaders = ["field", "status", "count", "raw_examples"];
writeBlock(legendSheet, 16, 0, qualityHeaders, analysis.quality_counts);
styleBlock(legendSheet, 16, 0, qualityHeaders, analysis.quality_counts.length, { field: 24, status: 30, count: 12, raw_examples: 36 });
addTableAt(legendSheet, `A17:D${17 + analysis.quality_counts.length}`, "tblQualityCounts");
legendSheet.getRange("A15:F15").merge();
legendSheet.getRange("A15").values = [["Frekuensi status pada CSV kemiskinan yang diimpor"]];
styleSection(legendSheet.getRange("A15:F15"));

// Inventory of obtained and candidate variables.
const inventoryRows = [
  ["poverty_rate_pct", "Persentase penduduk miskin Maret", "target utama", "%", "2015–2025; stable32 lengkap", "TERKUMPUL", "Poverty_Raw / Panel_March", "Target forecast provinsi.", "P0"],
  ["poor_population_thousand", "Jumlah penduduk miskin Maret", "target sekunder", "ribu orang", "2015–2025", "TERKUMPUL", "Poverty_Raw / Panel_March", "Menunjukkan beban absolut; sensitif ukuran penduduk.", "P0"],
  ["poverty_line_rp", "Garis kemiskinan Maret", "definisi target", "rupiah/kapita/bulan", "2017–2025", "PARSIAL", "Poverty_Raw / Panel_March", "Tahun yang sama berisiko leakage/endogeneity.", "P1"],
  ["tpt_aug_pct", "Tingkat Pengangguran Terbuka Agustus", "pasar kerja", "%", "2015–2025", "TERKUMPUL", "Statistik Indonesia", "Untuk target Maret t gunakan Agustus t-1.", "P0"],
  ["tpak_aug_pct", "Tingkat Partisipasi Angkatan Kerja Agustus", "pasar kerja", "%", "2015–2025", "TERKUMPUL", "Statistik Indonesia", "Gunakan lag t-1.", "P0"],
  ["hdi", "Indeks Pembangunan Manusia", "modal manusia", "indeks", "2015–2025", "TERKUMPUL", "Statistik Indonesia", "Flag perubahan metode seri disediakan.", "P0"],
  ["pdrb_pc_adhk2010_thousand_rp", "PDRB riil per kapita", "kapasitas ekonomi", "ribu rupiah", "2015–2025", "TERKUMPUL", "Statistik Indonesia", "Gunakan lag; angka terbaru dapat direvisi.", "P0"],
  ["pdrb_growth_pct", "Pertumbuhan PDRB riil", "siklus ekonomi", "%", "2015–2025", "TERKUMPUL", "Statistik Indonesia", "Gunakan lag dan dummy pandemi.", "P0"],
  ["sanitation_access_pct", "Akses sanitasi layak", "infrastruktur", "% rumah tangga", "2015–2025; 1 gap", "HAMPIR LENGKAP", "Statistik Indonesia", "Perubahan konsep seri diberi flag.", "P0"],
  ["drinking_water_access_pct", "Akses air minum layak", "infrastruktur", "% rumah tangga", "2015–2025; 1 gap", "HAMPIR LENGKAP", "Statistik Indonesia", "Gunakan lag t-1.", "P0"],
  ["food_share_pct", "Porsi pengeluaran makanan", "kerentanan konsumsi", "% pengeluaran", "Seri berlubang", "PARSIAL", "Statistik Indonesia", "Dekat dengan Susenas; gunakan deskriptif atau lag.", "P1"],
  ["gini_ratio", "Gini rasio", "ketimpangan", "rasio", "Sumber ditemukan", "DITUNDA", "Tabel Statistik BPS", "Prioritas untuk pertumbuhan inklusif.", "P0"],
  ["formal_employment_pct", "Proporsi tenaga kerja formal", "kualitas kerja", "% pekerja", "Sumber ditemukan", "DITUNDA", "Tabel Statistik BPS", "Pelengkap TPT.", "P1"],
  ["poverty_gap_p1", "Indeks kedalaman kemiskinan", "target tambahan", "indeks", "Sumber ditemukan", "DITUNDA", "Tabel Statistik BPS", "Mengukur jarak dari garis kemiskinan.", "P1"],
  ["poverty_severity_p2", "Indeks keparahan kemiskinan", "target tambahan", "indeks", "Sumber ditemukan", "DITUNDA", "Tabel Statistik BPS", "Ketimpangan di antara penduduk miskin.", "P1"],
  ["inflation_pct", "Inflasi pangan/umum", "harga", "% y/y", "Butuh harmonisasi kota–provinsi", "DESAIN ULANG", "BPS IHK", "Cakupan kota IHK berubah.", "P2"],
];
const inventoryHeaders = ["variable_code", "nama_indikator", "peran", "unit", "cakupan_diperoleh", "status", "sumber", "catatan_model", "prioritas"];
inventory.getRangeByIndexes(0, 0, inventoryRows.length + 1, inventoryHeaders.length).values = [inventoryHeaders, ...inventoryRows];
styleDataSheet(inventory, inventoryHeaders, inventoryRows.length, { variable_code: 32, nama_indikator: 38, peran: 20, unit: 23, cakupan_diperoleh: 28, status: 18, sumber: 30, catatan_model: 56, prioritas: 10 });
inventory.getRange(`A2:I${inventoryRows.length + 1}`).format.rowHeight = 38;
inventory.getRange(`B2:H${inventoryRows.length + 1}`).format.wrapText = true;
addMainTable(inventory, inventoryHeaders, inventoryRows.length, "tblInventaris");

// Province-year panel.
const panelHeaders = [
  "province", "year", "island_group", "territory_class", "stable32_model_flag", "covid_2020_dummy",
  "hdi_method_break_2021plus", "sanitation_concept_break_2016plus", "papua_boundary_break_2023plus",
  "poverty_line_rp", "poor_population_thousand", "poverty_rate_pct", "tpt_aug_pct", "tpak_aug_pct", "hdi",
  "pdrb_pc_adhk2010_thousand_rp", "pdrb_growth_pct", "pdrb_pc_growth_pct", "sanitation_access_pct",
  "drinking_water_access_pct", "food_exp_pc_month_rp", "nonfood_exp_pc_month_rp", "total_exp_pc_month_rp",
  "food_share_pct", "core_nonmissing_count", "core_complete_flag",
];
writeBlock(panelSheet, 0, 0, panelHeaders, data.panel_rows);
styleDataSheet(panelSheet, panelHeaders, data.panel_rows.length, { province: 25, year: 9, island_group: 20, territory_class: 30, stable32_model_flag: 17, poverty_line_rp: 18, poor_population_thousand: 21, poverty_rate_pct: 17, pdrb_pc_adhk2010_thousand_rp: 27, sanitation_access_pct: 20, drinking_water_access_pct: 22, food_exp_pc_month_rp: 21, nonfood_exp_pc_month_rp: 22, total_exp_pc_month_rp: 21, food_share_pct: 16, core_nonmissing_count: 20, core_complete_flag: 17 });
panelSheet.getRange(`J2:J${data.panel_rows.length + 1}`).format.numberFormat = "#,##0";
panelSheet.getRange(`K2:K${data.panel_rows.length + 1}`).format.numberFormat = "#,##0.00";
panelSheet.getRange(`L2:T${data.panel_rows.length + 1}`).format.numberFormat = "0.00";
panelSheet.getRange(`U2:W${data.panel_rows.length + 1}`).format.numberFormat = "#,##0";
panelSheet.getRange(`X2:X${data.panel_rows.length + 1}`).format.numberFormat = "0.00";
panelSheet.getRange(`L2:L${data.panel_rows.length + 1}`).conditionalFormats.add("colorScale", { criteria: [{ type: "lowestValue", color: COLORS.paleGreen }, { type: "percentile", value: 50, color: "#FFE699" }, { type: "highestValue", color: COLORS.paleRed }] });
addMainTable(panelSheet, panelHeaders, data.panel_rows.length, "tblPanelMarch");

// Leakage-safe lag panel used by the models.
const modelPanelHeaders = [
  "province", "year", "lag_year", "island_group", "poverty_rate_pct", "lag_poverty_rate_pct", "lag_tpt_aug_pct",
  "lag_tpak_aug_pct", "lag_hdi", "lag_pdrb_pc_adhk2010_thousand_rp", "lag_log_pdrb_pc", "lag_pdrb_growth_pct",
  "lag_pdrb_pc_growth_pct", "lag_sanitation_access_pct", "lag_drinking_water_access_pct", "lag_food_share_pct",
  "year_index", "covid_2020_dummy", "lag_pdrb_vintage_status", "model_row_status",
];
writeBlock(modelPanelSheet, 0, 0, modelPanelHeaders, analysis.model_panel_lag1);
styleDataSheet(modelPanelSheet, modelPanelHeaders, analysis.model_panel_lag1.length, { province: 25, year: 9, lag_year: 10, island_group: 20, poverty_rate_pct: 18, lag_poverty_rate_pct: 19, lag_pdrb_pc_adhk2010_thousand_rp: 29, lag_log_pdrb_pc: 18, lag_sanitation_access_pct: 23, lag_drinking_water_access_pct: 25, lag_pdrb_vintage_status: 30, model_row_status: 18 });
modelPanelSheet.getRange(`E2:P${analysis.model_panel_lag1.length + 1}`).format.numberFormat = "0.000";
addMainTable(modelPanelSheet, modelPanelHeaders, analysis.model_panel_lag1.length, "tblModelPanelLag1");

// EDA trends, ranks, and changes.
const trendHeaders = ["year", "province_n", "unweighted_mean_pct", "median_pct", "minimum_pct", "maximum_pct", "std_dev_pct"];
writeBlock(trendSheet, 0, 0, trendHeaders, analysis.eda_trend);
styleBlock(trendSheet, 0, 0, trendHeaders, analysis.eda_trend.length, { year: 10, province_n: 13, unweighted_mean_pct: 22, median_pct: 15, minimum_pct: 15, maximum_pct: 15, std_dev_pct: 15 });
addTableAt(trendSheet, `A1:G${analysis.eda_trend.length + 1}`, "tblEdaTrend");
const rankHeaders = ["province", "island_group", "poverty_rate_pct", "rank_high_to_low"];
writeBlock(trendSheet, 0, 9, rankHeaders, analysis.eda_rank_2025);
styleBlock(trendSheet, 0, 9, rankHeaders, analysis.eda_rank_2025.length, { province: 25, island_group: 20, poverty_rate_pct: 18, rank_high_to_low: 18 });
addTableAt(trendSheet, `J1:M${analysis.eda_rank_2025.length + 1}`, "tblRank2025");
const changeHeaders = ["province", "poverty_rate_2015_pct", "poverty_rate_2024_pct", "poverty_rate_2025_pct", "change_2015_2025_pp", "change_2024_2025_pp"];
writeBlock(trendSheet, 0, 15, changeHeaders, analysis.eda_changes);
styleBlock(trendSheet, 0, 15, changeHeaders, analysis.eda_changes.length, { province: 25, poverty_rate_2015_pct: 20, poverty_rate_2024_pct: 20, poverty_rate_2025_pct: 20, change_2015_2025_pp: 21, change_2024_2025_pp: 21 });
addTableAt(trendSheet, `P1:U${analysis.eda_changes.length + 1}`, "tblEdaChanges");
trendSheet.showGridLines = false;
trendSheet.freezePanes.freezeRows(1);
trendSheet.getRange("A34:C45").values = [["Tahun", "Mean P0", "Median P0"], ...Array.from({ length: 11 }, () => [null, null, null])];
styleHeader(trendSheet.getRange("A34:C34"));
trendSheet.getRange("A35").formulas = [["=A2"]];
trendSheet.getRange("A35:A45").fillDown();
trendSheet.getRange("B35").formulas = [["=C2"]];
trendSheet.getRange("B35:B45").fillDown();
trendSheet.getRange("C35").formulas = [["=D2"]];
trendSheet.getRange("C35:C45").fillDown();
trendSheet.getRange("B35:C45").format.numberFormat = "0.00";
const trendChart = trendSheet.charts.add("line", trendSheet.getRange("A34:C45"));
trendChart.setPosition("A15", "H31");
trendChart.title = "Sebaran P0 Provinsi Stable32";
trendChart.xAxis = { axisType: "textAxis" };
trendChart.yAxis = { numberFormatCode: "0.0" };
trendSheet.getRange(`C2:G${analysis.eda_trend.length + 1}`).format.numberFormat = "0.00";
trendSheet.getRange(`L2:L${analysis.eda_rank_2025.length + 1}`).format.numberFormat = "0.00";
trendSheet.getRange(`Q2:U${analysis.eda_changes.length + 1}`).format.numberFormat = "0.00";

// Driver associations and standardized ridge coefficients.
const corrHeaders = ["feature_code", "feature_name", "n_complete", "pooled_pearson_r", "within_province_r", "within_n", "interpretation_guardrail"];
writeBlock(driverSheet, 0, 0, corrHeaders, analysis.eda_correlations);
styleBlock(driverSheet, 0, 0, corrHeaders, analysis.eda_correlations.length, { feature_code: 32, feature_name: 34, n_complete: 13, pooled_pearson_r: 19, within_province_r: 20, within_n: 12, interpretation_guardrail: 52 });
addTableAt(driverSheet, `A1:G${analysis.eda_correlations.length + 1}`, "tblDriverCorr");
const coefHeaders = ["feature_code", "feature_name", "standardized_coefficient", "absolute_coefficient", "coefficient_sign", "interpretation_guardrail"];
writeBlock(driverSheet, 0, 9, coefHeaders, analysis.ridge_coefficients);
styleBlock(driverSheet, 0, 9, coefHeaders, analysis.ridge_coefficients.length, { feature_code: 32, feature_name: 34, standardized_coefficient: 23, absolute_coefficient: 20, coefficient_sign: 17, interpretation_guardrail: 56 });
addTableAt(driverSheet, `J1:O${analysis.ridge_coefficients.length + 1}`, "tblRidgeCoefficients");
driverSheet.showGridLines = false;
driverSheet.freezePanes.freezeRows(1);
driverSheet.getRange(`D2:E${analysis.eda_correlations.length + 1}`).format.numberFormat = "0.000";
driverSheet.getRange(`L2:M${analysis.ridge_coefficients.length + 1}`).format.numberFormat = "0.000";
driverSheet.getRange(`G2:G${analysis.eda_correlations.length + 1}`).format.wrapText = true;
driverSheet.getRange(`O2:O${analysis.ridge_coefficients.length + 1}`).format.wrapText = true;
driverSheet.getRange("R1:T11").values = [["Fitur", "Pooled r", "Within r"], ...Array.from({ length: 10 }, () => [null, null, null])];
styleHeader(driverSheet.getRange("R1:T1"));
driverSheet.getRange("R2").formulas = [["=B2"]];
driverSheet.getRange("R2:R11").fillDown();
driverSheet.getRange("S2").formulas = [["=D2"]];
driverSheet.getRange("S2:S11").fillDown();
driverSheet.getRange("T2").formulas = [["=E2"]];
driverSheet.getRange("T2:T11").fillDown();
driverSheet.getRange("S2:T11").format.numberFormat = "0.000";
const corrChart = driverSheet.charts.add("bar", driverSheet.getRange("R1:T11"));
corrChart.setPosition("A14", "H31");
corrChart.title = "Korelasi pooled vs dalam-provinsi";
corrChart.yAxis = { numberFormatCode: "0.0", min: -1, max: 1 };
const coefChart = driverSheet.charts.add("bar", driverSheet.getRange(`K1:L${analysis.ridge_coefficients.length + 1}`));
coefChart.setPosition("J14", "Q31");
coefChart.title = "Koefisien Ridge Terstandar";
coefChart.hasLegend = false;

// Rolling-origin benchmark.
const benchmarkHeaders = ["evaluation_scope", "test_year", "model_code", "model_name", "n", "mape_pct", "r2", "rmse", "mae", "mae_rank", "recommended_flag"];
writeBlock(benchmarkSheet, 0, 0, benchmarkHeaders, analysis.model_benchmark);
styleDataSheet(benchmarkSheet, benchmarkHeaders, analysis.model_benchmark.length, { evaluation_scope: 23, test_year: 12, model_code: 28, model_name: 42, n: 10, mape_pct: 14, r2: 12, rmse: 13, mae: 13, mae_rank: 12, recommended_flag: 18 });
benchmarkSheet.getRange(`F2:I${analysis.model_benchmark.length + 1}`).format.numberFormat = "0.000";
benchmarkSheet.getRange(`K2:K${analysis.model_benchmark.length + 1}`).conditionalFormats.add("cellIs", { operator: "equal", formula: 1, format: { fill: COLORS.paleGreen, font: { color: "#006100", bold: true } } });
addMainTable(benchmarkSheet, benchmarkHeaders, analysis.model_benchmark.length, "tblModelBenchmark");
benchmarkSheet.getRange("M1:N6").values = [["Model", "MAE"], ...overallBench.map((r) => [shortModelNames[r.model_code], r.mae])];
styleHeader(benchmarkSheet.getRange("M1:N1"));
benchmarkSheet.getRange("N2:N6").format.numberFormat = "0.000";
const benchmarkChart = benchmarkSheet.charts.add("bar", benchmarkSheet.getRange("M1:N6"));
benchmarkChart.setPosition("M8", "T24");
benchmarkChart.title = "MAE keseluruhan 2022–2025";
benchmarkChart.hasLegend = false;
benchmarkChart.yAxis = { numberFormatCode: "0.00", min: 0, max: 0.7 };

// Out-of-sample prediction audit trail.
const cvHeaders = ["province", "test_year", "model_code", "model_name", "actual_poverty_rate_pct", "predicted_poverty_rate_pct", "residual_actual_minus_pred", "absolute_error"];
writeBlock(cvSheet, 0, 0, cvHeaders, analysis.cv_predictions);
styleDataSheet(cvSheet, cvHeaders, analysis.cv_predictions.length, { province: 25, test_year: 12, model_code: 28, model_name: 42, actual_poverty_rate_pct: 23, predicted_poverty_rate_pct: 25, residual_actual_minus_pred: 28, absolute_error: 17 });
cvSheet.getRange(`E2:H${analysis.cv_predictions.length + 1}`).format.numberFormat = "0.000";
cvSheet.getRange(`H2:H${analysis.cv_predictions.length + 1}`).conditionalFormats.add("colorScale", { criteria: [{ type: "lowestValue", color: COLORS.paleGreen }, { type: "percentile", value: 50, color: "#FFE699" }, { type: "highestValue", color: COLORS.paleRed }] });
addMainTable(cvSheet, cvHeaders, analysis.cv_predictions.length, "tblCvPredictions");

// 2026 experimental forecast with all model outputs.
const forecastHeaders = ["province", "forecast_year", "actual_2025_pct", "recommended_model_code", "recommended_model_name", "forecast_poverty_rate_pct", "lower_80_pct", "upper_80_pct", "change_vs_2025_pp", "naive_lag1_pct", "province_linear_trend_pct", "ridge_lag_drivers_pct", "ridge_drivers_only_pct", "ensemble_naive_ridge_pct", "input_pdrb_vintage_status", "forecast_status", "forecast_rank_high_to_low"];
writeBlock(forecastSheet, 0, 0, forecastHeaders, analysis.forecast_2026);
styleDataSheet(forecastSheet, forecastHeaders, analysis.forecast_2026.length, { province: 25, forecast_year: 13, actual_2025_pct: 17, recommended_model_code: 29, recommended_model_name: 42, forecast_poverty_rate_pct: 24, lower_80_pct: 16, upper_80_pct: 16, change_vs_2025_pp: 19, province_linear_trend_pct: 25, ridge_lag_drivers_pct: 22, ridge_drivers_only_pct: 23, ensemble_naive_ridge_pct: 25, input_pdrb_vintage_status: 28, forecast_status: 26, forecast_rank_high_to_low: 23 });
forecastSheet.getRange(`C2:N${analysis.forecast_2026.length + 1}`).format.numberFormat = "0.00";
forecastSheet.getRange(`F2:F${analysis.forecast_2026.length + 1}`).conditionalFormats.add("colorScale", { criteria: [{ type: "lowestValue", color: COLORS.paleGreen }, { type: "percentile", value: 50, color: "#FFE699" }, { type: "highestValue", color: COLORS.paleRed }] });
addMainTable(forecastSheet, forecastHeaders, analysis.forecast_2026.length, "tblForecast2026");
forecastSheet.getRange("S1:T11").values = [["Provinsi", "Forecast P0 (%)"], ...Array.from({ length: 10 }, () => [null, null])];
styleHeader(forecastSheet.getRange("S1:T1"));
forecastSheet.getRange("S2").formulas = [["=A2"]];
forecastSheet.getRange("S2:S11").fillDown();
forecastSheet.getRange("T2").formulas = [["=F2"]];
forecastSheet.getRange("T2:T11").fillDown();
forecastSheet.getRange("T2:T11").format.numberFormat = "0.00";
const forecastChart = forecastSheet.charts.add("bar", forecastSheet.getRange("S1:T11"));
forecastChart.setPosition("S13", "Z30");
forecastChart.title = "10 Forecast P0 Tertinggi — 2026";
forecastChart.hasLegend = false;

// Raw poverty data with symbol/status preservation.
const povertyHeaders = [
  "province", "year", "semester", "geo_level", "poverty_line_rp", "poverty_line_raw", "poverty_line_status",
  "poor_population_thousand", "poor_population_raw", "poor_population_status", "poverty_rate_pct", "poverty_rate_raw",
  "poverty_rate_status", "source_file", "source_row", "validation_flag", "validation_note",
];
writeBlock(povertySheet, 0, 0, povertyHeaders, data.poverty_raw);
styleDataSheet(povertySheet, povertyHeaders, data.poverty_raw.length, { province: 25, year: 9, semester: 13, geo_level: 12, poverty_line_rp: 18, poverty_line_raw: 20, poverty_line_status: 29, poor_population_thousand: 23, poor_population_raw: 21, poor_population_status: 29, poverty_rate_pct: 18, poverty_rate_raw: 18, poverty_rate_status: 29, source_file: 58, source_row: 12, validation_flag: 28, validation_note: 70 });
povertySheet.getRange(`E2:E${data.poverty_raw.length + 1}`).format.numberFormat = "#,##0";
povertySheet.getRange(`H2:H${data.poverty_raw.length + 1}`).format.numberFormat = "#,##0.00";
povertySheet.getRange(`K2:K${data.poverty_raw.length + 1}`).format.numberFormat = "0.00";
povertySheet.getRange(`G2:G${data.poverty_raw.length + 1}`).conditionalFormats.add("containsText", { text: "unavailable", format: { fill: COLORS.paleOrange, font: { color: "#9C5700" } } });
povertySheet.getRange(`J2:J${data.poverty_raw.length + 1}`).conditionalFormats.add("containsText", { text: "unavailable", format: { fill: COLORS.paleOrange, font: { color: "#9C5700" } } });
povertySheet.getRange(`M2:M${data.poverty_raw.length + 1}`).conditionalFormats.add("containsText", { text: "unavailable", format: { fill: COLORS.paleOrange, font: { color: "#9C5700" } } });
povertySheet.getRange(`P2:P${data.poverty_raw.length + 1}`).conditionalFormats.add("containsText", { text: "ERROR", format: { fill: COLORS.paleRed, font: { color: "#9C0006", bold: true } } });
povertySheet.getRange(`N2:Q${data.poverty_raw.length + 1}`).format.wrapText = true;
addMainTable(povertySheet, povertyHeaders, data.poverty_raw.length, "tblPovertyRaw");

// Long-form indicators with provenance.
const indicatorHeaders = ["province", "year", "variable_code", "value", "unit", "publication", "table", "pdf_page", "source_url", "note"];
writeBlock(indicatorsSheet, 0, 0, indicatorHeaders, data.indicators_long);
styleDataSheet(indicatorsSheet, indicatorHeaders, data.indicators_long.length, { province: 25, year: 9, variable_code: 34, value: 16, unit: 24, publication: 25, table: 20, pdf_page: 12, source_url: 68, note: 58 });
indicatorsSheet.getRange(`D2:D${data.indicators_long.length + 1}`).format.numberFormat = "#,##0.0000";
indicatorsSheet.getRange(`I2:J${data.indicators_long.length + 1}`).format.wrapText = true;
addMainTable(indicatorsSheet, indicatorHeaders, data.indicators_long.length, "tblIndicatorsLong");

// Formula-backed coverage QC against Panel_March.
const coverageHeaders = ["year", "variable_code", "nonmissing_stable32", "expected_stable32", "coverage_pct", "status", "panel_column"];
const columnMap = { poverty_line_rp: "J", poor_population_thousand: "K", poverty_rate_pct: "L", tpt_aug_pct: "M", tpak_aug_pct: "N", hdi: "O", pdrb_pc_adhk2010_thousand_rp: "P", pdrb_growth_pct: "Q", pdrb_pc_growth_pct: "R", sanitation_access_pct: "S", drinking_water_access_pct: "T", food_exp_pc_month_rp: "U", nonfood_exp_pc_month_rp: "V", total_exp_pc_month_rp: "W", food_share_pct: "X" };
const coverageRows = data.coverage.map((r) => ({ ...r, panel_column: columnMap[r.variable_code] }));
writeBlock(qcSheet, 0, 0, coverageHeaders, coverageRows);
styleDataSheet(qcSheet, coverageHeaders, coverageRows.length, { year: 10, variable_code: 38, nonmissing_stable32: 22, expected_stable32: 18, coverage_pct: 16, status: 14, panel_column: 14 });
for (let i = 0; i < coverageRows.length; i++) {
  const row = i + 2;
  const variableCol = coverageRows[i].panel_column;
  if (coverageRows[i].variable_code === "food_share_pct") {
    qcSheet.getRange(`C${row}`).formulas = [[`=COUNTIFS(Panel_March!$B$2:$B$419,A${row},Panel_March!$E$2:$E$419,1,Panel_March!$U$2:$U$419,\">0\",Panel_March!$W$2:$W$419,\">0\")`]];
  } else {
    qcSheet.getRange(`C${row}`).formulas = [[`=COUNTIFS(Panel_March!$B$2:$B$419,A${row},Panel_March!$E$2:$E$419,1,Panel_March!$${variableCol}$2:$${variableCol}$419,\"<>\")`]];
  }
  qcSheet.getRange(`D${row}`).values = [[32]];
  qcSheet.getRange(`E${row}`).formulas = [[`=C${row}/D${row}`]];
  qcSheet.getRange(`F${row}`).formulas = [[`=IF(E${row}=1,\"Lengkap\",IF(C${row}=0,\"Kosong\",\"Parsial\"))`]];
}
qcSheet.getRange(`E2:E${coverageRows.length + 1}`).format.numberFormat = "0.0%";
qcSheet.getRange(`E2:E${coverageRows.length + 1}`).conditionalFormats.add("colorScale", { criteria: [{ type: "lowestValue", color: COLORS.paleRed }, { type: "percentile", value: 50, color: "#FFE699" }, { type: "highestValue", color: COLORS.paleGreen }] });
addMainTable(qcSheet, coverageHeaders, coverageRows.length, "tblCoverageQC");

// Source registry.
const sourceRows = [
  ["poverty_csv", "Jumlah dan Persentase Penduduk Miskin Menurut Provinsi", "2015–2025", "11 CSV lokal", "data/raw/poverty/Jumlah dan Persentase Penduduk Miskin Menurut Provinsi, YYYY.csv", "https://www.bps.go.id/id/statistics-table/3/UkVkWGJVZFNWakl6VWxKVFQwWjVWeTlSZDNabVFUMDkjMw==/jumlah-dan-persentase-penduduk-miskin-menurut-provinsi--2023.html?year=2025", "diimpor", "Maret dan September; 2023 tanpa September"],
  ["statindo2016", "Statistik Indonesia 2016", "2011–2015", "PDF BPS", "data/raw/bps_publications/Statistik_Indonesia_2016.pdf", "https://www.bps.go.id/id/publication/2016/06/29/7aa1e8f93b4148234a9b4bc3/statistik-indonesia-2016.html", "diekstrak", "Pasar kerja, sanitasi, air, pengeluaran"],
  ["statindo2019", "Statistik Indonesia 2019", "2015–2018", "PDF BPS", "data/raw/bps_publications/Statistik_Indonesia_2019.pdf", "https://www.bps.go.id/id/publication/2019/07/04/daac1ba18cae1e90706ee58a/statistik-indonesia-2019.html", "diekstrak", "Pasar kerja, PDRB, pengeluaran"],
  ["statindo2021", "Statistik Indonesia 2021", "2015–2020", "PDF BPS", "data/raw/bps_publications/Statistik_Indonesia_2021.pdf", "https://www.bps.go.id/id/publication/2021/02/26/938316574c78772f27e9b477/statistik-indonesia-2021.html", "diekstrak", "Pasar kerja, IPM, layanan dasar, PDRB"],
  ["statindo2024", "Statistik Indonesia 2024", "2020–2023", "PDF BPS", "data/raw/bps_publications/Statistik_Indonesia_2024.pdf", "https://www.bps.go.id/id/publication/2024/02/28/c1bacde03256343b2bf769b0/statistik-indonesia-2024.html", "diekstrak", "Pasar kerja, PDRB, pengeluaran"],
  ["statindo2026", "Statistik Indonesia 2026", "2021–2025", "PDF BPS", "data/raw/bps_publications/Statistik_Indonesia_2026.pdf", "https://www.bps.go.id/id/publication/2026/02/27/a43f03f45543dc4e9942f44c/statistik-indonesia-2026.html", "diekstrak", "Cross-check kemiskinan nasional dan indikator terbaru"],
  ["gini", "Gini Rasio", "kandidat", "Tabel Statistik BPS", null, "https://www.bps.go.id/id/statistics-table/2/OTgjMg%3D%3D/gini-rasio", "ditunda", "Prioritas tinggi tahap pengayaan"],
  ["p1", "Indeks Kedalaman Kemiskinan (P1)", "kandidat", "Tabel Statistik BPS", null, "https://www.bps.go.id/id/statistics-table/2/NTAzIzI%3D/indeks-kedalaman-kemiskinan--p1--menurut-provinsi-dan-daerah.html", "ditunda", "Target tambahan"],
  ["p2", "Indeks Keparahan Kemiskinan (P2)", "kandidat", "Tabel Statistik BPS", null, "https://www.bps.go.id/id/statistics-table/2/NTA0IzI%3D/indeks-keparahan-kemiskinan--p2--menurut-provinsi-dan-daerah--persen-.html", "ditunda", "Target tambahan"],
  ["formal", "Persentase Tenaga Kerja Formal", "kandidat", "Tabel Statistik BPS", null, "https://www.bps.go.id/id/statistics-table/2/MTE2OCMy/persentase-tenaga-kerja-formal-menurut-provinsi.html", "ditunda", "Kualitas pekerjaan"],
];
const sourceHeaders = ["source_id", "title", "period", "source_type", "local_file", "url", "status", "notes"];
sourcesSheet.getRangeByIndexes(0, 0, sourceRows.length + 1, sourceHeaders.length).values = [sourceHeaders, ...sourceRows];
styleDataSheet(sourcesSheet, sourceHeaders, sourceRows.length, { source_id: 18, title: 46, period: 16, source_type: 20, local_file: 62, url: 90, status: 16, notes: 52 });
sourcesSheet.getRange(`E2:H${sourceRows.length + 1}`).format.wrapText = true;
sourcesSheet.getRange(`A2:H${sourceRows.length + 1}`).format.rowHeight = 45;
addMainTable(sourcesSheet, sourceHeaders, sourceRows.length, "tblSources");

await fs.mkdir(PREVIEW_DIR, { recursive: true });
const overview = await wb.inspect({ kind: "workbook,sheet,table", maxChars: 12000, tableMaxRows: 2, tableMaxCols: 6 });
console.log("WORKBOOK_OVERVIEW\n" + overview.ndjson);

const previewRanges = {
  Dashboard_Seed: "A1:N49", Data_Legend: "A1:F38", Inventaris: "A1:I17", Panel_March: "A1:Z26",
  Model_Panel_Lag1: "A1:T26", EDA_Tren: "A1:U45", EDA_Driver: "A1:T31", Model_Benchmark: "A1:T26",
  CV_Predictions: "A1:H28", Forecast_2026: "A1:Z33", Poverty_Raw: "A1:Q28", Indicators_Long: "A1:J28",
  QC_Coverage: "A1:G32", Sources: "A1:H11",
};
for (const [sheetName, range] of Object.entries(previewRanges)) {
  const region = await wb.inspect({ kind: "region", sheetId: sheetName, range, maxChars: 3500 });
  console.log(`REGION_${sheetName}\n${region.ndjson}`);
  const preview = await wb.render({ sheetName, range, scale: 0.75, format: "png" });
  await fs.writeFile(path.join(PREVIEW_DIR, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 5000 });
console.log("FORMULA_ERROR_SCAN\n" + errors.ndjson);

const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(OUTPUT_PATH);
console.log(JSON.stringify({ output: OUTPUT_PATH, previews: PREVIEW_DIR, recommended_model: analysis.methodology.recommended_model_name }));
