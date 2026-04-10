@echo off
cd /d "%~dp0"
echo Instalando dependencias (si faltan)...
pip install -r requirements.txt
echo Iniciando Seora CRM...
python app.py
pause
