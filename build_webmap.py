"""
build_webmap.py
Interactive Leaflet web map of the solar suitability analysis.

Layers (all toggleable except parcels):
  - Scored parcels, coloured by suitability (clickable for details)
  - Study area outline
  - Protected areas (simplified)        [off by default]
  - Forests >=3ha (simplified)          [off by default]
  - Existing solar parks                [off by default]

Big exclusion polygons are simplified so the map stays fast in a browser.
Output: a single self-contained index.html.

Needs: folium  (pip install folium)
"""

import os
import geopandas as gpd
import folium

GDB = r"C:\Solar_Sites_Wetterau\arcgis\SolarSuitabilityWetterau.gdb"
GPKG = r"C:\Solar_Sites_Wetterau\data\processed\parcels_final.gpkg"
SOLAR = r"C:\Solar_Sites_Wetterau\data\processed\existing_solar.gpkg"
OUT = r"C:\Solar_Sites_Wetterau\webmap\index.html"

SIMPLIFY_M = 40   # metres of tolerance; bigger = lighter file, coarser edges


def load(path, layer, simplify=False):
    """Read a layer, optionally simplify (in metres), return WGS84."""
    g = gpd.read_file(path, layer=layer)
    if simplify:
        g["geometry"] = g.geometry.simplify(SIMPLIFY_M)  # in CRS units (m)
    return g.to_crs(4326)


def color(v):
    if v >= 4.0:
        return "#1a6b1a"
    if v >= 3.5:
        return "#4ca64c"
    if v >= 3.0:
        return "#86c986"
    if v >= 2.5:
        return "#c0e3c0"
    return "#e8f4e8"


# --- scored parcels (the main layer) ---
p = load(GPKG, "parcels_final")
c = p.geometry.union_all().centroid
m = folium.Map(location=[c.y, c.x], zoom_start=10, tiles="CartoDB positron")

# bundle all parcels into ONE layer so they don't flood the layer control
parcels_fg = folium.FeatureGroup(name="Suitability parcels")
for _, r in p.iterrows():
    eeg = "Yes" if r.get("in_eeg_corridor", 0) in (1, True) else "No"
    popup_html = f"""
    <b>Rank #{int(r['rank'])} of 197</b><br>
    Suitability score: <b>{r['TOTAL']:.2f}</b> / 5<br>
    <hr style='margin:4px 0'>
    Mean slope: {r['slope_mean']:.1f}&deg;<br>
    Substation distance: {r['substation_dist_m']:.0f} m<br>
    Inside EEG corridor: {eeg}
    """
    folium.GeoJson(
        r.geometry,
        style_function=lambda x, col=color(r["TOTAL"]): {
            "fillColor": col, "color": "#333", "weight": 1, "fillOpacity": 0.85},
        tooltip=f"Rank {int(r['rank'])} | Score {r['TOTAL']:.2f}",
        popup=folium.Popup(popup_html, max_width=260),
    ).add_to(parcels_fg)
parcels_fg.add_to(m)

# --- study area outline ---
try:
    sa = gpd.read_file(r"C:\Solar_Sites_Wetterau\arcgis\study area.shp").to_crs(4326)
    sa = sa[["geometry"]]  # drop all attribute columns (incl. the date that breaks JSON)
    folium.GeoJson(
        sa, name="Study area",
        style_function=lambda x: {"fillOpacity": 0, "color": "#000", "weight": 2.5},
    ).add_to(m)
except Exception as e:
    print("(study area skipped:", e, ")")

# --- protected areas (simplified, toggle off) ---
try:
    pa = load(GDB, "protected_all", simplify=True)
    folium.GeoJson(
        pa, name="Protected areas", show=False,
        style_function=lambda x: {"fillColor": "#7e57c2", "color": "#5e35b1",
                                  "weight": 1, "fillOpacity": 0.4},
        tooltip="Protected area (Natura 2000 / NSG) - excluded",
    ).add_to(m)
except Exception as e:
    print("(protected areas skipped:", e, ")")

# --- forests >=3ha (simplified, toggle off) ---
try:
    fo = load(GDB, "forest_large", simplify=True)
    folium.GeoJson(
        fo, name="Forests (>=3ha)", show=False,
        style_function=lambda x: {"fillColor": "#f1c40f", "color": "#d4ac0d",
                                  "weight": 1, "fillOpacity": 0.5},
        tooltip="Forest - excluded",
    ).add_to(m)
except Exception as e:
    print("(forests skipped:", e, ")")

# --- existing solar parks (toggle off) ---
try:
    s = load(SOLAR, "existing_solar")
    fg = folium.FeatureGroup(name="Existing solar parks", show=False)
    for _, r in s.iterrows():
        folium.CircleMarker(
            [r.geometry.y, r.geometry.x], radius=4,
            color="#c0392b", fill=True, fill_opacity=0.9,
            tooltip="Existing solar park (MaStR)").add_to(fg)
    fg.add_to(m)
except Exception as e:
    print("(existing solar skipped:", e, ")")

# --- legend ---
legend = """
<div style="position:fixed; bottom:25px; left:25px; z-index:9999;
  background:white; padding:10px 12px; border:1px solid #999; border-radius:5px;
  font:13px sans-serif; line-height:1.5">
<b>Suitability score</b><br>
<span style="background:#1a6b1a;width:12px;height:12px;display:inline-block"></span> Very High (4.0+)<br>
<span style="background:#4ca64c;width:12px;height:12px;display:inline-block"></span> High (3.5-4.0)<br>
<span style="background:#86c986;width:12px;height:12px;display:inline-block"></span> Moderate (3.0-3.5)<br>
<span style="background:#c0e3c0;width:12px;height:12px;display:inline-block"></span> Low (2.5-3.0)<br>
<span style="background:#e8f4e8;width:12px;height:12px;display:inline-block"></span> Very Low (&lt;2.5)<br>
<hr style="margin:5px 0">
<span style="background:#7e57c2;width:12px;height:12px;display:inline-block"></span> Protected area<br>
<span style="background:#f1c40f;width:12px;height:12px;display:inline-block"></span> Forest<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend))
folium.LayerControl(collapsed=False).add_to(m)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
m.save(OUT)
print(f"Done. Open this in a browser:\n{OUT}")