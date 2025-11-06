# main.py (VersiÃƒÂ³n Mejorada 3.1)
"""
AplicaciÃƒÂ³n principal mejorada con extracciÃƒÂ³n mÃƒÂ¡s robusta
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
from modules.data_processing import DataProcessorOptimized
from modules.report_generator import ReportGenerator


class ImprovedReviewDialog(tk.Toplevel):
    """DiÃƒÂ¡logo mejorado de revisiÃƒÂ³n manual"""
    
    def __init__(self, master, row: dict):
        super().__init__(master)
        self.title(f"RevisiÃƒÂ³n: {Path(row.get('archivo', '')).name}")
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
        # InformaciÃƒÂ³n del archivo
        info_text = f"Archivo: {Path(self.row.get('archivo', '')).name}\n"
        info_text += f"Confianza OCR: {self.row.get('confianza', 0):.1%}\n"
        info_text += f"Calidad: {self.row.get('quality_score', 0):.1%}"
        
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
        
        ttk.Button(btn_frame, text="Ã°Å¸â€œâ€š Abrir original", 
                  command=self._open_original).pack(side="left", padx=2)
    
    def _create_fields(self, parent):
        """Crea los campos editables"""
        # Crear variables
        self.vars = {}
        
        campos = [
            ("Nombre", "nombre", "entry"),
            ("RUT", "rut", "entry"),
            ("NÃ‚Â° Boleta", "nro_boleta", "entry"),
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
        
        # InformaciÃƒÂ³n adicional
        if self.row.get('valor_hora_calculado'):
            info = f"\nValor hora calculado: ${self.row['valor_hora_calculado']:,.0f}"
            if self.row.get('monto_fuera_rango'):
                info += "\nÃ¢Å¡Â Ã¯Â¸Â Monto parece fuera de rango esperado"
            ttk.Label(parent, text=info, foreground="blue").pack(pady=5)
        
        # Botones de acciÃƒÂ³n
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="Ã¢Å“â€œ Guardar", 
                  command=self._on_save).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Ã¢Å Ëœ Omitir", 
                  command=self._on_skip).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Ã¢Å“â€” Cancelar", 
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
        """Cancela la revisiÃƒÂ³n"""
        self.result = None
        self.destroy()


class BoletasApp(tk.Tk):
    """AplicaciÃƒÂ³n principal mejorada"""
    
    def __init__(self):
        super().__init__()
        self.title("Sistema de Boletas OCR v3.1 - Mejorado")
        self.geometry("1200x800")
        
        # Variables
        self.root_dir = tk.StringVar(value=str(REGISTRO_DIR.resolve()))
        self.out_file = tk.StringVar(value=str((EXPORT_DIR / "boletas_procesadas.xlsx").resolve()))
        self.var_manual_review = tk.BooleanVar(value=True)
        self.var_generate_reports = tk.BooleanVar(value=True)
        self.var_individual_reports = tk.BooleanVar(value=True)
        
        # Procesadores
        self.data_processor = DataProcessorOptimized()
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
        
        # ConfiguraciÃƒÂ³n
        config_frame = ttk.LabelFrame(main_frame, text="ConfiguraciÃƒÂ³n", padding=10)
        config_frame.pack(fill="x", pady=5)
        
        # Carpeta entrada
        row1 = ttk.Frame(config_frame)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Ã°Å¸â€œÂ Carpeta entrada:").pack(side="left")
        ttk.Entry(row1, textvariable=self.root_dir, width=60).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(row1, text="Seleccionar", command=self.select_input).pack(side="left")
        
        # Archivo salida
        row2 = ttk.Frame(config_frame)
        row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="Ã°Å¸â€œÅ  Archivo salida:").pack(side="left")
        ttk.Entry(row2, textvariable=self.out_file, width=60).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(row2, text="Guardar como", command=self.select_output).pack(side="left")
        
        # Opciones
        options_frame = ttk.LabelFrame(main_frame, text="Opciones", padding=10)
        options_frame.pack(fill="x", pady=5)
        
        ttk.Checkbutton(options_frame, text="Ã¢Å“â€œ RevisiÃƒÂ³n manual de registros dudosos",
                       variable=self.var_manual_review).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Ã°Å¸â€œÅ  Generar informes por convenio",
                       variable=self.var_generate_reports).pack(anchor="w")
        
        # Botones control
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        self.btn_start = ttk.Button(control_frame, text="Ã¢â€“Â¶ Iniciar Procesamiento",
                                    command=self.start_processing)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="Ã¢ÂÂ¸ Detener",
                                   command=self.stop_processing,
                                   state="disabled")
        self.btn_stop.pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="Ã¢Å’â€š Salir", command=self.quit).pack(side="right", padx=5)
        
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
            "info": "Ã¢â€žÂ¹",
            "success": "Ã¢Å“â€œ",
            "warning": "Ã¢Å¡Â ",
            "error": "Ã¢Å“â€”"
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
            self.log("Tesseract: OK Ã¢Å“â€œ", "success")
        else:
            self.log("Tesseract: NO ENCONTRADO", "warning")
        
        if detect_poppler_bin():
            self.log("Poppler: OK Ã¢Å“â€œ", "success")
        else:
            self.log("Poppler: No encontrado (opcional)", "info")
    
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
        
        self.log("=" * 50, "info")
        self.log("INICIANDO PROCESAMIENTO", "info")
        self.log("=" * 50, "info")
        self.log(f"Carpeta: {input_dir}", "info")
        self.log(f"Salida: {self.out_file.get()}", "info")
        
        # Thread de procesamiento
        self.thread = threading.Thread(target=self.process_files_thread, daemon=True)
        self.thread.start()
    
    def stop_processing(self):
        """Detiene el procesamiento"""
        self.processing = False
        self.log("Deteniendo...", "warning")
    
    def process_files_thread(self):
        """Thread principal de procesamiento"""
        try:
            input_dir = Path(self.root_dir.get())
            files = list(iter_files(input_dir))
            total = len(files)
            
            if total == 0:
                self.log("No se encontraron archivos", "warning")
                return
            
            self.log(f"Encontrados {total} archivo(s)", "info")
            
            results = []
            review_queue = []
            errors = []
            
            # Procesar archivos
            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(self.data_processor.process_file, f): f for f in files}
                
                completed = 0
                for future in as_completed(futures):
                    if not self.processing:
                        break
                    
                    completed += 1
                    progress = (completed / total) * 100
                    self.progress_var.set(progress)
                    self.progress_label.config(text=f"{completed}/{total}")
                    
                    file_path = futures[future]
                    
                    try:
                        result = future.result(timeout=30)
                        
                        if result.get('error'):
                            errors.append(str(file_path))
                            self.log(f"Ã¢Å“â€” Error: {file_path.name} - {result.get('error')}", "error")
                        elif result.get('needs_review'):
                            review_queue.append(result)
                            self.log(f"Ã¢Å¡Â  Revisar: {file_path.name}", "warning")
                        else:
                            results.append(result)
                            quality = result.get('quality_score', 0)
                            self.log(f"Ã¢Å“â€œ OK: {file_path.name} (Q:{quality:.0%})", "success")
                    
                    except Exception as e:
                        errors.append(str(file_path))
                        self.log(f"Ã¢Å“â€” Error: {file_path.name} - {e}", "error")
                    
                    self.update_idletasks()
            
            # RevisiÃƒÂ³n manual
            if self.var_manual_review.get() and review_queue:
                self.log(f"Iniciando revisiÃƒÂ³n manual: {len(review_queue)} boletas", "info")
                reviewed = self._manual_review_process(review_queue)
                results.extend(reviewed)
            
            # Generar Excel
            if results:
                self._generate_excel(results)
            
            # Mostrar resumen
            self._show_summary(results, errors, total)
            
        except Exception as e:
            self.log(f"Error crÃƒÂ­tico: {e}", "error")
            self.log(traceback.format_exc(), "error")
        finally:
            self.processing = False
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.progress_var.set(100)
    
    def _manual_review_process(self, review_queue):
        """Proceso de revisiÃƒÂ³n manual"""
        reviewed = []
        
        for i, record in enumerate(review_queue):
            if not self.processing:
                break
            
            self.progress_label.config(text=f"Revisando {i+1}/{len(review_queue)}")
            
            dialog = ImprovedReviewDialog(self, record)
            self.wait_window(dialog)
            
            if dialog.result:
                reviewed.append(dialog.result)
                self.log(f"Ã¢Å“â€œ Revisado: {Path(record['archivo']).name}", "success")
            else:
                self.log(f"Ã¢Å Ëœ Omitido: {Path(record['archivo']).name}", "warning")
        
        return reviewed
    
    def _generate_excel(self, results):
        """Genera el archivo Excel con guardado seguro"""
        try:
            output_file = Path(self.out_file.get())
            output_file.parent.mkdir(parents=True, exist_ok=True)

            self.log("Generando Excel...", "info")

            # 1) Crear el Excel pero en un temporal
            tmp_file = output_file.with_suffix(".tmp.xlsx")
            df = self.report_generator.create_excel_with_reports(
                results,
                str(tmp_file),  # ojo: escribir al temporal
                generate_reports=self.var_generate_reports.get()
            )

            # 2) Intentar reemplazo atÃƒÂ³mico
            try:
                os.replace(tmp_file, output_file)  # sobrescribe si existe
                self.log(f"Ã¢Å“â€œ Excel generado: {output_file}", "success")
            except PermissionError:
                # 3) Si estÃƒÂ¡ bloqueado, guardamos con nombre alternativo
                alt = output_file.with_name(
                    f"{output_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{output_file.suffix}"
                )
                os.replace(tmp_file, alt)
                self.log("Ã¢Å¡Â  Archivo destino en uso (Excel abierto). "
                        f"Guardado como: {alt}", "warning")

            self.log(f"  Total registros: {len(df)}", "info")

            # Solo preguntar abrir si se generÃƒÂ³ con ÃƒÂ©xito sin lock
            if output_file.exists():
                if messagebox.askyesno("Completado", "Ã‚Â¿Abrir el archivo Excel?"):
                    try:
                        os.startfile(str(output_file))
                    except Exception:
                        pass

        except Exception as e:
            self.log(f"Error generando Excel: {e}", "error")
            # Limpieza del temporal si quedÃƒÂ³ tirado
            try:
                if 'tmp_file' in locals() and Path(tmp_file).exists():
                    Path(tmp_file).unlink(missing_ok=True)
            except Exception:
                pass
    
    def _show_summary(self, results, errors, total):
        """Muestra resumen final"""
        self.log("=" * 50, "info")
        self.log("PROCESAMIENTO COMPLETADO", "success")
        self.log("=" * 50, "info")
        
        processed = len(results)
        failed = len(errors)
        success_rate = (processed / total * 100) if total > 0 else 0
        
        self.log(f"Total archivos: {total}", "info")
        self.log(f"Procesados: {processed} ({success_rate:.1f}%)", "success")
        self.log(f"Con errores: {failed}", "error" if failed > 0 else "info")   
        
        if results:
            avg_quality = sum(r.get('quality_score', 0) for r in results) / len(results)
            self.log(f"Calidad promedio: {avg_quality:.1%}", "info")
        
        # Guardar memoria
        if processed > 0:
            try:
                self.data_processor.memory.save()
                stats = self.data_processor.memory.get_stats()
                self.log(f"Memoria guardada ({stats['total_ruts']} RUTs conocidos).", "info")
            except Exception as e:
                self.log(f"Error guardando memoria: {e}", "warning")


def main():
    """FunciÃƒÂ³n principal"""
    app = BoletasApp()
    
    app.log("=" * 50, "info")
    app.log("SISTEMA DE BOLETAS OCR v3.1", "info")
    app.log("VersiÃƒÂ³n mejorada con extracciÃƒÂ³n robusta", "info")
    app.log("=" * 50, "info")
    app.log("Listo para procesar Ã¢Å“â€œ", "success")
    
    app.mainloop()


if __name__ == "__main__":
    main()