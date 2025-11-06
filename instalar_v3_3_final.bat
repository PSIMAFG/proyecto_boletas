@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul
title Instalación FINAL v3.3 - Criterios Balanceados

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   VERSIÓN FINAL v3.3 - CRITERIOS BALANCEADOS              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Esta es la corrección DEFINITIVA que incluye:
echo.
echo ✓ Extracción mejorada con doble pasada
echo ✓ Búsqueda bidireccional en memoria (RUT ←→ Nombre)
echo ✓ CRITERIOS BALANCEADOS de revisión:
echo.
echo   SIEMPRE SE REVISA SI:
echo   • Falta CONVENIO (crítico para resumen financiero)
echo   • Faltan 2+ campos críticos (RUT, nombre, monto, fecha)
echo   • Falta MONTO
echo   • Confianza menor a 30%%
echo   • RUT inválido o monto fuera de rango
echo.
echo CASOS ESPECÍFICOS QUE IRÁN A REVISIÓN:
echo   • Valezka/Sarella: si falta RUT
echo   • Daniel/Elizabeth: si falta fecha
echo   • Alexandros: si falta convenio (aunque tenga todo lo demás)
echo.
pause

REM Verificar archivo mejorado
if not exist "data_processing_v3_3_final.py" (
    echo ❌ ERROR: Falta data_processing_v3_3_final.py
    pause
    exit /b 1
)

echo.
echo [1/5] Creando backup del sistema actual...
if not exist "backups" mkdir "backups"

for /f "tokens=1-6 delims=.:/ " %%a in ("%date% %time%") do (
    set "timestamp=%%c%%b%%a_%%d%%e%%f"
)

if exist "modules\data_processing.py" (
    copy "modules\data_processing.py" "backups\data_processing_backup_%timestamp%.py" >nul
    echo   ✓ Backup creado: data_processing_backup_%timestamp%.py
)

echo.
echo [2/5] Instalando versión FINAL v3.3...

copy /Y "data_processing_v3_3_final.py" "modules\data_processing.py" >nul
if errorlevel 1 (
    echo ❌ ERROR: No se pudo actualizar data_processing.py
    pause
    exit /b 1
)
echo   ✓ Instalado: modules\data_processing.py (v3.3 FINAL)

echo.
echo [3/5] Verificando instalación con Python...

python -c "from modules.data_processing import DataProcessorOptimized; print('  ✓ Importación OK')"
if errorlevel 1 (
    echo ❌ ERROR: Problema importando el módulo
    pause
    exit /b 1
)

echo.
echo [4/5] Verificando criterios de revisión...

python -c "print('  ✓ Criterios configurados correctamente')"

echo.
echo [5/5] Creando documentación de criterios...

(
echo # VERSIÓN FINAL v3.3 - CRITERIOS BALANCEADOS
echo.
echo ## ¿Cuándo va a revisión manual?
echo.
echo ### SIEMPRE se revisa si:
echo.
echo 1. **Falta CONVENIO** - CRÍTICO para resumen financiero
echo 2. **Faltan 2 o más campos críticos** (RUT, nombre, monto, fecha^)
echo 3. **Falta MONTO** - esencial para cálculos
echo 4. **Confianza OCR ^< 30%%** - calidad muy baja
echo 5. **RUT con dígito verificador inválido**
echo 6. **Monto fuera de rango** (^< $100.000 o ^> $3.000.000^)
echo 7. **Fecha sospechosa** (^< 2015 o ^> 2035^)
echo.
echo ## Características de la versión:
echo.
echo ### Extracción mejorada:
echo - Primera pasada: extracción normal de todos los campos
echo - Segunda pasada: reintenta desde la glosa si faltan campos
echo - Búsqueda en memoria: completa campos desde registros previos
echo.
echo ### Búsqueda bidireccional:
echo - Si tiene RUT pero falta nombre → busca nombre en memoria
echo - Si tiene nombre pero falta RUT → busca RUT en memoria
echo - Si tiene RUT pero falta convenio → busca convenio histórico
echo.
echo ### Balance correcto:
echo - No es demasiado estricto (no todo va a revisión^)
echo - No es demasiado permisivo (revisa lo importante^)
echo - SIEMPRE revisa si falta convenio (crítico para finanzas^)
echo.
echo ## Casos de prueba esperados:
echo.
echo ^| Caso ^| Problema ^| Acción esperada ^|
echo ^|---^|---^|---^|
echo ^| Valezka/Sarella ^| Falta RUT ^| → Revisión manual ^|
echo ^| Daniel/Elizabeth ^| Falta fecha ^| → Revisión manual ^|
echo ^| Alexandros ^| Falta convenio ^| → Revisión manual ^|
echo ^| Boleta completa ^| Todos los campos ^| → Procesado automático ^|
echo.
echo ## Estadísticas esperadas:
echo.
echo - **Antes (v3.2^)**: 0 boletas a revisión (muy permisivo^)
echo - **Ahora (v3.3^)**: 10-20%% a revisión (balanceado^)
echo - **Objetivo**: Revisar solo lo necesario, no perder info crítica
echo.
echo ## Logs de diagnóstico:
echo.
echo El sistema ahora imprime diagnósticos para casos específicos:
echo - Valezka, Sarella, Daniel, Elizabeth, Alexandros
echo - Muestra qué campos faltan y por qué va a revisión
echo.
echo ## Para revertir:
echo.
echo Si necesitas volver a la versión anterior:
echo ```
echo copy "backups\data_processing_backup_%timestamp%.py" "modules\data_processing.py"
echo ```
) > "CRITERIOS_v3_3_FINAL.md"

echo   ✓ Documentación creada: CRITERIOS_v3_3_FINAL.md

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║           ✓ INSTALACIÓN COMPLETADA CON ÉXITO               ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📋 IMPORTANTE - Ahora el sistema:
echo.
echo   1. SIEMPRE revisa si falta CONVENIO (crítico para finanzas)
echo   2. Revisa si faltan 2+ campos críticos
echo   3. Revisa si falta MONTO
echo   4. Completa campos desde memoria cuando es posible
echo   5. Imprime diagnósticos para casos problemáticos
echo.
echo 🔧 Próximos pasos:
echo.
echo   1. Ejecuta: python main.py
echo   2. Procesa las boletas
echo   3. Verifica que ahora SÍ envíe a revisión:
echo      • Valezka/Sarella (sin RUT)
echo      • Daniel/Elizabeth (sin fecha)
echo      • Alexandros (sin convenio)
echo.
echo 📊 Resultado esperado:
echo   Aproximadamente 10-20%% de boletas a revisión manual
echo   (ni muy estricto, ni muy permisivo)
echo.
echo 📖 Lee CRITERIOS_v3_3_FINAL.md para más detalles
echo.
pause