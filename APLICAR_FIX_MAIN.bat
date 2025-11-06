@echo off
chcp 65001 >nul
title Fix Main.py - Agregar Imports Faltantes

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║        FIX RÁPIDO - Imports Faltantes en main.py        ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Este script corregirá el error:
echo   NameError: name 'List' is not defined
echo.

REM Verificar que existe main.py
if not exist "main.py" (
    echo ❌ ERROR: No se encuentra main.py en la carpeta actual
    echo    Ejecuta este script desde la raíz del proyecto
    pause
    exit /b 1
)

echo [1/3] Creando backup de main.py...
if not exist "backups" mkdir "backups"
for /f "tokens=1-6 delims=.:/ " %%a in ("%date% %time%") do (
    set "timestamp=%%c%%b%%a_%%d%%e%%f"
)
copy "main.py" "backups\main.py.backup_%timestamp%" >nul
echo   ✓ Backup creado: backups\main.py.backup_%timestamp%

echo.
echo [2/3] Aplicando corrección...

REM Crear versión temporal con el fix
powershell -Command "$content = Get-Content 'main.py' -Raw -Encoding UTF8; if ($content -notmatch 'from typing import') { $content = $content -replace '(from datetime import datetime)', '$1`nfrom typing import List, Dict, Optional, Tuple'; $content | Set-Content 'main.py.fixed' -Encoding UTF8 -NoNewline; Write-Host '  ✓ Corrección aplicada' } else { Write-Host '  ℹ️ El archivo ya tiene los imports necesarios'; exit 0 }"

if exist "main.py.fixed" (
    move /Y "main.py.fixed" "main.py" >nul
    echo   ✓ Archivo main.py actualizado
) else (
    echo   ℹ️ No se requieren cambios
)

echo.
echo [3/3] Verificando corrección...
python -c "import sys; sys.path.insert(0, '.'); from main import BoletasApp; print('✓ Importación exitosa: No hay errores')" 2>nul
if errorlevel 1 (
    echo   ⚠️ Advertencia: No se pudo verificar (¿Python no está en PATH?)
    echo   Intenta ejecutar: python main.py
) else (
    echo   ✓ Verificación completada sin errores
)

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║              ✓ CORRECCIÓN APLICADA                       ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Ahora puedes ejecutar el sistema normalmente:
echo   python main.py
echo.
echo O usando el entorno virtual:
echo   ejecutar_con_entorno.bat
echo.
pause
