#!/usr/bin/env python3
"""
Script de Prueba Rápida - Sistema de Boletas OCR v3.2
Valida las mejoras implementadas
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Colores para terminal
class Color:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{text:^70}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}\n")

def print_result(label, value, confidence=None, expected=None, critical=False):
    """Imprime un resultado con formato"""
    icon = "🔴" if critical else "🟢"
    conf_text = f" (conf: {confidence:.2%})" if confidence else ""
    
    if expected:
        match = value == expected
        status = f"{Color.GREEN}✓{Color.END}" if match else f"{Color.RED}✗{Color.END}"
        exp_text = f" | Esperado: {expected}"
    else:
        status = ""
        exp_text = ""
    
    print(f"{icon} {label:.<25} {status} {value}{conf_text}{exp_text}")

def test_file(file_path: Path):
    """Prueba un archivo individual"""
    from modules.data_processing import DataProcessorOptimized
    
    print_header(f"PROBANDO: {file_path.name}")
    
    try:
        processor = DataProcessorOptimized()
        result = processor.process_file(file_path)
        
        if result.get('error'):
            print(f"{Color.RED}ERROR: {result['error']}{Color.END}")
            return False
        
        # Mostrar resultados
        print(f"\n{Color.BOLD}CAMPOS CRÍTICOS:{Color.END}")
        print_result("RUT", result.get('rut', 'N/A'), 
                    result.get('rut_confidence'), critical=True)
        print_result("Nombre", result.get('nombre', 'N/A')[:50], 
                    result.get('nombre_confidence'), critical=True)
        print_result("Monto", f"${result.get('monto', 'N/A')}", 
                    result.get('monto_confidence'), critical=True)
        
        print(f"\n{Color.BOLD}CAMPOS IMPORTANTES:{Color.END}")
        print_result("Folio", result.get('nro_boleta', 'N/A'), 
                    result.get('folio_confidence'))
        print_result("Fecha Documento", result.get('fecha_documento', 'N/A'), 
                    result.get('fecha_confidence'))
        print_result("Periodo Servicio", result.get('periodo_servicio', 'N/A'), 
                    result.get('periodo_servicio_confidence'))
        print_result("Convenio", result.get('convenio', 'N/A'), 
                    result.get('convenio_confidence'))
        
        print(f"\n{Color.BOLD}CAMPOS AUXILIARES:{Color.END}")
        print_result("Horas", result.get('horas', 'N/A'))
        print_result("Tipo", result.get('tipo', 'N/A'))
        print_result("Decreto", result.get('decreto_alcaldicio', 'N/A'))
        
        print(f"\n{Color.BOLD}METADATA:{Color.END}")
        print_result("Confianza OCR", f"{result.get('confianza', 0):.1%}")
        print_result("Quality Score", f"{result.get('quality_score', 0):.1%}")
        print_result("Necesita Revisión", "Sí" if result.get('needs_review') else "No")
        print_result("Origen Monto", result.get('monto_origen', 'N/A'))
        
        if result.get('validation_warnings'):
            print(f"\n{Color.YELLOW}⚠ ADVERTENCIAS:{Color.END}")
            for warning in result['validation_warnings']:
                print(f"  • {warning}")
        
        # Validaciones
        print(f"\n{Color.BOLD}VALIDACIONES:{Color.END}")
        
        errores = []
        warnings = []
        
        # RUT válido
        if result.get('rut'):
            from modules.utils import dv_ok
            if not dv_ok(result['rut']):
                errores.append("RUT con dígito verificador inválido")
        else:
            warnings.append("Falta RUT")
        
        # Monto en rango
        if result.get('monto'):
            try:
                monto = float(result['monto'])
                if monto < 200000 or monto > 2500000:
                    warnings.append(f"Monto fuera de rango esperado: ${monto:,.0f}")
            except:
                errores.append("Monto no numérico")
        else:
            warnings.append("Falta Monto")
        
        # Nombre válido
        if result.get('nombre'):
            nombre = result['nombre']
            if len(nombre) < 5:
                warnings.append("Nombre muy corto")
            if any(char.isdigit() for char in nombre):
                warnings.append("Nombre contiene números")
        else:
            warnings.append("Falta Nombre")
        
        # Fecha válida
        if result.get('fecha_documento'):
            from datetime import datetime
            try:
                fecha = datetime.strptime(result['fecha_documento'], "%Y-%m-%d")
                if fecha.year < 2015 or fecha.year > 2035:
                    warnings.append(f"Fecha sospechosa: {fecha.year}")
            except:
                errores.append("Fecha en formato inválido")
        
        # Mostrar resultados de validación
        if errores:
            print(f"\n{Color.RED}✗ ERRORES CRÍTICOS:{Color.END}")
            for error in errores:
                print(f"  • {error}")
        
        if warnings:
            print(f"\n{Color.YELLOW}⚠ ADVERTENCIAS:{Color.END}")
            for warning in warnings:
                print(f"  • {warning}")
        
        if not errores and not warnings:
            print(f"{Color.GREEN}✓ Todas las validaciones pasaron{Color.END}")
        
        # Glosa (truncada)
        if result.get('glosa'):
            print(f"\n{Color.BOLD}GLOSA:{Color.END}")
            glosa = result['glosa']
            if len(glosa) > 150:
                glosa = glosa[:150] + "..."
            print(f"  {glosa}")
        
        return len(errores) == 0
        
    except Exception as e:
        print(f"{Color.RED}EXCEPCIÓN: {e}{Color.END}")
        import traceback
        traceback.print_exc()
        return False

def test_batch(directory: Path, max_files: int = 5):
    """Prueba múltiples archivos"""
    from modules.utils import iter_files
    
    print_header(f"PRUEBA POR LOTES: {directory}")
    
    files = list(iter_files(directory))[:max_files]
    
    if not files:
        print(f"{Color.RED}No se encontraron archivos en {directory}{Color.END}")
        return
    
    print(f"Probando {len(files)} archivo(s)...\n")
    
    results = []
    for i, file_path in enumerate(files, 1):
        print(f"\n{Color.BOLD}[{i}/{len(files)}]{Color.END}")
        success = test_file(file_path)
        results.append((file_path.name, success))
    
    # Resumen
    print_header("RESUMEN")
    
    exitosos = sum(1 for _, success in results if success)
    fallidos = len(results) - exitosos
    
    for nombre, success in results:
        icon = f"{Color.GREEN}✓{Color.END}" if success else f"{Color.RED}✗{Color.END}"
        print(f"{icon} {nombre}")
    
    print(f"\n{Color.BOLD}Total:{Color.END} {len(results)}")
    print(f"{Color.GREEN}Exitosos:{Color.END} {exitosos} ({exitosos/len(results)*100:.1f}%)")
    print(f"{Color.RED}Fallidos:{Color.END} {fallidos} ({fallidos/len(results)*100:.1f}%)")

def test_unit_extraction():
    """Pruebas unitarias de extracción"""
    from modules.data_processing import FieldExtractor
    
    print_header("PRUEBAS UNITARIAS DE EXTRACCIÓN")
    
    extractor = FieldExtractor()
    
    # Test 1: Extracción de RUT
    print(f"\n{Color.BOLD}TEST 1: Extracción de RUT{Color.END}")
    test_text = """
    BOLETA DE HONORARIOS
    RUT: 12.345.678-5
    Nombre: Juan Pérez González
    """
    rut, conf = extractor.extract_rut(test_text)
    print_result("RUT extraído", rut, conf, expected="12.345.678-5")
    
    # Test 2: Extracción de monto
    print(f"\n{Color.BOLD}TEST 2: Extracción de Monto{Color.END}")
    test_text = """
    Total Honorarios $ 1.085.172
    Retenciones: $ 108.517
    Líquido a Pagar: $ 976.655
    """
    monto, conf = extractor.extract_monto(test_text)
    print_result("Monto extraído", monto, conf, expected="1085172")
    
    # Test 3: Extracción de fecha
    print(f"\n{Color.BOLD}TEST 3: Extracción de Fecha{Color.END}")
    test_text = """
    Fecha: 15 de marzo de 2024
    Hora: 10:30
    """
    fecha, conf = extractor.extract_fecha(test_text)
    print_result("Fecha extraída", fecha, conf, expected="2024-03-15")
    
    # Test 4: Extracción de periodo
    print(f"\n{Color.BOLD}TEST 4: Extracción de Periodo{Color.END}")
    test_text = """
    Servicio prestado durante el mes de febrero 2024
    """
    periodo, conf = extractor.extract_periodo_servicio(test_text, "2024-03-15")
    print_result("Periodo extraído", periodo, conf, expected="2024-02")
    
    # Test 5: Extracción de convenio
    print(f"\n{Color.BOLD}TEST 5: Extracción de Convenio{Color.END}")
    test_text = """
    Programa ACOMPAÑAMIENTO PSICOSOCIAL
    Convenio: DIR APS
    """
    convenio, conf = extractor.extract_convenio(test_text)
    print_result("Convenio extraído", convenio, conf, expected="ACOMPAÑAMIENTO")
    
    # Test 6: No confundir MUNICIPAL de encabezado
    print(f"\n{Color.BOLD}TEST 6: Evitar Falso Positivo MUNICIPAL{Color.END}")
    test_text = """
    I. MUNICIPALIDAD DE QUILICURA
    Departamento de Salud
    
    Servicio: Programa DIR
    """
    convenio, conf = extractor.extract_convenio(test_text)
    print_result("Convenio extraído", convenio, conf)
    if convenio != "MUNICIPAL":
        print(f"{Color.GREEN}✓ No confundió encabezado con convenio{Color.END}")
    else:
        print(f"{Color.RED}✗ Falso positivo: confundió encabezado{Color.END}")

def main():
    """Función principal"""
    print(f"\n{Color.BOLD}Sistema de Boletas OCR - Prueba Rápida v3.2{Color.END}\n")
    
    if len(sys.argv) > 1:
        # Modo: probar archivo específico
        file_path = Path(sys.argv[1])
        
        if not file_path.exists():
            print(f"{Color.RED}Error: Archivo no encontrado: {file_path}{Color.END}")
            return 1
        
        if file_path.is_dir():
            test_batch(file_path)
        else:
            test_file(file_path)
    else:
        # Modo: pruebas unitarias
        print(f"{Color.YELLOW}Modo: Pruebas Unitarias{Color.END}")
        print(f"Para probar archivo: python test_quick.py ruta/al/archivo.pdf")
        print(f"Para probar carpeta: python test_quick.py ruta/a/carpeta/\n")
        
        test_unit_extraction()
        
        # Probar carpeta Registro si existe
        registro_dir = Path("Registro")
        if registro_dir.exists():
            print(f"\n{Color.YELLOW}¿Probar archivos en carpeta Registro? (y/n):{Color.END} ", end="")
            if input().lower() == 'y':
                test_batch(registro_dir, max_files=3)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Color.YELLOW}Prueba cancelada{Color.END}\n")
        sys.exit(130)