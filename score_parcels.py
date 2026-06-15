"""
score_parcels.py
Turns the five measured criteria into a single suitability score per parcel.

Each criterion -> a 1-5 score -> multiplied by its weight -> summed.
Final TOTAL ranges 1 (worst) to 5 (best). Also adds a 0-100 version and a rank.

Weights are the starting set (settlement proximity dropped for v1, the rest
renormalized to 100%). Swap these for AHP-derived weights later, nothing else
changes.
"""

import numpy as np
import geopandas as gpd

GPKG = r"C:\Solar_Sites_Wetterau\data\processed\parcels_full.gpkg"
OUT = r"C:\Solar_Sites_Wetterau\data\processed\parcels_final.gpkg"

WEIGHTS = {
    "s_eeg":   0.272,   # EEG 500m corridor
    "s_sub":   0.272,   # substation distance
    "s_slope": 0.163,   # slope
    "s_south": 0.163,   # southness (aspect)
    "s_ghi":   0.130,   # solar irradiation
}

# ----------------------------------------------------------------------
p = gpd.read_file(GPKG, layer="parcels_full")

# GHI is scored relative to the spread across these parcels
GMIN, GMAX = p["ghi_mean"].min(), p["ghi_mean"].max()

# --- 1-5 scoring functions ---
# slope: flatter is better (your tiers)
p["s_slope"] = np.select(
    [p.slope_mean <= 3, p.slope_mean <= 5, p.slope_mean <= 7, p.slope_mean <= 10],
    [5, 4, 3, 2], default=1)

# southness: +1 (south or flat) best, -1 (north) worst, linear
p["s_south"] = np.clip(3 + 2 * p.south_mean, 1, 5)

# GHI: scaled across parcels, sunniest = 5
p["s_ghi"] = 1 + 4 * (p.ghi_mean - GMIN) / (GMAX - GMIN)

# substation distance: nearer is better
p["s_sub"] = np.select(
    [p.substation_dist_m < 1000, p.substation_dist_m < 2500,
     p.substation_dist_m < 5000, p.substation_dist_m < 8000],
    [5, 4, 3, 2], default=1)

# EEG corridor: inside = 5, graded down by distance outside
p["s_eeg"] = np.select(
    [p.eeg_corridor_dist_m <= 0, p.eeg_corridor_dist_m < 250,
     p.eeg_corridor_dist_m < 500, p.eeg_corridor_dist_m < 1000],
    [5, 4, 3, 2], default=1)

# --- weighted sum ---
p["TOTAL"] = sum(p[k] * w for k, w in WEIGHTS.items()).round(3)
p["score_100"] = ((p["TOTAL"] - 1) / 4 * 100).round(1)   # rescale 1-5 -> 0-100
p["rank"] = p["TOTAL"].rank(ascending=False, method="min").astype(int)

# --- report ---
print(f"scored {len(p)} parcels")
print(f"TOTAL  min/median/max: {p.TOTAL.min():.2f} / {p.TOTAL.median():.2f} / {p.TOTAL.max():.2f}")
print("\n--- TOP 10 parcels ---")
cols = ["rank", "TOTAL", "s_eeg", "s_sub", "s_slope", "s_south", "s_ghi",
        "substation_dist_m", "in_eeg_corridor"]
cols = [c for c in cols if c in p.columns]
print(p.sort_values("rank")[cols].head(10).to_string(index=False))

p.to_file(OUT, layer="parcels_final", driver="GPKG")
print(f"\nDone. Wrote scored parcels to:\n{OUT}")
