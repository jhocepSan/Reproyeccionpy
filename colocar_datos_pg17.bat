@echo off
SET "PSQL=C:\Program Files\PostgreSQL\17\bin\psql"
SET DB=cmpc
SET USER=postgres
SET HOST=localhost
SET PORT=5433
SET SQL_FILE="E:\ArcGisTrabajo\Reproyeccion\consulta.sql"

"%PSQL%" -U %USER% -h %HOST% -p %PORT% -d %DB% -f %SQL_FILE%
pause
