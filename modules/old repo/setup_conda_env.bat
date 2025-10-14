@echo off
REM setup_conda_env.bat - Configuración automática del entorno conda Python 3.10

echo ======================================================================
echo CONFIGURACION AUTOMATICA - SISTEMA BOLETAS CON PADDLEOCR
echo ======================================================================
echo.

REM Verificar si conda está disponible
where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Conda no encontrado en PATH
    echo Asegurate de tener Miniconda o Anaconda instalado
    pause
    exit /b 1
)

echo Paso 1: Eliminando entorno anterior si existe...
call conda env remove -n boletas310 -y >nul 2>&1

echo Paso 2: Creando nuevo entorno con Python 3.10...
call conda create -n boletas310 python=3.10 -y
if %errorlevel% neq 0 (
    echo ERROR: No se pudo crear el entorno
    pause
    exit /b 1
)

echo Paso 3: Activando entorno...
call conda activate boletas310

echo Paso 4: Instalando paquetes...
python fix_paddle_install.py

echo.
echo ======================================================================
echo CONFIGURACION COMPLETADA
echo ======================================================================
echo.
echo Para usar el sistema:
echo   1. Abre una nueva terminal
echo   2. Ejecuta: conda activate boletas310
echo   3. Ejecuta: python main_enhanced.py
echo.
echo IMPORTANTE: Siempre activa el entorno boletas310 antes de usar el sistema
echo.
pause