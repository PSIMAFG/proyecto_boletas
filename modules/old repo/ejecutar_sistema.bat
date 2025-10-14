# ============================================================================
# ejecutar_sistema.bat
# ============================================================================
@echo off
title Sistema de Boletas de Honorarios v3.0
cls

echo =====================================================
echo    SISTEMA DE BOLETAS DE HONORARIOS v3.0
echo    Iniciando...
echo =====================================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado o no está en PATH
    echo.
    echo Por favor instale Python desde: https://python.org
    echo Asegúrese de marcar "Add Python to PATH" durante la instalación
    echo.
    pause
    exit /b 1
)

echo Ejecutando sistema...
echo.

REM Ejecutar el programa principal
python main.py

if errorlevel 1 (
    echo.
    echo =====================================================
    echo Ha ocurrido un error al ejecutar el programa
    echo =====================================================
    pause
)

exit /b 0


