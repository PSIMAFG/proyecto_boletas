# modules/data_processing.py (Mejorado y Simplificado)
"""
MÃ³dulo de procesamiento mejorado - Combina robustez del cÃ³digo original
con estructura modular. VersiÃ³n 3.1
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
    """Extractor de campos simplificado y robusto"""
    
    def __init__(self):
        self.meses = MESES
        self.convenios_conocidos = KNOWN_CONVENIOS
        
    def extract_rut(self, text: str) -> Tuple[str, float]:
        """Extrae RUT con validaciÃ³n - MÃ©todo del cÃ³digo original"""
        # Primero buscar con ancla "RUT:"
        for match in RUT_ANCHOR_RE.finditer(text):
            rut = match.group(1)
            if dv_ok(rut):
                return rut.strip(), 0.95
        
        # Buscar cualquier RUT vÃ¡lido
        for match in RUT_RE.finditer(text):
            rut = match.group(1)
            if dv_ok(rut):
                return rut.strip(), 0.85
        
        return "", 0.0
    
    def extract_folio(self, text: str) -> Tuple[str, float]:
        """Extrae nÃºmero de folio"""
        # Buscar con etiqueta
        match = FOLIO_RE.search(text)
        if match:
            return match.group(1).strip(), 0.90
        
        # Buscar nÃºmero de 4-7 dÃ­gitos en primeras lÃ­neas
        lines = text.split('\n')[:15]
        for line in lines:
            nums = re.findall(r'\b(\d{4,7})\b', line)
            for num in nums:
                if 1000 <= int(num) <= 9999999:
                    return num, 0.60
        
        return "", 0.0
    
    def extract_fecha(self, text: str) -> Tuple[str, float]:
        """
        Extrae SOLO la fecha del encabezado 'Fecha:' del documento.
        NUNCA usa 'Fecha / Hora Impresión'.
        Prioridad absoluta:
        1) Líneas con 'Fecha:' aislado (encabezado de boleta)
        2) 'Fecha Emisión' o 'Fecha / Hora Emisión'
        3) Fechas en primeras 15 líneas sin contexto
        """
        # Normalización básica
        t = re.sub(r'[|]+', ' ', text)
        t = re.sub(r'[ \t]+', ' ', t)
        lines = [l.strip() for l in t.split('\n') if l.strip()]

        # Palabras de ruido que INVALIDAN una línea
        ruido_keywords = (
            'res ex', 'res. ex', 'verifique este documento', 'www.sii.cl',
            'codigo verificador', 'código verificador', 'timbre', 'barra',
            'resolución', 'resolucion', 'impresión', 'impresion'  # ← CLAVE: bloquear impresión
        )

        # Regex para fechas
        rex_texto = re.compile(
            r'(?i)\b(\d{1,2})\s*de\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|'
            r'septiembre|setiembre|octubre|noviembre|diciembre)\s*de\s*(\d{2,4})'
        )
        rex_num = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b')

        def parse_texto(m):
            d = int(m.group(1))
            mes = m.group(2).lower().replace('setiembre', 'septiembre')
            y = int(m.group(3))
            y = y + 2000 if y < 100 else y
            mm = self.meses.get(mes, 0)
            if 1 <= d <= 31 and 1 <= mm <= 12 and 2015 <= y <= 2035:
                try:
                    return datetime(y, mm, d)
                except:
                    return None
            return None

        def parse_num(m):
            d = int(m.group(1))
            mm = int(m.group(2))
            y = int(m.group(3))
            y = y + 2000 if y < 100 else y
            if 1 <= d <= 31 and 1 <= mm <= 12 and 2015 <= y <= 2035:
                try:
                    return datetime(y, mm, d)
                except:
                    return None
            return None

        candidatos = []  # (score, dt, line_num) para debugging

        # FASE 1: Buscar "Fecha:" PURO (sin "Hora", sin "Impresión", sin "Emisión")
        # Este es el encabezado de la boleta
        for i, line in enumerate(lines[:25]):  # solo primeras 25 líneas
            ll = line.lower()
            
            # Descartar líneas con ruido
            if any(kw in ll for kw in ruido_keywords):
                continue
            
            # Buscar "Fecha:" pero NO "Fecha / Hora" ni "Fecha Emisión"
            # Debe ser "Fecha:" seguido directamente de la fecha
            if re.search(r'\bfecha\s*:', ll):
                # Verificar que NO sea "Fecha / Hora" o "Fecha Emisión"
                if not re.search(r'fecha\s*[/\s]*hora|fecha\s+emisi[oó]n', ll):
                    # ¡Este es el encabezado puro! Máxima prioridad
                    m1 = rex_texto.search(line)
                    if m1:
                        dt = parse_texto(m1)
                        if dt:
                            candidatos.append((100, dt, i))  # Score 100 = máxima prioridad
                            continue
                    
                    m2 = rex_num.search(line)
                    if m2:
                        dt = parse_num(m2)
                        if dt:
                            candidatos.append((100, dt, i))
                            continue

        # FASE 2: Si no encontramos "Fecha:" puro, buscar "Fecha Emisión" o "Fecha / Hora Emisión"
        if not candidatos:
            for i, line in enumerate(lines[:25]):
                ll = line.lower()
                
                # Descartar ruido
                if any(kw in ll for kw in ruido_keywords):
                    continue
                
                # Buscar "Fecha Emisión" o "Fecha / Hora Emisión"
                if re.search(r'fecha\s*[/\s]*hora\s*emisi[oó]n|fecha\s+emisi[oó]n', ll):
                    m1 = rex_texto.search(line)
                    if m1:
                        dt = parse_texto(m1)
                        if dt:
                            candidatos.append((50, dt, i))  # Score 50 = segunda prioridad
                            continue
                    
                    m2 = rex_num.search(line)
                    if m2:
                        dt = parse_num(m2)
                        if dt:
                            candidatos.append((50, dt, i))
                            continue

        # FASE 3: Como último recurso, buscar fechas en primeras 15 líneas (sin contexto)
        # PERO NUNCA en líneas con ruido
        if not candidatos:
            for i, line in enumerate(lines[:15]):
                ll = line.lower()
                
                # Descartar ruido ESTRICTAMENTE
                if any(kw in ll for kw in ruido_keywords):
                    continue
                
                # Descartar si tiene palabras sospechosas
                if any(x in ll for x in ['hora', 'timbre', 'res.', 'www', 'sii.cl']):
                    continue
                
                m1 = rex_texto.search(line)
                if m1:
                    dt = parse_texto(m1)
                    if dt:
                        candidatos.append((10, dt, i))  # Score 10 = baja prioridad
                        continue
                
                m2 = rex_num.search(line)
                if m2:
                    dt = parse_num(m2)
                    if dt:
                        candidatos.append((10, dt, i))
                        continue

        if not candidatos:
            return "", 0.0

        # Ordenar por score (mayor primero), luego por fecha más reciente
        candidatos.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        best_score, best_dt, _ = candidatos[0]
        
        # Confianza según el score
        if best_score >= 100:
            conf = 0.98
        elif best_score >= 50:
            conf = 0.90
        else:
            conf = 0.75

        return best_dt.strftime("%Y-%m-%d"), conf

    
    def extract_periodo_servicio(self, text: str, fecha_doc_iso: str = "") -> Tuple[str, float]:
        """
        Detecta mes/aÃ±o del servicio desde glosa/texto.
        Acepta variantes con ruido de OCR: 'MARZ0', 'MARZODA', 'MES MARZO25', 'MARZO-25', 'MARZO 2025', etc.
        Si no trae aÃ±o, lo infiere con la fecha del documento (servicio suele ser el mes anterior o mismo mes).
        """
        glosa = self.extract_glosa(text)
        base = glosa if glosa else text

        # Normaliza ruido antes de buscar
        base = self._norm_ocr_es(base)

        meses_map = {k.lower(): v for k, v in self.meses.items()}

        # Construimos un patrÃ³n "robusto" para cada mes que tolere basura entre letras (OCR)
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

        # PatrÃ³n: [MES] (opcional "de") (opcional aÃ±o 2â€“4 dÃ­gitos junto o separado)
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

        # Si no hay aÃ±o explÃ­cito, inferir con la fecha del documento
        if fecha_doc_iso:
            try:
                y_doc = int(fecha_doc_iso[:4]); m_doc = int(fecha_doc_iso[5:7])
                # Si el mes del servicio es MAYOR al mes del documento, asumimos servicio del aÃ±o anterior.
                y = (y_doc - 1) if mes_num > m_doc else y_doc
                return f"{y:04d}-{mes_num:02d}", 0.80
            except Exception:
                pass

        return f"XXXX-{mes_num:02d}", 0.60
    
    def extract_monto(self, text: str) -> Tuple[str, float]:
        """
        Extrae MONTO BRUTO priorizando la celda 'Total Honorarios $' de la boleta.
        - Toma el nÃºmero de la misma lÃ­nea o en la lÃ­nea siguiente (misma columna)
        - Acepta separadores . o , y espacios raros
        - Solo devuelve si es verosÃ­mil (200.000 a 2.000.000)
        - JAMÃS inventa: si no encuentra nada verosÃ­mil, devuelve "" (para que el
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
            # â€œ1.085.172â€, â€œ1,085,172â€, â€œ723.448â€, â€œ  476.818 â€ -> "1085172" / "723448" / "476818"
            s = re.sub(r'[^\d,.\s]', '', s)  # deja solo dÃ­gitos y separadores
            # si hay coma y punto, nos quedamos con el separador de miles mÃ¡s comÃºn
            s = s.replace(' ', '')
            if s.count('.') + s.count(',') > 1:
                s = s.replace(',', '').replace('.', '')
            else:
                s = s.replace(',', '').replace('.', '')
            return s

        def plausible(v: float) -> bool:
            return 200000 <= v <= 2000000

        # 1) Buscar explÃ­citamente â€œTotal Honorariosâ€
        kw_re = re.compile(r'(?i)total\s+honorarios?\b')
        money_re = re.compile(r'\$\s*([\d\.\,\s]+)|\b(\d{1,3}(?:[.,]\d{3}){1,3})\b')

        candidatos: List[Tuple[float, float]] = []  # (conf, valor)

        for i, line in enumerate(lines):
            if kw_re.search(line):
                # nÃºmeros en la lÃ­nea
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

        # 2) Si no hubo etiqueta, agarrar nÃºmeros con $ grandes en todo el texto
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
        """Extrae nombre - LÃ³gica del cÃ³digo original"""
        # Recortar a zona de boleta
        zona = self._recortar_boleta(text)
        
        # Buscar con anclas
        nombre_anclas = [
            r'RazÃ³n\s*Social',
            r'Nombre',
            r'Contribuyente',
            r'Emisor',
            r'SeÃ±or(?:es)?',
            r'Prestador',
        ]
        
        lines = zona.split('\n')
        for i, line in enumerate(lines):
            for ancla in nombre_anclas:
                if re.search(ancla, line, re.IGNORECASE):
                    # Buscar en la misma lÃ­nea despuÃ©s de ":"
                    if ':' in line:
                        candidate = line.split(':', 1)[1].strip()
                        if self._is_valid_name(candidate):
                            return candidate[:120], 0.85
                    
                    # Buscar en lÃ­neas siguientes
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
        - PequeÃ±o fallback por decreto con baja confianza (solo si conoces el mapeo).
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
            'MEJOR NIÃ‘EZ': [
                r'\bMEJOR\s+NI[Ã‘N]EZ\b', r'\bSENAME\b', r'\bSPE\b', r'\bNINEZ/SENAME\b'
            ],
            'ACOMPAÃ‘AMIENTO': [
                r'\bACOMP[AÃ‘N]AMIENTO\b',
                r'PROGRAMA\s+ACOMP',           # â€œH. CONV. PROGRAMA ACOMP...â€
                r'PSICOSOCIAL',                # pista Ãºtil en tus boletas
                r'PSICOSICIAL'                 # OCR comÃºn
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
            # Ejemplos extra (actÃ­valos si aplican en tu realidad):
            'CHCC': [
                r'\bCHCC\b', r'CRECE\s+CONTIGO'
            ],
            # 'PRM': [r'\bPRM\b'],  # etc...
        }

        # --------- Scoring y bÃºsqueda ---------
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
                    elif conv == 'ACOMPAÃ‘AMIENTO':
                        conf = 0.95
                    else:
                        conf = 0.90
                    hits.append((conv, conf))
                    break  # ya confirmÃ³ este convenio

        if hits:
            # Prioriza por mayor confianza; si empata, deja el primero encontrado
            hits.sort(key=lambda x: x[1], reverse=True)
            return hits[0]

        # --------- Fallback por decreto (solo si conoces mapeo) ---------
        # Evita mapear a MUNICIPAL aquÃ­. Usa solo los que sabes con certeza.
        m_dec = re.search(r'\bD\s*\.?\s*A\s*\.?\s*(\d{3,5})\b', t) or \
                re.search(r'\bDECRETO\s+ALCALDICIO\s*(?:N[ÂºO]\s*)?(\d{3,5})\b', t)
        if m_dec:
            DECREE_TO_CONV = {
                "612": "ACOMPAÃ‘AMIENTO",
                "1928": "ACOMPAÃ‘AMIENTO",
                "1845": "DIR",
            }
            conv = DECREE_TO_CONV.get(m_dec.group(1))
            if conv:
                return conv, 0.70

        # Sin match claro => vacÃ­o (revisiÃ³n o memoria), nunca MUNICIPAL por defecto
        return "", 0.30
    
    def _norm_ocr_es(self, s: str) -> str:
        """
        Normaliza texto con errores tÃ­picos de OCR:
        - 0â†”O en meses (MARZ0 -> MARZO)
        - Quitar basura como '=b', dobles espacios, guiones raros, etc.
        - Unificar acentos y espacios.
        """
        t = s

        # Normalizaciones bÃ¡sicas
        t = t.replace('\u00AD', '')  # soft hyphen
        t = re.sub(r'[=]+b', ' ', t, flags=re.I)   # '=b' -> espacio
        t = re.sub(r'[,;:]+', ' ', t)
        t = re.sub(r'\s+', ' ', t)

        # Otras confusiones de OCR: 0 (cero) por O al final de 'MARZ0'
        t = re.sub(r'(?i)marz0', 'marzo', t)

        # setiembre â†’ septiembre
        t = re.sub(r'(?i)setiembre', 'septiembre', t)

        return t.strip()
    
    def extract_horas(self, text: str, glosa: str = "") -> str:
        """Extrae horas trabajadas"""
        texto_completo = text + " " + glosa
        
        match = re.search(r'(\d{1,3})\s*(?:h|hrs?|horas)', texto_completo, re.IGNORECASE)
        if match:
            horas = int(match.group(1))
            # Validar rango razonable (4 a 200 horas por perÃ­odo)
            if 4 <= horas <= 200:
                return match.group(1)
        
        return ""
    
    #def extract_decreto(self, text: str) -> str:
     #   """Extrae decreto alcaldicio"""
      #  match = re.search(r'D\.?A\.?\s*N?[Â°Âºo]?\s*(\d{2,6})', text, re.IGNORECASE)
       # if match:
        #    return match.group(1)
        #return ""
    
    #def extract_decreto(self, text: str) -> str:
     #   """Extrae decreto alcaldicio tolerando espacios y puntos (D A / D.A / DA)."""
      #  m = re.search(r'D\s*\.?\s*A\s*\.?\s*N?[Â°Âºo]?\s*(\d{2,6})', text, re.IGNORECASE)
       # return m.group(1) if m else ""
    
    def extract_decreto(self, text: str) -> str:
        t = self._normalize(text)
        # Variantes: D.A, D A, DA, Decreto Alcaldicio NÂ°, Dcto
        patrones = [
            r'\bD[\. ]?A[\. ]?\s*(\d{3,5})\b',
            r'(?i)\bdecreto(?:\s+alcaldicio)?\s*(?:n[Âºo]\s*)?(\d{3,5})\b',
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

        # tomar renglones que contienen claves tÃ­picas de glosa
        candidatos = []
        for line in t.splitlines():
            if re.search(r'(?i)(servicio|programa|acomp(a|Ã¡)Ã±amiento|honorario|hrs?|semanales|mensuales)', line):
                candidatos.append(line)

        glosa = ' | '.join(candidatos)[:300] if candidatos else t[:300]

        # limpieza suave: quita secuencias de 1â€“2 sÃ­mbolos intercalados, colapsa espacios
        glosa = re.sub(r'[\=\|\Â·\_]{1,2}', ' ', glosa)
        glosa = re.sub(r'\s{2,}', ' ', glosa).strip()

        # normaliza â€œD.Aâ€ pegado y variantes
        glosa = re.sub(r'\bD\s*A\b', 'D.A', glosa, flags=re.I)

        return glosa
    
    # MÃ©todos auxiliares privados
    
    def _recortar_boleta(self, text: str) -> str:
        """Recorta el texto a la zona de la boleta"""
        start = re.search(r'BOLETA\s+DE\s+HONORARIOS', text, re.IGNORECASE)
        if not start:
            return text
        
        # Buscar posibles finales
        end_patterns = [
            r'Fecha\s*/\s*Hora\s*EmisiÃ³n',
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
        """Valida si un texto parece un nombre vÃ¡lido"""
        if not text or len(text) < 5 or len(text) > 100:
            return False
        
        # Limpiar
        text_clean = re.sub(r'\s+', ' ', text).strip()
        
        # Rechazar si tiene muchos nÃºmeros
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
        tokens = [t for t in tokens if re.match(r'^[A-Za-zÃÃ‰ÃÃ“ÃšÃ‘Ã¡Ã©Ã­Ã³ÃºÃ±]{2,}$', t)]
        
        if len(tokens) >= 2:
            return ' '.join(tokens[:5]).title()
        
        return ""
    
    def _normalize(self, text: str) -> str:
        """Normaliza texto para procesamiento"""
        if not text:
            return ""
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        # Normalizar puntos y comas
        text = text.replace('..', '.').replace(',,', ',')
        # Quitar caracteres de control
        text = ''.join(c for c in text if c.isprintable() or c in '\n\t')
        return text.strip()


class DataProcessorOptimized:
    """Procesador principal mejorado"""
    
    def __init__(self):
        from modules.ocr_extraction import OCRExtractorOptimized
        from modules.memory import Memory
        self.ocr_extractor = OCRExtractorOptimized()
        self.field_extractor = FieldExtractor()
        self.memory = Memory()
    
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
            
            # Paso 2: Combinar todo el texto extraÃ­do
            texto_completo = "\n".join(texts)
            confianza_promedio = float(np.mean(confidences)) if confidences else 0.0
            
            # Paso 3: Extraer campos del texto
            campos = self._extract_all_fields(texto_completo, file_path)
            
            # Paso 3.5: Autocompletar campos con memoria histórica
            campos = self.memory.autofill(campos)

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
            
            # Paso 6: Determinar si necesita revisiÃ³n (MENOS ESTRICTO)
            campos['needs_review'] = self._needs_review_relaxed(campos, confianza_promedio)
            campos['quality_score'] = self._calculate_quality(campos)
            
            # Paso 7: Aprender de este registro para mejorar futuros procesamientos
            if not campos.get('error') and campos.get('rut'):
                self.memory.learn(campos)
            
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

        # Periodo del servicio (mes) usando glosa y fecha_doc para inferir aÃ±o si falta
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
            'monto_origen': 'ocr' if monto else '',               # auditorÃ­a del origen del monto
        }

    def _validate_monto_horas(self, campos: Dict) -> Dict:
        """Valida coherencia y calcula monto si falta."""
        monto_str = campos.get('monto', '')
        horas_str = campos.get('horas', '')
        tipo = (campos.get('tipo') or '').lower()

        # Fallback: si NO hay monto pero sÃ­ horas/tipo -> calcular
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

        # A partir de aquÃ­, si hay monto/horas hacemos validaciÃ³n como tenÃ­as:
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
        """Determina si necesita revisiÃ³n - VERSIÃ“N MÃS PERMISIVA"""
        # Campos crÃ­ticos mÃ­nimos
        tiene_rut = bool(campos.get('rut'))
        tiene_folio = bool(campos.get('nro_boleta'))
        tiene_monto = bool(campos.get('monto'))
        
        # Si tiene los 3 campos crÃ­ticos, no necesita revisiÃ³n
        # aunque falten otros campos
        if tiene_rut and tiene_folio and tiene_monto:
            # Solo revisar si la confianza es MUY baja
            if confianza < 0.20:
                return True
            
            # O si el monto estÃ¡ muy fuera de rango
            if campos.get('monto_fuera_rango', False):
                return True
            
            return False
        
        # Si falta algÃºn campo crÃ­tico
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
                
                # BonificaciÃ³n por confianza
                conf_campo = campos.get(f'{campo}_confidence', 0.7)
                score += peso * 0.4 * conf_campo
        
        return round(min(score, 1.0), 3)