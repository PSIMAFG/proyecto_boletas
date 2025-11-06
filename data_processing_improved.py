# modules/data_processing.py (Ultra-Mejorado v3.2)
"""
Versión 3.2 Ultra-Mejorada:
- Extrae glosa PRIMERO para usar su información
- Segunda pasada de extracción si faltan campos críticos
- Búsqueda inversa en memoria (nombre → RUT, RUT → nombre)
- Criterios de revisión MUCHO más relajados
- Autocompletado inteligente antes de pedir revisión
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
    """Extractor de campos con inteligencia mejorada"""
    
    def __init__(self):
        self.meses = MESES
        self.convenios_conocidos = KNOWN_CONVENIOS
    
    def extract_from_glosa(self, glosa: str, campo: str) -> Tuple[str, float]:
        """
        Extrae un campo específico desde la glosa si no se encontró en el texto principal
        """
        if not glosa:
            return "", 0.0
        
        if campo == 'fecha':
            return self.extract_fecha(glosa)
        elif campo == 'convenio':
            return self.extract_convenio(glosa, glosa)
        elif campo == 'periodo':
            return self.extract_periodo_servicio(glosa, "")
        elif campo == 'decreto':
            return self.extract_decreto(glosa), 0.7
        elif campo == 'horas':
            horas = self.extract_horas(glosa, "")
            return horas, 0.7 if horas else 0.0
        
        return "", 0.0
    
    def extract_rut(self, text: str) -> Tuple[str, float]:
        """Extrae RUT con validación"""
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
        match = FOLIO_RE.search(text)
        if match:
            return match.group(1).strip(), 0.90
        
        lines = text.split('\n')[:15]
        for line in lines:
            nums = re.findall(r'\b(\d{4,7})\b', line)
            for num in nums:
                if 1000 <= int(num) <= 9999999:
                    return num, 0.60
        
        return "", 0.0
    
    def extract_fecha(self, text: str) -> Tuple[str, float]:
        """Extrae SOLO fecha del encabezado, nunca de impresión"""
        t = re.sub(r'[|]+', ' ', text)
        t = re.sub(r'[ \t]+', ' ', t)
        lines = [l.strip() for l in t.split('\n') if l.strip()]

        ruido_keywords = (
            'res ex', 'res. ex', 'verifique este documento', 'www.sii.cl',
            'codigo verificador', 'código verificador', 'timbre', 'barra',
            'resolución', 'resolucion', 'impresión', 'impresion'
        )

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

        candidatos = []

        # FASE 1: "Fecha:" puro
        for i, line in enumerate(lines[:25]):
            ll = line.lower()
            if any(kw in ll for kw in ruido_keywords):
                continue
            if re.search(r'\bfecha\s*:', ll):
                if not re.search(r'fecha\s*[/\s]*hora|fecha\s+emisi[oó]n', ll):
                    m1 = rex_texto.search(line)
                    if m1:
                        dt = parse_texto(m1)
                        if dt:
                            candidatos.append((100, dt, i))
                            continue
                    m2 = rex_num.search(line)
                    if m2:
                        dt = parse_num(m2)
                        if dt:
                            candidatos.append((100, dt, i))
                            continue

        # FASE 2: "Fecha Emisión"
        if not candidatos:
            for i, line in enumerate(lines[:25]):
                ll = line.lower()
                if any(kw in ll for kw in ruido_keywords):
                    continue
                if re.search(r'fecha\s*[/\s]*hora\s*emisi[oó]n|fecha\s+emisi[oó]n', ll):
                    m1 = rex_texto.search(line)
                    if m1:
                        dt = parse_texto(m1)
                        if dt:
                            candidatos.append((50, dt, i))
                            continue
                    m2 = rex_num.search(line)
                    if m2:
                        dt = parse_num(m2)
                        if dt:
                            candidatos.append((50, dt, i))
                            continue

        # FASE 3: Fechas en primeras líneas
        if not candidatos:
            for i, line in enumerate(lines[:15]):
                ll = line.lower()
                if any(kw in ll for kw in ruido_keywords):
                    continue
                if any(x in ll for x in ['hora', 'timbre', 'res.', 'www', 'sii.cl']):
                    continue
                m1 = rex_texto.search(line)
                if m1:
                    dt = parse_texto(m1)
                    if dt:
                        candidatos.append((10, dt, i))
                        continue
                m2 = rex_num.search(line)
                if m2:
                    dt = parse_num(m2)
                    if dt:
                        candidatos.append((10, dt, i))
                        continue

        if not candidatos:
            return "", 0.0

        candidatos.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_score, best_dt, _ = candidatos[0]
        
        if best_score >= 100:
            conf = 0.98
        elif best_score >= 50:
            conf = 0.90
        else:
            conf = 0.75

        return best_dt.strftime("%Y-%m-%d"), conf
    
    def extract_periodo_servicio(self, text: str, fecha_doc_iso: str = "") -> Tuple[str, float]:
        """Detecta mes/año del servicio desde glosa/texto"""
        base = self._norm_ocr_es(text)
        meses_map = {k.lower(): v for k, v in self.meses.items()}

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

        if fecha_doc_iso:
            try:
                y_doc = int(fecha_doc_iso[:4])
                m_doc = int(fecha_doc_iso[5:7])
                y = (y_doc - 1) if mes_num > m_doc else y_doc
                return f"{y:04d}-{mes_num:02d}", 0.80
            except Exception:
                pass

        return f"XXXX-{mes_num:02d}", 0.60
    
    def extract_monto(self, text: str) -> Tuple[str, float]:
        """Extrae MONTO BRUTO priorizando 'Total Honorarios $'"""
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

        t = text.replace('S$', '$').replace(' $', ' $')
        t = re.sub(r'[|]+', ' ', t)
        lines = [l.strip() for l in t.split('\n') if l.strip()]

        def norm_num(s: str) -> str:
            s = re.sub(r'[^\d,.\s]', '', s)
            s = s.replace(' ', '')
            if s.count('.') + s.count(',') > 1:
                s = s.replace(',', '').replace('.', '')
            else:
                s = s.replace(',', '').replace('.', '')
            return s

        def plausible(v: float) -> bool:
            return 200000 <= v <= 2000000

        kw_re = re.compile(r'(?i)total\s+honorarios?\b')
        money_re = re.compile(r'\$\s*([\d\.\,\s]+)|\b(\d{1,3}(?:[.,]\d{3}){1,3})\b')

        candidatos: List[Tuple[float, float]] = []

        for i, line in enumerate(lines):
            if kw_re.search(line):
                nums = [m.group(1) or m.group(2) for m in money_re.finditer(line)]
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
                            candidatos.append((0.95, val))
                    except Exception:
                        pass

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
                            candidatos.append((0.75, val))
                    except Exception:
                        pass

        if not candidatos:
            return "", 0.0

        candidatos.sort(key=lambda x: (x[0], x[1]))
        conf, best = candidatos[-1]
        return str(int(best)), conf
    
    def extract_nombre(self, text: str, file_path: Optional[Path] = None) -> Tuple[str, float]:
        """Extrae nombre con múltiples estrategias"""
        zona = self._recortar_boleta(text)
        
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
                    if ':' in line:
                        candidate = line.split(':', 1)[1].strip()
                        if self._is_valid_name(candidate):
                            return candidate[:120], 0.85
                    
                    for j in range(i + 1, min(i + 3, len(lines))):
                        candidate = lines[j].strip(' :')
                        if self._is_valid_name(candidate):
                            return candidate[:120], 0.80
        
        rut_match = RUT_RE.search(zona)
        if rut_match:
            texto_antes_rut = zona[:rut_match.start()]
            lines_antes = texto_antes_rut.split('\n')
            
            for line in lines_antes[-3:]:
                line = line.strip(' :')
                if self._is_valid_name(line) and len(line) > 10:
                    return line, 0.75
        
        if file_path:
            nombre_archivo = self._extract_name_from_filename(file_path)
            if nombre_archivo:
                return nombre_archivo, 0.60
        
        return "", 0.0
    
    def extract_convenio(self, text: str, glosa: str = "") -> Tuple[str, float]:
        """Extrae convenio evitando falsos positivos"""
        base = f"{glosa or ''}\n{text or ''}"
        t = re.sub(r'\s+', ' ', (base or '').upper()).strip()
        t = re.sub(r'\bMUNICIPALIDAD\b', 'MUNI_HDR', t)

        CONVENIO_PATTERNS = {
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
                r'PROGRAMA\s+ACOMP',
                r'PSICOSOCIAL',
                r'PSICOSICIAL'
            ],
            'ESPACIOS_AMIGABLES': [
                r'\bESPACIOS?\s+AMIGABLES?\b', r'\bEEAA\b', r'\bPAI\b'
            ],
            'DIR': [
                r'\bPROGRAMA\s+DIR\b',
                r'\bDIR\s+APS\b',
                r'(?:(?<=\W)|^)\bDIR\b(?:(?=\W)|$)'
            ],
            'MUNICIPAL': [
                r'\b(CONVENIO|CONV\.?|PROGRAMA)\s+MUNICIPAL\b'
            ],
            'SALUD MENTAL': [
                r'\bSALUD\s+MENTAL\b'
            ],
        }

        hits = []
        for conv, pats in CONVENIO_PATTERNS.items():
            for pat in pats:
                if re.search(pat, t):
                    if conv == 'MUNICIPAL':
                        if 'MUNI_HDR' in t and not re.search(r'\b(CONVENIO|CONV\.?|PROGRAMA)\s+MUNICIPAL\b', t):
                            continue
                        conf = 0.85
                    elif conv == 'ACOMPAÑAMIENTO':
                        conf = 0.95
                    else:
                        conf = 0.90
                    hits.append((conv, conf))
                    break

        if hits:
            hits.sort(key=lambda x: x[1], reverse=True)
            return hits[0]

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

        return "", 0.30
    
    def _norm_ocr_es(self, s: str) -> str:
        """Normaliza errores OCR típicos"""
        t = s
        t = t.replace('\u00AD', '')
        t = re.sub(r'[=]+b', ' ', t, flags=re.I)
        t = re.sub(r'[,;:]+', ' ', t)
        t = re.sub(r'\s+', ' ', t)
        t = re.sub(r'(?i)marz0', 'marzo', t)
        t = re.sub(r'(?i)setiembre', 'septiembre', t)
        return t.strip()
    
    def extract_horas(self, text: str, glosa: str = "") -> str:
        """Extrae horas trabajadas"""
        texto_completo = text + " " + glosa
        match = re.search(r'(\d{1,3})\s*(?:h|hrs?|horas)', texto_completo, re.IGNORECASE)
        if match:
            horas = int(match.group(1))
            if 4 <= horas <= 200:
                return match.group(1)
        return ""
    
    def extract_decreto(self, text: str) -> str:
        """Extrae decreto alcaldicio"""
        t = self._normalize(text)
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
        """Extrae tipo de pago"""
        texto = (text + " " + glosa).lower()
        if re.search(r'\bsemanal(?:es)?\b', texto):
            return "semanales"
        if re.search(r'\bmensual(?:es)?\b', texto):
            return "mensuales"
        return "semanales"

    def extract_glosa(self, text: str) -> str:
        """Extrae glosa descriptiva"""
        t = self._normalize(text)
        candidatos = []
        for line in t.splitlines():
            if re.search(r'(?i)(servicio|programa|acomp(a|á)ñamiento|honorario|hrs?|semanales|mensuales)', line):
                candidatos.append(line)

        glosa = ' | '.join(candidatos)[:300] if candidatos else t[:300]
        glosa = re.sub(r'[\=\|\_]{1,2}', ' ', glosa)
        glosa = re.sub(r'\s{2,}', ' ', glosa).strip()
        glosa = re.sub(r'\bD\s*A\b', 'D.A', glosa, flags=re.I)
        return glosa
    
    def _recortar_boleta(self, text: str) -> str:
        """Recorta texto a zona relevante"""
        start = re.search(r'BOLETA\s+DE\s+HONORARIOS', text, re.IGNORECASE)
        if not start:
            return text
        
        end_patterns = [
            r'Fecha\s*/\s*Hora\s*Emisión',
            r'Verifique\s+este\s+documento',
            r'RES\.\s*EX\.',
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
        """Valida si texto es nombre válido"""
        if not text or len(text) < 5 or len(text) > 100:
            return False
        
        text_clean = re.sub(r'\s+', ' ', text).strip()
        
        if len(re.findall(r'\d', text_clean)) > 2:
            return False
        
        palabras_rechazo = {
            'municipalidad', 'boleta', 'honorarios', 'rut', 'fecha',
            'monto', 'total', 'documento', 'folio', 'servicio'
        }
        
        text_lower = text_clean.lower()
        if any(palabra in text_lower for palabra in palabras_rechazo):
            return False
        
        palabras = text_clean.split()
        if len(palabras) < 2:
            return False
        
        return True
    
    def _extract_name_from_filename(self, path: Path) -> str:
        """Extrae nombre del archivo"""
        stem = path.stem
        nombre = re.sub(r'[_\-\.]+', ' ', stem)
        nombre = re.sub(r'\([^)]*\)', ' ', nombre)
        nombre = re.sub(r'\d+', ' ', nombre)
        
        palabras_comunes = {
            'boleta', 'honorarios', 'aps', 'dir', 'pai', 'doc', 'scan'
        }
        
        tokens = [t for t in nombre.split() if t.lower() not in palabras_comunes]
        tokens = [t for t in tokens if re.match(r'^[A-Za-zÁÉÍÓÚÑáéíóúñ]{2,}$', t)]
        
        if len(tokens) >= 2:
            return ' '.join(tokens[:5]).title()
        
        return ""
    
    def _normalize(self, text: str) -> str:
        """Normaliza texto"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('..', '.').replace(',,', ',')
        text = ''.join(c for c in text if c.isprintable() or c in '\n\t')
        return text.strip()


class DataProcessorOptimized:
    """Procesador Ultra-Mejorado v3.2"""
    
    def __init__(self):
        from modules.ocr_extraction import OCRExtractorOptimized
        from modules.memory import Memory
        self.ocr_extractor = OCRExtractorOptimized()
        self.field_extractor = FieldExtractor()
        self.memory = Memory()
    
    def process_file(self, file_path: Path) -> Dict:
        """Procesa archivo con DOBLE PASADA y autocompletado agresivo"""
        try:
            # Paso 1: OCR
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
            
            texto_completo = "\n".join(texts)
            confianza_promedio = float(np.mean(confidences)) if confidences else 0.0
            
            # Paso 2: PRIMERA PASADA - Extracción inicial
            campos = self._extract_all_fields(texto_completo, file_path)
            
            # Paso 3: Autocompletar con memoria (incluye búsqueda inversa)
            campos = self._autofill_inteligente(campos)
            
            # Paso 4: SEGUNDA PASADA - Reintentar campos faltantes desde glosa
            campos = self._segunda_pasada_desde_glosa(campos, texto_completo)
            
            # Paso 5: Validar monto/horas
            campos = self._validate_monto_horas(campos)
            
            # Paso 6: Calcular periodo_dt
            periodo_iso = (campos.get('periodo_servicio') or '')
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
                except Exception:
                    campos['periodo_dt'] = ""
                    campos['periodo_final'] = ""
            else:
                campos['periodo_dt'] = ""
                campos['periodo_final'] = ""
            
            # Paso 7: Metadata
            campos['archivo'] = str(file_path)
            campos['paginas'] = len(texts)
            campos['confianza'] = round(confianza_promedio, 3)
            campos['confianza_max'] = round(max(confidences), 3) if confidences else 0.0
            campos['preview_path'] = preview
            
            # Paso 8: Decisión de revisión (ULTRA-RELAJADA)
            campos['needs_review'] = self._needs_review_ultra_relaxed(campos, confianza_promedio)
            campos['quality_score'] = self._calculate_quality(campos)
            
            # Paso 9: Aprender para el futuro
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
        """Primera pasada de extracción"""
        extractor = self.field_extractor

        rut, rut_conf = extractor.extract_rut(text)
        folio, folio_conf = extractor.extract_folio(text)
        fecha, fecha_conf = extractor.extract_fecha(text)
        monto, monto_conf = extractor.extract_monto(text)
        nombre, nombre_conf = extractor.extract_nombre(text, file_path)
        
        # EXTRAER GLOSA PRIMERO (información clave)
        glosa = extractor.extract_glosa(text)
        
        convenio, convenio_conf = extractor.extract_convenio(text, glosa)
        periodo_servicio, periodo_conf = extractor.extract_periodo_servicio(text, fecha)
        
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
            'periodo_servicio': periodo_servicio,
            'periodo_servicio_confidence': periodo_conf,
            'monto_origen': 'ocr' if monto else '',
        }
    
    def _autofill_inteligente(self, campos: Dict) -> Dict:
        """Autocompletado INTELIGENTE con búsqueda inversa"""
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        
        # CASO 1: Tengo RUT pero falta nombre → buscar en memoria
        if rut and (not nombre or campos.get('nombre_confidence', 0) < 0.5):
            nombre_historico = self.memory.get_name_by_rut(rut)
            if nombre_historico:
                campos['nombre'] = nombre_historico
                campos['nombre_confidence'] = 0.85
                campos['nombre_origen'] = 'memoria'
        
        # CASO 2: Tengo nombre pero falta RUT → buscar RUT por nombre
        if nombre and not rut:
            rut_encontrado = self.memory.get_rut_by_name(nombre)
            if rut_encontrado:
                campos['rut'] = rut_encontrado
                campos['rut_confidence'] = 0.80
                campos['rut_origen'] = 'memoria'
        
        # CASO 3: Autocompletar convenio
        convenio_actual = campos.get('convenio', '').strip()
        if (not convenio_actual or campos.get('convenio_confidence', 0) < 0.4) and rut:
            convenio_historico = self.memory.get_convenio_by_rut(rut)
            if convenio_historico:
                campos['convenio'] = convenio_historico
                campos['convenio_confidence'] = 0.70
                campos['convenio_origen'] = 'memoria'
        
        return campos
    
    def _segunda_pasada_desde_glosa(self, campos: Dict, texto_completo: str) -> Dict:
        """SEGUNDA PASADA: Reintentar extraer desde glosa si faltan campos críticos"""
        glosa = campos.get('glosa', '')
        if not glosa:
            return campos
        
        extractor = self.field_extractor
        
        # Reintentar FECHA si falta o tiene baja confianza
        if not campos.get('fecha_documento') or campos.get('fecha_confidence', 0) < 0.6:
            fecha_glosa, fecha_conf_glosa = extractor.extract_from_glosa(glosa, 'fecha')
            if fecha_glosa and fecha_conf_glosa > campos.get('fecha_confidence', 0):
                campos['fecha_documento'] = fecha_glosa
                campos['fecha_confidence'] = fecha_conf_glosa
                campos['fecha_origen'] = 'glosa'
        
        # Reintentar CONVENIO si falta
        if not campos.get('convenio') or campos.get('convenio_confidence', 0) < 0.4:
            convenio_glosa, convenio_conf_glosa = extractor.extract_from_glosa(glosa, 'convenio')
            if convenio_glosa and convenio_conf_glosa > campos.get('convenio_confidence', 0):
                campos['convenio'] = convenio_glosa
                campos['convenio_confidence'] = convenio_conf_glosa
                campos['convenio_origen'] = 'glosa'
        
        # Reintentar DECRETO si falta
        if not campos.get('decreto_alcaldicio'):
            decreto_glosa, decreto_conf = extractor.extract_from_glosa(glosa, 'decreto')
            if decreto_glosa:
                campos['decreto_alcaldicio'] = decreto_glosa
        
        # Reintentar HORAS si falta
        if not campos.get('horas'):
            horas_glosa, horas_conf = extractor.extract_from_glosa(glosa, 'horas')
            if horas_glosa:
                campos['horas'] = horas_glosa
        
        return campos
    
    def _validate_monto_horas(self, campos: Dict) -> Dict:
        """Valida monto/horas y calcula si es necesario"""
        monto_str = campos.get('monto', '')
        horas_str = campos.get('horas', '')
        tipo = (campos.get('tipo') or '').lower()

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
    
    def _needs_review_ultra_relaxed(self, campos: Dict, confianza: float) -> bool:
        """
        Criterio ULTRA-RELAJADO para revisión manual.
        Solo pedir revisión si REALMENTE hay problemas graves.
        """
        tiene_rut = bool(campos.get('rut'))
        tiene_nombre = bool(campos.get('nombre'))
        tiene_monto = bool(campos.get('monto'))
        tiene_folio = bool(campos.get('nro_boleta'))
        
        # Si tiene los 3 campos SUPER-CRÍTICOS (RUT, nombre, monto) → NO REVISAR
        if tiene_rut and tiene_nombre and tiene_monto:
            # Solo revisar si confianza es EXTREMADAMENTE baja
            if confianza < 0.15:
                return True
            return False
        
        # Si tiene RUT + monto (aunque falte nombre) → NO REVISAR
        # porque el nombre se puede completar con memoria
        if tiene_rut and tiene_monto:
            return False
        
        # Si tiene nombre + monto (aunque falte RUT) → NO REVISAR
        # porque el RUT se puede buscar por nombre
        if tiene_nombre and tiene_monto:
            return False
        
        # Solo pedir revisión si:
        # 1. Falta monto Y (falta RUT O falta nombre)
        # 2. O si la confianza es DEMASIADO baja
        if not tiene_monto and (not tiene_rut or not tiene_nombre):
            return True
        
        if confianza < 0.25:
            return True
        
        return False
    
    def _calculate_quality(self, campos: Dict) -> float:
        """Calcula score de calidad"""
        score = 0.0
        
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
                score += peso * 0.6
                conf_campo = campos.get(f'{campo}_confidence', 0.7)
                score += peso * 0.4 * conf_campo
        
        return round(min(score, 1.0), 3)
