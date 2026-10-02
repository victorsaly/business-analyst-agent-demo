@echo off
rem Double-click me (once) on Windows to set up the demo. Takes about 5 minutes.
cd /d "%~dp0app"
echo == Business Performance Analyst Agent: setup (Windows) ==
set "PY="
py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul && set "PY=python"
if not defined PY goto nopython
set "STEP=1/4 Creating the Python environment"
call :show "in app\.venv ..."
%PY% -m venv .venv || goto failed
set "STEP=2/4 Updating pip"
call :show "..."
.venv\Scripts\python -m pip install --upgrade pip --disable-pip-version-check || goto failed
set "STEP=3/4 Installing Python packages"
call :show "This is the slow part, a few minutes. Progress shows below."
.venv\Scripts\python -m pip install -r requirements.txt --disable-pip-version-check || goto failed
if not exist .env copy .env.example .env >nul
set "STEP=4/4 Preparing the AdventureWorks database"
call :show "..."
.venv\Scripts\python -c "from analyst import data; print('Database ready:', data.DB_FILES['real'])" || goto failed
title Setup done
echo.
echo ===== SETUP DONE =====
echo.
echo Last step: your free AI key for Live AI (get one at https://console.groq.com/keys).
echo Notepad opens a file called .env. Paste the key after GROQ_API_KEY=, save, and close Notepad.
echo (No key? Just close Notepad: Replay mode works without one.)
start "" /wait notepad .env
.venv\Scripts\python check_key.py
echo.
echo Next: double-click "Windows - 2 Start.bat".
pause
exit /b 0
:show
title Setup %STEP%
echo.
echo [%STEP%] %~1
exit /b 0
:nopython
echo.
echo Python 3.10 or newer is not installed yet.
echo Your browser will now open python.org. Download and run the Windows installer.
echo IMPORTANT: on the first screen of the installer, tick "Add python.exe to PATH".
echo Then double-click this file again.
start "" https://www.python.org/downloads/windows/
pause
exit /b 1
:failed
title Setup FAILED
echo.
echo ===== SETUP FAILED at step %STEP% =====
echo See the message above. Check your internet connection and double-click this file again.
echo Finished steps are quick on a re-run.
pause
exit /b 1
