# ============================================================================
# crear_entorno_python310.bat
# ============================================================================
@echo off
title Creador de Entorno Python 3.10
cls

echo =====================================================
echo    CREADOR DE ENTORNO PYTHON 3.10 PARA PADDLEOCR
echo =====================================================
echo.
echo Este script creará un entorno virtual con Python 3.10
echo para compatibilidad óptima con PaddleOCR
echo.

REM Verificar si existe conda
where conda >nul 2>&1
if errorlevel 1 (
    echo Conda no está instalado. Intentando con venv...
    echo.
    
    REM Verificar versión de Python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
    echo Python actual: %PYVER%
    
    echo.
    echo Creando entorno virtual...
    python -m venv venv_boletas
    
    echo.
    echo Activando entorno...
    call venv_boletas\Scripts\activate.bat
    
    echo.
    echo Instalando dependencias...
    pip install --upgrade pip
    pip install -r requirements_auto.txt
    
    echo.
    echo =====================================================
    echo Entorno creado exitosamente
    echo.
    echo Para usar el sistema:
    echo   1. venv_boletas\Scripts\activate.bat
    echo   2. python main.py
    echo =====================================================
    
) else (
    echo Conda detectado. Creando entorno con Python 3.10...
    echo.
    
    REM Crear entorno con conda
    conda create -n boletas_env python=3.10 -y
    
    echo.
    echo Activando entorno...
    call conda activate boletas_env
    
    echo.
    echo Instalando dependencias...
    pip install --upgrade pip
    pip install -r requirements_auto.txt
    
    echo.
    echo =====================================================
    echo Entorno conda creado exitosamente
    echo.
    echo Para usar el sistema:
    echo   1. conda activate boletas_env
    echo   2. python main.py
    echo =====================================================
)

pause
exit /b 0


