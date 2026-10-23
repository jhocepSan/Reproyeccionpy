import rasterio, os
from rasterio.warp import reproject, Resampling, aligned_target,calculate_default_transform
from rasterio.transform import Affine
import geopandas as gpd
import numpy as np
import pandas as pd
from pathlib import Path

def reproject_raster(input_path, output_path, reference_raster, dst_crs='EPSG:32718', resolution=100):
    with rasterio.open(reference_raster) as ref:
        ref_transform = ref.transform
        ref_crs = ref.crs
        
        # EL TRUCO: Extraemos el origen exacto (x_min, y_max) del de 20m
        # ref_transform[2] es x_min (oeste)
        # ref_transform[5] es y_max (norte)
        dst_transform = Affine(resolution, 0.0, ref_transform[2],
                               0.0, -resolution, ref_transform[5])
        
        # Calculamos dimensiones para cubrir el mismo área
        dst_width = int(np.ceil((ref.bounds.right - ref.bounds.left) / resolution))
        dst_height = int(np.ceil((ref.bounds.top - ref.bounds.bottom) / resolution))

    with rasterio.open(input_path) as src:
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': ref_crs,
            'transform': dst_transform,
            'width': dst_width,
            'height': dst_height,
            'nodata': src.nodata if src.nodata is not None else 0,
            'compress': 'LZW'
        })

        with rasterio.open(output_path, 'w', **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=ref_crs,
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
        #break  # ⚠️ ojo: quita este break si quieres procesar TODOS los archivos

    print("termino todo los archivos")

if __name__ == "__main__":
    main()
