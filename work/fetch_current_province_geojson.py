from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard-web" / "public" / "data" / "indonesia-adm1-current.geojson"
CACHE = ROOT / "tmp" / "big-adm1-batches"
SERVICE = (
    "https://geoservices.big.go.id/rbi/rest/services/"
    "BATASWILAYAH/BATAS_WILAYAH/MapServer/12/query"
)

NAME_FIXES = {
    "Daerah Istimewa Yogyakarta": "DI Yogyakarta",
}


def request_json(params: dict[str, str], timeout: int = 90) -> dict:
    url = f"{SERVICE}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/geo+json",
            "User-Agent": "KemiskinanIndo-reproducible-pipeline/1.0",
        },
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8-sig"))
        except Exception as error:  # network retry is deliberate in this fetch-only script
            last_error = error
            if attempt == 3:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Gagal mengambil data BIG: {last_error}")


def polygon_parts(geometry: dict) -> list:
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"Tipe geometri tidak didukung: {geometry['type']}")
    # ArcGIS dapat menyertakan ordinat Z. D3 dan analisis centroid hanya
    # memerlukan bujur-lintang; membuang Z juga memperkecil aset deployment.
    cleaned = [
        [[[float(point[0]), float(point[1])] for point in ring] for ring in polygon]
        for polygon in polygons
    ]
    valid = []
    for polygon in cleaned:
        if not polygon:
            continue
        # Layer BIG berisi fragmen batas per lembar/segmen. Setelah
        # penyederhanaan, ring tambahan kadang tidak lagi berada di dalam ring
        # utama dan tidak valid sebagai hole GeoJSON. Untuk peta dashboard,
        # pertahankan outer ring setiap fragmen dan abaikan hole kecil.
        ring = polygon[0]
        if len(ring) < 4:
            continue
        unique_points = {(point[0], point[1]) for point in ring}
        signed_area = sum(
            ring[index][0] * ring[(index + 1) % len(ring)][1]
            - ring[(index + 1) % len(ring)][0] * ring[index][1]
            for index in range(len(ring))
        ) / 2.0
        # Penyederhanaan ArcGIS dapat meruntuhkan pulau sangat kecil menjadi
        # garis/titik. Ring nol-area dibaca D3 sebagai komplemen bumi dan
        # menghasilkan kotak besar, sehingga harus dibuang.
        if len(unique_points) < 3 or abs(signed_area) < 1e-10:
            continue
        valid.append([ring])
    return valid


ids_payload = request_json({"where": "1=1", "returnIdsOnly": "true", "f": "json"})
object_ids = sorted(set(int(value) for value in ids_payload["objectIds"]))
if len(object_ids) < 38:
    raise RuntimeError(f"Jumlah object ID BIG tidak wajar: {len(object_ids)}")

CACHE.mkdir(parents=True, exist_ok=True)
features: list[dict] = []
batch_size = 25
for batch_index, start in enumerate(range(0, len(object_ids), batch_size), start=1):
    batch_ids = object_ids[start : start + batch_size]
    cache_path = CACHE / f"batch-{batch_index:02d}.geojson"
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8-sig"))
    else:
        payload = request_json(
            {
                "objectIds": ",".join(str(value) for value in batch_ids),
                "outFields": "wadmpr",
                "returnGeometry": "true",
                "outSR": "4326",
                "geometryPrecision": "3",
                "maxAllowableOffset": "0.005",
                "f": "geojson",
            }
        )
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    features.extend(payload.get("features", []))
    print(f"BIG batch {batch_index}: {len(payload.get('features', []))} fitur")

grouped: dict[str, list] = defaultdict(list)
for feature in features:
    raw_name = str(feature.get("properties", {}).get("wadmpr", "")).strip()
    if not raw_name or not feature.get("geometry"):
        continue
    name = NAME_FIXES.get(raw_name, raw_name)
    grouped[name].extend(polygon_parts(feature["geometry"]))

if len(grouped) != 38:
    raise RuntimeError(
        f"BIG seharusnya menghasilkan 38 provinsi, tetapi ditemukan {len(grouped)}: "
        f"{sorted(grouped)}"
    )

output_features = []
for name in sorted(grouped):
    parts = grouped[name]
    output_features.append(
        {
            "type": "Feature",
            "properties": {
                "province": name,
                "shapeName": name,
                "source": "Badan Informasi Geospasial (BIG), layer Area Batas Wilayah Administrasi Provinsi",
            },
            "geometry": {"type": "MultiPolygon", "coordinates": parts},
        }
    )

collection = {
    "type": "FeatureCollection",
    "name": "Indonesia ADM1 current 38 provinces",
    "source": "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_WILAYAH/MapServer/12",
    "note": "Disederhanakan untuk visualisasi dashboard; bukan untuk penetapan batas hukum.",
    "features": output_features,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
)
print(json.dumps({"output": str(OUTPUT), "province_n": 38, "bytes": OUTPUT.stat().st_size}))
