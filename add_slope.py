import geopandas as gpd

GDB  = r"C:\Solar_Sites_Wetterau\arcgis\SolarSuitabilityWetterau.gdb"
GPKG = r"C:\Solar_Sites_Wetterau\data\processed\parcels_full.gpkg"

# read slope (the 'MEAN' column) from the gdb, in the same row order
src = gpd.read_file(GDB, layer="parcels_scored").reset_index(drop=True)
slope = src["MEAN"].values

# read the gpkg, attach slope, save back
p = gpd.read_file(GPKG, layer="parcels_full").reset_index(drop=True)
assert len(p) == len(slope), f"row mismatch {len(p)} vs {len(slope)}"
p["slope_mean"] = slope
p.to_file(GPKG, layer="parcels_full", driver="GPKG")

print("added slope_mean. columns now:")
print(list(p.columns))
print(p[["pid", "slope_mean", "south_mean", "ghi_mean"]].head().to_string(index=False))