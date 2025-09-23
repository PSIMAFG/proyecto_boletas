# SPDX-License-Identifier: BUSL-1.1
# © 2025 Matías A. Fernández

# main_enhanced.py
"""
Aplicación principal mejorada con soporte multi-motor OCR y visualización de versiones
Versión 3.0
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

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

# Importar configuración y módulos
from config import *
from modules.utils import *
from modules.ocr_extraction_enhanced import EnhancedOCRExtractor, PaddleOCRWrapper
from modules.data_processing import DataProcessor
from modules.report_generator import ReportGenerator

class EnhancedReviewDialog(tk.Toplevel):
    """Diálogo de revisión manual mejorado con visualización de múltiples versiones"""
    
    def __init__(self, master, row: dict):
        super().__init__(master)
        self.title("Revisión manual de boleta - Vista mejorada")
        self.resizable(True, True)
        self.state('zoomed')  # Maximizar ventana
        
        self.row = row.copy()
        self.result = None
        self.current_version_idx = 0
        self.versions = row.get('versions', {})
        self.version_list = list(self.versions.keys()) if self.versions else []
        
        self.create_widgets()
        self.load_version(0)
        
        self.grab_set()
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def create_widgets(self):
        """Crea los widgets del diálogo"""
        main_frame = ttk.Frame(self, padding=8)
        main_frame.pack(fill="both", expand=True)
        
        # Panel izquierdo - Visualización de imágenes
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0,8))
        
        # Controles de versión
        version_frame = ttk.Frame(left_panel)
        version_frame.pack(fill="x", pady=(0,5))
        
        ttk.Label(version_frame, text="Versión:").pack(side="left")
        self.version_label = ttk.Label(version_frame, text="", font=('', 10, 'bold'))
        self.version_label.pack(side="left", padx=10)
        
        ttk.Button(version_frame, text="◀ Anterior", 
                  command=self.prev_version).pack(side="left", padx=2)
        ttk.Button(version_frame, text="Siguiente ▶", 
                  command=self.next_version).pack(side="left", padx=2)
        
        # Selector de versión
        self.version_combo = ttk.Combobox(version_frame, values=self.version_list, 
                                         state="readonly", width=30)
        self.version_combo.pack(side="left", padx=10)
        self.version_combo.bind('<<ComboboxSelected>>', self.on_version_selected)
        
        # Botones de archivo
        ttk.Button(version_frame, text="📁 Abrir original", 
                  command=self._open_original).pack(side="right", padx=2)
        ttk.Button(version_frame, text="📁 Abrir carpeta versiones",
                  command=self._open_versions_folder).pack(side="right", padx=2)
        
        # Controles de rotación
        rotation_frame = ttk.Frame(left_panel)
        rotation_frame.pack(fill="x", pady=(0,5))
        
        ttk.Label(rotation_frame, text="Rotación:").pack(side="left")
        ttk.Button(rotation_frame, text="↺ 90°", 
                  command=lambda: self.rotate_image(90)).pack(side="left", padx=2)
        ttk.Button(rotation_frame, text="↻ -90°", 
                  command=lambda: self.rotate_image(-90)).pack(side="left", padx=2)
        ttk.Button(rotation_frame, text="↕ 180°", 
                  command=lambda: self.rotate_image(180)).pack(side="left", padx=2)
        
        # Canvas con scrollbars para la imagen
        canvas_frame = ttk.Frame(left_panel)
        canvas_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="gray90")
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Panel derecho - Campos de datos
        right_panel = ttk.Frame(main_frame, width=500)
        right_panel.pack(side="left", fill="both", expand=False)
        
        # Información del archivo y motor OCR
        info_frame = ttk.LabelFrame(right_panel, text="Información del procesamiento", padding=5)
        info_frame.pack(fill="x", pady=(0,10))
        
        ttk.Label(info_frame, text=f"Archivo: {Path(self.row.get('archivo','')).name}").pack(anchor="w")
        
        engine_info = self.row.get('ocr_engine', 'desconocido')
        confidence = self.row.get('confianza', 0)
        ttk.Label(info_frame, text=f"Motor OCR: {engine_info} | Confianza: {confidence:.2%}").pack(anchor="w")
        
        # Frame para los campos
        fields_frame = ttk.Frame(right_panel)
        fields_frame.pack(fill="both", expand=True)
        
        # Crear campos de entrada
        self.create_input_fields(fields_frame)
        
        # Botones de acción
        btn_frame = ttk.Frame(right_panel)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="💾 Guardar", command=self._on_save,
                  style="Accent.TButton").pack(side="left", padx=2)
        ttk.Button(btn_frame, text="⏭ Omitir", command=self._on_skip).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="🔄 Reprocesar con PaddleOCR", 
                  command=self._reprocess_paddle).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="❌ Cancelar", command=self._on_cancel).pack(side="right", padx=2)
        
        # Estado y sugerencias
        self.status_label = ttk.Label(right_panel, text="", foreground="blue")
        self.status_label.pack(fill="x", pady=5)
        
        # Configurar zoom con rueda del mouse
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        
        self.zoom_level = 1.0
        self.canvas_image = None
        self.current_pil_image = None
    
    def create_input_fields(self, parent):
        """Crea los campos de entrada"""
        def add_row(lbl, var, row_num):
            ttk.Label(parent, text=lbl, width=18, anchor="w").grid(row=row_num, column=0, sticky="w", pady=2)
            entry = ttk.Entry(parent, textvariable=var, width=45)
            entry.grid(row=row_num, column=1, sticky="ew", pady=2)
            return entry
        
        # Variables de entrada
        self.var_nombre = tk.StringVar(value=self.row.get("nombre",""))
        self.var_rut = tk.StringVar(value=self.row.get("rut",""))
        self.var_folio = tk.StringVar(value=self.row.get("nro_boleta",""))
        self.var_fecha = tk.StringVar(value=self.row.get("fecha_documento",""))
        self.var_monto = tk.StringVar(value=self.row.get("monto",""))
        self.var_convenio = tk.StringVar(value=self.row.get("convenio",""))
        self.var_horas = tk.StringVar(value=self.row.get("horas",""))
        self.var_tipo = tk.StringVar(value=self.row.get("tipo",""))
        self.var_decreto = tk.StringVar(value=self.row.get("decreto_alcaldicio",""))
        
        # Crear campos
        r = 0
        add_row("Nombre:", self.var_nombre, r); r += 1
        add_row("RUT:", self.var_rut, r); r += 1
        add_row("N° Boleta:", self.var_folio, r); r += 1
        add_row("Fecha (YYYY-MM-DD):", self.var_fecha, r); r += 1
        add_row("Monto bruto:", self.var_monto, r); r += 1
        add_row("Convenio:", self.var_convenio, r); r += 1
        add_row("Horas:", self.var_horas, r); r += 1
        add_row("Tipo:", self.var_tipo, r); r += 1
        add_row("Decreto Alcaldicio:", self.var_decreto, r); r += 1
        
        # Glosa (campo de texto multilínea)
        ttk.Label(parent, text="Glosa:").grid(row=r, column=0, sticky="nw", pady=2)
        
        glosa_frame = ttk.Frame(parent)
        glosa_frame.grid(row=r, column=1, sticky="ew", pady=2)
        
        self.txt_glosa = tk.Text(glosa_frame, height=6, width=45)
        glosa_scroll = ttk.Scrollbar(glosa_frame, orient="vertical", command=self.txt_glosa.yview)
        self.txt_glosa.configure(yscrollcommand=glosa_scroll.set)
        
        self.txt_glosa.pack(side="left", fill="both", expand=True)
        glosa_scroll.pack(side="right", fill="y")
        
        self.txt_glosa.insert("1.0", self.row.get("glosa",""))
        
        # Configurar expansión de columnas
        parent.columnconfigure(1, weight=1)
    
    def load_version(self, idx):
        """Carga una versión específica de la imagen"""
        if not self.version_list or idx >= len(self.version_list):
            # Si no hay versiones, cargar imagen original o preview
            img_path = self.row.get('preview_path') or self.row.get('archivo')
            if img_path and Path(img_path).exists():
                self.load_image(img_path)
            else:
                self.canvas.delete("all")
                self.canvas.create_text(400, 300, text="Sin imagen disponible", 
                                       font=('Arial', 20), fill='gray')
            return
        
        version_key = self.version_list[idx]
        version_path = self.versions.get(version_key)
        
        if version_path and Path(version_path).exists():
            self.load_image(version_path)
            self.version_label.config(text=version_key)
            self.version_combo.set(version_key)
            self.current_version_idx = idx
        else:
            self.status_label.config(text=f"No se encontró la imagen: {version_path}")
    
    def load_image(self, path):
        """Carga una imagen en el canvas"""
        try:
            self.current_pil_image = Image.open(path)
            self.display_image()
            self.status_label.config(text=f"Imagen cargada: {Path(path).name}")
        except Exception as e:
            self.status_label.config(text=f"Error cargando imagen: {e}", foreground="red")
    
    def display_image(self):
        """Muestra la imagen actual con el nivel de zoom"""
        if not self.current_pil_image:
            return
        
        # Calcular nuevo tamaño con zoom
        width = int(self.current_pil_image.width * self.zoom_level)
        height = int(self.current_pil_image.height * self.zoom_level)
        
        # Redimensionar imagen
        resized = self.current_pil_image.resize((width, height), Image.Resampling.LANCZOS)
        
        # Convertir a PhotoImage
        self.tk_image = ImageTk.PhotoImage(resized)
        
        # Actualizar canvas
        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
    
    def rotate_image(self, angle):
        """Rota la imagen actual"""
        if not self.current_pil_image:
            return
        
        if angle == 90:
            self.current_pil_image = self.current_pil_image.rotate(-90, expand=True)
        elif angle == -90:
            self.current_pil_image = self.current_pil_image.rotate(90, expand=True)
        elif angle == 180:
            self.current_pil_image = self.current_pil_image.rotate(180, expand=True)
        
        self.display_image()
        self.status_label.config(text=f"Imagen rotada {angle}°")
    
    def on_zoom(self, event):
        """Maneja el zoom con la rueda del mouse"""
        # Zoom in/out
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level /= 1.1
        
        # Limitar zoom
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        
        self.display_image()
        self.status_label.config(text=f"Zoom: {self.zoom_level:.1%}")
    
    def on_canvas_click(self, event):
        """Maneja click en el canvas para arrastrar"""
        self.canvas.scan_mark(event.x, event.y)
    
    def on_canvas_drag(self, event):
        """Maneja arrastre en el canvas"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def prev_version(self):
        """Muestra la versión anterior"""
        if self.version_list and self.current_version_idx > 0:
            self.load_version(self.current_version_idx - 1)
    
    def next_version(self):
        """Muestra la siguiente versión"""
        if self.version_list and self.current_version_idx < len(self.version_list) - 1:
            self.load_version(self.current_version_idx + 1)
    
    def on_version_selected(self, event):
        """Maneja la selección de versión del combo"""
        selected = self.version_combo.get()
        if selected in self.version_list:
            idx = self.version_list.index(selected)
            self.load_version(idx)
    
    def _open_original(self):
        """Abre el archivo original"""
        p = self.row.get("archivo")
        if p and Path(p).exists():
            try:
                os.startfile(p)  # Windows
            except:
                import subprocess
                subprocess.run(['open', p])  # Mac/Linux
    
    def _open_versions_folder(self):
        """Abre la carpeta con todas las versiones"""
        if self.versions:
            # Obtener carpeta de la primera versión
            first_version = list(self.versions.values())[0]
            folder = Path(first_version).parent
            if folder.exists():
                try:
                    os.startfile(str(folder))  # Windows
                except:
                    import subprocess
                    subprocess.run(['open', str(folder)])  # Mac/Linux
    
    def _reprocess_paddle(self):
        """Reprocesa la imagen con PaddleOCR"""
        self.status_label.config(text="Reprocesando con PaddleOCR...", foreground="orange")
        self.update()
        
        try:
            # Crear extractor con PaddleOCR
            extractor = EnhancedOCRExtractor(OCREngine.PADDLEOCR)
            
            # Procesar archivo
            file_path = Path(self.row.get("archivo"))
            if file_path.suffix.lower() == '.pdf':
                result = extractor.process_pdf_multi_engine(file_path)
                text = "\n".join(result['texts'])
            else:
                result = extractor.process_image_multi_engine(file_path)
                text = result['text']
            
            # Extraer campos con el nuevo texto
            processor = DataProcessor()
            fields = processor.extract_fields_from_text(text, file_path)
            
            # Actualizar campos en la GUI
            self.var_nombre.set(fields.get('nombre', ''))
            self.var_rut.set(fields.get('rut', ''))
            self.var_folio.set(fields.get('nro_boleta', ''))
            self.var_fecha.set(fields.get('fecha_documento', ''))
            self.var_monto.set(fields.get('monto', ''))
            self.var_convenio.set(fields.get('convenio', ''))
            self.var_horas.set(fields.get('horas', ''))
            self.var_tipo.set(fields.get('tipo', ''))
            self.var_decreto.set(fields.get('decreto_alcaldicio', ''))
            self.txt_glosa.delete("1.0", "end")
            self.txt_glosa.insert("1.0", fields.get('glosa', ''))
            
            # Actualizar versiones si hay nuevas
            if 'versions' in result:
                self.versions.update(result['versions'])
                self.version_list = list(self.versions.keys())
                self.version_combo['values'] = self.version_list
            
            self.status_label.config(text="✓ Reprocesado con PaddleOCR exitosamente", foreground="green")
            
        except Exception as e:
            self.status_label.config(text=f"Error al reprocesar: {e}", foreground="red")
    
    def _on_save(self):
        """Guarda los cambios"""
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
        r['manually_reviewed'] = True
        self.result = r
        self.destroy()
    
    def _on_skip(self):
        """Omite este registro"""
        self.result = None
        self.destroy()
    
    def _on_cancel(self):
        """Cancela la revisión"""
        self.result = None
        self.destroy()


class EnhancedBoletasApp(tk.Tk):
    """Aplicación principal mejorada con soporte multi-motor OCR"""
    
    def __init__(self):
        super().__init__()
        self.title("Sistema de Boletas de Honorarios v3.0 - Multi-Motor OCR")
        self.geometry("1400x900")
        self.minsize(1200, 800)
        
        # Variables de configuración
        self.root_dir = tk.StringVar(value=str(REGISTRO_DIR.resolve()))
        self.out_file = tk.StringVar(value=str((EXPORT_DIR / "boletas_procesadas.xlsx").resolve()))
        self.min_conf = tk.DoubleVar(value=0.60)
        self.var_manual_review = tk.BooleanVar(value=True)
        self.min_conf_review = tk.DoubleVar(value=OCR_CONFIDENCE_THRESHOLD)
        self.var_generate_reports = tk.BooleanVar(value=False)
        self.var_save_versions = tk.BooleanVar(value=SAVE_ALL_VERSIONS)
        
        # Variable para motor OCR
        self.ocr_engine = tk.StringVar(value=DEFAULT_OCR_ENGINE.value)
        
        # Instanciar procesadores
        self.report_generator = ReportGenerator()
        
        # Estado de procesamiento
        self.processing = False
        self.thread = None
        self.job_result = None
        
        # Crear la interfaz
        self.create_widgets()
        
        # Verificar dependencias
        self.check_dependencies()
    
    def check_dependencies(self):
        """Verifica las dependencias del sistema"""
        status_items = []
        
        # Verificar Tesseract
        tesseract_cmd = detect_tesseract_cmd()
        if tesseract_cmd:
            status_items.append(("Tesseract", "✓ Instalado", "green"))
        else:
            status_items.append(("Tesseract", "✗ No encontrado", "red"))
        
        # Verificar PaddleOCR
        paddle = PaddleOCRWrapper()
        if paddle.is_available():
            status_items.append(("PaddleOCR", "✓ Instalado", "green"))
        else:
            status_items.append(("PaddleOCR", "✗ No encontrado", "orange"))
        
        # Verificar Poppler
        poppler_bin = detect_poppler_bin()
        if poppler_bin:
            status_items.append(("Poppler", "✓ Instalado", "green"))
        else:
            status_items.append(("Poppler", "⚠ No encontrado (PDF limitado)", "orange"))
        
        # Actualizar etiquetas de estado
        for i, (name, status, color) in enumerate(status_items):
            if hasattr(self, 'status_labels'):
                self.status_labels[i].config(text=f"{name}: {status}", foreground=color)
    
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
        notebook.add(process_tab, text="📄 Procesamiento")
        self.create_process_tab(process_tab)
        
        # Pestaña de configuración
        config_tab = ttk.Frame(notebook)
        notebook.add(config_tab, text="⚙ Configuración")
        self.create_config_tab(config_tab)
        
        # Pestaña de ayuda
        help_tab = ttk.Frame(notebook)
        notebook.add(help_tab, text="❓ Ayuda")
        self.create_help_tab(help_tab)
    
    def create_process_tab(self, parent):
        """Crea la pestaña de procesamiento"""
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)
        
        # Frame superior para rutas
        paths_frame = ttk.LabelFrame(frm, text="Rutas", padding=10)
        paths_frame.pack(fill="x", pady=(0, 10))
        
        # Carpeta de entrada
        row1 = ttk.Frame(paths_frame)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="Carpeta a procesar:", width=20).pack(side="left")
        ttk.Entry(row1, textvariable=self.root_dir, width=50).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(row1, text="Elegir...", command=self.select_root).pack(side="left")
        
        # Archivo de salida
        row2 = ttk.Frame(paths_frame)
        row2.pack(fill="x", pady=5)
        ttk.Label(row2, text="Archivo de salida:", width=20).pack(side="left")
        ttk.Entry(row2, textvariable=self.out_file, width=50).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(row2, text="Guardar como...", command=self.select_out).pack(side="left")
        
        # Frame de opciones de OCR
        ocr_frame = ttk.LabelFrame(frm, text="Motor OCR", padding=10)
        ocr_frame.pack(fill="x", pady=(0, 10))
        
        ocr_options = ttk.Frame(ocr_frame)
        ocr_options.pack(fill="x")
        
        ttk.Label(ocr_options, text="Motor OCR:").pack(side="left", padx=(0, 10))
        
        ttk.Radiobutton(ocr_options, text="Tesseract", 
                       variable=self.ocr_engine, value="tesseract").pack(side="left", padx=5)
        ttk.Radiobutton(ocr_options, text="PaddleOCR", 
                       variable=self.ocr_engine, value="paddleocr").pack(side="left", padx=5)
        ttk.Radiobutton(ocr_options, text="Auto (Tesseract → PaddleOCR)", 
                       variable=self.ocr_engine, value="auto").pack(side="left", padx=5)
        
        # Estado de motores
        self.status_labels = []
        status_frame = ttk.Frame(ocr_frame)
        status_frame.pack(fill="x", pady=5)
        
        for i in range(3):  # Tesseract, PaddleOCR, Poppler
            label = ttk.Label(status_frame, text="")
            label.pack(side="left", padx=10)
            self.status_labels.append(label)
        
        # Opciones de procesamiento
        options_frame = ttk.LabelFrame(frm, text="Opciones de procesamiento", padding=10)
        options_frame.pack(fill="x", pady=(0, 10))
        
        # Primera fila
        opt_row1 = ttk.Frame(options_frame)
        opt_row1.pack(fill="x", pady=3)
        
        self.var_skip_low_conf = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_row1, text="Excluir registros con confianza <",
                       variable=self.var_skip_low_conf).pack(side="left")
        ttk.Spinbox(opt_row1, from_=0.0, to=0.99, increment=0.05,
                   textvariable=self.min_conf, width=5).pack(side="left", padx=5)
        
        # Segunda fila
        opt_row2 = ttk.Frame(options_frame)
        opt_row2.pack(fill="x", pady=3)
        
        ttk.Checkbutton(opt_row2, text="Revisión manual automática", 
                       variable=self.var_manual_review).pack(side="left")
        ttk.Label(opt_row2, text="Umbral:").pack(side="left", padx=(10,2))
        ttk.Spinbox(opt_row2, from_=0.0, to=0.95, increment=0.05,
                   textvariable=self.min_conf_review, width=5).pack(side="left")
        
        # Tercera fila
        opt_row3 = ttk.Frame(options_frame)
        opt_row3.pack(fill="x", pady=3)
        
        ttk.Checkbutton(opt_row3, text="Generar informes por convenio", 
                       variable=self.var_generate_reports).pack(side="left")
        ttk.Checkbutton(opt_row3, text="Guardar todas las versiones de imágenes",
                       variable=self.var_save_versions).pack(side="left", padx=20)
        
        # Botones de control
        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_run = ttk.Button(btn_frame, text="▶ Iniciar procesamiento", 
                                 command=self.on_run)
        self.btn_run.pack(side="left")
        
        self.btn_stop = ttk.Button(btn_frame, text="⏹ Detener", state="disabled")
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
        log_frame.pack(fill="both", expand=True)
        
        ttk.Label(log_frame, text="Bitácora:").pack(anchor="w")
        
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.txt = tk.Text(text_frame, height=15, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=scrollbar.set)
        
        self.txt.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.txt.configure(state="disabled")
        
        # Configurar tags para colores
        self.txt.tag_config("error", foreground="red")
        self.txt.tag_config("warning", foreground="orange")
        self.txt.tag_config("success", foreground="green")
        self.txt.tag_config("info", foreground="blue")
    
    def create_config_tab(self, parent):
        """Crea la pestaña de configuración"""
        frm = ttk.Frame(parent, padding=20)
        frm.pack(fill="both", expand=True)
        
        # Información del sistema
        info_frame = ttk.LabelFrame(frm, text="Información del sistema", padding=15)
        info_frame.pack(fill="x", pady=10)
        
        ttk.Label(info_frame, text=f"Procesadores paralelos: {MAX_WORKERS}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Carpeta de versiones: {VERSIONS_DIR}").pack(anchor="w")
        ttk.Label(info_frame, text=f"DPI para OCR: {OCR_DPI}").pack(anchor="w")
        
        # Configuración de timeouts
        timeout_frame = ttk.LabelFrame(frm, text="Timeouts (segundos)", padding=15)
        timeout_frame.pack(fill="x", pady=10)
        
        ttk.Label(timeout_frame, text=f"Tesseract: {TESSERACT_TIMEOUT}s").pack(anchor="w")
        ttk.Label(timeout_frame, text=f"PaddleOCR: {PADDLE_TIMEOUT}s").pack(anchor="w")
        
        # Configuración de PaddleOCR
        paddle_frame = ttk.LabelFrame(frm, text="Configuración PaddleOCR", padding=15)
        paddle_frame.pack(fill="x", pady=10)
        
        ttk.Label(paddle_frame, text=f"GPU: {'Sí' if PADDLE_CONFIG['use_gpu'] else 'No'}").pack(anchor="w")
        ttk.Label(paddle_frame, text=f"Detección de ángulo: {'Sí' if PADDLE_CONFIG['use_angle_cls'] else 'No'}").pack(anchor="w")
        ttk.Label(paddle_frame, text=f"Idioma: {PADDLE_CONFIG['lang']}").pack(anchor="w")
    
    def create_help_tab(self, parent):
        """Crea la pestaña de ayuda"""
        frm = ttk.Frame(parent, padding=20)
        frm.pack(fill="both", expand=True)
        
        help_text = """
        SISTEMA DE PROCESAMIENTO DE BOLETAS v3.0
        =========================================
        
        MEJORAS EN ESTA VERSIÓN:
        ------------------------
        • Soporte para PaddleOCR además de Tesseract
        • Modo AUTO que intenta Tesseract primero y luego PaddleOCR si falla
        • Guardado de todas las versiones procesadas de las imágenes
        • Visualización mejorada en revisión manual con:
          - Navegación entre versiones
          - Rotación manual de imágenes
          - Zoom con Ctrl+Rueda del mouse
          - Reprocesamiento con PaddleOCR desde el diálogo
        
        MOTORES OCR:
        -----------
        • TESSERACT: Rápido y preciso para documentos bien escaneados
        • PADDLEOCR: Mejor para imágenes con bajo contraste o distorsión
        • AUTO: Intenta Tesseract primero, si falla usa PaddleOCR
        
        INSTALACIÓN DE PADDLEOCR:
        ------------------------
        pip install paddlepaddle paddleocr
        
        Para GPU (CUDA):
        pip install paddlepaddle-gpu paddleocr
        
        SOLUCIÓN DE PROBLEMAS:
        ---------------------
        • Si las imágenes se distorsionan: Usar modo "original" en las versiones
        • Si el texto no se detecta: Probar con PaddleOCR
        • Si hay problemas de orientación: Usar los botones de rotación en revisión
        • Para documentos de baja calidad: Preferir PaddleOCR
        
        TIPS PARA MEJOR RENDIMIENTO:
        ---------------------------
        • Escanear a 300 DPI (no más de 350)
        • Usar modo AUTO para procesamiento inteligente
        • Activar "Guardar todas las versiones" para revisión posterior
        • En revisión manual, navegar entre versiones para encontrar la mejor
        
        Versión 3.0 - Sistema Multi-Motor con gestión de versiones
        """
        
        text = tk.Text(frm, wrap="word")
        text.pack(fill="both", expand=True)
        text.insert("1.0", help_text)
        text.configure(state="disabled")
    
    def log(self, msg: str, level="INFO"):
        """Agrega un mensaje a la bitácora"""
        self.txt.configure(state="normal")
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        tag = None
        prefix = ""
        
        if level == "ERROR":
            tag = "error"
            prefix = "✗"
        elif level == "WARNING":
            tag = "warning"
            prefix = "⚠"
        elif level == "SUCCESS":
            tag = "success"
            prefix = "✓"
        elif level == "INFO":
            tag = "info"
            prefix = "ℹ"
        
        full_msg = f"[{timestamp}] {prefix} {msg}\n"
        
        if tag:
            self.txt.insert("end", full_msg, tag)
        else:
            self.txt.insert("end", full_msg)
        
        self.txt.see("end")
        self.txt.configure(state="disabled")
        self.update_idletasks()
    
    def select_root(self):
        """Selecciona la carpeta raíz"""
        d = filedialog.askdirectory(title="Selecciona la carpeta con las boletas")
        if d:
            self.root_dir.set(d)
    
    def select_out(self):
        """Selecciona el archivo de salida"""
        f = filedialog.asksaveasfilename(
            title="Guardar resultados como",
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
            messagebox.showerror("Error", "Selecciona una carpeta válida")
            return
        
        if not out.endswith(".xlsx"):
            messagebox.showerror("Error", "El archivo debe ser .xlsx")
            return
        
        # Actualizar configuración global
        global SAVE_ALL_VERSIONS
        SAVE_ALL_VERSIONS = self.var_save_versions.get()
        
        # Iniciar procesamiento
        self.processing = True
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.pb['value'] = 0
        
        self.log("Iniciando procesamiento...")
        self.log(f"Motor OCR: {self.ocr_engine.get().upper()}", "INFO")
        self.log(f"Carpeta: {root}")
        self.log(f"Archivo salida: {out}")
        
        self.job_result = None
        self.thread = threading.Thread(target=self.run_job, daemon=True)
        self.thread.start()
        self.after(200, self.poll_thread)
    
    def poll_thread(self):
        """Verifica el estado del hilo"""
        if self.thread is None:
            return
        
        if self.thread.is_alive():
            self.after(200, self.poll_thread)
        else:
            self.processing = False
            self.btn_run.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.log("Procesamiento automático completado")
            self.after(10, self.after_job_complete)
    
    def run_job(self):
        """Ejecuta el trabajo de procesamiento (continuará en siguiente artifact)"""
        try:
            from modules.data_processing import DataProcessor
            
            # Configurar motor OCR
            engine_map = {
                'tesseract': OCREngine.TESSERACT,
                'paddleocr': OCREngine.PADDLEOCR,
                'auto': OCREngine.AUTO
            }
            selected_engine = engine_map[self.ocr_engine.get()]
            
            # Crear procesador con motor seleccionado
            processor = DataProcessor()
            processor.ocr_extractor = EnhancedOCRExtractor(selected_engine)
            
            root_path = Path(self.root_dir.get())
            files = list(iter_files(root_path))
            total = len(files)
            
            if total == 0:
                self.log("No se encontraron archivos", "WARNING")
                self.job_result = dict(registros=[], review_queue=[], err_count=0, low_conf_count=0, total=0)
                return
            
            self.log(f"Procesando {total} archivos...")
            
            # Configuración
            skip_low_conf = self.var_skip_low_conf.get()
            min_conf = float(self.min_conf.get())
            manual_review = self.var_manual_review.get()
            min_conf_review = float(self.min_conf_review.get())
            
            registros = []
            review_queue = []
            low_conf_count = 0
            err_count = 0
            
            self.pb['maximum'] = total
            
            # Procesar archivos secuencialmente (para mejor control con múltiples motores)
            for i, file_path in enumerate(files, 1):
                try:
                    self.lbl_progress.configure(text=f"Procesando {i}/{total}: {file_path.name}")
                    
                    # Procesar archivo
                    row = processor.process_file(file_path)
                    row['ocr_engine'] = selected_engine.value
                    
                    if row:
                        # Decidir si necesita revisión
                        needs_review = manual_review and (
                            row.get('needs_review') or 
                            row.get('confianza', 0.0) < min_conf_review
                        )
                        
                        if needs_review:
                            review_queue.append(row)
                        else:
                            if skip_low_conf and row.get('confianza', 0.0) < min_conf:
                                low_conf_count += 1
                            else:
                                registros.append(row)
                    else:
                        err_count += 1
                        
                except Exception as e:
                    err_count += 1
                    self.log(f"Error en {file_path.name}: {e}", "ERROR")
                
                self.pb['value'] = i
                
                if i % 10 == 0:
                    self.log(f"Progreso: {i}/{total}")
                
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
            import traceback
            self.log(traceback.format_exc(), "ERROR")
    
    def after_job_complete(self):
        """Ejecuta después de completar el procesamiento"""
        if not self.job_result:
            return
        
        registros = self.job_result['registros']
        review_queue = self.job_result['review_queue']
        err_count = self.job_result['err_count']
        low_conf_count = self.job_result['low_conf_count']
        
        # Revisión manual
        reviewed_rows = []
        if self.var_manual_review.get() and review_queue:
            self.log(f"Iniciando revisión manual de {len(review_queue)} boletas...")
            
            for idx, row in enumerate(review_queue):
                self.lbl_progress.configure(text=f"Revisando {idx+1}/{len(review_queue)}")
                
                dlg = EnhancedReviewDialog(self, row)
                self.wait_window(dlg)
                
                if dlg.result:
                    reviewed_rows.append(dlg.result)
        
        # Combinar resultados
        final_rows = registros + reviewed_rows
        
        if final_rows:
            # Generar Excel
            if self.var_generate_reports.get():
                self.log("Generando informes por convenio...")
                df = self.report_generator.create_excel_with_reports(
                    final_rows,
                    self.out_file.get(),
                    generate_reports=True
                )
            else:
                df = self.report_generator.create_excel_with_reports(
                    final_rows,
                    self.out_file.get(),
                    generate_reports=False
                )
            
            self.log(f"Archivo guardado: {self.out_file.get()}", "SUCCESS")
            self.log(f"Total procesados: {len(df)}", "SUCCESS")
            
        else:
            self.log("No hay registros para exportar", "WARNING")
        
        # Estadísticas
        if err_count:
            self.log(f"Archivos con error: {err_count}", "WARNING")
        if low_conf_count:
            self.log(f"Descartados por baja confianza: {low_conf_count}", "WARNING")
        
        self.log("✓ Proceso completado", "SUCCESS")
        self.lbl_progress.configure(text="")


def main():
    """Función principal"""
    app = EnhancedBoletasApp()
    app.mainloop()


if __name__ == "__main__":
    main()

