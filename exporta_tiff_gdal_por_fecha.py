# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import psycopg2
from datetime import datetime, timedelta

# =========================================================
# CONFIGURACION
# =========================================================
DB_CONFIG = {
    "host": "localhost",
    "port": 5434,
    "dbname": "cmpc",
    "user": "postgres",
    "password": "asdf"
}

OUTPUT_DIR = r"G:\tiffs"

PIXEL_SIZE = 20.0
NODATA = -9999

FECHA_DESDE = "2026-09-10"
FECHA_HASTA = "2026-10-19"

GDAL_RASTERIZE_EXE = "gdal_rasterize"

# Para que se llenen todas las celdas tocadas
ALL_TOUCHED = True


# =========================================================
# UTILIDADES
# =========================================================
def asegurar_carpeta(path):
    if not os.path.exists(path):
        os.makedirs(path)

def verificar_gdal():
    exe = shutil.which(GDAL_RASTERIZE_EXE)
    if exe is None:
        raise RuntimeError(
            f"No se encontró '{GDAL_RASTERIZE_EXE}' en el PATH."
        )
    return exe

def limpiar_variables_pg():
    vars_pg = [
        "PGSERVICE", "PGSERVICEFILE", "PGPASSFILE", "PGCLIENTENCODING",
        "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"
    ]
    for var in vars_pg:
        os.environ.pop(var, None)

def construir_dsn():
    return (
        f"host={DB_CONFIG['host']} "
        f"port={DB_CONFIG['port']} "
        f"dbname={DB_CONFIG['dbname']} "
        f"user={DB_CONFIG['user']} "
        f"password={DB_CONFIG['password']}"
    )

def pg_connection_string():
    return (
        f"PG:host={DB_CONFIG['host']} "
        f"port={DB_CONFIG['port']} "
        f"dbname={DB_CONFIG['dbname']} "
        f"user={DB_CONFIG['user']} "
        f"password={DB_CONFIG['password']}"
    )

def sql_literal_timestamp(dt_obj):
    return dt_obj.strftime("%Y-%m-%d %H:%M:%S")

def fecha_a_nombre(fecha_obj):
    return fecha_obj.strftime("%d%m%Y") + "_swc4_26"


# =========================================================
# CONSULTAS
# =========================================================
def obtener_fechas(conn):
    where_extra = []
    params = []

    if FECHA_DESDE:
        where_extra.append("fecha::date >= %s::date")
        params.append(FECHA_DESDE)

    if FECHA_HASTA:
        where_extra.append("fecha::date <= %s::date")
        params.append(FECHA_HASTA)

    where_clause = ""
    if where_extra:
        where_clause = "WHERE " + " AND ".join(where_extra)

    sql = f"""
        SELECT DISTINCT fecha::date
        FROM cmpc.estadistica_swc_utb
        {where_clause}
        ORDER BY fecha::date;
    """

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [r[0] for r in cur.fetchall()]

def contar_registros_fecha(conn, fecha_obj):
    fecha_ini = datetime.combine(fecha_obj, datetime.min.time())
    fecha_fin = fecha_ini + timedelta(days=1)

    sql = """
        SELECT COUNT(*)
        FROM cmpc.estadistica_swc_utb e
        JOIN public.ri_utbs_riego p
          ON e.gid_poligono = p.gid
        WHERE e.fecha >= %s
          AND e.fecha < %s
          AND e.valor IS NOT NULL
          AND p.the_geom IS NOT NULL;
    """

    with conn.cursor() as cur:
        cur.execute(sql, (fecha_ini, fecha_fin))
        return cur.fetchone()[0]

def obtener_srid(conn):
    sql = """
        SELECT ST_SRID(the_geom)
        FROM public.ri_utbs_riego
        WHERE the_geom IS NOT NULL
        LIMIT 1;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        if not row or row[0] is None:
            raise RuntimeError("No se pudo determinar el SRID de public.ri_utbs_riego.the_geom")
        return row[0]

def obtener_grilla_exacta_ri_utbs(conn):
    """
    Usa la extensión exacta de ri_utbs_riego, sin snap.
    La grilla queda anclada exactamente al origen real de la capa.
    """
    sql = """
        SELECT
            ST_XMin(ext::geometry) AS xmin,
            ST_YMin(ext::geometry) AS ymin,
            ST_XMax(ext::geometry) AS xmax,
            ST_YMax(ext::geometry) AS ymax
        FROM (
            SELECT ST_Extent(the_geom) AS ext
            FROM public.ri_utbs_riego
            WHERE the_geom IS NOT NULL
        ) q;
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    if not row or row[0] is None:
        raise RuntimeError("No se pudo calcular la extensión de public.ri_utbs_riego")

    xmin, ymin, xmax, ymax = [float(v) for v in row]

    ancho = xmax - xmin
    alto = ymax - ymin

    cols_f = ancho / PIXEL_SIZE
    rows_f = alto / PIXEL_SIZE

    cols = round(cols_f)
    rows = round(rows_f)

    tol = 1e-6
    if abs(cols_f - cols) > tol or abs(rows_f - rows) > tol:
        raise RuntimeError(
            f"La extensión no es múltiplo exacto de {PIXEL_SIZE}. "
            f"cols={cols_f}, rows={rows_f}"
        )

    return xmin, ymin, xmax, ymax, cols, rows

def construir_sql_para_fecha(fecha_obj):
    fecha_ini = datetime.combine(fecha_obj, datetime.min.time())
    fecha_fin = fecha_ini + timedelta(days=1)

    fi = sql_literal_timestamp(fecha_ini)
    ff = sql_literal_timestamp(fecha_fin)

    sql = f"""
        SELECT
            p.the_geom,
            e.valor
        FROM cmpc.estadistica_swc_utb e
        JOIN public.ri_utbs_riego p
          ON e.gid_poligono = p.gid
        WHERE e.fecha >= TIMESTAMP '{fi}'
          AND e.fecha < TIMESTAMP '{ff}'
          AND e.valor IS NOT NULL
          AND p.the_geom IS NOT NULL
    """
    return " ".join(sql.split())


# =========================================================
# GDAL
# =========================================================


def generar_tiff_con_gdal(fecha_obj, grilla_fija):
    xmin, ymin, xmax, ymax, cols, rows = grilla_fija
    output_path = os.path.join(OUTPUT_DIR, f"{fecha_a_nombre(fecha_obj)}.tif")
    sql = construir_sql_para_fecha(fecha_obj)

    cmd = [
        GDAL_RASTERIZE_EXE,
        "-of", "GTiff",
        "-ot", "Float32",
        "-a", "valor",
        "-a_nodata", str(NODATA),
        "-te", str(xmin), str(ymin), str(xmax), str(ymax),
        "-ts", str(cols), str(rows),
        # 👉 COMPRESIÓN
        "-co", "COMPRESS=LZW",
        "-co", "PREDICTOR=2",
        "-sql", sql,
    ]

    if ALL_TOUCHED:
        cmd.append("-at")

    cmd.extend([
        pg_connection_string(),
        output_path
    ])

    print("   Comando GDAL:")
    print("   " + " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd))

    print("   Ejecutando gdal_rasterize...")
    resultado = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if resultado.returncode != 0:
        print("   Error GDAL:")
        print(resultado.stderr)
        return None

    return output_path

# =========================================================
# MAIN
# =========================================================
def main():
    asegurar_carpeta(OUTPUT_DIR)
    verificar_gdal()
    limpiar_variables_pg()

    print("Conectando a PostgreSQL...")

    dsn = construir_dsn()
    dsn_visible = dsn.replace(DB_CONFIG["password"], "******")
    print("DSN:", dsn_visible)

    conn = psycopg2.connect(dsn)

    try:
        srid = obtener_srid(conn)
        print(f"SRID detectado: {srid}")

        grilla_fija = obtener_grilla_exacta_ri_utbs(conn)
        xmin, ymin, xmax, ymax, cols, rows = grilla_fija

        print("Grilla exacta de ri_utbs_riego:")
        print(f"   xmin = {xmin}")
        print(f"   ymin = {ymin}")
        print(f"   xmax = {xmax}")
        print(f"   ymax = {ymax}")
        print(f"   cols = {cols}")
        print(f"   rows = {rows}")
        print(f"   pixel_size = {PIXEL_SIZE}")

        fechas = obtener_fechas(conn)
        print(f"Fechas encontradas en el rango: {len(fechas)}")

        if not fechas:
            print("No se encontraron fechas dentro del rango indicado.")
            return

        generados = 0

        for i, fecha_obj in enumerate(fechas, start=1):
            print(f"\n[{i}/{len(fechas)}] Procesando {fecha_obj}...")

            n = contar_registros_fecha(conn, fecha_obj)
            print(f"   Registros con geometría y valor: {n}")

            if n == 0:
                print("   Sin datos útiles para esa fecha.")
                continue

            salida = generar_tiff_con_gdal(fecha_obj, grilla_fija)

            if salida:
                generados += 1
                print(f"   OK -> {salida}")
            else:
                print("   Sin salida")

        print("\nProceso finalizado.")
        print(f"Total TIFF generados: {generados}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()