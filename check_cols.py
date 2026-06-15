import geopandas as gpd
import pandas as pd

GDB = r"C:\Solar_Sites_Wetterau\arcgis\SolarSuitabilityWetterau.gdb"
p = gpd.read_file(GDB, layer="parcels_scored")

print("COLUMNS:", list(p.columns))
print()
pd.set_option("display.max_columns", None, "display.width", 200)
print(p.drop(columns="geometry").head(2).to_string())