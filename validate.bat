@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -B -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -B -m tooling check --all --validate
exit /b %errorlevel%