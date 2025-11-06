# Parche para main.py - Integración v3.4 con BatchMemory
# 
# INSTRUCCIONES:
# 1. Hacer backup de main.py
# 2. Reemplazar la sección process_files_thread con este código
# 3. Agregar opción para reportes por profesional en la GUI

"""
Este código reemplaza el método process_files_thread del main.py
para integrar BatchMemory y búsqueda cruzada antes de revisión manual
"""

def process_files_thread_v34(self):
    """Thread principal de procesamiento con BatchMemory v3.4"""
    try:
        from modules.data_processing import DataProcessorOptimized, BatchMemory
        
        input_dir = Path(self.root_dir.get())
        files = list(iter_files(input_dir))
        total = len(files)
        
        if total == 0:
            self.log("No se encontraron archivos", "warning")
            return
        
        self.log(f"Encontrados {total} archivo(s)", "info")
        
        # Crear BatchMemory compartida para búsqueda cruzada
        batch_memory = BatchMemory()
        
        # PRIMERA PASADA: Procesar todos los archivos
        self.log("=" * 50, "info")
        self.log("FASE 1: Extraccion y procesamiento inicial", "info")
        self.log("=" * 50, "info")
        
        all_results = []
        initial_review_queue = []
        errors = []
        
        # Crear procesador con BatchMemory
        processor = DataProcessorOptimized(batch_memory=batch_memory)
        
        # Procesar archivos secuencialmente para aprovechar BatchMemory
        for i, file_path in enumerate(files, 1):
            if not self.processing:
                break
            
            progress = (i / total) * 50  # Primera mitad de la barra
            self.progress_var.set(progress)
            self.progress_label.config(text=f"Procesando {i}/{total}")
            
            try:
                result = processor.process_file(file_path)
                
                if result.get('error'):
                    errors.append(str(file_path))
                    self.log(f"[X] Error: {file_path.name} - {result.get('error')}", "error")
                else:
                    all_results.append(result)
                    
                    # Log informativo
                    if result.get('needs_review'):
                        razon = result.get('revision_reason', 'Sin especificar')
                        self.log(f"[?] {file_path.name} - A revision: {razon}", "warning")
                    else:
                        quality = result.get('quality_score', 0)
                        self.log(f"[OK] {file_path.name} (Q:{quality:.0%})", "success")
                        
            except Exception as e:
                errors.append(str(file_path))
                self.log(f"[X] Error: {file_path.name} - {e}", "error")
            
            self.update_idletasks()
        
        # SEGUNDA PASADA: Búsqueda cruzada en batch
        self.log("=" * 50, "info")
        self.log("FASE 2: Busqueda cruzada y autocompletado", "info")
        self.log("=" * 50, "info")
        
        mejorados = 0
        final_results = []
        final_review_queue = []
        
        for i, result in enumerate(all_results):
            progress = 50 + (i / len(all_results)) * 30  # Siguiente 30% de la barra
            self.progress_var.set(progress)
            self.progress_label.config(text=f"Optimizando {i+1}/{len(all_results)}")
            
            mejoras = []
            
            # Buscar datos faltantes en otros registros del batch
            rut = result.get('rut', '').strip()
            nombre = result.get('nombre', '').strip()
            convenio = result.get('convenio', '').strip()
            
            # Si falta RUT pero tiene nombre, buscar en batch
            if nombre and not rut:
                rut_encontrado = batch_memory.find_rut_by_nombre(nombre)
                if rut_encontrado:
                    result['rut'] = rut_encontrado
                    result['rut_confidence'] = 0.85
                    result['rut_origen'] = 'batch_cross_reference'
                    mejoras.append(f"RUT encontrado: {rut_encontrado}")
            
            # Si falta nombre pero tiene RUT, buscar en batch
            if rut and not nombre:
                nombre_encontrado = batch_memory.find_nombre_by_rut(rut)
                if nombre_encontrado:
                    result['nombre'] = nombre_encontrado
                    result['nombre_confidence'] = 0.85
                    result['nombre_origen'] = 'batch_cross_reference'
                    mejoras.append(f"Nombre encontrado: {nombre_encontrado}")
            
            # Si falta convenio pero tiene RUT, buscar en batch
            if rut and not convenio:
                convenio_encontrado = batch_memory.find_convenio_by_rut(rut)
                if convenio_encontrado:
                    result['convenio'] = convenio_encontrado
                    result['convenio_confidence'] = 0.75
                    result['convenio_origen'] = 'batch_cross_reference'
                    mejoras.append(f"Convenio encontrado: {convenio_encontrado}")
            
            # Re-evaluar si necesita revisión después de las mejoras
            if mejoras:
                mejorados += 1
                archivo_nombre = Path(result['archivo']).name
                self.log(f"[+] Mejorado {archivo_nombre}: {', '.join(mejoras)}", "success")
                
                # Re-calcular necesidad de revisión con los datos nuevos
                result['needs_review'] = processor._needs_review_v34(
                    result, 
                    result.get('confianza', 0.5)
                )
            
            # Clasificar resultado final
            if result.get('needs_review'):
                final_review_queue.append(result)
            else:
                final_results.append(result)
            
            self.update_idletasks()
        
        self.log(f"Registros mejorados por busqueda cruzada: {mejorados}", "info")
        
        # FASE 3: Revisión manual (si está habilitada)
        if self.var_manual_review.get() and final_review_queue:
            self.log("=" * 50, "info")
            self.log(f"FASE 3: Revision manual - {len(final_review_queue)} boletas", "info")
            self.log("=" * 50, "info")
            
            # Mostrar razones de revisión
            razones_count = {}
            for item in final_review_queue:
                razon = item.get('revision_reason', 'Sin especificar')
                razones_count[razon] = razones_count.get(razon, 0) + 1
            
            self.log("Razones de revision:", "info")
            for razon, count in razones_count.items():
                self.log(f"  - {razon}: {count} casos", "info")
            
            reviewed = self._manual_review_process(final_review_queue)
            final_results.extend(reviewed)
            
            # Actualizar barra de progreso
            self.progress_var.set(90)
            self.progress_label.config(text="Generando Excel...")
        else:
            final_results.extend(final_review_queue)
        
        # FASE 4: Generar Excel con reportes mejorados
        if final_results:
            self._generate_excel_v34(final_results)
        
        # FASE 5: Mostrar resumen
        self._show_summary_v34(final_results, errors, total, final_review_queue)
        
        self.progress_var.set(100)
        self.progress_label.config(text="Completado")
        
    except Exception as e:
        self.log(f"Error critico: {e}", "error")
        self.log(traceback.format_exc(), "error")
    finally:
        self.processing = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.progress_var.set(100)

def _generate_excel_v34(self, results):
    """Genera el archivo Excel con reportes por convenio Y por profesional"""
    try:
        from modules.report_generator import ReportGenerator
        
        output_file = Path(self.out_file.get())
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.log("Generando Excel con reportes mejorados...", "info")
        
        # Crear generador de reportes
        report_gen = ReportGenerator()
        
        # Generar con AMBOS tipos de reportes
        generate_professional = getattr(self, 'var_professional_reports', tk.BooleanVar(value=True)).get()
        
        tmp_file = output_file.with_suffix(".tmp.xlsx")
        df = report_gen.create_excel_with_reports(
            results,
            str(tmp_file),
            generate_reports=self.var_generate_reports.get(),
            generate_professional_reports=generate_professional  # NUEVO
        )
        
        # Reemplazo atómico
        try:
            os.replace(tmp_file, output_file)
            self.log(f"[OK] Excel generado: {output_file}", "success")
            
            # Información sobre hojas creadas
            convenios_unicos = len(set(r.get('convenio', '') for r in results if r.get('convenio')))
            profesionales_unicos = len(set(r.get('rut', '') for r in results if r.get('rut')))
            
            self.log(f"  - Hoja principal: Base de Datos", "info")
            self.log(f"  - Hojas por convenio: {convenios_unicos}", "info")
            self.log(f"  - Hojas por profesional: {profesionales_unicos}", "info")
            self.log(f"  - Hoja de resumen general", "info")
            
        except PermissionError:
            alt = output_file.with_name(
                f"{output_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{output_file.suffix}"
            )
            os.replace(tmp_file, alt)
            self.log(f"[!] Archivo destino en uso. Guardado como: {alt}", "warning")
        
        self.log(f"  Total registros: {len(df)}", "info")
        
        if output_file.exists():
            if messagebox.askyesno("Completado", "¿Abrir el archivo Excel?"):
                try:
                    os.startfile(str(output_file))
                except Exception:
                    pass
                    
    except Exception as e:
        self.log(f"Error generando Excel: {e}", "error")
        try:
            if 'tmp_file' in locals() and Path(tmp_file).exists():
                Path(tmp_file).unlink(missing_ok=True)
        except Exception:
            pass

def _show_summary_v34(self, results, errors, total, review_queue):
    """Muestra resumen final mejorado"""
    self.log("=" * 50, "info")
    self.log("PROCESAMIENTO COMPLETADO", "success")
    self.log("=" * 50, "info")
    
    processed = len(results)
    failed = len(errors)
    reviewed_manual = len(review_queue)
    success_rate = (processed / total * 100) if total > 0 else 0
    
    self.log(f"Total archivos: {total}", "info")
    self.log(f"Procesados exitosamente: {processed} ({success_rate:.1f}%)", "success")
    self.log(f"Enviados a revision manual: {reviewed_manual}", "warning" if reviewed_manual > 0 else "info")
    self.log(f"Con errores: {failed}", "error" if failed > 0 else "info")
    
    if results:
        avg_quality = sum(r.get('quality_score', 0) for r in results) / len(results)
        self.log(f"Calidad promedio: {avg_quality:.1%}", "info")
        
        # Estadísticas de campos completados
        con_rut = sum(1 for r in results if r.get('rut'))
        con_nombre = sum(1 for r in results if r.get('nombre'))
        con_convenio = sum(1 for r in results if r.get('convenio'))
        con_mes = sum(1 for r in results if r.get('mes_nombre') and r.get('mes_nombre') != 'Sin Periodo')
        
        self.log("Completitud de campos:", "info")
        self.log(f"  - Con RUT: {con_rut}/{processed} ({con_rut/processed*100:.1f}%)", "info")
        self.log(f"  - Con nombre: {con_nombre}/{processed} ({con_nombre/processed*100:.1f}%)", "info")
        self.log(f"  - Con convenio: {con_convenio}/{processed} ({con_convenio/processed*100:.1f}%)", "info")
        self.log(f"  - Con periodo: {con_mes}/{processed} ({con_mes/processed*100:.1f}%)", "info")
    
    # Guardar memoria
    if processed > 0:
        try:
            # Nota: La memoria ya se guarda en cada process_file
            stats = self.data_processor.memory.get_stats()
            self.log(f"Memoria actualizada: {stats['total_ruts']} RUTs conocidos", "info")
        except Exception as e:
            self.log(f"Error guardando memoria: {e}", "warning")

# AGREGAR CHECKBOX EN LA GUI para reportes por profesional
# En el método create_widgets de BoletasApp, después de var_generate_reports:

"""
# En create_widgets(), después de la línea que crea var_generate_reports:

self.var_professional_reports = tk.BooleanVar(value=True)
ttk.Checkbutton(options_frame, text="[NUEVO] Generar reportes por profesional (una hoja por persona)",
               variable=self.var_professional_reports).pack(anchor="w")
"""
