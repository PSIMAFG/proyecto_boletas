# SPDX-License-Identifier: BUSL-1.1
# © 2025 Matías A. Fernández

# modules/data_processing.py
"""
Módulo de procesamiento de datos extraídos de boletas
"""
import re
import difflib
from pathlib import Path
from typing import Optional, Dict, List
import numpy as np
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import *
from modules.utils import *
from modules.ocr_extraction import OCRExtractor

class DataProcessor:
    """Clase para procesar y extraer campos de los textos OCR"""
    
    def __init__(self):
        self.ocr_extractor = OCRExtractor()
    
    def recorte_boleta(self, txt: str) -> str:
        """Recorta la sección 'Boleta de Honorarios' del texto"""
        start = re.search(r'BOLETA\s+DE\s+HONORARIOS', txt, re.IGNORECASE)
        if not start:
            return txt
        
        candidates = [
            re.search(r'Fecha\s*/\s*Hora\s*Emisi[oó]n', txt, re.IGNORECASE),
            re.search(r'Verifique\s+este\s+documento', txt, re.IGNORECASE),
            re.search(r'\bRES\.\s*EX\.', txt, re.IGNORECASE),
            re.search(r'\bINFORME\b', txt, re.IGNORECASE),
            re.search(r'\bCONTRATO\b', txt, re.IGNORECASE),
        ]
        
        ends = [m.start() for m in candidates if m]
        return txt[start.start(): min(ends)] if ends else txt[start.start():]
    
    def find_by_anchor(self, text: str, anchors: List[str], max_chars=120) -> str:
        """Busca texto después de anclajes específicos"""
        lines = [re.sub(r'[|]+', ' ', ln) for ln in text.splitlines()]
        
        for i, ln in enumerate(lines):
            for a in anchors:
                if re.search(a, ln, re.IGNORECASE):
                    candidatos = []
                    after = ln.split(':', 1)[1].strip() if ':' in ln else ''
                    if after:
                        candidatos.append(after)
                    if i + 1 < len(lines): 
                        candidatos.append(lines[i+1].strip())
                    if i + 2 < len(lines): 
                        candidatos.append(lines[i+2].strip())
                    
                    for cand in candidatos:
                        c = re.sub(r'\s{2,}', ' ', cand).strip(' :')
                        if looks_like_person_name(c):
                            return c[:max_chars]
        return ""
    
    def candidate_name_from_filename(self, path: Path) -> str:
        """Extrae un posible nombre del nombre del archivo"""
        stem = Path(path).stem
        s = re.sub(r'[_\-\.]+', ' ', stem)
        s = re.sub(r'\([^)]*\)', ' ', s)
        s = re.sub(r'\d+', ' ', s)
        
        tokens = [t for t in s.split() if t.strip()]
        bad = {'boleta','honorarios','honorario','aps','dir','pai','praps',
               'hcv','ssvsa','senda','programa','pg','doc','b'}
        
        tokens = [t for t in tokens if t.lower() not in bad and 
                 t.lower() not in MESES and t.lower() not in MESES_SHORT]
        tokens = [t for t in tokens if re.match(r'^[A-Za-zÁÉÍÓÚÑáéíóú]{2,}$', t)]
        
        if not tokens:
            return ""
        
        best = []
        cur = []
        for t in tokens:
            if re.match(r'^[A-Za-zÁÉÍÓÚÑáéíóú]+$', t):
                cur.append(t)
            else:
                if len(cur) > len(best):
                    best = cur
                cur = []
        
        if len(cur) > len(best):
            best = cur
        
        if len(best) >= 3:
            cand = " ".join(best[:5]).title()
            return cand
        
        cand = " ".join(tokens[:4]).title()
        return cand
    
    def score_line_for_candidate(self, line: str, cand_tokens: List[str]) -> float:
        """Puntúa una línea según su similitud con tokens candidatos"""
        line_clean = re.sub(r'[^A-Za-zÁÉÍÓÚÑáéíóú\s\-]', ' ', line)
        ltokens = [t.lower() for t in line_clean.split() if len(t) >= 2]
        
        if not ltokens:
            return 0.0
        
        hits = sum(1 for t in cand_tokens if t in ltokens)
        ratio = difflib.SequenceMatcher(a=line_clean.lower(), b=" ".join(cand_tokens)).ratio()
        bonus = 0.2 if looks_like_person_name(line_clean) else 0.0
        
        return hits + ratio + bonus
    
    def extract_nombre(self, text: str, zona: str, archivo_path: Optional[Path]) -> str:
        """Extrae el nombre del prestador de servicios"""
        NOMBRE_ANCLAS = [
            r'Raz[oó]n\s*Social',
            r'Nombre\s*(?:\/?\s*Raz[oó]n\s*Social)?',
            r'Contribuyente',
            r'Emisor',
            r'Señor(?:es)?',
            r'Proveedor',
            r'Prestador',
        ]
        
        cand_file = self.candidate_name_from_filename(archivo_path) if archivo_path else ""
        
        # Buscar por anclajes
        n = self.find_by_anchor(zona, NOMBRE_ANCLAS, max_chars=120)
        if n and looks_like_person_name(n):
            return n
        
        # Buscar antes del RUT
        sen_idx = re.search(r'Señor(?:es)?\s*:', zona, re.IGNORECASE)
        sen_pos = sen_idx.start() if sen_idx else None
        lines = [re.sub(r'[|]+', ' ', ln).strip() for ln in zona.splitlines()]
        text_join = "\n".join(lines)
        
        rut_matches = list(RUT_ANCHOR_RE.finditer(text_join)) or list(RUT_RE.finditer(text_join))
        chosen_rut_pos = None
        
        if rut_matches:
            for m in rut_matches:
                if sen_pos is None or m.start() < sen_pos:
                    chosen_rut_pos = m.start()
                    break
            
            if chosen_rut_pos is None:
                chosen_rut_pos = rut_matches[0].start()
        
        if chosen_rut_pos is not None:
            acc = 0
            for idx, ln in enumerate(lines):
                acc_next = acc + len(ln) + 1
                if acc <= chosen_rut_pos < acc_next:
                    best = ""
                    for j in range(max(0, idx-3), idx):
                        cand = lines[j].strip(' :')
                        if looks_like_person_name(cand):
                            if len(cand) > len(best):
                                best = cand
                    if best:
                        return best
                    break
                acc = acc_next
        
        # Usar nombre del archivo si coincide
        if cand_file:
            cand_tokens = [t.lower() for t in cand_file.split() if len(t) >= 2]
            best_line = ""
            best_score = 0.0
            
            for ln in (zona.splitlines() or text.splitlines()):
                sc = self.score_line_for_candidate(ln, cand_tokens)
                if sc > best_score:
                    best_score = sc
                    best_line = ln
            
            if best_line and best_score >= 1.5 and looks_like_person_name(best_line):
                return re.sub(r'\s{2,}', ' ', best_line).strip(' :').title()
            
            if looks_like_person_name(cand_file):
                return cand_file
        
        # Buscar entre "BOLETA DE HONORARIOS" y RUT
        m1 = re.search(r'BOLETA\s+DE\s+HONORARIOS', zona, re.IGNORECASE)
        m2 = RUT_ANCHOR_RE.search(zona) or RUT_RE.search(zona)
        
        if m1 and m2:
            trozo = zona[m1.end():m2.start()]
            cand = max((ln.strip(' :') for ln in trozo.splitlines()
                       if looks_like_person_name(ln)), key=len, default='')
            if cand:
                return cand
        
        return ""
    
    def extract_best_date(self, text: str) -> str:
        """Extrae la mejor fecha del texto"""
        fechas = set()
        
        for m in FECHA_TEXT_RE.finditer(text):
            iso = parse_fecha(m.group(0))
            if iso: 
                fechas.add(iso)
        
        for m in FECHA_NUM_EMI_RE.finditer(text):
            iso = parse_fecha(m.group(1))
            if iso: 
                fechas.add(iso)
        
        for m in FECHA_NUM_RE.finditer(text):
            iso = parse_fecha(m.group(1))
            if iso: 
                fechas.add(iso)
        
        if not fechas:
            return ""
        
        def score(dt_str):
            y = int(dt_str[:4])
            in_band = 1 if 2020 <= y <= 2035 else 0
            from datetime import datetime
            ts = datetime.strptime(dt_str, "%Y-%m-%d").timestamp()
            return (in_band, ts)
        
        return sorted(fechas, key=score)[-1]
    
    def is_noise_line_for_amount(self, ln: str) -> bool:
        """Verifica si una línea es ruido para detección de montos"""
        low = ln.lower()
        
        if any(t in low for t in AMOUNT_NOISE_TERMS):
            return True
        
        # Líneas con muchos dígitos seguidos sin formato de monto
        if re.search(r'\d{9,}', ln) and ('$' not in ln) and ('.' not in ln) and (',' not in ln):
            return True
        
        return False
    
    def extract_number_tokens_from_line(self, ln: str) -> List[str]:
        """Extrae tokens numéricos de una línea"""
        tokens = []
        
        # Buscar montos con símbolo $
        MONEDA_SIM_RE = re.compile(r'\$\s*([0-9][0-9\.\,\s]*)')
        for m in MONEDA_SIM_RE.finditer(ln):
            raw = m.group(1)
            raw = re.match(r'^[0-9][0-9\.\,\s]*', raw).group(0)
            tokens.append(raw.strip())
        
        # Buscar números con formato de miles
        NUM_TOKEN_RE = re.compile(r'([0-9]{1,3}(?:[.\s]\d{3})+(?:,\d{2})?|\d{4,}(?:,\d{2})?|\d{1,3}(?:,\d{2}))')
        for m in NUM_TOKEN_RE.finditer(ln):
            tokens.append(m.group(1))
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        out = []
        for t in tokens:
            k = t.strip()
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        
        return out
    
    def pick_best_amount_from_tokens(self, tokens: List[str], require_formatted: bool, line_has_dollar: bool) -> str:
        """Selecciona el mejor monto de una lista de tokens"""
        best_val = -1.0
        best_str = ""
        
        for tok in tokens:
            if require_formatted and (not line_has_dollar) and ('.' not in tok and ',' not in tok):
                continue
            
            val_str = normaliza_monto(tok)
            if not val_str:
                continue
            
            try:
                val = float(val_str)
            except Exception:
                continue
            
            if plaus_amount(val) and val > best_val:
                best_val = val
                best_str = val_str
        
        return best_str
    
    def find_monto_bruto(self, zona: str) -> str:
        """Encuentra el monto bruto en el texto"""
        lines = [ln.strip() for ln in zona.splitlines() if ln.strip()]
        
        # Buscar líneas con palabras clave de montos
        idx_keys = []
        for i, ln in enumerate(lines):
            low = ln.lower()
            if (("honor" in low) or MONTO_BRUTO_LABEL_RE.search(ln) or
                MONTO_NETO_LABEL_RE.search(ln) or RETENCION_LABEL_RE.search(ln) or
                re.search(r'\btotal\b', low)):
                idx_keys.append(i)
        
        def window_indices(center: int, total: int, r: int = 2):
            a = max(0, center - r)
            b = min(total, center + r + 1)
            return range(a, b)
        
        def scan_block(a_idx_list):
            gross_tokens, net_tokens, ret_tokens, plain_tokens = [], [], [], []
            seen_idx = set()
            
            for idx in a_idx_list:
                for j in window_indices(idx, len(lines), r=2):
                    if j in seen_idx:
                        continue
                    seen_idx.add(j)
                    
                    ln = lines[j]
                    if self.is_noise_line_for_amount(ln):
                        continue
                    
                    toks = self.extract_number_tokens_from_line(ln)
                    if not toks:
                        continue
                    
                    low = ln.lower()
                    if RETENCION_LABEL_RE.search(ln):
                        ret_tokens += toks
                    elif MONTO_BRUTO_LABEL_RE.search(ln) or ("honor" in low):
                        gross_tokens += toks
                    elif MONTO_NETO_LABEL_RE.search(ln) or (("total" in low) and ("honor" not in low)):
                        net_tokens += toks
                    else:
                        plain_tokens += toks
            
            return gross_tokens, net_tokens, ret_tokens, plain_tokens
        
        if idx_keys:
            gross_t, net_t, ret_t, plain_t = scan_block(idx_keys)
            
            # Priorizar monto bruto
            if gross_t:
                has_dollar = any('$' in lines[i] for i in idx_keys)
                amt = self.pick_best_amount_from_tokens(gross_t, require_formatted=False, line_has_dollar=has_dollar)
                if amt:
                    return amt
            
            # Calcular bruto desde neto + retención
            best_net = self.pick_best_amount_from_tokens(net_t, require_formatted=False, line_has_dollar=False) if net_t else ""
            best_ret = self.pick_best_amount_from_tokens(ret_t, require_formatted=False, line_has_dollar=False) if ret_t else ""
            
            if best_net and best_ret:
                try:
                    bruto = float(best_net) + float(best_ret)
                    if plaus_amount(bruto):
                        return str(int(bruto)) if bruto.is_integer() else f"{bruto:.0f}"
                except Exception:
                    pass
            
            # Usar el monto más alto encontrado
            combined = []
            for t in (gross_t + net_t + plain_t):
                v = normaliza_monto(t)
                if v:
                    try:
                        fv = float(v)
                        if plaus_amount(fv):
                            combined.append(fv)
                    except Exception:
                        pass
            
            if combined:
                best = max(combined)
                return str(int(best)) if float(best).is_integer() else str(best)
        
        # Buscar montos con símbolo $
        candidates = []
        for ln in lines:
            if self.is_noise_line_for_amount(ln):
                continue
            
            if '$' in ln:
                toks = self.extract_number_tokens_from_line(ln)
                v = self.pick_best_amount_from_tokens(toks, require_formatted=False, line_has_dollar=True)
                if v:
                    try:
                        candidates.append(float(v))
                    except Exception:
                        pass
        
        if candidates:
            best = max(candidates)
            return str(int(best)) if float(best).is_integer() else str(best)
        
        # Buscar números con formato de miles
        THOUSANDS_GROUP_RE = re.compile(r'^\d{1,3}(?:\.\d{3})+(?:,\d{2})?$')
        fallback = []
        
        for ln in lines:
            if self.is_noise_line_for_amount(ln):
                continue
            
            toks = self.extract_number_tokens_from_line(ln)
            toks = [t for t in toks if THOUSANDS_GROUP_RE.match(t)]
            v = self.pick_best_amount_from_tokens(toks, require_formatted=False, line_has_dollar=('$' in ln))
            
            if v:
                try:
                    fallback.append(float(v))
                except Exception:
                    pass
        
        if fallback:
            best = max(fallback)
            return str(int(best)) if float(best).is_integer() else str(best)
        
        return ""
    
    def extract_fields_from_text(self, full_text: str, archivo_path: Optional[Path] = None) -> Dict:
        """Extrae todos los campos relevantes del texto"""
        text = clean_text(full_text)
        boleta = self.recorte_boleta(text)
        zona = boleta if len(boleta) >= 50 else text
        
        # RUT
        rut = ""
        sen_idx = re.search(r'Señor(?:es)?\s*:', zona, re.IGNORECASE)
        sen_pos = sen_idx.start() if sen_idx else None
        
        for m in (RUT_ANCHOR_RE.finditer(zona) or RUT_RE.finditer(zona)):
            r = m.group(1)
            if sen_pos is None or m.start() < sen_pos:
                if dv_ok(r):
                    rut = r
                    break
        
        if not rut:
            m = RUT_RE.search(zona)
            if m and dv_ok(m.group(1)):
                rut = m.group(1)
        
        # Número de boleta
        nro = ""
        for m in FOLIO_RE.finditer(zona):
            nro = m.group(1)
        
        # Fecha
        fecha = self.extract_best_date(zona)
        
        # Monto
        monto = self.find_monto_bruto(zona)
        
        # Nombre
        nombre = self.extract_nombre(text, zona, archivo_path)
        
        # Glosa
        glosa = ""
        glosa_pat = re.compile(
            r'Por\s+atenci[oó]n\s+profesional\s*:\s*(.+?)(?:\n\s*\n|Total\s+Honorarios|Total\s*$)',
            re.IGNORECASE | re.DOTALL
        )
        mg = glosa_pat.search(zona)
        if mg:
            glosa = re.sub(r'\s+', ' ', mg.group(1)).strip()
        else:
            lines = [l for l in zona.splitlines() if len(l.strip()) > 15]
            glosa = " ".join(lines[-8:]) if lines else ""
        
        # Convenio
        convenio = ""
        for kw in KNOWN_CONVENIOS:
            if re.search(rf'\b{re.escape(kw)}\b', glosa, re.IGNORECASE) or \
               re.search(rf'\b{re.escape(kw)}\b', zona, re.IGNORECASE):
                convenio = kw
                break
        
        # Horas
        horas = ""
        HORAS_RE = re.compile(r'\b(\d{1,3})\s*(?:h|hrs?|horas)\b', re.IGNORECASE)
        m = HORAS_RE.search(glosa or zona)
        if m:
            horas = m.group(1)
        
        # Tipo
        tipo = ""
        TIPO_RE = re.compile(r'\b(semanales?|mensuales?)\b', re.IGNORECASE)
        m = TIPO_RE.search(glosa or zona)
        if m:
            tipo = m.group(1).lower()
        
        # Decreto
        decreto = ""
        DECRETO_RE = re.compile(r'\bD[.\s]?A[.\s]?\s*([0-9]{2,6})(?:\s+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}))?',
                                re.IGNORECASE)
        m = DECRETO_RE.search(zona)
        if m:
            decreto = m.group(1)
        
        return dict(
            nombre=(nombre or "").strip(),
            rut=rut.strip(),
            nro_boleta=nro.strip(),
            fecha_documento=(fecha or "").strip(),
            monto=(monto or "").strip(),
            convenio=convenio.strip(),
            horas=horas.strip(),
            tipo=tipo.strip(),
            glosa=(glosa or "").strip(),
            decreto_alcaldicio=(decreto or "").strip()
        )
    
    def needs_manual_review(self, fields: Dict[str, str], conf_mean: float, text_all: str, conf_thresh: float = 0.45) -> bool:
        """Determina si un registro necesita revisión manual"""
        # Campos requeridos
        required = ['rut', 'nro_boleta', 'fecha_documento', 'monto', 'nombre']
        missing = any(not fields.get(k) for k in required)
        
        # Verificar monto
        monto_ok = False
        try:
            mv = float(fields.get('monto') or 0)
            monto_ok = plaus_amount(mv)
        except Exception:
            monto_ok = False
        
        # Necesita revisión si falta algo crítico o la confianza es baja
        if conf_mean < conf_thresh or missing or not monto_ok:
            return True
        
        return False
    
    def process_file(self, path: Path) -> Dict:
        """Procesa un archivo completo y extrae los campos"""
        ext = path.suffix.lower()
        texts = []
        confs = []
        preview_path = ""
        
        if ext == ".pdf":
            # Primero intentar extraer texto embebido
            embedded_text = self.ocr_extractor.extract_text_from_pdf_embedded(path).strip()
            used_embedded = False
            
            # Verificar si el texto embebido es utilizable
            if len(embedded_text) >= 40 and self.ocr_extractor.check_if_text_is_readable(embedded_text):
                fields_embedded = self.extract_fields_from_text(embedded_text, path)
                # Si tiene campos clave, usar el texto embebido
                if any(fields_embedded.get(k) for k in ("rut", "nro_boleta", "monto")):
                    texts.append(embedded_text)
                    confs.append(0.99)
                    used_embedded = True
            
            # Si no se usó texto embebido o no es legible, usar OCR
            if not used_embedded:
                page_texts, page_confs, prev = self.ocr_extractor.process_pdf_with_ocr(path)
                if prev:
                    preview_path = prev
                if page_texts:
                    texts.extend(page_texts)
                    confs.extend(page_confs)
        else:
            # Procesar imagen
            txt, c, prev = self.ocr_extractor.process_image_with_ocr(path)
            if prev:
                preview_path = prev
            if txt:
                texts.append(txt)
                confs.append(float(c))
        
        if not texts:
            raise RuntimeError("OCR/Extracción no devolvió texto utilizable")
        
        # Combinar textos y calcular confianza
        text_all = "\n".join(texts)
        conf_mean = float(np.mean(confs)) if confs else 0.0
        conf_max = float(np.max(confs)) if confs else 0.0
        
        # Extraer campos
        fields = self.extract_fields_from_text(text_all, path)
        fields['archivo'] = str(path)
        fields['paginas'] = text_all.count("\f") + 1 if ext == ".pdf" else 1
        fields['confianza'] = round(conf_mean, 3)
        fields['confianza_max'] = round(conf_max, 3)
        fields['preview_path'] = preview_path
        fields['needs_review'] = self.needs_manual_review(fields, conf_mean, text_all, conf_thresh=OCR_CONFIDENCE_THRESHOLD)
        
        return fields

