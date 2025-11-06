@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul
title Instalación de Correcciones v3.3 - Sistema Boletas OCR

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║  CORRECCIONES v3.3 - Revisión Estricta ^& Mejor Memoria   ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo Esta actualización corrige:
echo   ✓ Criterio de revisión MÁS ESTRICTO
echo      - Revisa si falta: nombre O RUT O monto O convenio
echo   ✓ Mejor extracción de horas (más patrones)
echo   ✓ Búsqueda en registros del lote actual
echo   ✓ Periodo solo con mes (YYYY-MM)
echo.
pause

REM Verificar archivo corregido
if not exist "data_processing_fixed.py" (
    echo ❌ ERROR: Falta data_processing_fixed.py
    pause
    exit /b 1
)

echo [1/4] Creando backups...
if not exist "backups" mkdir "backups"

for /f "tokens=1-6 delims=.:/ " %%a in ("%date% %time%") do (
    set "timestamp=%%c%%b%%a_%%d%%e%%f"
)

if exist "modules\data_processing.py" (
    copy "modules\data_processing.py" "backups\data_processing_backup_%timestamp%.py" >nul
    echo   ✓ Backup: data_processing.py guardado
)

echo.
echo [2/4] Instalando versión corregida...

copy /Y "data_processing_fixed.py" "modules\data_processing.py" >nul
if errorlevel 1 (
    echo ❌ ERROR: No se pudo actualizar data_processing.py
    pause
    exit /b 1
)
echo   ✓ Instalado: modules\data_processing.py (v3.3)

echo.
echo [3/4] Verificando instalación...

python -c "from modules.data_processing import DataProcessorOptimized; print('✓ DataProcessor OK')"
if errorlevel 1 (
    echo ❌ ERROR: Problema con data_processing.py
    pause
    exit /b 1
)

python -c "from modules.memory import Memory; m=Memory(); print('✓ Memory OK'); stats=m.get_stats(); print(f'  - RUTs: {stats[\"total_ruts\"]}'); print(f'  - Nombres: {stats.get(\"total_nombres\", 0)}')"
if errorlevel 1 (
    echo ❌ ERROR: Problema con memory.py
    pause
    exit /b 1
)

echo.
echo [4/4] Creando documentación...

(
echo # CORRECCIONES v3.3 - Revisión Estricta ^& Mejor Memoria
echo.
echo ## Cambios Implementados
echo.
echo ### 1. Criterio de Revisión MÁS ESTRICTO
echo.
echo **ANTES (v3.2):** Era demasiado permisivo. No pedía revisión si:
echo - Tenía RUT + monto (aunque faltara nombre)
echo - Tenía nombre + monto (aunque faltara RUT)
echo.
echo **AHORA (v3.3):** Pide revisión si falta CUALQUIERA de:
echo - **Nombre**
echo - **RUT**
echo - **Monto**
echo - **Convenio**
echo.
echo O si la confianza es ^< 35%%
echo.
echo ### 2. Mejor Extracción de Horas
echo.
echo Nuevos patrones:
echo - "44 horas" / "44 hrs" / "44 h"
echo - "Horas: 44" / "Hrs: 44"
echo - "44 H" (mayúscula)
echo - "horas trabajadas: 44"
echo - "44hrs" (sin espacio)
echo.
echo ### 3. Búsqueda en Lote Actual
echo.
echo Ahora busca información en los registros YA PROCESADOS de esta sesión:
echo.
echo **Ejemplo:**
echo - Boleta 1: "Juan Pérez" con RUT 12.345.678-9
echo - Boleta 2: "Juan Pérez" sin RUT
echo - **Sistema automáticamente completa el RUT de la Boleta 2**
echo.
echo ### 4. Periodo Solo con Mes
echo.
echo - Formato correcto: "2024-02" (año-mes)
echo - No muestra día
echo.
echo ## Resultados Esperados
echo.
echo - **Revisiones:** Aumentarán (más estricto), pero captará TODOS los casos problemáticos
echo - **Autocompletado:** Mejor gracias a búsqueda en lote
echo - **Horas:** Mucho mejor detección
echo.
echo ## Uso
echo.
echo 1. Ejecuta `python main.py` normalmente
echo 2. El sistema ahora pedirá revisión si falta algún campo crítico
echo 3. Usa la memoria del lote para autocompletar datos faltantes
echo.
echo ## Revertir Cambios
echo.
echo Si necesitas volver a la versión anterior:
echo ```batch
echo copy "backups\data_processing_backup_[timestamp].py" "modules\data_processing.py"
echo ```
) > "CORRECCIONES_v3.3_INSTALADAS.md"

echo   ✓ Documentación creada: CORRECCIONES_v3.3_INSTALADAS.md

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║              ✓ INSTALACIÓN COMPLETADA                     ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.
echo 📋 Cambios principales:
echo.
echo   1️⃣  REVISIÓN MÁS ESTRICTA
echo       Ahora pide revisión si falta nombre, RUT, monto o convenio
echo.
echo   2️⃣  MEJOR EXTRACCIÓN DE HORAS
echo       Detecta: "44hrs", "Horas: 44", "44 h", etc.
echo.
echo   3️⃣  BÚSQUEDA EN LOTE ACTUAL
echo       Si una persona sale 2 veces, usa datos de la primera boleta
echo.
echo   4️⃣  PERIODO SOLO CON MES
echo       Formato: "2024-02" (sin día)
echo.
echo 💡 Importante: Verás MÁS revisiones manuales, pero esto es BUENO
echo    porque ahora detecta TODOS los casos problemáticos.
echo.
echo 📄 Lee: CORRECCIONES_v3.3_INSTALADAS.md para más detalles
echo.
pause