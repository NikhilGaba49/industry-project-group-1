"""Flatten and clean public_transport_stops.geojson into a stop-level CSV."""

import json
from pathlib import Path

import pandas as pd

SRC = Path("/Users/agamjotsandhu/Downloads/gtfs/public_transport_stops.geojson")
OUT = Path("data") / "curated" / "ptv_stops_master.csv"

VALID_MODES = {
    "INTERSTATE TRAIN",
    "METRO BUS",
    "METRO TRAIN",
    "METRO TRAM",
    "REGIONAL BUS",
    "REGIONAL COACH",
    "REGIONAL TRAIN",
    "SKYBUS",
}

# Approximate Victoria bounding box (lat, lon).
VIC_LAT_MIN, VIC_LAT_MAX = -39, -34
VIC_LON_MIN, VIC_LON_MAX = 140.9, 150.1

with open(SRC) as f:
    geojson = json.load(f)

features = geojson["features"]
print(f"Raw features: {len(features)}")

rows = []
for feat in features:
    props = feat.get("properties", {})
    coords = feat.get("geometry", {}).get("coordinates")
    rows.append(
        {
            "stop_id": props.get("STOP_ID"),
            "stop_name": props.get("STOP_NAME"),
            "mode": props.get("MODE"),
            "stop_lon": coords[0] if coords else None,
            "stop_lat": coords[1] if coords else None,
        }
    )

df = pd.DataFrame(rows)

df["stop_name"] = df["stop_name"].astype("string").str.strip()
df["mode"] = df["mode"].astype("string").str.strip()

# STOP_ID is documented as INTEGER but train stops (metro/regional/interstate) use
# GTFS-style string ids like "vic:rail:ART" - keep stop_id as a string so those
# aren't dropped, and only coerce lat/lon to numeric.
df["stop_id"] = df["stop_id"].astype("string").str.strip()
df["stop_lat"] = pd.to_numeric(df["stop_lat"], errors="coerce")
df["stop_lon"] = pd.to_numeric(df["stop_lon"], errors="coerce")

missing_mask = df["stop_id"].isna() | (df["stop_id"] == "") | df["stop_lat"].isna() | df["stop_lon"].isna()
n_missing = missing_mask.sum()
print(f"Dropping {n_missing} rows missing stop_id or coordinates")
df = df[~missing_mask].copy()

out_of_vic = ~df["stop_lat"].between(VIC_LAT_MIN, VIC_LAT_MAX) | ~df["stop_lon"].between(
    VIC_LON_MIN, VIC_LON_MAX
)
df["flag_out_of_vic_bbox"] = out_of_vic
if out_of_vic.any():
    print(f"WARNING: {out_of_vic.sum()} rows have coordinates outside the Victoria bounding box")

bad_mode = ~df["mode"].isin(VALID_MODES)
df["flag_unknown_mode"] = bad_mode
if bad_mode.any():
    print(f"WARNING: {bad_mode.sum()} rows have an unrecognised MODE value: {sorted(df.loc[bad_mode, 'mode'].unique())}")

n_dupes = df["stop_id"].duplicated().sum()
print(f"Duplicate stop_id rows found: {n_dupes}")
df = df.drop_duplicates(subset="stop_id", keep="first")

df = df[["stop_id", "stop_name", "mode", "stop_lat", "stop_lon", "flag_out_of_vic_bbox", "flag_unknown_mode"]]

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)

print(f"\nFinal row count: {len(df)}")
print("\nMode value counts:")
print(df["mode"].value_counts(dropna=False).to_string())
print(f"\nWrote {OUT}")
