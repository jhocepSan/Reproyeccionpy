import rasterio, os
from rasterio.warp import reproject, Resampling, aligned_target
import geopandas as gpd
import numpy as np
import pandas as pd
from pathlib import Path

def reproject_raster(input_path, output_path, reference_raster, dst_crs='EPSG:32718', resolution=100):
    with rasterio.open(reference_raster) as ref:
        ref_transform = ref.transform
        ref_width = ref.width
        ref_height = ref.height

        # Crear transform alineado a la grilla del raster de referencia pero con resolución deseada
        dst_transform, dst_width, dst_height = aligned_target(
            ref_transform,
            ref_width,
            ref_height,
            resolution  # 👈 aquí va directo, sin "res="
        )

    # Abrir raster a reproyectar
    with rasterio.open(input_path) as src:
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': dst_transform,
            'width': dst_width,
            'height': dst_height,
            'nodata': src.nodata if src.nodata is not None else 0,
            'compress': 'LZW',
            'predictor': 2,
            'tiled': True,
            'dtype': src.dtypes[0]
        })

        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest
                )
    print(f"✅ Reproyectado: {output_path}")

def main():
    input_path = Path(r"G:/cmpc/agua100")
    output_path = Path(r"G:/cmpc/agua100/reproyectado")
    os.environ['PROJ_LIB'] = "C:/Users/sajhy/.conda/envs/trabajpy/Library/share/proj"

    archivos = [archivo.name for archivo in input_path.glob("*.tif")]
    print("cantidad archivos:", len(archivos))

    # Raster de referencia (20x20m)
    reference_raster = Path(r"E:/extecmpcriego2/repro/01012024_1330_tem5_26.tif")#E:/AgostoRiego/swc/reproyectados/2025/07/01072025_swc4.tif")

    for nombre in archivos:
        direin = os.path.join(input_path, nombre)
        dirout = os.path.join(output_path, nombre)
        try:
            if not os.path.exists(dirout):
                reproject_raster(
                    direin, dirout,
                    reference_raster=reference_raster,
                    dst_crs='EPSG:32718',
                    resolution=100  # queremos salida de 100m
                )
        except Exception as error:
            print("No procesado", nombre)
            print(error)
        break  # ⚠️ ojo: quita este break si quieres procesar TODOS los archivos

    print("termino todo los archivos")

if __name__ == "__main__":
    main()
