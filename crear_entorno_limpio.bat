@echo off
chcp 65001 >nul
cls
echo ╔═══════════════════════════════════════════════════════════╗
echo ║         CREAR ENTORNO VIRTUAL LIMPIO - Boletas v3.1      ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo Este script creará un entorno virtual aislado para evitar
echo conflictos con otros paquetes de Python instalados.
echo.
pause

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python NO encontrado
    pause
    exit /b 1
)

echo [1/7] Verificando Python...
python --version
echo.

REM Eliminar entorno virtual anterior si existe
if exist "venv_boletas" (
    echo [2/7] Eliminando entorno virtual anterior...
    rmdir /s /q venv_boletas
    echo ✓ Entorno anterior eliminado
) else (
    echo [2/7] No hay entorno anterior
)
echo.

REM Crear nuevo entorno virtual
echo [3/7] Creando entorno virtual nuevo...
python -m venv venv_boletas
if errorlevel 1 (
    echo ❌ Error creando entorno virtual
    echo    Intenta: pip install virtualenv
    pause
    exit /b 1
)
echo ✓ Entorno virtual creado
echo.

REM Activar entorno virtual
echo [4/7] Activando entorno virtual...
call venv_boletas\Scripts\activate.bat
echo ✓ Entorno activado
echo.

REM Actualizar pip en el entorno virtual
echo [5/7] Actualizando pip...
python -m pip install --upgrade pip --quiet
echo ✓ pip actualizado
echo.

REM Instalar dependencias en orden
echo [6/7] Instalando dependencias...
echo    → numpy...
pip install --no-cache-dir --only-binary :all: numpy==1.26.4 --quiet

echo    → pandas...
pip install --no-cache-dir --only-binary :all: pandas==2.2.2 --quiet

echo    → opencv...
pip install --no-cache-dir --only-binary :all: opencv-python-headless==4.10.0.84 --quiet

echo    → pillow...
pip install --no-cache-dir --only-binary :all: pillow==10.4.0 --quiet

echo    → pytesseract...
pip install --no-cache-dir pytesseract==0.3.10 --quiet

echo    → pdf2image...
pip install --no-cache-dir pdf2image==1.17.0 --quiet

echo    → openpyxl...
pip install --no-cache-dir --only-binary :all: openpyxl==3.1.5 --quiet

echo    → xlsxwriter...
pip install --no-cache-dir xlsxwriter==3.2.0 --quiet

echo    → pypdf...
pip install --no-cache-dir pypdf==4.3.1 --quiet

echo ✓ Todas las dependencias instaladas
echo.

REM Verificar instalación
echo [7/7] Verificando instalación...
python -c "import numpy, pandas, cv2, pytesseract, PIL, pdf2image, openpyxl, xlsxwriter, pypdf; print('✓ Todos los paquetes OK')"
if errorlevel 1 (
    echo ❌ Algunos paquetes no se instalaron correctamente
    pause
    exit /b 1
)
echo.

REM Crear script de activación rápida
echo @echo off > activar_entorno.bat
echo call venv_boletas\Scripts\activate.bat >> activar_entorno.bat
echo echo ╔═══════════════════════════════════════════════════════════╗ >> activar_entorno.bat
echo echo ║           ENTORNO VIRTUAL ACTIVADO - Boletas v3.1        ║ >> activar_entorno.bat
echo echo ╚═══════════════════════════════════════════════════════════╝ >> activar_entorno.bat
echo echo. >> activar_entorno.bat
echo echo Para ejecutar el sistema: python main.py >> activar_entorno.bat
echo echo. >> activar_entorno.bat

REM Crear script de ejecución directa
echo @echo off > ejecutar_con_entorno.bat
echo call venv_boletas\Scripts\activate.bat >> ejecutar_con_entorno.bat
echo python main.py >> ejecutar_con_entorno.bat
echo pause >> ejecutar_con_entorno.bat

echo ╔═══════════════════════════════════════════════════════════╗
echo ║                   ✓ INSTALACIÓN COMPLETA                  ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo Archivos creados:
echo   • venv_boletas/          - Entorno virtual
echo   • activar_entorno.bat    - Activa el entorno
echo   • ejecutar_con_entorno.bat - Ejecuta el sistema
echo.
echo PRÓXIMOS PASOS:
echo.
echo 1. Instalar Tesseract OCR desde:
echo    https://github.com/UB-Mannheim/tesseract/wiki
echo.
echo 2. Ejecutar el sistema:
echo    - Doble clic en: ejecutar_con_entorno.bat
echo    - O manualmente: activar_entorno.bat, luego python main.py
echo.
pause