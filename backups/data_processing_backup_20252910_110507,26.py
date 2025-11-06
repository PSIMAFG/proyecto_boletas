# modules/data_processing.py (v3.5 FINAL - Búsqueda mejorada y campos obligatorios)
"""
Versión 3.5 FINAL - Correcciones críticas:
- Búsqueda cruzada MEJORADA que realmente encuentra datos existentes
- RUT, convenio y mes_nombre NUNCA pueden quedar vacíos
- Si faltan estos campos críticos → SIEMPRE a revisión
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


class BatchMemory:
    """Memoria temporal del batch actual para búsqueda cruzada MEJORADA"""
    
    def __init__(self):
        self.registros = []
        self.rut_to_data = {}
        self.nombre_to_data = {}
        # Índice adicional para búsqueda más flexible
        self.nombre_variations = {}  # Variaciones de nombres
    
    def add_registro(self, campos: Dict):
        """Agrega un registro procesado a la memoria del batch"""
        self.registros.append(campos)
        
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        convenio = campos.get('convenio', '').strip()
        
        if rut:
            if rut not in self.rut_to_data:
                self.rut_to_data[rut] = {
                    'nombres': [],
                    'convenios': [],
                    'registros': []
                }
            if nombre and nombre not in self.rut_to_data[rut]['nombres']:
                self.rut_to_data[rut]['nombres'].append(nombre)
            if convenio and convenio not in self.rut_to_data[rut]['convenios']:
                self.rut_to_data[rut]['convenios'].append(convenio)
            self.rut_to_data[rut]['registros'].append(campos)
        
        if nombre:
            # Guardar nombre normalizado
            nombre_norm = self._normalize_name(nombre)
            if nombre_norm not in self.nombre_to_data:
                self.nombre_to_data[nombre_norm] = {
                    'nombre_original': nombre,
                    'ruts': [],
                    'convenios': []
                }
            if rut and rut not in self.nombre_to_data[nombre_norm]['ruts']:
                self.nombre_to_data[nombre_norm]['ruts'].append(rut)
            if convenio and convenio not in self.nombre_to_data[nombre_norm]['convenios']:
                self.nombre_to_data[nombre_norm]['convenios'].append(convenio)
            
            # Guardar variaciones del nombre para búsqueda flexible
            self._add_name_variations(nombre, rut, convenio)
    
    def _add_name_variations(self, nombre: str, rut: str, convenio: str):
        """Agrega variaciones del nombre para búsqueda más flexible"""
        # Separar el nombre en partes
        partes = nombre.split()
        
        # Guardar por primer nombre
        if partes:
            primer_nombre = self._normalize_name(partes[0])
            if primer_nombre not in self.nombre_variations:
                self.nombre_variations[primer_nombre] = []
            self.nombre_variations[primer_nombre].append({
                'nombre_completo': nombre,
                'rut': rut,
                'convenio': convenio
            })
        
        # Guardar por apellido (si hay al menos 2 partes)
        if len(partes) >= 2:
            apellido = self._normalize_name(partes[-1])
            if apellido not in self.nombre_variations:
                self.nombre_variations[apellido] = []
            self.nombre_variations[apellido].append({
                'nombre_completo': nombre,
                'rut': rut,
                'convenio': convenio
            })
    
    def find_rut_by_nombre(self, nombre: str, strict: bool = False) -> str:
        """
        Busca RUT por nombre en registros del batch
        strict=False permite búsqueda más flexible
        """
        if not nombre:
            return ""
        
        nombre_norm = self._normalize_name(nombre)
        
        # Búsqueda exacta
        if nombre_norm in self.nombre_to_data:
            ruts = self.nombre_to_data[nombre_norm].get('ruts', [])
            if ruts:
                print(f"  [BATCH] Encontrado RUT exacto para '{nombre}': {ruts[0]}")
                return ruts[0]
        
        if not strict:
            # Búsqueda por similitud alta (85%)
            mejores = difflib.get_close_matches(nombre_norm, self.nombre_to_data.keys(), n=1, cutoff=0.85)
            if mejores:
                ruts = self.nombre_to_data[mejores[0]].get('ruts', [])
                if ruts:
                    nombre_encontrado = self.nombre_to_data[mejores[0]].get('nombre_original', '')
                    print(f"  [BATCH] Encontrado RUT similar para '{nombre}' → '{nombre_encontrado}': {ruts[0]}")
                    return ruts[0]
            
            # Búsqueda por partes del nombre
            partes = nombre.split()
            if partes:
                # Buscar por primer nombre o apellido
                for parte in partes:
                    parte_norm = self._normalize_name(parte)
                    if len(parte_norm) < 3:  # Ignorar partes muy cortas
                        continue
                    
                    if parte_norm in self.nombre_variations:
                        candidatos = self.nombre_variations[parte_norm]
                        # Verificar si algún candidato tiene similitud razonable
                        for candidato in candidatos:
                            if candidato['rut']:
                                # Verificar similitud del nombre completo
                                similitud = difflib.SequenceMatcher(None, 
                                                                   nombre_norm, 
                                                                   self._normalize_name(candidato['nombre_completo'])).ratio()
                                if similitud > 0.7:  # 70% de similitud
                                    print(f"  [BATCH] Encontrado RUT parcial para '{nombre}' → '{candidato['nombre_completo']}': {candidato['rut']}")
                                    return candidato['rut']
        
        return ""
    
    def find_nombre_by_rut(self, rut: str) -> str:
        """Busca nombre por RUT en registros del batch"""
        if not rut:
            return ""
        
        if rut in self.rut_to_data:
            nombres = self.rut_to_data[rut].get('nombres', [])
            if nombres:
                # Retornar el nombre más frecuente o el más reciente
                print(f"  [BATCH] Encontrado nombre para RUT {rut}: {nombres[0]}")
                return nombres[0]
        
        return ""
    
    def find_convenio_by_rut(self, rut: str) -> str:
        """Busca convenio por RUT en registros del batch"""
        if not rut:
            return ""
        
        if rut in self.rut_to_data:
            convenios = self.rut_to_data[rut].get('convenios', [])
            if convenios:
                # Retornar el más frecuente
                from collections import Counter
                convenio_mas_comun = Counter(convenios).most_common(1)[0][0]
                print(f"  [BATCH] Encontrado convenio para RUT {rut}: {convenio_mas_comun}")
                return convenio_mas_comun
        
        return ""
    
    def find_convenio_by_nombre(self, nombre: str) -> str:
        """Busca convenio por nombre en registros del batch"""
        if not nombre:
            return ""
        
        nombre_norm = self._normalize_name(nombre)
        
        # Búsqueda exacta
        if nombre_norm in self.nombre_to_data:
            convenios = self.nombre_to_data[nombre_norm].get('convenios', [])
            if convenios:
                from collections import Counter
                convenio_mas_comun = Counter(convenios).most_common(1)[0][0]
                print(f"  [BATCH] Encontrado convenio para nombre '{nombre}': {convenio_mas_comun}")
                return convenio_mas_comun
        
        # Búsqueda aproximada
        mejores = difflib.get_close_matches(nombre_norm, self.nombre_to_data.keys(), n=1, cutoff=0.8)
        if mejores:
            convenios = self.nombre_to_data[mejores[0]].get('convenios', [])
            if convenios:
                from collections import Counter
                convenio_mas_comun = Counter(convenios).most_common(1)[0][0]
                print(f"  [BATCH] Encontrado convenio aproximado para '{nombre}': {convenio_mas_comun}")
                return convenio_mas_comun
        
        return ""
    
    def _normalize_name(self, nombre: str) -> str:
        """Normaliza nombre para búsqueda"""
        nombre = nombre.lower()
        nombre = ''.join(
            c for c in unicodedata.normalize('NFD', nombre)
            if unicodedata.category(c) != 'Mn'
        )
        nombre = re.sub(r'[^a-z\s]', '', nombre)
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        return nombre


class FieldExtractor:
    """Extractor de campos con inteligencia mejorada"""
    
    def __init__(self):
        self.meses = MESES
        self.convenios_conocidos = KNOWN_CONVENIOS
    
    def extract_from_glosa(self, glosa: str, campo: str) -> Tuple[str, float]:
        """Extrae un campo específico desde la glosa si no se encontró en el texto principal"""
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
        elif campo == 'rut':
            return self.extract_rut(glosa)
        elif campo == 'nombre':
            match = re.search(r'Señor(?:es)?:\s*([^,\n]+)', glosa, re.IGNORECASE)
            if match:
                nombre_candidato = match.group(1).strip()
                if self._is_valid_name(nombre_candidato):
                    return nombre_candidato, 0.65
        
        return "", 0.0
    
    def extract_rut(self, text: str) -> Tuple[str, float]:
        """Extrae RUT con validación"""
        for match in RUT_ANCHOR_RE.finditer(text):
            rut = match.group(1)
            if dv_ok(rut):
                return rut.strip(), 0.95
        
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

        return "", 0.0
    
    def _norm_ocr_es(self, s: str) -> str:
        """Normaliza errores OCR típicos"""
        t = s
        t = t.replace('\u00AD', '')
        t = re.sub(r'[=]+', ' ', t, flags=re.I)
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
    """Procesador v3.5 FINAL con búsqueda mejorada y campos obligatorios"""
    
    def __init__(self, batch_memory: Optional[BatchMemory] = None):
        from modules.ocr_extraction import OCRExtractorOptimized
        from modules.memory import Memory
        self.ocr_extractor = OCRExtractorOptimized()
        self.field_extractor = FieldExtractor()
        self.memory = Memory()
        self.batch_memory = batch_memory or BatchMemory()
        self.month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
    
    def process_file(self, file_path: Path) -> Dict:
        """Procesa archivo con búsqueda cruzada mejorada y validación estricta"""
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
            
            # Paso 3: SEGUNDA PASADA - Reintentar desde glosa
            campos = self._segunda_pasada_desde_glosa(campos, texto_completo)
            
            # Paso 4: Búsqueda cruzada MEJORADA en batch actual
            campos = self._busqueda_cruzada_batch_mejorada(campos)
            
            # Paso 5: Autocompletar con memoria persistente
            campos = self._autofill_inteligente(campos)
            
            # Paso 6: Última búsqueda agresiva si faltan campos críticos
            campos = self._busqueda_final_agresiva(campos)
            
            # Paso 7: Validar monto/horas
            campos = self._validate_monto_horas(campos)
            
            # Paso 8: Calcular periodo y mes_nombre (OBLIGATORIO)
            campos = self._calculate_periodo_and_mes(campos)
            
            # Paso 9: Asegurar convenio por defecto si no hay
            if not campos.get('convenio'):
                # Si no se pudo determinar convenio, intentar última búsqueda
                if campos.get('rut'):
                    convenio_batch = self.batch_memory.find_convenio_by_rut(campos['rut'])
                    if convenio_batch:
                        campos['convenio'] = convenio_batch
                        campos['convenio_origen'] = 'batch_final'
                elif campos.get('nombre'):
                    convenio_batch = self.batch_memory.find_convenio_by_nombre(campos['nombre'])
                    if convenio_batch:
                        campos['convenio'] = convenio_batch
                        campos['convenio_origen'] = 'batch_final'
                
                # Si aún no hay convenio, poner uno por defecto PERO marcarlo para revisión
                if not campos.get('convenio'):
                    campos['convenio'] = 'SIN_CONVENIO'
                    campos['convenio_confidence'] = 0.0
            
            # Paso 10: Metadata
            campos['archivo'] = str(file_path)
            campos['paginas'] = len(texts)
            campos['confianza'] = round(confianza_promedio, 3)
            campos['confianza_max'] = round(max(confidences), 3) if confidences else 0.0
            campos['preview_path'] = preview
            
            # Paso 11: Decisión de revisión ESTRICTA para campos obligatorios
            campos['needs_review'] = self._needs_review_v35_strict(campos, confianza_promedio)
            campos['quality_score'] = self._calculate_quality(campos)
            
            # Log diagnóstico para casos específicos
            nombre_archivo = file_path.stem.lower()
            if 'needs_review' in campos and campos['needs_review']:
                print(f"[REVISION] {file_path.name}: {campos.get('revision_reason', 'Sin especificar')}")
            
            # Paso 12: Agregar al batch y aprender
            if not campos.get('error'):
                self.batch_memory.add_registro(campos)
                if campos.get('rut'):
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

        glosa = extractor.extract_glosa(text)
        
        rut, rut_conf = extractor.extract_rut(text)
        folio, folio_conf = extractor.extract_folio(text)
        fecha, fecha_conf = extractor.extract_fecha(text)
        monto, monto_conf = extractor.extract_monto(text)
        nombre, nombre_conf = extractor.extract_nombre(text, file_path)
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
    
    def _segunda_pasada_desde_glosa(self, campos: Dict, texto_completo: str) -> Dict:
        """Segunda pasada desde glosa"""
        glosa = campos.get('glosa', '')
        if not glosa:
            return campos
        
        extractor = self.field_extractor
        
        if not campos.get('fecha_documento') or campos.get('fecha_confidence', 0) < 0.6:
            fecha_glosa, fecha_conf_glosa = extractor.extract_from_glosa(glosa, 'fecha')
            if fecha_glosa and fecha_conf_glosa > campos.get('fecha_confidence', 0):
                campos['fecha_documento'] = fecha_glosa
                campos['fecha_confidence'] = fecha_conf_glosa
                campos['fecha_origen'] = 'glosa'
        
        if not campos.get('convenio') or campos.get('convenio_confidence', 0) < 0.4:
            convenio_glosa, convenio_conf_glosa = extractor.extract_from_glosa(glosa, 'convenio')
            if convenio_glosa and convenio_conf_glosa > campos.get('convenio_confidence', 0):
                campos['convenio'] = convenio_glosa
                campos['convenio_confidence'] = convenio_conf_glosa
                campos['convenio_origen'] = 'glosa'
        
        if not campos.get('rut'):
            rut_glosa, rut_conf_glosa = extractor.extract_from_glosa(glosa, 'rut')
            if rut_glosa:
                campos['rut'] = rut_glosa
                campos['rut_confidence'] = rut_conf_glosa
                campos['rut_origen'] = 'glosa'
        
        if not campos.get('nombre') or campos.get('nombre_confidence', 0) < 0.5:
            nombre_glosa, nombre_conf_glosa = extractor.extract_from_glosa(glosa, 'nombre')
            if nombre_glosa:
                campos['nombre'] = nombre_glosa
                campos['nombre_confidence'] = nombre_conf_glosa
                campos['nombre_origen'] = 'glosa'
        
        return campos
    
    def _busqueda_cruzada_batch_mejorada(self, campos: Dict) -> Dict:
        """Búsqueda cruzada MEJORADA en registros del batch actual"""
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        
        # Si tengo nombre pero no RUT, buscar en batch (más agresivo)
        if nombre and not rut:
            rut_encontrado = self.batch_memory.find_rut_by_nombre(nombre, strict=False)
            if rut_encontrado:
                campos['rut'] = rut_encontrado
                campos['rut_confidence'] = 0.85
                campos['rut_origen'] = 'batch_memory'
        
        # Si tengo RUT pero no nombre, buscar en batch
        if rut and not nombre:
            nombre_encontrado = self.batch_memory.find_nombre_by_rut(rut)
            if nombre_encontrado:
                campos['nombre'] = nombre_encontrado
                campos['nombre_confidence'] = 0.85
                campos['nombre_origen'] = 'batch_memory'
        
        # Si tengo RUT pero no convenio, buscar en batch
        if rut and not campos.get('convenio'):
            convenio_encontrado = self.batch_memory.find_convenio_by_rut(rut)
            if convenio_encontrado:
                campos['convenio'] = convenio_encontrado
                campos['convenio_confidence'] = 0.75
                campos['convenio_origen'] = 'batch_memory'
        
        # Si tengo nombre pero no convenio, buscar por nombre también
        if nombre and not campos.get('convenio'):
            convenio_encontrado = self.batch_memory.find_convenio_by_nombre(nombre)
            if convenio_encontrado:
                campos['convenio'] = convenio_encontrado
                campos['convenio_confidence'] = 0.70
                campos['convenio_origen'] = 'batch_memory_nombre'
        
        return campos
    
    def _busqueda_final_agresiva(self, campos: Dict) -> Dict:
        """Búsqueda final más agresiva si aún faltan campos críticos"""
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        
        # Si no hay RUT pero hay nombre, buscar más agresivamente
        if not rut and nombre:
            # Buscar por partes del nombre
            partes = nombre.split()
            for parte in partes:
                if len(parte) > 3:  # Ignorar partes muy cortas
                    rut_parcial = self.batch_memory.find_rut_by_nombre(parte, strict=False)
                    if rut_parcial:
                        campos['rut'] = rut_parcial
                        campos['rut_confidence'] = 0.70
                        campos['rut_origen'] = 'batch_parcial'
                        print(f"  [BATCH-AGRESIVO] RUT encontrado por '{parte}': {rut_parcial}")
                        break
        
        return campos
    
    def _autofill_inteligente(self, campos: Dict) -> Dict:
        """Autocompletado desde memoria persistente"""
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        
        # Solo usar memoria persistente si el batch no encontró nada
        if rut and (not nombre or campos.get('nombre_origen') != 'batch_memory'):
            nombre_historico = self.memory.get_name_by_rut(rut)
            if nombre_historico and not nombre:
                campos['nombre'] = nombre_historico
                campos['nombre_confidence'] = 0.80
                campos['nombre_origen'] = 'memoria_persistente'
        
        if nombre and (not rut or campos.get('rut_origen') not in ['batch_memory', 'batch_parcial']):
            rut_encontrado = self.memory.get_rut_by_name(nombre)
            if rut_encontrado and not rut:
                campos['rut'] = rut_encontrado
                campos['rut_confidence'] = 0.75
                campos['rut_origen'] = 'memoria_persistente'
        
        if rut and (not campos.get('convenio') or campos.get('convenio_origen') not in ['batch_memory', 'batch_memory_nombre']):
            convenio_historico = self.memory.get_convenio_by_rut(rut)
            if convenio_historico and not campos.get('convenio'):
                campos['convenio'] = convenio_historico
                campos['convenio_confidence'] = 0.70
                campos['convenio_origen'] = 'memoria_persistente'
        
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
    
    def _calculate_periodo_and_mes(self, campos: Dict) -> Dict:
        """Calcula periodo_dt y ASEGURA que mes_nombre NUNCA quede vacío"""
        periodo_iso = campos.get('periodo_servicio', '')
        fecha_doc = campos.get('fecha_documento', '')
        
        # Intentar obtener mes y año del periodo de servicio
        if periodo_iso and not periodo_iso.startswith('XXXX-'):
            try:
                yy = int(periodo_iso[:4])
                mm = int(periodo_iso[5:7])
                campos['mes'] = mm
                campos['anio'] = yy
                campos['mes_nombre'] = self.month_names.get(mm, f'Mes {mm}')
                
                # Calcular periodo_dt
                from datetime import datetime
                import calendar
                first = datetime(yy, mm, 1)
                last_day = calendar.monthrange(yy, mm)[1]
                last = datetime(yy, mm, last_day)
                campos['periodo_dt'] = first.strftime("%Y-%m-%d")
                campos['periodo_final'] = last.strftime("%Y-%m-%d")
                
                return campos
            except Exception:
                pass
        
        # Si no hay periodo pero sí fecha documento, usar esa
        if fecha_doc:
            try:
                from datetime import datetime
                fecha_dt = datetime.strptime(fecha_doc, "%Y-%m-%d")
                
                # Si el periodo tenía mes pero no año (XXXX-MM), usar el mes del periodo
                if periodo_iso and periodo_iso.startswith('XXXX-'):
                    try:
                        mm = int(periodo_iso[5:7])
                        # Decidir el año: si el mes es mayor al de la fecha, es del año anterior
                        if mm > fecha_dt.month:
                            yy = fecha_dt.year - 1
                        else:
                            yy = fecha_dt.year
                    except:
                        mm = fecha_dt.month
                        yy = fecha_dt.year
                else:
                    # Usar el mes anterior a la fecha del documento (asumiendo pago mes vencido)
                    if fecha_dt.month == 1:
                        mm = 12
                        yy = fecha_dt.year - 1
                    else:
                        mm = fecha_dt.month - 1
                        yy = fecha_dt.year
                
                campos['mes'] = mm
                campos['anio'] = yy
                campos['mes_nombre'] = self.month_names.get(mm, f'Mes {mm}')
                
                # Calcular periodo_dt
                import calendar
                first = datetime(yy, mm, 1)
                last_day = calendar.monthrange(yy, mm)[1]
                last = datetime(yy, mm, last_day)
                campos['periodo_dt'] = first.strftime("%Y-%m-%d")
                campos['periodo_final'] = last.strftime("%Y-%m-%d")
                
                return campos
            except Exception:
                pass
        
        # Si no hay nada, poner valores por defecto pero NUNCA vacíos
        campos['mes'] = 0
        campos['anio'] = 0
        campos['mes_nombre'] = 'SIN_PERIODO'  # NUNCA vacío
        campos['periodo_dt'] = ""
        campos['periodo_final'] = ""
        
        return campos
    
    def _needs_review_v35_strict(self, campos: Dict, confianza: float) -> bool:
        """
        Criterio v3.5 ESTRICTO para campos obligatorios
        RUT, convenio y mes_nombre NO pueden faltar
        """
        tiene_rut = bool(campos.get('rut'))
        tiene_nombre = bool(campos.get('nombre'))
        tiene_monto = bool(campos.get('monto'))
        tiene_fecha = bool(campos.get('fecha_documento'))
        tiene_convenio = bool(campos.get('convenio') and campos.get('convenio') != 'SIN_CONVENIO')
        tiene_mes_nombre = bool(campos.get('mes_nombre') and campos.get('mes_nombre') != 'SIN_PERIODO')
        
        # CRITERIO 1: Si falta RUT → SIEMPRE REVISAR
        if not tiene_rut:
            campos['revision_reason'] = 'Falta RUT (campo obligatorio)'
            return True
        
        # CRITERIO 2: Si falta convenio o es SIN_CONVENIO → SIEMPRE REVISAR
        if not tiene_convenio:
            campos['revision_reason'] = 'Falta convenio (critico para resumen financiero)'
            return True
        
        # CRITERIO 3: Si falta mes_nombre o es SIN_PERIODO → SIEMPRE REVISAR
        if not tiene_mes_nombre:
            campos['revision_reason'] = 'Falta periodo/mes (critico para resumen mensual)'
            return True
        
        # CRITERIO 4: Si faltan otros campos críticos
        campos_faltantes = 0
        faltantes_nombres = []
        
        if not tiene_nombre:
            campos_faltantes += 1
            faltantes_nombres.append('Nombre')
        if not tiene_monto:
            campos_faltantes += 1
            faltantes_nombres.append('Monto')
        if not tiene_fecha:
            campos_faltantes += 1
            faltantes_nombres.append('Fecha')
        
        # Si faltan 2 o más de estos otros campos → REVISAR
        if campos_faltantes >= 2:
            campos['revision_reason'] = f'Faltan campos: {", ".join(faltantes_nombres)}'
            return True
        
        # CRITERIO 5: Si falta solo monto → REVISAR
        if not tiene_monto:
            campos['revision_reason'] = 'Falta monto'
            return True
        
        # CRITERIO 6: Si confianza es MUY baja → REVISAR
        if confianza < 0.30:
            campos['revision_reason'] = f'Confianza muy baja: {confianza:.1%}'
            return True
        
        # CRITERIO 7: Validaciones adicionales
        if tiene_rut:
            from modules.utils import dv_ok
            if not dv_ok(campos['rut']):
                campos['revision_reason'] = 'RUT con digito verificador invalido'
                return True
        
        if tiene_monto:
            try:
                monto = float(campos['monto'])
                if monto < 100000 or monto > 3000000:
                    campos['revision_reason'] = f'Monto fuera de rango: ${monto:,.0f}'
                    return True
            except:
                pass
        
        if tiene_fecha:
            try:
                from datetime import datetime
                fecha_dt = datetime.strptime(campos['fecha_documento'], "%Y-%m-%d")
                if fecha_dt.year < 2015 or fecha_dt.year > 2035:
                    campos['revision_reason'] = f'Fecha sospechosa: {fecha_dt.year}'
                    return True
            except:
                pass
        
        return False
    
    def _calculate_quality(self, campos: Dict) -> float:
        """Calcula score de calidad"""
        score = 0.0
        
        pesos = {
            'rut': 0.20,  # Más importante ahora que es obligatorio
            'nombre': 0.15,
            'monto': 0.20,
            'fecha_documento': 0.10,
            'convenio': 0.15,  # Más importante ahora que es obligatorio
            'mes_nombre': 0.10,  # Importante para resumen
            'nro_boleta': 0.05,
            'glosa': 0.05
        }
        
        for campo, peso in pesos.items():
            valor = campos.get(campo, '')
            # Verificar que el campo tenga valor real (no placeholder)
            if valor and valor not in ['SIN_CONVENIO', 'SIN_PERIODO']:
                score += peso * 0.6
                conf_campo = campos.get(f'{campo}_confidence', 0.7)
                score += peso * 0.4 * conf_campo
        
        return round(min(score, 1.0), 3)
