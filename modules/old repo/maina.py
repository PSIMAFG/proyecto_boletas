#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sistema de Procesamiento de Boletas de Honorarios v3.0
Con instalación automática y manejo inteligente de dependencias
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

# ============================================================================
# CONFIGURACIÓN DE VERSIONES Y COMPATIBILIDAD
# ============================================================================

PYTHON_MIN_VERSION = (3, 8)
PYTHON_MAX_VERSION = (3, 11)  # PaddleOCR no funciona bien en 3.12+
PYTHON_RECOMMENDED = "3.10"

# ============================================================================
# VERIFICADOR DE SISTEMA Y AUTO-INSTALADOR
# ============================================================================

class SystemChecker:
    """Verificador y configurador automático del sistema"""
    
    def __init__(self):
        self.python_version = sys.version_info
        self.is_windows = platform.system() == 'Windows'
        self.base_dir = Path(__file__).parent
        self.venv_dir = self.base_dir / "venv_boletas"
        self.requirements_file = self.base_dir / "requirements_auto.txt"
        self.has_paddle = False
        self.has_tesseract = False
        
    def check_python_version(self):
        """Verifica que Python esté en el rango compatible"""
        print("=" * 70)
        print("VERIFICACIÓN DE SISTEMA")
        print("=" * 70)
        print(f"Python detectado: {sys.version}")
        
        if self.python_version < PYTHON_MIN_VERSION:
            print(f"\n❌ ERROR: Python {self.python_version.major}.{self.python_version.minor} es muy antiguo.")
            print(f"Se requiere Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]} o superior.")
            return False
            
        if self.python_version > PYTHON_MAX_VERSION:
            print(f"\n⚠️ ADVERTENCIA: Python {self.python_version.major}.{self.python_version.minor} puede tener problemas con PaddleOCR.")
            print(f"Se recomienda Python {PYTHON_RECOMMENDED}")
            
            response = input("\n¿Desea continuar de todas formas? (PaddleOCR podría no funcionar) [s/N]: ")
            if response.lower() != 's':
                print("\nSugerencia: Instale Python {PYTHON_RECOMMENDED} desde python.org")
                return False
        
        print(f"✅ Python {self.python_version.major}.{self.python_version.minor} - Compatible")
        return True
    
    def create_requirements(self):
        """Crea el archivo de requirements dinámicamente según la versión de Python"""
        
        # Requirements básicos que funcionan en todas las versiones
        basic_reqs = [
            "opencv-python==4.8.1.78",
            "pytesseract==0.3.10",
            "pdf2image==1.16.3",
            "pillow==10.1.0",
            "pandas==2.0.3",
            "openpyxl==3.1.2",
            "xlsxwriter==3.1.9",
            "pypdf==3.17.0",
            "numpy==1.24.3"
        ]
        
        # Requirements específicos para PaddleOCR según versión de Python
        paddle_reqs = []
        
        if self.python_version.minor == 8:
            paddle_reqs = [
                "paddlepaddle==2.5.1",
                "paddleocr==2.6.1.3"
            ]
        elif self.python_version.minor == 9:
            paddle_reqs = [
                "paddlepaddle==2.5.2", 
                "paddleocr==2.7.0.3"
            ]
        elif self.python_version.minor == 10:
            paddle_reqs = [
                "paddlepaddle==2.5.2",
                "paddleocr==2.7.0.3"
            ]
        elif self.python_version.minor == 11:
            paddle_reqs = [
                "paddlepaddle==2.6.0",
                "paddleocr==2.7.0.3"
            ]
        
        with open(self.requirements_file, 'w') as f:
            f.write("# Requirements automáticos para Sistema de Boletas\n")
            f.write(f"# Python {self.python_version.major}.{self.python_version.minor}\n\n")
            
            for req in basic_reqs:
                f.write(req + "\n")
            
            if paddle_reqs and self.python_version <= PYTHON_MAX_VERSION:
                f.write("\n# PaddleOCR (opcional)\n")
                for req in paddle_reqs:
                    f.write(req + "\n")
        
        print(f"✅ Archivo de requirements creado: {self.requirements_file}")
        return True
    
    def check_and_install_packages(self):
        """Verifica e instala los paquetes necesarios"""
        print("\n" + "=" * 70)
        print("VERIFICACIÓN DE DEPENDENCIAS")
        print("=" * 70)
        
        # Lista de paquetes a verificar
        packages_to_check = [
            ("cv2", "opencv-python"),
            ("pytesseract", "pytesseract"),
            ("pdf2image", "pdf2image"),
            ("PIL", "pillow"),
            ("pandas", "pandas"),
            ("openpyxl", "openpyxl"),
            ("xlsxwriter", "xlsxwriter"),
            ("pypdf", "pypdf"),
            ("numpy", "numpy")
        ]
        
        missing_packages = []
        
        for import_name, package_name in packages_to_check:
            try:
                __import__(import_name)
                print(f"✅ {package_name} instalado")
            except ImportError:
                print(f"❌ {package_name} no encontrado")
                missing_packages.append(package_name)
        
        # Verificar PaddleOCR separadamente
        try:
            import paddle
            from paddleocr import PaddleOCR
            print("✅ PaddleOCR instalado")
            self.has_paddle = True
        except ImportError:
            print("⚠️ PaddleOCR no instalado (opcional)")
            
            if self.python_version <= PYTHON_MAX_VERSION:
                response = input("\n¿Desea intentar instalar PaddleOCR? (mejora la precisión) [S/n]: ")
                if response.lower() != 'n':
                    missing_packages.append("paddleocr")
        
        # Instalar paquetes faltantes
        if missing_packages:
            print("\n" + "=" * 70)
            print("INSTALACIÓN DE PAQUETES")
            print("=" * 70)
            
            response = input(f"\nSe instalarán {len(missing_packages)} paquetes. ¿Continuar? [S/n]: ")
            if response.lower() != 'n':
                self.install_packages(missing_packages)
            else:
                print("\n⚠️ Sin los paquetes necesarios el sistema no funcionará.")
                return False
        
        return True
    
    def install_packages(self, packages):
        """Instala los paquetes especificados"""
        for package in packages:
            print(f"\nInstalando {package}...")
            
            if package == "paddleocr":
                # Instalación especial para PaddleOCR
                self.install_paddleocr()
            else:
                # Instalación normal
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", 
                        "--upgrade", package
                    ])
                    print(f"✅ {package} instalado correctamente")
                except subprocess.CalledProcessError:
                    print(f"❌ Error instalando {package}")
    
    def install_paddleocr(self):
        """Instalación especial para PaddleOCR con manejo de errores"""
        print("\nInstalando PaddleOCR (puede tardar varios minutos)...")
        
        try:
            # Primero instalar paddlepaddle
            if self.is_windows:
                # Para Windows, usar la versión CPU
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "paddlepaddle==2.5.2", "-i", "https://pypi.org/simple/"
                ])
            else:
                # Para Linux/Mac
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "paddlepaddle==2.5.2"
                ])
            
            # Luego instalar paddleocr
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "paddleocr==2.7.0.3"
            ])
            
            # Verificar que funciona
            test_code = """
import paddle
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='latin', show_log=False)
print("PaddleOCR OK")
"""
            result = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ PaddleOCR instalado y funcionando")
                self.has_paddle = True
            else:
                raise Exception("PaddleOCR instalado pero no funciona")
                
        except Exception as e:
            print(f"⚠️ PaddleOCR no se pudo instalar/configurar: {e}")
            print("El sistema funcionará solo con Tesseract OCR.")
            
            response = input("\n¿Continuar sin PaddleOCR? [S/n]: ")
            if response.lower() == 'n':
                print("\nPara usar PaddleOCR, considere:")
                print("1. Crear un entorno virtual con Python 3.10")
                print("2. Instalar Visual C++ Redistributable (Windows)")
                print("3. Verificar que tiene suficiente espacio en disco (>2GB)")
                return False
        
        return True
    
    def check_external_tools(self):
        """Verifica herramientas externas (Tesseract, Poppler)"""
        print("\n" + "=" * 70)
        print("VERIFICACIÓN DE HERRAMIENTAS EXTERNAS")
        print("=" * 70)
        
        # Verificar Tesseract
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        
        tesseract_found = False
        for path in tesseract_paths:
            if Path(path).exists():
                tesseract_found = True
                print(f"✅ Tesseract encontrado: {path}")
                break
        
        if not tesseract_found:
            # Intentar con which/where
            try:
                if self.is_windows:
                    result = subprocess.run(["where", "tesseract"], capture_output=True, text=True)
                else:
                    result = subprocess.run(["which", "tesseract"], capture_output=True, text=True)
                
                if result.returncode == 0:
                    tesseract_found = True
                    print(f"✅ Tesseract encontrado en PATH")
            except:
                pass
        
        if not tesseract_found:
            print("⚠️ Tesseract OCR no encontrado")
            print("\nPara instalar Tesseract:")
            if self.is_windows:
                print("1. Descargue desde: https://github.com/UB-Mannheim/tesseract/wiki")
                print("2. Instale con las opciones por defecto")
                print("3. Reinicie este programa")
            else:
                print("Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-spa")
                print("Mac: brew install tesseract")
            
            response = input("\n¿Continuar sin Tesseract? (limitado a PDFs con texto) [s/N]: ")
            if response.lower() != 's':
                return False
        
        self.has_tesseract = tesseract_found
        
        # Verificar Poppler (opcional)
        print("\nVerificando Poppler (para conversión de PDF)...")
        poppler_found = False
        
        try:
            if self.is_windows:
                result = subprocess.run(["where", "pdftoppm"], capture_output=True, text=True)
            else:
                result = subprocess.run(["which", "pdftoppm"], capture_output=True, text=True)
            
            if result.returncode == 0:
                poppler_found = True
                print("✅ Poppler encontrado")
        except:
            pass
        
        if not poppler_found:
            print("⚠️ Poppler no encontrado (conversión de PDF puede fallar)")
            print("Nota: El sistema intentará procesar PDFs de todas formas")
        
        return True
    
    def run_checks(self):
        """Ejecuta todas las verificaciones"""
        print("\n🚀 SISTEMA DE BOLETAS DE HONORARIOS v3.0")
        print("Sistema de configuración automática\n")
        
        # 1. Verificar Python
        if not self.check_python_version():
            return False
        
        # 2. Crear requirements
        if not self.create_requirements():
            return False
        
        # 3. Instalar paquetes
        if not self.check_and_install_packages():
            return False
        
        # 4. Verificar herramientas externas
        if not self.check_external_tools():
            return False
        
        print("\n" + "=" * 70)
        print("✅ SISTEMA LISTO PARA EJECUTAR")
        print("=" * 70)
        
        # Resumen de capacidades
        print("\nCapacidades disponibles:")
        if self.has_tesseract:
            print("✅ Tesseract OCR - Procesamiento estándar")
        if self.has_paddle:
            print("✅ PaddleOCR - Procesamiento avanzado")
        if not self.has_tesseract and not self.has_paddle:
            print("⚠️ Solo PDFs con texto embebido")
        
        print("\n" + "=" * 70)
        
        return True

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal con verificación automática"""
    
    # Crear verificador
    checker = SystemChecker()
    
    # Ejecutar verificaciones
    if not checker.run_checks():
        print("\n❌ No se puede continuar. Resuelva los problemas indicados.")
        input("\nPresione Enter para salir...")
        sys.exit(1)
    
    # Si todo está OK, importar y ejecutar la aplicación
    print("\nIniciando aplicación...")
    print("-" * 70)
    
    try:
        # Configurar el path para los módulos
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Configurar variable para indicar capacidades
        os.environ['HAS_PADDLE'] = '1' if checker.has_paddle else '0'
        os.environ['HAS_TESSERACT'] = '1' if checker.has_tesseract else '0'
        
        # Importar la aplicación principal
        from app_main import BoletasApp
        
        # Ejecutar
        app = BoletasApp()
        app.mainloop()
        
    except ImportError as e:
        print(f"\n❌ Error importando módulos: {e}")
        print("\nVerifique que todos los archivos del proyecto estén presentes:")
        print("- app_main.py")
        print("- modules/")
        print("  - __init__.py")
        print("  - config.py")
        print("  - ocr_processor.py")
        print("  - data_extractor.py")
        print("  - report_generator.py")
        print("  - utils.py")
        input("\nPresione Enter para salir...")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error ejecutando la aplicación: {e}")
        import traceback
        traceback.print_exc()
        input("\nPresione Enter para salir...")
        sys.exit(1)

if __name__ == "__main__":
    main()