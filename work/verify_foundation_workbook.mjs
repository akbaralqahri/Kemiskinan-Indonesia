import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const file = new URL("../output/spreadsheets/poverty_analysis_2015_2026/analisis_dan_forecast_kemiskinan_indonesia_2015_2026.xlsx", import.meta.url).pathname.replace(/^\/(.:)/, "$1");
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(file));

const sheets = await wb.inspect({ kind: "sheet", include: "id,name", maxChars: 5000 });
const dashboard = await wb.inspect({ kind: "region", sheetId: "Dashboard_Seed", range: "A1:N16", maxChars: 5000 });
const benchmark = await wb.inspect({ kind: "region", sheetId: "Model_Benchmark", range: "A1:K6", maxChars: 4000 });
const forecast = await wb.inspect({ kind: "region", sheetId: "Forecast_2026", range: "A1:Q6", maxChars: 5000 });
const legend = await wb.inspect({ kind: "region", sheetId: "Data_Legend", range: "A1:F13", maxChars: 5000 });
const qc = await wb.inspect({ kind: "region", sheetId: "QC_Coverage", range: "A1:G32", maxChars: 5000 });
const errors = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  maxChars: 3000,
});

console.log("SHEETS\n" + sheets.ndjson);
console.log("DASHBOARD_CHECK\n" + dashboard.ndjson);
console.log("BENCHMARK_CHECK\n" + benchmark.ndjson);
console.log("FORECAST_CHECK\n" + forecast.ndjson);
console.log("LEGEND_CHECK\n" + legend.ndjson);
console.log("QC_CHECK\n" + qc.ndjson);
console.log("ERROR_CHECK\n" + errors.ndjson);
