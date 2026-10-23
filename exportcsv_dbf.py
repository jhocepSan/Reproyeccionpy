# -*- coding: utf-8 -*-
import arcpy
import os

folder = r"G:\prueba"
carpeta_salida = r"G:\prueba"

for archivo in os.listdir(folder):
    if archivo.lower().endswith(".csv"):
        ruta_csv = os.path.join(folder, archivo)
        nombre_salida = os.path.splitext(archivo)[0] + ".dbf"
        arcpy.TableToTable_conversion(ruta_csv, carpeta_salida, nombre_salida)
        print("✅ {0} → {1}".format(archivo, nombre_salida))
