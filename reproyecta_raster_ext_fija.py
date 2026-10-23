import rasterio,os
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import shapes
import geopandas as gpd
import numpy as np
from shapely.geometry import shape
import pandas as pd
from pathlib import Path

def reproject_raster(input_path, output_path, dst_crs='EPSG:32718', resolution=20, reference_transform=None, reference_width=None, reference_height=None):
    with rasterio.open(input_path) as src:
        if reference_transform is None:
            # Calculamos el transform global para el primer raster
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs,
                src.width, src.height,
                *src.bounds,
                resolution=resolution
            )
        else:
            # Usar el grid de referencia para alinear todos
            transform = reference_transform
            width = reference_width
            height = reference_height
        
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height,
            'nodata': 0,
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
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest
                )

def main():
    # Input and output paths
    #input_path = Path(r"E:/AgostoRiego/swc")
    #input_path = Path(r"G:/cmpc/temperatura")
    input_path = Path(r"G:/cmpc/agua")
    #output_path = Path(r"E:/AgostoRiego/swc/reproprueba")
    #output_path = Path(r"E:/AgostoRiego/temperatura/reproyectado")
    #output_path = Path(r"G:/cmpc/temperatura/reproyectado")
    output_path = Path(r"G:/cmpc/agua/reprop")
    os.environ['PROJ_LIB'] = "C:/Users/sajhy/.conda/envs/trabajpy/Library/share/proj"
    archivos = [archivo.name for archivo in input_path.glob("*.tif")]
    # Step 1: Reproject the raster to UTM Zone 19S with 100m pixels
    print("cantidad archivos",len(archivos))
    #first_raster =Path(r"E:/AgostoRiego/swc/reproyectados/2025/07/01072025_swc4.tif")
    #first_raster =Path(r"E:/extecmpcriego2/repro/01022024_swc4_26.tif")
    first_raster =Path(r"E:/extecmpcriego2/repro/01012024_1330_tem5_26.tif")
    with rasterio.open(first_raster) as src:
        ref_transform, ref_width, ref_height = calculate_default_transform(
            src.crs, 'EPSG:32718',
            src.width, src.height,
            *src.bounds,
            resolution=20
        )
    
    for nombre in archivos:
        #en caso de que no tenga formato ddmmyyyy los tif a convertir
        #nombreSalida=nombre.split('.')[0].split('-')
        #nombrefinal = f"{nombreSalida[2]}{nombreSalida[1]}{nombreSalida[0]}_swc.tif"
        direin=os.path.join(input_path,nombre)
        dirout=os.path.join(output_path,nombre)
        try:
            if not os.path.exists(dirout):
                reproject_raster(
                    direin, dirout,
                    dst_crs='EPSG:32718',
                    resolution=20,
                    reference_transform=ref_transform,
                    reference_width=ref_width,
                    reference_height=ref_height
                )
            else:
                print("Ya procesado")
              
        except Exception as error:
            print("No procesado",nombre)
            print(error)

    
    print("termino todo los archivos")
    # Step 3: Analyze areas of pixels and polygons
    #analyze_areas()

if __name__ == "__main__":
    main()