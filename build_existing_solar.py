"""
build_existing_solar.py
Turns the two MaStR CSV exports (Wetterau + Vogelsberg) into ONE clean
point layer of existing ground-mounted solar parks, reprojected to
ETRS89 / UTM32N (EPSG:25832).
"""

import pandas as pd
import geopandas as gpd

# --- paths: change these only if your filenames differ -----------------
RAW = r"C:\Solar_Sites_Wetterau\data\raw"
OUT = r"C:\Solar_Sites_Wetterau\data\processed\existing_solar.gpkg"
FILES = [rf"{RAW}\mastr_wetterau.csv", rf"{RAW}\mastr_vogelsberg.csv"]

LAT = "Koordinate: Breitengrad (WGS84)"   # latitude  ~ 50
LON = "Koordinate: Längengrad (WGS84)"    # longitude ~ 9

KEEP = {
    "MaStR-Nr. der Einheit": "mastr_id",
    "Anzeige-Name der Einheit": "name",
    "Betriebs-Status": "status",
    "Bruttoleistung der Einheit": "power_kw",
    "Größe der in Anspruch genommenen Fläche in Hektar": "area_ha",
    "Überwiegende Nutzungsart der Fläche vor Errichtung": "prior_use",
    "Inbetriebnahmedatum der Einheit": "commission",
    "Gemeinde": "gemeinde",
    "Landkreis": "landkreis",
    LAT: "lat",
    LON: "lon",
}


def load(path):
    try:
        df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig", dtype=str)
    except UnicodeDecodeError:
        df = pd.read_csv(path, sep=";", decimal=",", encoding="cp1252", dtype=str)
    df = df[list(KEEP)].rename(columns=KEEP)
    for c in ("lat", "lon", "power_kw", "area_ha"):
        df[c] = pd.to_numeric(df[c].str.replace(",", ".", regex=False), errors="coerce")
    return df


df = pd.concat([load(f) for f in FILES], ignore_index=True)

gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["lon"], df["lat"]),
    crs=4326,
).to_crs(25832)

print(f"total parks: {len(gdf)}")
print(f"rows with no coordinate: {gdf['lat'].isna().sum()}")
print(f"X range: {gdf.geometry.x.min():.0f} - {gdf.geometry.x.max():.0f}  (expect ~470000-540000)")
print(f"Y range: {gdf.geometry.y.min():.0f} - {gdf.geometry.y.max():.0f}  (expect ~5570000-5620000)")

gdf.to_file(OUT, layer="existing_solar", driver="GPKG")
print(f"\nDone. Wrote {len(gdf)} parks to:\n{OUT}")