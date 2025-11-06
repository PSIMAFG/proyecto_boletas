@echo off
setlocal enableextensions
title Instalacion v4.0 FINAL - Post-procesamiento Inteligente

rem Forzar a ejecutar desde la carpeta del script
pushd "%~dp0" 1>nul 2>nul || (
  echo [ERROR] No se pudo cambiar al directorio del script: "%~dp0"
  pause & exit /b 1
)

echo.
echo ===============================================================
echo    ACTUALIZACION v4.0 FINAL - Sistema Inteligente
echo ===============================================================
echo.
echo Esta actualizacion incluye:
echo   [OK] Post-procesamiento despues de extraer TODAS las boletas
echo   [OK] Busqueda cruzada masiva
echo   [OK] Inferencia decreto-convenio automatica
echo   [OK] Revision automatica incremental
echo   [OK] Generacion de reportes individuales
echo.
echo Reduccion esperada: de 37/240 (15%%) a 2-5/240 (0.8-2%%)
echo.

rem --- Comprobaciones basicas ---
if not exist "modules\" (
  echo [ERROR] No se encontro la carpeta "modules" en: "%cd%"
  pause & exit /b 1
)

if not exist "data_processing_v4_FINAL.py" (
  echo [ERROR] Falta data_processing_v4_FINAL.py en: "%cd%"
  pause & exit /b 1
)

if not exist "main_v4_FINAL.py" (
  echo [ERROR] Falta main_v4_FINAL.py en: "%cd%"
  pause & exit /b 1
)

rem --- Timestamp solo con numeros ---
for /f "tokens=1-3 delims=/- " %%a in ("%date%") do set FECHA=%%c%%a%%b
for /f "tokens=1-3 delims=:." %%a in ("%time%") do set HORA=00%%a%%b%%c
set HORA=%HORA:~-6%
set TS=%FECHA%_%HORA%

echo [1/5] Creando backups de seguridad...
if not exist "backups" mkdir "backups" >nul
if exist "main.py" copy /y "main.py" "backups\main_backup_%TS%.py" >nul && echo   [OK] Backup: main.py
if exist "modules\data_processing.py" copy /y "modules\data_processing.py" "backups\data_processing_backup_%TS%.py" >nul && echo   [OK] Backup: data_processing.py

echo.
echo [2/5] Verificando archivos mejorados...
echo   [OK] Archivos mejorados encontrados

echo.
echo [3/5] Instalando versiones mejoradas...
copy /y "data_processing_v4_FINAL.py" "modules\data_processing.py" >nul || (echo [ERROR] No se pudo actualizar modules\data_processing.py & pause & exit /b 1)
echo   [OK] Instalado: modules\data_processing.py
copy /y "main_v4_FINAL.py" "main.py" >nul || (echo [ERROR] No se pudo actualizar main.py & pause & exit /b 1)
echo   [OK] Instalado: main.py

echo.
REM ===== [4/5] Verificando instalacion =====
echo.
echo [4/5] Verificando instalacion...

REM Pequeño delay por antivirus/lock de archivos recien copiados
ping -n 2 127.0.0.1 >nul

REM Detectar python
set "PYEXE="
where python >nul 2>&1 && set "PYEXE=python"
if not defined PYEXE (
  where py >nul 2>&1 && set "PYEXE=py -3"
)

if defined PYEXE (
  set "TMPFILE=%TEMP%\check_import_%RANDOM%_%TS%.py"
  if exist "%TMPFILE%" del /f /q "%TMPFILE%" >nul 2>&1

  > "%TMPFILE%" echo from importlib import import_module
  >> "%TMPFILE%" echo m = import_module("modules.data_processing")
  >> "%TMPFILE%" echo getattr(m, "DataProcessorOptimized")
  >> "%TMPFILE%" echo getattr(m, "IntelligentBatchProcessor")
  >> "%TMPFILE%" echo print("OK")

  REM Pequeño delay extra por si algun proceso indexa el archivo temporal
  ping -n 2 127.0.0.1 >nul

  %PYEXE% "%TMPFILE%" >nul 2>&1
  set "VERIFY_ERR=%ERRORLEVEL%"

  if exist "%TMPFILE%" del /f /q "%TMPFILE%" >nul 2>&1

  if not "%VERIFY_ERR%"=="0" (
    echo [ERROR] Fallo la importacion de modules.data_processing
    echo         Es probable que algun proceso tenga archivos bloqueados.
    echo         Restaurando backups si existen...
    if exist "backups\data_processing_backup_%TS%.py" copy /y "backups\data_processing_backup_%TS%.py" "modules\data_processing.py" >nul
    if exist "backups\main_backup_%TS%.py" copy /y "backups\main_backup_%TS%.py" "main.py" >nul
    echo         Sugerencias:
    echo           - Cierra VSCode/Notepad u otros editores abiertos sobre .py
    echo           - Cierra instancias de python:  tasklist ^| find /I "python"
    echo           - Espera 10-20s (antivirus/indexador) y reintenta
    pause
    popd >nul
    exit /b 1
  ) else (
    echo   [OK] Verificacion de import completada
  )
) else (
  echo [WARN] No se encontro python/py en PATH. Omitiendo verificacion.
)echo [5/5] Creando documentacion...
> "INSTALACION_v4_FINAL.md" (
  echo # ACTUALIZACION v4.0 FINAL - Post-procesamiento Inteligente
  echo
  echo ## Resumen
  echo - Post-procesamiento con base del batch completo
  echo - Inferencia decreto-convenio
  echo - Busqueda cruzada masiva (nombre^/RUT)
  echo - Revision automatica incremental
  echo - Reportes individuales por profesional
  echo
  echo ## Revertir cambios
  echo copy "backups\main_backup_%TS%.py" "main.py"
  echo copy "backups\data_processing_backup_%TS%.py" "modules\data_processing.py"
)
echo   [OK] Documentacion creada: INSTALACION_v4_FINAL.md

echo.
echo ===============================================================
echo              INSTALACION COMPLETADA
echo ===============================================================
echo.
echo Archivos actualizados:
echo   - modules\data_processing.py
echo   - main.py
echo Backups: backups\*_backup_%TS%.py
echo.
echo Proximos pasos:
echo   1) python main.py   (o)  py -3 main.py
echo.
if exist _check_import.py del _check_import.py >nul
pause
popd >nul
exit /b 0
