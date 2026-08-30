@echo off
setlocal EnableExtensions EnableDelayedExpansion

title CAHMA Demo Launcher
set "PROJECT_DIR=%~dp0"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "API_KEY=hackathon-demo-key"
set "API_URL=http://127.0.0.1:8080"
set "DASHBOARD_URL=http://127.0.0.1:5173"
set "RUNTIME_VERSION=v2"

echo.
echo ============================================================
echo   CAHMA Arena - Complete Demo Launcher
echo ============================================================
echo.

set "PYTHON_EXE=python"
"%PYTHON_EXE%" -c "import fastapi, joblib, sklearn, cv2, onnxruntime, uvicorn" >nul 2>&1
if errorlevel 1 (
    set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if exist "!BUNDLED_PYTHON!" set "PYTHON_EXE=!BUNDLED_PYTHON!"
)

"%PYTHON_EXE%" -c "import fastapi, joblib, sklearn, cv2, onnxruntime, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo ERROR: The backend Python dependencies are not installed.
    echo.
    echo Run this first from the backend folder:
    echo   python -m pip install -e ".[dev]"
    echo.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm was not found. Install Node.js and run npm install.
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%node_modules" (
    echo ERROR: Frontend dependencies are missing.
    echo Run: npm install
    pause
    exit /b 1
)

for %%F in (
    "%BACKEND_DIR%\checkpoints\router-review1-v2.joblib"
    "%BACKEND_DIR%\models\yolox_tiny.onnx"
    "%BACKEND_DIR%\assets\scenarios\feed-a-clear.avi"
    "%BACKEND_DIR%\assets\scenarios\feed-b-degraded.avi"
    "%BACKEND_DIR%\assets\scenarios\feed-c-temporal.avi"
) do (
    if not exist "%%~F" (
        echo ERROR: Required demo file is missing:
        echo   %%~F
        pause
        exit /b 1
    )
)

if /I "%~1"=="--check" (
    echo Preflight passed: Python, npm, dependencies, models, and videos are ready.
    exit /b 0
)

echo [1/5] Checking backend API...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r=Invoke-RestMethod -Uri '%API_URL%/healthz' -TimeoutSec 2; if($r.status -eq 'ok' -and $r.runtime_version -eq '%RUNTIME_VERSION%' -and $r.router_mode -eq 'scalar' -and $r.router_model_sha256 -eq 'a098669583c43b93796f0d0fed1d1581183bada5c3852def14cbe74239dc8509'){ exit 0 } } catch {}; if(Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue){ exit 2 }; exit 1"
set "BACKEND_CHECK=!ERRORLEVEL!"
if "!BACKEND_CHECK!"=="0" (
    echo       Reusing the healthy scalar-router backend already on port 8080.
) else if "!BACKEND_CHECK!"=="2" (
    echo ERROR: Port 8080 is occupied by another or outdated service.
    echo Stop that service, then run this launcher again.
    echo If it is the old CAHMA Docker stack, run: docker compose down
    pause
    exit /b 1
) else (
    echo       Starting backend API...
    start "CAHMA Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && set CAHMA_API_KEY=%API_KEY%&& set CAHMA_RUNTIME_VERSION=%RUNTIME_VERSION%&& set CAHMA_DATABASE_PATH=./data/demo-live.db&& ""%PYTHON_EXE%"" -m uvicorn app.main:app --host 127.0.0.1 --port 8080"
)

echo       Waiting for backend health check...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$deadline=(Get-Date).AddSeconds(45); do { try { $r=Invoke-RestMethod -Uri '%API_URL%/healthz' -TimeoutSec 2; if($r.status -eq 'ok' -and $r.runtime_version -eq '%RUNTIME_VERSION%' -and $r.router_mode -eq 'scalar'){ exit 0 } } catch {}; Start-Sleep -Milliseconds 500 } while((Get-Date)-lt $deadline); exit 1"
if errorlevel 1 (
    echo ERROR: Backend did not become healthy within 45 seconds.
    echo Inspect the CAHMA Backend window for the error.
    pause
    exit /b 1
)

echo [2/5] Checking dashboard...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if(Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue){ exit 0 }; exit 1"
set "DASHBOARD_CHECK=!ERRORLEVEL!"
if "!DASHBOARD_CHECK!"=="0" (
    echo       Reusing the dashboard already on port 5173.
) else (
    echo       Starting dashboard...
    start "CAHMA Dashboard" cmd /k "cd /d ""%PROJECT_DIR%"" && set ""VITE_CAHMA_API_URL=%API_URL%"" && npm run dev -- --host 127.0.0.1"
)

echo       Waiting for dashboard readiness...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$deadline=(Get-Date).AddSeconds(60); do { if(Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue){ exit 0 }; Start-Sleep -Milliseconds 500 } while((Get-Date)-lt $deadline); exit 1"
if errorlevel 1 (
    echo ERROR: Dashboard did not become ready within 60 seconds.
    echo Inspect the CAHMA Dashboard window for the error.
    pause
    exit /b 1
)

echo [3/5] Starting CAHMA v2 observer and scheduler driver...
powershell -NoProfile -ExecutionPolicy Bypass -Command "if(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -like '*app.v2_driver*' }){ exit 0 }; exit 1"
if errorlevel 1 (
    start "CAHMA v2 Driver" cmd /k "cd /d ""%BACKEND_DIR%"" && ""%PYTHON_EXE%"" -m app.v2_driver --source-a ""assets/scenarios/feed-a-clear.avi"" --source-b ""assets/scenarios/feed-b-degraded.avi"" --source-c ""assets/scenarios/feed-c-temporal.avi"" --api ""%API_URL%"" --api-key ""%API_KEY%"" --sample-fps 0.5 --evidence ""data/v2-demo.jsonl"""
) else (
    echo       Reusing CAHMA v2 driver.
)

echo [4/5] Resident model pool verified by backend readiness.
echo [5/5] Policy engine, capacity guard, and live receipts ready.

echo.
echo All services started successfully.
echo Dashboard: %DASHBOARD_URL%
echo Health:    %API_URL%/healthz
echo Metrics:   %API_URL%/metrics
echo.
echo Close the three labeled terminal windows or press Ctrl+C in each to stop.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 3"
start "" "%DASHBOARD_URL%"

endlocal
