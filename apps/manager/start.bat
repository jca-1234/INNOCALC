@echo off
rem ======================================================================
rem  InnoCalc - Innovis calculation management
rem  Starts the local service and opens http://127.0.0.1:8125/
rem
rem  Optional settings: remove the "rem" and edit as needed.
rem ======================================================================
rem set "ICM_ROOT=J:\Active Projects"
rem set "ICM_PORT=8125"
rem Every other setting is described in ..\..\.env.example.

setlocal EnableExtensions
for %%I in ("%~dp0.") do set "SUITE=%%~fI"
:find_suite
if exist "%SUITE%\suite.toml" goto :have_suite
for %%I in ("%SUITE%\..") do set "PARENT=%%~fI"
if /i "%PARENT%"=="%SUITE%" goto :missing_suite
set "SUITE=%PARENT%"
goto :find_suite
:have_suite
cd /d "%~dp0"

rem ---- find a Python interpreter ---------------------------------------
set "PY=%SUITE%\.venv\Scripts\python.exe"
if exist "%PY%" goto :have_python
echo Run "%SUITE%\setup.bat" once to prepare the suite environment.
pause
exit /b 1

:have_python
rem ---- pypdf combines drawing sets and PDF inserts ----------------------
"%PY%" -c "import pypdf" >nul 2>nul
if errorlevel 1 (
    echo Dependencies are missing. Run "%SUITE%\setup.bat".
    pause
    exit /b 1
)

rem ---- Chromium produces the PDFs --------------------------------------
"%PY%" -c "import sys; sys.path.insert(0, sys.argv[1]); import calcpad.export as e; e.browser_path()" "%SUITE%" >nul 2>nul
if errorlevel 1 echo   Note: Microsoft Edge or Google Chrome is required for PDF export.

echo.
"%PY%" server.py
if errorlevel 1 pause
endlocal
goto :eof

:missing_suite
echo InnoCalc suite.toml was not found above this application folder.
pause
exit /b 1
