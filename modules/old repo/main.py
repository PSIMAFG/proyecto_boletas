# SPDX-License-Identifier: BUSL-1.1
# © 2025 Matías A. Fernández

# main.py
"""
Aplicación principal del sistema de procesamiento de boletas de honorarios
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

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

# Importar configuración y módulos
from config import *
from modules.utils import *
from modules.ocr_extraction import OCRExtractor
from modules.data_processing import DataProcessor
from modules.report_generator import ReportGenerator

class ReviewDialog(tk.Toplevel):
    """Diálogo de revisión manual de boletas"""
    
    def __init__(self, master, row: dict):
        super().__init__(master)
        self.title("Revisión manual de boleta")
        self.resizable(True, True)
        self.row = row.copy()
        self.result = None
        
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        
        # Vista previa a la izquierda
        left = ttk.Frame(frm)
        left.pack(side="left", fill="both", expand=True, padx=(0,8))
        
        prev_path = row.get("preview_path") or ""
        self.img_label = ttk.Label(left, text="Sin vista previa disponible")
        self.img_label.pack(fill="both", expand=True)
        
        btns_left = ttk.Frame(left)
        btns_left.pack(fill="x", pady=5)
        ttk.Button(btns_left, text="Abrir original", command=self._open_original).pack(side="left")
        ttk.Button(btns_left, text="Abrir preview", command=self._open_preview).pack(side="left", padx=5)
        
        # Cargar imagen de preview si existe
        if prev_path and Path(prev_path).exists():
            try:
                pil = Image.open(prev_path)
                pil.thumbnail((900, 900))
                self.tkimg = ImageTk.PhotoImage(pil)
                self.img_label.configure(image=self.tkimg, text="")
            except Exception:
                pass
        
        # Campos a la derecha
        right = ttk.Frame(frm)
        right.pack(side="left", fill="both", expand=False)
        
        def add_row(lbl, var):
            r = ttk.Frame(right)
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=lbl, width=18, anchor="w").pack(side="left")
            e = ttk.Entry(r, textvariable=var, width=50)
            e.pack(side="left", fill="x", expand=True)
            return e
        
        self.var_nombre = tk.StringVar(value=row.get("nombre",""))
        self.var_rut = tk.StringVar(value=row.get("rut",""))
        self.var_folio = tk.StringVar(value=row.get("nro_boleta",""))
        self.var_fecha = tk.StringVar(value=row.get("fecha_documento",""))
        self.var_monto = tk.StringVar(value=row.get("monto",""))
        self.var_convenio = tk.StringVar(value=row.get("convenio",""))
        self.var_horas = tk.StringVar(value=row.get("horas",""))
        self.var_tipo = tk.StringVar(value=row.get("tipo",""))
        self.var_decreto = tk.StringVar(value=row.get("decreto_alcaldicio",""))
        
        # Mostrar información del archivo
        ttk.Label(right, text=f"Archivo:\n{row.get('archivo','')}", wraplength=380, justify="left").pack(fill="x", pady=4)
        
        add_row("Nombre:", self.var_nombre)
        add_row("RUT:", self.var_rut)
        add_row("Folio:", self.var_folio)
        add_row("Fecha (YYYY-MM-DD):", self.var_fecha)
        add_row("Monto bruto:", self.var_monto)
        add_row("Convenio:", self.var_convenio)
        add_row("Horas:", self.var_horas)
        add_row("Tipo:", self.var_tipo)
        add_row("Decreto Alcaldicio:", self.var_decreto)
        
        # Glosa como Text multilinea
        ttk.Label(right, text="Glosa:").pack(anchor="w")
        self.txt_glosa = tk.Text(right, height=6, width=60)
        self.txt_glosa.pack(fill="both", expand=False)
        self.txt_glosa.insert("1.0", row.get("glosa",""))
        
        # Botones
        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Guardar", command=self._on_save).pack(side="left")
        ttk.Button(btns, text="Omitir", command=self._on_skip).pack(side="left", padx=5)
        ttk.Button(btns, text="Cancelar", command=self._on_cancel).pack(side="left")
        
        self.grab_set()
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _open_original(self):
        p = self.row.get("archivo")
        if p and Path(p).exists():
            try:
                os.startfile(p)  # Windows
            except Exception:
                pass
    
    def _open_preview(self):
        p = self.row.get("preview_path")
        if p and Path(p).exists():
            try:
                os.startfile(p)
            except Exception:
                pass
    
    def _on_save(self):
        r = self.row.copy()
        r['nombre'] = self.var_nombre.get().strip()
        r['rut'] = self.var_rut.get().strip()
        r['nro_boleta'] = self.var_folio.get().strip()
        r['fecha_documento'] = self.var_fecha.get().strip()
        r['monto'] = normaliza_monto(self.var_monto.get())
        r['convenio'] = self.var_convenio.get().strip()
        r['horas'] = self.var_horas.get().strip()
        r['tipo'] = self.var_tipo.get().strip()
        r['decreto_alcaldicio'] = self.var_decreto.get().strip()
        r['glosa'] = self.txt_glosa.get("1.0", "end").strip()
        r['needs_review'] = False
        self.result = r
        self.destroy()
    
    def _on_skip(self):
        self.result = None
        self.destroy()
    
    def _on_cancel(self):
        self.result = None
        self.destroy()

class BoletasApp(tk.Tk):
    """Aplicación principal para procesamiento de boletas de honorarios"""
    
    def __init__(self):
        super().__init__()
        self.title("Lector de Boletas de Honorarios (OCR) - Chile v2.0")
        self.geometry("1200x800")
        self.minsize(1200, 800)
        
        # Variables de configuración
        self.root_dir = tk.StringVar(value=str(REGISTRO_DIR.resolve()))
        self.out_file = tk.StringVar(value=str((EXPORT_DIR / "boletas_procesadas.xlsx").resolve()))
        self.min_conf = tk.DoubleVar(value=0.60)
        self.var_manual_review = tk.BooleanVar(value=True)
        self.min_conf_review = tk.DoubleVar(value=OCR_CONFIDENCE_THRESHOLD)
        self.var_generate_reports = tk.BooleanVar(value=False)
        
        # Instanciar procesadores
        self.data_processor = DataProcessor()
        self.report_generator = ReportGenerator()
        
        # Estado de procesamiento
        self.processing = False
        self.thread = None
        self.job_result = None
        self.registros_final = []
        
        # Crear la interfaz
        self.create_widgets()
        
        # Verificar dependencias
        self.check_dependencies()
    
    def check_dependencies(self):
        """Verifica que las dependencias necesarias estén instaladas"""
        tesseract_cmd = detect_tesseract_cmd()
        poppler_bin = detect_poppler_bin()
        
        if not tesseract_cmd:
            messagebox.showwarning(
                "Tesseract no encontrado",
                "No se encontró Tesseract OCR. Por favor, instálalo desde:\n"
                "https://github.com/tesseract-ocr/tesseract\n\n"
                "O configura la variable de entorno TESSERACT_CMD"
            )
        
        if not poppler_bin:
            messagebox.showwarning(
                "Poppler no encontrado",
                "No se encontró Poppler (necesario para PDF). Por favor, instálalo desde:\n"
                "https://github.com/oschwartz10612/poppler-windows/releases\n\n"
                "O configura la variable de entorno POPPLER_PATH"
            )
    
    def create_widgets(self):
        """Crea todos los widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Notebook para pestañas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Pestaña de procesamiento
        process_tab = ttk.Frame(notebook)
        notebook.add(process_tab, text="Procesamiento")
        self.create_process_tab(process_tab)
        
        # Pestaña de configuración
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="Configuración")
        self.create_config_tab(config_tab)
        
        # Pestaña de ayuda
        help_tab = ttk.Frame(notebook)
        notebook.add(help_tab, text="Ayuda")
        self.create_help_tab(help_tab)
    
    def create_process_tab(self, parent):
        """Crea la pestaña de procesamiento"""
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)
        
        # Carpeta de entrada
        row1 = ttk.Frame(frm)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="Carpeta raíz a procesar:").pack(side="left")
        ttk.Entry(row1, textvariable=self.root_dir, width=60).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row1, text="Elegir...", command=self.select_root).pack(side="left")
        
        # Archivo de salida
        row2 = ttk.Frame(frm)
        row2.pack(fill="x", pady=5)
        ttk.Label(row2, text="Archivo de salida XLSX:").pack(side="left")
        ttk.Entry(row2, textvariable=self.out_file, width=60).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row2, text="Guardar como...", command=self.select_out).pack(side="left")
        
        # Opciones de procesamiento
        options_frame = ttk.LabelFrame(frm, text="Opciones de procesamiento", padding=10)
        options_frame.pack(fill="x", pady=10)
        
        # Primera fila de opciones
        opt_row1 = ttk.Frame(options_frame)
        opt_row1.pack(fill="x", pady=5)
        
        self.var_skip_low_conf = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_row1, text="Excluir registros con confianza <",
                       variable=self.var_skip_low_conf).pack(side="left")
        ttk.Spinbox(opt_row1, from_=0.0, to=0.99, increment=0.05,
                   textvariable=self.min_conf, width=5).pack(side="left", padx=(5, 10))
        ttk.Label(opt_row1, text="(recomendado 0.60)").pack(side="left")
        
        # Segunda fila de opciones
        opt_row2 = ttk.Frame(options_frame)
        opt_row2.pack(fill="x", pady=5)
        
        ttk.Checkbutton(opt_row2, text="Revisión manual automática", 
                       variable=self.var_manual_review).pack(side="left")
        ttk.Label(opt_row2, text="Conf. para revisión <").pack(side="left", padx=(10,2))
        ttk.Spinbox(opt_row2, from_=0.0, to=0.95, increment=0.05,
                   textvariable=self.min_conf_review, width=5).pack(side="left")
        ttk.Label(opt_row2, text="(y/o si faltan campos clave)").pack(side="left")
        
        # Tercera fila - NUEVA: Opción de informes
        opt_row3 = ttk.Frame(options_frame)
        opt_row3.pack(fill="x", pady=5)
        
        ttk.Checkbutton(opt_row3, text="Generar informes por convenio", 
                       variable=self.var_generate_reports,
                       command=self.on_report_toggle).pack(side="left")
        self.lbl_report_info = ttk.Label(opt_row3, 
                                        text="(Crea hojas adicionales con resúmenes mensuales por convenio)",
                                        foreground="gray")
        self.lbl_report_info.pack(side="left", padx=(10, 0))
        
        # Botones de control
        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_run = ttk.Button(btn_frame, text="Iniciar procesamiento", 
                                 command=self.on_run, style="Accent.TButton")
        self.btn_run.pack(side="left")
        
        self.btn_stop = ttk.Button(btn_frame, text="Detener", state="disabled",
                                  command=self.on_stop)
        self.btn_stop.pack(side="left", padx=10)
        
        ttk.Button(btn_frame, text="Salir", command=self.destroy).pack(side="right")
        
        # Barra de progreso
        prog_frame = ttk.Frame(frm)
        prog_frame.pack(fill="x", pady=5)
        
        self.pb = ttk.Progressbar(prog_frame, mode="determinate")
        self.pb.pack(fill="x")
        
        self.lbl_progress = ttk.Label(prog_frame, text="")
        self.lbl_progress.pack(pady=2)
        
        # Bitácora
        log_frame = ttk.Frame(frm)
        log_frame.pack(fill="both", expand=True, pady=8)
        
        ttk.Label(log_frame, text="Bitácora:").pack(anchor="w")
        
        # Frame para el Text y Scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.txt = tk.Text(text_frame, height=20, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=scrollbar.set)
        
        self.txt.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.txt.configure(state="disabled")
    
    def create_config_tab(self, parent):
        """Crea la pestaña de configuración"""
        frm = ttk.Frame(parent, padding=20)
        frm.pack(fill="both", expand=True)
        
        # Información del sistema
        info_frame = ttk.LabelFrame(frm, text="Información del sistema", padding=15)
        info_frame.pack(fill="x", pady=10)
        
        tesseract_cmd = detect_tesseract_cmd()
        poppler_bin = detect_poppler_bin()
        
        ttk.Label(info_frame, text=f"Tesseract: {tesseract_cmd or 'No encontrado'}").pack(anchor="w", pady=2)
        ttk.Label(info_frame, text=f"Poppler: {poppler_bin or 'No encontrado'}").pack(anchor="w", pady=2)
        ttk.Label(info_frame, text=f"Procesos paralelos: {MAX_WORKERS}").pack(anchor="w", pady=2)
        
        # Configuración de debug
        debug_frame = ttk.LabelFrame(frm, text="Debug", padding=15)
        debug_frame.pack(fill="x", pady=10)
        
        self.var_debug = tk.BooleanVar(value=DEBUG_SAVE_PREPROC)
        ttk.Checkbutton(debug_frame, text="Guardar imágenes de preprocesamiento",
                       variable=self.var_debug,
                       command=self.toggle_debug).pack(anchor="w")
        
        # Configuración de convenios
        conv_frame = ttk.LabelFrame(frm, text="Convenios conocidos", padding=15)
        conv_frame.pack(fill="x", pady=10)
        
        conv_text = ", ".join(KNOWN_CONVENIOS)
        ttk.Label(conv_frame, text=conv_text, wraplength=500).pack(anchor="w")
    
    def create_help_tab(self, parent):
        """Crea la pestaña de ayuda"""
        frm = ttk.Frame(parent, padding=20)
        frm.pack(fill="both", expand=True)
        
        help_text = """
        SISTEMA DE PROCESAMIENTO DE BOLETAS DE HONORARIOS
        ==================================================
        
        Este sistema procesa boletas de honorarios en formato PDF e imágenes,
        extrayendo automáticamente los siguientes campos:
        
        • Nombre del prestador de servicios
        • RUT
        • Número de boleta
        • Fecha del documento
        • Monto bruto
        • Convenio asociado
        • Horas trabajadas
        • Tipo de trabajo (mensual/semanal)
        • Glosa descriptiva
        • Decreto alcaldicio
        
        CARACTERÍSTICAS PRINCIPALES:
        ----------------------------
        • OCR automático con múltiples variantes de preprocesamiento
        • Detección inteligente de texto embebido en PDFs
        • Revisión manual asistida para casos dudosos
        • Generación de informes por convenio con resúmenes mensuales
        • Exportación a Excel con fórmulas dinámicas
        • Procesamiento paralelo para mayor velocidad
        
        FORMATOS SOPORTADOS:
        -------------------
        • PDF (con o sin texto embebido)
        • PNG, JPG, JPEG
        • TIF, TIFF
        • BMP
        
        REQUERIMIENTOS:
        --------------
        • Tesseract OCR 4.0 o superior
        • Poppler (para conversión de PDFs)
        • Python 3.7 o superior
        
        TIPS PARA MEJORES RESULTADOS:
        -----------------------------
        • Escanear documentos a 300 DPI mínimo
        • Evitar documentos muy inclinados o borrosos
        • Nombrar archivos con el nombre del prestador cuando sea posible
        • Mantener una estructura de carpetas organizada por mes/año
        
        INFORMES POR CONVENIO:
        ---------------------
        Cuando se activa la opción "Generar informes por convenio", el sistema:
        • Crea una hoja de Excel por cada convenio detectado
        • Organiza los datos mes a mes dentro de cada hoja
        • Calcula totales mensuales automáticamente
        • Genera una tabla resumen con estadísticas
        • Usa fórmulas dinámicas que se actualizan si modifica la base de datos
        
        Versión 2.0 - Sistema modular y escalable
        """
        
        text = tk.Text(frm, wrap="word", width=80)
        text.pack(fill="both", expand=True)
        text.insert("1.0", help_text)
        text.configure(state="disabled")
    
    def on_report_toggle(self):
        """Maneja el cambio en la opción de generar informes"""
        if self.var_generate_reports.get():
            self.lbl_report_info.configure(foreground="black")
        else:
            self.lbl_report_info.configure(foreground="gray")
    
    def toggle_debug(self):
        """Activa/desactiva el modo debug"""
        global DEBUG_SAVE_PREPROC
        DEBUG_SAVE_PREPROC = self.var_debug.get()
    
    def log(self, msg: str, level="INFO"):
        """Agrega un mensaje a la bitácora"""
        self.txt.configure(state="normal")
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "ERROR":
            self.txt.insert("end", f"[{timestamp}] ERROR: {msg}\n", "error")
        elif level == "WARNING":
            self.txt.insert("end", f"[{timestamp}] ADVERTENCIA: {msg}\n", "warning")
        elif level == "SUCCESS":
            self.txt.insert("end", f"[{timestamp}] ✓ {msg}\n", "success")
        else:
            self.txt.insert("end", f"[{timestamp}] {msg}\n")
        
        self.txt.see("end")
        self.txt.configure(state="disabled")
        self.update_idletasks()
    
    def select_root(self):
        """Selecciona la carpeta raíz a procesar"""
        d = filedialog.askdirectory(title="Selecciona la carpeta raíz")
        if d:
            self.root_dir.set(d)
    
    def select_out(self):
        """Selecciona el archivo de salida"""
        f = filedialog.asksaveasfilename(
            title="Selecciona archivo de salida",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if f:
            self.out_file.set(f)
    
    def on_run(self):
        """Inicia el procesamiento"""
        if self.processing:
            return
        
        root = self.root_dir.get().strip()
        out = self.out_file.get().strip()
        
        # Validaciones
        if not root or not Path(root).exists():
            messagebox.showerror("Error", "Selecciona una carpeta raíz válida.")
            return
        
        if not out.endswith(".xlsx"):
            messagebox.showerror("Error", "El archivo de salida debe terminar en .xlsx")
            return
        
        # Crear directorios necesarios
        Path(root).mkdir(parents=True, exist_ok=True)
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        
        # Iniciar procesamiento
        self.processing = True
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.pb['value'] = 0
        
        self.log("Iniciando procesamiento...")
        self.log(f"Carpeta: {root}")
        self.log(f"Archivo salida: {out}")
        self.log(f"Procesando en paralelo con {MAX_WORKERS} proceso(s)...")
        
        if self.var_generate_reports.get():
            self.log("Se generarán informes por convenio", "INFO")
        
        self.job_result = None
        self.thread = threading.Thread(target=self.run_job, daemon=True)
        self.thread.start()
        self.after(200, self.poll_thread)
    
    def on_stop(self):
        """Detiene el procesamiento"""
        # TODO: Implementar detención segura del procesamiento
        self.log("Deteniendo procesamiento...", "WARNING")
    
    def poll_thread(self):
        """Verifica el estado del hilo de procesamiento"""
        if self.thread is None:
            return
        
        if self.thread.is_alive():
            self.after(200, self.poll_thread)
        else:
            self.processing = False
            self.btn_run.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.log("Procesamiento automático finalizado.")
            
            # Después de terminar, manejar revisión manual si aplica
            self.after(10, self.after_job_complete)
    
    def run_job(self):
        """Ejecuta el trabajo de procesamiento en un hilo separado"""
        try:
            root_path = Path(self.root_dir.get())
            files = list(iter_files(root_path))
            total = len(files)
            
            if total == 0:
                self.log("No se encontraron archivos para procesar", "WARNING")
                self.job_result = dict(registros=[], review_queue=[], err_count=0, low_conf_count=0, total=0)
                return
            
            self.log(f"Se encontraron {total} archivo(s) para procesar")
            
            # Configuración
            skip_low_conf = self.var_skip_low_conf.get()
            min_conf = float(self.min_conf.get())
            manual_review = self.var_manual_review.get()
            min_conf_review = float(self.min_conf_review.get())
            
            # Estados
            registros = []
            review_queue = []
            low_conf_count = 0
            err_count = 0
            
            self.pb['maximum'] = total
            i = 0
            
            # Procesamiento paralelo
            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
                futs = {ex.submit(self.data_processor.process_file, f): f for f in files}
                
                for fut in as_completed(futs):
                    f = futs[fut]
                    i += 1
                    
                    try:
                        row = fut.result()
                        if row:
                            # Decidir si necesita revisión
                            send_to_review = manual_review and (
                                row.get('needs_review')
                                or (row.get('confianza', 0.0) < min_conf_review)
                            )
                            
                            if send_to_review:
                                review_queue.append(row)
                            else:
                                if skip_low_conf and row.get('confianza', 0.0) < min_conf:
                                    low_conf_count += 1
                                else:
                                    registros.append(row)
                        else:
                            err_count += 1
                            self.log(f"  ! Sin resultado: {f}", "ERROR")
                    
                    except Exception as e:
                        err_count += 1
                        self.log(f"  ! Error en {f}: {e}", "ERROR")
                    
                    self.pb['value'] = i
                    self.lbl_progress.configure(text=f"Progreso: {i}/{total}")
                    
                    if i % 5 == 0 or i == total:
                        self.log(f"Procesados: {i}/{total}")
                    
                    self.update_idletasks()
            
            self.job_result = dict(
                registros=registros,
                review_queue=review_queue,
                err_count=err_count,
                low_conf_count=low_conf_count,
                total=total
            )
            
        except Exception as e:
            self.job_result = dict(registros=[], review_queue=[], err_count=0, low_conf_count=0, total=0)
            self.log(f"Error crítico: {e}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")
    
    def after_job_complete(self):
        """Ejecuta después de completar el procesamiento"""
        if not self.job_result:
            self.log("No hay resultados para mostrar.", "WARNING")
            return
        
        registros = self.job_result['registros']
        review_queue = self.job_result['review_queue']
        err_count = self.job_result['err_count']
        low_conf_count = self.job_result['low_conf_count']
        
        # Revisión manual si procede
        reviewed_rows = []
        if self.var_manual_review.get() and review_queue:
            self.log(f"Revisión manual: {len(review_queue)} boleta(s) requieren revisión.")
            
            for idx, row in enumerate(review_queue):
                self.lbl_progress.configure(text=f"Revisando boleta {idx+1} de {len(review_queue)}")
                
                dlg = ReviewDialog(self, row)
                self.wait_window(dlg)
                
                if dlg.result:
                    reviewed_rows.append(dlg.result)
        
        # Unir todos los registros
        final_rows = registros + reviewed_rows
        
        if final_rows:
            # Generar el Excel
            if self.var_generate_reports.get():
                self.log("Generando informes por convenio...")
                df = self.report_generator.create_excel_with_reports(
                    final_rows, 
                    self.out_file.get(),
                    generate_reports=True
                )
            else:
                # Solo generar la hoja principal
                df = self.report_generator.create_excel_with_reports(
                    final_rows, 
                    self.out_file.get(),
                    generate_reports=False
                )
            
            self.log(f"Guardado: {self.out_file.get()}", "SUCCESS")
            self.log(f"Registros totales exportados: {len(df)}", "SUCCESS")
            
            # Estadísticas finales
            convenios_unicos = df[df['convenio'] != '']['convenio'].nunique()
            if convenios_unicos > 0 and self.var_generate_reports.get():
                self.log(f"Se generaron informes para {convenios_unicos} convenio(s)", "SUCCESS")
            
        else:
            self.log("No hubo registros válidos para exportar.", "WARNING")
        
        # Estadísticas finales
        if self.var_skip_low_conf.get() and low_conf_count:
            self.log(f"Registros descartados por baja confianza: {low_conf_count}", "WARNING")
        
        if err_count:
            self.log(f"Archivos con error: {err_count}", "WARNING")
        
        self.log("Proceso finalizado.", "SUCCESS")
        self.lbl_progress.configure(text="")

def main():
    """Función principal"""
    app = BoletasApp()
    
    # Configurar estilos para los tags del texto
    app.txt.tag_config("error", foreground="red")
    app.txt.tag_config("warning", foreground="orange")
    app.txt.tag_config("success", foreground="green")
    
    app.mainloop()

if __name__ == "__main__":
    main()

