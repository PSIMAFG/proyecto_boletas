@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Solución Completa - Fix Main.py

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║      SOLUCIÓN COMPLETA - Sistema de Boletas OCR          ║
echo ║           Fix + Verificación + Listo para Usar           ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Verificar Python
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Python no encontrado
    echo   Instala Python desde: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo   ✓ %%i

REM Verificar main.py
echo.
echo [2/5] Verificando archivos del proyecto...
if not exist "main.py" (
    echo   ❌ main.py no encontrado
    echo   Ejecuta este script desde la raíz del proyecto
    pause
    exit /b 1
)
echo   ✓ main.py encontrado

if not exist "modules" (
    echo   ❌ Carpeta 'modules' no encontrada
    pause
    exit /b 1
)
echo   ✓ Carpeta 'modules' encontrada

REM Aplicar fix
echo.
echo [3/5] Aplicando corrección...

REM Verificar si ya tiene el fix
findstr /C:"from typing import" main.py >nul
if not errorlevel 1 (
    echo   ℹ️  El archivo ya tiene los imports necesarios
    goto :verificar
)

REM Crear backup
if not exist "backups" mkdir "backups"
for /f "tokens=1-6 delims=.:/ " %%a in ("%date% %time%") do (
    set "timestamp=%%c%%b%%a_%%d%%e%%f"
)
copy "main.py" "backups\main.py.backup_!timestamp!" >nul 2>&1
if not errorlevel 1 (
    echo   ✓ Backup creado
) else (
    echo   ⚠️  No se pudo crear backup
)

REM Aplicar fix con PowerShell
powershell -NoProfile -Command ^
    "$content = Get-Content 'main.py' -Raw -Encoding UTF8; ^
     $newLine = 'from typing import List, Dict, Optional, Tuple'; ^
     if ($content -match '(from datetime import datetime)') { ^
         $content = $content -replace '(from datetime import datetime)', ('^$1' + [Environment]::NewLine + $newLine); ^
         $content | Set-Content 'main.py' -Encoding UTF8 -NoNewline; ^
         Write-Host '  ✓ Corrección aplicada exitosamente' ^
     } else { ^
         Write-Host '  ⚠️  No se encontró la línea de referencia' ^
     }"

if errorlevel 1 (
    echo   ❌ Error aplicando corrección
    echo   Intenta manualmente: agrega esta línea después de "from datetime import datetime"
    echo   from typing import List, Dict, Optional, Tuple
    pause
    exit /b 1
)

:verificar
REM Verificación rápida
echo.
echo [4/5] Verificando corrección...
python -c "from typing import List, Dict, Optional, Tuple; print('  ✓ Imports de typing funcionan')" 2>nul
if errorlevel 1 (
    echo   ⚠️  Advertencia: No se pudo verificar typing
)

python -c "import sys; sys.path.insert(0, '.'); from main import BoletasApp; print('  ✓ main.py se importa correctamente')" 2>nul
if errorlevel 1 (
    echo   ⚠️  Advertencia: Verifica dependencias con: pip install -r requirements.txt
) else (
    echo   ✓ main.py verificado
)

REM Test final
echo.
echo [5/5] Verificación completa del sistema...
echo.

if exist "verificar_sistema_completo.py" (
    python verificar_sistema_completo.py
) else (
    echo   ℹ️  verificar_sistema_completo.py no encontrado
    echo   Verificación básica completada
)

REM Resumen
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                ✓ SOLUCIÓN APLICADA                       ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo El sistema está listo para usar. Para iniciar:
echo.
echo   Opción 1: python main.py
echo   Opción 2: ejecutar_con_entorno.bat
echo.
echo Si encuentras problemas:
echo   1. Lee: SOLUCION_COMPLETA.md
echo   2. Ejecuta: python verificar_sistema_completo.py
echo   3. Verifica dependencias: pip install -r requirements.txt
echo.

REM Preguntar si quiere ejecutar ahora
set /p "ejecutar=¿Deseas ejecutar el sistema ahora? (S/N): "
if /i "!ejecutar!"=="S" (
    echo.
    echo Iniciando sistema...
    echo.
    python main.py
)

echo.
pause
