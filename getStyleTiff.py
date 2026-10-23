from qgis.core import QgsRasterLayer

# Ruta del TIFF
tif_path = r"E:/ArcGisTrabajo/Miselanios/quadw/2024-03/692-909.tif"

# Crear capa ráster
layer = QgsRasterLayer(tif_path, "mi_raster")

# Verificar si se cargó correctamente
if not layer.isValid():
    raise Exception("❌ No se pudo cargar el TIFF")

# Guardar su estilo (simbología) en un archivo .qml
qml_path = r"G:/stylo.qml"
layer.saveNamedStyle(qml_path)

print("✅ Estilo guardado en:", qml_path)
