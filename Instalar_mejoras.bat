@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul
title Instalación de Mejoras v3.2 - Sistema Boletas OCR

REM ——————————————————————————————————————————————————————————
REM 0) Anclarse a la carpeta del script (raíz del repo)
REM ——————————————————————————————————————————————————————————
pushd "%~dp0"

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║      INSTALACIÓN DE MEJORAS v3.2 - Sistema Boletas       ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo Este script instalará las mejoras críticas del sistema
echo.

REM Función auxiliar: abortar con código y mensaje
set "_FAILMSG="
set "_PY=python"
where py >nul 2>&1 && set "_PY=py -3"

REM 1) Verificar estructura mínima
echo [1/8] Verificando estructura del proyecto...
if not exist "modules" (
  echo ❌ ERROR: No existe la carpeta ^"modules^" en: %cd%
  goto :fail
)
if not exist "modules\__init__.py" (
  echo ⚠️  Aviso: creando modules\__init__.py (requerido para importar como paquete)
  > "modules\__init__.py" echo # paquete modules
)

if not exist "modules\data_processing.py" (
  echo ❌ ERROR: No se encuentra modules\data_processing.py
  echo    Ejecuta este script desde la raíz del proyecto: %cd%
  goto :fail
)

if not exist "data_processing_improved.py" (
  echo ❌ ERROR: No se encuentra data_processing_improved.py en la raíz del proyecto
  echo    Copia el archivo mejorado aquí: %cd%
  goto :fail
)
echo ✓ Archivos base encontrados
echo.

REM 2) Timestamp seguro para nombre de backup
echo [2/8] Creando backup del sistema actual...
for /f "tokens=1-6 delims=.:/ -_" %%a in ("%date% %time%") do (
  set _Y=!date:~-4!
  set _M=!date:~3,2!
  set _D=!date:~0,2!
  set _H=!time:~0,2!
  set _m=!time:~3,2!
  set _S=!time:~6,2!
)
set _H=%_H: =0%
set "timestamp=%_Y%%_M%%_D%_%_H%%_m%%_S%"

if not exist "backups" mkdir "backups" >nul 2>&1
copy "modules\data_processing.py" "backups\data_processing_backup_%timestamp%.py" >nul
if errorlevel 1 (
  echo ⚠️  Advertencia: No se pudo crear backup en ^"backups\^"
) else (
  echo ✓ Backup creado en: backups\data_processing_backup_%timestamp%.py
)
echo.

REM 3) Instalar versión mejorada
echo [3/8] Instalando versión mejorada...
copy /Y "data_processing_improved.py" "modules\data_processing.py" >nul
if errorlevel 1 (
  echo ❌ ERROR: No se pudo copiar data_processing_improved.py ^> modules\data_processing.py
  goto :fail
)
echo ✓ Archivo modules\data_processing.py actualizado
echo.

REM 4) Detectar/activar entorno Python (opcional venv)
echo [4/8] Verificando Python...
%_PY% --version
if errorlevel 1 (
  echo ❌ ERROR: No se encontró Python. Prueba instalando Python o usando ^"py -3^".
  goto :fail
)

REM Activar venv si existe
if exist ".venv\Scripts\activate.bat" (
  echo ↪ Detectado entorno virtual .venv, activando...
  call ".venv\Scripts\activate.bat"
  if errorlevel 1 (
    echo ⚠️  Advertencia: no se pudo activar .venv, continuo con el Python del sistema.
  )
)

echo ✓ Python disponible
echo.

REM 5) Comprobar dependencias mínimas (opcionales)
echo [5/8] Chequeando dependencias opcionales (cv2, numpy)...
%_PY% -c "import importlib,sys; \
mods=['cv2','numpy']; \
missing=[m for m in mods if importlib.util.find_spec(m) is None]; \
print('Faltan:' , ','.join(missing)) if missing else print('✓ Dependencias presentes')" 
echo.

REM 6) Importar módulo y mostrar ruta real para diagnosticar
echo [6/8] Verificando import de modules.data_processing...
%_PY% - <<PYCODE
import sys, os
print("sys.executable:", sys.executable)
print("cwd:", os.getcwd())
print("sys.path[0]:", sys.path[0])
try:
    import modules.data_processing as dp
    print("✓ Módulo data_processing importa correctamente:", dp.__file__)
except Exception as e:
    import traceback; traceback.print_exc(); raise
PYCODE
if errorlevel 1 (
  echo ❌ ERROR: Falló la importación de modules.data_processing
  echo    Verifica que ^"modules\__init__.py^" exista y dependencias estén instaladas.
  goto :fail
)
echo.

REM 7) Verificar clase esperada
echo [7/8] Verificando clase DataProcessorOptimized...
%_PY% - <<PYCODE
from modules.data_processing import DataProcessorOptimized
print("✓ Clase DataProcessorOptimized disponible")
PYCODE
if errorlevel 1 (
  echo ❌ ERROR: Clase DataProcessorOptimized no encontrada en modules\data_processing.py
  goto :fail
)
echo.

REM 8) Documentación y tests rápidos
echo [8/8] Instalando documentación y utilidades...
if not exist "docs" mkdir "docs" >nul 2>&1

if exist "MEJORAS_IMPLEMENTADAS.md" (
  copy /Y "MEJORAS_IMPLEMENTADAS.md" "docs\" >nul & if not errorlevel 1 echo ✓ MEJORAS_IMPLEMENTADAS.md
)
if exist "CASOS_DE_PRUEBA.md" (
  copy /Y "CASOS_DE_PRUEBA.md" "docs\" >nul & if not errorlevel 1 echo ✓ CASOS_DE_PRUEBA.md
)
if exist "RESUMEN_EJECUTIVO.md" (
  copy /Y "RESUMEN_EJECUTIVO.md" "docs\" >nul & if not errorlevel 1 echo ✓ RESUMEN_EJECUTIVO.md
)
if exist "test_quick.py" (
  copy /Y "test_quick.py" "." >nul & if not errorlevel 1 echo ✓ test_quick.py
)

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║              ✓ INSTALACIÓN COMPLETADA                     ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo 📦 Archivos instalados:
echo   • modules\data_processing.py (v3.2 Ultra-Robusto)
echo   • Backup en: backups\data_processing_backup_%timestamp%.py
echo.
echo 📋 Próximos pasos:
echo   1) python test_quick.py ruta\al\archivo.pdf
echo   2) python test_quick.py
echo   3) python main.py
echo.
echo ⚠️  El sistema es más conservador: más casos a revisión manual (intencional).
echo.
pause
popd
exit /b 0

:fail
echo.
echo ✖ Instalación abortada.
if defined _FAILMSG echo %_FAILMSG%
echo.
pause
popd
exit /b 1
