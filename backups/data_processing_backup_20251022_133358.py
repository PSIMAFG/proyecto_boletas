# modules/data_processing.py (Mejorado y Simplificado)
"""
Módulo de procesamiento mejorado - Combina robustez del código original
con estructura modular. Versión 3.1
"""
import re
import difflib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
from datetime import datetime
import sys
import unicodedata
import modules
from modules import memory

sys.path.append(str(Path(__file__).parent.parent))
from config import *
from modules.utils import *


class FieldExtractor:
    """Extractor de campos simplificado y robusto"""
    
    def __init__(self):
        self.meses = MESES
        self.convenios_conocidos = KNOWN_CONVENIOS
        
    def extract_rut(self, text: str) -> Tuple[str, float]:
        """Extrae RUT con validación - Método del código original"""
        # Primero buscar con ancla "RUT:"
        for match in RUT_ANCHOR_RE.finditer(text):
            rut = match.group(1)
            if dv_ok(rut):
                return rut.strip(), 0.95
        
        # Buscar cualquier RUT válido
        for match in RUT_RE.finditer(text):
            rut = match.group(1)
            if dv_ok(rut):
                return rut.strip(), 0.85
        
        return "", 0.0
    
    def extract_folio(self, text: str) -> Tuple[str, float]:
        """Extrae número de folio"""
        # Buscar con etiqueta
        match = FOLIO_RE.search(text)
        if match:
            return match.group(1).strip(), 0.90
        
        # Buscar número de 4-7 dígitos en primeras líneas
        lines = text.split('\n')[:15]
        for line in lines:
            nums = re.findall(r'\b(\d{4,7})\b', line)
            for num in nums:
                if 1000 <= int(num) <= 9999999:
                    return num, 0.60
        
        return "", 0.0
    
    def extract_fecha(self, text: str) -> Tuple[str, float]:
        """
        Extrae la FECHA DEL DOCUMENTO (la que sale en el encabezado como 'Fecha:').
        Prioriza:
        1) Líneas con 'Fecha:' (encabezado)
        2) 'Fecha / Hora Emisión'
        3) 'Fecha / Hora Impresión'
        Excluye líneas de ruido: 'Res. Ex', 'www.sii.cl', 'Verifique', 'código verificador', 'D.A.', etc.
        """
        # Normalización básica para mejorar OCR
        t = re.sub(r'[|]+', ' ', text)
        t = re.sub(r'[ \t]+', ' ', t)
        lines = [l.strip() for l in t.split('\n') if l.strip()]

        # Utilidades
        meses_map = self.meses  # {'enero':1, ...}
        ruido = ('res ex', 'res. ex', 'verifique este documento', 'www.sii.cl',
                'codigo verificador', 'código verificador', 'barra', 'resolución',
                'resolucion', 'd.a.', 'da ', 'del ')
        # Regex flexibles para "01 de abril de 2025" y "01/04/2025" o "01-04-2025"
        rex_texto = re.compile(
            r'(?i)\b(\d{1,2})\s*de\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s*de\s*(\d{2,4})'
        )
        rex_num = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b')

        def parse_texto(m):
            d = int(m.group(1))
            mes = m.group(2).lower().replace('setiembre', 'septiembre')
            y = int(m.group(3))
            y = y + 2000 if y < 100 else y
            mm = meses_map.get(mes, 0)
            if 1 <= d <= 31 and 1 <= mm <= 12 and 2015 <= y <= 2035:
                from datetime import datetime
                return datetime(y, mm, d)
            return None

        def parse_num(m):
            d = int(m.group(1)); mm = int(m.group(2)); y = int(m.group(3))
            y = y + 2000 if y < 100 else y
            if 1 <= d <= 31 and 1 <= mm <= 12 and 2015 <= y <= 2035:
                from datetime import datetime
                return datetime(y, mm, d)
            return None
        def _is_noise(l: str) -> bool:
            ll = l.lower()
            return any(t in ll for t in ('verifique este documento', 'www.sii.cl', 'res. ex n° 83', 'res. ex n', '2004'))

        # Ranking por contexto
        candidatos = []  # (score, dt)

        for line in lines:
            l = line.lower()
            # Descarta líneas de ruido
            if any(tok in l for tok in ruido):
                continue

            score_ctx = -1
            if 'fecha:' in l:
                score_ctx = 3                     # Máxima prioridad (encabezado)
            elif 'fecha / hora emisión' in l or 'fecha/ hora emisión' in l or 'fecha / hora emision' in l:
                score_ctx = 2
            elif 'fecha / hora impresión' in l or 'fecha/ hora impresión' in l or 'fecha / hora impresion' in l:
                score_ctx = 1

            # Intentar ambos formatos en la línea
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
                    continue

        # Si no hubo nada con contexto, como último recurso,
        # buscamos globalmente pero manteniendo exclusiones y años razonables
        if not candidatos:
            for line in lines:
                l = line.lower()
                if any(tok in l for tok in ruido):
                    continue
                m1 = rex_texto.search(line)
                if m1:
                    dt = parse_texto(m1)
                    if dt:
                        candidatos.append((0, dt))
                        continue
                m2 = rex_num.search(line)
                if m2:
                    dt = parse_num(m2)
                    if dt:
                        candidatos.append((0, dt))
                        continue

        if not candidatos:
            return "", 0.0

        # Elegir por mayor score de contexto y, si empata, la fecha más reciente
        candidatos.sort(key=lambda x: (x[0], x[1]))
        best = candidatos[-1][1]
        return best.strftime("%Y-%m-%d"), 0.95 if candidatos[-1][0] >= 2 else 0.90

    
    def extract_periodo_servicio(self, text: str, fecha_doc_iso: str = "") -> Tuple[str, float]:
        """
        Detecta mes/año del servicio desde glosa/texto.
        Acepta variantes con ruido de OCR: 'MARZ0', 'MARZODA', 'MES MARZO25', 'MARZO-25', 'MARZO 2025', etc.
        Si no trae año, lo infiere con la fecha del documento (servicio suele ser el mes anterior o mismo mes).
        """
        glosa = self.extract_glosa(text)
        base = glosa if glosa else text

        # Normaliza ruido antes de buscar
        base = self._norm_ocr_es(base)

        meses_map = {k.lower(): v for k, v in self.meses.items()}

        # Construimos un patrón "robusto" para cada mes que tolere basura entre letras (OCR)
        meses_regex = {
            'enero': r'e\s*n\s*e\s*r\s*o',
            'febrero': r'f\s*e\s*b\s*r\s*e\s*r\s*o',
            'marzo': r'm\s*a\s*r\s*z\s*[o0]',
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

        # Patrón: [MES] (opcional "de") (opcional año 2–4 dígitos junto o separado)
        # Ejemplos: "MES MARZO25", "MARZO 2025", "MARZO-25", "MARZO de 2025"
        mes_union = '|'.join(meses_regex[m] for m in meses_regex)
        patron = rf'(?i)\b(?:mes\s+)?({mes_union})\s*(?:de\s*)?(?:[-\s]?(\d{{2,4}}))?'

        m = re.search(patron, base, flags=re.I)
        if not m:
            return "", 0.0

        mes_canonico = None
        for nombre, rx in meses_regex.items():
            if re.fullmatch(rf'(?i){rx}', m.group(1).strip(), flags=re.I):
                mes_canonico = nombre
                break

        if not mes_canonico:
            return "", 0.0

        mes_num = meses_map.get(mes_canonico, 0)
        if not mes_num:
            return "", 0.0

        year_token = m.group(2)
        if year_token:
            try:
                y = int(year_token)
                if y < 100:
                    y += 2000
                if 2000 <= y <= 2035:
                    return f"{y:04d}-{mes_num:02d}", 0.90
            except Exception:
                pass

        # Si no hay año explícito, inferir con la fecha del documento
        if fecha_doc_iso:
            try:
                y_doc = int(fecha_doc_iso[:4]); m_doc = int(fecha_doc_iso[5:7])
                # Si el mes del servicio es MAYOR al mes del documento, asumimos servicio del año anterior.
                y = (y_doc - 1) if mes_num > m_doc else y_doc
                return f"{y:04d}-{mes_num:02d}", 0.80
            except Exception:
                pass

        return f"XXXX-{mes_num:02d}", 0.60
    
    def extract_monto(self, text: str) -> Tuple[str, float]:
        """
        Extrae MONTO BRUTO priorizando la celda 'Total Honorarios $' de la boleta.
        - Toma el número de la misma línea o en la línea siguiente (misma columna)
        - Acepta separadores . o , y espacios raros
        - Solo devuelve si es verosímil (200.000 a 2.000.000)
        - JAMÁS inventa: si no encuentra nada verosímil, devuelve "" (para que el
        validador estime *solo* si no hay OCR)
        """

        # PRIORIDAD: celda 'Total Honorarios $' (tabla SII)
        m1 = re.search(r'Total\s+Honorarios\s*\$?\s*[:\-]?\s*([\d\.\s,]+)', text, re.IGNORECASE)
        if m1:
            normalized = normaliza_monto(m1.group(1))
            if normalized:
                try:
                    val = float(normalized)
                    if plaus_amount(val):
                        return str(int(val)), 0.97
                except ValueError:
                    pass

        # Normalizaciones suaves para OCR
        t = text.replace('S$', '$').replace(' $', ' $').replace('  $', ' $')
        t = re.sub(r'[|]+', ' ', t)
        lines = [l.strip() for l in t.split('\n') if l.strip()]

        # Utilidades
        def norm_num(s: str) -> str:
            # “1.085.172”, “1,085,172”, “723.448”, “  476.818 ” -> "1085172" / "723448" / "476818"
            s = re.sub(r'[^\d,.\s]', '', s)  # deja solo dígitos y separadores
            # si hay coma y punto, nos quedamos con el separador de miles más común
            s = s.replace(' ', '')
            if s.count('.') + s.count(',') > 1:
                s = s.replace(',', '').replace('.', '')
            else:
                s = s.replace(',', '').replace('.', '')
            return s

        def plausible(v: float) -> bool:
            return 200000 <= v <= 2000000

        # 1) Buscar explícitamente “Total Honorarios”
        kw_re = re.compile(r'(?i)total\s+honorarios?\b')
        money_re = re.compile(r'\$\s*([\d\.\,\s]+)|\b(\d{1,3}(?:[.,]\d{3}){1,3})\b')

        candidatos: List[Tuple[float, float]] = []  # (conf, valor)

        for i, line in enumerate(lines):
            if kw_re.search(line):
                # números en la línea
                nums = [m.group(1) or m.group(2) for m in money_re.finditer(line)]
                # o en la siguiente (misma fila de tabla OCR)
                if i + 1 < len(lines):
                    nums += [m.group(1) or m.group(2) for m in money_re.finditer(lines[i + 1])]
                for raw in nums:
                    if not raw:
                        continue
                    val_s = norm_num(raw)
                    if not val_s:
                        continue
                    try:
                        val = float(val_s)
                        if plausible(val):
                            # muy alta confianza si viene etiquetado
                            candidatos.append((0.95, val))
                    except Exception:
                        pass

        # 2) Si no hubo etiqueta, agarrar números con $ grandes en todo el texto
        if not candidatos:
            for line in lines:
                for m in money_re.finditer(line):
                    raw = m.group(1) or m.group(2)
                    if not raw:
                        continue
                    val_s = norm_num(raw)
                    if not val_s:
                        continue
                    try:
                        val = float(val_s)
                        if plausible(val):
                            # menor confianza al no estar etiquetado
                            candidatos.append((0.75, val))
                    except Exception:
                        pass

        if not candidatos:
            return "", 0.0

        # Elegir candidato con mayor confianza; si empata, el mayor valor (suele ser bruto)
        candidatos.sort(key=lambda x: (x[0], x[1]))
        conf, best = candidatos[-1]
        return str(int(best)), conf
    
    def extract_nombre(self, text: str, file_path: Optional[Path] = None) -> Tuple[str, float]:
        """Extrae nombre - Lógica del código original"""
        # Recortar a zona de boleta
        zona = self._recortar_boleta(text)
        
        # Buscar con anclas
        nombre_anclas = [
            r'Razón\s*Social',
            r'Nombre',
            r'Contribuyente',
            r'Emisor',
            r'Señor(?:es)?',
            r'Prestador',
        ]
        
        lines = zona.split('\n')
        for i, line in enumerate(lines):
            for ancla in nombre_anclas:
                if re.search(ancla, line, re.IGNORECASE):
                    # Buscar en la misma línea después de ":"
                    if ':' in line:
                        candidate = line.split(':', 1)[1].strip()
                        if self._is_valid_name(candidate):
                            return candidate[:120], 0.85
                    
                    # Buscar en líneas siguientes
                    for j in range(i + 1, min(i + 3, len(lines))):
                        candidate = lines[j].strip(' :')
                        if self._is_valid_name(candidate):
                            return candidate[:120], 0.80
        
        # Buscar antes del RUT
        rut_match = RUT_RE.search(zona)
        if rut_match:
            texto_antes_rut = zona[:rut_match.start()]
            lines_antes = texto_antes_rut.split('\n')
            
            for line in lines_antes[-3:]:
                line = line.strip(' :')
                if self._is_valid_name(line) and len(line) > 10:
                    return line, 0.75
        
        # Intentar desde nombre de archivo
        if file_path:
            nombre_archivo = self._extract_name_from_filename(file_path)
            if nombre_archivo:
                return nombre_archivo, 0.60
        
        return "", 0.0
    
    def extract_convenio(self, text: str, glosa: str = "") -> Tuple[str, float]:
        """
        Extrae convenio evitando falsos positivos:
        - Neutraliza 'MUNICIPALIDAD' para no disparar MUNICIPAL por encabezado.
        - Patrones extensibles por convenio.
        - Sin match claro => devuelve "", 0.30 (NO inventa MUNICIPAL).
        - Pequeño fallback por decreto con baja confianza (solo si conoces el mapeo).
        """
        base = f"{glosa or ''}\n{text or ''}"
        t = re.sub(r'\s+', ' ', (base or '').upper()).strip()

        # Neutraliza encabezados 'I MUNICIPALIDAD DE ...' para que no activen MUNICIPAL
        t = re.sub(r'\bMUNICIPALIDAD\b', 'MUNI_HDR', t)

        # --------- Patrones por convenio (extensible) ---------
        CONVENIO_PATTERNS = {
            # Tal como lo vienes usando
            'AIDIA': [
                r'\bA\.?I\.?D\.?I\.?A\b', r'\bAIDIA\b', r'\bPRAPS-?AIDIA\b', r'\bAYDIA\b'
            ],
            'PASMI': [
                r'\bPASMI\b', r'\bP\.?A\.?S\.?M\.?I\b'
            ],
            'MEJOR NIÑEZ': [
                r'\bMEJOR\s+NI[ÑN]EZ\b', r'\bSENAME\b', r'\bSPE\b', r'\bNINEZ/SENAME\b'
            ],
            'ACOMPAÑAMIENTO': [
                r'\bACOMP[AÑN]AMIENTO\b',
                r'PROGRAMA\s+ACOMP',           # “H. CONV. PROGRAMA ACOMP...”
                r'PSICOSOCIAL',                # pista útil en tus boletas
                r'PSICOSICIAL'                 # OCR común
            ],
            'ESPACIOS_AMIGABLES': [
                r'\bESPACIOS?\s+AMIGABLES?\b', r'\bEEAA\b', r'\bPAI\b'
            ],
            'DIR': [
                r'\bPROGRAMA\s+DIR\b',
                r'\bDIR\s+APS\b',
                r'(?:(?<=\W)|^)\bDIR\b(?:(?=\W)|$)'   # "DIR" aislado (evita palabras largas)
            ],
            'MUNICIPAL': [
                r'\b(CONVENIO|CONV\.?|PROGRAMA)\s+MUNICIPAL\b'
            ],
            'SALUD MENTAL': [
                r'\bSALUD\s+MENTAL\b'
            ],
            # Ejemplos extra (actívalos si aplican en tu realidad):
            'CHCC': [
                r'\bCHCC\b', r'CRECE\s+CONTIGO'
            ],
            # 'PRM': [r'\bPRM\b'],  # etc...
        }

        # --------- Scoring y búsqueda ---------
        hits = []
        for conv, pats in CONVENIO_PATTERNS.items():
            for pat in pats:
                if re.search(pat, t):
                    # Reglas anti-falso-positivo:
                    if conv == 'MUNICIPAL':
                        # si solo aparece encabezado municipal, NO activar
                        if 'MUNI_HDR' in t and not re.search(r'\b(CONVENIO|CONV\.?|PROGRAMA)\s+MUNICIPAL\b', t):
                            continue
                        conf = 0.85
                    elif conv == 'ACOMPAÑAMIENTO':
                        conf = 0.95
                    else:
                        conf = 0.90
                    hits.append((conv, conf))
                    break  # ya confirmó este convenio

        if hits:
            # Prioriza por mayor confianza; si empata, deja el primero encontrado
            hits.sort(key=lambda x: x[1], reverse=True)
            return hits[0]

        # --------- Fallback por decreto (solo si conoces mapeo) ---------
        # Evita mapear a MUNICIPAL aquí. Usa solo los que sabes con certeza.
        m_dec = re.search(r'\bD\s*\.?\s*A\s*\.?\s*(\d{3,5})\b', t) or \
                re.search(r'\bDECRETO\s+ALCALDICIO\s*(?:N[ºO]\s*)?(\d{3,5})\b', t)
        if m_dec:
            DECREE_TO_CONV = {
                "612": "ACOMPAÑAMIENTO",
                "1928": "ACOMPAÑAMIENTO",
                "1845": "DIR",
            }
            conv = DECREE_TO_CONV.get(m_dec.group(1))
            if conv:
                return conv, 0.70

        # Sin match claro => vacío (revisión o memoria), nunca MUNICIPAL por defecto
        return "", 0.30
    
    def _norm_ocr_es(self, s: str) -> str:
        """
        Normaliza texto con errores típicos de OCR:
        - 0↔O en meses (MARZ0 -> MARZO)
        - Quitar basura como '=b', dobles espacios, guiones raros, etc.
        - Unificar acentos y espacios.
        """
        t = s

        # Normalizaciones básicas
        t = t.replace('\u00AD', '')  # soft hyphen
        t = re.sub(r'[=]+b', ' ', t, flags=re.I)   # '=b' -> espacio
        t = re.sub(r'[,;:]+', ' ', t)
        t = re.sub(r'\s+', ' ', t)

        # Otras confusiones de OCR: 0 (cero) por O al final de 'MARZ0'
        t = re.sub(r'(?i)marz0', 'marzo', t)

        # setiembre → septiembre
        t = re.sub(r'(?i)setiembre', 'septiembre', t)

        return t.strip()
    
    def extract_horas(self, text: str, glosa: str = "") -> str:
        """Extrae horas trabajadas"""
        texto_completo = text + " " + glosa
        
        match = re.search(r'(\d{1,3})\s*(?:h|hrs?|horas)', texto_completo, re.IGNORECASE)
        if match:
            horas = int(match.group(1))
            # Validar rango razonable (4 a 200 horas por período)
            if 4 <= horas <= 200:
                return match.group(1)
        
        return ""
    
    #def extract_decreto(self, text: str) -> str:
     #   """Extrae decreto alcaldicio"""
      #  match = re.search(r'D\.?A\.?\s*N?[°ºo]?\s*(\d{2,6})', text, re.IGNORECASE)
       # if match:
        #    return match.group(1)
        #return ""
    
    #def extract_decreto(self, text: str) -> str:
     #   """Extrae decreto alcaldicio tolerando espacios y puntos (D A / D.A / DA)."""
      #  m = re.search(r'D\s*\.?\s*A\s*\.?\s*N?[°ºo]?\s*(\d{2,6})', text, re.IGNORECASE)
       # return m.group(1) if m else ""
    
    def extract_decreto(self, text: str) -> str:
        t = self._normalize(text)
        # Variantes: D.A, D A, DA, Decreto Alcaldicio N°, Dcto
        patrones = [
            r'\bD[\. ]?A[\. ]?\s*(\d{3,5})\b',
            r'(?i)\bdecreto(?:\s+alcaldicio)?\s*(?:n[ºo]\s*)?(\d{3,5})\b',
            r'(?i)\bdcto\.?\s*(\d{3,5})\b',
        ]
        for p in patrones:
            m = re.search(p, t)
            if m:
                return m.group(1)
        return ''


    def extract_tipo(self, text: str, glosa: str = "") -> str:
        """Extrae y normaliza tipo de pago."""
        texto = (text + " " + glosa).lower()
        if re.search(r'\bsemanal(?:es)?\b', texto):
            return "semanales"
        if re.search(r'\bmensual(?:es)?\b', texto):
            return "mensuales"
        return "semanales"

    def extract_glosa(self, text: str) -> str:
        t = self._normalize(text)

        # tomar renglones que contienen claves típicas de glosa
        candidatos = []
        for line in t.splitlines():
            if re.search(r'(?i)(servicio|programa|acomp(a|á)ñamiento|honorario|hrs?|semanales|mensuales)', line):
                candidatos.append(line)

        glosa = ' | '.join(candidatos)[:300] if candidatos else t[:300]

        # limpieza suave: quita secuencias de 1–2 símbolos intercalados, colapsa espacios
        glosa = re.sub(r'[\=\|\·\_]{1,2}', ' ', glosa)
        glosa = re.sub(r'\s{2,}', ' ', glosa).strip()

        # normaliza “D.A” pegado y variantes
        glosa = re.sub(r'\bD\s*A\b', 'D.A', glosa, flags=re.I)

        return glosa
    
    # Métodos auxiliares privados
    
    def _recortar_boleta(self, text: str) -> str:
        """Recorta el texto a la zona de la boleta"""
        start = re.search(r'BOLETA\s+DE\s+HONORARIOS', text, re.IGNORECASE)
        if not start:
            return text
        
        # Buscar posibles finales
        end_patterns = [
            r'Fecha\s*/\s*Hora\s*Emisión',
            r'Verifique\s+este\s+documento',
            r'RES\.\s*EX\.',
            r'INFORME',
            r'CONTRATO'
        ]
        
        end_positions = []
        for pattern in end_patterns:
            match = re.search(pattern, text[start.start():], re.IGNORECASE)
            if match:
                end_positions.append(start.start() + match.start())
        
        if end_positions:
            return text[start.start():min(end_positions)]
        else:
            return text[start.start():]
    
    def _is_valid_name(self, text: str) -> bool:
        """Valida si un texto parece un nombre válido"""
        if not text or len(text) < 5 or len(text) > 100:
            return False
        
        # Limpiar
        text_clean = re.sub(r'\s+', ' ', text).strip()
        
        # Rechazar si tiene muchos números
        if len(re.findall(r'\d', text_clean)) > 2:
            return False
        
        # Rechazar palabras clave
        palabras_rechazo = {
            'municipalidad', 'boleta', 'honorarios', 'rut', 'fecha',
            'monto', 'total', 'documento', 'folio', 'servicio'
        }
        
        text_lower = text_clean.lower()
        if any(palabra in text_lower for palabra in palabras_rechazo):
            return False
        
        # Debe tener al menos 2 palabras
        palabras = text_clean.split()
        if len(palabras) < 2:
            return False
        
        return True
    
    def _extract_name_from_filename(self, path: Path) -> str:
        """Extrae nombre candidato del nombre del archivo"""
        stem = path.stem
        
        # Limpiar
        nombre = re.sub(r'[_\-\.]+', ' ', stem)
        nombre = re.sub(r'\([^)]*\)', ' ', nombre)
        nombre = re.sub(r'\d+', ' ', nombre)
        
        # Remover palabras comunes
        palabras_comunes = {
            'boleta', 'honorarios', 'aps', 'dir', 'pai', 'doc', 'scan'
        }
        
        tokens = [t for t in nombre.split() if t.lower() not in palabras_comunes]
        tokens = [t for t in tokens if re.match(r'^[A-Za-zÁÉÍÓÚÑáéíóúñ]{2,}$', t)]
        
        if len(tokens) >= 2:
            return ' '.join(tokens[:5]).title()
        
        return ""


class DataProcessorOptimized:
    """Procesador principal mejorado"""
    
    def __init__(self):
        from modules.ocr_extraction import OCRExtractorOptimized
        self.ocr_extractor = OCRExtractorOptimized()
        self.field_extractor = FieldExtractor()
    
    def process_file(self, file_path: Path) -> Dict:
        """Procesa un archivo con flujo mejorado"""
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
            
            # Paso 2: Combinar todo el texto extraído
            texto_completo = "\n".join(texts)
            confianza_promedio = float(np.mean(confidences)) if confidences else 0.0
            
            # Paso 3: Extraer campos del texto
            campos = self._extract_all_fields(texto_completo, file_path)

            periodo_iso = (campos.get('periodo_servicio') or '')
            if periodo_iso and not periodo_iso.startswith('XXXX-'):
                try:
                    from datetime import datetime
                    import calendar
                    yy = int(periodo_iso[:4]); mm = int(periodo_iso[5:7])
                    first = datetime(yy, mm, 1)
                    last_day = calendar.monthrange(yy, mm)[1]
                    last = datetime(yy, mm, last_day)
                    campos['periodo_dt'] = first.strftime("%Y-%m-%d")
                    campos['periodo_final'] = last.strftime("%Y-%m-%d")
                except Exception:
                    campos['periodo_dt'] = ""
                    campos['periodo_final'] = ""
            else:
                campos['periodo_dt'] = ""
                campos['periodo_final'] = ""
            
            # Paso 4: Validar monto con horas (si aplica)
            campos = self._validate_monto_horas(campos)
            
            # Paso 5: Agregar metadata
            campos['archivo'] = str(file_path)
            campos['paginas'] = len(texts)
            campos['confianza'] = round(confianza_promedio, 3)
            campos['confianza_max'] = round(max(confidences), 3) if confidences else 0.0
            campos['preview_path'] = preview
            
            # Paso 6: Determinar si necesita revisión (MENOS ESTRICTO)
            campos['needs_review'] = self._needs_review_relaxed(campos, confianza_promedio)
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
        """Extrae todos los campos del texto"""
        extractor = self.field_extractor

        # Campos base
        rut, rut_conf = extractor.extract_rut(text)
        folio, folio_conf = extractor.extract_folio(text)
        fecha, fecha_conf = extractor.extract_fecha(text)  # Fecha del documento (pago/entrega)

        # Periodo del servicio (mes) usando glosa y fecha_doc para inferir año si falta
        periodo_servicio, periodo_conf = extractor.extract_periodo_servicio(text, fecha)

        monto, monto_conf = extractor.extract_monto(text)
        nombre, nombre_conf = extractor.extract_nombre(text, file_path)

        # Glosa y convenio
        glosa = extractor.extract_glosa(text)
        convenio, convenio_conf = extractor.extract_convenio(text, glosa)

        horas = extractor.extract_horas(text, glosa)
        decreto = extractor.extract_decreto(text)
        tipo = extractor.extract_tipo(text, glosa)

        return {
            'nombre': nombre,
            'nombre_confidence': nombre_conf,
            'rut': rut,
            'rut_confidence': rut_conf,
            'nro_boleta': folio,
            'folio_confidence': folio_conf,
            'fecha_documento': fecha,
            'fecha_confidence': fecha_conf,
            'monto': monto,
            'monto_confidence': monto_conf,
            'convenio': convenio,
            'convenio_confidence': convenio_conf,
            'horas': horas,
            'decreto_alcaldicio': decreto,
            'tipo': tipo,
            'glosa': glosa,
            'periodo_servicio': periodo_servicio,                 # 'YYYY-MM' o 'XXXX-MM'
            'periodo_servicio_confidence': periodo_conf,
            'monto_origen': 'ocr' if monto else '',               # auditoría del origen del monto
        }

    def _validate_monto_horas(self, campos: Dict) -> Dict:
        """Valida coherencia y calcula monto si falta."""
        monto_str = campos.get('monto', '')
        horas_str = campos.get('horas', '')
        tipo = (campos.get('tipo') or '').lower()

        # Fallback: si NO hay monto pero sí horas/tipo -> calcular
        if (not monto_str) and horas_str and tipo:
            try:
                horas = int(horas_str)
                base_hora = 8221.0
                factor = 4.0 if 'semanal' in tipo else 1.0
                calculado = round(base_hora * horas * factor)
                campos['monto'] = str(int(calculado))
                campos['monto_confidence'] = 0.55
                campos['monto_origen'] = 'calculado'
            except Exception:
                pass

        # A partir de aquí, si hay monto/horas hacemos validación como tenías:
        monto_str = campos.get('monto', '')
        horas_str = campos.get('horas', '')
        if not monto_str or not horas_str:
            return campos

        try:
            monto = float(monto_str)
            horas = int(horas_str)
            valor_hora_estimado = monto / (horas * (4 if 'semanal' in tipo else 1))
            campos['valor_hora_calculado'] = round(valor_hora_estimado, 2)
            campos['monto_fuera_rango'] = not (7000 <= valor_hora_estimado <= 12000)
        except (ValueError, ZeroDivisionError):
            pass

        return campos
    
    def _needs_review_relaxed(self, campos: Dict, confianza: float) -> bool:
        """Determina si necesita revisión - VERSIÓN MÁS PERMISIVA"""
        # Campos críticos mínimos
        tiene_rut = bool(campos.get('rut'))
        tiene_folio = bool(campos.get('nro_boleta'))
        tiene_monto = bool(campos.get('monto'))
        
        # Si tiene los 3 campos críticos, no necesita revisión
        # aunque falten otros campos
        if tiene_rut and tiene_folio and tiene_monto:
            # Solo revisar si la confianza es MUY baja
            if confianza < 0.20:
                return True
            
            # O si el monto está muy fuera de rango
            if campos.get('monto_fuera_rango', False):
                return True
            
            return False
        
        # Si falta algún campo crítico
        if not tiene_rut or not tiene_monto:
            return True
        
        # Si la confianza es baja y faltan campos
        if confianza < 0.50:
            return True
        
        return False
    
    def _calculate_quality(self, campos: Dict) -> float:
        """Calcula score de calidad"""
        score = 0.0
        
        # Pesos por campo
        pesos = {
            'rut': 0.25,
            'nro_boleta': 0.15,
            'fecha_documento': 0.15,
            'monto': 0.25,
            'nombre': 0.10,
            'convenio': 0.05,
            'glosa': 0.05
        }
        
        for campo, peso in pesos.items():
            if campos.get(campo):
                # Valor base por tener el campo
                score += peso * 0.6
                
                # Bonificación por confianza
                conf_campo = campos.get(f'{campo}_confidence', 0.7)
                score += peso * 0.4 * conf_campo
        
        return round(min(score, 1.0), 3)