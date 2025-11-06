# modules/data_processing.py (VERSIÓN MEJORADA Y ROBUSTA)
"""
Módulo de procesamiento ULTRA-ROBUSTO - Versión 3.2
PRIORIDAD: NO EQUIVOCARSE en montos, nombres, fechas, convenios y RUTs
"""
import re
import difflib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
from datetime import datetime
import sys
import unicodedata

sys.path.append(str(Path(__file__).parent.parent))
from config import *
from modules.utils import *


class FieldExtractor:
    """Extractor de campos ULTRA-ROBUSTO con validaciones estrictas"""
    
    def __init__(self):
        self.meses = MESES
        self.convenios_conocidos = KNOWN_CONVENIOS
        
    # ============================================================================
    # RUT - MUY ROBUSTO, SOLO CAMBIO MENOR
    # ============================================================================
    def extract_rut(self, text: str) -> Tuple[str, float]:
        """Extrae RUT con validación - PRIORIZA RUTs con ancla"""
        # PRIORIDAD 1: Buscar con ancla "RUT:" (máxima confianza)
        for match in RUT_ANCHOR_RE.finditer(text):
            rut = match.group(1)
            if dv_ok(rut):
                return rut.strip(), 0.98  # Aumentada confianza
        
        # PRIORIDAD 2: Buscar RUT en primeras 20 líneas (zona de encabezado)
        lines = text.split('\n')[:20]
        for line in lines:
            for match in RUT_RE.finditer(line):
                rut = match.group(1)
                if dv_ok(rut):
                    return rut.strip(), 0.90
        
        # PRIORIDAD 3: Buscar en todo el texto (menor confianza)
        for match in RUT_RE.finditer(text):
            rut = match.group(1)
            if dv_ok(rut):
                return rut.strip(), 0.75
        
        return "", 0.0
    
    # ============================================================================
    # FOLIO - ROBUSTO
    # ============================================================================
    def extract_folio(self, text: str) -> Tuple[str, float]:
        """Extrae número de folio - EVITA números de códigos SII"""
        # PRIORIDAD 1: Con etiqueta clara
        match = FOLIO_RE.search(text)
        if match:
            folio = match.group(1).strip()
            # Validar que sea razonable (4-7 dígitos)
            if 4 <= len(folio) <= 7 and folio.isdigit():
                num = int(folio)
                if 1000 <= num <= 9999999:
                    return folio, 0.95
        
        # PRIORIDAD 2: Buscar en primeras 15 líneas
        lines = text.split('\n')[:15]
        
        # Palabras de ruido que indican que NO es un folio
        ruido_folio = ['código', 'codigo', 'verificador', 'timbre', 'sii', 
                       'resolución', 'resolucion', 'hash', 'barras']
        
        for line in lines:
            # Skip líneas con ruido
            if any(palabra in line.lower() for palabra in ruido_folio):
                continue
            
            # Buscar números de 4-7 dígitos
            nums = re.findall(r'\b(\d{4,7})\b', line)
            for num_str in nums:
                num = int(num_str)
                if 1000 <= num <= 9999999:
                    return num_str, 0.70
        
        return "", 0.0
    
    # ============================================================================
    # FECHA DOCUMENTO - MEJORADA
    # ============================================================================
    def extract_fecha(self, text: str) -> Tuple[str, float]:
        """
        Extrae FECHA DEL DOCUMENTO (fecha de emisión/pago)
        VERSIÓN MEJORADA: más estricta con el ruido
        """
        # Normalización
        t = re.sub(r'[|]+', ' ', text)
        t = re.sub(r'[ \t]+', ' ', t)
        lines = [l.strip() for l in t.split('\n') if l.strip()]

        # Palabras de RUIDO que indican que NO es una fecha válida
        ruido_keywords = [
            'res ex', 'res. ex', 'verifique', 'www.sii.cl', 
            'codigo verificador', 'código verificador', 'barra', 
            'resolución', 'resolucion', 'd.a.', 'decreto',
            'timbre', 'hash', 'qr'
        ]

        # Regex para fechas
        rex_texto = re.compile(
            r'(?i)\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|'
            r'septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+(\d{2,4})'
        )
        rex_num = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b')

        def parse_texto(m):
            try:
                d = int(m.group(1))
                mes = m.group(2).lower().replace('setiembre', 'septiembre')
                y = int(m.group(3))
                y = y + 2000 if y < 100 else y
                mm = self.meses.get(mes, 0)
                if 1 <= d <= 31 and 1 <= mm <= 12 and 2015 <= y <= 2035:
                    return datetime(y, mm, d)
            except:
                pass
            return None

        def parse_num(m):
            try:
                d = int(m.group(1))
                mm = int(m.group(2))
                y = int(m.group(3))
                y = y + 2000 if y < 100 else y
                # VALIDACIÓN ESTRICTA: día y mes razonables
                if 1 <= d <= 31 and 1 <= mm <= 12 and 2015 <= y <= 2035:
                    return datetime(y, mm, d)
            except:
                pass
            return None

        candidatos = []  # (score_contexto, datetime)

        for line in lines:
            l_lower = line.lower()
            
            # SKIP líneas de ruido
            if any(ruido in l_lower for ruido in ruido_keywords):
                continue

            # Scoring por contexto
            score_ctx = -1
            if 'fecha:' in l_lower or 'fecha :' in l_lower:
                score_ctx = 5  # Máxima prioridad
            elif 'fecha / hora emisión' in l_lower or 'fecha/hora emision' in l_lower:
                score_ctx = 4
            elif 'fecha / hora impresión' in l_lower or 'fecha/hora impresion' in l_lower:
                score_ctx = 2

            # Buscar fechas en la línea
            m1 = rex_texto.search(line)
            if m1:
                dt = parse_texto(m1)
                if dt:
                    candidatos.append((score_ctx, dt))
                    continue

            m2 = rex_num.search(line)
            if m2:
                dt = parse_num(m2)
                if dt:
                    candidatos.append((score_ctx, dt))

        if not candidatos:
            return "", 0.0

        # Ordenar: primero por score de contexto, luego por fecha más reciente
        candidatos.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_score, best_date = candidatos[0]
        
        # Confianza basada en el contexto
        conf = 0.98 if best_score >= 4 else (0.90 if best_score >= 2 else 0.75)
        
        return best_date.strftime("%Y-%m-%d"), conf
    
    # ============================================================================
    # PERIODO DE SERVICIO - MEJORADO
    # ============================================================================
    def extract_periodo_servicio(self, text: str, fecha_doc_iso: str = "") -> Tuple[str, float]:
        """
        Detecta MES/AÑO del servicio prestado (NO la fecha de pago)
        VERSIÓN MEJORADA: más tolerante a OCR y mejor inferencia de año
        """
        # Normalizar OCR
        base = self._norm_ocr_es(text)
        
        # Patrones robustos para meses (toleran espacios y errores OCR)
        meses_regex = {
            'enero': r'e\s*n\s*e\s*r\s*o',
            'febrero': r'f\s*e\s*b\s*r\s*e\s*r\s*o',
            'marzo': r'm\s*a\s*r\s*z\s*[o0]',  # tolera MARZ0
            'abril': r'a\s*b\s*r\s*i\s*l',
            'mayo': r'm\s*a\s*y\s*o',
            'junio': r'j\s*u\s*n\s*i\s*o',
            'julio': r'j\s*u\s*l\s*i\s*o',
            'agosto': r'a\s*g\s*o\s*s\s*t\s*o',
            'septiembre': r's\s*e\s*p\s*t\s*i\s*e\s*m\s*b\s*r\s*e',
            'octubre': r'o\s*c\s*t\s*u\s*b\s*r\s*e',
            'noviembre': r'n\s*o\s*v\s*i\s*e\s*m\s*b\s*r\s*e',
            'diciembre': r'd\s*i\s*c\s*i\s*e\s*m\s*b\s*r\s*e'
        }

        # Patrón: buscar mes con opcional "MES", "DE", año
        mes_union = '|'.join(meses_regex[m] for m in meses_regex)
        # Captura: (mes) y opcionalmente (año)
        patron = rf'(?i)\b(?:mes\s+de\s+|mes\s+)?({mes_union})\s*(?:de\s*)?(?:[-\s/]?(\d{{2,4}}))?'

        matches = list(re.finditer(patron, base, flags=re.I))
        
        if not matches:
            return "", 0.0

        # Tomar la PRIMERA ocurrencia válida (suele estar en glosa/descripción)
        for m in matches:
            mes_texto = m.group(1).strip()
            year_token = m.group(2)
            
            # Identificar mes canónico
            mes_canonico = None
            for nombre, rx in meses_regex.items():
                if re.fullmatch(rf'(?i){rx}', mes_texto, flags=re.I):
                    mes_canonico = nombre
                    break
            
            if not mes_canonico:
                continue
            
            mes_num = self.meses.get(mes_canonico, 0)
            if not mes_num:
                continue

            # ¿Hay año explícito?
            if year_token:
                try:
                    y = int(year_token)
                    if y < 100:
                        y += 2000
                    if 2015 <= y <= 2035:
                        return f"{y:04d}-{mes_num:02d}", 0.95
                except:
                    pass

            # Inferir año desde fecha del documento
            if fecha_doc_iso and len(fecha_doc_iso) >= 7:
                try:
                    y_doc = int(fecha_doc_iso[:4])
                    m_doc = int(fecha_doc_iso[5:7])
                    
                    # LÓGICA: Si el mes del servicio es mayor al mes del documento,
                    # probablemente el servicio fue del año anterior
                    # (ej: documento en Enero 2025, servicio de Diciembre → 2024)
                    if mes_num > m_doc:
                        y = y_doc - 1
                    else:
                        y = y_doc
                    
                    return f"{y:04d}-{mes_num:02d}", 0.85
                except:
                    pass

            # Año desconocido, retornar solo el mes
            return f"XXXX-{mes_num:02d}", 0.60

        return "", 0.0
    
    # ============================================================================
    # MONTO - CRÍTICO - VERSION MÁS ROBUSTA
    # ============================================================================
    def extract_monto(self, text: str) -> Tuple[str, float]:
        """
        Extrae MONTO BRUTO - VERSIÓN ULTRA-ROBUSTA
        PRIORIDADES:
        1. Celda "Total Honorarios $" en tabla SII
        2. Números grandes con $ en contexto correcto
        3. NUNCA tomar códigos, folios, RUTs, fechas
        """
        # Normalizar
        t = text.replace('S$', '$').replace('  ', ' ')
        t = re.sub(r'[|]+', ' ', t)
        lines = [l.strip() for l in t.split('\n') if l.strip()]

        # Palabras de RUIDO que indican que NO es un monto
        ruido_monto = [
            'código', 'codigo', 'verificador', 'timbre', 'sii', 'folio',
            'resolución', 'resolucion', 'hash', 'barras', 'qr', 'rut',
            'fecha', 'www', 'http', 'decreto', 'd.a'
        ]

        def es_linea_limpia(linea: str) -> bool:
            """Verifica que la línea NO contenga ruido"""
            l = linea.lower()
            return not any(r in l for r in ruido_monto)

        def normalizar_numero(s: str) -> str:
            """Normaliza un string numérico: '1.085.172' → '1085172'"""
            s = re.sub(r'[^\d,.\s]', '', s)
            s = s.replace(' ', '')
            # Si tiene múltiples separadores, asumimos son de miles
            if s.count('.') + s.count(',') > 1:
                s = s.replace(',', '').replace('.', '')
            else:
                # Un solo separador: puede ser decimal, pero en Chile
                # los montos suelen ser enteros
                s = s.replace(',', '').replace('.', '')
            return s

        def es_monto_valido(valor: float) -> bool:
            """Valida que el valor esté en rango plausible"""
            return 200_000 <= valor <= 2_500_000

        candidatos = []  # (confianza, valor, linea_origen)

        # ========== PRIORIDAD 1: "Total Honorarios $" ==========
        for i, line in enumerate(lines):
            if not es_linea_limpia(line):
                continue
            
            # Buscar "Total Honorarios" (case-insensitive)
            if re.search(r'(?i)total\s+honorarios?\s*\$?', line):
                # Extraer números de la misma línea o siguiente
                lineas_busqueda = [line]
                if i + 1 < len(lines):
                    lineas_busqueda.append(lines[i + 1])
                
                for linea in lineas_busqueda:
                    # Buscar patrones: $1.234.567 o 1.234.567 o 1234567
                    nums = re.findall(r'\$?\s*([\d\.\,\s]{6,})', linea)
                    for num_str in nums:
                        num_clean = normalizar_numero(num_str)
                        if not num_clean or len(num_clean) < 6:
                            continue
                        
                        try:
                            valor = float(num_clean)
                            if es_monto_valido(valor):
                                candidatos.append((0.98, valor, line))
                        except:
                            pass

        # ========== PRIORIDAD 2: Líneas con $ y números grandes ==========
        if not candidatos:
            for line in lines:
                if not es_linea_limpia(line):
                    continue
                
                # Buscar $<número> o <número> grande
                nums = re.findall(r'\$\s*([\d\.\,\s]{6,})|(?<!\d)([\d\.\,]{6,})(?!\d)', line)
                for match in nums:
                    num_str = match[0] or match[1]
                    if not num_str:
                        continue
                    
                    num_clean = normalizar_numero(num_str)
                    if not num_clean or len(num_clean) < 6:
                        continue
                    
                    try:
                        valor = float(num_clean)
                        if es_monto_valido(valor):
                            # Menor confianza si no tiene etiqueta clara
                            conf = 0.85 if '$' in line else 0.75
                            candidatos.append((conf, valor, line))
                    except:
                        pass

        if not candidatos:
            return "", 0.0

        # Ordenar por confianza y valor (preferir mayores)
        candidatos.sort(key=lambda x: (x[0], x[1]), reverse=True)
        mejor_conf, mejor_valor, _ = candidatos[0]
        
        return str(int(mejor_valor)), mejor_conf
    
    # ============================================================================
    # NOMBRE - CRÍTICO - VERSION MÁS ESTRICTA
    # ============================================================================
    def extract_nombre(self, text: str, file_path: Optional[Path] = None) -> Tuple[str, float]:
        """
        Extrae nombre del prestador - VERSIÓN ULTRA-ESTRICTA
        PRIORIDADES:
        1. Nombre con ancla clara ("Nombre:", "Contribuyente:", etc.)
        2. Nombre antes del RUT (validado estrictamente)
        3. Nombre desde archivo (menor confianza)
        NUNCA tomar: glosas, descripciones, encabezados
        """
        # Recortar a zona relevante
        zona = self._recortar_boleta(text)
        lines = [l.strip() for l in zona.split('\n') if l.strip()]

        # Anclas para buscar nombre
        anclas_nombre = [
            r'Nombre\s*:',
            r'Razón\s+Social\s*:',
            r'Contribuyente\s*:',
            r'Prestador(?:\(a\))?\s*:',
            r'Emisor\s*:',
            r'Señor(?:es)?\s*:',
            r'Sr(?:a)?\.\s*:'
        ]

        # PRIORIDAD 1: Buscar con ancla
        for i, line in enumerate(lines):
            for patron_ancla in anclas_nombre:
                if re.search(patron_ancla, line, re.IGNORECASE):
                    # Extraer texto después de ":"
                    if ':' in line:
                        candidato = line.split(':', 1)[1].strip()
                        if self._es_nombre_valido_estricto(candidato):
                            return candidato[:100], 0.95
                    
                    # Buscar en siguiente línea
                    if i + 1 < len(lines):
                        candidato = lines[i + 1].strip(' :')
                        if self._es_nombre_valido_estricto(candidato):
                            return candidato[:100], 0.90

        # PRIORIDAD 2: Buscar antes del RUT
        rut_match = RUT_RE.search(zona)
        if rut_match:
            texto_antes_rut = zona[:rut_match.start()]
            lines_antes = [l.strip() for l in texto_antes_rut.split('\n') if l.strip()]
            
            # Revisar últimas 3 líneas antes del RUT
            for line in reversed(lines_antes[-3:]):
                candidato = line.strip(' :')
                if self._es_nombre_valido_estricto(candidato) and len(candidato) >= 10:
                    return candidato[:100], 0.80

        # PRIORIDAD 3: Desde nombre de archivo (muy baja confianza)
        if file_path:
            nombre_archivo = self._extraer_nombre_de_archivo(file_path)
            if nombre_archivo:
                return nombre_archivo[:100], 0.50

        return "", 0.0
    
    def _es_nombre_valido_estricto(self, texto: str) -> bool:
        """
        Validación ESTRICTA de nombre - Versión mejorada
        Rechaza: glosas, descripciones, encabezados, RUTs, fechas
        """
        if not texto or len(texto) < 5:
            return False
        
        # Limpiar y normalizar
        texto_limpio = re.sub(r'\s+', ' ', texto).strip()
        texto_lower = texto_limpio.lower()

        # RECHAZAR si tiene números (excepto "II", "III", etc.)
        if re.search(r'\d', texto_limpio):
            # Permitir números romanos pequeños
            if not re.fullmatch(r'[A-Z\sÁÉÍÓÚÑ]+(II|III|IV|V)?', texto_limpio, re.I):
                return False

        # RECHAZAR palabras clave que indican que NO es nombre
        palabras_rechazo = {
            # Términos de documentos
            'municipalidad', 'ilustre', 'boleta', 'honorarios', 'documento',
            'folio', 'nro', 'número', 'numero', 'fecha', 'total', 'monto',
            # Términos de glosas/descripciones
            'atención', 'atencion', 'profesional', 'servicio', 'prestación',
            'prestacion', 'domicilio', 'dirección', 'direccion', 'comuna',
            'teléfono', 'telefono', 'email', 'correo', 'fono',
            # Términos institucionales
            'hospital', 'cesfam', 'consultorio', 'corporación', 'corporacion',
            'fundación', 'fundacion', 'ministerio', 'servicio', 'programa',
            'departamento', 'unidad', 'sección', 'seccion', 'división', 'division',
            # Otros
            'rut', 'giro', 'actividad', 'código', 'codigo', 'timbre'
        }
        
        # Verificar cada palabra de rechazo
        for palabra in palabras_rechazo:
            if palabra in texto_lower:
                return False

        # RECHAZAR si empieza con preposiciones o artículos
        if re.match(r'^(por|para|con|en|de|del|la|el|los|las|un|una|unos|unas)\s', texto_lower):
            return False

        # RECHAZAR si tiene símbolos extraños
        if re.search(r'[<>@#$%^&*+=\[\]{}|\\;`~]', texto_limpio):
            return False

        # Debe tener al menos 2 palabras
        palabras = texto_limpio.split()
        if len(palabras) < 2:
            return False

        # Al menos 2 palabras deben tener más de 2 letras
        palabras_validas = [p for p in palabras if len(p) > 2 and re.match(r'^[A-ZÁÉÍÓÚÑa-záéíóúñ]+$', p)]
        if len(palabras_validas) < 2:
            return False

        # No debe tener muchas mayúsculas seguidas (probablemente sea un encabezado)
        mayusculas_seguidas = re.findall(r'[A-ZÁÉÍÓÚÑ]{6,}', texto_limpio)
        if len(mayusculas_seguidas) > 2:
            return False

        return True
    
    def _extraer_nombre_de_archivo(self, path: Path) -> str:
        """Intenta extraer nombre del nombre del archivo"""
        stem = path.stem
        
        # Limpiar
        nombre = re.sub(r'[_\-\.]+', ' ', stem)
        nombre = re.sub(r'\([^)]*\)', ' ', nombre)
        nombre = re.sub(r'\d+', ' ', nombre)
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        
        # Palabras a remover
        palabras_comunes = {
            'boleta', 'honorarios', 'aps', 'dir', 'pai', 'doc', 'scan',
            'pdf', 'img', 'imagen', 'archivo', 'new', 'copia'
        }
        
        tokens = nombre.split()
        tokens = [t for t in tokens if t.lower() not in palabras_comunes]
        tokens = [t for t in tokens if len(t) >= 3]
        tokens = [t for t in tokens if re.match(r'^[A-Za-zÁÉÍÓÚÑáéíóúñ]+$', t)]
        
        if len(tokens) >= 2:
            return ' '.join(tokens[:5]).title()
        
        return ""
    
    # ============================================================================
    # CONVENIO - CRÍTICO - VERSION MÁS ROBUSTA
    # ============================================================================
    def extract_convenio(self, text: str, glosa: str = "") -> Tuple[str, float]:
        """
        Extrae convenio - VERSIÓN ULTRA-ROBUSTA
        Evita falsos positivos, especialmente MUNICIPAL
        """
        base = f"{glosa or ''}\n{text or ''}"
        t = re.sub(r'\s+', ' ', (base or '').upper()).strip()

        # Neutralizar encabezados institucionales
        t = re.sub(r'\b(I\.?\s*)?MUNICIPALIDAD\s+DE\b', 'MUNI_HDR', t)
        t = re.sub(r'\bILUSTRE\s+MUNICIPALIDAD\b', 'MUNI_HDR', t)

        # Patrones por convenio (ORDENADOS POR ESPECIFICIDAD)
        CONVENIO_PATTERNS = {
            'AIDIA': {
                'patterns': [
                    r'\bAIDIA\b',
                    r'\bA\.?I\.?D\.?I\.?A\.?\b',
                    r'\bPRAPS[-\s]?AIDIA\b',
                    r'\bAYDIA\b'  # error OCR común
                ],
                'peso': 10,
                'requiere_contexto': False
            },
            'ACOMPAÑAMIENTO': {
                'patterns': [
                    r'\bACOMPAÑAMIENTO\s+PSICOSOCIAL\b',
                    r'\bACOMP\w*MIENTO\b',  # tolera errores OCR
                    r'\bPROGRAMA\s+ACOMP',
                    r'\bPSICOSOCIAL\b'
                ],
                'peso': 9,
                'requiere_contexto': False
            },
            'DIR': {
                'patterns': [
                    r'\bPROGRAMA\s+DIR\b',
                    r'\bDIR\s+APS\b',
                    r'\bPAI[-\s]?DIR\b',
                    # DIR aislado SOLO si está en contexto de programa
                    r'\bPROGRAMA\s+\w+\s+DIR\b',
                ],
                'peso': 8,
                'requiere_contexto': True
            },
            'PASMI': {
                'patterns': [
                    r'\bPASMI\b',
                    r'\bP\.?A\.?S\.?M\.?I\.?\b'
                ],
                'peso': 10,
                'requiere_contexto': False
            },
            'MEJOR NIÑEZ': {
                'patterns': [
                    r'\bMEJOR\s+NI[ÑN]EZ\b',
                    r'\bSENAME\b',
                    r'\bSPE\b',
                    r'\bNINEZ\s*/\s*SENAME\b'
                ],
                'peso': 9,
                'requiere_contexto': False
            },
            'ESPACIOS AMIGABLES': {
                'patterns': [
                    r'\bESPACIOS?\s+AMIGABLES?\b',
                    r'\bEEAA\b',
                    r'\bE\.?A\.?A\.?\b'
                ],
                'peso': 9,
                'requiere_contexto': False
            },
            'SALUD MENTAL': {
                'patterns': [
                    r'\bSALUD\s+MENTAL\b',
                    r'\bPROGRAMA\s+SALUD\s+MENTAL\b'
                ],
                'peso': 8,
                'requiere_contexto': False
            },
            'MUNICIPAL': {
                'patterns': [
                    # SOLO aceptar si tiene "CONVENIO" o "PROGRAMA" explícito
                    r'\b(CONVENIO|CONV\.?|PROGRAMA)\s+MUNICIPAL\b',
                    r'\bCONVENIO\s+SALUD\s+MUNICIPAL\b'
                ],
                'peso': 5,  # Menor peso por ser más genérico
                'requiere_contexto': True
            },
            'CHCC': {
                'patterns': [
                    r'\bCHCC\b',
                    r'\bCRECE\s+CONTIGO\b',
                    r'\bCHILE\s+CRECE\s+CONTIGO\b'
                ],
                'peso': 8,
                'requiere_contexto': False
            }
        }

        # Buscar matches
        candidatos = []  # (convenio, peso, confianza)

        for convenio, config in CONVENIO_PATTERNS.items():
            for patron in config['patterns']:
                if re.search(patron, t):
                    # Validaciones adicionales
                    if convenio == 'MUNICIPAL':
                        # No activar si solo hay encabezado
                        if t.count('MUNI_HDR') > 0 and 'CONVENIO' not in t and 'PROGRAMA' not in t:
                            continue
                    
                    if convenio == 'DIR':
                        # DIR debe tener contexto de programa
                        if not re.search(r'\b(PROGRAMA|CONVENIO)\b', t):
                            continue
                    
                    # Calcular confianza
                    conf = 0.95 if not config['requiere_contexto'] else 0.85
                    candidatos.append((convenio, config['peso'], conf))
                    break  # Solo un match por convenio

        if not candidatos:
            # Fallback por decreto (solo casos muy conocidos)
            m_dec = re.search(r'\bD\s*\.?\s*A\s*\.?\s*(\d{3,5})\b', t)
            if m_dec:
                DECREE_MAP = {
                    "612": ("ACOMPAÑAMIENTO", 0.75),
                    "1928": ("ACOMPAÑAMIENTO", 0.75),
                    "1845": ("DIR", 0.75),
                }
                resultado = DECREE_MAP.get(m_dec.group(1))
                if resultado:
                    return resultado
            
            return "", 0.30

        # Ordenar por peso (mayor es más específico) y confianza
        candidatos.sort(key=lambda x: (x[1], x[2]), reverse=True)
        mejor_convenio, _, mejor_conf = candidatos[0]
        
        return mejor_convenio, mejor_conf
    
    # ============================================================================
    # CAMPOS AUXILIARES (Ya robustos)
    # ============================================================================
    def extract_horas(self, text: str, glosa: str = "") -> str:
        """Extrae horas trabajadas - Ya robusto"""
        texto_completo = text + " " + glosa
        match = re.search(r'(\d{1,3})\s*(?:h|hrs?|horas)', texto_completo, re.IGNORECASE)
        if match:
            horas = int(match.group(1))
            if 4 <= horas <= 220:  # Rango más amplio
                return match.group(1)
        return ""
    
    def extract_decreto(self, text: str) -> str:
        """Extrae decreto alcaldicio - Ya robusto"""
        t = text.upper()
        patrones = [
            r'\bD[\.\s]*A[\.\s]*\s*(?:N[ºO°])?\s*(\d{3,5})\b',
            r'\bDECRETO\s+(?:ALCALDICIO\s+)?(?:N[ºO°])?\s*(\d{3,5})\b',
            r'\bDCTO[\.\s]+(?:N[ºO°])?\s*(\d{3,5})\b',
        ]
        for p in patrones:
            m = re.search(p, t)
            if m:
                return m.group(1)
        return ''
    
    def extract_tipo(self, text: str, glosa: str = "") -> str:
        """Extrae y normaliza tipo de pago - Ya robusto"""
        texto = (text + " " + glosa).lower()
        if re.search(r'\bsemanal(?:es)?\b', texto):
            return "semanales"
        if re.search(r'\bmensual(?:es)?\b', texto):
            return "mensuales"
        return "semanales"  # Default

    def extract_glosa(self, text: str) -> str:
        """Extrae glosa descriptiva - Ya robusto"""
        t = text
        t = re.sub(r'\s+', ' ', t)
        
        # Buscar líneas relevantes
        candidatos = []
        for line in t.splitlines():
            line_clean = line.strip()
            if len(line_clean) < 10:
                continue
            
            # Líneas que probablemente contengan glosa
            if re.search(r'(?i)(servicio|programa|honorario|hrs?|semanales|mensuales|'
                        r'atención|atencion|prestación|prestacion)', line_clean):
                candidatos.append(line_clean)
        
        # Tomar primeras 3 líneas relevantes
        glosa = ' | '.join(candidatos[:3])[:300] if candidatos else t[:300]
        
        # Limpieza
        glosa = re.sub(r'[\=\|\·\_]{1,2}', ' ', glosa)
        glosa = re.sub(r'\s{2,}', ' ', glosa).strip()
        
        return glosa
    
    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    def _norm_ocr_es(self, s: str) -> str:
        """Normaliza errores comunes de OCR en español"""
        t = s
        t = t.replace('\u00AD', '')
        t = re.sub(r'[=]+b', ' ', t, flags=re.I)
        t = re.sub(r'[,;:]+', ' ', t)
        t = re.sub(r'\s+', ' ', t)
        
        # Errores comunes OCR
        t = re.sub(r'(?i)marz0', 'marzo', t)
        t = re.sub(r'(?i)setiembre', 'septiembre', t)
        t = re.sub(r'(?i)acompa[ñn]amiento', 'acompañamiento', t)
        
        return t.strip()
    
    def _recortar_boleta(self, text: str) -> str:
        """Recorta texto a la zona útil de la boleta"""
        # Buscar inicio
        start = re.search(r'BOLETA\s+DE\s+HONORARIOS', text, re.IGNORECASE)
        if not start:
            return text[:2000]  # Primeras líneas si no encuentra
        
        # Buscar fin (zona de códigos y timbres)
        end_patterns = [
            r'Fecha\s*/\s*Hora\s*Emisión',
            r'Verifique\s+este\s+documento',
            r'RES\.\s*EX\.',
            r'código\s+verificador',
            r'timbre\s+electrónico'
        ]
        
        end_pos = len(text)
        for pattern in end_patterns:
            match = re.search(pattern, text[start.start():], re.IGNORECASE)
            if match:
                end_pos = min(end_pos, start.start() + match.start())
        
        return text[start.start():end_pos]


# ============================================================================
# PROCESADOR PRINCIPAL
# ============================================================================
class DataProcessorOptimized:
    """Procesador principal ULTRA-ROBUSTO"""
    
    def __init__(self):
        from modules.ocr_extraction import OCRExtractorOptimized
        self.ocr_extractor = OCRExtractorOptimized()
        self.field_extractor = FieldExtractor()
    
    def process_file(self, file_path: Path) -> Dict:
        """Procesa un archivo con validaciones estrictas"""
        try:
            # Paso 1: Extraer texto con OCR
            ext = file_path.suffix.lower()
            
            if ext == '.pdf':
                texts, confidences, preview = self.ocr_extractor.process_pdf_optimized(file_path)
            else:
                import cv2
                img = cv2.imread(str(file_path))
                if img is None:
                    raise ValueError(f"No se pudo leer: {file_path}")
                
                text, conf, preview_img = self.ocr_extractor.process_image_optimized(img)
                texts = [text] if text else []
                confidences = [conf] if conf else []
                preview = self.ocr_extractor._save_preview(preview_img, file_path, 0) if preview_img is not None else ""
            
            if not texts:
                raise ValueError("No se pudo extraer texto")
            
            # Paso 2: Combinar texto
            texto_completo = "\n".join(texts)
            confianza_promedio = float(np.mean(confidences)) if confidences else 0.0
            
            # Paso 3: Extraer TODOS los campos
            campos = self._extract_all_fields(texto_completo, file_path)
            
            # Paso 4: Calcular periodo datetime
            periodo_iso = campos.get('periodo_servicio', '')
            if periodo_iso and not periodo_iso.startswith('XXXX-'):
                try:
                    from datetime import datetime
                    import calendar
                    yy = int(periodo_iso[:4])
                    mm = int(periodo_iso[5:7])
                    first = datetime(yy, mm, 1)
                    last_day = calendar.monthrange(yy, mm)[1]
                    last = datetime(yy, mm, last_day)
                    campos['periodo_dt'] = first.strftime("%Y-%m-%d")
                    campos['periodo_final'] = last.strftime("%Y-%m-%d")
                except:
                    campos['periodo_dt'] = ""
                    campos['periodo_final'] = ""
            else:
                campos['periodo_dt'] = ""
                campos['periodo_final'] = ""
            
            # Paso 5: Validar y calcular monto (SOLO si no hay monto OCR)
            campos = self._validate_monto_horas(campos)
            
            # Paso 6: Metadata
            campos['archivo'] = str(file_path)
            campos['paginas'] = len(texts)
            campos['confianza'] = round(confianza_promedio, 3)
            campos['confianza_max'] = round(max(confidences), 3) if confidences else 0.0
            campos['preview_path'] = preview
            
            # Paso 7: Determinar si necesita revisión (MÁS ESTRICTO)
            campos['needs_review'] = self._needs_review_strict(campos, confianza_promedio)
            campos['quality_score'] = self._calculate_quality(campos)
            
            return campos
            
        except Exception as e:
            return {
                'archivo': str(file_path),
                'error': str(e),
                'needs_review': True,
                'confianza': 0.0,
                'quality_score': 0.0
            }
    
    def _extract_all_fields(self, text: str, file_path: Path) -> Dict:
        """Extrae todos los campos con máxima robustez"""
        ext = self.field_extractor

        # Extraer campos en orden de dependencia
        rut, rut_conf = ext.extract_rut(text)
        folio, folio_conf = ext.extract_folio(text)
        fecha_doc, fecha_conf = ext.extract_fecha(text)
        
        # Glosa primero (la usan otros extractores)
        glosa = ext.extract_glosa(text)
        
        # Periodo de servicio (usa fecha_doc para inferir año)
        periodo, periodo_conf = ext.extract_periodo_servicio(text, fecha_doc)
        
        # Monto (crítico)
        monto, monto_conf = ext.extract_monto(text)
        
        # Nombre (crítico)
        nombre, nombre_conf = ext.extract_nombre(text, file_path)
        
        # Convenio (crítico)
        convenio, convenio_conf = ext.extract_convenio(text, glosa)
        
        # Campos auxiliares
        horas = ext.extract_horas(text, glosa)
        decreto = ext.extract_decreto(text)
        tipo = ext.extract_tipo(text, glosa)

        return {
            'nombre': nombre,
            'nombre_confidence': nombre_conf,
            'rut': rut,
            'rut_confidence': rut_conf,
            'nro_boleta': folio,
            'folio_confidence': folio_conf,
            'fecha_documento': fecha_doc,
            'fecha_confidence': fecha_conf,
            'monto': monto,
            'monto_confidence': monto_conf,
            'convenio': convenio,
            'convenio_confidence': convenio_conf,
            'horas': horas,
            'decreto_alcaldicio': decreto,
            'tipo': tipo,
            'glosa': glosa,
            'periodo_servicio': periodo,
            'periodo_servicio_confidence': periodo_conf,
            'monto_origen': 'ocr' if monto else '',
        }
    
    def _validate_monto_horas(self, campos: Dict) -> Dict:
        """
        Valida coherencia monto-horas
        CRÍTICO: Solo calcular si NO hay monto OCR
        """
        monto_str = campos.get('monto', '')
        horas_str = campos.get('horas', '')
        tipo = (campos.get('tipo') or '').lower()

        # SI NO HAY MONTO pero SÍ horas → calcular
        if not monto_str and horas_str and tipo:
            try:
                horas = int(horas_str)
                if 4 <= horas <= 220:
                    base_hora = 8221.0
                    factor = 4.0 if 'semanal' in tipo else 1.0
                    calculado = round(base_hora * horas * factor)
                    
                    # Validar que esté en rango
                    if 200_000 <= calculado <= 2_500_000:
                        campos['monto'] = str(int(calculado))
                        campos['monto_confidence'] = 0.60
                        campos['monto_origen'] = 'calculado'
            except:
                pass

        # Si hay monto, validar coherencia con horas
        monto_str = campos.get('monto', '')
        if monto_str and horas_str:
            try:
                monto = float(monto_str)
                horas = int(horas_str)
                factor = 4.0 if 'semanal' in tipo else 1.0
                
                valor_hora = monto / (horas * factor)
                campos['valor_hora_calculado'] = round(valor_hora, 2)
                
                # Flag si está muy fuera de rango
                campos['monto_fuera_rango'] = not (6000 <= valor_hora <= 15000)
            except:
                pass

        return campos
    
    def _needs_review_strict(self, campos: Dict, confianza: float) -> bool:
        """
        Determina si necesita revisión manual - VERSIÓN ESTRICTA
        Prioriza precisión sobre automatización
        """
        # Campos CRÍTICOS que DEBEN estar
        tiene_rut = bool(campos.get('rut'))
        tiene_nombre = bool(campos.get('nombre'))
        tiene_folio = bool(campos.get('nro_boleta'))
        tiene_fecha = bool(campos.get('fecha_documento'))
        tiene_monto = bool(campos.get('monto'))
        tiene_convenio = bool(campos.get('convenio'))
        
        # Si falta CUALQUIER campo crítico → revisión
        if not (tiene_rut and tiene_nombre and tiene_monto):
            return True
        
        # Si la confianza es baja → revisión
        if confianza < 0.40:
            return True
        
        # Si el monto está fuera de rango → revisión
        if campos.get('monto_fuera_rango', False):
            return True
        
        # Si la confianza de campos críticos es baja → revisión
        if campos.get('nombre_confidence', 0) < 0.60:
            return True
        
        if campos.get('monto_confidence', 0) < 0.65:
            return True
        
        if campos.get('convenio_confidence', 0) < 0.50 and not tiene_convenio:
            return True
        
        # Si no tiene fecha o folio (menos crítico pero deseable)
        if not tiene_fecha or not tiene_folio:
            # Solo revisar si además la confianza es media-baja
            if confianza < 0.60:
                return True
        
        return False
    
    def _calculate_quality(self, campos: Dict) -> float:
        """Calcula score de calidad (0-1)"""
        score = 0.0
        
        # Pesos ajustados (críticos tienen más peso)
        pesos = {
            'rut': 0.20,
            'nombre': 0.20,
            'monto': 0.25,
            'nro_boleta': 0.10,
            'fecha_documento': 0.10,
            'convenio': 0.10,
            'glosa': 0.05
        }
        
        for campo, peso in pesos.items():
            if campos.get(campo):
                # Base por tener el campo
                score += peso * 0.5
                
                # Bonus por confianza
                conf_campo = campos.get(f'{campo}_confidence', 0.7)
                score += peso * 0.5 * conf_campo
        
        return round(min(score, 1.0), 3)