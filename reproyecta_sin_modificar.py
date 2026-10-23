import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

# Rutas de entrada y salida
raster_entrada = "ruta/al/raster_entrada.tif"
raster_salida = "ruta/al/raster_salida_UTM.tif"

# Definir CRS de salida (EPSG:32718)
crs_destino = "EPSG:32718"

# Abrir el raster de entrada
with rasterio.open(raster_entrada) as src:
    # Calcular transformación y nuevos parámetros
    transform, width, height = calculate_default_transform(
        src.crs, crs_destino, src.width, src.height, *src.bounds
    )

    # Definir metadatos del nuevo raster
    kwargs = src.meta.copy()
    kwargs.update({
        "crs": crs_destino,
        "transform": transform,
        "width": width,
        "height": height
    })

    # Crear el nuevo raster reproyectado
    with rasterio.open(raster_salida, "w", **kwargs) as dst:
        for i in range(1, src.count + 1):  # Iterar sobre las bandas
            reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=crs_destino,
                resampling=Resampling.nearest
            )

print(f"✅ Reproyección completada: {raster_salida}")
