from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "extracted_panel.json"
OUTPUT = ROOT / "data" / "processed" / "poverty_analysis.json"

TARGET = "poverty_rate_pct"
CV_YEARS = [2022, 2023, 2024, 2025]
LAMBDAS = [0.01, 0.1, 1.0, 10.0, 100.0]

CORE_FEATURES = [
    "lag_poverty_rate_pct",
    "lag_tpt_aug_pct",
    "lag_tpak_aug_pct",
    "lag_hdi",
    "lag_log_pdrb_pc",
    "lag_pdrb_growth_pct",
    "lag_sanitation_access_pct",
    "lag_drinking_water_access_pct",
    "year_index",
    "covid_2020_dummy",
]

DRIVER_FEATURES = [feature for feature in CORE_FEATURES if feature != "lag_poverty_rate_pct"]

FEATURE_LABELS = {
    "lag_poverty_rate_pct": "Kemiskinan Maret t-1",
    "lag_tpt_aug_pct": "TPT Agustus t-1",
    "lag_tpak_aug_pct": "TPAK Agustus t-1",
    "lag_hdi": "IPM t-1",
    "lag_log_pdrb_pc": "Log PDRB riil/kapita t-1",
    "lag_pdrb_growth_pct": "Pertumbuhan PDRB t-1",
    "lag_sanitation_access_pct": "Sanitasi layak t-1",
    "lag_drinking_water_access_pct": "Air minum layak t-1",
    "year_index": "Tren waktu (2015=0)",
    "covid_2020_dummy": "Dummy target 2020",
}

MODEL_LABELS = {
    "naive_lag1": "Naive: P0 tahun sebelumnya",
    "province_linear_trend": "Tren linear per provinsi",
    "ridge_lag_drivers": "Ridge: lag P0 + penggerak",
    "ridge_drivers_only": "Ridge: penggerak tanpa lag P0",
    "ensemble_naive_ridge": "Ensemble 50% naive + 50% ridge",
}


def safe_float(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def clean_records(frame: pd.DataFrame) -> list[dict]:
    records = []
    for row in frame.to_dict(orient="records"):
        cleaned = {}
        for key, value in row.items():
            if value is None or (isinstance(value, float) and not math.isfinite(value)):
                cleaned[key] = None
            elif isinstance(value, (np.integer,)):
                cleaned[key] = int(value)
            elif isinstance(value, (np.floating,)):
                cleaned[key] = safe_float(value)
            elif isinstance(value, (pd.Timestamp,)):
                cleaned[key] = value.isoformat()
            else:
                cleaned[key] = value
        records.append(cleaned)
    return records


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | int | None]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    residual = y_true - y_pred
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    nonzero = np.abs(y_true) > 1e-12
    mape = float(np.mean(np.abs(residual[nonzero] / y_true[nonzero])) * 100) if nonzero.any() else None
    denominator = float(np.sum(np.square(y_true - y_true.mean())))
    r2 = 1.0 - float(np.sum(np.square(residual))) / denominator if denominator > 0 else None
    return {"n": int(len(y_true)), "mae": mae, "rmse": rmse, "mape_pct": mape, "r2": r2}


def pearson(x: pd.Series, y: pd.Series) -> tuple[float | None, int]:
    pair = pd.concat([x, y], axis=1).dropna()
    if len(pair) < 3 or pair.iloc[:, 0].std(ddof=0) == 0 or pair.iloc[:, 1].std(ddof=0) == 0:
        return None, int(len(pair))
    return float(np.corrcoef(pair.iloc[:, 0], pair.iloc[:, 1])[0, 1]), int(len(pair))


def design_fit(train: pd.DataFrame, features: list[str], lam: float) -> dict:
    medians = {}
    means = {}
    stds = {}
    numeric_blocks = []
    for feature in features:
        series = pd.to_numeric(train[feature], errors="coerce")
        median = float(series.median())
        filled = series.fillna(median).astype(float)
        mean = float(filled.mean())
        std = float(filled.std(ddof=0))
        if std == 0 or not math.isfinite(std):
            std = 1.0
        medians[feature] = median
        means[feature] = mean
        stds[feature] = std
        numeric_blocks.append(((filled.to_numpy() - mean) / std).reshape(-1, 1))

    provinces = sorted(train["province"].unique().tolist())
    province_map = {province: idx for idx, province in enumerate(provinces)}
    province_block = np.zeros((len(train), len(provinces)), dtype=float)
    for row_idx, province in enumerate(train["province"]):
        province_block[row_idx, province_map[province]] = 1.0

    X = np.hstack([np.ones((len(train), 1)), *numeric_blocks, province_block])
    y = train[TARGET].to_numpy(dtype=float)
    penalty = np.eye(X.shape[1])
    penalty[0, 0] = 0.0
    beta = np.linalg.pinv(X.T @ X + lam * penalty) @ X.T @ y
    return {
        "features": features,
        "lambda": float(lam),
        "medians": medians,
        "means": means,
        "stds": stds,
        "provinces": provinces,
        "beta": beta,
    }


def design_predict(model: dict, test: pd.DataFrame) -> np.ndarray:
    blocks = []
    for feature in model["features"]:
        series = pd.to_numeric(test[feature], errors="coerce").fillna(model["medians"][feature]).astype(float)
        blocks.append(((series.to_numpy() - model["means"][feature]) / model["stds"][feature]).reshape(-1, 1))
    province_map = {province: idx for idx, province in enumerate(model["provinces"])}
    province_block = np.zeros((len(test), len(model["provinces"])), dtype=float)
    for row_idx, province in enumerate(test["province"]):
        if province in province_map:
            province_block[row_idx, province_map[province]] = 1.0
    X = np.hstack([np.ones((len(test), 1)), *blocks, province_block])
    return np.maximum(0.0, X @ model["beta"])


def select_inner_lambda(train: pd.DataFrame, features: list[str]) -> float:
    validation_year = int(train["year"].max())
    inner_train = train[train["year"] < validation_year]
    inner_validation = train[train["year"] == validation_year]
    if inner_train["year"].nunique() < 3 or inner_validation.empty:
        return 1.0
    scores = []
    for lam in LAMBDAS:
        model = design_fit(inner_train, features, lam)
        prediction = design_predict(model, inner_validation)
        scores.append((metrics(inner_validation[TARGET].to_numpy(), prediction)["mae"], lam))
    return float(min(scores)[1])


def predict_province_trend(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    predictions = []
    global_mean = float(train[TARGET].mean())
    for _, row in test.iterrows():
        subset = train[train["province"] == row["province"]].sort_values("year")
        if len(subset) >= 2:
            x = subset["year"].to_numpy(dtype=float)
            y = subset[TARGET].to_numpy(dtype=float)
            slope, intercept = np.polyfit(x, y, 1)
            value = intercept + slope * float(row["year"])
        elif len(subset) == 1:
            value = float(subset[TARGET].iloc[-1])
        else:
            value = global_mean
        predictions.append(max(0.0, value))
    return np.asarray(predictions)


def final_lambda_by_rolling_cv(model_panel: pd.DataFrame, features: list[str]) -> tuple[float, list[dict]]:
    rows = []
    for lam in LAMBDAS:
        all_true = []
        all_pred = []
        for test_year in CV_YEARS:
            train = model_panel[model_panel["year"] < test_year]
            test = model_panel[model_panel["year"] == test_year]
            fitted = design_fit(train, features, lam)
            all_true.extend(test[TARGET].to_numpy(dtype=float))
            all_pred.extend(design_predict(fitted, test))
        score = metrics(np.asarray(all_true), np.asarray(all_pred))
        rows.append({"model_family": "ridge_lag_drivers" if "lag_poverty_rate_pct" in features else "ridge_drivers_only", "lambda": lam, **score})
    best = min(rows, key=lambda row: row["mae"])["lambda"]
    return float(best), rows


def pdrb_vintage_status(year: int) -> str:
    return {
        2017: "preliminary",
        2018: "very_preliminary",
        2019: "preliminary",
        2020: "very_preliminary",
        2022: "preliminary",
        2023: "very_preliminary",
        2024: "preliminary",
        2025: "very_preliminary",
    }.get(int(year), "published_without_preliminary_mark")


with INPUT.open("r", encoding="utf-8") as handle:
    source = json.load(handle)

panel_all = pd.DataFrame(source["panel_rows"]).sort_values(["province", "year"]).reset_index(drop=True)
panel = panel_all[panel_all["stable32_model_flag"] == 1].copy()

lag_sources = {
    "poverty_rate_pct": "lag_poverty_rate_pct",
    "tpt_aug_pct": "lag_tpt_aug_pct",
    "tpak_aug_pct": "lag_tpak_aug_pct",
    "hdi": "lag_hdi",
    "pdrb_pc_adhk2010_thousand_rp": "lag_pdrb_pc_adhk2010_thousand_rp",
    "pdrb_growth_pct": "lag_pdrb_growth_pct",
    "pdrb_pc_growth_pct": "lag_pdrb_pc_growth_pct",
    "sanitation_access_pct": "lag_sanitation_access_pct",
    "drinking_water_access_pct": "lag_drinking_water_access_pct",
    "food_share_pct": "lag_food_share_pct",
}
for source_col, lag_col in lag_sources.items():
    panel[lag_col] = panel.groupby("province", sort=False)[source_col].shift(1)

panel["lag_log_pdrb_pc"] = np.log(panel["lag_pdrb_pc_adhk2010_thousand_rp"].where(panel["lag_pdrb_pc_adhk2010_thousand_rp"] > 0))
panel["year_index"] = panel["year"] - 2015
panel["lag_year"] = panel["year"] - 1
panel["lag_pdrb_vintage_status"] = panel["lag_year"].map(pdrb_vintage_status)
panel["model_row_status"] = np.where(panel["lag_poverty_rate_pct"].notna(), "eligible", "no_lag_target")

model_panel = panel[(panel["year"] >= 2016) & panel[TARGET].notna() & panel["lag_poverty_rate_pct"].notna()].copy()

cv_predictions = []
chosen_lambdas = []
for test_year in CV_YEARS:
    train = model_panel[model_panel["year"] < test_year].copy()
    test = model_panel[model_panel["year"] == test_year].copy()
    core_lambda = select_inner_lambda(train, CORE_FEATURES)
    drivers_lambda = select_inner_lambda(train, DRIVER_FEATURES)
    chosen_lambdas.append({"test_year": test_year, "ridge_lag_drivers_lambda": core_lambda, "ridge_drivers_only_lambda": drivers_lambda})
    core_prediction = design_predict(design_fit(train, CORE_FEATURES, core_lambda), test)
    drivers_prediction = design_predict(design_fit(train, DRIVER_FEATURES, drivers_lambda), test)
    naive_prediction = test["lag_poverty_rate_pct"].to_numpy(dtype=float)
    trend_prediction = predict_province_trend(train, test)
    ensemble_prediction = 0.5 * naive_prediction + 0.5 * core_prediction
    prediction_map = {
        "naive_lag1": naive_prediction,
        "province_linear_trend": trend_prediction,
        "ridge_lag_drivers": core_prediction,
        "ridge_drivers_only": drivers_prediction,
        "ensemble_naive_ridge": ensemble_prediction,
    }
    for row_idx, (_, row) in enumerate(test.iterrows()):
        for model_code, predictions in prediction_map.items():
            prediction = float(predictions[row_idx])
            actual = float(row[TARGET])
            cv_predictions.append({
                "province": row["province"],
                "test_year": test_year,
                "model_code": model_code,
                "model_name": MODEL_LABELS[model_code],
                "actual_poverty_rate_pct": actual,
                "predicted_poverty_rate_pct": prediction,
                "residual_actual_minus_pred": actual - prediction,
                "absolute_error": abs(actual - prediction),
            })

cv_frame = pd.DataFrame(cv_predictions)
benchmark_rows = []
for model_code, subset in cv_frame.groupby("model_code", sort=False):
    overall = metrics(subset["actual_poverty_rate_pct"].to_numpy(), subset["predicted_poverty_rate_pct"].to_numpy())
    benchmark_rows.append({
        "evaluation_scope": "overall_2022_2025",
        "test_year": None,
        "model_code": model_code,
        "model_name": MODEL_LABELS[model_code],
        **overall,
    })
    for test_year, year_subset in subset.groupby("test_year"):
        score = metrics(year_subset["actual_poverty_rate_pct"].to_numpy(), year_subset["predicted_poverty_rate_pct"].to_numpy())
        benchmark_rows.append({
            "evaluation_scope": "single_year",
            "test_year": int(test_year),
            "model_code": model_code,
            "model_name": MODEL_LABELS[model_code],
            **score,
        })

benchmark = pd.DataFrame(benchmark_rows)
overall_benchmark = benchmark[benchmark["evaluation_scope"] == "overall_2022_2025"].sort_values(["mae", "rmse"]).reset_index(drop=True)
overall_benchmark["mae_rank"] = np.arange(1, len(overall_benchmark) + 1)
recommended_model = str(overall_benchmark.iloc[0]["model_code"])
benchmark = benchmark.merge(overall_benchmark[["model_code", "mae_rank"]], on="model_code", how="left")
benchmark["recommended_flag"] = (benchmark["model_code"] == recommended_model).astype(int)

final_core_lambda, core_lambda_scores = final_lambda_by_rolling_cv(model_panel, CORE_FEATURES)
final_drivers_lambda, driver_lambda_scores = final_lambda_by_rolling_cv(model_panel, DRIVER_FEATURES)
lambda_scores = pd.DataFrame(core_lambda_scores + driver_lambda_scores)

forecast_source = panel[panel["year"] == 2025].copy()
forecast_2026 = forecast_source[["province", "island_group"]].copy()
forecast_2026["year"] = 2026
forecast_2026["year_index"] = 11
forecast_2026["covid_2020_dummy"] = 0
forecast_2026["lag_year"] = 2025
forecast_2026["lag_poverty_rate_pct"] = forecast_source["poverty_rate_pct"].to_numpy()
forecast_2026["lag_tpt_aug_pct"] = forecast_source["tpt_aug_pct"].to_numpy()
forecast_2026["lag_tpak_aug_pct"] = forecast_source["tpak_aug_pct"].to_numpy()
forecast_2026["lag_hdi"] = forecast_source["hdi"].to_numpy()
forecast_2026["lag_pdrb_pc_adhk2010_thousand_rp"] = forecast_source["pdrb_pc_adhk2010_thousand_rp"].to_numpy()
forecast_2026["lag_log_pdrb_pc"] = np.log(forecast_2026["lag_pdrb_pc_adhk2010_thousand_rp"].where(forecast_2026["lag_pdrb_pc_adhk2010_thousand_rp"] > 0))
forecast_2026["lag_pdrb_growth_pct"] = forecast_source["pdrb_growth_pct"].to_numpy()
forecast_2026["lag_pdrb_pc_growth_pct"] = forecast_source["pdrb_pc_growth_pct"].to_numpy()
forecast_2026["lag_sanitation_access_pct"] = forecast_source["sanitation_access_pct"].to_numpy()
forecast_2026["lag_drinking_water_access_pct"] = forecast_source["drinking_water_access_pct"].to_numpy()
forecast_2026["lag_food_share_pct"] = forecast_source["food_share_pct"].to_numpy()
forecast_2026["lag_pdrb_vintage_status"] = "very_preliminary"

full_train = model_panel.copy()
forecast_predictions = {
    "naive_lag1": forecast_2026["lag_poverty_rate_pct"].to_numpy(dtype=float),
    "province_linear_trend": predict_province_trend(full_train, forecast_2026),
    "ridge_lag_drivers": design_predict(design_fit(full_train, CORE_FEATURES, final_core_lambda), forecast_2026),
    "ridge_drivers_only": design_predict(design_fit(full_train, DRIVER_FEATURES, final_drivers_lambda), forecast_2026),
}
forecast_predictions["ensemble_naive_ridge"] = 0.5 * forecast_predictions["naive_lag1"] + 0.5 * forecast_predictions["ridge_lag_drivers"]

recommended_residuals = cv_frame.loc[cv_frame["model_code"] == recommended_model, "residual_actual_minus_pred"].to_numpy(dtype=float)
lower_residual = float(np.quantile(recommended_residuals, 0.10))
upper_residual = float(np.quantile(recommended_residuals, 0.90))
recommended_point = forecast_predictions[recommended_model]
forecast_rows = []
for row_idx, (_, row) in enumerate(forecast_2026.iterrows()):
    point = float(recommended_point[row_idx])
    forecast_rows.append({
        "province": row["province"],
        "forecast_year": 2026,
        "actual_2025_pct": float(row["lag_poverty_rate_pct"]),
        "recommended_model_code": recommended_model,
        "recommended_model_name": MODEL_LABELS[recommended_model],
        "forecast_poverty_rate_pct": point,
        "lower_80_pct": max(0.0, point + lower_residual),
        "upper_80_pct": max(0.0, point + upper_residual),
        "change_vs_2025_pp": point - float(row["lag_poverty_rate_pct"]),
        "naive_lag1_pct": float(forecast_predictions["naive_lag1"][row_idx]),
        "province_linear_trend_pct": float(forecast_predictions["province_linear_trend"][row_idx]),
        "ridge_lag_drivers_pct": float(forecast_predictions["ridge_lag_drivers"][row_idx]),
        "ridge_drivers_only_pct": float(forecast_predictions["ridge_drivers_only"][row_idx]),
        "ensemble_naive_ridge_pct": float(forecast_predictions["ensemble_naive_ridge"][row_idx]),
        "input_pdrb_vintage_status": "very_preliminary",
        "forecast_status": "experimental_nonofficial",
    })
forecast_frame = pd.DataFrame(forecast_rows).sort_values("forecast_poverty_rate_pct", ascending=False).reset_index(drop=True)
forecast_frame["forecast_rank_high_to_low"] = np.arange(1, len(forecast_frame) + 1)

trend_rows = []
for year, subset in panel.groupby("year"):
    values = subset[TARGET].dropna().astype(float)
    trend_rows.append({
        "year": int(year),
        "province_n": int(len(values)),
        "unweighted_mean_pct": float(values.mean()),
        "median_pct": float(values.median()),
        "minimum_pct": float(values.min()),
        "maximum_pct": float(values.max()),
        "std_dev_pct": float(values.std(ddof=1)),
    })
trend_frame = pd.DataFrame(trend_rows)

rank_2025 = panel[panel["year"] == 2025][["province", "island_group", TARGET]].sort_values(TARGET, ascending=False).copy()
rank_2025["rank_high_to_low"] = np.arange(1, len(rank_2025) + 1)

pivot_poverty = panel.pivot(index="province", columns="year", values=TARGET)
change_rows = []
for province, row in pivot_poverty.iterrows():
    change_rows.append({
        "province": province,
        "poverty_rate_2015_pct": safe_float(row.get(2015)),
        "poverty_rate_2024_pct": safe_float(row.get(2024)),
        "poverty_rate_2025_pct": safe_float(row.get(2025)),
        "change_2015_2025_pp": safe_float(row.get(2025) - row.get(2015)),
        "change_2024_2025_pp": safe_float(row.get(2025) - row.get(2024)),
    })
change_frame = pd.DataFrame(change_rows).sort_values("change_2015_2025_pp")

corr_features = [
    "lag_poverty_rate_pct", "lag_tpt_aug_pct", "lag_tpak_aug_pct", "lag_hdi",
    "lag_log_pdrb_pc", "lag_pdrb_growth_pct", "lag_pdrb_pc_growth_pct",
    "lag_sanitation_access_pct", "lag_drinking_water_access_pct", "lag_food_share_pct",
]
corr_rows = []
for feature in corr_features:
    pooled, n_pooled = pearson(model_panel[feature], model_panel[TARGET])
    pair = model_panel[["province", feature, TARGET]].dropna().copy()
    pair["feature_within"] = pair[feature] - pair.groupby("province")[feature].transform("mean")
    pair["target_within"] = pair[TARGET] - pair.groupby("province")[TARGET].transform("mean")
    within, n_within = pearson(pair["feature_within"], pair["target_within"])
    corr_rows.append({
        "feature_code": feature,
        "feature_name": FEATURE_LABELS.get(feature, feature.replace("lag_", "") + " t-1"),
        "n_complete": n_pooled,
        "pooled_pearson_r": pooled,
        "within_province_r": within,
        "within_n": n_within,
        "interpretation_guardrail": "Asosiasi deskriptif; bukan bukti sebab-akibat.",
    })
corr_frame = pd.DataFrame(corr_rows)

final_core_model = design_fit(full_train, CORE_FEATURES, final_core_lambda)
coefficient_rows = []
for idx, feature in enumerate(CORE_FEATURES, start=1):
    coefficient_rows.append({
        "feature_code": feature,
        "feature_name": FEATURE_LABELS[feature],
        "standardized_coefficient": float(final_core_model["beta"][idx]),
        "absolute_coefficient": abs(float(final_core_model["beta"][idx])),
        "coefficient_sign": "positive" if final_core_model["beta"][idx] > 0 else "negative" if final_core_model["beta"][idx] < 0 else "zero",
        "interpretation_guardrail": "Koefisien prediktif terstandar; tidak boleh dibaca sebagai dampak kausal.",
    })
coefficient_frame = pd.DataFrame(coefficient_rows).sort_values("absolute_coefficient", ascending=False)

quality_rows = []
poverty_raw = pd.DataFrame(source["poverty_raw"])
for field in ["poverty_line", "poor_population", "poverty_rate"]:
    status_col = f"{field}_status"
    raw_col = f"{field}_raw"
    grouped = poverty_raw.groupby(status_col, dropna=False)
    for status, subset in grouped:
        samples = [str(value) for value in subset[raw_col].dropna().astype(str).unique()[:3]]
        quality_rows.append({
            "field": field,
            "status": status if pd.notna(status) else "missing_status",
            "count": int(len(subset)),
            "raw_examples": "; ".join(samples),
        })
quality_frame = pd.DataFrame(quality_rows).sort_values(["field", "status"])

legend_rows = [
    {"symbol": "...", "displayed_meaning": "Data tidak tersedia", "numeric_handling": "NULL", "quality_status": "unavailable", "model_action": "Tidak diimputasi saat staging; imputasi hanya di dalam split pelatihan bila fitur memerlukannya.", "note": "Tidak pernah diperlakukan sebagai nol."},
    {"symbol": "–", "displayed_meaning": "Tidak ada atau nol", "numeric_handling": "Kontekstual", "quality_status": "none_zero_or_structural", "model_action": "Verifikasi konteks; untuk wilayah sebelum terbentuk diperlakukan sebagai structural missing.", "note": "Mencegah provinsi hasil pemekaran memiliki riwayat nol palsu."},
    {"symbol": "NA", "displayed_meaning": "Data tidak dapat ditampilkan", "numeric_handling": "NULL", "quality_status": "suppressed_not_displayed", "model_action": "Dikeluarkan dari perhitungan langsung.", "note": "Umumnya berkaitan dengan mutu estimasi yang tidak memadai."},
    {"symbol": "e", "displayed_meaning": "Angka estimasi", "numeric_handling": "Pertahankan angka", "quality_status": "estimated", "model_action": "Boleh digunakan dengan flag mutu.", "note": "Status wajib dibawa ke audit trail."},
    {"symbol": "r", "displayed_meaning": "Angka diperbaiki", "numeric_handling": "Pertahankan angka", "quality_status": "revised", "model_action": "Gunakan versi revisi dan simpan status.", "note": "Jangan mengganti dengan rilis lama."},
    {"symbol": "~0", "displayed_meaning": "Data dapat diabaikan", "numeric_handling": "0 dengan flag", "quality_status": "negligible_zero", "model_action": "Gunakan nol hanya setelah menyimpan bentuk mentah.", "note": "Berbeda dari data hilang."},
    {"symbol": "*", "displayed_meaning": "Angka sementara", "numeric_handling": "Pertahankan angka", "quality_status": "preliminary", "model_action": "Boleh digunakan; beri peringatan bahwa nilai dapat direvisi.", "note": "Diterapkan pada beberapa seri PDRB."},
    {"symbol": "**", "displayed_meaning": "Angka sangat sementara", "numeric_handling": "Pertahankan angka", "quality_status": "very_preliminary", "model_action": "Boleh digunakan dengan peringatan lebih kuat.", "note": "Input PDRB 2025 untuk forecast 2026 berada pada kategori ini."},
    {"symbol": "***", "displayed_meaning": "Angka sangat sangat sementara", "numeric_handling": "Pertahankan angka", "quality_status": "very_very_preliminary", "model_action": "Gunakan hanya dengan flag eksplisit.", "note": "Potensi revisi lebih tinggi."},
    {"symbol": "a", "displayed_meaning": "25% < RSE ≤ 50%", "numeric_handling": "Pertahankan angka", "quality_status": "rse_25_to_50_caution", "model_action": "Analisis sensitif; jangan menonjolkan peringkat tipis.", "note": "Estimasi perlu kehati-hatian."},
    {"symbol": "b", "displayed_meaning": "RSE < 50% (sebagaimana tampil pada legenda yang diberikan)", "numeric_handling": "Verifikasi", "quality_status": "rse_code_b_verify", "model_action": "Jangan gunakan otomatis sebelum definisi tabel asal dikonfirmasi.", "note": "Definisi tampil tumpang tindih dengan kode a dan kemungkinan salah ketik."},
    {"symbol": "c", "displayed_meaning": "Penjumlahan tidak sama dengan wilayah di atasnya", "numeric_handling": "Pertahankan angka", "quality_status": "nonadditive_hierarchy", "model_action": "Jangan menjumlahkan menjadi total wilayah tanpa rekonsiliasi.", "note": "Gunakan agregat resmi bila tersedia."},
]

model_panel_export_columns = [
    "province", "year", "lag_year", "island_group", TARGET,
    "lag_poverty_rate_pct", "lag_tpt_aug_pct", "lag_tpak_aug_pct", "lag_hdi",
    "lag_pdrb_pc_adhk2010_thousand_rp", "lag_log_pdrb_pc", "lag_pdrb_growth_pct",
    "lag_pdrb_pc_growth_pct", "lag_sanitation_access_pct", "lag_drinking_water_access_pct",
    "lag_food_share_pct", "year_index", "covid_2020_dummy", "lag_pdrb_vintage_status", "model_row_status",
]

output = {
    "methodology": {
        "target": "Persentase penduduk miskin provinsi pada Maret tahun t",
        "model_universe": "32 provinsi dengan batas wilayah stabil sepanjang 2015–2025",
        "feature_timing": "Seluruh indikator substantif menggunakan lag t-1; target 2026 memakai informasi 2025",
        "validation": "Rolling-origin; latih hingga t-1 dan uji pada 2022, 2023, 2024, 2025",
        "imputation": "Median fitur dihitung hanya dari data pelatihan pada setiap split",
        "recommended_model_code": recommended_model,
        "recommended_model_name": MODEL_LABELS[recommended_model],
        "forecast_interval": "Interval empiris 80% dari kuantil residual out-of-sample model rekomendasi",
        "forecast_warning": "Forecast 2026 bersifat eksperimental/nonresmi dan bukan publikasi BPS",
        "final_core_lambda": final_core_lambda,
        "final_drivers_lambda": final_drivers_lambda,
        "training_observations": int(len(full_train)),
        "cv_observations_per_model": int(len(cv_frame[cv_frame["model_code"] == recommended_model])),
    },
    "data_legend": legend_rows,
    "quality_counts": clean_records(quality_frame),
    "model_panel_lag1": clean_records(model_panel[model_panel_export_columns]),
    "eda_trend": clean_records(trend_frame),
    "eda_rank_2025": clean_records(rank_2025),
    "eda_changes": clean_records(change_frame),
    "eda_correlations": clean_records(corr_frame),
    "ridge_coefficients": clean_records(coefficient_frame),
    "model_benchmark": clean_records(benchmark.sort_values(["evaluation_scope", "mae_rank", "test_year"], na_position="first")),
    "cv_predictions": clean_records(cv_frame.sort_values(["test_year", "model_code", "province"])),
    "chosen_lambdas_by_fold": chosen_lambdas,
    "lambda_scores": clean_records(lambda_scores),
    "forecast_2026": clean_records(forecast_frame),
}

with OUTPUT.open("w", encoding="utf-8") as handle:
    json.dump(output, handle, ensure_ascii=False, indent=2, allow_nan=False)

print(json.dumps({
    "output": str(OUTPUT),
    "model_rows": len(model_panel),
    "cv_prediction_rows": len(cv_frame),
    "recommended_model": recommended_model,
    "recommended_model_name": MODEL_LABELS[recommended_model],
    "forecast_rows": len(forecast_frame),
    "overall_benchmark": clean_records(overall_benchmark),
}, ensure_ascii=False))
