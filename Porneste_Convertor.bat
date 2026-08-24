@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Verific dependențele Python...
python -c "import pypxlib, openpyxl" 2>nul
if errorlevel 1 (
    echo Instalez dependențele Python...
    pip install -r requirements.txt
)

python app.py
if errorlevel 1 pause
