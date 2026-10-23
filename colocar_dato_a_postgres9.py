import os
import subprocess
from pathlib import Path

# === CONFIGURACIÓN ===
db = "trabajo"
user = "postgres"
password = "asdf"
schema = "cmpc"
host = "localhost"
port = 5432
folder = r"G:\prueba"

# Ruta a ogr2ogr.exe (ajústala a tu instalación de QGIS o OSGeo)
ogr2ogr_path = r"C:\Program Files\QGIS 3.28.4\bin\ogr2ogr.exe"

dbfs = sorted([f for f in os.listdir(folder) if f.lower().endswith(".dbf")])
contador = 1

for f in dbfs:
    base_name = 'utb_utim25uuu'
    sufijo = "u" * contador
    table_name = f"{base_name}{sufijo}"
    ruta_dbf = str(Path(folder) / f)

    print(f"Importando {f} → {table_name}")

    conn = f"PG:host={host} port={port} dbname={db} user={user} password={password}"
    cmd = [
        ogr2ogr_path,
        "-f", "PostgreSQL",
        conn,
        ruta_dbf,
        "-nln", f"{schema}.{table_name}",
        "-nlt", "NONE",   # SIN GEOMETRÍA
        "-overwrite"      # Sobrescribe tabla si ya existe
    ]

    subprocess.run(cmd, check=True)
    contador += 1  
    

print("✅ Importación completada sin campo the_geom.")
