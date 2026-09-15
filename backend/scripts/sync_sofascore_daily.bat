@echo off
REM ─────────────────────────────────────────────────────────────
REM Sync diario de Sofascore, pensado para correr desde Task
REM Scheduler en esta PC (IP residencial). Sofascore/Cloudflare
REM bloquea IPs de datacenter (Render, GitHub Actions, etc.), por
REM eso esto NO corre en la nube — ver conversación del 2026-09 para
REM el detalle completo del bloqueo 403.
REM
REM Requiere: venv activado con ScraperFC instalado, y un .env en
REM backend/ con DATABASE_URL apuntando a Neon (el mismo que ya
REM usás para correr el backend localmente).
REM ─────────────────────────────────────────────────────────────

setlocal

REM Ajustá esta ruta si el proyecto no está en OneDrive\Escritorio
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
echo [Argentina - Liga Profesional] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Argentina Liga Profesional" "2026" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

REM ─── 5 grandes ligas europeas ──────────────────────────
REM Temporada partida "26/27" confirmada con get_valid_seasons()
REM el 2026-09. Cuando arranque la 27/28, hay que actualizar acá.
echo [Inglaterra - Premier League] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "England Premier League" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [España - La Liga] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Spain La Liga" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [Italia - Serie A] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Italy Serie A" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [Alemania - Bundesliga] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "Germany Bundesliga" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [Francia - Ligue 1] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "France Ligue 1" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

REM ─── Competencias internacionales ──────────────────────
echo [UEFA - Champions League] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "UEFA Champions League" "26/27" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1

echo [CONMEBOL - Copa Libertadores] >> "%LOG_FILE%"
python -m app.cli.seed_sofascore_upcoming "CONMEBOL Copa Libertadores" "2026" "%MAX_MATCHES%" >> "%LOG_FILE%" 2>&1


echo Sync finalizado: %date% %time% >> "%LOG_FILE%"

endlocal