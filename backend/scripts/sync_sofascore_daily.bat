@echo off
REM ─────────────────────────────────────────────────────────────
REM Sync diario de Sofascore, pensado para correr desde Task
REM Scheduler en esta PC (IP residencial). Sofascore/Cloudflare
REM bloquea IPs de datacenter (Render, GitHub Actions, etc.), por
REM eso esto NO corre en la nube.
REM
REM Por cada liga: primero actualiza status/resultado de partidos
REM ya cargados (sync_sofascore_statuses), después trae los nuevos
REM partidos próximos (seed_sofascore_upcoming).
REM ─────────────────────────────────────────────────────────────

setlocal

set PROJECT_DIR=C:\Users\santi\OneDrive\Escritorio\ZonaMetrica
set BACKEND_DIR=%PROJECT_DIR%\backend
set LOG_FILE=%BACKEND_DIR%\scripts\sofascore_sync_log.txt
set MAX_MATCHES=50

cd /d "%BACKEND_DIR%"
call "%BACKEND_DIR%\venv\Scripts\activate.bat"

echo. >> "%LOG_FILE%"
echo ==================================================== >> "%LOG_FILE%"
echo Sync iniciado: %date% %time% >> "%LOG_FILE%"
echo ==================================================== >> "%LOG_FILE%"

REM ─── Local ──────────────────────────────────────────────
echo [Argentina - Liga Profesional - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "Argentina Liga Profesional" "2026" >> "%LOG_FILE%" 2>&1
echo [Argentina - Liga Profesional] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Argentina Liga Profesional" "2026" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

REM ─── 5 grandes ligas europeas ──────────────────────────
echo [Inglaterra - Premier League - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "England Premier League" "26/27" >> "%LOG_FILE%" 2>&1
echo [Inglaterra - Premier League] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "England Premier League" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [España - La Liga - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "Spain La Liga" "26/27" >> "%LOG_FILE%" 2>&1
echo [España - La Liga] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Spain La Liga" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [Italia - Serie A - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "Italy Serie A" "26/27" >> "%LOG_FILE%" 2>&1
echo [Italia - Serie A] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Italy Serie A" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [Alemania - Bundesliga - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "Germany Bundesliga" "26/27" >> "%LOG_FILE%" 2>&1
echo [Alemania - Bundesliga] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Germany Bundesliga" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [Francia - Ligue 1 - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "France Ligue 1" "26/27" >> "%LOG_FILE%" 2>&1
echo [Francia - Ligue 1] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "France Ligue 1" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

REM ─── Competencias internacionales ──────────────────────
echo [UEFA - Champions League - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "UEFA Champions League" "26/27" >> "%LOG_FILE%" 2>&1
echo [UEFA - Champions League] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "UEFA Champions League" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [CONMEBOL - Copa Libertadores - status] >> "%LOG_FILE%"
python -m app.cli.sync_sofascore_statuses "CONMEBOL Copa Libertadores" "2026" >> "%LOG_FILE%" 2>&1
echo [CONMEBOL - Copa Libertadores] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "CONMEBOL Copa Libertadores" "2026" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo Sync finalizado: %date% %time% >> "%LOG_FILE%"

endlocal