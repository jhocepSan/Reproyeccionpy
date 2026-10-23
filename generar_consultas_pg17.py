import os,calendar,logging
from datetime import datetime,timedelta

class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.ERROR
        
logger = logging.getLogger("MiLogger")
logger.setLevel(logging.DEBUG)
logger.propagate = False
formatter = logging.Formatter('%(message)s')

file_handler1 = logging.FileHandler("./sqlFechas_cmpctemp_2026.log", mode="a", encoding="utf-8")
file_handler1.setLevel(logging.DEBUG)
file_handler1.setFormatter(formatter)
file_handler1.addFilter(InfoFilter())

file_handler2 = logging.FileHandler("./sqlCalculo_cmpctemp_2026.log", mode="a", encoding="utf-8")
file_handler2.setLevel(logging.ERROR)
file_handler2.setFormatter(formatter)
logger.addHandler(file_handler1)
logger.addHandler(file_handler2)

directorio = rf"G:\cmpc\temperatura\reproyectado\2026\10"
fechaLista=[]
finalLista=[]
condicion_excluir = "qf"
"""
for raiz, directorios, archivos in os.walk(directorio):
    for archivo in archivos:
        if archivo.endswith(".tif") and condicion_excluir not in archivo:  # Filtrar por extensión y condición
            fechaNombre = archivo.split('.')[0]
            fechaLista.append(fechaNombre)
"""
for raiz, directorios, archivos in os.walk(directorio):
    for archivo in archivos:
        if archivo.endswith(".tif") and condicion_excluir not in archivo:  # Filtrar por extensión y condición
            fechaNombre = archivo.split('_')
            tipo='TEMP5'
            if fechaNombre[1]!='1330':
                tipo='TEMP6'
            reordenFecha = fechaNombre[0]
            fechaLista.append({'fecha':reordenFecha[4:]+'/'+reordenFecha[2:4]+'/'+reordenFecha[:2],'tipo':tipo})

print(fechaLista)
#qlFinal = "INSERT INTO cmpc.disponible_fechas(fecha,tipo) values "+",".join(f"('{fech['fecha']}','{fech['tipo']}')" for fech in fechaLista)+";"
sqlFinal = (
    "INSERT INTO cmpc.disponible_fechas(fecha,tipo) VALUES "
    + ",".join(
        f"('{fch['fecha']}','{fch['tipo']}')" for fch in fechaLista
    )
    + ";"
)
logger.info(sqlFinal)
#print(len(finalLista))
'''
for fecha in fechaLista:
    if fecha!='':
        texto = fecha.split('_')[1]
        tipol='TEMP5'
        if texto=='0130':
            tipol='TEMP6'

        reordenFecha = fecha.split('_')[0]
        print(reordenFecha)
        fechaOrganizada = reordenFecha[4:]+'/'+reordenFecha[2:4]+'/'+reordenFecha[:2]

        sqlBase= f"""-- estadisticas upf
                INSERT INTO cmpc.estadistica_tem(
                    gid_poligono, fecha,tipo, promedio, minimo, maximo,acumulado,desviacion)
                SELECT 
                    p.gid,
                    '{fechaOrganizada}' as fecha,
                    '{tipol}' as tipo,
                    AVG(p.val) AS promedio, 
                    MIN(p.val) AS minimo, 
                    MAX(p.val) AS maximo,
                    SUM(p.val) AS acumulado,
                    STDDEV(p.val) AS desviacion
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, p.the_geom,TRUE,TRUE))).*,p.gid
                    FROM "{fecha}" r
                    JOIN public.fundos_vn p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0
                group by p.gid;
                -- este para utb
                INSERT INTO cmpc.estadistica_tem_utb(
                    gid_poligono, fecha,tipo, valor)
                SELECT 
                    p.gid,
                    '{fechaOrganizada}' as fecha,
                    '{tipol}' as tipo,
                    (p.val) AS valor
                FROM (
                    SELECT (ST_PixelAsPoints(ST_Clip(r.rast, 1, ST_Buffer(p.the_geom,-0.01),TRUE,TRUE))).*,p.gid
                    FROM "{fecha}" r
                    JOIN public.utbs_fundos_vn p
                    ON ST_Intersects(r.rast, p.the_geom) 
                ) AS p
                WHERE p.val > 0 ;
                """
        logger.error(sqlBase)
'''
for handler in logger.handlers[:]:  # Iterar sobre una copia de la lista
    handler.close()
    logger.removeHandler(handler)
logging.shutdown()