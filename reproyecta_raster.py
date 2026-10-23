import rasterio,os
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import shapes
import geopandas as gpd
import numpy as np
from shapely.geometry import shape
import pandas as pd
from pathlib import Path

def reproject_raster(input_path, output_path, dst_crs='EPSG:32719'):
    """
    Reproject raster to UTM Zone 18S (suitable for Chile) with 100m pixels
    """
    with rasterio.open(input_path) as src:
        src_nodata = 0
        # Calculate transform for new projection
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, 
            *src.bounds,resolution=20
        )
        
        # Update metadata for the output file
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
        
        # Create the reprojected raster
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
    input_path = Path(r"G:/temPirque")
    output_path = Path(r"G:/temPirque/reproyectado")
    os.environ['PROJ_LIB'] = "C:/Users/sajhy/.conda/envs/trabajpy/Library/share/proj"
    archivos = [archivo.name for archivo in input_path.glob("*.tif")]
    # Step 1: Reproject the raster to UTM Zone 19S with 100m pixels
    print("cantidad archivos",len(archivos))
    for nombre in archivos:
        #en caso de que no tenga formato ddmmyyyy los tif a convertir
        #nombreSalida=nombre.split('.')[0].split('-')
        #nombrefinal = f"{nombreSalida[2]}{nombreSalida[1]}{nombreSalida[0]}_swc.tif"
        direin=os.path.join(input_path,nombre)
        dirout=os.path.join(output_path,nombre)
        try:
            if not os.path.exists(dirout):
                reproject_raster(direin, dirout)
        except Exception as error:
            print("No procesado",nombre)
            print(error)

    print("termino todo los archivos")
    # Step 3: Analyze areas of pixels and polygons
    #analyze_areas()

if __name__ == "__main__":
    main()
