@echo off
REM ejecutar_boletas.bat
REM SIEMPRE usa este script para ejecutar el programa

echo ============================================================
echo SISTEMA DE BOLETAS CON PADDLEOCR
echo ============================================================
echo.

REM Activar el entorno correcto
echo Activando entorno Python 3.10...
call conda activate boletas310

REM Verificar versión
python --version | findstr "3.10"
if errorlevel 1 (
    echo.
    echo ERROR: El entorno no tiene Python 3.10
    echo.
    echo Ejecuta primero: install_paddle_definitivo.bat
    pause
    exit /b 1
)

REM Verificar que PaddleOCR funciona
echo.
echo Verificando PaddleOCR...
python -c "from paddleocr import PaddleOCR; print('PaddleOCR: OK')" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: PaddleOCR no esta instalado correctamente
    echo.
    echo Ejecuta primero: install_paddle_definitivo.bat
    pause
    exit /b 1
)

echo.
echo [OK] Todo listo - Iniciando programa...
echo.

REM Ejecutar el programa principal
python main_enhanced.py

pause
