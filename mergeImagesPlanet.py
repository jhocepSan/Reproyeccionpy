# -*- coding: utf-8 -*-
import os
from qgis.core import *
from PyQt5.QtGui import QColor
import processing

feedback = QgsProcessingFeedback()
directorio = r"E:\ArcGisTrabajo\Miselanios\quadw"
#shapefile=r"E:\ArcGisTrabajo\Miselanios\segunda_arear.shp"
nombre_carpeta = "ndviUnido"
ejecutando = True
finalLista = []
for raiz, directorios, archivos in os.walk(directorio):
    if os.path.basename(raiz).lower() == "ndviconvert":
        os.makedirs(os.path.join(os.path.dirname(os.path.dirname(raiz)),f'{nombre_carpeta}'), exist_ok=True)
        tiff_files = [os.path.join(raiz,f) for f in archivos if f.lower().endswith(".tif")]
        name_arch = os.path.normpath(raiz).split(os.sep)
        param_nombre='ndvi_'+name_arch[-4]+"_"+name_arch[-3]+"_"+name_arch[-2]
        output_mosaic = os.path.join(
            os.path.dirname(os.path.dirname(raiz)),
            nombre_carpeta,
            f"{param_nombre}.tif"
        )
        output_mosaic = os.path.normpath(output_mosaic)
        print(f"PROCESANDO EL ARCHIVO {output_mosaic}")
        if len(tiff_files)!=0:
            try:
                result = processing.run("gdal:merge", 
                    {'INPUT':tiff_files,
                    'PCT':False,'SEPARATE':False,
                    'NODATA_INPUT':None,'NODATA_OUTPUT':None,
                    'OPTIONS':'','EXTRA':'','DATA_TYPE':5,
                    'OUTPUT':output_mosaic})
                #os.makedirs(os.path.join(os.path.dirname(os.path.dirname(raiz)),f'{nombre_carpeta}c'), exist_ok=True)
            except:
                print(f"algo malo paso con el archivo {output_mosaic}")
            """
            output_mosaico = os.path.join(
                os.path.dirname(os.path.dirname(raiz)),
                f'{nombre_carpeta}c',
                f"{param_nombre}.tif"
            )
            print(f"PROCESANDO EL ARCHIVO {output_mosaic}")
            print("Verificando raster merge...")
            if not os.path.exists(output_mosaic):
                print("ERROR: el merge NO se generó:", output_mosaic)
                continue

            print("Merge OK:", output_mosaic)

            # Verificar CRS del raster (debug)
            layer_test = QgsRasterLayer(output_mosaic, "test")
            if not layer_test.isValid():
                print("ERROR: El raster merge NO es válido:", output_mosaic)
                continue

            print("CRS del raster:", layer_test.crs().authid())
            
            # Ejecutar clip
            print("Ejecutando clip...")
            try:
                result_clip = processing.run("gdal:cliprasterbymasklayer", 
                        {'INPUT':output_mosaic,
                        'MASK':shapefile,
                        'SOURCE_CRS':None,'TARGET_CRS':None,
                        'TARGET_EXTENT':None,
                        'NODATA':-999,'ALPHA_BAND':False,
                        'CROP_TO_CUTLINE':False,'KEEP_RESOLUTION':False,
                        'SET_RESOLUTION':True,'X_RESOLUTION':None,
                        'Y_RESOLUTION':None,'MULTITHREADING':False,
                        'OPTIONS':'','DATA_TYPE':0,'EXTRA':'',
                        'OUTPUT':output_mosaico})
                print("Clip terminado.")
                print("¿Existe el archivo final?:", os.path.exists(output_mosaico))

            except Exception as e:
                print("ERROR EN CLIP:", e)
            """
print("termino los procesos")