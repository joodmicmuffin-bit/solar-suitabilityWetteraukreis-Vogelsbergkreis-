"""
distances.py
Computes the two DISTANCE criteria for each parcel and writes them to a CSV
you can join back onto parcels_scored in ArcGIS.

  1. substation_dist_m : straight-line distance to the nearest substation
                         (grid-connection cost proxy)
  2. eeg_corridor_dist_m : distance to the EEG 500 m Flaechenkulisse corridor
                         along motorways + 2-track rail (0 = inside the corridor)
  3. in_eeg_corridor    : True if the parcel touches the corridor at all

Everything is done in EPSG:25832 (meters) so distances are real meters.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.strtree import STRtree

# ----------------------------------------------------------------------
# paths
GDB = r"C:\Solar_Sites_Wetterau\arcgis\SolarSuitabilityWetterau.gdb"
OSM = r"C:\Solar_Sites_Wetterau\data\raw\hessen_osm"
RAW = r"C:\Solar_Sites_Wetterau\data\raw"
STUDY = r"C:\Solar_Sites_Wetterau\arcgis\study area.shp"
OUT = r"C:\Solar_Sites_Wetterau\data\processed\parcels_full.gpkg"

CRS = 25832
EEG_BUFFER = 500   # meters: EEG corridor width along qualifying roads/rail
ANBAU = 40         # meters: Autobahn Anbauverbotszone carved out of the inside

# which OSM fclass values count for the EEG corridor
MOTORWAY = {"motorway", "motorway_link", "trunk", "trunk_link"}
RAIL = {"rail"}   # main-line rail (OSM fclass); we treat these as the 2-track lines

# ----------------------------------------------------------------------
# load everything, reproject to 25832
print("loading data...")
parcels = gpd.read_file(GDB, layer="parcels_scored").to_crs(CRS)
parcels = parcels.reset_index(drop=True)
parcels["pid"] = range(1, len(parcels) + 1)   # our own stable ID, 1..197
study = gpd.read_file(STUDY).to_crs(CRS)
subs = gpd.read_file(rf"{RAW}\substations.geojson").to_crs(CRS)
roads = gpd.read_file(rf"{OSM}\gis_osm_roads_free_1.shp").to_crs(CRS)
rails = gpd.read_file(rf"{OSM}\gis_osm_railways_free_1.shp").to_crs(CRS)

# clip the big OSM files down to the study area (much faster, smaller)
study_geom = study.union_all()
roads = roads[roads.intersects(study_geom)]
rails = rails[rails.intersects(study_geom)]

# substations: some OSM features are polygons -> use centroids as the point
subs["geometry"] = subs.geometry.centroid
print(f"  parcels: {len(parcels)}, substations: {len(subs)}, "
      f"roads: {len(roads)}, rails: {len(rails)}")

# ----------------------------------------------------------------------
# 1. SUBSTATION DISTANCE  (nearest neighbor via STRtree)
sub_geoms = list(subs.geometry)
tree = STRtree(sub_geoms)
parcels["substation_dist_m"] = [
    round(g.distance(sub_geoms[tree.nearest(g)]), 1) for g in parcels.geometry
]

# ----------------------------------------------------------------------
# 2. EEG 500 m CORRIDOR
mot = roads[roads["fclass"].isin(MOTORWAY)]
rail = rails[rails["fclass"].isin(RAIL)]
qualifying = pd.concat([mot.geometry, rail.geometry])

if len(qualifying) == 0:
    print("WARNING: no qualifying motorway/rail found in study area!")
    parcels["eeg_corridor_dist_m"] = np.nan
    parcels["in_eeg_corridor"] = False
else:
    lines = qualifying.union_all()
    corridor = lines.buffer(EEG_BUFFER).difference(lines.buffer(ANBAU))
    parcels["eeg_corridor_dist_m"] = [
        round(g.distance(corridor), 1) for g in parcels.geometry
    ]
    parcels["in_eeg_corridor"] = [g.intersects(corridor) for g in parcels.geometry]

# ----------------------------------------------------------------------
# keep a clean set of columns: our id, the 3 terrain criteria, the 2 distances,
# plus area/compactness if present, plus geometry
wanted = ["pid", "slope_mean", "south_mean", "ghi_mean",
          "substation_dist_m", "eeg_corridor_dist_m", "in_eeg_corridor",
          "compact", "Shape_Area"]
cols = [c for c in wanted if c in parcels.columns] + ["geometry"]
clean = parcels[cols].copy()

# ----------------------------------------------------------------------
# sanity output + write
print("\n--- sanity check (first rows) ---")
show = [c for c in ["pid", "substation_dist_m",
                    "eeg_corridor_dist_m", "in_eeg_corridor"] if c in clean.columns]
print(clean[show].head(8).to_string(index=False))
print(f"\nsubstation dist  min/median/max: "
      f"{parcels.substation_dist_m.min():.0f} / "
      f"{parcels.substation_dist_m.median():.0f} / "
      f"{parcels.substation_dist_m.max():.0f} m")
print(f"parcels inside EEG corridor: {parcels.in_eeg_corridor.sum()} / {len(parcels)}")

clean.to_file(OUT, layer="parcels_full", driver="GPKG")
print(f"\nDone. Wrote complete parcel layer (terrain + distances) to:\n{OUT}")
