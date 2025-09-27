@echo off
cd /d "%~dp0"
call ..\venv\Scripts\activate.bat
echo Ambiente virtual ativado!
echo Diretório atual: %CD%
cmd