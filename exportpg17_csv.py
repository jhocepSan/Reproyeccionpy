import os
import subprocess
from datetime import datetime, timedelta

# === CONFIGURACIÓN ===
psql_path = r"C:\Program Files\PostgreSQL\17\bin\psql.exe"
host = "localhost"
port = 5433
user = "postgres"
db = "cmpc"
password = "asdf"

# Carpeta de salida
out_folder = r"G:\prueba"

# Fechas
fecha_inicio = datetime(2025, 10, 28)
fecha_fin = datetime(2025, 11, 5)
dias_intervalo = 10

# Variable de entorno para contraseña
env = os.environ.copy()
env["PGPASSWORD"] = password

contador = 0
fecha_actual = fecha_inicio

while fecha_actual <= fecha_fin:
    fecha_final = fecha_actual + timedelta(days=dias_intervalo - 1)
    if fecha_final > fecha_fin:
        fecha_final = fecha_fin

    # sufijo "u", "uu", "uuu", etc.
    sufijo = "u" * contador
    nombre_archivo = f"utbswc25r{sufijo}.csv"
    ruta_csv = os.path.join(out_folder, nombre_archivo)

    # Comando SQL
    sql = (
        f"\\COPY (SELECT gid_poligono, fecha, (valor/100)-273.15 AS valor,tipo "
        f"FROM cmpc.estadistica_tem_utb "
        f"WHERE fecha BETWEEN '{fecha_actual.date()}' AND '{fecha_final.date()}') "
        f"TO '{ruta_csv}' CSV HEADER"
    )
    '''
    sql = (
        f"\\COPY (SELECT gid_poligono, fecha, (valor/1000) AS valor "
        f"FROM cmpc.estadistica_swc_utb "
        f"WHERE fecha BETWEEN '{fecha_actual.date()}' AND '{fecha_final.date()}') "
        f"TO '{ruta_csv}' CSV HEADER"
    )'''

    # Ejecutar psql
    print(f"Exportando {nombre_archivo} ({fecha_actual.date()} → {fecha_final.date()})")
    
    subprocess.run(
        [
            psql_path,
            "-h", host,
            "-p", str(port),
            "-U", user,
            "-d", db,
            "-c", sql,
        ],
        env=env,
        check=True
    )

    # Avanzar
    contador += 1
    fecha_actual = fecha_final + timedelta(days=1)

print("✅ Exportación completa.")
