@echo off
setlocal EnableExtensions
cd /d "%~dp0"
rem Steel, Concrete Column and Calculation Pad are submodules; fetch any that are missing.
if not exist "calculations\steel\member\.git" git submodule update --init --recursive
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-dev.lock
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install --no-build-isolation --no-deps -e .
if errorlevel 1 exit /b 1
if exist "calculations\general\calculation_pad\pyproject.toml" (
    ".venv\Scripts\python.exe" -m pip install --no-build-isolation --no-deps -e calculations\general\calculation_pad
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m tooling check --all
exit /b %errorlevel%