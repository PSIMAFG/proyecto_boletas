# modules/memory.py (v4.1 - Normalización RUT + Decreto)
"""
Sistema de memoria con búsqueda BIDIRECCIONAL y normalización de pagos:
- RUT → Nombre
- Nombre → RUT  
- RUT → Convenio
- RUT + Decreto → Monto/Horas (NUEVO v4.1)
- Historial completo
"""
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Optional
import difflib
from datetime import datetime

class Memory:
    """Sistema de memoria bidireccional para autocompletado inteligente"""
    
    def __init__(self, path: Path = Path("memory.json")):
        self.path = Path(path)
        self.data = {
            "rut_to_name": {},           # RUT → nombre
            "name_to_rut": {},           # NOMBRE → RUT
            "rut_to_convenio": {},       # RUT → convenio(s)
            "rut_stats": {},             # Estadísticas por RUT
            "name_variations": {},        # Variaciones de nombres
            "processing_history": [],     # Historial
            "rut_decreto_to_payment": {} # NUEVO v4.1: RUT + Decreto → Monto/Horas
        }
        self._load()
    
    def _load(self):
        """Carga memoria desde JSON"""
        if self.path.exists():
            try:
                loaded_data = json.loads(self.path.read_text(encoding="utf-8"))
                # Asegurar que exista rut_decreto_to_payment
                if "rut_decreto_to_payment" not in loaded_data:
                    loaded_data["rut_decreto_to_payment"] = {}
                self.data.update(loaded_data)
            except Exception as e:
                print(f"⚠️ No se pudo cargar memoria: {e}")
    
    def save(self):
        """Guarda memoria en JSON"""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"⚠️ No se pudo guardar memoria: {e}")
    
    def learn(self, campos: Dict):
        """Aprende de un registro exitoso"""
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        convenio = campos.get('convenio', '').strip()
        decreto = campos.get('decreto_alcaldicio', '').strip()
        monto = campos.get('monto', '').strip()
        horas = campos.get('horas', '').strip()
        
        if not rut:
            return
        
        # Aprender RUT → Nombre
        if nombre:
            if rut not in self.data["rut_to_name"]:
                self.data["rut_to_name"][rut] = nombre
            
            # Registrar variaciones
            if rut not in self.data["name_variations"]:
                self.data["name_variations"][rut] = []
            if nombre not in self.data["name_variations"][rut]:
                self.data["name_variations"][rut].append(nombre)
            
            # Aprender Nombre → RUT (búsqueda inversa)
            nombre_normalizado = self._normalize_name(nombre)
            if nombre_normalizado:
                self.data.setdefault("name_to_rut", {})[nombre_normalizado] = rut
        
        # Aprender RUT → Convenio
        if convenio:
            if rut not in self.data["rut_to_convenio"]:
                self.data["rut_to_convenio"][rut] = {}
            
            conv_dict = self.data["rut_to_convenio"][rut]
            if isinstance(conv_dict, str):
                conv_dict = {conv_dict: 1}
                self.data["rut_to_convenio"][rut] = conv_dict
            
            conv_dict[convenio] = conv_dict.get(convenio, 0) + 1
        
        # NUEVO v4.1: Aprender RUT + Decreto → Monto/Horas
        if decreto and (monto or horas):
            self.learn_payment_pattern(rut, decreto, monto, horas)
        
        # Actualizar estadísticas
        if rut not in self.data["rut_stats"]:
            self.data["rut_stats"][rut] = {
                "count": 0,
                "last_seen": "",
                "convenios": []
            }
        
        self.data["rut_stats"][rut]["count"] += 1
        self.data["rut_stats"][rut]["last_seen"] = campos.get('fecha_documento', '')
        
        self.save()
    
    def learn_payment_pattern(self, rut: str, decreto: str, monto: str, horas: str):
        """
        NUEVO v4.1: Aprende el patrón de pago RUT + Decreto → Monto/Horas
        Esto permite normalizar automáticamente boletas futuras
        """
        if not rut or not decreto:
            return
        
        if rut not in self.data["rut_decreto_to_payment"]:
            self.data["rut_decreto_to_payment"][rut] = {}
        
        # Guardar o actualizar el patrón
        if decreto in self.data["rut_decreto_to_payment"][rut]:
            # Ya existe, actualizar contador
            existing = self.data["rut_decreto_to_payment"][rut][decreto]
            if existing.get("monto") == monto and existing.get("horas") == horas:
                existing["count"] = existing.get("count", 1) + 1
            else:
                # Conflicto - usar el más común o el más reciente
                if existing.get("count", 1) < 5:  # Si tiene pocas ocurrencias, actualizar
                    existing["monto"] = monto
                    existing["horas"] = horas
                    existing["count"] = 1
        else:
            # Nuevo patrón
            self.data["rut_decreto_to_payment"][rut][decreto] = {
                "monto": monto,
                "horas": horas,
                "count": 1,
                "last_updated": datetime.now().isoformat()
            }
        
        self.save()
    
    def get_payment_by_rut_decreto(self, rut: str, decreto: str) -> Dict:
        """
        NUEVO v4.1: Obtiene monto/horas conocido para RUT + Decreto
        Retorna: {"monto": str, "horas": str, "count": int}
        """
        if not rut or not decreto:
            return {}
        
        if rut in self.data.get("rut_decreto_to_payment", {}):
            return self.data["rut_decreto_to_payment"][rut].get(decreto, {})
        
        return {}
    
    def autofill(self, campos: Dict) -> Dict:
        """Autocompleta campos usando memoria"""
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        
        # CASO 1: Tengo RUT → buscar nombre
        if rut and (not nombre or campos.get('nombre_confidence', 0) < 0.5):
            nombre_historico = self.get_name_by_rut(rut)
            if nombre_historico:
                campos['nombre'] = nombre_historico
                campos['nombre_confidence'] = 0.85
                campos['nombre_origen'] = 'memoria'
        
        # CASO 2: Tengo nombre → buscar RUT
        if nombre and not rut:
            rut_encontrado = self.get_rut_by_name(nombre)
            if rut_encontrado:
                campos['rut'] = rut_encontrado
                campos['rut_confidence'] = 0.80
                campos['rut_origen'] = 'memoria'
        
        # CASO 3: Autocompletar convenio
        convenio_actual = campos.get('convenio', '').strip()
        if (not convenio_actual or campos.get('convenio_confidence', 0) < 0.4) and rut:
            convenio_historico = self.get_convenio_by_rut(rut)
            if convenio_historico:
                campos['convenio'] = convenio_historico
                campos['convenio_confidence'] = 0.70
                campos['convenio_origen'] = 'memoria'
        
        # NUEVO v4.1: CASO 4: Autocompletar monto/horas desde RUT + Decreto
        decreto = campos.get('decreto_alcaldicio', '').strip()
        if rut and decreto:
            known_payment = self.get_payment_by_rut_decreto(rut, decreto)
            if known_payment:
                # Aplicar monto conocido si falta
                if known_payment.get("monto") and not campos.get('monto'):
                    campos['monto'] = known_payment["monto"]
                    campos['monto_confidence'] = 0.95
                    campos['monto_origen'] = 'memoria_rut_decreto'
                
                # Aplicar horas conocidas si faltan
                if known_payment.get("horas") and not campos.get('horas'):
                    campos['horas'] = known_payment["horas"]
                    campos['horas_origen'] = 'memoria_rut_decreto'
        
        return campos
    
    def get_name_by_rut(self, rut: str) -> str:
        """RUT → Nombre"""
        return self.data.get("rut_to_name", {}).get(rut, "")
    
    def get_rut_by_name(self, nombre: str) -> str:
        """
        Nombre → RUT
        Busca por coincidencia exacta o similar
        """
        if not nombre:
            return ""
        
        nombre_norm = self._normalize_name(nombre)
        
        # Búsqueda exacta
        name_to_rut = self.data.get("name_to_rut", {})
        if nombre_norm in name_to_rut:
            return name_to_rut[nombre_norm]
        
        # Búsqueda difusa (similar)
        mejores_matches = difflib.get_close_matches(
            nombre_norm, 
            name_to_rut.keys(), 
            n=1, 
            cutoff=0.85  # 85% de similitud
        )
        
        if mejores_matches:
            return name_to_rut[mejores_matches[0]]
        
        return ""
    
    def set_name_for_rut(self, rut: str, nombre: str):
        """Asocia manualmente nombre a RUT"""
        self.data.setdefault("rut_to_name", {})[rut] = nombre
        nombre_norm = self._normalize_name(nombre)
        if nombre_norm:
            self.data.setdefault("name_to_rut", {})[nombre_norm] = rut
        self.save()
    
    def get_convenio_by_rut(self, rut: str) -> str:
        """Obtiene convenio más común de un RUT"""
        if rut not in self.data.get("rut_to_convenio", {}):
            return ""
        
        convenios = self.data["rut_to_convenio"][rut]
        if isinstance(convenios, str):
            return convenios
        elif isinstance(convenios, dict):
            if not convenios:
                return ""
            return max(convenios.items(), key=lambda x: x[1])[0]
        return ""
    
    def _normalize_name(self, nombre: str) -> str:
        """Normaliza nombre para búsqueda"""
        import unicodedata
        
        # Minúsculas
        nombre = nombre.lower()
        
        # Eliminar acentos
        nombre = ''.join(
            c for c in unicodedata.normalize('NFD', nombre)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Eliminar caracteres especiales, dejar solo letras y espacios
        import re
        nombre = re.sub(r'[^a-z\s]', '', nombre)
        
        # Colapsar espacios múltiples
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        
        return nombre
    
    def get_stats(self) -> Dict:
        """Estadísticas de la memoria"""
        return {
            "total_ruts": len(self.data.get("rut_to_name", {})),
            "total_nombres": len(self.data.get("name_to_rut", {})),
            "total_convenios_únicos": len(set(
                c for convs in self.data.get("rut_to_convenio", {}).values()
                for c in (convs.keys() if isinstance(convs, dict) else [convs])
            )),
            "procesados_total": sum(
                stats.get("count", 0) 
                for stats in self.data.get("rut_stats", {}).values()
            ),
            "patrones_pago": sum(len(v) for v in self.data.get("rut_decreto_to_payment", {}).values())
        }
    
    def clear(self):
        """Limpia toda la memoria"""
        self.data = {
            "rut_to_name": {},
            "name_to_rut": {},
            "rut_to_convenio": {},
            "rut_stats": {},
            "name_variations": {},
            "processing_history": [],
            "rut_decreto_to_payment": {}
        }
        self.save()
