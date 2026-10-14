@echo off
setlocal

set PROJECT_DIR=C:\Users\santi\OneDrive\Escritorio\ZonaMetrica
set BACKEND_DIR=%PROJECT_DIR%\backend

cd /d "%BACKEND_DIR%"
call "%BACKEND_DIR%\venv\Scripts\activate.bat"

echo ====================================================
echo Sync Oficial iniciado: %date% %time%
echo ====================================================

echo [1/2] Actualizando estados de partidos (Football-Data)...
python -m app.cli.sync_football_data_statuses BSA
python -m app.cli.sync_football_data_statuses PL
python -m app.cli.sync_football_data_statuses PD

echo [2/2] Ingestando proximos partidos (API-Football)...
python -m app.cli.seed_incremental_api_football

echo Sync finalizado con exito: %date% %time%
endlocal
pause