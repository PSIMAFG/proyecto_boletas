@echo off
setlocal ENABLEDELAYEDEXPANSION
chcp 65001 >nul
title Instalacion Mejoras v4.1 - Normalizacion RUT + Decreto

echo.
echo ================================================================
echo    MEJORAS v4.1 - Normalizacion RUT + Decreto
echo ================================================================
echo.
echo Esta actualizacion incluye:
echo   - Normalizacion automatica RUT + Decreto para Monto/Horas
echo   - Propagacion tras revision manual
echo   - Aprendizaje acumulativo en memoria
echo   - Fix error monto_num en reportes
echo.
echo Reduccion esperada: 50 a 10-15 boletas a revisar
echo.
pause

REM ========== VERIFICACION DE ARCHIVOS ==========
echo [1/6] Verificando archivos...

if not exist "modules\memory.py" (
    echo ERROR: No existe modules\memory.py
    pause
    exit /b 1
)

if not exist "modules\data_processing.py" (
    echo ERROR: No existe modules\data_processing.py
    pause
    exit /b 1
)

if not exist "main.py" (
    echo ERROR: No existe main.py
    pause
    exit /b 1
)

if not exist "modules\report_generator.py" (
    echo ERROR: No existe modules\report_generator.py
    pause
    exit /b 1
)

echo   [OK] Archivos encontrados

REM ========== CREAR BACKUPS ==========
echo.
echo [2/6] Creando backups...

if not exist "backups_v4_1" mkdir "backups_v4_1"

for /f "tokens=1-6 delims=.:/ " %%a in ("%date% %time%") do (
    set "timestamp=%%c%%b%%a_%%d%%e%%f"
)

copy "modules\memory.py" "backups_v4_1\memory_backup_%timestamp%.py" >nul
copy "modules\data_processing.py" "backups_v4_1\data_processing_backup_%timestamp%.py" >nul
copy "main.py" "backups_v4_1\main_backup_%timestamp%.py" >nul
copy "modules\report_generator.py" "backups_v4_1\report_generator_backup_%timestamp%.py" >nul

echo   [OK] Backups creados en: backups_v4_1\

REM ========== INSTALAR MEMORY.PY ==========
echo.
echo [3/6] Instalando memory.py v4.1...

if not exist "memory_v4_1.py" (
    echo ERROR: No se encuentra memory_v4_1.py
    echo    Descarga los archivos v4.1 primero
    pause
    exit /b 1
)

copy /Y "memory_v4_1.py" "modules\memory.py" >nul
if errorlevel 1 (
    echo ERROR: No se pudo instalar memory.py
    pause
    exit /b 1
)

echo   [OK] memory.py actualizado

REM ========== CREAR ARCHIVO CON SNIPPETS ==========
echo.
echo [4/6] Generando snippets para integracion manual...

(
echo # ================================================================
echo # SNIPPET 1: Agregar a BatchMemory en data_processing.py
echo # Ubicacion: Despues del metodo _normalize_name
echo # ================================================================
echo.
echo     def normalize_by_rut_decreto^(self, registros: List[Dict], log_callback=None^) -^> List[Dict]:
echo         """Normaliza monto/horas por RUT + Decreto en el batch actual"""
echo         if not registros:
echo             return registros
echo.        
echo         # Construir mapa RUT + Decreto -^> Monto/Horas
echo         rut_decreto_map = {}
echo         for r in registros:
echo             rut = r.get^('rut', ''^).strip^(^)
echo             decreto = r.get^('decreto_alcaldicio', ''^).strip^(^)
echo             monto = r.get^('monto', ''^).strip^(^)
echo             horas = r.get^('horas', ''^).strip^(^)
echo.            
echo             if rut and decreto and ^(monto or horas^):
echo                 key = f"{rut}_{decreto}"
echo                 if key not in rut_decreto_map:
echo                     rut_decreto_map[key] = {'monto': monto, 'horas': horas, 'count': 1}
echo                 else:
echo                     rut_decreto_map[key]['count'] += 1
echo.        
echo         # Aplicar normalizacion
echo         aplicados = 0
echo         for r in registros:
echo             rut = r.get^('rut', ''^).strip^(^)
echo             decreto = r.get^('decreto_alcaldicio', ''^).strip^(^)
echo.            
echo             if rut and decreto:
echo                 key = f"{rut}_{decreto}"
echo                 if key in rut_decreto_map:
echo                     pattern = rut_decreto_map[key]
echo.                    
echo                     if pattern.get^('monto'^) and not r.get^('monto'^):
echo                         r['monto'] = pattern['monto']
echo                         r['monto_confidence'] = 0.90
echo                         r['monto_origen'] = 'batch_rut_decreto'
echo                         aplicados += 1
echo.                    
echo                     if pattern.get^('horas'^) and not r.get^('horas'^):
echo                         r['horas'] = pattern['horas']
echo                         r['horas_origen'] = 'batch_rut_decreto'
echo.        
echo         if log_callback and aplicados ^> 0:
echo             log_callback^(f"   [OK] {aplicados} campos normalizados por RUT+Decreto", "success"^)
echo.        
echo         return registros
echo.
echo.
echo # ================================================================
echo # SNIPPET 2: Modificar IntelligentBatchProcessor.post_process_batch
echo # Ubicacion: Despues de _normalize_decreto_convenio
echo # ================================================================
echo.
echo         # Paso 1.5: Normalizar por RUT + Decreto
echo         registros = self.batch_memory.normalize_by_rut_decreto^(registros, log_callback^)
echo.
echo         # Paso 1.6: Aplicar patrones conocidos de memoria
echo         registros = self._apply_known_patterns^(registros, log_callback^)
echo.
echo.
echo # ================================================================
echo # SNIPPET 3: Agregar metodo a IntelligentBatchProcessor
echo # Ubicacion: Despues de _needs_review_post_process
echo # ================================================================
echo.
echo     def _apply_known_patterns^(self, registros: List[Dict], log_callback=None^) -^> List[Dict]:
echo         """Aplica patrones conocidos RUT + Decreto desde memoria persistente"""
echo         aplicados = 0
echo.        
echo         for r in registros:
echo             rut = r.get^('rut', ''^).strip^(^)
echo             decreto = r.get^('decreto_alcaldicio', ''^).strip^(^)
echo.            
echo             if rut and decreto:
echo                 known_payment = self.memory.get_payment_by_rut_decreto^(rut, decreto^)
echo.                
echo                 if known_payment:
echo                     if known_payment.get^("monto"^) and not r.get^('monto'^):
echo                         r['monto'] = known_payment["monto"]
echo                         r['monto_confidence'] = 0.95
echo                         r['monto_origen'] = 'memoria_rut_decreto'
echo                         aplicados += 1
echo.                    
echo                     if known_payment.get^("horas"^) and not r.get^('horas'^):
echo                         r['horas'] = known_payment["horas"]
echo                         r['horas_origen'] = 'memoria_rut_decreto'
echo.        
echo         if log_callback and aplicados ^> 0:
echo             log_callback^(f"   [OK] {aplicados} pagos aplicados desde memoria RUT+Decreto", "success"^)
echo.        
echo         return registros
echo.
echo.
echo # ================================================================
echo # SNIPPET 4: Modificar main.py - _manual_review_process_incremental
echo # Ubicacion: Dentro de "if dialog.result:", despues de reviewed.append
echo # ================================================================
echo.
echo             # NUEVO v4.1: Aprender patron RUT + Decreto
echo             rut = dialog.result.get^('rut', ''^).strip^(^)
echo             decreto = dialog.result.get^('decreto_alcaldicio', ''^).strip^(^)
echo             monto = dialog.result.get^('monto', ''^).strip^(^)
echo             horas = dialog.result.get^('horas', ''^).strip^(^)
echo.            
echo             if rut and decreto:
echo                 # Guardar en memoria persistente
echo                 self.data_processor.memory.learn_payment_pattern^(rut, decreto, monto, horas^)
echo.                
echo                 # PROPAGAR a TODOS los pendientes con mismo RUT + Decreto
echo                 actualizados = 0
echo                 for pending in pendientes:
echo                     if ^(pending.get^('rut'^) == rut and 
echo                         pending.get^('decreto_alcaldicio'^) == decreto^):
echo.                        
echo                         if monto and pending.get^('monto'^) != monto:
echo                             pending['monto'] = monto
echo                             pending['monto_confidence'] = 0.95
echo                             pending['monto_origen'] = 'revision_manual_propagada'
echo                             actualizados += 1
echo.                        
echo                         if horas and pending.get^('horas'^) != horas:
echo                             pending['horas'] = horas
echo                             pending['horas_origen'] = 'revision_manual_propagada'
echo                             actualizados += 1
echo.                
echo                 if actualizados ^> 0:
echo                     boletas_afectadas = len^([p for p in pendientes if p.get^('rut'^)==rut and p.get^('decreto_alcaldicio'^)==decreto]^)
echo                     self.log^(f"   [INFO] Patron aplicado a {actualizados} campos en {boletas_afectadas} boletas similares", "success"^)
echo.
echo.
echo # ================================================================
echo # SNIPPET 5: Fix monto_num en report_generator.py
echo # Ubicacion: En _create_main_dataframe, ANTES del return df
echo # ================================================================
echo.
echo         # Asegurar que monto_num existe SIEMPRE ^(fix error reportes individuales^)
echo         if 'monto_num' not in df.columns or df['monto_num'].isna^(^).all^(^):
echo             df["monto_num"] = pd.to_numeric^(df.get^("monto", ""^), errors="coerce"^).fillna^(0^)
echo.        
echo         return df
) > "SNIPPETS_V4_1_MANUAL.txt"

echo   [OK] Snippets generados: SNIPPETS_V4_1_MANUAL.txt

REM ========== VERIFICAR INSTALACION ==========
echo.
echo [5/6] Verificando instalacion de memory.py...

python -c "from modules.memory import Memory; m=Memory(); stats=m.get_stats(); print(f'[OK] Memory v4.1 OK - {stats.get(\"patrones_pago\", 0)} patrones de pago')"
if errorlevel 1 (
    echo ERROR: Problema con memory.py
    pause
    exit /b 1
)

REM ========== MANUAL ==========
echo.
echo [6/6] Siguiente paso: INTEGRACION MANUAL
echo.
echo ================================================================
echo              ACCION MANUAL REQUERIDA
echo ================================================================
echo.
echo memory.py esta instalado [OK]
echo.
echo AHORA debes editar manualmente 3 archivos:
echo.
echo   1. modules\data_processing.py
echo      - Agregar metodo normalize_by_rut_decreto a BatchMemory
echo      - Agregar metodo _apply_known_patterns a IntelligentBatchProcessor
echo      - Modificar post_process_batch
echo.
echo   2. main.py
echo      - Modificar _manual_review_process_incremental
echo.
echo   3. modules\report_generator.py
echo      - Agregar fix monto_num en _create_main_dataframe
echo.
echo Abre el archivo: SNIPPETS_V4_1_MANUAL.txt
echo Contiene todos los codigos a copiar/pegar
echo.
echo Tambien puedes consultar: INSTALACION_V4_1.md
echo Para instrucciones paso a paso detalladas
echo.
pause

echo.
echo ================================================================
echo          INSTALACION PARCIAL COMPLETADA
echo ================================================================
echo.
echo [OK] memory.py instalado y verificado
echo [OK] Backups creados
echo [OK] Snippets generados
echo.
echo [PENDIENTE] Falta completar edicion manual de:
echo   - data_processing.py
echo   - main.py
echo   - report_generator.py
echo.
echo Consulta SNIPPETS_V4_1_MANUAL.txt para el codigo exacto
echo.
pause