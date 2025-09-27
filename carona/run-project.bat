@echo off
cd /d "%~dp0"
call ..\venv\Scripts\activate.bat
echo Ambiente virtual ativado!
echo Iniciando o servidor Django...
python manage.py runserver
pause