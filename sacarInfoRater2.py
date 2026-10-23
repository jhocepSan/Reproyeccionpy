from psycopg_pool import AsyncConnectionPool
import asyncio,sys
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

class RasterDatos:
    def recortar(self, raster, gdf):
        with rasterio.open(raster) as src:
            if gdf.crs != src.crs:
                gdf = gdf.to_crs(src.crs)

            geoms = gdf.geometry.values
            out_image, out_transform = mask(src, geoms, crop=True,all_touched=True)
            nodata = src.nodata

        band = out_image[0]  # una sola banda
        return band, out_transform, nodata
    def obtener_valor_centroide(self, raster, gdf):
        with rasterio.open(raster) as src:
            # 1. Asegurar que el punto esté en el mismo CRS que el raster
            if gdf.crs != src.crs:
                gdf = gdf.to_crs(src.crs)
            
            # 2. Obtener el centroide de la UTB
            centroide = gdf.geometry.centroid.iloc[0]
            coord = [(centroide.x, centroide.y)]
            
            # 3. Muestrear el valor del píxel en esa coordenada
            # sample() devuelve un generador de arrays (uno por cada punto y banda)
            valor_gen = src.sample(coord)
            valor_pixel = next(valor_gen)[0] # Tomamos la primera banda del primer punto
            
            nodata = src.nodata
            return valor_pixel, nodata
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
    def sacarDatosAgua(self,info,ruta,tipo,fuente):
        geom_obj = shape(info["geometry"])
        data = {"geometry": [geom_obj]}
        gdf = gpd.GeoDataFrame(data, crs="EPSG:32718")
        archivos_py = [f for f in os.listdir(ruta) if f.endswith('.tif')]
        for archivo in archivos_py:
            raster_path = os.path.join(
                ruta, archivo
            )
            nombre = archivo.split('_')[0]
            if tipo =='upf':
                band, transform, nodata = self.recortar(raster_path, gdf)
                if band is not None:
                    valid_pixels = band[(band > 0) & (band != nodata)]
                    print(valid_pixels)
                    if valid_pixels.size > 0:
                        stats = {
                            "gid": info["gid"],
                            "fecha": nombre[4:]+'-'+nombre[2:4]+'-'+nombre[:2], # Puedes extraerla del nombre del archivo si gustas
                            "maximo": float(np.max(valid_pixels)/1000),
                            "minimo": float(np.min(valid_pixels)/1000),
                            "promedio": float(np.mean(valid_pixels)/1000),
                            "acumulado": float(np.sum(valid_pixels)/1000),
                            "desviacion": float(np.std(valid_pixels)/1000),
                            "fuente":fuente
                        }
                        print(stats)
            else:
                valor, nodata = self.obtener_valor_centroide(raster_path, gdf)
                if valor != nodata and valor > 0:
                    stats = {
                        "gid":info["gid"],
                        "fecha": nombre[4:]+'-'+nombre[2:4]+'-'+nombre[:2],
                        "valor": float(valor/1000),
                        "fuente":fuente
                    }
                    print(stats)
    async def sacarDatosTempe(self,info,ruta,tipo,sql):
        geom_obj = shape(info["geometry"])
        data = {"geometry": [geom_obj]}
        gdf = gpd.GeoDataFrame(data, crs="EPSG:32718")
        archivos_py = [f for f in os.listdir(ruta) if f.endswith('.tif')]
        for archivo in archivos_py:
            raster_path = os.path.join(
                ruta, archivo
            )
            nombre = archivo.split('_')[0]
            tipot = archivo.split('_')[1]
            if tipo =='upf':
                band, transform, nodata = self.recortar(raster_path, gdf)
                if band is not None:
                    valid_pixels = band[(band > 0) & (band != nodata)]
                    if valid_pixels.size > 0:
                        stats = {
                            "gid": info["gid"],
                            "fecha": nombre[4:]+'-'+nombre[2:4]+'-'+nombre[:2], # Puedes extraerla del nombre del archivo si gustas
                            "maximo": float((np.max(valid_pixels)/100)-273.15),
                            "minimo": float((np.min(valid_pixels)/100)-273.15),
                            "promedio": float((np.mean(valid_pixels)/100)-273.15),
                            "acumulado": float((np.sum(valid_pixels)/100)-273.15),
                            "desviacion": float(np.std(valid_pixels)/100),
                            "tipo": "TEMP5" if tipot=='1330' else "TEMP6"
                        }
                        await self.insertarResgistro(sql,stats)
            else:
                valor, nodata = self.obtener_valor_centroide(raster_path, gdf)
                if valor != nodata and valor > 0:
                    stats = {
                        "gid":info["gid"],
                        "fecha": nombre[4:]+'-'+nombre[2:4]+'-'+nombre[:2],
                        "valor": float((valor/100)-273.15),
                        "tipo": "TEMP5" if tipot=='1330' else "TEMP6"
                    }
                    await self.insertarResgistro(sql,stats)
    async def procesar_unico_fundo_swc(self, fundo, archivos_py, ruta, tipo,fuente):
        geom_obj = shape(fundo["geometry"])
        data = {"geometry": [geom_obj]}
        gdf = gpd.GeoDataFrame(data, crs="EPSG:32718")
        
        resultados_fundo = []
        
        for archivo in archivos_py:
            raster_path = os.path.join(ruta, archivo)
            nombre = archivo.split('_')[0]
            tipot = archivo.split('_')[1]
            fecha = f"{nombre[4:]}-{nombre[2:4]}-{nombre[:2]}"
            
            if tipo == 'upf':
                # Ejecutamos la lectura pesada del TIF en un hilo separado para no bloquear el CPU
                band, transform, nodata = await asyncio.to_thread(self.recortar, raster_path, gdf)
                if band is not None:
                    valid_pixels = band[(band > 0) & (band != nodata)]
                    if valid_pixels.size > 0:
                        resultados_fundo.append({
                            "gid": fundo["gid"],
                            "fecha": fecha,
                            "maximo": float(np.max(valid_pixels)/1000),
                            "minimo": float(np.min(valid_pixels)/1000),
                            "promedio": float(np.mean(valid_pixels)/1000),
                            "acumulado": float(np.sum(valid_pixels)/1000),
                            "desviacion": float(np.std(valid_pixels)/1000),
                            "fuente":fuente
                        })
            else:
                # Muestreo de centroide en hilo separado
                valor, nodata = await asyncio.to_thread(self.obtener_valor_centroide, raster_path, gdf)
                if valor != nodata and valor > 0:
                    resultados_fundo.append({
                        "gid": fundo["gid"],
                        "fecha": fecha,
                        "valor": float((valor/1000)),
                        "fuente":fuente
                    })
                    
        return resultados_fundo
                        
    async def procesar_unico_fundo(self, fundo, archivos_py, ruta, tipo):
        geom_obj = shape(fundo["geometry"])
        data = {"geometry": [geom_obj]}
        gdf = gpd.GeoDataFrame(data, crs="EPSG:32718")
        
        resultados_fundo = []
        
        for archivo in archivos_py:
            raster_path = os.path.join(ruta, archivo)
            nombre = archivo.split('_')[0]
            tipot = archivo.split('_')[1]
            fecha = f"{nombre[4:]}-{nombre[2:4]}-{nombre[:2]}"
            
            if tipo == 'upf':
                # Ejecutamos la lectura pesada del TIF en un hilo separado para no bloquear el CPU
                band, transform, nodata = await asyncio.to_thread(self.recortar, raster_path, gdf)
                if band is not None:
                    valid_pixels = band[(band > 0) & (band != nodata)]
                    if valid_pixels.size > 0:
                        resultados_fundo.append({
                            "gid": fundo["gid"],
                            "fecha": fecha,
                            "maximo": float((np.max(valid_pixels)/100)-273.15),
                            "minimo": float((np.min(valid_pixels)/100)-273.15),
                            "promedio": float((np.mean(valid_pixels)/100)-273.15),
                            "acumulado": float((np.sum(valid_pixels)/100)-273.15),
                            "desviacion": float(np.std(valid_pixels)/100),
                            "tipo": "TEMP5" if tipot == '1330' else "TEMP6"
                        })
            else:
                # Muestreo de centroide en hilo separado
                valor, nodata = await asyncio.to_thread(self.obtener_valor_centroide, raster_path, gdf)
                if valor != nodata and valor > 0:
                    resultados_fundo.append({
                        "gid": fundo["gid"],
                        "fecha": fecha,
                        "valor": float((valor/100)-273.15),
                        "tipo": "TEMP5" if tipot == '1330' else "TEMP6"
                    })
                    
        return resultados_fundo

    async def sacarDatosRater(self):
        sqlPredios = "select gid,n_cod_fund,n_cod_roda,ST_AsGeoJSON(the_geom)::json AS geometry from fundos_riego order by gid desc"
        sqlInsertAgua = f'''INSERT INTO cmpc.estadistica_swc (gid_poligono, fecha, maximo, minimo, promedio, acumulado,desviacion,fuente)
            values (%(gid)s,%(fecha)s,%(maximo)s,%(minimo)s,%(promedio)s,%(acumulado)s,%(desviacion)s,%(fuente)s)
            on conflict(gid_poligono,fecha) DO NOTHING;'''
        sqlInsertAguaUtb = f"""INSERT INTO cmpc.estadistica_swc_utb (gid_poligono, fecha, valor,fuente) 
            values (%(gid)s,%(fecha)s,%(valor)s,%(fuente)s)
            on conflict(gid_poligono,fecha) DO NOTHING;"""
        sqlUtbs = "select gid,ST_AsGeoJSON(the_geom)::json AS geometry from ri_utbs_riego where ejecutar=1"
        sqlPrediosT = "select gid,cod_fundo,cod_rodal,ST_AsGeoJSON(the_geom)::json AS geometry from upfs_temperatura order by gid"
        sqlInsertTempe = f'''INSERT INTO cmpc.estadistica_tem (gid_poligono, fecha, maximo, minimo, promedio, acumulado,desviacion,tipo)
            values (%(gid)s,%(fecha)s,%(maximo)s,%(minimo)s,%(promedio)s,%(acumulado)s,%(desviacion)s,%(tipo)s)
            on conflict(gid_poligono,fecha,tipo) DO NOTHING;'''
        sqlInsertTemUtb = f"""INSERT INTO cmpc.estadistica_tem_utb (gid_poligono, fecha, valor,tipo) 
            values (%(gid)s,%(fecha)s,%(valor)s,%(tipo)s)
            on conflict(gid_poligono,fecha,tipo) DO NOTHING;"""
        sqlUtbsTem = "select gid,ST_AsGeoJSON(the_geom)::json AS geometry from ri_utbs_temperatura"
        ruta = r"G:/cmpc/agua/reprop/2020/02"#r"G:/cmpc/agua/reprop/2026/01"06/07
        fundos = await self.ejecutarConsultaJson(sqlUtbs, {})
        archivos_py = [f for f in os.listdir(ruta) if f.endswith('.tif')]
        todos_los_datos = []
        lote_tamano = 200  # Procesamos de 100 en 100 para no saturar la memoria RAM
        
        print(f"Iniciando procesamiento de {len(fundos)} registros...")
        
        for i in range(0, len(fundos), lote_tamano):
            lote = fundos[i : i + lote_tamano]
            
            # Lanzamos 100 tareas concurrentes al mismo tiempo
            tareas = [self.procesar_unico_fundo_swc(fundo, archivos_py, ruta, 'utb','20m') for fundo in lote]
            resultados_lote = await asyncio.gather(*tareas)
            datos_para_guardar=[]
            # Unimos los resultados del lote
            for res in resultados_lote:
                datos_para_guardar.extend(res)
            if datos_para_guardar:
                await self.insertarRegistroMasivos(sqlInsertAguaUtb, datos_para_guardar)
            print(f"Procesados: {min(i + lote_tamano, len(fundos))}/{len(fundos)}")
            del datos_para_guardar
            del resultados_lote
            del tareas
            if i % 5000 == 0:
                gc.collect()
            print(f"Procesados e Insertados: {min(i + lote_tamano, len(fundos))}/{len(fundos)}")
            
            
        print("guardado masivo correcto")

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
