"""
Script de diagnóstico para identificar y solucionar problemas
"""
import sys
import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import pytesseract

# Agregar path
sys.path.append(str(Path(__file__).parent))

def check_dependencies():
    """Verifica todas las dependencias"""
    print("=" * 60)
    print("VERIFICACIÓN DE DEPENDENCIAS")
    print("=" * 60)
    
    issues = []
    
    # Python version
    print(f"✓ Python: {sys.version}")
    
    # Tesseract
    try:
        from modules.utils import detect_tesseract_cmd
        tesseract_path = detect_tesseract_cmd()
        if tesseract_path:
            print(f"✓ Tesseract encontrado: {tesseract_path}")
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # Probar Tesseract
            try:
                version = pytesseract.get_tesseract_version()
                print(f"  Versión: {version}")
            except Exception as e:
                print(f"  ⚠ Error al obtener versión: {e}")
                issues.append("Tesseract no funciona correctamente")
        else:
            print("✗ Tesseract NO encontrado")
            issues.append("Tesseract no está instalado")
    except Exception as e:
        print(f"✗ Error verificando Tesseract: {e}")
        issues.append(f"Error con Tesseract: {e}")
    
    # Poppler
    try:
        from modules.utils import detect_poppler_bin
        poppler_path = detect_poppler_bin()
        if poppler_path:
            print(f"✓ Poppler encontrado: {poppler_path}")
        else:
            print("⚠ Poppler NO encontrado (opcional)")
    except Exception as e:
        print(f"⚠ Error verificando Poppler: {e}")
    
    # Directorios
    print("\nDIRECTORIOS:")
    from config import REVIEW_PREVIEW_DIR, REGISTRO_DIR, EXPORT_DIR
    
    for name, dir_path in [("Preview", REVIEW_PREVIEW_DIR), 
                           ("Registro", REGISTRO_DIR),
                           ("Export", EXPORT_DIR)]:
        if dir_path.exists():
            print(f"✓ {name}: {dir_path}")
        else:
            print(f"⚠ {name} no existe, creando...")
            dir_path.mkdir(exist_ok=True, parents=True)
            if dir_path.exists():
                print(f"  ✓ Creado exitosamente")
            else:
                print(f"  ✗ Error al crear")
                issues.append(f"No se pudo crear directorio {name}")
    
    # Bibliotecas Python
    print("\nBIBLIOTECAS PYTHON:")
    required_libs = [
        "cv2", "numpy", "PIL", "pytesseract", "pdf2image",
        "pandas", "openpyxl", "xlsxwriter", "pypdf"
    ]
    
    for lib in required_libs:
        try:
            __import__(lib)
            print(f"✓ {lib}")
        except ImportError:
            print(f"✗ {lib} NO instalado")
            issues.append(f"Biblioteca {lib} no instalada")
    
    return issues


def test_ocr():
    """Prueba el OCR con una imagen de ejemplo"""
    print("\n" + "=" * 60)
    print("PRUEBA DE OCR")
    print("=" * 60)
    
    # Crear imagen de prueba
    test_img = np.ones((100, 300, 3), dtype=np.uint8) * 255
    cv2.putText(test_img, "PRUEBA OCR 123", (10, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Guardar imagen de prueba
    test_path = Path("test_ocr.png")
    cv2.imwrite(str(test_path), test_img)
    print(f"Imagen de prueba creada: {test_path}")
    
    # Probar OCR
    try:
        text = pytesseract.image_to_string(test_img, lang='spa')
        print(f"Texto extraído: '{text.strip()}'")
        
        if "PRUEBA" in text or "123" in text:
            print("✓ OCR funciona correctamente")
        else:
            print("⚠ OCR funciona pero el resultado no es óptimo")
            
        # Limpiar
        test_path.unlink()
        
    except Exception as e:
        print(f"✗ Error en OCR: {e}")


def test_preview_saving():
    """Prueba el guardado de previews"""
    print("\n" + "=" * 60)
    print("PRUEBA DE GUARDADO DE PREVIEWS")
    print("=" * 60)
    
    from config import REVIEW_PREVIEW_DIR
    
    # Crear imagen de prueba
    test_img = np.ones((200, 300, 3), dtype=np.uint8) * 255
    cv2.putText(test_img, "PREVIEW TEST", (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Guardar en el directorio de previews
    preview_path = REVIEW_PREVIEW_DIR / "test_preview.png"
    
    try:
        success = cv2.imwrite(str(preview_path), test_img)
        
        if success and preview_path.exists():
            print(f"✓ Preview guardado correctamente en: {preview_path}")
            
            # Verificar que se puede leer
            img_read = cv2.imread(str(preview_path))
            if img_read is not None:
                print("✓ Preview se puede leer correctamente")
            else:
                print("✗ Preview existe pero no se puede leer")
            
            # Limpiar
            preview_path.unlink()
            
        else:
            print(f"✗ Error guardando preview")
            
    except Exception as e:
        print(f"✗ Error: {e}")


def test_sample_file():
    """Prueba con un archivo de muestra si existe"""
    print("\n" + "=" * 60)
    print("PRUEBA CON ARCHIVO DE MUESTRA")
    print("=" * 60)
    
    from config import REGISTRO_DIR
    from modules.data_processing import DataProcessorOptimized
    
    # Buscar un archivo de muestra
    sample_files = list(REGISTRO_DIR.glob("*.pdf")) + \
                  list(REGISTRO_DIR.glob("*.png")) + \
                  list(REGISTRO_DIR.glob("*.jpg"))
    
    if not sample_files:
        print("No se encontraron archivos de muestra en la carpeta Registro")
        print("Coloque un PDF o imagen para probar")
        return
    
    sample_file = sample_files[0]
    print(f"Probando con: {sample_file.name}")
    
    try:
        processor = DataProcessorOptimized()
        result = processor.process_file(sample_file)
        
        if result:
            print("\n✓ Archivo procesado exitosamente")
            print("\nCampos extraídos:")
            for field in ['nombre', 'rut', 'nro_boleta', 'fecha_documento', 'monto']:
                value = result.get(field, '')
                conf = result.get(f'{field}_confidence', 0)
                if value:
                    print(f"  {field}: {value} (confianza: {conf:.0%})")
                else:
                    print(f"  {field}: [NO DETECTADO]")
            
            print(f"\n¿Necesita revisión?: {result.get('needs_review', False)}")
            print(f"Preview guardado: {result.get('preview_path', 'NO')}")
            
            if result.get('preview_path') and Path(result['preview_path']).exists():
                print("✓ Preview existe y es accesible")
            else:
                print("✗ Preview no se guardó correctamente")
                
        else:
            print("✗ Error al procesar el archivo")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def generate_recommendations(issues):
    """Genera recomendaciones basadas en los problemas encontrados"""
    print("\n" + "=" * 60)
    print("RECOMENDACIONES")
    print("=" * 60)
    
    if not issues:
        print("✓ No se detectaron problemas críticos")
        print("El sistema debería funcionar correctamente")
    else:
        print("Se encontraron los siguientes problemas:\n")
        
        for issue in issues:
            print(f"• {issue}")
            
            # Recomendaciones específicas
            if "Tesseract" in issue:
                print("  → Solución: Instale Tesseract OCR desde:")
                print("    https://github.com/UB-Mannheim/tesseract/wiki")
                
            elif "Biblioteca" in issue and "no instalada" in issue:
                lib_name = issue.split()[1]
                print(f"  → Solución: pip install {lib_name}")
                
            elif "directorio" in issue:
                print("  → Solución: Verifique permisos de escritura en la carpeta")
        
        print("\nPara instalar todas las bibliotecas faltantes:")
        print("pip install opencv-python-headless pytesseract pdf2image pillow")
        print("pip install pandas openpyxl xlsxwriter pypdf")


def main():
    """Función principal del diagnóstico"""
    print("SISTEMA DE DIAGNÓSTICO - PROCESADOR OCR DE BOLETAS")
    print("=" * 60)
    
    # Verificar dependencias
    issues = check_dependencies()
    
    # Solo continuar con pruebas si Tesseract está disponible
    if not any("Tesseract" in issue for issue in issues):
        test_ocr()
        test_preview_saving()
        test_sample_file()
    else:
        print("\n⚠ Se omiten las pruebas porque Tesseract no está disponible")
    
    # Generar recomendaciones
    generate_recommendations(issues)
    
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO COMPLETADO")
    print("=" * 60)
    
    input("\nPresione Enter para salir...")


if __name__ == "__main__":
    main()