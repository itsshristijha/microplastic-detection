@echo off
setlocal enabledelayedexpansion
echo ==================================================
echo         Starting ELLE Project Servers...
echo ==================================================
echo.
:: Get the directory where this batch file is located
set "BASE_DIR=%~dp0"
:: Define relative paths to backend and frontend
set "BACKEND_PATH=backend"
set "FRONTEND_PATH=frontend"
:: Combined absolute paths
set "BACKEND_DIR=%BASE_DIR%%BACKEND_PATH%"
set "FRONTEND_DIR=%BASE_DIR%%FRONTEND_PATH%"
echo [CHECK] Verifying directories...
if not exist "%BACKEND_DIR%" (
    echo [ERROR] Backend directory not found: "%BACKEND_DIR%"
    pause
    exit /b
)
if not exist "%FRONTEND_DIR%" (
    echo [ERROR] Frontend directory not found: "%FRONTEND_DIR%"
    pause
    exit /b
)
echo [OK] Directories found.
echo.
echo Starting Flask Backend Server (Port 5000)...
:: We call python.exe directly from the venv for maximum reliability
start "ELLE Backend" cmd /k "cd /d "%BACKEND_DIR%" && .\.venv_new\Scripts\python.exe app.py"
echo Starting React Frontend Server (Port 8080)...
start "ELLE Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"
echo.
echo Both servers are starting up in separate windows!
echo - Keep those windows open while you are working.
echo - You can access the website at: http://localhost:8080
echo.
pause