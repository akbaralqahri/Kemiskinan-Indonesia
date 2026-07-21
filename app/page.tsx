"use client";

import { useEffect, useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import dashboardData from "./data/dashboard-data.json";

type Tab = "overview" | "drivers" | "forecast" | "methodology";
type MetricCode =
  | "poverty_rate_pct"
  | "poor_population_thousand"
  | "hdi"
  | "tpt_aug_pct"
  | "pdrb_pc_adhk2010_thousand_rp"
  | "sanitation_access_pct"
  | "drinking_water_access_pct";

type PanelRow = {
  province: string;
  year: number;
  island_group: string;
  territory_class: string;
  stable32_model_flag: number;
  poor_population_thousand: number | null;
  poverty_rate_pct: number | null;
  tpt_aug_pct: number | null;
  tpak_aug_pct: number | null;
  hdi: number | null;
  pdrb_pc_adhk2010_thousand_rp: number | null;
  pdrb_growth_pct: number | null;
  sanitation_access_pct: number | null;
  drinking_water_access_pct: number | null;
  food_share_pct: number | null;
};

type ForecastRow = {
  province: string;
  forecast_year: number;
  actual_2025_pct: number;
  recommended_model_code: string;
  recommended_model_name: string;
  forecast_poverty_rate_pct: number;
  lower_80_pct: number;
  upper_80_pct: number;
  change_vs_2025_pp: number;
  naive_lag1_pct: number;
  province_linear_trend_pct: number;
  ridge_lag_drivers_pct: number;
  ridge_drivers_only_pct: number;
  ensemble_naive_ridge_pct: number;
  input_pdrb_vintage_status: string;
  forecast_status: string;
  forecast_rank_high_to_low: number;
};

type BenchmarkRow = {
  model_code: string;
  model_name: string;
  n: number;
  mape_pct: number;
  r2: number;
  rmse: number;
  mae: number;
  mae_rank: number;
};

type CvRow = {
  province: string;
  test_year: number;
  actual_poverty_rate_pct: number;
  predicted_poverty_rate_pct: number;
  residual_actual_minus_pred: number;
  absolute_error: number;
};

type GeoFeature = {
  type: "Feature";
  properties: { shapeName?: string };
  geometry:
    | { type: "Polygon"; coordinates: number[][][] }
    | { type: "MultiPolygon"; coordinates: number[][][][] };
};

type GeoCollection = {
  type: "FeatureCollection";
  features: GeoFeature[];
};

const DATA = dashboardData as unknown as {
  meta: Record<string, string | number>;
  national_trend: { year: number; poverty_rate_pct: number; poor_population_thousand: number }[];
  panel: PanelRow[];
  forecast: ForecastRow[];
  benchmark: BenchmarkRow[];
  cv_predictions: CvRow[];
  correlations: {
    feature_code: string;
    feature_name: string;
    n_complete: number;
    pooled_pearson_r: number;
    within_province_r: number;
  }[];
  coefficients: {
    feature_code: string;
    feature_name: string;
    standardized_coefficient: number;
    absolute_coefficient: number;
    coefficient_sign: string;
  }[];
  data_legend: {
    symbol: string;
    displayed_meaning: string;
    numeric_handling: string;
    quality_status: string;
    model_action: string;
    note: string;
  }[];
  sources: { label: string; url: string }[];
};

const METRICS: Record<MetricCode, { label: string; short: string; unit: string; decimals: number }> = {
  poverty_rate_pct: { label: "Persentase penduduk miskin", short: "P0", unit: "%", decimals: 2 },
  poor_population_thousand: { label: "Jumlah penduduk miskin", short: "Penduduk miskin", unit: "ribu", decimals: 0 },
  hdi: { label: "Indeks Pembangunan Manusia", short: "IPM", unit: "poin", decimals: 2 },
  tpt_aug_pct: { label: "Tingkat Pengangguran Terbuka", short: "TPT", unit: "%", decimals: 2 },
  pdrb_pc_adhk2010_thousand_rp: { label: "PDRB riil per kapita", short: "PDRB/kapita", unit: "ribu Rp", decimals: 0 },
  sanitation_access_pct: { label: "Akses sanitasi layak", short: "Sanitasi", unit: "%", decimals: 2 },
  drinking_water_access_pct: { label: "Akses air minum layak", short: "Air minum", unit: "%", decimals: 2 },
};

const DRIVER_OPTIONS = [
  { code: "hdi", label: "IPM" },
  { code: "pdrb_pc_adhk2010_thousand_rp", label: "PDRB riil per kapita" },
  { code: "tpt_aug_pct", label: "TPT Agustus" },
  { code: "sanitation_access_pct", label: "Sanitasi layak" },
  { code: "drinking_water_access_pct", label: "Air minum layak" },
  { code: "food_share_pct", label: "Porsi pengeluaran makanan" },
] as const;

const GEO_NAME_MAP: Record<string, string> = {
  "West Nusa Tenggara": "Nusa Tenggara Barat",
  "East Nusa Tenggara": "Nusa Tenggara Timur",
  "Central Java": "Jawa Tengah",
  "West Java": "Jawa Barat",
  "East Java": "Jawa Timur",
  "Central Kalimantan": "Kalimantan Tengah",
  "South Kalimantan": "Kalimantan Selatan",
  "West Kalimantan": "Kalimantan Barat",
  "East Kalimantan": "Kalimantan Timur",
  "North Kalimantan": "Kalimantan Utara",
  "Central Sulawesi": "Sulawesi Tengah",
  "North Sulawesi": "Sulawesi Utara",
  "South Sulawesi": "Sulawesi Selatan",
  "Southeast Sulawesi": "Sulawesi Tenggara",
  "West Sulawesi": "Sulawesi Barat",
  "North Maluku": "Maluku Utara",
  "West Sumatra": "Sumatera Barat",
  "South Sumatra": "Sumatera Selatan",
  "North Sumatra": "Sumatera Utara",
  "Bangka-Belitung Islands": "Kepulauan Bangka Belitung",
  "Riau Islands": "Kepulauan Riau",
  "West Papua": "Papua Barat",
  "Special Region of Yogyakarta": "DI Yogyakarta",
  "Jakarta Special Capital Region": "DKI Jakarta",
};

const NAV: { id: Tab; label: string; kicker: string }[] = [
  { id: "overview", label: "Ringkasan", kicker: "Tren & wilayah" },
  { id: "drivers", label: "Faktor terkait", kicker: "Eksplorasi hubungan" },
  { id: "forecast", label: "Prediksi 2026", kicker: "Model & interval" },
  { id: "methodology", label: "Metodologi", kicker: "Mutu & sumber" },
];

function signedRingArea(ring: number[][]) {
  return ring.reduce((sum, point, index) => {
    const next = ring[(index + 1) % ring.length];
    return sum + point[0] * next[1] - next[0] * point[1];
  }, 0) / 2;
}

function rewindPolygonForD3(polygon: number[][][]) {
  return polygon.map((ring, index) => {
    const area = signedRingArea(ring);
    const mustReverse = index === 0 ? area > 0 : area < 0;
    return mustReverse ? [...ring].reverse() : ring;
  });
}

function rewindGeoJsonForD3(collection: GeoCollection): GeoCollection {
  return {
    ...collection,
    features: collection.features.map((feature) => ({
      ...feature,
      geometry: feature.geometry.type === "Polygon"
        ? { ...feature.geometry, coordinates: rewindPolygonForD3(feature.geometry.coordinates) }
        : { ...feature.geometry, coordinates: feature.geometry.coordinates.map(rewindPolygonForD3) },
    })),
  };
}

function fmt(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  const sign = value < 0 ? "-" : "";
  const [integer, decimal] = Math.abs(value).toFixed(digits).split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${sign}${grouped}${digits > 0 ? `,${decimal}` : ""}`;
}

function signed(value: number, digits = 2) {
  return `${value > 0 ? "+" : ""}${fmt(value, digits)}`;
}

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
}

function pearson(x: number[], y: number[]) {
  if (x.length < 3 || x.length !== y.length) return 0;
  const mx = mean(x);
  const my = mean(y);
  let numerator = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < x.length; i += 1) {
    const a = x[i] - mx;
    const b = y[i] - my;
    numerator += a * b;
    dx += a * a;
    dy += b * b;
  }
  return dx && dy ? numerator / Math.sqrt(dx * dy) : 0;
}

function MiniArrow({ value }: { value: number }) {
  const improving = value < 0;
  return (
    <span className={improving ? "delta improving" : value > 0 ? "delta worsening" : "delta neutral"}>
      {improving ? "↓" : value > 0 ? "↑" : "→"} {signed(value)} pp
    </span>
  );
}

function StatCard({ eyebrow, value, unit, note, tone = "default" }: { eyebrow: string; value: string; unit?: string; note: React.ReactNode; tone?: "default" | "accent" | "dark" }) {
  return (
    <article className={`stat-card ${tone}`}>
      <p className="stat-eyebrow">{eyebrow}</p>
      <p className="stat-value">{value} {unit && <span>{unit}</span>}</p>
      <div className="stat-note">{note}</div>
    </article>
  );
}

function NationalTrendChart({ selectedProvince }: { selectedProvince: string }) {
  const width = 760;
  const height = 286;
  const pad = { left: 48, right: 52, top: 22, bottom: 36 };
  const national = DATA.national_trend;
  const province = DATA.panel.filter((row) => row.province === selectedProvince && row.poverty_rate_pct !== null).sort((a, b) => a.year - b.year);
  const allValues = [...national.map((d) => d.poverty_rate_pct), ...province.map((d) => d.poverty_rate_pct as number)];
  const minY = Math.max(0, Math.floor(Math.min(...allValues) - 1));
  const maxY = Math.ceil(Math.max(...allValues) + 1);
  const x = (year: number) => pad.left + ((year - 2015) / 10) * (width - pad.left - pad.right);
  const y = (value: number) => pad.top + ((maxY - value) / (maxY - minY || 1)) * (height - pad.top - pad.bottom);
  const points = (rows: { year: number; value: number }[]) => rows.map((d) => `${x(d.year)},${y(d.value)}`).join(" ");
  const nationalRows = national.map((d) => ({ year: d.year, value: d.poverty_rate_pct }));
  const provinceRows = province.map((d) => ({ year: d.year, value: d.poverty_rate_pct as number }));
  const ticks = [minY, minY + (maxY - minY) / 2, maxY];

  return (
    <div className="chart-wrap">
      <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="trend-title trend-desc">
        <title id="trend-title">{`Tren kemiskinan nasional dan ${selectedProvince}, 2015 sampai 2025`}</title>
        <desc id="trend-desc">Garis terracotta menunjukkan nasional. Garis navy menunjukkan provinsi terpilih.</desc>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} className="grid-line" />
            <text x={pad.left - 10} y={y(tick) + 4} textAnchor="end" className="axis-label">{fmt(tick, 1)}%</text>
          </g>
        ))}
        {national.filter((_, index) => index % 2 === 0 || index === national.length - 1).map((d) => (
          <text key={d.year} x={x(d.year)} y={height - 10} textAnchor="middle" className="axis-label">{d.year}</text>
        ))}
        <polyline points={points(nationalRows)} className="trend-national" />
        <polyline points={points(provinceRows)} className="trend-province" />
        {nationalRows.map((d) => <circle key={`n-${d.year}`} cx={x(d.year)} cy={y(d.value)} r="3.5" className="point-national"><title>{`${d.year}: ${fmt(d.value)}%`}</title></circle>)}
        {provinceRows.map((d) => <circle key={`p-${d.year}`} cx={x(d.year)} cy={y(d.value)} r="3.5" className="point-province"><title>{`${selectedProvince} ${d.year}: ${fmt(d.value)}%`}</title></circle>)}
        <text x={width - pad.right + 8} y={y(nationalRows.at(-1)?.value ?? 0) + 4} className="end-label national">Nasional</text>
        <text x={width - pad.right + 8} y={y(provinceRows.at(-1)?.value ?? 0) + 4} className="end-label province">{selectedProvince}</text>
      </svg>
    </div>
  );
}

function IndonesiaMap({ year, metric, selectedProvince, onSelect }: { year: number; metric: MetricCode; selectedProvince: string; onSelect: (province: string) => void }) {
  const [geo, setGeo] = useState<GeoCollection | null>(null);
  const rows = useMemo(() => DATA.panel.filter((row) => row.year === year), [year]);
  const rowByProvince = useMemo(() => new Map(rows.map((row) => [row.province, row])), [rows]);
  const values = rows.map((row) => row[metric]).filter((value): value is number => typeof value === "number");
  const low = Math.min(...values);
  const high = Math.max(...values);
  const colors = ["#dce5de", "#b9c9bd", "#91aa99", "#c99070", "#b55e3f"];

  useEffect(() => {
    fetch("/data/indonesia-adm1-legacy.geojson")
      .then((response) => response.json())
      .then((payload: GeoCollection) => setGeo(rewindGeoJsonForD3(payload)))
      .catch(() => setGeo(null));
  }, []);

  const paths = useMemo(() => {
    if (!geo) return [];
    const projection = geoMercator().fitExtent([[18, 20], [882, 414]], geo as never);
    const makePath = geoPath(projection);
    return geo.features.map((feature) => ({ feature, d: makePath(feature as never) ?? "" }));
  }, [geo]);

  const fillFor = (province: string) => {
    if (year >= 2023 && (province === "Papua" || province === "Papua Barat")) return "#e8e1d4";
    const value = rowByProvince.get(province)?.[metric];
    if (typeof value !== "number") return "#e8e1d4";
    const ratio = (value - low) / (high - low || 1);
    return colors[Math.min(colors.length - 1, Math.floor(ratio * colors.length))];
  };

  return (
    <div className="map-stage">
      {!geo && <div className="map-loading">Memuat batas wilayah…</div>}
      {geo && (
        <svg viewBox="0 0 900 440" role="img" aria-labelledby="map-title map-desc" className="map-svg">
          <title id="map-title">{`Peta ${METRICS[metric].label} menurut provinsi, ${year}`}</title>
          <desc id="map-desc">Semakin terracotta warnanya, semakin tinggi nilainya. Peta memakai geometri 34 provinsi historis.</desc>
          {paths.map(({ feature, d }) => {
            const englishName = feature.properties.shapeName ?? "";
            const province = GEO_NAME_MAP[englishName] ?? englishName;
            const value = rowByProvince.get(province)?.[metric];
            const uncertainPapua = year >= 2023 && (province === "Papua" || province === "Papua Barat");
            return (
              <path
                key={englishName}
                d={d}
                className={`province-shape ${province === selectedProvince ? "selected" : ""}`}
                fill={fillFor(province)}
                onClick={() => !uncertainPapua && rowByProvince.has(province) && onSelect(province)}
              >
                <title>{`${province}: ${uncertainPapua ? "lihat tabel pemekaran" : `${fmt(value as number, METRICS[metric].decimals)} ${METRICS[metric].unit}`}`}</title>
              </path>
            );
          })}
        </svg>
      )}
      <div className="map-legend" aria-label="Legenda warna peta">
        <span>Rendah</span>{colors.map((color) => <i key={color} style={{ background: color }} />)}<span>Tinggi</span>
      </div>
      <p className="map-note">Batas peta: 34 provinsi historis. Enam wilayah Papua 2025 tersedia lengkap pada peringkat, tanpa dipaksakan ke geometri lama.</p>
    </div>
  );
}

function Ranking({ rows, metric, selectedProvince, onSelect }: { rows: PanelRow[]; metric: MetricCode; selectedProvince: string; onSelect: (province: string) => void }) {
  const definition = METRICS[metric];
  const sorted = [...rows].filter((row) => typeof row[metric] === "number").sort((a, b) => (b[metric] as number) - (a[metric] as number));
  const max = Math.max(...sorted.map((row) => row[metric] as number));
  return (
    <div className="ranking-list" aria-label={`Peringkat ${definition.label}`}>
      {sorted.map((row, index) => (
        <button key={row.province} className={`ranking-row ${row.province === selectedProvince ? "active" : ""}`} onClick={() => onSelect(row.province)}>
          <span className="rank-number">{String(index + 1).padStart(2, "0")}</span>
          <span className="rank-main">
            <span className="rank-name">{row.province}</span>
            <span className="rank-track"><i style={{ width: `${((row[metric] as number) / max) * 100}%` }} /></span>
          </span>
          <span className="rank-value">{fmt(row[metric] as number, definition.decimals)} <small>{definition.unit}</small></span>
        </button>
      ))}
    </div>
  );
}

function ScatterPlot({ year, driver, selectedProvince, onSelect }: { year: number; driver: typeof DRIVER_OPTIONS[number]["code"]; selectedProvince: string; onSelect: (province: string) => void }) {
  const rows = DATA.panel.filter((row) => row.year === year && typeof row[driver] === "number" && typeof row.poverty_rate_pct === "number");
  const xs = rows.map((row) => row[driver] as number);
  const ys = rows.map((row) => row.poverty_rate_pct as number);
  const width = 720;
  const height = 400;
  const pad = { left: 62, right: 30, top: 24, bottom: 52 };
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.max(0, Math.floor(Math.min(...ys) - 1));
  const maxY = Math.ceil(Math.max(...ys) + 1);
  const x = (value: number) => pad.left + ((value - minX) / (maxX - minX || 1)) * (width - pad.left - pad.right);
  const y = (value: number) => pad.top + ((maxY - value) / (maxY - minY || 1)) * (height - pad.top - pad.bottom);
  const xTicks = [minX, minX + (maxX - minX) / 2, maxX];
  const yTicks = [minY, minY + (maxY - minY) / 2, maxY];
  const driverLabel = DRIVER_OPTIONS.find((option) => option.code === driver)?.label ?? driver;
  return (
    <div className="chart-wrap scatter-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="scatter-title scatter-desc" className="scatter-chart">
        <title id="scatter-title">{`Hubungan ${driverLabel} dan kemiskinan pada ${year}`}</title>
        <desc id="scatter-desc">Setiap titik adalah satu provinsi. Titik yang dipilih diberi lingkar luar.</desc>
        {yTicks.map((tick) => <g key={`y-${tick}`}><line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} className="grid-line" /><text x={pad.left - 10} y={y(tick) + 4} textAnchor="end" className="axis-label">{fmt(tick, 1)}%</text></g>)}
        {xTicks.map((tick) => <g key={`x-${tick}`}><line y1={pad.top} y2={height - pad.bottom} x1={x(tick)} x2={x(tick)} className="grid-line" /><text x={x(tick)} y={height - 18} textAnchor="middle" className="axis-label">{fmt(tick, driver === "pdrb_pc_adhk2010_thousand_rp" ? 0 : 1)}</text></g>)}
        {rows.map((row) => (
          <circle
            key={row.province}
            cx={x(row[driver] as number)}
            cy={y(row.poverty_rate_pct as number)}
            r={row.province === selectedProvince ? 8 : 5}
            className={`scatter-point ${row.province === selectedProvince ? "selected" : ""}`}
            onClick={() => onSelect(row.province)}
          >
            <title>{`${row.province}: ${driverLabel} ${fmt(row[driver] as number)}; P0 ${fmt(row.poverty_rate_pct)}%`}</title>
          </circle>
        ))}
        <text x={(pad.left + width - pad.right) / 2} y={height - 2} textAnchor="middle" className="axis-title">{driverLabel}</text>
        <text transform={`translate(15 ${(pad.top + height - pad.bottom) / 2}) rotate(-90)`} textAnchor="middle" className="axis-title">Kemiskinan (%)</text>
      </svg>
    </div>
  );
}

function ForecastIntervals({ rows, selectedProvince, onSelect }: { rows: ForecastRow[]; selectedProvince: string; onSelect: (province: string) => void }) {
  const max = Math.max(...rows.map((row) => row.upper_80_pct));
  return (
    <div className="interval-list">
      {rows.map((row) => (
        <button key={row.province} className={`interval-row ${row.province === selectedProvince ? "active" : ""}`} onClick={() => onSelect(row.province)}>
          <span className="interval-name"><b>{String(row.forecast_rank_high_to_low).padStart(2, "0")}</b>{row.province}</span>
          <span className="interval-track">
            <i className="interval-range" style={{ left: `${(row.lower_80_pct / max) * 100}%`, width: `${((row.upper_80_pct - row.lower_80_pct) / max) * 100}%` }} />
            <i className="interval-point" style={{ left: `${(row.forecast_poverty_rate_pct / max) * 100}%` }} />
          </span>
          <span className="interval-value">{fmt(row.forecast_poverty_rate_pct)}%</span>
        </button>
      ))}
    </div>
  );
}

function ModelComparison({ row }: { row: ForecastRow }) {
  const models = [
    ["Naive lag-1", row.naive_lag1_pct],
    ["Tren provinsi", row.province_linear_trend_pct],
    ["Ridge lag + driver", row.ridge_lag_drivers_pct],
    ["Ridge driver", row.ridge_drivers_only_pct],
    ["Ensemble rekomendasi", row.ensemble_naive_ridge_pct],
  ] as const;
  const min = Math.min(...models.map((item) => item[1])) - 0.5;
  const max = Math.max(...models.map((item) => item[1])) + 0.5;
  return (
    <div className="model-bars">
      {models.map(([name, value]) => (
        <div className={`model-row ${name.startsWith("Ensemble") ? "recommended" : ""}`} key={name}>
          <span>{name}</span>
          <span className="model-track"><i style={{ width: `${((value - min) / (max - min || 1)) * 100}%` }} /></span>
          <b>{fmt(value)}%</b>
        </div>
      ))}
    </div>
  );
}

function CvScatter() {
  const rows = DATA.cv_predictions;
  const width = 520;
  const height = 340;
  const pad = 42;
  const maxValue = Math.ceil(Math.max(...rows.flatMap((row) => [row.actual_poverty_rate_pct, row.predicted_poverty_rate_pct]))) + 1;
  const x = (value: number) => pad + (value / maxValue) * (width - pad * 2);
  const y = (value: number) => height - pad - (value / maxValue) * (height - pad * 2);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="cv-scatter" role="img" aria-labelledby="cv-title cv-desc">
      <title id="cv-title">Aktual dibanding prediksi out-of-sample</title>
      <desc id="cv-desc">Titik yang mendekati garis diagonal menunjukkan prediksi yang lebih akurat.</desc>
      <line x1={x(0)} y1={y(0)} x2={x(maxValue)} y2={y(maxValue)} className="identity-line" />
      {[0, 5, 10, 15, 20].filter((tick) => tick <= maxValue).map((tick) => <g key={tick}><line x1={x(tick)} x2={x(tick)} y1={pad} y2={height - pad} className="grid-line" /><line x1={pad} x2={width - pad} y1={y(tick)} y2={y(tick)} className="grid-line" /><text x={x(tick)} y={height - 14} textAnchor="middle" className="axis-label">{tick}</text><text x={pad - 10} y={y(tick) + 4} textAnchor="end" className="axis-label">{tick}</text></g>)}
      {rows.map((row, index) => <circle key={`${row.province}-${row.test_year}-${index}`} cx={x(row.actual_poverty_rate_pct)} cy={y(row.predicted_poverty_rate_pct)} r="3.5" className={`cv-point year-${row.test_year}`}><title>{`${row.province} ${row.test_year}: aktual ${fmt(row.actual_poverty_rate_pct)}%, prediksi ${fmt(row.predicted_poverty_rate_pct)}%`}</title></circle>)}
      <text x={width / 2} y={height - 1} textAnchor="middle" className="axis-title">Aktual (%)</text>
      <text transform={`translate(12 ${height / 2}) rotate(-90)`} textAnchor="middle" className="axis-title">Prediksi (%)</text>
    </svg>
  );
}

function Overview({ year, setYear, metric, setMetric, selectedProvince, setSelectedProvince }: { year: number; setYear: (value: number) => void; metric: MetricCode; setMetric: (value: MetricCode) => void; selectedProvince: string; setSelectedProvince: (value: string) => void }) {
  const yearRows = DATA.panel.filter((row) => row.year === year);
  const metricRows = yearRows.filter((row) => typeof row[metric] === "number");
  const selected = yearRows.find((row) => row.province === selectedProvince);
  const national = DATA.national_trend.find((row) => row.year === year);
  const previousNational = DATA.national_trend.find((row) => row.year === year - 1);
  const highest = [...metricRows].sort((a, b) => (b[metric] as number) - (a[metric] as number))[0];
  const lowest = [...metricRows].sort((a, b) => (a[metric] as number) - (b[metric] as number))[0];
  const definition = METRICS[metric];
  const overviewValue = metric === "poverty_rate_pct" && national
    ? national.poverty_rate_pct
    : metric === "poor_population_thousand" && national
      ? national.poor_population_thousand
      : mean(metricRows.map((row) => row[metric] as number));
  const latestYear = year === 2025;

  return (
    <>
      <section className="page-intro">
        <div>
          <p className="eyebrow">Gambaran nasional dan provinsi</p>
          <h1>Jejak kemiskinan, dibaca lintas waktu.</h1>
          <p className="lead">Bandingkan tingkat kemiskinan dengan pasar kerja, pembangunan manusia, kapasitas ekonomi, dan layanan dasar tanpa mencampur batas waktu pengukuran.</p>
        </div>
        <div className="control-panel" aria-label="Filter ringkasan">
          <label>Tahun
            <select value={year} onChange={(event) => setYear(Number(event.target.value))}>
              {Array.from({ length: 11 }, (_, index) => 2015 + index).map((value) => <option key={value}>{value}</option>)}
            </select>
          </label>
          <label>Indikator
            <select value={metric} onChange={(event) => setMetric(event.target.value as MetricCode)}>
              {Object.entries(METRICS).map(([code, item]) => <option key={code} value={code}>{item.label}</option>)}
            </select>
          </label>
          <label>Provinsi pembanding
            <select value={selectedProvince} onChange={(event) => setSelectedProvince(event.target.value)}>
              {[...new Set(DATA.panel.map((row) => row.province))].sort().map((province) => <option key={province}>{province}</option>)}
            </select>
          </label>
        </div>
      </section>

      <section className="stat-grid" aria-label="Indikator utama">
        <StatCard eyebrow={metric === "poverty_rate_pct" || metric === "poor_population_thousand" ? "Indonesia" : "Rerata 32 provinsi stabil"} value={fmt(overviewValue, definition.decimals)} unit={definition.unit} note={<>{definition.short} pada {year}{metric === "poverty_rate_pct" && previousNational && national ? <> · <MiniArrow value={national.poverty_rate_pct - previousNational.poverty_rate_pct} /></> : null}</>} tone="accent" />
        <StatCard eyebrow="Nilai tertinggi" value={fmt(highest?.[metric] as number, definition.decimals)} unit={definition.unit} note={highest?.province ?? "—"} />
        <StatCard eyebrow="Nilai terendah" value={fmt(lowest?.[metric] as number, definition.decimals)} unit={definition.unit} note={lowest?.province ?? "—"} />
        <StatCard eyebrow={selectedProvince} value={fmt(selected?.[metric] as number, definition.decimals)} unit={definition.unit} note={latestYear && selected?.poverty_rate_pct !== null ? <>P0 2025 · {fmt(selected?.poverty_rate_pct)}%</> : <>Data terpilih · {year}</>} tone="dark" />
      </section>

      <section className="dashboard-grid map-grid">
        <article className="panel map-panel">
          <div className="panel-heading"><div><p className="eyebrow">Sebaran spasial</p><h2>{definition.label}</h2></div><span className="year-chip">{year}</span></div>
          <IndonesiaMap year={year} metric={metric} selectedProvince={selectedProvince} onSelect={setSelectedProvince} />
        </article>
        <article className="panel ranking-panel">
          <div className="panel-heading"><div><p className="eyebrow">Urutan provinsi</p><h2>Peringkat {definition.short}</h2></div><span className="small-muted">Klik untuk memilih</span></div>
          <Ranking rows={yearRows} metric={metric} selectedProvince={selectedProvince} onSelect={setSelectedProvince} />
        </article>
      </section>

      <section className="dashboard-grid trend-grid">
        <article className="panel trend-panel">
          <div className="panel-heading"><div><p className="eyebrow">Perjalanan 11 tahun</p><h2>Nasional vs {selectedProvince}</h2></div><div className="legend-inline"><span className="national-dot">Nasional</span><span className="province-dot">Provinsi</span></div></div>
          <NationalTrendChart selectedProvince={selectedProvince} />
        </article>
        <aside className="editorial-note">
          <span className="note-number">01</span>
          <p className="eyebrow">Bacaan utama</p>
          <h2>Kemiskinan nasional turun, tetapi jarak antarprovinsi masih lebar.</h2>
          <p>P0 Indonesia turun dari 11,22% pada 2015 menjadi 8,47% pada 2025. Pada 2025, rentang provinsi masih berada antara 3,72% dan 18,60%.</p>
          <div className="note-rule" />
          <p className="small-muted">Garis nasional menggunakan agregat resmi BPS; statistik antarprovinsi adalah perbandingan deskriptif dan tidak berbobot penduduk.</p>
        </aside>
      </section>
    </>
  );
}

function Drivers({ year, setYear, selectedProvince, setSelectedProvince }: { year: number; setYear: (value: number) => void; selectedProvince: string; setSelectedProvince: (value: string) => void }) {
  const [driver, setDriver] = useState<typeof DRIVER_OPTIONS[number]["code"]>("hdi");
  const rows = DATA.panel.filter((row) => row.year === year && typeof row[driver] === "number" && typeof row.poverty_rate_pct === "number");
  const r = pearson(rows.map((row) => row[driver] as number), rows.map((row) => row.poverty_rate_pct as number));
  const selected = rows.find((row) => row.province === selectedProvince);
  const lagCodeMap: Record<string, string> = {
    hdi: "lag_hdi", pdrb_pc_adhk2010_thousand_rp: "lag_log_pdrb_pc", tpt_aug_pct: "lag_tpt_aug_pct",
    sanitation_access_pct: "lag_sanitation_access_pct", drinking_water_access_pct: "lag_drinking_water_access_pct", food_share_pct: "lag_food_share_pct",
  };
  const panelCorrelation = DATA.correlations.find((item) => item.feature_code === lagCodeMap[driver]);
  const label = DRIVER_OPTIONS.find((item) => item.code === driver)?.label;
  return (
    <>
      <section className="page-intro compact">
        <div><p className="eyebrow">Eksplorasi multivariat</p><h1>Apa yang bergerak bersama kemiskinan?</h1><p className="lead">Pisahkan pola antarprovinsi dari perubahan di dalam provinsi. Korelasi membantu menemukan hipotesis, bukan menetapkan sebab-akibat.</p></div>
        <div className="control-panel two">
          <label>Tahun potret<select value={year} onChange={(event) => setYear(Number(event.target.value))}>{Array.from({ length: 11 }, (_, index) => 2015 + index).map((value) => <option key={value}>{value}</option>)}</select></label>
          <label>Faktor pembanding<select value={driver} onChange={(event) => setDriver(event.target.value as typeof driver)}>{DRIVER_OPTIONS.map((option) => <option key={option.code} value={option.code}>{option.label}</option>)}</select></label>
        </div>
      </section>

      <section className="stat-grid three">
        <StatCard eyebrow={`Korelasi lintas provinsi · ${year}`} value={signed(r, 3)} note={`Hubungan ${label} dengan P0 pada tahun terpilih`} tone="accent" />
        <StatCard eyebrow="Korelasi pooled · lag t-1" value={signed(panelCorrelation?.pooled_pearson_r ?? 0, 3)} note="320 observasi provinsi-tahun" />
        <StatCard eyebrow="Korelasi dalam-provinsi · lag t-1" value={signed(panelCorrelation?.within_province_r ?? 0, 3)} note="Mengurangi perbedaan tetap antarprovinsi" tone="dark" />
      </section>

      <section className="dashboard-grid driver-grid">
        <article className="panel scatter-panel">
          <div className="panel-heading"><div><p className="eyebrow">Setiap titik = provinsi</p><h2>{label} vs P0</h2></div><span className="year-chip">{year}</span></div>
          <ScatterPlot year={year} driver={driver} selectedProvince={selectedProvince} onSelect={setSelectedProvince} />
        </article>
        <aside className="selected-detail">
          <p className="eyebrow">Provinsi terpilih</p><h2>{selectedProvince}</h2>
          <div className="detail-metric"><span>{label}</span><b>{fmt(selected?.[driver] as number, driver === "pdrb_pc_adhk2010_thousand_rp" ? 0 : 2)}</b></div>
          <div className="detail-metric"><span>Kemiskinan</span><b>{fmt(selected?.poverty_rate_pct)}%</b></div>
          <div className="detail-metric"><span>Kelompok pulau</span><b>{selected?.island_group ?? "—"}</b></div>
          <p className="caution-copy">Titik ini menunjukkan posisi relatif pada {year}. Perbedaan definisi, waktu survei, struktur ekonomi, dan batas wilayah tetap perlu dipertimbangkan.</p>
        </aside>
      </section>

      <section className="panel full-panel">
        <div className="panel-heading"><div><p className="eyebrow">Sinyal model</p><h2>Asosiasi lag t-1 terhadap P0 tahun berikutnya</h2></div><span className="small-muted">Pooled vs dalam-provinsi</span></div>
        <div className="correlation-table" role="table" aria-label="Korelasi faktor terkait kemiskinan">
          <div className="correlation-head" role="row"><span>Faktor</span><span>Pooled r</span><span>Within r</span><span>Pola</span></div>
          {DATA.correlations.map((item) => (
            <div className="correlation-row" role="row" key={item.feature_code}>
              <span>{item.feature_name}</span><b>{signed(item.pooled_pearson_r, 3)}</b><b>{signed(item.within_province_r, 3)}</b>
              <span className={Math.sign(item.pooled_pearson_r) !== Math.sign(item.within_province_r) ? "pattern flip" : "pattern stable"}>{Math.sign(item.pooled_pearson_r) !== Math.sign(item.within_province_r) ? "Arah berbalik" : "Arah konsisten"}</span>
            </div>
          ))}
        </div>
        <p className="footnote">Contoh temuan: TPT negatif secara pooled tetapi positif di dalam provinsi. Ini kandidat paradoks agregasi—struktur antarprovinsi dapat membalik kesimpulan yang terlihat pada data gabungan.</p>
      </section>
    </>
  );
}

function Forecast({ selectedProvince, setSelectedProvince }: { selectedProvince: string; setSelectedProvince: (value: string) => void }) {
  const selected = DATA.forecast.find((row) => row.province === selectedProvince) ?? DATA.forecast[0];
  const best = DATA.benchmark[0];
  const averageForecast = mean(DATA.forecast.map((row) => row.forecast_poverty_rate_pct));
  const averageChange = mean(DATA.forecast.map((row) => row.change_vs_2025_pp));
  return (
    <>
      <section className="forecast-hero">
        <div><p className="eyebrow light">Eksperimen prediksi · Maret 2026</p><h1>Melihat satu tahun ke depan, dengan ketidakpastian yang terlihat.</h1><p>Forecast memakai informasi 2025 sebagai lag t-1. Nilai ini bukan angka resmi BPS dan tidak boleh menggantikan hasil Susenas.</p></div>
        <div className="forecast-stamp"><span>MODEL TERPILIH</span><b>{best.model_name}</b><small>Rolling-origin 2022–2025</small></div>
      </section>

      <section className="stat-grid forecast-stats">
        <StatCard eyebrow="Rerata forecast 32 provinsi" value={fmt(averageForecast)} unit="%" note={<MiniArrow value={averageChange} />} tone="accent" />
        <StatCard eyebrow="MAE out-of-sample" value={fmt(best.mae, 3)} unit="pp" note="128 observasi uji, 2022–2025" />
        <StatCard eyebrow="R² out-of-sample" value={fmt(best.r2, 3)} note="Kecocokan prediksi terhadap aktual" />
        <StatCard eyebrow="Status" value="Nonresmi" note="Eksperimental · dapat direvisi" tone="dark" />
      </section>

      <section className="dashboard-grid forecast-grid">
        <article className="panel forecast-rank-panel">
          <div className="panel-heading"><div><p className="eyebrow">Titik dan interval empiris 80%</p><h2>Prediksi seluruh provinsi model</h2></div><span className="small-muted">Klik provinsi</span></div>
          <div className="interval-axis"><span>0%</span><span>5%</span><span>10%</span><span>15%</span><span>20%</span></div>
          <ForecastIntervals rows={DATA.forecast} selectedProvince={selected.province} onSelect={setSelectedProvince} />
        </article>
        <aside className="forecast-detail">
          <label className="select-label">Provinsi<select value={selected.province} onChange={(event) => setSelectedProvince(event.target.value)}>{DATA.forecast.map((row) => <option key={row.province}>{row.province}</option>)}</select></label>
          <p className="forecast-place">{selected.province}</p>
          <p className="forecast-number">{fmt(selected.forecast_poverty_rate_pct)}<span>%</span></p>
          <div className="forecast-range"><span>Interval 80%</span><b>{fmt(selected.lower_80_pct)}–{fmt(selected.upper_80_pct)}%</b></div>
          <div className="forecast-change"><span>Dibanding 2025</span><MiniArrow value={selected.change_vs_2025_pp} /></div>
          <div className="forecast-divider" />
          <p className="eyebrow light">Lima sudut pandang model</p>
          <ModelComparison row={selected} />
          <p className="forecast-caution">Input PDRB 2025 berstatus sangat sementara. Kejutan harga, kebijakan, bencana, dan perubahan survei tidak tertangkap penuh.</p>
        </aside>
      </section>

      <section className="dashboard-grid validation-grid">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">Validasi temporal</p><h2>Aktual vs prediksi</h2></div><div className="year-legend"><span>2022</span><span>2023</span><span>2024</span><span>2025</span></div></div>
          <CvScatter />
        </article>
        <article className="panel benchmark-panel">
          <div className="panel-heading"><div><p className="eyebrow">Benchmark</p><h2>Model mana yang paling stabil?</h2></div></div>
          {DATA.benchmark.map((model) => (
            <div className={`benchmark-row ${model.mae_rank === 1 ? "winner" : ""}`} key={model.model_code}>
              <span className="benchmark-rank">{model.mae_rank}</span>
              <span className="benchmark-name"><b>{model.model_name}</b><small>MAPE {fmt(model.mape_pct, 2)}% · R² {fmt(model.r2, 3)}</small></span>
              <span className="benchmark-mae"><b>{fmt(model.mae, 3)}</b><small>MAE pp</small></span>
            </div>
          ))}
          <p className="footnote">Pemilihan model berdasarkan MAE terkecil pada rolling-origin. Setiap tahun uji hanya diprediksi menggunakan data yang tersedia sebelumnya.</p>
        </article>
      </section>
    </>
  );
}

function Methodology() {
  const variables = ["P0 kemiskinan", "TPT", "TPAK", "IPM", "PDRB/kapita", "Pertumbuhan PDRB", "Sanitasi", "Air minum", "Porsi makanan"];
  return (
    <>
      <section className="page-intro compact"><div><p className="eyebrow">Transparansi analisis</p><h1>Dari tabel BPS menuju model yang dapat diaudit.</h1><p className="lead">Data mentah, status mutu, transformasi lag, validasi waktu, dan sumber dipisahkan agar setiap angka dapat ditelusuri.</p></div></section>

      <section className="method-steps">
        {[
          ["01", "Akuisisi", "11 CSV kemiskinan 2015–2025 dan lima edisi Statistik Indonesia."],
          ["02", "Harmonisasi", "Nama provinsi, konsep indikator, wilayah pemekaran, dan simbol kualitas distandardisasi."],
          ["03", "Panel lag", "Target Maret tahun t dipasangkan dengan prediktor t-1 untuk mencegah kebocoran waktu."],
          ["04", "Validasi", "Rolling-origin: latih sampai t-1, lalu uji terpisah pada 2022, 2023, 2024, dan 2025."],
          ["05", "Forecast", "Model terbaik dilatih ulang sampai 2025 untuk memproyeksikan 2026 beserta interval empiris."],
        ].map(([number, title, copy]) => <article key={number}><span>{number}</span><div><h2>{title}</h2><p>{copy}</p></div></article>)}
      </section>

      <section className="dashboard-grid method-grid">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">Spesifikasi model</p><h2>Aturan yang dijaga</h2></div></div>
          <dl className="method-list">
            <div><dt>Target</dt><dd>Persentase penduduk miskin provinsi pada Maret tahun t.</dd></div>
            <div><dt>Unit model</dt><dd>32 provinsi dengan batas wilayah stabil sepanjang 2015–2025.</dd></div>
            <div><dt>Prediktor</dt><dd>{variables.join(", ")}—seluruh indikator substantif memakai lag t-1.</dd></div>
            <div><dt>Imputasi</dt><dd>Median dihitung hanya dari data pelatihan pada setiap split.</dd></div>
            <div><dt>Model terpilih</dt><dd>Ensemble 50% naive lag-1 dan 50% ridge lag + driver.</dd></div>
            <div><dt>Interval</dt><dd>Kuantil 10% dan 90% residual out-of-sample model rekomendasi.</dd></div>
          </dl>
        </article>
        <aside className="guardrail-panel">
          <span className="guardrail-mark">!</span>
          <p className="eyebrow light">Batas penggunaan</p>
          <h2>Prediktif bukan kausal.</h2>
          <p>Koefisien dan korelasi tidak membuktikan bahwa perubahan satu variabel menyebabkan kemiskinan berubah. Dashboard ini cocok untuk eksplorasi, penyusunan hipotesis, dan pemantauan—bukan evaluasi dampak kebijakan tanpa desain kausal.</p>
        </aside>
      </section>

      <section className="panel full-panel quality-panel">
        <div className="panel-heading"><div><p className="eyebrow">Keterangan data BPS</p><h2>Simbol mutu dan perlakuannya</h2></div><span className="small-muted">Bentuk mentah selalu dipertahankan</span></div>
        <div className="quality-table" role="table" aria-label="Legenda kualitas data BPS">
          <div className="quality-head" role="row"><span>Simbol</span><span>Makna</span><span>Nilai numerik</span><span>Perlakuan model</span></div>
          {DATA.data_legend.map((item) => (
            <div className="quality-row" role="row" key={item.symbol}>
              <b>{item.symbol}</b><span>{item.displayed_meaning}</span><span>{item.numeric_handling}</span><span>{item.model_action}{item.symbol === "b" ? " Definisi tampil tumpang tindih dengan kode a sehingga ditandai untuk verifikasi." : ""}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="sources-section">
        <div><p className="eyebrow">Jejak sumber</p><h2>Publikasi dan geometri</h2></div>
        <div className="source-list">
          {DATA.sources.map((source, index) => <a href={source.url} target="_blank" rel="noreferrer" key={source.url}><span>{String(index + 1).padStart(2, "0")}</span>{source.label}<i>↗</i></a>)}
        </div>
        <p className="source-note">Peta menggunakan geoBoundaries ADM1 berlisensi Open Data Commons ODbL 1.0. Tabel dan publikasi statistik berasal dari Badan Pusat Statistik.</p>
      </section>
    </>
  );
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [year, setYear] = useState(2025);
  const [metric, setMetric] = useState<MetricCode>("poverty_rate_pct");
  const [selectedProvince, setSelectedProvince] = useState("Nusa Tenggara Timur");

  const switchTab = (tab: Tab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" onClick={() => switchTab("overview")} aria-label="Kembali ke ringkasan">
          <span className="brand-mark">PI</span>
          <span><b>Peta Kemiskinan</b><small>Indonesia · 2015–2026</small></span>
        </a>
        <nav aria-label="Navigasi analisis">
          {NAV.map((item) => <button key={item.id} className={activeTab === item.id ? "active" : ""} onClick={() => switchTab(item.id)}><span>{item.label}</span><small>{item.kicker}</small></button>)}
        </nav>
        <div className="data-status"><i />Data BPS terharmonisasi</div>
      </header>

      <div className="site-shell" id="top">
        {activeTab === "overview" && <Overview year={year} setYear={setYear} metric={metric} setMetric={setMetric} selectedProvince={selectedProvince} setSelectedProvince={setSelectedProvince} />}
        {activeTab === "drivers" && <Drivers year={year} setYear={setYear} selectedProvince={selectedProvince} setSelectedProvince={setSelectedProvince} />}
        {activeTab === "forecast" && <Forecast selectedProvince={selectedProvince} setSelectedProvince={setSelectedProvince} />}
        {activeTab === "methodology" && <Methodology />}
      </div>

      <footer>
        <div><span className="brand-mark small">PI</span><p><b>Peta Kemiskinan Indonesia</b><small>Analisis eksploratif berbasis data BPS</small></p></div>
        <p>Data 2015–2025 · Forecast 2026 nonresmi<br />Diperbarui 21 Juli 2026</p>
      </footer>
    </main>
  );
}
