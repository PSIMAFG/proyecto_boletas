# app_main.py
"""
Aplicación GUI principal del Sistema de Boletas
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import os
import sys

# Agregar directorio de módulos al path
sys.path.append(str(Path(__file__).parent / "modules"))

from modules.config import Config
from modules.ocr_processor import OCRProcessor
from modules.data_extractor import DataExtractor
from modules.report_generator import ReportGenerator
from modules.utils import *

class ReviewDialog(tk.Toplevel):
    """Diálogo de revisión manual de boletas"""
    
    def __init__(self, master, data):
        super().__init__(master)
        self.title("Revisión Manual de Boleta")
        self.geometry("900x600")
        self.resizable(True, True)
        
        self.data = data.copy()
        self.result = None
        
        self.create_widgets()
        
        # Configurar para modal
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
    def create_widgets(self):
        """Crea los widgets del diálogo"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Frame de información
        info_frame = ttk.LabelFrame(main_frame, text="Información del Archivo", padding="5")
        info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(info_frame, text=f"Archivo: {Path(self.data.get('archivo', '')).name}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Confianza OCR: {self.data.get('confianza', 0):.2%}").pack(anchor="w")
        
        # Frame de campos
        fields_frame = ttk.LabelFrame(main_frame, text="Datos Extraídos (edite si es necesario)", padding="10")
        fields_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Variables para los campos
        self.vars = {}
        fields = [
            ("nombre", "Nombre:"),
            ("rut", "RUT:"),
            ("nro_boleta", "N° Boleta:"),
            ("fecha_documento", "Fecha:"),
            ("monto", "Monto:"),
            ("convenio", "Convenio:"),
            ("horas", "Horas:"),
            ("tipo", "Tipo:"),
            ("decreto_alcaldicio", "Decreto:"),
        ]
        
        for row, (field, label) in enumerate(fields):
            ttk.Label(fields_frame, text=label, width=15).grid(row=row, column=0, sticky="w", pady=2)
            
            var = tk.StringVar(value=self.data.get(field, ""))
            self.vars[field] = var
            
            entry = ttk.Entry(fields_frame, textvariable=var, width=50)
            entry.grid(row=row, column=1, sticky="ew", pady=2)
        
        # Glosa (campo de texto multilínea)
        row = len(fields)
        ttk.Label(fields_frame, text="Glosa:").grid(row=row, column=0, sticky="nw", pady=2)
        
        self.text_glosa = tk.Text(fields_frame, height=4, width=50)
        self.text_glosa.grid(row=row, column=1, sticky="ew", pady=2)
        self.text_glosa.insert("1.0", self.data.get("glosa", ""))
        
        fields_frame.columnconfigure(1, weight=1)
        
        # Frame de botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Guardar", command=self.on_save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Omitir", command=self.on_skip).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.on_cancel).pack(side="right", padx=5)
    
    def on_save(self):
        """Guarda los cambios"""
        for field, var in self.vars.items():
            self.data[field] = var.get().strip()
        
        self.data["glosa"] = self.text_glosa.get("1.0", "end-1c").strip()
        self.data["manually_reviewed"] = True
        
        self.result = self.data
        self.destroy()
    
    def on_skip(self):
        """Omite este registro"""
        self.result = None
        self.destroy()
    
    def on_cancel(self):
        """Cancela la revisión"""
        self.result = None
        self.destroy()


class BoletasApp(tk.Tk):
    """Aplicación principal del sistema de boletas"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Sistema de Boletas de Honorarios v3.0")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        
        # Configuración
        self.config = Config()
        
        # Procesadores
        self.ocr_processor = OCRProcessor(self.config)
        self.data_extractor = DataExtractor(self.config)
        self.report_generator = ReportGenerator(self.config)
        
        # Variables
        self.input_dir = tk.StringVar(value=str(self.config.DEFAULT_INPUT_DIR))
        self.output_file = tk.StringVar(value=str(self.config.DEFAULT_OUTPUT_FILE))
        self.ocr_engine = tk.StringVar(value="auto")
        self.var_manual_review = tk.BooleanVar(value=True)
        self.var_generate_reports = tk.BooleanVar(value=True)
        self.min_confidence = tk.DoubleVar(value=0.5)
        
        # Estado
        self.processing = False
        self.thread = None
        self.results = []
        
        # Crear interfaz
        self.create_widgets()
        
        # Verificar capacidades
        self.check_capabilities()
    
    def check_capabilities(self):
        """Verifica las capacidades disponibles"""
        has_paddle = os.environ.get('HAS_PADDLE', '0') == '1'
        has_tesseract = os.environ.get('HAS_TESSERACT', '0') == '1'
        
        if not has_tesseract and not has_paddle:
            messagebox.showwarning(
                "Capacidades Limitadas",
                "No se detectó Tesseract ni PaddleOCR.\n"
                "Solo se podrán procesar PDFs con texto embebido."
            )
            self.ocr_engine.set("embedded")
        elif not has_paddle:
            self.ocr_engine.set("tesseract")
        
        # Actualizar opciones de motor OCR
        if hasattr(self, 'ocr_options'):
            if not has_tesseract:
                self.radio_tesseract.config(state="disabled")
            if not has_paddle:
                self.radio_paddle.config(state="disabled")
    
    def create_widgets(self):
        """Crea la interfaz de usuario"""
        # Frame principal
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Notebook para pestañas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Pestaña principal
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Procesamiento")
        self.create_main_tab(main_tab)
        
        # Pestaña de configuración
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="Configuración")
        self.create_config_tab(config_tab)
        
        # Pestaña de ayuda
        help_tab = ttk.Frame(notebook)
        notebook.add(help_tab, text="Ayuda")
        self.create_help_tab(help_tab)
    
    def create_main_tab(self, parent):
        """Crea la pestaña principal"""
        # Frame de entrada/salida
        io_frame = ttk.LabelFrame(parent, text="Archivos", padding="10")
        io_frame.pack(fill="x", pady=(0, 10))
        
        # Directorio de entrada
        ttk.Label(io_frame, text="Carpeta de entrada:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(io_frame, textvariable=self.input_dir, width=50).grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Button(io_frame, text="Buscar...", command=self.select_input_dir).grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # Archivo de salida
        ttk.Label(io_frame, text="Archivo de salida:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(io_frame, textvariable=self.output_file, width=50).grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Button(io_frame, text="Buscar...", command=self.select_output_file).grid(row=1, column=2, padx=(5, 0), pady=5)
        
        io_frame.columnconfigure(1, weight=1)
        
        # Frame de opciones
        options_frame = ttk.LabelFrame(parent, text="Opciones", padding="10")
        options_frame.pack(fill="x", pady=(0, 10))
        
        # Motor OCR
        ttk.Label(options_frame, text="Motor OCR:").pack(anchor="w")
        ocr_frame = ttk.Frame(options_frame)
        ocr_frame.pack(fill="x", pady=(0, 10))
        
        self.radio_auto = ttk.Radiobutton(ocr_frame, text="Auto (Recomendado)", 
                                          variable=self.ocr_engine, value="auto")
        self.radio_auto.pack(side="left", padx=5)
        
        self.radio_tesseract = ttk.Radiobutton(ocr_frame, text="Tesseract", 
                                               variable=self.ocr_engine, value="tesseract")
        self.radio_tesseract.pack(side="left", padx=5)
        
        self.radio_paddle = ttk.Radiobutton(ocr_frame, text="PaddleOCR", 
                                            variable=self.ocr_engine, value="paddle")
        self.radio_paddle.pack(side="left", padx=5)
        
        self.ocr_options = ocr_frame  # Para referencia posterior
        
        # Otras opciones
        ttk.Checkbutton(options_frame, text="Revisión manual de registros dudosos",
                       variable=self.var_manual_review).pack(anchor="w", pady=2)
        
        ttk.Checkbutton(options_frame, text="Generar informes por convenio",
                       variable=self.var_generate_reports).pack(anchor="w", pady=2)
        
        conf_frame = ttk.Frame(options_frame)
        conf_frame.pack(fill="x", pady=5)
        ttk.Label(conf_frame, text="Umbral de confianza mínima:").pack(side="left")
        ttk.Scale(conf_frame, from_=0.0, to=1.0, variable=self.min_confidence,
                 orient="horizontal", length=200).pack(side="left", padx=10)
        self.conf_label = ttk.Label(conf_frame, text="0.50")
        self.conf_label.pack(side="left")
        
        self.min_confidence.trace("w", lambda *args: self.conf_label.config(
            text=f"{self.min_confidence.get():.2f}"))
        
        # Botones de control
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill="x", pady=(0, 10))
        
        self.btn_start = ttk.Button(control_frame, text="▶ Iniciar Procesamiento",
                                   command=self.start_processing)
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="■ Detener",
                                  command=self.stop_processing, state="disabled")
        self.btn_stop.pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="Salir", command=self.quit).pack(side="right", padx=5)
        
        # Barra de progreso
        self.progress = ttk.Progressbar(parent, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))
        
        # Log
        log_frame = ttk.LabelFrame(parent, text="Registro de Actividad", padding="5")
        log_frame.pack(fill="both", expand=True)
        
        # Text widget con scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(text_frame, height=10, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Tags para colores
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")
    
    def create_config_tab(self, parent):
        """Crea la pestaña de configuración"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Configuración del Sistema", 
                 font=("", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Información del sistema
        info_frame = ttk.LabelFrame(frame, text="Información", padding="10")
        info_frame.pack(fill="x", pady=(0, 10))
        
        has_paddle = os.environ.get('HAS_PADDLE', '0') == '1'
        has_tesseract = os.environ.get('HAS_TESSERACT', '0') == '1'
        
        ttk.Label(info_frame, text=f"Tesseract OCR: {'✅ Disponible' if has_tesseract else '❌ No disponible'}").pack(anchor="w")
        ttk.Label(info_frame, text=f"PaddleOCR: {'✅ Disponible' if has_paddle else '❌ No disponible'}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Python: {sys.version}").pack(anchor="w")
        
        # Directorios
        dir_frame = ttk.LabelFrame(frame, text="Directorios", padding="10")
        dir_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(dir_frame, text=f"Directorio base: {self.config.BASE_DIR}").pack(anchor="w")
        ttk.Label(dir_frame, text=f"Directorio temporal: {self.config.TEMP_DIR}").pack(anchor="w")
    
    def create_help_tab(self, parent):
        """Crea la pestaña de ayuda"""
        frame = ttk.Frame(parent, padding="20")
        frame.pack(fill="both", expand=True)
        
        help_text = """
SISTEMA DE BOLETAS DE HONORARIOS v3.0
======================================

CARACTERÍSTICAS:
• Procesamiento automático de boletas en PDF e imágenes
• Múltiples motores OCR (Tesseract y PaddleOCR)
• Extracción inteligente de campos
• Revisión manual asistida
• Generación de informes por convenio
• Exportación a Excel con fórmulas dinámicas

MOTORES OCR:
• AUTO: Selecciona automáticamente el mejor motor
• Tesseract: Rápido y preciso para documentos limpios
• PaddleOCR: Mejor para imágenes con problemas

CAMPOS EXTRAÍDOS:
• Nombre del prestador
• RUT
• Número de boleta
• Fecha
• Monto
• Convenio
• Horas trabajadas
• Tipo (mensual/semanal)
• Glosa
• Decreto alcaldicio

FORMATO DE ARCHIVOS:
• PDF (con o sin texto embebido)
• Imágenes: PNG, JPG, JPEG, TIF, TIFF, BMP

TIPS:
• Use escaneos de al menos 300 DPI
• Mantenga los documentos derechos
• Organice por carpetas (año/mes)
• Revise registros con baja confianza
• Active informes para análisis detallado

Para más información, visite la documentación del proyecto.
"""
        
        text = tk.Text(frame, wrap="word", width=80)
        text.pack(fill="both", expand=True)
        text.insert("1.0", help_text)
        text.configure(state="disabled")
    
    def log(self, message, level="info"):
        """Agrega un mensaje al log"""
        self.log_text.insert("end", f"{message}\n", level)
        self.log_text.see("end")
        self.update_idletasks()
    
    def select_input_dir(self):
        """Selecciona el directorio de entrada"""
        directory = filedialog.askdirectory(
            title="Seleccionar carpeta de entrada",
            initialdir=self.input_dir.get()
        )
        if directory:
            self.input_dir.set(directory)
    
    def select_output_file(self):
        """Selecciona el archivo de salida"""
        filename = filedialog.asksaveasfilename(
            title="Guardar resultados como",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
            initialfile="boletas_procesadas.xlsx"
        )
        if filename:
            self.output_file.set(filename)
    
    def start_processing(self):
        """Inicia el procesamiento"""
        if self.processing:
            return
        
        # Validar entrada
        input_path = Path(self.input_dir.get())
        if not input_path.exists():
            messagebox.showerror("Error", "La carpeta de entrada no existe")
            return
        
        output_path = Path(self.output_file.get())
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configurar estado
        self.processing = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress["value"] = 0
        
        # Limpiar log
        self.log_text.delete("1.0", "end")
        
        # Iniciar thread de procesamiento
        self.thread = threading.Thread(target=self.process_files, daemon=True)
        self.thread.start()
    
    def stop_processing(self):
        """Detiene el procesamiento"""
        self.processing = False
        self.btn_stop.config(state="disabled")
        self.log("Deteniendo procesamiento...", "warning")
    
    def process_files(self):
        """Procesa los archivos (ejecuta en thread separado)"""
        try:
            self.log("Iniciando procesamiento...", "info")
            
            # Configurar motor OCR
            self.ocr_processor.set_engine(self.ocr_engine.get())
            
            # Buscar archivos
            input_path = Path(self.input_dir.get())
            files = list(find_files(input_path, self.config.SUPPORTED_EXTENSIONS))
            
            if not files:
                self.log("No se encontraron archivos para procesar", "warning")
                return
            
            self.log(f"Encontrados {len(files)} archivos", "info")
            
            # Configurar progreso
            self.progress["maximum"] = len(files)
            
            # Procesar archivos
            self.results = []
            
            for i, file_path in enumerate(files):
                if not self.processing:
                    break
                
                self.log(f"Procesando: {file_path.name}", "info")
                
                try:
                    # Procesar con OCR
                    ocr_result = self.ocr_processor.process_file(file_path)
                    
                    if ocr_result and ocr_result.get("text"):
                        # Extraer campos
                        data = self.data_extractor.extract_fields(
                            ocr_result["text"],
                            file_path
                        )
                        
                        # Agregar metadata
                        data["archivo"] = str(file_path)
                        data["confianza"] = ocr_result.get("confidence", 0)
                        data["motor_ocr"] = ocr_result.get("engine", "unknown")
                        
                        # Verificar si necesita revisión
                        if self.var_manual_review.get():
                            if data["confianza"] < self.min_confidence.get():
                                data["needs_review"] = True
                        
                        self.results.append(data)
                        self.log(f"  ✓ Extraído: {data.get('nombre', 'Sin nombre')}", "success")
                    else:
                        self.log(f"  ✗ Sin texto extraíble", "error")
                        
                except Exception as e:
                    self.log(f"  ✗ Error: {e}", "error")
                
                # Actualizar progreso
                self.progress["value"] = i + 1
                self.update_idletasks()
            
            # Revisión manual si está habilitada
            if self.var_manual_review.get():
                self.review_results()
            
            # Generar reporte
            if self.results:
                self.generate_report()
            else:
                self.log("No hay resultados para guardar", "warning")
            
        except Exception as e:
            self.log(f"Error crítico: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
        
        finally:
            self.processing = False
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.log("Procesamiento completado", "success")
    
    def review_results(self):
        """Ejecuta la revisión manual de resultados dudosos"""
        to_review = [r for r in self.results if r.get("needs_review")]
        
        if not to_review:
            return
        
        self.log(f"Revisión manual: {len(to_review)} registros", "info")
        
        reviewed = []
        for data in to_review:
            # Mostrar diálogo de revisión
            dialog = ReviewDialog(self, data)
            self.wait_window(dialog)
            
            if dialog.result:
                reviewed.append(dialog.result)
        
        # Actualizar resultados
        self.results = [r for r in self.results if not r.get("needs_review")]
        self.results.extend(reviewed)
    
    def generate_report(self):
        """Genera el reporte Excel"""
        try:
            output_path = Path(self.output_file.get())
            
            # Generar Excel
            self.report_generator.generate_excel(
                self.results,
                output_path,
                generate_reports=self.var_generate_reports.get()
            )
            
            self.log(f"Reporte guardado: {output_path}", "success")
            self.log(f"Total de registros: {len(self.results)}", "info")
            
            # Abrir el archivo si el usuario quiere
            if messagebox.askyesno("Éxito", "¿Desea abrir el archivo Excel generado?"):
                os.startfile(str(output_path))  # Windows
                # Para otros SO: subprocess.run(["open", str(output_path)])
                
        except Exception as e:
            self.log(f"Error generando reporte: {e}", "error")
            messagebox.showerror("Error", f"No se pudo generar el reporte:\n{e}")


if __name__ == "__main__":
    app = BoletasApp()
    app.mainloop()