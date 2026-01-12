@echo off
echo ========================================
echo   Gerador de Nova Versao - Comissys
echo ========================================
echo.

REM Verifica se PyInstaller está instalado
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller nao encontrado. Instalando...
    pip install pyinstaller
)

echo.
echo Iniciando gerador automatico de versao...
echo.

REM Executa o script Python que incrementa versão e gera exe
python build_version.py

pause
