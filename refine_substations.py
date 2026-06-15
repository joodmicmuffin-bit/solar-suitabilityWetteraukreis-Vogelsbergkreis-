"""
refine_substations.py
Re-computes ONLY the substation-distance criterion, this time filtered to
grid-connection-capable substations (by voltage), and updates the existing
parcels_full.gpkg in place.

It first PRINTS a voltage breakdown so you can see what's in the data and
pick a sensible threshold. Default threshold = 30 kV (medium-high voltage).
Change THRESHOLD if the breakdown suggests a better cut.
"""

import re
import numpy as np
import geopandas as gpd
from shapely.strtree import STRtree

RAW = r"C:\Solar_Sites_Wetterau\data\raw"
GPKG = r"C:\Solar_Sites_Wetterau\data\processed\parcels_full.gpkg"
CRS = 25832

THRESHOLD = 30000   # volts. 30000 = 30 kV. Try 110000 for transmission-grade only.


def parse_voltage(v):
    """Pull the highest voltage (in volts) out of a messy OSM voltage tag."""
    if v is None:
        return np.nan
    s = str(v).lower()
    if s.strip() in ("", "nan", "none"):
        return np.nan
    vals = []
    for tok in re.split(r"[;,]", s):
        tok = tok.strip()
        nums = re.findall(r"\d+\.?\d*", tok)
        if not nums:
            continue
        n = float(nums[0])
        if "k" in tok and n < 1000:     # "110 kV" style
            n *= 1000
        vals.append(n)
    return max(vals) if vals else np.nan


# ----------------------------------------------------------------------
parcels = gpd.read_file(GPKG, layer="parcels_full").to_crs(CRS)
subs = gpd.read_file(rf"{RAW}\substations.geojson").to_crs(CRS)
subs["geometry"] = subs.geometry.centroid

# parse voltage (column may be named 'voltage'; fall back to NaN if absent)
volt_col = "voltage" if "voltage" in subs.columns else None
subs["volt"] = subs[volt_col].apply(parse_voltage) if volt_col else np.nan

# ---- voltage breakdown so you can SEE the data ----
total = len(subs)
tagged = subs["volt"].notna().sum()
print(f"substations total: {total}")
print(f"  with a voltage tag: {tagged}  ({total - tagged} untagged)")
for thr in (20000, 30000, 60000, 110000, 220000):
    print(f"  >= {thr//1000:>3} kV : {(subs['volt'] >= thr).sum()}")

# ---- filter to grid-scale ----
grid = subs[subs["volt"] >= THRESHOLD]
print(f"\nusing THRESHOLD = {THRESHOLD//1000} kV  ->  {len(grid)} grid-scale substations")
if len(grid) < 3:
    print("  (very few left, consider lowering THRESHOLD)")

# ---- recompute nearest-substation distance ----
geoms = list(grid.geometry)
tree = STRtree(geoms)
parcels["substation_dist_m"] = [
    round(g.distance(geoms[tree.nearest(g)]), 1) for g in parcels.geometry
]

print(f"\nNEW substation dist  min/median/max: "
      f"{parcels.substation_dist_m.min():.0f} / "
      f"{parcels.substation_dist_m.median():.0f} / "
      f"{parcels.substation_dist_m.max():.0f} m")

parcels.to_file(GPKG, layer="parcels_full", driver="GPKG")
print(f"\nDone. Updated substation distances in:\n{GPKG}")
