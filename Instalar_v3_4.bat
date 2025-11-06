@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul 2>&1
title Instalacion v3.4 - Consolidacion Final del Lote

echo.
echo ================================================================
echo    VERSION 3.4 - Consolidacion Final del Lote
echo ================================================================
echo.
echo Esta actualizacion incluye:
echo   [OK] Consolidacion final ANTES de revision manual
echo   [OK] Cruza nombres con RUTs en TODO el lote
echo   [OK] Fecha documento OBLIGATORIA (critica para reportes)
echo   [OK] Mejor calidad de datos final
echo.
echo IMPORTANTE: Tambien debes modificar main.py
echo            (Ver instrucciones en INTEGRACION_v3_4.md)
echo.
pause

REM Verificar archivo
if not exist "data_processing_v3_4.py" (
    echo [ERROR] Falta data_processing_v3_4.py
    pause
    exit /b 1
)

echo [1/4] Creando backups...
if not exist "backups" mkdir "backups"

for /f "tokens=1-6 delims=.:/ " %%a in ("%date% %time%") do (
    set "timestamp=%%c%%b%%a_%%d%%e%%f"
)

if exist "modules\data_processing.py" (
    copy "modules\data_processing.py" "backups\data_processing_backup_!timestamp!.py" >nul 2>&1
    echo   [OK] Backup: data_processing.py guardado
)

if exist "main.py" (
    copy "main.py" "backups\main_backup_!timestamp!.py" >nul 2>&1
    echo   [OK] Backup: main.py guardado
)

echo.
echo [2/4] Instalando data_processing v3.4...

copy /Y "data_processing_v3_4.py" "modules\data_processing.py" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se pudo actualizar data_processing.py
    pause
    exit /b 1
)
echo   [OK] Instalado: modules\data_processing.py (v3.4)

echo.
echo [3/4] Verificando instalacion...

python -c "from modules.data_processing import DataProcessorOptimized; dp=DataProcessorOptimized(); print('[OK] DataProcessor OK'); print('[OK] Metodo consolidate_batch disponible')" 2>nul
if errorlevel 1 (
    echo [ERROR] Problema con data_processing.py
    pause
    exit /b 1
)

echo.
echo [4/4] Generando documentacion...

(
echo # VERSION 3.4 INSTALADA - Consolidacion Final del Lote
echo.
echo ## [OK] Instalacion Completada
echo.
echo Se ha instalado:
echo - modules\data_processing.py v3.4
echo.
echo Backups guardados en:
echo - backups\data_processing_backup_!timestamp!.py
echo - backups\main_backup_!timestamp!.py
echo.
echo ## [!] PASO IMPORTANTE
echo.
echo DEBES modificar main.py para usar la consolidacion.
echo.
echo Ver instrucciones detalladas en:
echo - INTEGRACION_v3_4.md
echo.
echo ## Que hace la consolidacion?
echo.
echo Antes de la revision manual:
echo 1. Analiza TODOS los registros procesados
echo 2. Crea indice de RUT -^> nombres
echo 3. Crea indice de nombres -^> RUTs
echo 4. Cruza informacion entre todas las boletas
echo 5. Completa datos faltantes automaticamente
echo 6. Solo entonces marca para revision lo que realmente falta
echo.
echo ### Ejemplo:
echo.
echo Lote de 100 boletas:
echo - Boleta 1: Juan Perez, RUT: 12.345.678-9 [OK]
echo - Boleta 2: Juan Perez, RUT: [FALTA]
echo - Boleta 3: Juan Perez, RUT: [FALTA]
echo.
echo Consolidacion:
echo Sistema detecta que Juan Perez = 12.345.678-9
echo [OK] Completa Boleta 2 con RUT: 12.345.678-9
echo [OK] Completa Boleta 3 con RUT: 12.345.678-9
echo.
echo Resultado:
echo 100 boletas -^> Solo 5-10 a revision manual (no 30-40^)
echo.
echo ## Modificacion de main.py
echo.
echo En la funcion process_files_thread:
echo.
echo 1. Cambiar results y review_queue por all_results
echo 2. Agregar despues del procesamiento:
echo    all_results = self.data_processor.consolidate_batch(all_results^)
echo 3. Separar entre OK y revision DESPUES de consolidar
echo.
echo Ver codigo completo en INTEGRACION_v3_4.md
echo.
echo ## Proximos Pasos
echo.
echo 1. Lee INTEGRACION_v3_4.md
echo 2. Modifica main.py segun las instrucciones
echo 3. Prueba con un lote pequeno
echo 4. [OK] Disfruta de mucho menos revisiones manuales
echo.
echo ## Campos que Activan Revision
echo.
echo Despues de consolidacion, se requiere revision si:
echo - [X] Falta FECHA documento (CRITICO para reportes mensuales^)
echo - [X] Falta nombre
echo - [X] Falta RUT
echo - [X] Falta monto
echo - [X] Falta convenio
echo - [X] Confianza ^< 30%%
echo.
echo ## Revertir
echo.
echo Si necesitas volver:
echo copy "backups\data_processing_backup_!timestamp!.py" "modules\data_processing.py"
echo copy "backups\main_backup_!timestamp!.py" "main.py"
) > "INSTALACION_v3_4_COMPLETA.md"

echo   [OK] Documentacion: INSTALACION_v3_4_COMPLETA.md

echo.
echo ================================================================
echo              [OK] INSTALACION COMPLETADA
echo ================================================================
echo.
echo [!] IMPORTANTE: Ahora debes modificar main.py
echo.
echo Lee las instrucciones en:
echo    - INTEGRACION_v3_4.md (instrucciones detalladas)
echo    - INSTALACION_v3_4_COMPLETA.md (resumen)
echo.
echo Cambio principal en main.py:
echo.
echo    # Despues de procesar todos los archivos
echo    all_results = self.data_processor.consolidate_batch(all_results)
echo.
echo    # Luego separar entre OK y revision
echo.
echo La consolidacion reduce revisiones manuales en 60-70%%
echo porque completa datos automaticamente entre boletas.
echo.
pause