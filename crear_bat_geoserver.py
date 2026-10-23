import os,shutil
from collections import defaultdict

#ruta = "E:/AgostoRiego/temperatura/geopublicarr"
ruta ="G:/tiffs/geoserver"
#ruta ="G:/cmpc/agua/reprop"
#ruta = "G:/aguaPirque/reproyectado"
archivos_py = [f for f in os.listdir(ruta) if f.endswith('.tif')]
print(len(archivos_py))
lista = defaultdict(list)

for archivo in archivos_py:
	nombre = archivo.split('_')[0]
	clave=nombre[4:]+nombre[2:4]
	lista[clave].append(archivo)

for clave,archivos in lista.items():
	print(clave)
	print(len(archivos))
	nuevaRuta = os.path.join(ruta,clave[:4]+'/'+clave[4:6])
	if not os.path.exists(nuevaRuta):
		os.makedirs(nuevaRuta)
	for archi in archivos:
		
		#nombren=str(archi[6:8])+str(archi[4:6])+str(archi[:4])+'_swc_3.tif'
		nombren=archi.split('.')[0]+'.tif'
		'''if '_100' in nombre_base:
			nombren = nombre_base + '.tif'
		else:
			nombren = nombre_base + '_100.tif'''
		ruta_nueva = os.path.join(nuevaRuta,nombren)
		ruta_antigua = os.path.join(ruta,archi)
		try:
			os.replace(ruta_antigua,ruta_nueva)
		except Exception as e:
			print(f"Error al mover {archi}: {e}")
		#nombrebat = str(archi[6:8])+str(archi[4:6])+str(archi[:4])+'_swc_3'
		nombrebat=archi.split('.')[0]
		
		if not os.path.exists(os.path.join(ruta,clave[4:6]+'_'+clave[:4]+".bat")):
			file = open(os.path.join(ruta,clave[4:6]+'_'+clave[:4]+".bat"), "w")
		with open(os.path.join(ruta,clave[4:6]+'_'+clave[:4]+".bat"),'a') as file:
			#file.write(f'curl -v -u admin:geoserver -XPOST -H "Content-Type: text/xml" -d "<coverageStore> <name>{nombrebat}</name> <enabled>true</enabled> <type>GeoTIFF</type> <url>file:/C:/geoserver_2.26/data_dir/coverages/cmpc_temperatura_2026/{clave[:4]}/{clave[4:6]}/{nombrebat}.tif</url> <workspace>cite</workspace> </coverageStore>" "http://localhost:8081/geoserver/rest/workspaces/cite/coveragestores?configure=all"\n')
			#file.write(f'curl -v -u admin:geoserver -XPOST -H "Content-type: text/xml" -d "<coverage> <name>{nombrebat}</name><nativeCRS>UNKNOWN</nativeCRS><srs>EPSG:32718</srs> <projectionPolicy>FORCE_DECLARED</projectionPolicy> <parameters><entry><string>InputTransparentColor</string><string>#000000</string></entry><entry><string>SUGGESTED_TILE_SIZE</string><string>256,256</string></entry></parameters> </coverage>" "http://localhost:8081/geoserver/rest/workspaces/cite/coveragestores/{nombrebat}/coverages"\n')
			file.write(f'curl -v -u admin:geoserver -XPOST -H "Content-Type: text/xml" -d "<coverageStore> <name>{nombrebat}</name> <enabled>true</enabled> <type>GeoTIFF</type> <url>file:/C:/geoserver_2.26/data_dir/coverages/cmpc_riego_2026/{clave[:4]}/{clave[4:6]}/{nombrebat}.tif</url> <workspace>cite</workspace> </coverageStore>" "http://localhost:8081/geoserver/rest/workspaces/cite/coveragestores?configure=all"\n')
			file.write(f'curl -v -u admin:geoserver -XPOST -H "Content-type: text/xml" -d "<coverage> <name>{nombrebat}</name><nativeCRS>UNKNOWN</nativeCRS><srs>EPSG:32718</srs> <projectionPolicy>FORCE_DECLARED</projectionPolicy> <parameters><entry><string>InputTransparentColor</string><string>#000000</string></entry><entry><string>SUGGESTED_TILE_SIZE</string><string>256,256</string></entry></parameters> </coverage>" "http://localhost:8081/geoserver/rest/workspaces/cite/coveragestores/{nombrebat}/coverages"\n')
		