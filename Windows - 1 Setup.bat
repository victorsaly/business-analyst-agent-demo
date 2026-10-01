@echo off
rem Double-click me (once) on Windows to set up the demo. Takes about 5 minutes.
cd /d "%~dp0app"
echo == Business Performance Analyst Agent: setup (Windows) ==
set "PY="
py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul && set "PY=python"
if not defined PY goto nopython
%PY% -m venv .venv || goto failed
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\python -m pip install -q -r requirements.txt || goto failed
if not exist .env copy .env.example .env >nul
.venv\Scripts\python -c "from analyst import data; print('Database ready:', data.DB_FILES['real'])" || goto failed
echo.
echo Setup done.
echo Notepad will open a file called .env. Paste your free Groq key after GROQ_API_KEY= and save it.
echo (No key? Just close Notepad: Replay mode works without one.)
start "" notepad .env
echo Next: double-click "Windows - 2 Start.bat".
pause
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
echo.
echo Something went wrong (see the message above). Check your internet connection and try again.
pause
exit /b 1
