"""
buffer_existing_solar.py
Turns the 36 existing-solar POINTS into area-matched circular FOOTPRINTS
so they can be erased from the candidate land (a single dot erases nothing).

Each circle's area matches the park's real size:
  - if 'area_ha' is given in MaStR, use it
  - if it's blank, estimate from power at ~1 MW per hectare (Fraunhofer rule)
Circle radius from area:  r = sqrt(area_m2 / pi)

Output: one dissolved footprint layer to erase against in ArcGIS.
"""

import numpy as np
import geopandas as gpd

IN = r"C:\Solar_Sites_Wetterau\data\processed\existing_solar.gpkg"
OUT = r"C:\Solar_Sites_Wetterau\data\processed\existing_solar_buffer.gpkg"

gdf = gpd.read_file(IN, layer="existing_solar")
assert gdf.crs.to_epsg() == 25832, "expected EPSG:25832"

# effective area (ha): real value, else estimated from power at 1 MW/ha
est_from_power = gdf["power_kw"] / 1000.0
area_ha = gdf["area_ha"].fillna(est_from_power)

gdf["area_used"] = area_ha.round(2)
gdf["src"] = np.where(gdf["area_ha"].isna(), "estimated", "reported")

# radius from area, with a small 30 m floor so nothing collapses to a dot
gdf["radius_m"] = np.sqrt(area_ha * 10000 / np.pi).clip(lower=30).round(1)

# grow each point into its own circle, then dissolve to one footprint layer
gdf["geometry"] = gdf.geometry.buffer(gdf["radius_m"])
footprint = gdf.dissolve()

print(f"parks buffered: {len(gdf)}  "
      f"(reported area: {(gdf['src']=='reported').sum()}, "
      f"estimated: {(gdf['src']=='estimated').sum()})")
print(f"total footprint area: {footprint.geometry.area.sum()/10000:.1f} ha")

footprint.to_file(OUT, layer="existing_solar_buffer", driver="GPKG")
print(f"\nDone. Wrote footprint to:\n{OUT}")
