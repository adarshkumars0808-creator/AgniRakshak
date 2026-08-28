@echo off
title THERMOSCOPE - Fire Risk Intelligence

cd /d "%~dp0"

echo.
echo ============================================================
echo              THERMOSCOPE
echo        Fire Risk Intelligence System
echo ============================================================
echo.

echo [1/2] Starting FastAPI Backend...

start "" /min cmd /c "call .venv\Scripts\activate.bat && python -m uvicorn src.api:app --port 8000"

echo Waiting for backend...

:WAIT_API
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/docs' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }"

if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_API
)

echo Backend is ready!

echo.
echo [2/2] Starting Streamlit Dashboard...

start "" /min cmd /c "call .venv\Scripts\activate.bat && streamlit run src\dashboard.py --server.headless true"

echo Waiting for dashboard...

:WAIT_DASHBOARD
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://localhost:8501' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }"

if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_DASHBOARD
)

echo Dashboard is ready!

echo.
echo Opening Thermoscope...
start "" "http://localhost:8501"

echo.
echo ============================================================
echo       THERMOSCOPE STARTED SUCCESSFULLY
echo ============================================================
echo.

exit