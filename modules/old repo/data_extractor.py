# ============================================================================
# modules/data_extractor.py
# ============================================================================
"""
Extractor de campos de datos
"""
import re
from pathlib import Path
from .config import Config
from .utils import validate_rut, clean_amount, format_date

class DataExtractor:
    """Extrae campos específicos del texto OCR"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def extract_fields(self, text, file_path=None):
        """Extrae todos los campos del texto"""
        fields = {
            "nombre": "",
            "rut": "",
            "nro_boleta": "",
            "fecha_documento": "",
            "monto": "",
            "convenio": "",
            "horas": "",
            "tipo": "",
            "glosa": "",
            "decreto_alcaldicio": ""
        }
        
        if not text:
            return fields
        
        # Extraer cada campo
        fields["nombre"] = self.extract_name(text, file_path)
        fields["rut"] = self.extract_rut(text)
        fields["nro_boleta"] = self.extract_folio(text)
        fields["fecha_documento"] = self.extract_date(text)
        fields["monto"] = self.extract_amount(text)
        fields["convenio"] = self.extract_convenio(text)
        fields["horas"] = self.extract_hours(text)
        fields["tipo"] = self.extract_type(text)
        fields["glosa"] = self.extract_glosa(text)
        fields["decreto_alcaldicio"] = self.extract_decreto(text)
        
        return fields
    
    def extract_name(self, text, file_path=None):
        """Extrae el nombre del prestador"""
        # Buscar después de palabras clave
        patterns = [
            r'Señor(?:es)?\s*:?\s*([^\n]+)',
            r'Nombre\s*:?\s*([^\n]+)',
            r'Prestador\s*:?\s*([^\n]+)',
            r'Emisor\s*:?\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Limpiar nombre
                name = re.sub(r'[^\w\s-]', ' ', name)
                name = ' '.join(name.split())
                if len(name) > 5 and not any(char.isdigit() for char in name):
                    return name.title()
        
        # Intentar desde el nombre del archivo
        if file_path:
            filename = Path(file_path).stem
            # Eliminar números y caracteres especiales
            name = re.sub(r'[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]', ' ', filename)
            name = ' '.join(name.split())
            if len(name) > 5:
                return name.title()
        
        return ""
    
    def extract_rut(self, text):
        """Extrae el RUT"""
        matches = self.config.RUT_PATTERN.findall(text)
        for rut in matches:
            if validate_rut(rut):
                return rut.upper()
        return ""
    
    def extract_folio(self, text):
        """Extrae el número de boleta"""
        match = self.config.FOLIO_PATTERN.search(text)
        if match:
            return match.group(1)
        return ""
    
    def extract_date(self, text):
        """Extrae la fecha del documento"""
        match = self.config.DATE_PATTERN.search(text)
        if match:
            day, month, year = match.groups()
            date_str = f"{day}/{month}/{year}"
            return format_date(date_str)
        return ""
    
    def extract_amount(self, text):
        """Extrae el monto"""
        # Buscar montos después de palabras clave
        patterns = [
            r'Total\s+Honorarios?\s*:?\s*\$?\s*([\d.,]+)',
            r'Monto\s+Bruto\s*:?\s*\$?\s*([\d.,]+)',
            r'Total\s*:?\s*\$?\s*([\d.,]+)',
            r'Honorarios?\s+Brutos?\s*:?\s*\$?\s*([\d.,]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = clean_amount(match.group(1))
                try:
                    value = float(amount)
                    if self.config.MIN_AMOUNT <= value <= self.config.MAX_AMOUNT:
                        return str(int(value))
                except ValueError:
                    continue
        
        # Buscar cualquier monto con símbolo $
        matches = re.findall(r'\$\s*([\d.,]+)', text)
        amounts = []
        for match in matches:
            amount = clean_amount(match)
            try:
                value = float(amount)
                if self.config.MIN_AMOUNT <= value <= self.config.MAX_AMOUNT:
                    amounts.append(value)
            except ValueError:
                continue
        
        if amounts:
            return str(int(max(amounts)))
        
        return ""
    
    def extract_convenio(self, text):
        """Extrae el convenio"""
        text_upper = text.upper()
        for convenio in self.config.KNOWN_CONVENIOS:
            if convenio.upper() in text_upper:
                return convenio
        return ""
    
    def extract_hours(self, text):
        """Extrae las horas trabajadas"""
        match = self.config.HOURS_PATTERN.search(text)
        if match:
            return match.group(1)
        return ""
    
    def extract_type(self, text):
        """Extrae el tipo (mensual/semanal)"""
        if re.search(r'\bmensual', text, re.IGNORECASE):
            return "mensual"
        elif re.search(r'\bsemanal', text, re.IGNORECASE):
            return "semanal"
        return ""
    
    def extract_glosa(self, text):
        """Extrae la glosa"""
        match = self.config.GLOSA_PATTERN.search(text)
        if match:
            glosa = match.group(1).strip()
            # Limpiar glosa
            glosa = re.sub(r'\s+', ' ', glosa)
            return glosa[:200]  # Limitar longitud
        
        # Buscar líneas que parezcan glosa
        lines = text.split('\n')
        for line in lines:
            if len(line) > 30 and 'atención' in line.lower():
                return line.strip()[:200]
        
        return ""
    
    def extract_decreto(self, text):
        """Extrae el decreto alcaldicio"""
        match = self.config.DECRETO_PATTERN.search(text)
        if match:
            return match.group(1)
        return ""


