# main.py (Versión 4.0 FINAL - Post-procesamiento Inteligente)
"""
Aplicación principal v4.0 FINAL con:
- Post-procesamiento después de OCR completo
- Revisión incremental automática
- Generación de reportes individuales
- Flujo optimizado en 4 fases
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image, ImageTk
import sys
import os
import json
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from config import *
from modules.utils import *
from modules.data_processing import DataProcessorOptimized, BatchMemory, IntelligentBatchProcessor
from modules.report_generator import ReportGenerator


class ImprovedReviewDialog(tk.Toplevel):
    """Diálogo mejorado de revisión manual"""
    
    def __init__(self, master, row: dict):
        super().__init__(master)
        self.title(f"Revisión: {Path(row.get('archivo', '')).name}")
        self.geometry("1200x800")
        
        self.row = row.copy()
        self.result = None
        
        # Frame principal
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Panel izquierdo - Preview
        left_panel = ttk.LabelFrame(main_frame, text="Vista Previa", padding=5)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self._create_preview(left_panel)
        
        # Panel derecho - Campos
        right_panel = ttk.LabelFrame(main_frame, text="Datos de la Boleta", padding=5)
        right_panel.pack(side="left", fill="both", expand=False)
        
        self._create_fields(right_panel)
        
        self.grab_set()
        self.transient(master)
    
    def _create_preview(self, parent):
        """Crea el panel de preview"""
        # Información del archivo
        info_text = f"Archivo: {Path(self.row.get('archivo', '')).name}\n"
        info_text += f"Confianza OCR: {self.row.get('confianza', 0):.1%}\n"
        info_text += f"Razón: {self.row.get('revision_reason', 'N/A')}"
        
        ttk.Label(parent, text=info_text, justify="left").pack(anchor="w", pady=5)
        
        # Canvas para imagen
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg='white')
        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
        
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Cargar imagen de preview
        preview_path = self.row.get("preview_path", "")
        if preview_path and Path(preview_path).exists():
            try:
                pil_img = Image.open(preview_path)
                pil_img.thumbnail((900, 1000), Image.Resampling.LANCZOS)
                self.tk_image = ImageTk.PhotoImage(pil_img)
                canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
                canvas.config(scrollregion=canvas.bbox("all"))
            except Exception:
                canvas.create_text(10, 10, anchor="nw", text="Error cargando imagen")
        else:
            canvas.create_text(10, 10, anchor="nw", text="Sin preview disponible")
        
        # Botones
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="📄 Abrir original", 
                  command=self._open_original).pack(side="left", padx=2)
    
    def _create_fields(self, parent):
        """Crea los campos editables"""
        # Crear variables
        self.vars = {}
        
        campos = [
            ("Nombre", "nombre", "entry"),
            ("RUT", "rut", "entry"),
            ("Nº Boleta", "nro_boleta", "entry"),
            ("Fecha (YYYY-MM-DD)", "fecha_documento", "entry"),
            ("Monto Bruto", "monto", "entry"),
            ("Convenio", "convenio", "combo"),
            ("Horas", "horas", "entry"),
            ("Tipo", "tipo", "combo"),
            ("Decreto", "decreto_alcaldicio", "entry"),
            ("Glosa", "glosa", "text"),
        ]
        
        for label, field, tipo in campos:
            frame = ttk.Frame(parent)
            frame.pack(fill="x", pady=3)
            
            ttk.Label(frame, text=label, width=20, anchor="w").pack(side="left")
            
            if tipo == "entry":
                var = tk.StringVar(value=self.row.get(field, ""))
                self.vars[field] = var
                ttk.Entry(frame, textvariable=var, width=50).pack(side="left", fill="x", expand=True)
            
            elif tipo == "combo":
                var = tk.StringVar(value=self.row.get(field, ""))
                self.vars[field] = var
                
                if field == "convenio":
                    values = [""] + KNOWN_CONVENIOS
                elif field == "tipo":
                    values = ["", "mensuales", "semanales"]
                else:
                    values = []
                
                ttk.Combobox(frame, textvariable=var, values=values, width=47).pack(side="left", fill="x", expand=True)
            
            elif tipo == "text":
                text_widget = tk.Text(frame, height=4, width=50)
                text_widget.pack(side="left", fill="both", expand=True)
                text_widget.insert("1.0", self.row.get(field, ""))
                self.vars[field] = text_widget
        
        # Información adicional
        if self.row.get('valor_hora_calculado'):
            info = f"\nValor hora calculado: ${self.row['valor_hora_calculado']:,.0f}"
            if self.row.get('monto_fuera_rango'):
                info += "\n⚠️ Monto parece fuera de rango esperado"
            ttk.Label(parent, text=info, foreground="blue").pack(pady=5)
        
        # Botones de acción
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="✓ Guardar", 
                  command=self._on_save).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="⏭ Omitir", 
                  command=self._on_skip).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="✕ Cancelar", 
                  command=self._on_cancel).pack(side="left", padx=2)
    
    def _open_original(self):
        """Abre el archivo original"""
        path = self.row.get("archivo")
        if path and Path(path).exists():
            try:
                os.startfile(path)
            except Exception:
                try:
                    os.system(f"open '{path}'")
                except Exception:
                    os.system(f"xdg-open '{path}'")
    
    def _on_save(self):
        """Guarda los cambios"""
        result = self.row.copy()
        
        for field, var in self.vars.items():
            if isinstance(var, tk.Text):
                result[field] = var.get("1.0", "end").strip()
            else:
                result[field] = var.get().strip()
        
        result['needs_review'] = False
        result['manually_reviewed'] = True
        
        self.result = result
        self.destroy()
    
    def _on_skip(self):
        """Omite este registro"""
        self.result = None
        self.destroy()
    
    def _on_cancel(self):
        """Cancela la revisión"""
        self.result = None
        self.destroy()


class BoletasApp(tk.Tk):
    """Aplicación principal v4.0 FINAL"""
    
    def __init__(self):
        super().__init__()
        self.title("Sistema de Boletas OCR v4.0 FINAL - Post-procesamiento Inteligente")
        self.geometry("1200x800")
        
        # Variables
        self.root_dir = tk.StringVar(value=str(REGISTRO_DIR.resolve()))
        self.out_file = tk.StringVar(value=str((EXPORT_DIR / "boletas_procesadas.xlsx").resolve()))
        self.var_manual_review = tk.BooleanVar(value=True)
        self.var_generate_reports = tk.BooleanVar(value=True)
        self.var_individual_reports = tk.BooleanVar(value=True)
        
        # Procesadores
        self.batch_memory = BatchMemory()
        self.data_processor = DataProcessorOptimized(self.batch_memory)
        self.batch_processor = self.data_processor.batch_processor
        self.report_generator = ReportGenerator()
        
        # Estado
        self.processing = False
        self.thread = None
        
        # Crear interfaz
        self.create_widgets()
        
        # Verificar dependencias
        self.check_dependencies()
    
    def create_widgets(self):
        """Crea la interfaz"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Configuración
        config_frame = ttk.LabelFrame(main_frame, text="Configuración", padding=10)
        config_frame.pack(fill="x", pady=5)
        
        # Carpeta entrada
        row1 = ttk.Frame(config_frame)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="📁 Carpeta entrada:").pack(side="left")
        ttk.Entry(row1, textvariable=self.root_dir, width=60).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(row1, text="Seleccionar", command=self.select_input).pack(side="left")
        
        # Archivo salida
        row2 = ttk.Frame(config_frame)
        row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="📊 Archivo salida:").pack(side="left")
        ttk.Entry(row2, textvariable=self.out_file, width=60).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(row2, text="Guardar como", command=self.select_output).pack(side="left")
        
        # Opciones
        options_frame = ttk.LabelFrame(main_frame, text="Opciones", padding=10)
        options_frame.pack(fill="x", pady=5)
        
        ttk.Checkbutton(options_frame, text="✓ Revisión manual de registros dudosos",
                       variable=self.var_manual_review).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="📊 Generar informes por convenio",
                       variable=self.var_generate_reports).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="👤 Generar reportes individuales por profesional (NUEVO v4.0)",
                       variable=self.var_individual_reports).pack(anchor="w")
        
        # Botones control
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        self.btn_start = ttk.Button(control_frame, text="▶ Iniciar Procesamiento",
                                    command=self.start_processing)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="⏸ Detener",
                                   command=self.stop_processing,
                                   state="disabled")
        self.btn_stop.pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="❌ Salir", command=self.quit).pack(side="right", padx=5)
        
        # Barra de progreso
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x")
        
        self.progress_label = ttk.Label(progress_frame, text="Listo")
        self.progress_label.pack(pady=2)
        
        # Log
        log_frame = ttk.LabelFrame(main_frame, text="Registro", padding=5)
        log_frame.pack(fill="both", expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=20, wrap="word",
                               bg="#1e1e1e", fg="white", font=("Consolas", 9))
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        
        # Tags para colores
        self.log_text.tag_config("info", foreground="white")
        self.log_text.tag_config("success", foreground="#00ff00")
        self.log_text.tag_config("warning", foreground="yellow")
        self.log_text.tag_config("error", foreground="#ff6666")
    
    def log(self, message: str, level: str = "info"):
        """Agrega mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✕"
        }
        
        icon = icons.get(level, "")
        
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {icon} {message}\n", level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update_idletasks()
    
    def check_dependencies(self):
        """Verifica dependencias"""
        self.log("Verificando sistema...", "info")
        
        if detect_tesseract_cmd():
            self.log("Tesseract: OK ✓", "success")
        else:
            self.log("Tesseract: NO ENCONTRADO", "warning")
        
        if detect_poppler_bin():
            self.log("Poppler: OK ✓", "success")
        else:
            self.log("Poppler: No encontrado (opcional)", "info")
        
        self.log("Post-procesamiento v4.0: ACTIVO 🧠", "success")
    
    def select_input(self):
        """Selecciona carpeta de entrada"""
        folder = filedialog.askdirectory(title="Carpeta con boletas")
        if folder:
            self.root_dir.set(folder)
    
    def select_output(self):
        """Selecciona archivo de salida"""
        file = filedialog.asksaveasfilename(
            title="Guardar como",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if file:
            self.out_file.set(file)
    
    def start_processing(self):
        """Inicia el procesamiento"""
        if self.processing:
            return
        
        input_dir = Path(self.root_dir.get())
        if not input_dir.exists():
            messagebox.showerror("Error", "La carpeta no existe")
            return
        
        self.processing = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0)
        
        # Limpiar log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        
        self.log("=" * 60, "info")
        self.log("INICIANDO PROCESAMIENTO v4.0 FINAL", "info")
        self.log("=" * 60, "info")
        self.log(f"Carpeta: {input_dir}", "info")
        self.log(f"Salida: {self.out_file.get()}", "info")
        self.log("", "info")
        
        # Thread de procesamiento
        self.thread = threading.Thread(target=self.process_files_thread, daemon=True)
        self.thread.start()
    
    def stop_processing(self):
        """Detiene el procesamiento"""
        self.processing = False
        self.log("Deteniendo...", "warning")
    
    def process_files_thread(self):
        """Thread principal de procesamiento v4.0"""
        try:
            input_dir = Path(self.root_dir.get())
            files = list(iter_files(input_dir))
            total = len(files)
            
            if total == 0:
                self.log("No se encontraron archivos", "warning")
                return
            
            self.log(f"Encontrados {total} archivo(s)", "info")
            self.log("", "info")
            
            # ========== FASE 1: EXTRACCIÓN OCR (0-50%) ==========
            self.log("=" * 60, "info")
            self.log("FASE 1/4: EXTRACCIÓN OCR", "info")
            self.log("=" * 60, "info")
            
            all_results = []
            errors = []
            
            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(self.data_processor.process_file, f): f for f in files}
                
                completed = 0
                for future in as_completed(futures):
                    if not self.processing:
                        break
                    
                    completed += 1
                    progress = (completed / total) * 50  # 0-50%
                    self.progress_var.set(progress)
                    self.progress_label.config(text=f"OCR: {completed}/{total}")
                    
                    file_path = futures[future]
                    
                    try:
                        result = future.result(timeout=30)
                        
                        if result.get('error'):
                            errors.append(str(file_path))
                            self.log(f"✕ Error: {file_path.name}", "error")
                        else:
                            all_results.append(result)
                            conf = result.get('confianza', 0)
                            self.log(f"✓ Extraído: {file_path.name} (Conf:{conf:.0%})", "success")
                    
                    except Exception as e:
                        errors.append(str(file_path))
                        self.log(f"✕ Error: {file_path.name} - {e}", "error")
                    
                    self.update_idletasks()
            
            if not all_results:
                self.log("No se pudo procesar ningún archivo", "error")
                return
            
            self.log("", "info")
            self.log(f"Fase 1 completada: {len(all_results)} boletas extraídas", "success")
            self.log("", "info")
            
            # ========== FASE 2: POST-PROCESAMIENTO (50-70%) ==========
            self.log("=" * 60, "info")
            self.log("FASE 2/4: POST-PROCESAMIENTO INTELIGENTE 🧠", "info")
            self.log("=" * 60, "info")
            
            self.progress_var.set(50)
            self.progress_label.config(text="Post-procesando...")
            
            completos, para_revision = self.batch_processor.post_process_batch(
                all_results, 
                log_callback=self.log
            )
            
            self.progress_var.set(70)
            self.log("", "info")
            
            # ========== FASE 3: REVISIÓN MANUAL (70-85%) ==========
            if self.var_manual_review.get() and para_revision:
                self.log("=" * 60, "info")
                self.log("FASE 3/4: REVISIÓN MANUAL", "info")
                self.log("=" * 60, "info")
                self.log(f"Boletas para revisar: {len(para_revision)}", "warning")
                self.log("", "info")
                
                reviewed = self._manual_review_process_incremental(para_revision, completos)
                completos.extend(reviewed)
                
                self.progress_var.set(85)
            else:
                self.log("Revisión manual desactivada o sin casos pendientes", "info")
                self.progress_var.set(85)
            
            # ========== FASE 4: GENERACIÓN DE REPORTES (85-100%) ==========
            self.log("", "info")
            self.log("=" * 60, "info")
            self.log("FASE 4/4: GENERACIÓN DE REPORTES", "info")
            self.log("=" * 60, "info")
            
            if completos:
                # Guardar en memoria persistente
                for registro in completos:
                    if registro.get('rut'):
                        self.data_processor.memory.learn(registro)
                self.data_processor.memory.save()
                
                # Calcular quality_score final
                for registro in completos:
                    registro['quality_score'] = self._calculate_final_quality(registro)
                
                # Generar Excel principal
                self._generate_excel(completos)
                self.progress_var.set(95)
                
                # Reportes individuales (opcional)
                if self.var_individual_reports.get():
                    self.log("Generando reportes individuales...", "info")
                    individual_dir = Path(self.out_file.get()).parent / "Reportes_Individuales"
                    try:
                        import pandas as pd
                        df = pd.DataFrame(completos)
                        self.report_generator.generate_individual_professional_reports(df, individual_dir)
                        self.log(f"✓ Reportes individuales en: {individual_dir}", "success")
                    except Exception as e:
                        self.log(f"⚠ Error generando reportes individuales: {e}", "warning")
            
            # Mostrar resumen
            self._show_summary(completos, para_revision, errors, total)
            self.progress_var.set(100)
            
        except Exception as e:
            self.log(f"Error crítico: {e}", "error")
            self.log(traceback.format_exc(), "error")
        finally:
            self.processing = False
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
    
    def _manual_review_process_incremental(self, review_queue: List[Dict], 
                                          completos: List[Dict]) -> List[Dict]:
        """
        NUEVO v4.0: Revisión manual con re-procesamiento incremental
        Cada vez que el usuario guarda una revisión, re-evalúa los pendientes
        """
        reviewed = []
        pendientes = review_queue.copy()
        
        while pendientes and self.processing:
            # Tomar el siguiente
            record = pendientes.pop(0)
            
            total_inicial = len(review_queue)
            actual = total_inicial - len(pendientes)
            self.progress_label.config(text=f"Revisando {actual}/{total_inicial}")
            
            # Mostrar diálogo
            dialog = ImprovedReviewDialog(self, record)
            self.wait_window(dialog)
            
            if dialog.result:
                # Usuario guardó la revisión
                reviewed.append(dialog.result)
                self.log(f"✓ Revisado: {Path(record['archivo']).name}", "success")
                
                # NUEVO v4.0: RE-PROCESAR pendientes con la nueva información
                if pendientes:
                    self.log("🔄 Re-procesando pendientes con nueva información...", "info")
                    
                    # Agregar el registro recién revisado al batch
                    self.batch_memory.add_registro(dialog.result)
                    
                    # Re-procesar pendientes
                    nuevos_completos, nuevos_pendientes = self.batch_processor.post_process_batch(
                        pendientes,
                        log_callback=None  # Sin log para evitar spam
                    )
                    
                    # Actualizar listas
                    if nuevos_completos:
                        reviewed.extend(nuevos_completos)
                        self.log(f"   ✓ {len(nuevos_completos)} boletas resueltas automáticamente!", "success")
                    
                    pendientes = nuevos_pendientes
            else:
                # Usuario omitió
                self.log(f"⏭ Omitido: {Path(record['archivo']).name}", "warning")
        
        return reviewed
    
    def _calculate_final_quality(self, registro: Dict) -> float:
        """Calcula score de calidad final"""
        score = 0.0
        
        pesos = {
            'rut': 0.20,
            'nombre': 0.15,
            'monto': 0.20,
            'fecha_documento': 0.10,
            'convenio': 0.15,
            'mes_nombre': 0.10,
            'nro_boleta': 0.05,
            'glosa': 0.05
        }
        
        for campo, peso in pesos.items():
            valor = registro.get(campo, '')
            if valor and valor not in ['SIN_CONVENIO', 'SIN_PERIODO']:
                score += peso * 0.6
                conf_campo = registro.get(f'{campo}_confidence', 0.7)
                score += peso * 0.4 * conf_campo
        
        return round(min(score, 1.0), 3)
    
    def _generate_excel(self, results):
        """Genera el archivo Excel con guardado seguro"""
        try:
            output_file = Path(self.out_file.get())
            output_file.parent.mkdir(parents=True, exist_ok=True)

            self.log("Generando Excel principal...", "info")

            # Crear en temporal
            tmp_file = output_file.with_suffix(".tmp.xlsx")
            df = self.report_generator.create_excel_with_reports(
                results,
                str(tmp_file),
                generate_reports=self.var_generate_reports.get()
            )

            # Reemplazo atómico
            try:
                os.replace(tmp_file, output_file)
                self.log(f"✓ Excel generado: {output_file}", "success")
            except PermissionError:
                alt = output_file.with_name(
                    f"{output_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{output_file.suffix}"
                )
                os.replace(tmp_file, alt)
                self.log(f"⚠ Archivo destino en uso. Guardado como: {alt}", "warning")

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
    
    def _show_summary(self, completos, para_revision, errors, total):
        """Muestra resumen final"""
        self.log("", "info")
        self.log("=" * 60, "info")
        self.log("PROCESAMIENTO COMPLETADO ✓", "success")
        self.log("=" * 60, "info")
        
        procesados = len(completos)
        revisados = len(para_revision)
        fallidos = len(errors)
        
        success_rate = (procesados / total * 100) if total > 0 else 0
        
        self.log(f"Total archivos: {total}", "info")
        self.log(f"Procesados automáticamente: {procesados} ({success_rate:.1f}%)", "success")
        self.log(f"Revisiones manuales omitidas: {revisados}", "warning")
        self.log(f"Con errores: {fallidos}", "error" if fallidos > 0 else "info")
        
        if completos:
            avg_quality = sum(r.get('quality_score', 0) for r in completos) / len(completos)
            self.log(f"Calidad promedio: {avg_quality:.1%}", "info")
        
        # Estadísticas de mejora v4.0
        self.log("", "info")
        self.log("📊 Estadísticas v4.0:", "info")
        mejoras_rut = sum(1 for r in completos if r.get('rut_origen') in ['batch_post', 'memoria_post'])
        mejoras_convenio = sum(1 for r in completos if r.get('convenio_origen') in ['decreto_inferido', 'inferencia_post'])
        
        if mejoras_rut > 0:
            self.log(f"  • {mejoras_rut} RUTs inferidos por post-procesamiento", "success")
        if mejoras_convenio > 0:
            self.log(f"  • {mejoras_convenio} convenios inferidos automáticamente", "success")
        
        # Guardar memoria
        stats = self.data_processor.memory.get_stats()
        self.log(f"Memoria guardada ({stats['total_ruts']} RUTs conocidos)", "info")


def main():
    """Función principal"""
    app = BoletasApp()
    
    app.log("=" * 60, "info")
    app.log("SISTEMA DE BOLETAS OCR v4.0 FINAL", "info")
    app.log("Post-procesamiento Inteligente + Revisión Incremental", "info")
    app.log("=" * 60, "info")
    app.log("Listo para procesar ✓", "success")
    
    app.mainloop()


if __name__ == "__main__":
    main()
