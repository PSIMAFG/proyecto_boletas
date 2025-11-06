# modules/data_processing.py (v4.0 FINAL - Post-procesamiento Inteligente)
"""
Versión 4.0 FINAL - Sistema con post-procesamiento inteligente:
- Extracción OCR de TODAS las boletas primero
- Post-procesamiento masivo con búsqueda cruzada
- Inferencia decreto-convenio automática
- Validación estricta de campos obligatorios
- Re-evaluación después de cada cambio
"""
import re
import difflib
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
from datetime import datetime
import sys
import unicodedata
from collections import defaultdict, Counter
from datetime import datetime



sys.path.append(str(Path(__file__).parent.parent))
from config import *
from modules.utils import *


def mark_review_flags(r: dict) -> dict:
    reasons = []

    # Si no hay fecha_documento o no se pudo derivar mes/año → revisión
    if not (r.get('fecha_documento') and r.get('mes') and r.get('anio')):
        reasons.append("Sin_mes_desde_Fecha (posible ticket/tapa OCR)")

    # Si la confianza general del documento es baja, también lo marcamos de apoyo
    conf = float(r.get('confianza') or 0)
    if conf < 0.55:
            reasons.append(f"Baja_confianza_OCR({conf:.2f})")

    r['needs_review'] = bool(reasons)
    r['review_reason'] = "; ".join(reasons)
    return r

def process_file_worker(file_path_str: str) -> dict:
    """
    Wrapper de nivel módulo para que ProcessPoolExecutor (spawn en Windows)
    pueda ejecutar sin problemas de pickling de métodos ligados.
    """
    from pathlib import Path
    dp = DataProcessorOptimized()   # instancia local al worker
    return dp.process_file(Path(file_path_str))

class BatchMemory:
    """Memoria temporal del batch actual para búsqueda cruzada MEJORADA"""
    
    def __init__(self):
        self.registros = []
        self.rut_to_data = {}
        self.nombre_to_data = {}
        self.nombre_variations = {}
        # NUEVO v4.0: Mapeo decreto <-> convenio
        self.decreto_to_convenio = {}
        self.rut_to_decretos = defaultdict(list)
    
    def add_registro(self, campos: Dict):
        """Agrega un registro procesado a la memoria del batch"""
        self.registros.append(campos)
        
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        convenio = campos.get('convenio', '').strip()
        decreto = campos.get('decreto_alcaldicio', '').strip()
        
        if rut:
            if rut not in self.rut_to_data:
                self.rut_to_data[rut] = {
                    'nombres': [],
                    'convenios': [],
                    'decretos': [],
                    'registros': []
                }
            if nombre and nombre not in self.rut_to_data[rut]['nombres']:
                self.rut_to_data[rut]['nombres'].append(nombre)
            if convenio and convenio not in self.rut_to_data[rut]['convenios']:
                self.rut_to_data[rut]['convenios'].append(convenio)
            if decreto and decreto not in self.rut_to_data[rut]['decretos']:
                self.rut_to_data[rut]['decretos'].append(decreto)
            self.rut_to_data[rut]['registros'].append(campos)
            
            # NUEVO v4.0: Registrar decreto-RUT
            if decreto:
                self.rut_to_decretos[rut].append(decreto)
        
        if nombre:
            nombre_norm = self._normalize_name(nombre)
            if nombre_norm not in self.nombre_to_data:
                self.nombre_to_data[nombre_norm] = {
                    'nombre_original': nombre,
                    'ruts': [],
                    'convenios': [],
                    'decretos': []
                }
            if rut and rut not in self.nombre_to_data[nombre_norm]['ruts']:
                self.nombre_to_data[nombre_norm]['ruts'].append(rut)
            if convenio and convenio not in self.nombre_to_data[nombre_norm]['convenios']:
                self.nombre_to_data[nombre_norm]['convenios'].append(convenio)
            if decreto and decreto not in self.nombre_to_data[nombre_norm]['decretos']:
                self.nombre_to_data[nombre_norm]['decretos'].append(decreto)
            
            self._add_name_variations(nombre, rut, convenio)
        
        # NUEVO v4.0: Aprender asociación decreto <-> convenio
        if decreto and convenio and convenio not in ['SIN_CONVENIO', '']:
            if decreto not in self.decreto_to_convenio:
                self.decreto_to_convenio[decreto] = []
            self.decreto_to_convenio[decreto].append(convenio)
    
    def find_rut_by_nombre(self, nombre: str, strict: bool = False) -> str:
        """Busca RUT por nombre en registros del batch"""
        if not nombre:
            return ""
        
        nombre_norm = self._normalize_name(nombre)
        
        # Búsqueda exacta
        if nombre_norm in self.nombre_to_data:
            ruts = self.nombre_to_data[nombre_norm].get('ruts', [])
            if ruts:
                return ruts[0]
        
        if not strict:
            # Búsqueda por similitud alta (85%)
            mejores = difflib.get_close_matches(nombre_norm, self.nombre_to_data.keys(), n=1, cutoff=0.85)
            if mejores:
                ruts = self.nombre_to_data[mejores[0]].get('ruts', [])
                if ruts:
                    return ruts[0]
            
            # Búsqueda por partes del nombre
            partes = nombre.split()
            if partes:
                for parte in partes:
                    parte_norm = self._normalize_name(parte)
                    if len(parte_norm) < 3:
                        continue
                    
                    if parte_norm in self.nombre_variations:
                        candidatos = self.nombre_variations[parte_norm]
                        for candidato in candidatos:
                            if candidato['rut']:
                                similitud = difflib.SequenceMatcher(None, 
                                                                   nombre_norm, 
                                                                   self._normalize_name(candidato['nombre_completo'])).ratio()
                                if similitud > 0.7:
                                    return candidato['rut']
        
        return ""
    
    def find_nombre_by_rut(self, rut: str) -> str:
        """Busca nombre por RUT en registros del batch"""
        if not rut:
            return ""
        
        if rut in self.rut_to_data:
            nombres = self.rut_to_data[rut].get('nombres', [])
            if nombres:
                return nombres[0]
        
        return ""
    
    def find_convenio_by_rut(self, rut: str) -> str:
        """Busca convenio por RUT en registros del batch"""
        if not rut:
            return ""
        
        if rut in self.rut_to_data:
            convenios = self.rut_to_data[rut].get('convenios', [])
            if convenios:
                # Filtrar 'SIN_CONVENIO'
                convenios_validos = [c for c in convenios if c and c != 'SIN_CONVENIO']
                if convenios_validos:
                    convenio_mas_comun = Counter(convenios_validos).most_common(1)[0][0]
                    return convenio_mas_comun
        
        return ""
    
    def find_convenio_by_nombre(self, nombre: str) -> str:
        """Busca convenio por nombre en registros del batch"""
        if not nombre:
            return ""
        
        nombre_norm = self._normalize_name(nombre)
        
        if nombre_norm in self.nombre_to_data:
            convenios = self.nombre_to_data[nombre_norm].get('convenios', [])
            if convenios:
                convenios_validos = [c for c in convenios if c and c != 'SIN_CONVENIO']
                if convenios_validos:
                    return Counter(convenios_validos).most_common(1)[0][0]
        
        mejores = difflib.get_close_matches(nombre_norm, self.nombre_to_data.keys(), n=1, cutoff=0.8)
        if mejores:
            convenios = self.nombre_to_data[mejores[0]].get('convenios', [])
            if convenios:
                convenios_validos = [c for c in convenios if c and c != 'SIN_CONVENIO']
                if convenios_validos:
                    return Counter(convenios_validos).most_common(1)[0][0]
        
        return ""
    
    def find_convenio_by_decreto(self, decreto: str) -> str:
        """NUEVO v4.0: Busca convenio más común asociado a un decreto"""
        if not decreto or decreto not in self.decreto_to_convenio:
            return ""
        
        convenios = self.decreto_to_convenio[decreto]
        convenios_validos = [c for c in convenios if c and c != 'SIN_CONVENIO']
        if convenios_validos:
            return Counter(convenios_validos).most_common(1)[0][0]
        
        return ""
    
    def _add_name_variations(self, nombre: str, rut: str, convenio: str):
        """Agrega variaciones del nombre para búsqueda más flexible"""
        partes = nombre.split()
        
        if partes:
            primer_nombre = self._normalize_name(partes[0])
            if primer_nombre not in self.nombre_variations:
                self.nombre_variations[primer_nombre] = []
            self.nombre_variations[primer_nombre].append({
                'nombre_completo': nombre,
                'rut': rut,
                'convenio': convenio
            })
        
        if len(partes) >= 2:
            apellido = self._normalize_name(partes[-1])
            if apellido not in self.nombre_variations:
                self.nombre_variations[apellido] = []
            self.nombre_variations[apellido].append({
                'nombre_completo': nombre,
                'rut': rut,
                'convenio': convenio
            })
    
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
        """
        Respaldo: intenta detectar mes/año SOLO alrededor de la línea 'Fecha'.
        Si no encuentra, cae al comportamiento previo.
        """
        # 1) recorta a 20-30 primeras líneas y busca la línea que contiene 'Fecha'
        t = re.sub(r'[|]+', ' ', text)
        lines = [l.strip() for l in t.split('\n') if l.strip()]
        header_zone = '\n'.join(lines[:30])

        # intenta hallar la línea 'Fecha' para acotar el scope
        mline = None
        for ln in lines[:30]:
            if re.search(r'(?i)\bfecha\b', ln):
                mline = ln
                break
        scope = mline if mline else header_zone

        # ---- desde aquí, el mismo parsing que ya usas, pero aplicado a 'scope' ----
        base = self._norm_ocr_es(scope)
        meses_map = {k.lower(): v for k, v in self.meses.items()}
        meses_regex = {
            'enero': r'e\s*n\s*e\s*r\s*o', 'febrero': r'f\s*e\s*b\s*r\s*e\s*r\s*o',
            'marzo': r'm\s*a\s*r\s*z\s*[o0]', 'abril': r'a\s*b\s*r\s*i\s*l',
            'mayo': r'm\s*a\s*y\s*o', 'junio': r'j\s*u\s*n\s*i\s*o',
            'julio': r'j\s*u\s*l\s*i\s*o', 'agosto': r'a\s*g\s*o\s*s\s*t\s*o',
            'septiembre': r's\s*e\s*p\s*t\s*i\s*e\s*m\s*b\s*r\s*e',
            'octubre': r'o\s*c\s*t\s*u\s*b\s*r\s*e','noviembre': r'n\s*o\s*v\s*i\s*e\s*m\s*b\s*r\s*e',
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
                y = int(year_token); y = y + 2000 if y < 100 else y
                if 2000 <= y <= 2035:
                    return f"{y:04d}-{mes_num:02d}", 0.90
            except Exception:
                pass

        if fecha_doc_iso:
            try:
                y_doc = int(fecha_doc_iso[:4]); m_doc = int(fecha_doc_iso[5:7])
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
    
    def extract_montos_prefer_bruto(self, text: str):
        """
        Devuelve (monto_bruto, monto_liquido, conf, origen)
        - Intenta extraer explícitos: 'Total Honorarios' (bruto) y 'Líquido Pagado' (líquido)
        - Si ambos existen, usa el MAYOR como bruto. Si están a ≤3% de diferencia, se prefiere el mayor igual.
        - Si solo hay uno, lo devuelve en su casilla y marca el origen.
        """
        t = re.sub(r'[|]+', ' ', text or '')
        bruto_pat  = re.compile(r'(?i)total\s+honorarios?\s*\$?\s*[:\-]?\s*([\d\.\s,]+)')
        liq_pat    = re.compile(r'(?i)l[ií]quido(?:\s+pagado)?\s*\$?\s*[:\-]?\s*([\d\.\s,]+)')
        any_money  = re.compile(r'\$\s*([\d\.\,\s]+)|\b(\d{1,3}(?:[.,]\d{3}){1,3})\b')

        def norm_money(s):
            s = re.sub(r'[^\d,.\s]', '', s).replace(' ', '')
            # normaliza miles
            if s.count('.') + s.count(',') > 1:
                s = s.replace('.', '').replace(',', '')
            else:
                s = s.replace('.', '').replace(',', '')
            try:
                return float(s)
            except: 
                return None

        bruto = None; liq = None; origen_b = None; origen_l = None
        m = bruto_pat.search(t)
        if m:
            v = norm_money(m.group(1))
            if v: bruto, origen_b = v, 'explicito_total_honorarios'
        m = liq_pat.search(t)
        if m:
            v = norm_money(m.group(1))
            if v: liq, origen_l = v, 'explicito_liquido'

        # Si ninguno, intenta un legacy de “mejor candidato”
        conf = 0.0
        if bruto is None and liq is None:
            # prueba con tu extractor legacy
            monto_legacy, conf_legacy = self.extract_monto(text)
            if monto_legacy:
                bruto = float(monto_legacy); origen_b = 'ocr_legacy'
                conf = max(conf, conf_legacy or 0.75)

        # Si solo salió uno, devuélvelo en su casilla
        if bruto is not None and liq is None:
            return int(bruto), None, max(conf, 0.90), origen_b
        if liq is not None and bruto is None:
            return None, int(liq), max(conf, 0.85), origen_l

        # Si ambos existen: el mayor es el bruto
        if bruto is not None and liq is not None:
            # si OCR invirtió, corrige
            if liq > bruto:
                bruto, liq = liq, bruto
                origen_b, origen_l = (origen_l or 'mayor_ajustado'), (origen_b or 'menor_ajustado')
            # si están muy cerca, igual tomar el mayor como bruto
            diff = abs(bruto - (liq or 0)) / max(bruto, 1)
            base_conf = 0.92 if diff > 0.03 else 0.95
            return int(bruto), int(liq), base_conf, (origen_b or 'mayor')

        # Nada confiable
        return None, None, 0.0, ''

    
    
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



class IntelligentBatchProcessor:
    """
    NUEVO v4.0: Procesador inteligente de post-procesamiento
    Se ejecuta DESPUÉS de extraer todas las boletas
    """
    
    def __init__(self, batch_memory: BatchMemory, persistent_memory):
        self.batch_memory = batch_memory
        self.memory = persistent_memory
        self.month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
    
    
    def _normalize_decreto_convenio(self, registros: List[Dict], log_callback=None) -> List[Dict]:
        """
        NUEVO v4.0: Normaliza convenios basándose en decretos
        Si un decreto está asociado con un convenio, aplicar a todos
        """
        if log_callback:
            log_callback("📋 Normalizando decreto-convenio...", "info")
        
        # Construir mapeo decreto -> convenio más común
        decreto_convenio_map = {}
        for decreto, convenios in self.batch_memory.decreto_to_convenio.items():
            convenios_validos = [c for c in convenios if c and c != 'SIN_CONVENIO']
            if convenios_validos:
                convenio_mas_comun = Counter(convenios_validos).most_common(1)[0][0]
                decreto_convenio_map[decreto] = convenio_mas_comun
        
        # Aplicar normalización
        aplicados = 0
        for registro in registros:
            decreto = registro.get('decreto_alcaldicio', '').strip()
            convenio_actual = registro.get('convenio', '').strip()
            
            if decreto and decreto in decreto_convenio_map:
                if not convenio_actual or convenio_actual == 'SIN_CONVENIO':
                    registro['convenio'] = decreto_convenio_map[decreto]
                    registro['convenio_confidence'] = 0.85
                    registro['convenio_origen'] = 'decreto_inferido'
                    aplicados += 1
        
        if log_callback and aplicados > 0:
            log_callback(f"   ✓ {aplicados} convenios inferidos desde decretos", "success")
        
        return registros
    
    def _massive_cross_search(self, registros: List[Dict], log_callback=None) -> List[Dict]:
        """
        NUEVO v4.0: Búsqueda cruzada masiva más agresiva
        """
        if log_callback:
            log_callback("🔍 Búsqueda cruzada masiva...", "info")
        
        mejoras = {'rut': 0, 'nombre': 0, 'convenio': 0}
        
        for registro in registros:
            rut = registro.get('rut', '').strip()
            nombre = registro.get('nombre', '').strip()
            convenio = registro.get('convenio', '').strip()
            
            # Buscar RUT por nombre (más agresivo)
            if nombre and not rut:
                # Batch actual
                rut_batch = self.batch_memory.find_rut_by_nombre(nombre, strict=False)
                if rut_batch:
                    registro['rut'] = rut_batch
                    registro['rut_confidence'] = 0.85
                    registro['rut_origen'] = 'batch_post'
                    mejoras['rut'] += 1
                else:
                    # Memoria persistente
                    rut_memoria = self.memory.get_rut_by_name(nombre)
                    if rut_memoria:
                        registro['rut'] = rut_memoria
                        registro['rut_confidence'] = 0.75
                        registro['rut_origen'] = 'memoria_post'
                        mejoras['rut'] += 1
            
            # Actualizar RUT si cambió
            rut = registro.get('rut', '').strip()
            
            # Buscar nombre por RUT
            if rut and (not nombre or registro.get('nombre_confidence', 0) < 0.7):
                nombre_batch = self.batch_memory.find_nombre_by_rut(rut)
                if nombre_batch:
                    if not nombre:
                        registro['nombre'] = nombre_batch
                        registro['nombre_confidence'] = 0.85
                        registro['nombre_origen'] = 'batch_post'
                        mejoras['nombre'] += 1
                else:
                    nombre_memoria = self.memory.get_name_by_rut(rut)
                    if nombre_memoria and not nombre:
                        registro['nombre'] = nombre_memoria
                        registro['nombre_confidence'] = 0.75
                        registro['nombre_origen'] = 'memoria_post'
                        mejoras['nombre'] += 1
            
            # Buscar convenio por múltiples vías
            if not convenio or convenio == 'SIN_CONVENIO':
                convenio_encontrado = None
                
                # Por RUT
                if rut:
                    convenio_encontrado = self.batch_memory.find_convenio_by_rut(rut)
                    if not convenio_encontrado:
                        convenio_encontrado = self.memory.get_convenio_by_rut(rut)
                
                # Por nombre
                if not convenio_encontrado and nombre:
                    convenio_encontrado = self.batch_memory.find_convenio_by_nombre(nombre)
                
                # Por decreto
                if not convenio_encontrado:
                    decreto = registro.get('decreto_alcaldicio', '').strip()
                    if decreto:
                        convenio_encontrado = self.batch_memory.find_convenio_by_decreto(decreto)
                
                if convenio_encontrado:
                    registro['convenio'] = convenio_encontrado
                    registro['convenio_confidence'] = 0.70
                    registro['convenio_origen'] = 'inferencia_post'
                    mejoras['convenio'] += 1
        
        if log_callback:
            if any(mejoras.values()):
                log_callback(f"   ✓ Mejoras aplicadas:", "success")
                if mejoras['rut'] > 0:
                    log_callback(f"     • {mejoras['rut']} RUTs completados", "success")
                if mejoras['nombre'] > 0:
                    log_callback(f"     • {mejoras['nombre']} nombres completados", "success")
                if mejoras['convenio'] > 0:
                    log_callback(f"     • {mejoras['convenio']} convenios completados", "success")
        
        return registros
    
    def _infer_missing_periods(self, registros: List[Dict], log_callback=None) -> List[Dict]:
        """
        Inferir periodos SOLO si NO existe fecha_documento.
        Si existe fecha_documento, ese mes/año mandan.
        """
        inferidos = 0

        for r in registros:
            fecha_doc = (r.get('fecha_documento') or '').strip()

            # Si ya hay fecha de encabezado, no tocar (ya se calculó en _calculate_periodo_basic)
            if fecha_doc:
                continue

            # Sin fecha: intentamos cerrar con periodo_servicio parcial (XXXX-MM) -> completar año
            mes_actual = r.get('mes'); anio_actual = r.get('anio')
            if mes_actual and not anio_actual:
                # Sin fecha_doc no podemos anclar el año de forma perfecta; mantén None o define una política local
                # Aquí NO inventamos el año para evitar errores.
                continue

            # Último recurso: si no hay mes_nombre, no inventar “mes vencido” sin fecha_doc
            if r.get('mes_nombre') in ['', 'SIN_PERIODO', None]:
                # Sin fecha del documento no inferimos nada para evitar falsos positivos
                continue

        if log_callback and inferidos > 0:
            log_callback(f"   ✓ {inferidos} periodos inferidos/cerrados", "success")
        return registros
    

    def post_process_batch(self, registros: List[Dict], log_callback=None) -> Tuple[List[Dict], List[Dict]]:
        """
        Post-procesamiento inteligente de todo el batch
        Retorna: (registros_completos, registros_para_revision)
        """
        if log_callback:
            log_callback("🧠 Iniciando post-procesamiento inteligente...", "info")
        
        # Paso 1: Normalizar decreto-convenio
        registros = self._normalize_decreto_convenio(registros, log_callback)
        
        # Paso 2: Búsqueda cruzada masiva
        registros = self._massive_cross_search(registros, log_callback)
        
        # Paso 3: Inferir periodos faltantes
        registros = self._infer_missing_periods(registros, log_callback)
        for i, r in enumerate(registros):
            registros[i] = mark_review_flags(r)
        # Paso 4: Re-evaluar necesidad de revisión
        completos = []
        para_revision = []

        for registro in registros:
            needs = bool(registro.get('needs_review')) or self._needs_review_post_process(registro)
            if needs:
                registro['needs_review'] = True
                # preserva la razón de mark_review_flags si existe
                if 'review_reason' not in registro or not registro['review_reason']:
                    registro['review_reason'] = 'Post-process rules'
                para_revision.append(registro)
            else:
                registro['needs_review'] = False
                completos.append(registro)
        
        if log_callback:
            log_callback(f"✅ Post-procesamiento completado:", "success")
            log_callback(f"   • Completos: {len(completos)}", "success")
            log_callback(f"   • Para revisión: {len(para_revision)}", "warning")
        
        return completos, para_revision

    def _needs_review_post_process(self, registro: Dict) -> bool:
        """
        NUEVO v4.0: Re-evaluación de necesidad de revisión después de post-procesamiento
        Criterios más relajados que en v3.5
        """
        tiene_rut = bool(registro.get('rut'))
        tiene_nombre = bool(registro.get('nombre'))
        tiene_monto = bool(registro.get('monto'))
        tiene_fecha = bool(registro.get('fecha_documento'))
        tiene_convenio = bool(registro.get('convenio') and registro.get('convenio') != 'SIN_CONVENIO')
        tiene_mes = bool(registro.get('mes_nombre') and registro.get('mes_nombre') != 'SIN_PERIODO')
        
        # Criterio 1: RUT OBLIGATORIO
        if not tiene_rut:
            registro['revision_reason'] = 'Falta RUT (no se pudo inferir)'
            return True
        
        # Criterio 2: Al menos 2 de 3 críticos (nombre, monto, convenio)
        criticos = sum([tiene_nombre, tiene_monto, tiene_convenio])
        if criticos < 2:
            faltantes = []
            if not tiene_nombre:
                faltantes.append('Nombre')
            if not tiene_monto:
                faltantes.append('Monto')
            if not tiene_convenio:
                faltantes.append('Convenio')
            registro['revision_reason'] = f'Faltan campos: {", ".join(faltantes)}'
            return True
        
        # Criterio 3: Validación de RUT
        if tiene_rut and not dv_ok(registro['rut']):
            registro['revision_reason'] = 'RUT con dígito verificador inválido'
            return True
        
        # Criterio 4: Monto en rango razonable
        if tiene_monto:
            try:
                monto = float(registro['monto'])
                if monto < 50000 or monto > 5000000:
                    registro['revision_reason'] = f'Monto sospechoso: ${monto:,.0f}'
                    return True
            except:
                pass
        
        # Si pasó todos los criterios, NO necesita revisión
        return False


class DataProcessorOptimized:
    """Procesador v4.0 FINAL con post-procesamiento inteligente"""
    
    def __init__(self, batch_memory: Optional[BatchMemory] = None):
        from modules.ocr_extraction import OCRExtractorOptimized
        from modules.memory import Memory
        self.ocr_extractor = OCRExtractorOptimized()
        self.field_extractor = FieldExtractor()
        self.memory = Memory()
        self.batch_memory = batch_memory or BatchMemory()
        self.batch_processor = IntelligentBatchProcessor(self.batch_memory, self.memory)
        self.month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
    
    def process_file(self, file_path: Path) -> Dict:
        """Procesa archivo (FASE 1: solo extracción OCR)"""
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
            
            # Paso 4: Búsqueda cruzada en batch actual (ligera)
            campos = self._busqueda_cruzada_batch_basica(campos)
            
            # Paso 5: Validar monto/horas
            campos = self._validate_monto_horas(campos)
            
            # Paso 6: Calcular periodo básico
            campos = self._calculate_periodo_basic(campos)
            
            # Paso 7: Metadata
            campos['archivo'] = str(file_path)
            campos['paginas'] = len(texts)
            campos['confianza'] = round(confianza_promedio, 3)
            campos['confianza_max'] = round(max(confidences), 3) if confidences else 0.0
            campos['preview_path'] = preview
            
            # NO decidir needs_review aquí - se hace en post-procesamiento
            campos['needs_review'] = None  # Pendiente de post-procesamiento
            
            # Paso 8: Agregar al batch
            self.batch_memory.add_registro(campos)
            
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
        """Primera pasada de extracción (robusta con inicialización de montos)."""
        extractor = self.field_extractor

        glosa = extractor.extract_glosa(text)

        rut, rut_conf = extractor.extract_rut(text)
        folio, folio_conf = extractor.extract_folio(text)
        fecha, fecha_conf = extractor.extract_fecha(text)

        # --- Inicialización defensiva para evitar UnboundLocalError ---
        monto_bruto: Optional[int] = None
        monto_liquido: Optional[int] = None
        monto_conf: float = 0.0
        monto_origen: str = ""

        # Intento principal (preferir bruto)
        try:
            mb, ml, mc, mo = extractor.extract_montos_prefer_bruto(text)
            if mb is not None:
                monto_bruto = int(mb)
            if ml is not None:
                monto_liquido = int(ml)
            if mc is not None:
                monto_conf = float(mc)
            if mo:
                monto_origen = mo
        except AttributeError:
            # Si aún no existe el método en FieldExtractor, seguimos con legacy
            pass
        except Exception:
            # Cualquier otro problema en el extractor “nuevo”: continuamos con fallback
            pass

        # Fallback legacy si no salió nada
        if monto_bruto is None and monto_liquido is None:
            m_legacy, c_legacy = extractor.extract_monto(text)
            if m_legacy:
                monto_bruto = int(m_legacy)
                monto_conf = max(monto_conf, (c_legacy or 0.75))
                if not monto_origen:
                    monto_origen = 'ocr_legacy'

        # Visible = bruto si existe; si no, líquido; si no, vacío
        monto_visible = monto_bruto if monto_bruto is not None else (
            monto_liquido if monto_liquido is not None else None
        )

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

            'monto': str(int(monto_visible)) if monto_visible is not None else '',
            'monto_confidence': monto_conf,
            'monto_origen': monto_origen or '',
            'monto_bruto': int(monto_bruto) if monto_bruto is not None else None,
            'monto_liquido': int(monto_liquido) if monto_liquido is not None else None,

            'convenio': convenio,
            'convenio_confidence': convenio_conf,
            'horas': horas,
            'decreto_alcaldicio': decreto,
            'tipo': tipo,
            'glosa': glosa,

            'periodo_servicio': periodo_servicio,
            'periodo_servicio_confidence': periodo_conf,
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
    
    def _busqueda_cruzada_batch_basica(self, campos: Dict) -> Dict:
        """Búsqueda cruzada básica (no tan agresiva como en post-proceso)"""
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        
        if nombre and not rut:
            rut_encontrado = self.batch_memory.find_rut_by_nombre(nombre, strict=True)
            if rut_encontrado:
                campos['rut'] = rut_encontrado
                campos['rut_confidence'] = 0.85
                campos['rut_origen'] = 'batch_inicial'
        
        if rut and not nombre:
            nombre_encontrado = self.batch_memory.find_nombre_by_rut(rut)
            if nombre_encontrado:
                campos['nombre'] = nombre_encontrado
                campos['nombre_confidence'] = 0.85
                campos['nombre_origen'] = 'batch_inicial'
        
        return campos
    
    def _validate_monto_horas(self, campos: Dict) -> Dict:
        """Valida monto/horas y calcula si es necesario"""
        monto_str = campos.get('monto', '')
        horas_str = campos.get('horas', '')
        tipo = (campos.get('tipo') or '').lower()

        if (not monto_str) and (not campos.get('monto_bruto')) and horas_str and tipo:
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
        
        if campos.get('monto_bruto'):
            campos['monto'] = str(int(campos['monto_bruto']))
            campos['monto_origen'] = campos.get('monto_origen') or 'prefer_bruto'

                # si el monto viene de prefer_bruto, no lo sobre-escribas con cálculos
        if campos.get('monto_origen') == 'prefer_bruto':
            return campos


        return campos
    
    def _calculate_periodo_basic(self, campos: Dict) -> Dict:
        """Cálculo básico de periodo: PRIORIDAD = fecha_documento (encabezado)."""
        periodo_iso = (campos.get('periodo_servicio') or '').strip()
        fecha_doc = (campos.get('fecha_documento') or '').strip()

        # 1) Si hay fecha de encabezado, manda SIEMPRE (y alinea periodo_servicio)
        if fecha_doc:
            dt = datetime.strptime(fecha_doc, "%Y-%m-%d")
            campos['mes'] = dt.month
            campos['anio'] = dt.year
            campos['mes_nombre'] = self.month_names.get(dt.month, f"Mes {dt.month}")
            campos['periodo_servicio'] = f"{dt.year:04d}-{dt.month:02d}"

            # Congela derivados para el export
            campos['fecha_dt'] = dt
            campos['periodo_dt'] = dt.replace(day=1)
            campos['periodo_final'] = dt  # si tu export usa este campo, queda igual al encabezado
            return campos

        # 2) Sin fecha: si el periodo viene YYYY-MM válido, úsalo
        if periodo_iso and not periodo_iso.startswith('XXXX-'):
            yy = int(periodo_iso[:4]); mm = int(periodo_iso[5:7])
            campos['mes'] = mm
            campos['anio'] = yy
            campos['mes_nombre'] = self.month_names.get(mm, f"Mes {mm}")

            # Derivados mínimos para export
            campos['fecha_dt'] = None
            campos['periodo_dt'] = datetime(yy, mm, 1)
            campos['periodo_final'] = campos['periodo_dt']
            return campos

        # 3) Sin fecha y con XXXX-MM: guarda solo el mes
        if periodo_iso.startswith('XXXX-'):
            mm = int(periodo_iso[5:7])
            campos['mes'] = mm
            campos['anio'] = None
            campos['mes_nombre'] = self.month_names.get(mm, f"Mes {mm}")
            campos['fecha_dt'] = None
            campos['periodo_dt'] = None
            campos['periodo_final'] = None
            return campos

        # 4) Nada definido todavía
        campos['mes'] = None
        campos['anio'] = None
        campos['mes_nombre'] = None
        campos['fecha_dt'] = None
        campos['periodo_dt'] = None
        campos['periodo_final'] = None
        return campos

