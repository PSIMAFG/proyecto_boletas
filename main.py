# main.py (Versión Simplificada y Corregida)
"""
Aplicación principal del sistema de procesamiento de boletas
Versión 3.1 - Simplificada y corregida
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import traceback
from PIL import Image, ImageTk
import sys
import os
from datetime import datetime
import pandas as pd

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

# Importar configuración y módulos
from config import *
from modules.utils import *
from modules.ocr_extraction import OCRExtractorOptimized
from modules.data_processing import DataProcessorOptimized
from modules.report_generator import ReportGenerator


class SimpleReviewDialog(tk.Toplevel):
    """Diálogo simplificado de revisión manual"""
    
    def __init__(self, master, row: dict):
        super().__init__(master)
        self.title("Revisión manual de boleta")
        self.geometry("1200x700")
        self.resizable(True, True)
        
        self.row = row.copy()
        self.result = None
        
        # Frame principal
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Panel izquierdo - Vista previa
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self._create_preview_panel(left_panel)
        
        # Panel derecho - Campos
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="left", fill="both", expand=False)
        
        self._create_fields_panel(right_panel)
        
        self.grab_set()
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_preview_panel(self, parent):
        """Crea el panel de vista previa"""
        ttk.Label(parent, text="Vista previa", font=('Arial', 10, 'bold')).pack(anchor="w")
        
        # Frame para la imagen
        img_frame = ttk.Frame(parent)
        img_frame.pack(fill="both", expand=True, pady=5)
        
        # Canvas para la imagen
        canvas = tk.Canvas(img_frame, bg='white', width=600, height=400)
        canvas.pack(fill="both", expand=True)
        
        # Cargar imagen
        preview_path = self.row.get("preview_path", "")
        if preview_path and Path(preview_path).exists():
            try:
                print(f"Cargando preview desde: {preview_path}")
                pil_img = Image.open(preview_path)
                # Escalar imagen
                pil_img.thumbnail((600, 800), Image.Resampling.LANCZOS)
                self.tk_image = ImageTk.PhotoImage(pil_img)
                canvas.create_image(10, 10, anchor="nw", image=self.tk_image)
            except Exception as e:
                print(f"Error cargando imagen: {e}")
                canvas.create_text(10, 10, anchor="nw", text=f"Error: {e}")
        else:
            canvas.create_text(10, 10, anchor="nw", text="Vista previa no disponible")
        
        # Botón para abrir archivo original
        ttk.Button(parent, text="Abrir archivo original",
                  command=self._open_original).pack(pady=5)
    
    def _create_fields_panel(self, parent):
        """Crea el panel de campos"""
        ttk.Label(parent, text="Campos extraídos", font=('Arial', 10, 'bold')).pack(anchor="w", pady=(0, 10))
        
        # Frame de campos
        fields_frame = ttk.Frame(parent)
        fields_frame.pack(fill="both", expand=True)
        
        self.field_vars = {}
        
        # Campos a editar
        fields = [
            ("Nombre:", "nombre"),
            ("RUT:", "rut"),
            ("N° Boleta:", "nro_boleta"),
            ("Fecha (YYYY-MM-DD):", "fecha_documento"),
            ("Monto:", "monto"),
            ("Convenio:", "convenio"),
            ("Horas:", "horas"),
            ("Tipo:", "tipo"),
            ("Decreto:", "decreto_alcaldicio")
        ]
        
        for i, (label, field) in enumerate(fields):
            ttk.Label(fields_frame, text=label, width=20, anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            
            var = tk.StringVar(value=self.row.get(field, ""))
            self.field_vars[field] = var
            
            if field == "convenio":
                widget = ttk.Combobox(fields_frame, textvariable=var, values=[""] + KNOWN_CONVENIOS, width=30)
            elif field == "tipo":
                widget = ttk.Combobox(fields_frame, textvariable=var, values=["", "mensual", "semanal"], width=30)
            else:
                widget = ttk.Entry(fields_frame, textvariable=var, width=30)
            
            widget.grid(row=i, column=1, sticky="w", pady=2)
            
            # Mostrar confianza si existe
            conf_field = f"{field}_confidence"
            if conf_field in self.row:
                conf = self.row[conf_field]
                color = "green" if conf > 0.7 else "orange" if conf > 0.4 else "red"
                conf_label = ttk.Label(fields_frame, text=f"{conf:.0%}", foreground=color)
                conf_label.grid(row=i, column=2, padx=5)
        
        # Campo de glosa (multilinea)
        ttk.Label(fields_frame, text="Glosa:", width=20, anchor="w").grid(row=len(fields), column=0, sticky="nw", pady=2)
        self.glosa_text = tk.Text(fields_frame, height=3, width=30)
        self.glosa_text.grid(row=len(fields), column=1, sticky="w", pady=2)
        self.glosa_text.insert("1.0", self.row.get("glosa", ""))
        
        # Botones
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="✓ Guardar", command=self._on_save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="⊘ Omitir", command=self._on_skip).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✗ Cancelar", command=self._on_cancel).pack(side="left", padx=5)
    
    def _open_original(self):
        """Abre el archivo original"""
        path = self.row.get("archivo")
        if path and Path(path).exists():
            try:
                os.startfile(path)  # Windows
            except:
                try:
                    os.system(f'open "{path}"')  # macOS
                except:
                    os.system(f'xdg-open "{path}"')  # Linux
    
    def _on_save(self):
        """Guarda los cambios"""
        result = self.row.copy()
        
        # Obtener valores de los campos
        for field, var in self.field_vars.items():
            result[field] = var.get().strip()
        
        # Obtener glosa
        result["glosa"] = self.glosa_text.get("1.0", "end").strip()
        
        # Marcar como revisado
        result["needs_review"] = False
        result["manually_reviewed"] = True
        
        self.result = result
        self.destroy()
    
    def _on_skip(self):
        """Omite este registro"""
        self.result = None
        self.destroy()
    
    def _on_cancel(self):
        """Cancela la revisión"""
        self.result = "CANCEL"
        self.destroy()


class BoletasAppSimplified(tk.Tk):
    """Aplicación principal simplificada"""
    
    def __init__(self):
        super().__init__()
        self.title("Sistema de Boletas OCR v3.1 - Simplificado")
        self.geometry("1000x700")
        
        # Variables de configuración
        self.root_dir = tk.StringVar(value=str(REGISTRO_DIR))
        self.out_file = tk.StringVar(value=str(EXPORT_DIR / "boletas_procesadas.xlsx"))
        self.var_manual_review = tk.BooleanVar(value=True)
        self.var_generate_reports = tk.BooleanVar(value=True)
        
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
        """Crea la interfaz simplificada"""
        # Frame principal
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="Sistema de Procesamiento OCR de Boletas", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Frame de configuración
        config_frame = ttk.LabelFrame(main_frame, text="Configuración", padding=10)
        config_frame.pack(fill="x", pady=(0, 10))
        
        # Carpeta de entrada
        row1 = ttk.Frame(config_frame)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="Carpeta de entrada:", width=20, anchor="w").pack(side="left")
        ttk.Entry(row1, textvariable=self.root_dir, width=40).pack(side="left", padx=5)
        ttk.Button(row1, text="Seleccionar", command=self.select_input_folder).pack(side="left")
        
        # Archivo de salida
        row2 = ttk.Frame(config_frame)
        row2.pack(fill="x", pady=5)
        ttk.Label(row2, text="Archivo de salida:", width=20, anchor="w").pack(side="left")
        ttk.Entry(row2, textvariable=self.out_file, width=40).pack(side="left", padx=5)
        ttk.Button(row2, text="Guardar como", command=self.select_output_file).pack(side="left")
        
        # Opciones
        options_frame = ttk.LabelFrame(main_frame, text="Opciones", padding=10)
        options_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Checkbutton(options_frame, text="Revisión manual de registros dudosos",
                       variable=self.var_manual_review).pack(anchor="w", pady=2)
        ttk.Checkbutton(options_frame, text="Generar informes por convenio",
                       variable=self.var_generate_reports).pack(anchor="w", pady=2)
        
        # Botones de control
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        self.btn_start = ttk.Button(control_frame, text="▶ Iniciar Procesamiento",
                                   command=self.start_processing)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="⏸ Detener",
                                  command=self.stop_processing,
                                  state="disabled")
        self.btn_stop.pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="Salir", command=self.quit).pack(side="right", padx=5)
        
        # Barra de progreso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=5)
        
        self.progress_label = ttk.Label(main_frame, text="Listo para procesar")
        self.progress_label.pack()
        
        # Log
        log_frame = ttk.LabelFrame(main_frame, text="Registro de actividad", padding=5)
        log_frame.pack(fill="both", expand=True)
        
        # Text widget con scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(text_frame, height=15, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def log(self, message: str):
        """Agrega mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.update_idletasks()
    
    def check_dependencies(self):
        """Verifica dependencias del sistema"""
        self.log("Verificando dependencias...")
        
        if not detect_tesseract_cmd():
            self.log("⚠ Tesseract OCR no encontrado")
            messagebox.showwarning("Tesseract no encontrado",
                                 "Tesseract OCR no está instalado.\n"
                                 "Descárgalo desde: github.com/UB-Mannheim/tesseract")
        else:
            self.log("✓ Tesseract OCR detectado")
        
        if not detect_poppler_bin():
            self.log("⚠ Poppler no encontrado (opcional)")
        else:
            self.log("✓ Poppler detectado")
    
    def select_input_folder(self):
        """Selecciona la carpeta de entrada"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta con boletas")
        if folder:
            self.root_dir.set(folder)
            self.log(f"Carpeta seleccionada: {folder}")
    
    def select_output_file(self):
        """Selecciona el archivo de salida"""
        file = filedialog.asksaveasfilename(
            title="Guardar archivo Excel como",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if file:
            self.out_file.set(file)
            self.log(f"Archivo de salida: {file}")
    
    def start_processing(self):
        """Inicia el procesamiento"""
        if self.processing:
            return
        
        # Validar entrada
        input_dir = Path(self.root_dir.get())
        if not input_dir.exists():
            messagebox.showerror("Error", "La carpeta de entrada no existe")
            return
        
        # Asegurar que el directorio de previews existe
        REVIEW_PREVIEW_DIR.mkdir(exist_ok=True, parents=True)
        
        # Preparar procesamiento
        self.processing = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0)
        
        self.log("=" * 50)
        self.log("INICIANDO PROCESAMIENTO")
        self.log("=" * 50)
        
        # Iniciar thread de procesamiento
        self.thread = threading.Thread(target=self.process_files_thread, daemon=True)
        self.thread.start()
    
    def stop_processing(self):
        """Detiene el procesamiento"""
        self.processing = False
        self.log("Deteniendo procesamiento...")
        self.btn_stop.config(state="disabled")
    
    def process_files_thread(self):
        """Thread principal de procesamiento"""
        try:
            # Recolectar archivos
            input_dir = Path(self.root_dir.get())
            files = list(iter_files(input_dir))
            total_files = len(files)
            
            if total_files == 0:
                self.log("No se encontraron archivos para procesar")
                return
            
            self.log(f"Encontrados {total_files} archivo(s)")
            
            # Procesar archivos
            results = []
            errors = []
            
            for i, file_path in enumerate(files):
                if not self.processing:
                    break
                
                # Actualizar progreso
                progress = ((i + 1) / total_files) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"Procesando {i+1}/{total_files}: {file_path.name}")
                
                try:
                    # Procesar archivo
                    self.log(f"Procesando: {file_path.name}")
                    result = self.data_processor.process_file(file_path)
                    
                    if result:
                        # Verificar si necesita revisión
                        if self.var_manual_review.get() and result.get('needs_review', False):
                            self.log(f"  → Requiere revisión manual")
                            
                            # Mostrar diálogo de revisión
                            dialog = SimpleReviewDialog(self, result)
                            self.wait_window(dialog)
                            
                            if dialog.result == "CANCEL":
                                self.log("Proceso cancelado por el usuario")
                                break
                            elif dialog.result:
                                results.append(dialog.result)
                                self.log(f"  ✓ Revisado y guardado")
                            else:
                                self.log(f"  ⊘ Omitido por el usuario")
                        else:
                            results.append(result)
                            quality = result.get('quality_score', 0)
                            self.log(f"  ✓ Procesado - Calidad: {quality:.0%}")
                    else:
                        errors.append(str(file_path))
                        self.log(f"  ✗ Error procesando archivo")
                        
                except Exception as e:
                    errors.append(str(file_path))
                    self.log(f"  ✗ Error: {str(e)}")
            
            # Generar Excel si hay resultados
            if results:
                self._generate_excel(results)
            
            # Mostrar resumen
            self.log("=" * 50)
            self.log(f"PROCESAMIENTO COMPLETADO")
            self.log(f"Procesados: {len(results)}")
            self.log(f"Con errores: {len(errors)}")
            self.log("=" * 50)
            
            if results:
                if messagebox.askyesno("Proceso completado", 
                                      f"Se procesaron {len(results)} archivos.\n"
                                      f"¿Desea abrir el archivo Excel generado?"):
                    try:
                        os.startfile(self.out_file.get())
                    except:
                        pass
            
        except Exception as e:
            self.log(f"Error crítico: {str(e)}")
            self.log(traceback.format_exc())
            messagebox.showerror("Error", f"Error durante el procesamiento:\n{str(e)}")
        finally:
            self.processing = False
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.progress_var.set(100)
            self.progress_label.config(text="Proceso completado")
    
    def _generate_excel(self, results):
        """Genera el archivo Excel con los resultados"""
        try:
            output_file = self.out_file.get()
            self.log(f"Generando Excel: {output_file}")
            
            # Crear DataFrame
            df = pd.DataFrame(results)
            
            # Ordenar columnas
            columns_order = ["nombre", "rut", "nro_boleta", "fecha_documento", "monto",
                           "convenio", "horas", "tipo", "glosa", "decreto_alcaldicio",
                           "archivo", "paginas", "confianza", "quality_score"]
            
            # Reordenar solo las columnas que existen
            existing_columns = [col for col in columns_order if col in df.columns]
            df = df[existing_columns]
            
            # Generar Excel
            if self.var_generate_reports.get():
                self.report_generator.create_excel_with_reports(
                    results, output_file, generate_reports=True
                )
            else:
                # Solo guardar los datos básicos
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Boletas', index=False)
                    
                    # Ajustar anchos de columna
                    worksheet = writer.sheets['Boletas']
                    for i, col in enumerate(df.columns):
                        max_length = max(df[col].astype(str).str.len().max(), len(col)) + 2
                        worksheet.set_column(i, i, min(max_length, 50))
            
            self.log(f"✓ Excel generado exitosamente")
            
        except Exception as e:
            self.log(f"✗ Error generando Excel: {str(e)}")
            messagebox.showerror("Error", f"Error al generar Excel:\n{str(e)}")


def main():
    """Función principal"""
    app = BoletasAppSimplified()
    app.log("Sistema iniciado")
    app.log("Seleccione una carpeta con boletas para comenzar")
    app.mainloop()


if __name__ == "__main__":
    main()