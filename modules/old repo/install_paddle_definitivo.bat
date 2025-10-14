@echo off
REM install_paddle_definitivo.bat
REM Script definitivo para instalar PaddleOCR correctamente

echo ============================================================
echo INSTALACION DEFINITIVA DE PADDLEOCR
echo ============================================================
echo.

REM Verificar que estamos en el entorno correcto
python --version | findstr "3.10"
if errorlevel 1 (
    echo ERROR: No estas en Python 3.10
    echo Ejecuta primero:
    echo   conda activate boletas310
    pause
    exit /b 1
)

echo [OK] Python 3.10 detectado
echo.

echo Paso 1: Limpiando instalaciones anteriores...
pip uninstall -y numpy opencv-python opencv-contrib-python opencv-python-headless paddlepaddle paddleocr

echo.
echo Paso 2: Instalando NumPy compatible...
pip install numpy==1.23.5

echo.
echo Paso 3: Instalando OpenCV compatible...
pip install opencv-python==4.6.0.66

echo.
echo Paso 4: Instalando PaddlePaddle...
pip install paddlepaddle==2.5.2 -i https://pypi.org/simple/

echo.
echo Paso 5: Instalando PaddleOCR y dependencias...
pip install shapely==2.0.2
pip install scikit-image==0.21.0
pip install imgaug==0.4.0
pip install pyclipper==1.3.0.post5
pip install lmdb==1.4.1
pip install rapidfuzz==3.5.0
pip install Pillow==10.0.0
pip install PyMuPDF==1.23.8
pip install attrdict==2.0.1
pip install paddleocr==2.7.0.3

echo.
echo Paso 6: Instalando resto de dependencias...
pip install pytesseract pdf2image pandas openpyxl xlsxwriter pypdf

echo.
echo ============================================================
echo VERIFICACION
echo ============================================================

python -c "import paddle; print(f'PaddlePaddle Version: {paddle.__version__}')"
if errorlevel 1 (
    echo [ERROR] PaddlePaddle no funciona
) else (
    echo [OK] PaddlePaddle funciona
)

python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
if errorlevel 1 (
    echo [ERROR] PaddleOCR no funciona
) else (
    echo [OK] PaddleOCR funciona
)

echo.
echo ============================================================
echo INSTALACION COMPLETADA
echo ============================================================
echo.
echo Para ejecutar el programa:
echo   1. Siempre activa primero el entorno: conda activate boletas310
echo   2. Luego ejecuta: python main_enhanced.py
echo.
pause