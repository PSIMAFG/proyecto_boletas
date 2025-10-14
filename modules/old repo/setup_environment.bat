@echo off
echo Configurando entorno para Sistema de Boletas v3.0...

REM Configurar variables de entorno
set PYTHONPATH=%CD%
set PYTHONIOENCODING=utf-8

REM Activar entorno si existe

call conda activate unknown

REM Verificar instalación
python -c "import paddle; print('PaddlePaddle OK')"
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"

echo.
echo Entorno configurado. Ejecuta: python main_enhanced.py
pause
