@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem --- titulo y cabecera (ASCII, sin tildes/emoji) ---
title Instalacion Reportes Individuales por Profesional
echo.
echo ===========================================================
echo =   INSTALACION: REPORTES INDIVIDUALES POR PROFESIONAL    =
echo ===========================================================
echo.
echo Esta actualizacion agrega la capacidad de generar
echo automaticamente un Excel por cada profesional.
echo.
echo Caracteristicas:
echo   - Verificacion cruzada Nombre-RUT
echo   - Tabla detallada por profesional
echo   - Calculo automatico de totales
echo   - Resumen por convenio si aplica
echo   - Advertencias de inconsistencias
echo.
pause

rem --- verificaciones basicas ---
if not exist "main_1.py" (
    echo ERROR: Archivo main_1.py no encontrado
    echo Ejecuta este script desde la raiz del proyecto
    pause
    exit /b 1
)

if not exist "modules\report_generator.py" (
    echo ERROR: Archivo modules\report_generator.py no encontrado
    pause
    exit /b 1
)

echo.
echo [1/4] Creando backups...

if not exist "backups" mkdir "backups"

rem --- timestamp robusto (independiente de la configuracion regional) ---
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyyMMdd_HHmmss\")"') do set "timestamp=%%i"
if not defined timestamp (
    echo ADVERTENCIA: No se pudo generar timestamp; usando valor por defecto
    set "timestamp=00000000_000000"
)

rem --- backup de main.py solo si existe ---
if exist "main.py" (
    copy /Y "main.py" "backups\main_backup_%timestamp%.py" >nul
    if errorlevel 1 (
        echo ERROR: No se pudo crear backup de main.py
        pause
        exit /b 1
    )
    echo   OK: Backup de main.py
) else (
    echo   INFO: No existe main.py previo (no se crea backup)
)

rem --- backup de report_generator.py ---
copy /Y "modules\report_generator.py" "backups\report_generator_backup_%timestamp%.py" >nul
if errorlevel 1 (
    echo ERROR: No se pudo crear backup de report_generator.py
    pause
    exit /b 1
)
echo   OK: Backup de report_generator.py

echo.
echo [2/4] Verificando archivos nuevos...

if not exist "report_generator.py" (
    echo ERROR: Falta archivo report_generator.py actualizado en la raiz
    echo Descarga los archivos desde el repositorio y vuelve a intentar
    pause
    exit /b 1
)
echo   OK: report_generator.py encontrado

if exist "main_1.py.new" (
    echo   OK: main_1.py.new encontrado (se usara para actualizar main.py)
) else (
    if exist "main_1.py" (
        echo   INFO: No hay main_1.py.new, se usara main_1.py para actualizar main.py
    ) else (
        echo ERROR: No se encuentra main_1.py
        pause
        exit /b 1
    )
)

echo.
echo [3/4] Instalando archivos actualizados...

rem --- actualizar modules\report_generator.py ---
copy /Y "report_generator.py" "modules\report_generator.py" >nul
if errorlevel 1 (
    echo ERROR: No se pudo actualizar modules\report_generator.py
    echo Restaurando backup...
    copy /Y "backups\report_generator_backup_%timestamp%.py" "modules\report_generator.py" >nul
    pause
    exit /b 1
)
echo   OK: modules\report_generator.py actualizado

rem --- actualizar main.py desde la version correcta ---
if exist "main_1.py.new" (
    copy /Y "main_1.py.new" "main.py" >nul
    if errorlevel 1 (
        echo ERROR: No se pudo actualizar main.py desde main_1.py.new
        pause
        exit /b 1
    )
    echo   OK: main.py actualizado desde main_1.py.new
) else (
    copy /Y "main_1.py" "main.py" >nul
    if errorlevel 1 (
        echo ERROR: No se pudo actualizar main.py desde main_1.py
        pause
        exit /b 1
    )
    echo   OK: main.py actualizado desde main_1.py
)

echo.
echo [4/4] Verificando instalacion...

rem --- prueba basica de import en ASCII (sin caracteres especiales) ---
python -c "from modules.report_generator import ReportGenerator; _=ReportGenerator(); print('report_generator OK'); print('install OK')"
if errorlevel 1 (
    echo ERROR: Problema al importar modules.report_generator
    echo Restaurando backup de report_generator.py...
    copy /Y "backups\report_generator_backup_%timestamp%.py" "modules\report_generator.py" >nul
    pause
    exit /b 1
)

echo.
echo ===========================================================
echo =              INSTALACION COMPLETADA                     =
echo ===========================================================
echo.
echo Archivos instalados:
echo   - modules\report_generator.py (con reportes individuales)
echo   - main.py (con opcion de reportes individuales)
echo   - Backups en: backups\*_backup_%timestamp%.py
echo.
echo Como usar:
echo   1) Ejecuta: python main.py
echo   2) Marca: "Generar reportes individuales por profesional"
echo   3) Procesa tus boletas normalmente
echo   4) Resultado:
echo      - Excel principal: Export\boletas_procesadas.xlsx
echo      - Reportes individuales: Export\Reportes_Individuales\
echo.
echo Tip: Los reportes individuales incluyen:
echo   - Tabla detallada de boletas por profesional
echo   - Total automatico con formulas
echo   - Verificacion nombre-RUT
echo   - Resumen por convenio
echo.
pause

echo.
set "respuesta="
set /p respuesta=Deseas hacer una prueba rapida? (S/N):
if /i "!respuesta!"=="S" (
    echo.
    echo Ejecutando prueba...
    python -c "from modules.report_generator import ReportGenerator; import pandas as pd; _=ReportGenerator(); print('modulos cargados correctamente'); print('sistema listo para usar')"
    if errorlevel 1 (
        echo ERROR: Hubo un problema en la prueba rapida
        echo Revisa los mensajes anteriores
    ) else (
        echo OK: Prueba rapida exitosa
    )
)

echo.
echo Instalacion finalizada. Presiona cualquier tecla para salir.
pause >nul

endlocal
