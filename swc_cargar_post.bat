@echo off
REM Variables de configuración
SET FOLDER="G:\cmpc\agua100\reproyectado\2026\10"
SET OUTPUT_SQL="G:\cmpc\agua100\reproyectado\2026\10\datos.sql"
SET TABLE_NAME=my_raster_table
SET RASTER2PGSQL="C:\Program Files\PostgreSQL\17\bin\raster2pgsql"
SET "PSQL=C:\Program Files\PostgreSQL\17\bin\psql"
SET DB=cmpc
SET USER=postgres
SET HOST=localhost
SET PORT=5433

REM Comprobar si el archivo de salida ya existe y eliminarlo
IF EXIST %OUTPUT_SQL% DEL %OUTPUT_SQL%
REM Iterar sobre cada archivo en la carpeta
FOR %%f IN (%FOLDER%\*.tif) DO (
    REM Extraer el nombre del archivo sin la ruta ni extensión
    FOR %%g IN ("%%~nf") DO (
        SET TABLE_NAME=%%~g
        echo Procesando %%f en la tabla %%~g...
        %RASTER2PGSQL% -s 32718 -I -C -M -R -t 100x100 "%%f" %%~g | CALL "%PSQL%" -U %USER% -h %HOST% -p %PORT% -d %DB%
    )
)

echo Archivo SQL generado: %OUTPUT_SQL%
pause
