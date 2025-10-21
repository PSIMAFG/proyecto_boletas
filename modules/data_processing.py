# modules/data_processing.py (Versión Corregida)
"""
Módulo optimizado de procesamiento de datos - CORREGIDO
Versión 3.1 - Con umbrales ajustados y mejor detección
"""
import re
import cv2
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import *
from modules.utils import *
from modules.ocr_extraction import OCRExtractorOptimized


class SmartFieldExtractor:
    """Extractor inteligente de campos - MEJORADO"""
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict:
        """Pre-compila todos los patrones regex para mejor rendimiento"""
        return {
            'rut': re.compile(r'(\d{1,2}\.?\d{3}\.?\d{3}[\-\s]?[\dkK])', re.IGNORECASE),
            'rut_loose': re.compile(r'(\d{7,8}[\s]?[\dkK])', re.IGNORECASE),
            'folio': re.compile(r'(?:N[°ºo\s]*|No\.?|Nro\.?|Folio|Numero)\s*[:.]?\s*(\d{3,7})', re.IGNORECASE),
            'folio_simple': re.compile(r'\b(\d{4,7})\b'),
            'fecha_completa': re.compile(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{2,4})', re.IGNORECASE),
            'fecha_num': re.compile(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})'),
            'monto_currency': re.compile(r'\$\s*([\d\.\,]+)'),
            'monto_simple': re.compile(r'(\d{1,3}(?:[\.\,]\d{3})+)'),
            'decreto': re.compile(r'D\.?A\.?\s*N?[°ºo]?\s*(\d{2,6})', re.IGNORECASE),
            'horas': re.compile(r'(\d{1,3})\s*(?:horas?|hrs?|h\.)', re.IGNORECASE),
        }
    
    def extract_rut_improved(self, text: str) -> Tuple[str, float]:
        """Extrae RUT con validación - MÁS FLEXIBLE"""
        candidates = []
        
        # Buscar RUTs con formato completo
        for match in self.patterns['rut'].finditer(text):
            rut = match.group(1)
            # Normalizar formato
            rut = rut.replace(' ', '').upper()
            if '-' not in rut and len(rut) >= 8:
                rut = rut[:-1] + '-' + rut[-1]
            
            # Agregar puntos si no los tiene
            if '.' not in rut and '-' in rut:
                parts = rut.split('-')
                if len(parts[0]) == 7:
                    rut = f"{parts[0][0]}.{parts[0][1:4]}.{parts[0][4:7]}-{parts[1]}"
                elif len(parts[0]) == 8:
                    rut = f"{parts[0][0:2]}.{parts[0][2:5]}.{parts[0][5:8]}-{parts[1]}"
            
            if dv_ok(rut):
                candidates.append((rut, 0.90))
            else:
                # Aún así agregar con menor confianza
                candidates.append((rut, 0.50))
        
        # Buscar RUTs sin formato
        if not candidates:
            for match in self.patterns['rut_loose'].finditer(text):
                rut_raw = match.group(1).replace(' ', '').upper()
                if len(rut_raw) >= 8:
                    body = rut_raw[:-1]
                    dv = rut_raw[-1]
                    
                    if len(body) == 7:
                        formatted = f"{body[0]}.{body[1:4]}.{body[4:7]}-{dv}"
                    else:
                        formatted = f"{body[0:2]}.{body[2:5]}.{body[5:8]}-{dv}"
                    
                    if dv_ok(formatted):
                        candidates.append((formatted, 0.70))
                    else:
                        candidates.append((formatted, 0.40))
        
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0]
        
        return "", 0.0
    
    def extract_folio_improved(self, text: str) -> Tuple[str, float]:
        """Extrae número de folio - MÁS FLEXIBLE"""
        candidates = []
        
        # Buscar con patrón completo
        for match in self.patterns['folio'].finditer(text):
            folio = match.group(1).strip()
            if folio and folio.isdigit() and len(folio) >= 3:
                candidates.append((folio, 0.85))
        
        # Buscar números que podrían ser folios en las primeras líneas
        if not candidates:
            lines = text.split('\n')[:15]  # Buscar en más líneas
            for line in lines:
                # Si la línea contiene palabras clave de folio
                if any(word in line.lower() for word in ['boleta', 'n°', 'no.', 'folio', 'numero']):
                    for match in self.patterns['folio_simple'].finditer(line):
                        num = match.group(1)
                        if 100 <= int(num) <= 9999999:  # Rango más amplio
                            candidates.append((num, 0.60))
        
        # Si aún no hay candidatos, buscar cualquier número de 4-7 dígitos
        if not candidates:
            for match in self.patterns['folio_simple'].finditer(text[:500]):  # Buscar al inicio
                num = match.group(1)
                if 1000 <= int(num) <= 9999999:
                    candidates.append((num, 0.40))
        
        if candidates:
            candidates.sort(key=lambda x: (x[1], len(x[0])), reverse=True)
            return candidates[0]
        
        return "", 0.0
    
    def extract_fecha_improved(self, text: str) -> Tuple[str, float]:
        """Extrae fecha con múltiples formatos - MÁS FLEXIBLE"""
        candidates = []
        current_year = datetime.now().year
        
        # Formato: "15 de marzo de 2024"
        for match in self.patterns['fecha_completa'].finditer(text):
            try:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                
                if year < 100:
                    year = 2000 + year if year <= (current_year % 100) + 5 else 1900 + year
                
                month = MESES.get(month_name, 0)
                
                if 1 <= day <= 31 and 1 <= month <= 12 and 2015 <= year <= current_year + 1:
                    date_obj = datetime(year, month, day)
                    iso_date = date_obj.strftime("%Y-%m-%d")
                    candidates.append((iso_date, 0.90))
            except:
                pass
        
        # Formato numérico
        for match in self.patterns['fecha_num'].finditer(text):
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                
                if year < 100:
                    year = 2000 + year if year <= (current_year % 100) + 5 else 1900 + year
                
                if 1 <= day <= 31 and 1 <= month <= 12 and 2015 <= year <= current_year + 1:
                    date_obj = datetime(year, month, day)
                    iso_date = date_obj.strftime("%Y-%m-%d")
                    candidates.append((iso_date, 0.80))
            except:
                pass
        
        # Si no hay candidatos, buscar el año actual y mes
        if not candidates:
            year_match = re.search(rf'{current_year}', text)
            if year_match:
                # Buscar mes cercano
                for month_name, month_num in MESES.items():
                    if month_name in text.lower():
                        # Asumir día 15 si no se encuentra
                        try:
                            date_obj = datetime(current_year, month_num, 15)
                            iso_date = date_obj.strftime("%Y-%m-%d")
                            candidates.append((iso_date, 0.50))
                        except:
                            pass
        
        if candidates:
            candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
            return candidates[0]
        
        return "", 0.0
    
    def extract_monto_improved(self, text: str) -> Tuple[str, float]:
        """Extrae monto - MÁS FLEXIBLE"""
        candidates = []
        
        # Buscar montos con símbolo de peso
        for match in self.patterns['monto_currency'].finditer(text):
            amount_str = match.group(1)
            normalized = normaliza_monto(amount_str)
            if normalized:
                try:
                    amount = float(normalized)
                    if 10000 <= amount <= 5000000:  # Rango más amplio
                        candidates.append((normalized, 0.85, amount))
                except:
                    pass
        
        # Buscar números grandes que podrían ser montos
        for match in self.patterns['monto_simple'].finditer(text):
            amount_str = match.group(1)
            normalized = normaliza_monto(amount_str)
            if normalized:
                try:
                    amount = float(normalized)
                    if 10000 <= amount <= 5000000:
                        # Dar más confianza si está cerca de palabras clave
                        context = text[max(0, match.start()-50):min(len(text), match.end()+50)].lower()
                        if any(word in context for word in ['total', 'monto', 'bruto', 'honorario', 'pagar']):
                            candidates.append((normalized, 0.75, amount))
                        else:
                            candidates.append((normalized, 0.50, amount))
                except:
                    pass
        
        # Seleccionar el monto más probable (generalmente el más alto)
        if candidates:
            # Preferir montos con mayor confianza y valor
            candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
            return candidates[0][0], candidates[0][1]
        
        return "", 0.0
    
    def extract_nombre_smart(self, text: str, file_path: Optional[Path] = None) -> Tuple[str, float]:
        """Extracción inteligente del nombre - SIMPLIFICADA"""
        candidates = []
        
        # Estrategia 1: Buscar después de palabras clave
        name_patterns = [
            (r'(?:Nombre|Prestador|Profesional)\s*:?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]+)', 0.80),
            (r'(?:Razón\s+Social|Señor(?:es)?)\s*:?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]+)', 0.75),
        ]
        
        for pattern, confidence in name_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1).strip()
                name = re.sub(r'\s+', ' ', name)  # Normalizar espacios
                if 5 < len(name) < 100 and ' ' in name:  # Debe tener al menos 2 palabras
                    candidates.append((name, confidence))
        
        # Estrategia 2: Usar el nombre del archivo
        if file_path and not candidates:
            filename = file_path.stem
            # Limpiar el nombre del archivo
            name_from_file = re.sub(r'[_\-\d]+', ' ', filename)
            name_from_file = re.sub(r'\s+', ' ', name_from_file).strip()
            
            if len(name_from_file) > 5 and ' ' in name_from_file:
                candidates.append((name_from_file.title(), 0.60))
        
        # Estrategia 3: Buscar líneas con formato de nombre (mayúsculas)
        if not candidates:
            lines = text.split('\n')[:20]
            for line in lines:
                line = line.strip()
                # Buscar líneas que parezcan nombres
                if re.match(r'^[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+){1,4}$', line):
                    if not any(word in line.lower() for word in ['municipalidad', 'boleta', 'honorario', 'rut', 'fecha']):
                        candidates.append((line, 0.50))
        
        if candidates:
            # Ordenar por confianza y tomar el mejor
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0]
        
        return "", 0.0
    
    def extract_convenio_contextual(self, text: str, glosa: str = "") -> Tuple[str, float]:
        """Extrae el convenio usando análisis contextual"""
        search_text = (text + " " + glosa).upper()
        
        for convenio in KNOWN_CONVENIOS:
            if convenio.upper() in search_text:
                return convenio, 0.80
            
            # Buscar variaciones
            convenio_clean = re.sub(r'[^A-Z]', '', convenio.upper())
            if len(convenio_clean) >= 3 and convenio_clean in search_text:
                return convenio, 0.60
        
        return "", 0.0


class DataProcessorOptimized:
    """Procesador de datos optimizado - CORREGIDO"""
    
    def __init__(self):
        self.ocr_extractor = OCRExtractorOptimized()
        self.field_extractor = SmartFieldExtractor()
    
    def process_file(self, file_path: Path) -> Dict:
        """Procesa un archivo con el pipeline optimizado"""
        try:
            ext = file_path.suffix.lower()
            
            # Procesar según tipo de archivo
            if ext == '.pdf':
                texts, confidences, preview = self.ocr_extractor.process_pdf_optimized(file_path)
            else:
                # Procesar imagen
                img = cv2.imread(str(file_path))
                if img is None:
                    # Intentar con PIL si OpenCV falla
                    from PIL import Image
                    pil_img = Image.open(str(file_path))
                    img = np.array(pil_img)
                
                text, conf, preview_img = self.ocr_extractor.process_image_optimized(img)
                texts = [text] if text else []
                confidences = [conf] if conf else []
                
                # Guardar preview
                preview = ""
                if preview_img is not None:
                    preview = self.ocr_extractor._save_preview(preview_img, file_path, 0)
            
            if not texts:
                raise ValueError("No se pudo extraer texto del archivo")
            
            # Combinar todos los textos
            combined_text = "\n".join(texts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            # Extraer campos
            fields = self._extract_all_fields(combined_text, file_path)
            
            # Agregar metadatos
            fields['archivo'] = str(file_path)
            fields['paginas'] = len(texts) if ext == '.pdf' else 1
            fields['confianza'] = round(avg_confidence, 3)
            fields['preview_path'] = preview if preview else ""
            
            # IMPORTANTE: Ajustar el criterio de needs_review
            fields['needs_review'] = self._needs_review(fields, avg_confidence)
            
            # Calcular score de calidad
            fields['quality_score'] = self._calculate_quality_score(fields)
            
            print(f"Procesado: {file_path.name} - Confianza: {avg_confidence:.2%} - Review: {fields['needs_review']}")
            
            return fields
            
        except Exception as e:
            print(f"Error procesando {file_path}: {e}")
            return {
                'archivo': str(file_path),
                'error': str(e),
                'needs_review': True,
                'confianza': 0.0,
                'preview_path': ""
            }
    
    def _extract_all_fields(self, text: str, file_path: Path) -> Dict:
        """Extrae todos los campos usando el extractor inteligente"""
        fields = {}
        
        # Extraer campos principales
        rut, rut_conf = self.field_extractor.extract_rut_improved(text)
        fields['rut'] = rut
        fields['rut_confidence'] = rut_conf
        
        folio, folio_conf = self.field_extractor.extract_folio_improved(text)
        fields['nro_boleta'] = folio
        fields['folio_confidence'] = folio_conf
        
        fecha, fecha_conf = self.field_extractor.extract_fecha_improved(text)
        fields['fecha_documento'] = fecha
        fields['fecha_confidence'] = fecha_conf
        
        monto, monto_conf = self.field_extractor.extract_monto_improved(text)
        fields['monto'] = monto
        fields['monto_confidence'] = monto_conf
        
        nombre, nombre_conf = self.field_extractor.extract_nombre_smart(text, file_path)
        fields['nombre'] = nombre
        fields['nombre_confidence'] = nombre_conf
        
        # Extraer glosa (simplificado)
        glosa_match = re.search(r'(?:por|glosa|detalle|descripción)\s*:?\s*(.{10,200})', 
                               text, re.IGNORECASE | re.DOTALL)
        fields['glosa'] = glosa_match.group(1).strip()[:200] if glosa_match else ""
        
        # Extraer convenio
        convenio, convenio_conf = self.field_extractor.extract_convenio_contextual(text, fields.get('glosa', ''))
        fields['convenio'] = convenio
        fields['convenio_confidence'] = convenio_conf
        
        # Campos adicionales
        horas_match = re.search(r'(\d{1,3})\s*(?:horas?|hrs?)', text, re.IGNORECASE)
        fields['horas'] = horas_match.group(1) if horas_match else ""
        
        decreto_match = re.search(r'D\.?A\.?\s*N?[°ºo]?\s*(\d{2,6})', text, re.IGNORECASE)
        fields['decreto_alcaldicio'] = decreto_match.group(1) if decreto_match else ""
        
        tipo = "mensual" if "mensual" in text.lower() else "semanal" if "semanal" in text.lower() else ""
        fields['tipo'] = tipo
        
        return fields
    
    def _needs_review(self, fields: Dict, avg_confidence: float) -> bool:
        """Determina si el registro necesita revisión manual - AJUSTADO"""
        # Campos críticos
        critical_fields = ['rut', 'nro_boleta', 'fecha_documento', 'monto']
        
        # Contar campos críticos presentes
        critical_present = sum(1 for field in critical_fields if fields.get(field))
        
        # Si tiene al menos 3 de 4 campos críticos, probablemente está bien
        if critical_present >= 3:
            # Verificar confianza de los campos presentes
            low_confidence = any(
                fields.get(f'{field}_confidence', 0) < 0.40  # REDUCIDO de 0.70
                for field in critical_fields
                if fields.get(field) and f'{field}_confidence' in fields
            )
            
            # Solo marcar para revisión si la confianza es muy baja
            if not low_confidence and avg_confidence >= 0.40:  # REDUCIDO de 0.65
                return False
        
        # Si falta más de la mitad de campos críticos, necesita revisión
        if critical_present < 2:
            return True
        
        # Si la confianza general es muy baja
        if avg_confidence < 0.35:  # REDUCIDO de 0.65
            return True
        
        # Si no tiene nombre ni RUT
        if not fields.get('rut') and not fields.get('nombre'):
            return True
        
        return False
    
    def _calculate_quality_score(self, fields: Dict) -> float:
        """Calcula un score de calidad del 0 al 1"""
        score = 0.0
        weights = {
            'rut': 0.25,
            'nro_boleta': 0.15,
            'fecha_documento': 0.15,
            'monto': 0.25,
            'nombre': 0.15,
            'convenio': 0.05
        }
        
        for field, weight in weights.items():
            if fields.get(field):
                # Agregar peso base por campo presente
                score += weight * 0.6
                
                # Agregar peso adicional por confianza
                conf_field = f'{field}_confidence'
                if conf_field in fields:
                    score += weight * 0.4 * fields[conf_field]
                else:
                    score += weight * 0.4
        
        return round(min(score, 1.0), 3)