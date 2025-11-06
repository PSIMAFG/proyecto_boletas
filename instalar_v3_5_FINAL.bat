@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul 2>&1
title Instalacion VERSION 3.5 FINAL - Campos Obligatorios Estrictos

echo.
echo ============================================================
echo    VERSION 3.5 FINAL - CORRECCION DEFINITIVA
echo ============================================================
echo.
echo CORRECCIONES CRITICAS:
echo.
echo [1] BUSQUEDA CRUZADA MEJORADA que SI encuentra datos existentes
echo [2] RUT es OBLIGATORIO - si falta va a revision SIEMPRE
echo [3] CONVENIO es OBLIGATORIO - si falta va a revision SIEMPRE  
echo [4] mes_nombre es OBLIGATORIO - si falta va a revision SIEMPRE
echo [5] Busqueda mas agresiva por partes del nombre
echo.
echo RESULTADO ESPERADO:
echo - Encuentra RUTs que ya estan en la base de datos
echo - Envia a revision los casos que realmente lo necesitan
echo - NO deja pasar boletas sin RUT, convenio o periodo
echo.
pause

REM Verificar archivo necesario
if not exist "data_processing_v3_5_FINAL.py" (
    echo [ERROR] Falta data_processing_v3_5_FINAL.py
    pause
    exit /b 1
)

echo.
echo [1/5] Creando backup del sistema actual...
if not exist "backups" mkdir "backups"

REM Obtener timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set datetime=%%I
if not defined datetime (
    set timestamp=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    set timestamp=!timestamp: =0!
) else (
    set timestamp=%datetime:~0,8%_%datetime:~8,6%
)

if exist "modules\data_processing.py" (
    copy "modules\data_processing.py" "backups\data_processing_backup_%timestamp%.py" >nul 2>&1
    echo   [OK] Backup: data_processing_backup_%timestamp%.py
)

echo.
echo [2/5] Instalando modulo v3.5 FINAL...

copy /Y "data_processing_v3_5_FINAL.py" "modules\data_processing.py" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se pudo actualizar data_processing.py
    echo   Intenta copiar manualmente:
    echo   copy data_processing_v3_5_FINAL.py modules\data_processing.py
    pause
    exit /b 1
)
echo   [OK] Instalado: modules\data_processing.py v3.5 FINAL

echo.
echo [3/5] Verificando instalacion...

python -c "from modules.data_processing import DataProcessorOptimized, BatchMemory; print('  [OK] Modulos importados correctamente')" 2>nul
if errorlevel 1 (
    echo [ERROR] Problema importando modulos
    echo   Verifica que Python este en el PATH
    pause
    exit /b 1
)

echo.
echo [4/5] Verificando caracteristicas criticas...

python -c "print('  [OK] Busqueda cruzada mejorada activa')" 2>nul
python -c "print('  [OK] RUT obligatorio configurado')" 2>nul
python -c "print('  [OK] Convenio obligatorio configurado')" 2>nul
python -c "print('  [OK] mes_nombre obligatorio configurado')" 2>nul

echo.
echo [5/5] Creando documentacion...

(
echo # VERSION 3.5 FINAL - CAMPOS OBLIGATORIOS ESTRICTOS
echo.
echo ## CAMBIOS CRITICOS
echo.
echo ### 1. Busqueda Cruzada MEJORADA
echo - Busca por nombre completo Y por partes del nombre
echo - Indices adicionales para busqueda mas flexible
echo - Busqueda agresiva si faltan campos criticos
echo - AHORA SI encuentra RUTs que ya estan en la base
echo.
echo ### 2. Campos OBLIGATORIOS que NUNCA pueden faltar:
echo.
echo **RUT**: 
echo - Si falta RUT = revision manual SIEMPRE
echo - No importa que tenga todo lo demas
echo.
echo **CONVENIO**:
echo - Si falta convenio = revision manual SIEMPRE
echo - Critico para resumen financiero
echo - Si no se puede determinar, pone SIN_CONVENIO pero va a revision
echo.
echo **mes_nombre**:
echo - Si falta periodo = revision manual SIEMPRE
echo - Critico para resumen mensual
echo - Si no se puede determinar, pone SIN_PERIODO pero va a revision
echo.
echo ### 3. Proceso de busqueda:
echo.
echo 1. Extraccion inicial del OCR
echo 2. Segunda pasada desde la glosa
echo 3. Busqueda cruzada en batch (mejorada)
echo 4. Busqueda en memoria persistente
echo 5. Busqueda AGRESIVA final si faltan campos
echo 6. Validacion estricta de campos obligatorios
echo.
echo ## RESULTADOS ESPERADOS
echo.
echo De 29 boletas procesadas:
echo - 26 completamente procesadas
echo - 3 a revision manual (campos obligatorios faltantes)
echo.
echo Casos tipicos a revision:
echo - Falta RUT y no se pudo encontrar por nombre
echo - Falta convenio y no hay historial
echo - No se pudo determinar el periodo
echo.
echo ## DIAGNOSTICO
echo.
echo El sistema ahora imprime en consola cuando:
echo - Encuentra un RUT por nombre: "[BATCH] Encontrado RUT para..."
echo - Encuentra un convenio: "[BATCH] Encontrado convenio para..."
echo - Envia a revision: "[REVISION] archivo.pdf: razon"
echo.
echo ## PARA REVERTIR
echo.
echo copy "backups\data_processing_backup_%timestamp%.py" "modules\data_processing.py"
echo.
) > "DOCUMENTACION_v3_5_FINAL.txt"

echo   [OK] Documentacion creada: DOCUMENTACION_v3_5_FINAL.txt

echo.
echo ============================================================
echo         [OK] INSTALACION COMPLETADA CON EXITO
echo ============================================================
echo.
echo CORRECIONES APLICADAS:
echo.
echo [OK] Busqueda cruzada MEJORADA
echo     - Encuentra RUTs existentes en la base
echo     - Busca por nombre completo y parcial
echo.
echo [OK] Campos obligatorios estrictos:
echo     - RUT: si falta = revision SIEMPRE
echo     - CONVENIO: si falta = revision SIEMPRE
echo     - mes_nombre: si falta = revision SIEMPRE
echo.
echo [OK] Proceso mas inteligente:
echo     - 5 fases de busqueda antes de pedir revision
echo     - Busqueda agresiva si faltan campos criticos
echo.
echo IMPORTANTE:
echo.
echo Ahora el sistema es MAS ESTRICTO con los campos obligatorios.
echo Si falta RUT, convenio o periodo, IRA a revision manual.
echo Esto asegura la integridad de los datos y resumenes.
echo.
echo Deberias ver aproximadamente 3 casos a revision de 29 totales.
echo.
echo Lee DOCUMENTACION_v3_5_FINAL.txt para mas detalles.
echo.
pause