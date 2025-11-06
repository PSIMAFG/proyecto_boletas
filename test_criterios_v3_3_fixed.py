#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar criterios de revision v3.3
Simula diferentes casos para validar que van a revision cuando corresponde
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

# Colores para terminal (version Windows compatible)
try:
    import colorama
    colorama.init()
    HAS_COLOR = True
except:
    HAS_COLOR = False

class Color:
    if HAS_COLOR:
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        BOLD = '\033[1m'
        END = '\033[0m'
    else:
        GREEN = ''
        YELLOW = ''
        RED = ''
        BLUE = ''
        BOLD = ''
        END = ''

def print_test(caso, esperado, resultado, razon=""):
    """Imprime resultado de prueba"""
    icon = "[OK]" if (resultado == esperado) else "[X]"
    color = Color.GREEN if (resultado == esperado) else Color.RED
    
    print(f"{color}{icon}{Color.END} {caso:.<40} ", end="")
    print(f"Esperado: {'REVISAR' if esperado else 'OK':8} | ", end="")
    print(f"Resultado: {'REVISAR' if resultado else 'OK':8}", end="")
    
    if razon:
        print(f" | {Color.YELLOW}{razon}{Color.END}")
    else:
        print()

def test_criterios():
    """Prueba los criterios de revision"""
    from modules.data_processing import DataProcessorOptimized
    
    print(f"\n{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{'PRUEBA DE CRITERIOS DE REVISION v3.3':^70}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}\n")
    
    processor = DataProcessorOptimized()
    
    # Casos de prueba
    casos_prueba = [
        # CASO 1: Boleta completa - NO debe ir a revision
        {
            'nombre': 'Boleta completa',
            'campos': {
                'rut': '12.345.678-5',
                'nombre': 'Juan Perez Gonzalez',
                'monto': '1200000',
                'fecha_documento': '2024-03-15',
                'convenio': 'DIR',
                'nro_boleta': '12345'
            },
            'confianza': 0.85,
            'esperado': False,  # No debe ir a revision
        },
        
        # CASO 2: Falta CONVENIO - SIEMPRE debe ir a revision
        {
            'nombre': 'Sin convenio (Alexandros)',
            'campos': {
                'rut': '12.345.678-5',
                'nombre': 'Alexandros Vergara',
                'monto': '1200000',
                'fecha_documento': '2024-03-15',
                'convenio': '',  # FALTA
                'nro_boleta': '12345'
            },
            'confianza': 0.90,
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 3: Falta RUT - debe ir a revision
        {
            'nombre': 'Sin RUT (Valezka/Sarella)',
            'campos': {
                'rut': '',  # FALTA
                'nombre': 'Valezka Sanchez',
                'monto': '1200000',
                'fecha_documento': '2024-03-15',
                'convenio': 'ACOMPANAMIENTO',
                'nro_boleta': '12345'
            },
            'confianza': 0.80,
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 4: Falta FECHA - debe ir a revision
        {
            'nombre': 'Sin fecha (Daniel/Elizabeth)',
            'campos': {
                'rut': '12.345.678-5',
                'nombre': 'Daniel Gonzalez',
                'monto': '1200000',
                'fecha_documento': '',  # FALTA
                'convenio': 'MUNICIPAL',
                'nro_boleta': '12345'
            },
            'confianza': 0.75,
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 5: Falta MONTO - SIEMPRE debe ir a revision
        {
            'nombre': 'Sin monto',
            'campos': {
                'rut': '12.345.678-5',
                'nombre': 'Maria Silva',
                'monto': '',  # FALTA
                'fecha_documento': '2024-03-15',
                'convenio': 'PASMI',
                'nro_boleta': '12345'
            },
            'confianza': 0.85,
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 6: Confianza muy baja - debe ir a revision
        {
            'nombre': 'Confianza muy baja',
            'campos': {
                'rut': '12.345.678-5',
                'nombre': 'Pedro Lopez',
                'monto': '1200000',
                'fecha_documento': '2024-03-15',
                'convenio': 'DIR',
                'nro_boleta': '12345'
            },
            'confianza': 0.25,  # MUY BAJA
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 7: RUT invalido - debe ir a revision
        {
            'nombre': 'RUT con DV invalido',
            'campos': {
                'rut': '12.345.678-9',  # DV incorrecto
                'nombre': 'Ana Martinez',
                'monto': '1200000',
                'fecha_documento': '2024-03-15',
                'convenio': 'AIDIA',
                'nro_boleta': '12345'
            },
            'confianza': 0.80,
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 8: Monto fuera de rango - debe ir a revision
        {
            'nombre': 'Monto muy bajo',
            'campos': {
                'rut': '12.345.678-5',
                'nombre': 'Carlos Diaz',
                'monto': '50000',  # Muy bajo
                'fecha_documento': '2024-03-15',
                'convenio': 'MEJOR NINEZ',
                'nro_boleta': '12345'
            },
            'confianza': 0.85,
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 9: Faltan multiples campos - debe ir a revision
        {
            'nombre': 'Faltan RUT y nombre',
            'campos': {
                'rut': '',  # FALTA
                'nombre': '',  # FALTA
                'monto': '1200000',
                'fecha_documento': '2024-03-15',
                'convenio': 'DIR',
                'nro_boleta': '12345'
            },
            'confianza': 0.70,
            'esperado': True,  # Debe ir a revision
        },
        
        # CASO 10: Solo falta folio - NO debe ir a revision
        {
            'nombre': 'Solo falta folio (no critico)',
            'campos': {
                'rut': '12.345.678-5',
                'nombre': 'Luis Rodriguez',
                'monto': '1200000',
                'fecha_documento': '2024-03-15',
                'convenio': 'ESPACIOS_AMIGABLES',
                'nro_boleta': ''  # Falta, pero no es critico
            },
            'confianza': 0.75,
            'esperado': False,  # NO debe ir a revision
        }
    ]
    
    # Ejecutar pruebas
    print(f"{Color.BOLD}Ejecutando pruebas de criterios:{Color.END}\n")
    
    correctos = 0
    total = len(casos_prueba)
    
    for caso in casos_prueba:
        # Simular evaluacion
        resultado = processor._needs_review_balanced(
            caso['campos'],
            caso['confianza']
        )
        
        razon = caso['campos'].get('revision_reason', '')
        
        print_test(
            caso['nombre'],
            caso['esperado'],
            resultado,
            razon
        )
        
        if resultado == caso['esperado']:
            correctos += 1
    
    # Resumen
    print(f"\n{Color.BOLD}{'='*70}{Color.END}")
    print(f"{Color.BOLD}RESUMEN:{Color.END}")
    print(f"  Pruebas correctas: {correctos}/{total} ", end="")
    
    if correctos == total:
        print(f"{Color.GREEN}[OK] TODOS LOS CRITERIOS FUNCIONAN CORRECTAMENTE{Color.END}")
    else:
        print(f"{Color.RED}[X] HAY CRITERIOS QUE NO FUNCIONAN COMO SE ESPERA{Color.END}")
    
    print(f"{Color.BOLD}{'='*70}{Color.END}\n")
    
    # Explicacion de criterios
    if correctos == total:
        print(f"{Color.GREEN}{Color.BOLD}[OK] Los criterios estan funcionando correctamente:{Color.END}")
        print()
        print("  1. SIEMPRE revisa si falta convenio (critico para finanzas)")
        print("  2. Revisa si faltan 2+ campos criticos")
        print("  3. Revisa si falta monto")
        print("  4. Revisa si confianza < 30%")
        print("  5. Revisa si RUT invalido o monto fuera de rango")
        print()
        print(f"{Color.YELLOW}Esto asegura un balance correcto:{Color.END}")
        print("  - No es muy permisivo (revisa casos problematicos)")
        print("  - No es muy estricto (no todo va a revision)")
        print("  - Protege la integridad del resumen financiero")

def main():
    """Funcion principal"""
    print(f"\n{Color.BOLD}Sistema de Boletas OCR - Prueba de Criterios v3.3{Color.END}\n")
    
    try:
        test_criterios()
    except ImportError as e:
        print(f"{Color.RED}Error: No se pudo importar el modulo.{Color.END}")
        print(f"Asegurate de haber instalado la version v3.3")
        print(f"Ejecuta: instalar_v3_3_final_fixed.bat")
        return 1
    except Exception as e:
        print(f"{Color.RED}Error inesperado: {e}{Color.END}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
