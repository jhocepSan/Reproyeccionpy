import pandas as pd

# Carga el archivo en un DataFrame
df = pd.read_csv('diferencias_colores_canopy_height_3.csv')
json_datos = df.to_json(orient='records', indent=4)

# Guardar en un archivo
with open('datos.json', 'w') as f:
    f.write(json_datos)

