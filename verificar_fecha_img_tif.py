# -*- coding: utf-8 -*-

import os
import re
import psycopg2
from datetime import datetime


# ============================================================
# CONFIGURACION
# ============================================================

CARPETA_TIFF = r"G:\tiffs\geoserver\2023"

PG_HOST = "localhost"
PG_PORT = 5434
PG_DATABASE = "cmpc"
PG_USER = "postgres"
PG_PASSWORD = "asdf"


FECHA_INICIO = "2023-01-01"
FECHA_FIN = "2023-12-31"

TIPO = "SWC4"


# ============================================================
# REGEX PARA LOS TIFF
#
# Ejemplo:
#
# 01012022_swc4_26.tiff
# 15062022_xxx_01.tiff
#
# Se toma solamente DDMMYYYY
# ============================================================

PATRON_TIFF = re.compile(
    r"^(\d{2})(\d{2})(\d{4})_.*\.tif$",
    re.IGNORECASE
)


# ============================================================
# CONECTAR POSTGRESQL
# ============================================================

def obtener_fechas_postgresql():

    print("=" * 70)
    print("CONSULTANDO POSTGRESQL")
    print("=" * 70)

    conexion = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )

    cursor = conexion.cursor()

    sql = """
        SELECT fecha
        FROM cmpc.disponible_fechas
        WHERE tipo = %s
          AND fecha >= %s
          AND fecha <= %s
        ORDER BY fecha;
    """

    cursor.execute(
        sql,
        (
            TIPO,
            FECHA_INICIO,
            FECHA_FIN
        )
    )

    fechas = set()

    for fila in cursor:

        fecha = fila[0]

        if fecha is None:
            continue

        # Si PostgreSQL devuelve datetime/date
        try:
            fecha = fecha.date()
        except:
            pass

        fechas.add(fecha)

    cursor.close()
    conexion.close()

    print("Fechas encontradas en PostgreSQL: {0}".format(
        len(fechas)
    ))

    return fechas


# ============================================================
# LEER TIFF
# ============================================================

def buscar_tiff():

    print()
    print("=" * 70)
    print("BUSCANDO TIFF")
    print("=" * 70)

    tiff_por_fecha = {}

    cantidad_archivos = 0
    cantidad_validos = 0

    for raiz, carpetas, archivos in os.walk(CARPETA_TIFF):

        for nombre in archivos:

            if not nombre.lower().endswith(".tif"):
                continue

            cantidad_archivos += 1

            m = PATRON_TIFF.match(nombre)

            if not m:
                print(
                    "[FORMATO NO RECONOCIDO] {0}".format(
                        os.path.join(raiz, nombre)
                    )
                )

                continue

            dia = int(m.group(1))
            mes = int(m.group(2))
            anio = int(m.group(3))

            try:

                fecha = datetime(
                    anio,
                    mes,
                    dia
                ).date()

            except ValueError:

                print(
                    "[FECHA INVALIDA] {0}".format(
                        os.path.join(raiz, nombre)
                    )
                )

                continue

            ruta = os.path.join(
                raiz,
                nombre
            )

            cantidad_validos += 1

            if fecha not in tiff_por_fecha:

                tiff_por_fecha[fecha] = []

            tiff_por_fecha[fecha].append(
                ruta
            )

    print(
        "Archivos TIFF encontrados: {0}".format(
            cantidad_archivos
        )
    )

    print(
        "TIFF con fecha valida: {0}".format(
            cantidad_validos
        )
    )

    print(
        "Fechas diferentes encontradas en TIFF: {0}".format(
            len(tiff_por_fecha)
        )
    )

    return tiff_por_fecha


# ============================================================
# COMPARAR
# ============================================================

def comparar(fechas_pg, tiff_por_fecha):

    print()
    print("=" * 70)
    print("COMPARACION")
    print("=" * 70)

    # --------------------------------------------------------
    # FECHAS QUE ESTAN EN PG Y TIENEN TIFF
    # --------------------------------------------------------

    fechas_con_tiff = (
        fechas_pg.intersection(
            set(tiff_por_fecha.keys())
        )
    )

    # --------------------------------------------------------
    # FECHAS QUE ESTAN EN PG PERO NO TIENEN TIFF
    # --------------------------------------------------------

    fechas_sin_tiff = (
        fechas_pg.difference(
            set(tiff_por_fecha.keys())
        )
    )

    # --------------------------------------------------------
    # TIFF CUYA FECHA NO EXISTE EN PG
    # --------------------------------------------------------

    tiff_sin_pg = (
        set(tiff_por_fecha.keys()).difference(
            fechas_pg
        )
    )

    # --------------------------------------------------------
    # RESULTADOS
    # --------------------------------------------------------

    print()
    print("RESUMEN")
    print("-" * 70)

    print(
        "Fechas PostgreSQL:       {0}".format(
            len(fechas_pg)
        )
    )

    print(
        "Fechas con TIFF:         {0}".format(
            len(fechas_con_tiff)
        )
    )

    print(
        "Fechas SIN TIFF:         {0}".format(
            len(fechas_sin_tiff)
        )
    )

    print(
        "Fechas TIFF sin PG:      {0}".format(
            len(tiff_sin_pg)
        )
    )

    # ========================================================
    # FECHAS SIN TIFF
    # ========================================================

    print()
    print("=" * 70)
    print("❌ FECHAS DE POSTGRESQL SIN IMAGEN TIFF")
    print("=" * 70)

    if not fechas_sin_tiff:

        print("No existen fechas faltantes.")

    else:

        for fecha in sorted(fechas_sin_tiff):

            print(
                "{0}  ->  FALTA TIFF".format(
                    fecha.strftime("%Y-%m-%d")
                )
            )

    # ========================================================
    # TIFF SIN REGISTRO EN POSTGRESQL
    # ========================================================

    print()
    print("=" * 70)
    print("⚠️ TIFF CUYA FECHA NO EXISTE EN POSTGRESQL")
    print("=" * 70)

    if not tiff_sin_pg:

        print("No existen TIFF adicionales.")

    else:

        for fecha in sorted(tiff_sin_pg):

            print()
            print(
                "{0}".format(
                    fecha.strftime("%Y-%m-%d")
                )
            )

            for ruta in tiff_por_fecha[fecha]:

                print(
                    "    {0}".format(
                        ruta
                    )
                )

    # ========================================================
    # TIFF ENCONTRADOS
    # ========================================================

    print()
    print("=" * 70)
    print("✅ FECHAS DE POSTGRESQL CON TIFF")
    print("=" * 70)

    for fecha in sorted(fechas_con_tiff):

        print()
        print(
            "{0}".format(
                fecha.strftime("%Y-%m-%d")
            )
        )

        for ruta in tiff_por_fecha[fecha]:

            print(
                "    {0}".format(
                    ruta
                )
            )

    return fechas_sin_tiff


# ============================================================
# MAIN
# ============================================================

def main():

    if not os.path.exists(CARPETA_TIFF):

        print(
            "ERROR: No existe la carpeta:"
        )

        print(
            CARPETA_TIFF
        )

        return

    try:

        fechas_pg = obtener_fechas_postgresql()

        tiff_por_fecha = buscar_tiff()

        faltantes = comparar(
            fechas_pg,
            tiff_por_fecha
        )

        print()
        print("=" * 70)
        print("PROCESO TERMINADO")
        print("=" * 70)

        print(
            "Total fechas faltantes: {0}".format(
                len(faltantes)
            )
        )

    except Exception as e:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)

        print(
            str(e)
        )


if __name__ == "__main__":

    main()