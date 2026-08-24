@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo WinDev — server web local
echo.

python -c "import flask, pypxlib, openpyxl" 2>nul
if errorlevel 1 (
    echo Instalez dependențele...
    pip install -r requirements.txt
)

set WINDEV_PORT=8080
echo Pornesc WinDev pe http://localhost:%WINDEV_PORT%
echo.
python web\app.py
pause
