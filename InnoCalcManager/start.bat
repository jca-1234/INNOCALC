@echo off
rem ======================================================================
rem  InnoCalc Manager - Innovis calculation management
rem  Starts the local service and opens http://127.0.0.1:8125/
rem
rem  Optional settings: remove the "rem" and edit as needed.
rem ======================================================================
rem set "ICM_ROOT=J:\Active Projects"
rem set "ICM_PORT=8125"

setlocal EnableExtensions
rem Suite root with no trailing backslash, so it can be quoted safely below.
for %%I in ("%~dp0..") do set "SUITE=%%~fI"
cd /d "%~dp0"

rem ---- find a Python interpreter ---------------------------------------
set "PY=%SUITE%\.venv\Scripts\python.exe"
if exist "%PY%" goto :have_python
set "PY=%SUITE%\SteelMemberDesign\.venv\Scripts\python.exe"
if exist "%PY%" goto :have_python

set "BOOT="
where py >nul 2>nul && set "BOOT=py -3"
if defined BOOT goto :make_venv
where python >nul 2>nul && set "BOOT=python"
if defined BOOT goto :make_venv
goto :no_python

:make_venv
echo Creating the Python environment in "%SUITE%\.venv" ...
%BOOT% -m venv "%SUITE%\.venv"
if errorlevel 1 goto :venv_failed
set "PY=%SUITE%\.venv\Scripts\python.exe"

:have_python
rem ---- pypdf combines drawing sets and PDF inserts ----------------------
"%PY%" -c "import pypdf" >nul 2>nul
if errorlevel 1 (
    echo Installing pypdf ...
    "%PY%" -m pip install --quiet --disable-pip-version-check pypdf
)

rem ---- Chromium produces the PDFs --------------------------------------
"%PY%" -c "import sys; sys.path.insert(0, sys.argv[1]); import calcpad.export as e; e.browser_path()" "%SUITE%" >nul 2>nul
if errorlevel 1 echo   Note: Microsoft Edge or Google Chrome is required for PDF export.

echo.
"%PY%" server.py
if errorlevel 1 pause
endlocal
goto :eof

:no_python
echo.
echo   Python was not found on this machine.
echo   Install Python 3.11 or later from https://www.python.org/downloads/
echo   ticking "Add python.exe to PATH", then run this file again.
echo.
pause
goto :eof

:venv_failed
echo.
echo   Could not create the Python environment in "%SUITE%\.venv".
echo   Check that you have write access to that folder.
echo.
pause
goto :eof
