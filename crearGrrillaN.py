import rasterio
from shapely.geometry import Polygon
import geopandas as gpd

# Ruta del archivo ráster
raster_path = r"E:\\Sensors\\repro2\\01112022_swc.tif"
output_shapefile = r"E:\\Sensors\\repro2\\grilla_pixeles.shp"

# Leer el ráster
with rasterio.open(raster_path) as src:
    raster_data = src.read(1)  # Leer la primera banda
    transform = src.transform  # Obtener la transformación del ráster
    crs = src.crs  # Sistema de referencia espacial

# Crear los polígonos individuales
polygons = []
values = []

rows, cols = raster_data.shape
for row in range(rows):
    for col in range(cols):
        # Coordenadas del píxel
        value = raster_data[row, col]
        if value != src.nodata:  # Ignorar valores nodata
            x_min, y_min = transform * (col, row)
            x_max, y_max = transform * (col + 1, row + 1)
            
            # Crear un polígono rectangular para cada píxel
            polygon = Polygon([(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)])
            polygons.append(polygon)
            values.append(value)

# Crear un GeoDataFrame
gdf = gpd.GeoDataFrame({"geometry": polygons, "value": values}, crs=crs)

# Guardar como shapefile
gdf.to_file(output_shapefile)
print(f"Polígonos guardados en {output_shapefile}")