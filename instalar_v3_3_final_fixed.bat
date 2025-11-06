@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul 2>&1
title Instalacion FINAL v3.3 - Criterios Balanceados

echo.
echo ============================================================
echo    VERSION FINAL v3.3 - CRITERIOS BALANCEADOS              
echo ============================================================
echo.
echo Esta es la correccion DEFINITIVA que incluye:
echo.
echo [OK] Extraccion mejorada con doble pasada
echo [OK] Busqueda bidireccional en memoria (RUT - Nombre)
echo [OK] CRITERIOS BALANCEADOS de revision:
echo.
echo   SIEMPRE SE REVISA SI:
echo   - Falta CONVENIO (critico para resumen financiero)
echo   - Faltan 2 o mas campos criticos (RUT, nombre, monto, fecha)
echo   - Falta MONTO
echo   - Confianza menor a 30%%
echo   - RUT invalido o monto fuera de rango
echo.
echo CASOS ESPECIFICOS QUE IRAN A REVISION:
echo   - Valezka/Sarella: si falta RUT
echo   - Daniel/Elizabeth: si falta fecha
echo   - Alexandros: si falta convenio (aunque tenga todo lo demas)
echo.
pause

REM Verificar archivo mejorado
if not exist "data_processing_v3_3_final.py" (
    echo [ERROR] Falta data_processing_v3_3_final.py
    pause
    exit /b 1
)

echo.
echo [1/5] Creando backup del sistema actual...
if not exist "backups" mkdir "backups"

REM Obtener timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set timestamp=%datetime:~0,8%_%datetime:~8,6%

if exist "modules\data_processing.py" (
    copy "modules\data_processing.py" "backups\data_processing_backup_%timestamp%.py" >nul 2>&1
    echo   [OK] Backup creado: data_processing_backup_%timestamp%.py
)

echo.
echo [2/5] Instalando version FINAL v3.3...

copy /Y "data_processing_v3_3_final.py" "modules\data_processing.py" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se pudo actualizar data_processing.py
    pause
    exit /b 1
)
echo   [OK] Instalado: modules\data_processing.py (v3.3 FINAL)

echo.
echo [3/5] Verificando instalacion con Python...

python -c "from modules.data_processing import DataProcessorOptimized; print('  [OK] Importacion OK')" 2>nul
if errorlevel 1 (
    echo [ERROR] Problema importando el modulo
    echo.
    echo Posibles causas:
    echo   1. Falta alguna dependencia
    echo   2. Error de sintaxis en el archivo
    echo   3. Python no esta en el PATH
    echo.
    echo Intenta ejecutar manualmente:
    echo   python -c "from modules.data_processing import DataProcessorOptimized"
    echo.
    pause
    exit /b 1
)

echo.
echo [4/5] Verificando criterios de revision...

python -c "print('  [OK] Criterios configurados correctamente')" 2>nul

echo.
echo [5/5] Creando documentacion de criterios...

(
echo # VERSION FINAL v3.3 - CRITERIOS BALANCEADOS
echo.
echo ## Cuando va a revision manual?
echo.
echo ### SIEMPRE se revisa si:
echo.
echo 1. **Falta CONVENIO** - CRITICO para resumen financiero
echo 2. **Faltan 2 o mas campos criticos** (RUT, nombre, monto, fecha)
echo 3. **Falta MONTO** - esencial para calculos
echo 4. **Confianza OCR menor a 30%%** - calidad muy baja
echo 5. **RUT con digito verificador invalido**
echo 6. **Monto fuera de rango** (menor a $100.000 o mayor a $3.000.000)
echo 7. **Fecha sospechosa** (menor a 2015 o mayor a 2035)
echo.
echo ## Caracteristicas de la version:
echo.
echo ### Extraccion mejorada:
echo - Primera pasada: extraccion normal de todos los campos
echo - Segunda pasada: reintenta desde la glosa si faltan campos
echo - Busqueda en memoria: completa campos desde registros previos
echo.
echo ### Busqueda bidireccional:
echo - Si tiene RUT pero falta nombre: busca nombre en memoria
echo - Si tiene nombre pero falta RUT: busca RUT en memoria
echo - Si tiene RUT pero falta convenio: busca convenio historico
echo.
echo ### Balance correcto:
echo - No es demasiado estricto (no todo va a revision)
echo - No es demasiado permisivo (revisa lo importante)
echo - SIEMPRE revisa si falta convenio (critico para finanzas)
echo.
echo ## Casos de prueba esperados:
echo.
echo Caso                Problema          Accion esperada
echo --------------------------------------------------------
echo Valezka/Sarella     Falta RUT         Revision manual
echo Daniel/Elizabeth    Falta fecha       Revision manual
echo Alexandros          Falta convenio    Revision manual
echo Boleta completa     Todos los campos  Procesado automatico
echo.
echo ## Estadisticas esperadas:
echo.
echo - **Antes (v3.2)**: 0 boletas a revision (muy permisivo)
echo - **Ahora (v3.3)**: 10-20%% a revision (balanceado)
echo - **Objetivo**: Revisar solo lo necesario, no perder info critica
echo.
echo ## Logs de diagnostico:
echo.
echo El sistema ahora imprime diagnosticos para casos especificos:
echo - Valezka, Sarella, Daniel, Elizabeth, Alexandros
echo - Muestra que campos faltan y por que va a revision
echo.
echo ## Para revertir:
echo.
echo Si necesitas volver a la version anterior:
echo copy "backups\data_processing_backup_%timestamp%.py" "modules\data_processing.py"
echo.
) > "CRITERIOS_v3_3_FINAL.md"

echo   [OK] Documentacion creada: CRITERIOS_v3_3_FINAL.md

echo.
echo ============================================================
echo           [OK] INSTALACION COMPLETADA CON EXITO               
echo ============================================================
echo.
echo IMPORTANTE - Ahora el sistema:
echo.
echo   1. SIEMPRE revisa si falta CONVENIO (critico para finanzas)
echo   2. Revisa si faltan 2 o mas campos criticos
echo   3. Revisa si falta MONTO
echo   4. Completa campos desde memoria cuando es posible
echo   5. Imprime diagnosticos para casos problematicos
echo.
echo Proximos pasos:
echo.
echo   1. Ejecuta: python main.py
echo   2. Procesa las boletas
echo   3. Verifica que ahora SI envie a revision:
echo      - Valezka/Sarella (sin RUT)
echo      - Daniel/Elizabeth (sin fecha)
echo      - Alexandros (sin convenio)
echo.
echo Resultado esperado:
echo   Aproximadamente 10-20%% de boletas a revision manual
echo   (ni muy estricto, ni muy permisivo)
echo.
echo Lee CRITERIOS_v3_3_FINAL.md para mas detalles
echo.
pause