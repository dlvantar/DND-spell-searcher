@echo off
cd /d "%~dp0"
python build_exe.py
if errorlevel 1 (
    echo.
    echo [ERROR] build failed - see log above.
)
pause