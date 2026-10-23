@echo off
SET "PSQL=C:\Program Files (x86)\PostgreSQL\9.0\bin\psql"
SET DB=trabajo
SET USER=postgres
SET HOST=localhost
SET PORT=5432
SET PASSWORD=asdf
SET SQL_FILE="E:\ArcGisTrabajo\Reproyeccion\consul_temp.sql"
REM === evitar prompt de contraseña ===
SET PGPASSWORD=%PASSWORD%

"%PSQL%" -U %USER% -h %HOST% -p %PORT% -d %DB% -f %SQL_FILE%
pause
