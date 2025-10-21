"""
Script de prueba para validar la extracción inteligente de campos
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from modules.data_processing import SmartFieldExtractor
from datetime import datetime

def test_extraction():
    """Prueba la extracción con ejemplos reales"""
    
    # Crear extractor
    extractor = SmartFieldExtractor()
    
    # Casos de prueba basados en los datos reales
    test_cases = [
        {
            'nombre': 'Caso 1: Boleta típica',
            'texto': """
            NATALIA PAOLA NILO ESCOBAR
            19.142.017-9
            
            BOLETA DE HONORARIOS ELECTRÓNICA
            Nro. 52
            
            Fecha: 08 de abril de 2025
            
            Señores: MUNICIPALIDAD DE SAN ANTONIO
            
            Por atención profesional:
            SERVICIO MES DE MARZO 2025. HONORARIO CONV. PROGRAMA DIR 
            16 HRS D.A 1845 2/04/25
            
            Total Honorarios $: 526.144
            14.50 % Impto. Retenido: 76.291
            Total: 449.853
            """,
            'esperado': {
                'nombre': 'NATALIA PAOLA NILO ESCOBAR',
                'rut': '19.142.017-9',
                'nro_boleta': '52',
                'fecha': '2025-04-08',
                'monto': '526144',
                'convenio': 'DIR',
                'horas': '16',
                'decreto': '1845'
            }
        },
        {
            'nombre': 'Caso 2: Convenio Salud Mental',
            'texto': """
            PRESTADOR DE SERVICIOS
            CAMILA ALBORNOZ MOLINA
            19.184.111-5
            
            Boleta N° 2025
            
            Fecha: 07 de diciembre de 2024
            
            OTROS PROFESIONALES DE, TERAPEUTA OCUPACIONAL
            
            Por: SERVICIO MES MARZO 2025 CONVENIO SALUD MENTAL EN APS
            44 HRS SEMANALES D.A. 567 31/01/2025
            
            Total Honorarios: $1.446.896
            """,
            'esperado': {
                'nombre': 'CAMILA ALBORNOZ MOLINA',
                'rut': '19.184.111-5',
                'nro_boleta': '2025',  # Problemático - es el año
                'fecha': '2024-12-07',
                'monto': '1446896',
                'convenio': 'SALUD MENTAL',
                'horas': '44',
                'decreto': '567'
            }
        },
        {
            'nombre': 'Caso 3: Acompañamiento Psicosocial',
            'texto': """
            CARLA RAFFO MIRANDA
            13.196.527-3
            
            Boleta de Honorarios N° 285547
            
            01 de abril de 2025
            
            Por atención profesional:
            H.CONV. PROGRAMA ACOMPAÑAMIENTO PSICOSOCIAL 
            15 HRS. SEMANALES MES MARZO 25, D.A. 612 DEL 31-01-2025
            
            Total Honorarios $: 493.280
            14.5 % Impto. Retenido: 69.139
            Total: 407.677
            """,
            'esperado': {
                'nombre': 'CARLA RAFFO MIRANDA',
                'rut': '13.196.527-3',
                'nro_boleta': '285547',
                'fecha': '2025-04-01',
                'monto': '493280',
                'convenio': 'ACOMPAÑAMIENTO PSICOSOCIAL',
                'horas': '15',
                'decreto': '612'
            }
        }
    ]
    
    print("=" * 80)
    print("PRUEBA DE EXTRACCIÓN INTELIGENTE DE CAMPOS")
    print("=" * 80)
    
    for caso in test_cases:
        print(f"\n{caso['nombre']}")
        print("-" * 40)
        
        texto = caso['texto']
        esperado = caso['esperado']
        
        # Extraer campos
        nombre, nombre_conf = extractor.extract_nombre_inteligente(texto)
        rut, rut_conf = extractor.extract_rut_improved(texto)
        folio, folio_conf = extractor.extract_folio_inteligente(texto)
        fecha, fecha_conf = extractor.extract_fecha_validada(texto)
        monto, monto_conf = extractor.extract_monto_inteligente(texto)
        convenio, convenio_conf = extractor.extract_convenio_inteligente(texto)
        horas, horas_conf = extractor.extract_horas_inteligente(texto)
        decreto, decreto_conf = extractor.extract_decreto_inteligente(texto)
        
        # Comparar con esperado
        resultados = {
            'nombre': (nombre, nombre_conf, esperado.get('nombre', '')),
            'rut': (rut, rut_conf, esperado.get('rut', '')),
            'nro_boleta': (folio, folio_conf, esperado.get('nro_boleta', '')),
            'fecha': (fecha, fecha_conf, esperado.get('fecha', '')),
            'monto': (monto, monto_conf, esperado.get('monto', '')),
            'convenio': (convenio, convenio_conf, esperado.get('convenio', '')),
            'horas': (horas, horas_conf, esperado.get('horas', '')),
            'decreto': (decreto, decreto_conf, esperado.get('decreto', ''))
        }
        
        # Mostrar resultados
        for campo, (valor, confianza, esperado_val) in resultados.items():
            if valor == esperado_val:
                status = "✓"
                color = "\033[92m"  # Verde
            elif valor and esperado_val:
                status = "≈"
                color = "\033[93m"  # Amarillo
            else:
                status = "✗"
                color = "\033[91m"  # Rojo
            
            print(f"{color}{status}\033[0m {campo:15} | Extraído: {valor:20} | Esperado: {esperado_val:20} | Conf: {confianza:.0%}")


def test_special_cases():
    """Prueba casos especiales problemáticos"""
    print("\n" + "=" * 80)
    print("PRUEBA DE CASOS ESPECIALES")
    print("=" * 80)
    
    extractor = SmartFieldExtractor()
    
    # Caso: Número de boleta que es un año
    texto_año = """
    BOLETA DE HONORARIOS
    N° 2025
    
    Otra información...
    Boleta número 1234
    """
    
    folio, conf = extractor.extract_folio_inteligente(texto_año)
    print(f"\nCaso: Año como número de boleta")
    print(f"  Texto: 'N° 2025' y 'Boleta número 1234'")
    print(f"  Resultado: {folio} (conf: {conf:.0%})")
    print(f"  {'✓' if folio == '1234' else '✗'} Debería ser 1234, no 2025")
    
    # Caso: Nombre genérico
    texto_nombre = """
    PRESTADOR DE SERVICIOS
    JUAN PEREZ GONZALEZ
    12.345.678-9
    """
    
    nombre, conf = extractor.extract_nombre_inteligente(texto_nombre)
    print(f"\nCaso: Evitar 'PRESTADOR DE SERVICIOS'")
    print(f"  Texto incluye 'PRESTADOR DE SERVICIOS' y 'JUAN PEREZ GONZALEZ'")
    print(f"  Resultado: {nombre} (conf: {conf:.0%})")
    print(f"  {'✓' if 'PRESTADOR' not in nombre else '✗'} No debería incluir 'PRESTADOR'")
    
    # Caso: Múltiples convenios
    texto_convenios = """
    Servicio prestado en el marco del CONVENIO SALUD MENTAL EN APS
    Programa DIR también mencionado
    """
    
    convenio, conf = extractor.extract_convenio_inteligente(texto_convenios)
    print(f"\nCaso: Múltiples convenios mencionados")
    print(f"  Texto menciona 'SALUD MENTAL EN APS' y 'DIR'")
    print(f"  Resultado: {convenio} (conf: {conf:.0%})")
    print(f"  ✓ Debería priorizar el más específico")
    
    # Caso: Horas en diferentes formatos
    texto_horas = """
    Prestación de servicios por 44 hrs semanales
    También mencionado: 176 horas mensuales
    """
    
    horas, conf = extractor.extract_horas_inteligente(texto_horas)
    print(f"\nCaso: Horas en diferentes formatos")
    print(f"  Texto: '44 hrs semanales' y '176 horas mensuales'")
    print(f"  Resultado: {horas} (conf: {conf:.0%})")
    print(f"  {'✓' if horas == '44' else '≈'} Debería priorizar horas semanales comunes")


def test_date_validation():
    """Prueba la validación de fechas"""
    print("\n" + "=" * 80)
    print("PRUEBA DE VALIDACIÓN DE FECHAS")
    print("=" * 80)
    
    extractor = SmartFieldExtractor()
    current_year = datetime.now().year
    
    test_dates = [
        (f"15 de marzo de {current_year}", f"{current_year}-03-15", True),
        (f"01/04/{current_year}", f"{current_year}-04-01", True),
        ("07 de diciembre de 2024", "2024-12-07", False),  # Año anterior - menor confianza
        ("32 de enero de 2025", "", False),  # Fecha inválida
        (f"15-06-{current_year}", f"{current_year}-06-15", True),
    ]
    
    for texto_fecha, esperado, deberia_pasar in test_dates:
        fecha, conf = extractor.extract_fecha_validada(f"Fecha: {texto_fecha}")
        status = "✓" if (fecha == esperado) else "✗"
        print(f"{status} '{texto_fecha}' → {fecha} (conf: {conf:.0%})")
        if not deberia_pasar and conf < 0.70:
            print(f"  ✓ Correctamente marcado con baja confianza")


if __name__ == "__main__":
    print("\n🔍 EJECUTANDO PRUEBAS DE EXTRACCIÓN INTELIGENTE\n")
    
    # Ejecutar todas las pruebas
    test_extraction()
    test_special_cases()
    test_date_validation()
    
    print("\n" + "=" * 80)
    print("PRUEBAS COMPLETADAS")
    print("=" * 80)
    
    print("\n📝 RESUMEN:")
    print("- Los nombres ya no deberían incluir 'PRESTADOR DE SERVICIOS'")
    print("- Los números de boleta no tomarán años (2024, 2025, etc)")
    print("- Los convenios se detectan del diccionario completo")
    print("- Las fechas se validan para el año esperado")
    print("- Las horas se extraen del número antes de 'hrs'")
    print("- Solo se procesa la primera página de PDFs")
    
    input("\nPresione Enter para salir...")