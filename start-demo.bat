@echo off
REM ── Dhwani-Kavach one-click demo launcher (Windows) ──────────────────────────
REM Double-click this file. It opens the backend + frontend in two windows
REM and then your browser at the dashboard. Close the two windows to stop.
cd /d "%~dp0"

REM Prefer the project venv (it has the pinned, tested deps: torch 2.3, onnxruntime,
REM librosa, ...). Bare "python" is often a different interpreter missing these,
REM which is the usual reason the backend won't start.
set "PYEXE=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"

echo Starting backend (v2 voice verification) on http://localhost:8000 (using %PYEXE%) ...
start "Dhwani Backend" cmd /k ""%PYEXE%" -m uvicorn verify_app.main:app --app-dir backend --port 8000"

echo Starting frontend on http://localhost:8080 ...
start "Dhwani Frontend" cmd /k "cd frontend && npm run dev"

echo Waiting for servers to come up...
timeout /t 14 /nobreak >nul

start "" http://localhost:8080
echo.
echo Demo is up:  Frontend http://localhost:8080   Backend http://localhost:8000
echo Close the two opened windows to stop the demo.
