import os,shutil,logging
from collections import defaultdict

class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.ERROR
        
logger = logging.getLogger("MiLogger")
logger.setLevel(logging.DEBUG)
logger.propagate = False
formatter = logging.Formatter('%(message)s')

file_handler1 = logging.FileHandler("sqlFechas_swc_2.log", mode="a", encoding="utf-8")
file_handler1.setLevel(logging.DEBUG)
file_handler1.setFormatter(formatter)
file_handler1.addFilter(InfoFilter())

file_handler2 = logging.FileHandler("sqlCalculo_swc_2.log", mode="a", encoding="utf-8")
file_handler2.setLevel(logging.ERROR)
file_handler2.setFormatter(formatter)
logger.addHandler(file_handler1)
logger.addHandler(file_handler2)

ruta = "G:/cmpc/agua100/reproyectado/2024/07"

archivos_py = [f for f in os.listdir(ruta) if f.endswith('.tif')]
print(len(archivos_py))
lista = defaultdict(list)

for archivo in archivos_py:
	nombre = archivo.split('_')[0]
	clave=nombre[4:]+nombre[2:4]
	lista[clave].append(archivo)

for clave,archivos in lista.items():
	print(clave)
	print(archivos)
	sqlFinal = "INSERT INTO cmpc.disponible_fechas(fecha,tipo) values "+",".join(f"('{clave[:4]}/{clave[4:]}/{fecha[:2]}','SWC4')" for fecha in archivos)+";"
	logger.info(sqlFinal)
	for archivo in archivos:
		sqlBase = f"""-- estadisticas upf
	        INSERT INTO cmpc.estadistica_swc(
	            gid_poligono, fecha,tipo, promedio, minimo, maximo,acumulado,desviacion)
	        SELECT 
	            p.gid,
	            '{clave[:4]}/{clave[4:]}/{archivo[:2]}' as fecha,
	            AVG(p.val) AS promedio, 
	            MIN(p.val) AS minimo, 
	            MAX(p.val) AS maximo,
	            SUM(p.val) AS acumulado,
	            STDDEV(p.val) AS desviacion
	        FROM (
	            SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, p.the_geom,TRUE,TRUE))).*,p.gid
	            FROM "{archivo.split('.')[0]}" r
	            JOIN public.fundos_riego p
	            ON ST_Intersects(r.rast, p.the_geom) 
	        ) AS p
	        WHERE p.val > 0
	        group by p.gid;
	        -- este para utb
	        INSERT INTO cmpc.estadistica_swc_utb(
	            gid_poligono, fecha,tipo, valor)
	        SELECT 
	            p.gid,
	            '{clave[:4]}/{clave[4:]}/{archivo[:2]}' as fecha,
	            (p.val) AS valor
	        FROM (
	            SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, ST_Buffer(p.the_geom,-0.01),TRUE,TRUE))).*,p.gid
	            FROM "{archivo.split('.')[0]}" r
	            JOIN public.ri_utbs_riego p
	            ON ST_Intersects(r.rast, p.the_geom) 
	        ) AS p
	        WHERE p.val > 0 ;
		"""
		logger.error(sqlBase)

for handler in logger.handlers[:]:  # Iterar sobre una copia de la lista
    handler.close()
    logger.removeHandler(handler)
logging.shutdown()