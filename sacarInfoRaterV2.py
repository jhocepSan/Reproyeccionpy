from psycopg_pool import AsyncConnectionPool
import asyncio,sys
from concurrent.futures import ProcessPoolExecutor
import json
import os
import geopandas as gpd
import numpy as np
import psycopg
import rasterio
from fastapi.encoders import jsonable_encoder
from psycopg.rows import dict_row
from rasterio.features import shapes
from rasterio.mask import mask
from shapely.geometry import shape

os.environ['GDAL_CACHEMAX'] = '64'
os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'TRUE'
import gc
db_config={
    "user": "postgres",
    "password": "asdf",
    "host": "localhost",
    "port": "5434",
    "database": "cmpc"
  }

class ConexionBaseAsync:
    def __init__(self, min_connections, max_connections, dsn):
        self.pool = AsyncConnectionPool(
            conninfo=dsn,
            min_size=min_connections,
            max_size=max_connections,
            open=False,  # No inicies todavía
        )

    async def open(self):
        await self.pool.open()

    async def close(self):
        await self.pool.close()

    def get_connection(self):
        # Devuelve un contexto async seguro
        return self.pool.connection()


# Inicializador global
async def init_async_pool():
    global poolConAsync

    try:
        # Construir DSN
        dsn = (
            f"host={db_config['host']} "
            f"port={db_config['port']} "
            f"dbname={db_config['database']} "
            f"user={db_config['user']} "
            f"password={db_config['password']}"
        )

        poolConAsync = ConexionBaseAsync(min_connections=1, max_connections=30, dsn=dsn)

        await poolConAsync.open()

    except Exception as error:
        print("Error iniciando pool async:", error)
        raise

def procesar_fundo_worker(fundo_geometry, archivo_info):
    """Worker function que corre en un proceso separado."""
    raster_path, fecha, tipot, tipo, gid = archivo_info
    
    try:
        with rasterio.open(raster_path) as src:
            # Optimización: Leer solo la ventana del polígono, no todo el raster
            geom = [shape(fundo_geometry)]
            out_image, out_transform = mask(src, geom, crop=True, nodata=src.nodata)
            band = out_image[0]
            nodata = src.nodata
            
            # Cálculo de métricas
            valid_pixels = band[(band > 0) & (band != nodata)]
            
            if valid_pixels.size == 0:
                return None

            if tipo == 'upf':
                return {
                    "gid": gid, "fecha": fecha,
                    "maximo": float((np.max(valid_pixels)/100)-273.15),
                    "minimo": float((np.min(valid_pixels)/100)-273.15),
                    "promedio": float((np.mean(valid_pixels)/100)-273.15),
                    "acumulado": float((np.sum(valid_pixels)/100)-273.15),
                    "desviacion": float(np.std(valid_pixels)/100),
                    "tipo": "TEMP5" if tipot == '1330' else "TEMP6"
                }
            else:
                # Muestreo rápido (centroide o promedio)
                return {
                    "gid": gid, "fecha": fecha,
                    "valor": float((np.mean(valid_pixels)/100)-273.15),
                    "tipo": "TEMP5" if tipot == '1330' else "TEMP6"
                }
    except Exception as e:
        # print(f"Error procesando {gid}: {e}")
        return None
def procesar_fundo_worker_agua(fundo_geometry, archivo_info):
    """Worker function que corre en un proceso separado."""
    raster_path, fecha, tipot, tipo, gid, fuente = archivo_info
    
    try:
        # Reconstruir la geometría de Shapely al inicio
        geom_obj = shape(fundo_geometry)
        
        with rasterio.open(raster_path) as src:
            nodata = src.nodata
            
            # --- CASO UPF: Análisis completo del polígono ---
            if tipo == 'upf':
                # Reutilizamos geom_obj convirtiéndolo en lista para mask
                out_image, out_transform = mask(src, [geom_obj], crop=True, nodata=nodata)
                band = out_image[0]
                
                valid_pixels = band[(band > 0) & (band != nodata)]
                
                if valid_pixels.size == 0:
                    return None

                return {
                    "gid": gid,
                    "fecha": fecha,
                    "maximo": float(np.max(valid_pixels)/1000),
                    "minimo": float(np.min(valid_pixels)/1000),
                    "promedio": float(np.mean(valid_pixels)/1000),
                    "acumulado": float(np.sum(valid_pixels)/1000),
                    "desviacion": float(np.std(valid_pixels)/1000),
                    "fuente": fuente
                }
            
            # --- CASO UTB: Extracción rápida del píxel en el centroide ---
            else:
                centroide = geom_obj.centroid
                x, y = centroide.x, centroide.y
                
                valor = None
                # rasterio.sample recibe una lista de tuplas (x, y)
                for val_array in src.sample([(x, y)]):
                    # val_array es un arreglo de numpy (ej. [1450])
                    valor = val_array[0] 
                    break
                
                # Validar que el valor extraído sea válido
                if valor is None or valor == nodata or valor <= 0:
                    return None
                  
                return {
                    "gid": gid,
                    "fecha": fecha,
                    "valor": float(valor/1000),
                    "fuente": fuente
                }
                
    except Exception as e:
        # IMPORTANTE: Descomenta esto temporalmente si sigue fallando 
        # para que puedas ver cualquier otro error en consola.
        # print(f"Error procesando GID {gid}: {e}")
        return None
class RasterDatos:
    
    async def ejecutarConsultaJson(self, sql, parametros):
        async with poolConAsync.get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    sql,
                    parametros,
                )
                resultado = await cur.fetchall()
        return resultado
    async def insertarResgistro(self,sql,parametros):
        async with poolConAsync.get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    sql,
                    parametros,
                )
            await conn.commit()
    async def insertarRegistroMasivos(self,sql,lista_parametros):
        if not lista_parametros:
            return
        async with poolConAsync.get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.executemany(
                    sql,
                    lista_parametros,
                )
            await conn.commit()
    
    async def sacarDatosRater(self):
        sqlPredios = "select gid,n_cod_fund,n_cod_roda,ST_AsGeoJSON(the_geom)::json AS geometry from fundos_riego order by gid "
        sqlInsertAgua = f'''INSERT INTO cmpc.estadistica_swc (gid_poligono, fecha, maximo, minimo, promedio, acumulado,desviacion,fuente)
            values (%(gid)s,%(fecha)s,%(maximo)s,%(minimo)s,%(promedio)s,%(acumulado)s,%(desviacion)s,%(fuente)s)
            on conflict(gid_poligono,fecha) DO NOTHING;'''
        sqlInsertAguaUtb = f"""INSERT INTO cmpc.estadistica_swc_utb_ult (gid_poligono, fecha, valor,fuente) 
            values (%(gid)s,%(fecha)s,%(valor)s,%(fuente)s)
            on conflict(gid_poligono,fecha) DO NOTHING;"""
        sqlUtbs = "select gid,ST_AsGeoJSON(the_geom)::json AS geometry from ri_utbs_riego where ejecutar is null"
        sqlPrediosT = "select gid,cod_fundo,cod_rodal,ST_AsGeoJSON(the_geom)::json AS geometry from upfs_temperatura order by gid"
        sqlInsertTempe = f'''INSERT INTO cmpc.estadistica_tem (gid_poligono, fecha, maximo, minimo, promedio, acumulado,desviacion,tipo)
            values (%(gid)s,%(fecha)s,%(maximo)s,%(minimo)s,%(promedio)s,%(acumulado)s,%(desviacion)s,%(tipo)s)
            on conflict(gid_poligono,fecha,tipo) DO NOTHING;'''
        sqlInsertTemUtb = f"""INSERT INTO cmpc.estadistica_tem_utb (gid_poligono, fecha, valor,tipo) 
            values (%(gid)s,%(fecha)s,%(valor)s,%(tipo)s)
            on conflict(gid_poligono,fecha,tipo) DO NOTHING;"""
        sqlUtbsTem = "select gid,ST_AsGeoJSON(the_geom)::json AS geometry from ri_utbs_temperatura"
        ruta = r"G:/cmpc/temperatura/reproyectado/2026/10"#r"G:/cmpc/agua/reprop/2026/01"06/07
        fundos = await self.ejecutarConsultaJson(sqlUtbsTem, {})
        archivos_py = [f for f in os.listdir(ruta) if f.endswith('.tif')]
    
        # Pre-procesar info de archivos
        lista_archivos = []
        for archivo in archivos_py:
            partes = archivo.split('_')
            lista_archivos.append({
                "path": os.path.join(ruta, archivo),
                "fecha": f"{partes[0][4:]}-{partes[0][2:4]}-{partes[0][:2]}",
                "tipot": partes[1]
            })
        print(f"Iniciando procesamiento de {len(fundos)} registros con {len(lista_archivos)} rasters...")
        
        # Tamaño del lote de fundos para no saturar la creación de tareas en memoria
        LOTE_FUNDOS = 2000 
        
        with ProcessPoolExecutor() as executor:
            loop = asyncio.get_running_loop()
            
            # Iteramos sobre los archivos raster uno por uno
            for idx_arch, arch in enumerate(lista_archivos, 1):
                print(f"[%] Procesando raster {idx_arch}/{len(lista_archivos)}: {os.path.basename(arch['path'])}")
                
                # Procesamos los fundos en bloques pequeños para este raster específico
                for i in range(0, len(fundos), LOTE_FUNDOS):
                    lote_actual_fundos = fundos[i : i + LOTE_FUNDOS]
                    tasks = []
                    
                    # Creamos tareas SOLO para el lote actual de fundos y el raster actual
                    for fundo in lote_actual_fundos:
                        tasks.append(
                            loop.run_in_executor(
                                executor, 
                                procesar_fundo_worker, 
                                fundo["geometry"], 
                                (arch["path"], arch["fecha"], arch["tipot"], 'utb', fundo["gid"])
                            )
                        )
                    
                    # Esperamos y acumulamos los resultados de este lote específico
                    all_results = []
                    for coro in asyncio.as_completed(tasks):
                        result = await coro
                        if result:
                            all_results.append(result)
                    
                    # Insertamos de golpe los resultados válidos de este bloque en la BD
                    if all_results:
                        await self.insertarRegistroMasivos(sqlInsertTemUtb, all_results)
                        # Imprime el progreso en la consola para confirmar que está guardando
                        print(f"    -> Insertados {len(all_results)} registros del bloque {min(i + LOTE_FUNDOS, len(fundos))}/{len(fundos)}")
                    
                    # Limpieza estricta de memoria antes del siguiente bloque
                    del tasks
                    del all_results
                    gc.collect()
                    
        print("Guardado masivo correcto y completado sin saturación.")

async def main():
    # 1. Inicializar el pool
    await init_async_pool()
    
    try:
        rasterApi = RasterDatos()
        # 2. Ejecutar la lógica principal esperando el resultado
        await rasterApi.sacarDatosRater()
    finally:
        # 3. Importante: cerrar el pool al terminar
        await poolConAsync.close()

if __name__ == '__main__':

    # SOLUCIÓN AL ERROR: Configurar el loop compatible con Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ahora ya puedes ejecutar main
    asyncio.run(main())
