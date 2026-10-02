@echo off
rem Double-click me on Windows to start the demo. Close this window to stop it.
cd /d "%~dp0app"
if not exist .venv\Scripts\python.exe (
  echo Run "Windows - 1 Setup.bat" first.
  pause
  exit /b 1
)
.venv\Scripts\python -m scripts.check_key
echo.
echo Starting the demo... your browser will open http://localhost:8501
echo Keep this window open while you present. Close it to stop the demo.
start "" cmd /c "timeout /t 3 >nul & start http://localhost:8501"
.venv\Scripts\python server.py
pause
