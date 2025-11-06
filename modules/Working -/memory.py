# modules/memory.py
"""
Sistema de memoria para autocompletado de campos
Versión 3.1.1 - Con método autofill implementado
"""
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, Optional

class Memory:
    """
    Sistema de memoria que aprende de boletas procesadas anteriormente
    para autocompletar campos faltantes en nuevos documentos
    """
    
    def __init__(self, path: Path = Path("memory.json")):
        self.path = Path(path)
        self.data = {
            "rut_to_name": {},           # RUT -> nombre más frecuente
            "rut_to_convenio": {},       # RUT -> convenio más frecuente
            "rut_stats": {},             # RUT -> estadísticas de uso
            "name_variations": {},        # Variaciones de nombres por RUT
            "processing_history": []      # Historial de procesamiento
        }
        self._load()
    
    def _load(self):
        """Carga la memoria desde el archivo JSON"""
        if self.path.exists():
            try:
                loaded_data = json.loads(self.path.read_text(encoding="utf-8"))
                # Actualizar con los datos cargados, manteniendo estructura por defecto
                self.data.update(loaded_data)
            except Exception as e:
                print(f"⚠️  No se pudo cargar memoria: {e}")
                self.data = {
                    "rut_to_name": {},
                    "rut_to_convenio": {},
                    "rut_stats": {},
                    "name_variations": {},
                    "processing_history": []
                }
    
    def save(self):
        """Guarda la memoria en el archivo JSON"""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"⚠️  No se pudo guardar memoria: {e}")
    
    def learn(self, campos: Dict):
        """
        Aprende de un registro procesado exitosamente
        
        Args:
            campos: Diccionario con los campos extraídos de la boleta
        """
        rut = campos.get('rut', '').strip()
        nombre = campos.get('nombre', '').strip()
        convenio = campos.get('convenio', '').strip()
        
        if not rut:
            return
        
        # Aprender nombre
        if nombre:
            if rut not in self.data["rut_to_name"]:
                self.data["rut_to_name"][rut] = nombre
            
            # Registrar variaciones de nombre
            if rut not in self.data["name_variations"]:
                self.data["name_variations"][rut] = []
            if nombre not in self.data["name_variations"][rut]:
                self.data["name_variations"][rut].append(nombre)
        
        # Aprender convenio
        if convenio:
            if rut not in self.data["rut_to_convenio"]:
                self.data["rut_to_convenio"][rut] = {}
            
            conv_dict = self.data["rut_to_convenio"][rut]
            if isinstance(conv_dict, str):
                # Convertir formato antiguo a nuevo
                conv_dict = {conv_dict: 1}
                self.data["rut_to_convenio"][rut] = conv_dict
            
            conv_dict[convenio] = conv_dict.get(convenio, 0) + 1
        
        # Actualizar estadísticas
        if rut not in self.data["rut_stats"]:
            self.data["rut_stats"][rut] = {
                "count": 0,
                "last_seen": "",
                "convenios": []
            }
        
        self.data["rut_stats"][rut]["count"] += 1
        self.data["rut_stats"][rut]["last_seen"] = campos.get('fecha_documento', '')
        
        # Guardar cambios
        self.save()
    
    def autofill(self, campos: Dict) -> Dict:
        """
        Autocompleta campos faltantes basándose en información histórica
        
        Args:
            campos: Diccionario con los campos parcialmente extraídos
            
        Returns:
            Diccionario con campos completados donde fue posible
        """
        rut = campos.get('rut', '').strip()
        
        if not rut:
            # No hay RUT, no se puede autocompletar
            return campos
        
        campos_mejorados = campos.copy()
        
        # Autocompletar nombre si falta o tiene baja confianza
        nombre_actual = campos.get('nombre', '').strip()
        nombre_conf = campos.get('nombre_confidence', 0.0)
        
        if (not nombre_actual or nombre_conf < 0.5) and rut in self.data["rut_to_name"]:
            nombre_historico = self.data["rut_to_name"][rut]
            if nombre_historico:
                campos_mejorados['nombre'] = nombre_historico
                campos_mejorados['nombre_confidence'] = 0.85  # Confianza basada en historial
                campos_mejorados['nombre_origen'] = 'memoria'
        
        # Autocompletar convenio si falta o tiene baja confianza
        convenio_actual = campos.get('convenio', '').strip()
        convenio_conf = campos.get('convenio_confidence', 0.0)
        
        if (not convenio_actual or convenio_conf < 0.4) and rut in self.data["rut_to_convenio"]:
            convenios_dict = self.data["rut_to_convenio"][rut]
            
            if isinstance(convenios_dict, dict) and convenios_dict:
                # Obtener el convenio más frecuente
                convenio_mas_comun = max(convenios_dict.items(), key=lambda x: x[1])[0]
                campos_mejorados['convenio'] = convenio_mas_comun
                campos_mejorados['convenio_confidence'] = 0.70  # Confianza moderada
                campos_mejorados['convenio_origen'] = 'memoria'
        
        return campos_mejorados
    
    def get_name_by_rut(self, rut: str) -> str:
        """Obtiene el nombre asociado a un RUT"""
        return self.data.get("rut_to_name", {}).get(rut, "")
    
    def set_name_for_rut(self, rut: str, nombre: str):
        """Asocia un nombre a un RUT"""
        self.data.setdefault("rut_to_name", {})[rut] = nombre
        self.save()
    
    def get_convenio_by_rut(self, rut: str) -> str:
        """Obtiene el convenio más común asociado a un RUT"""
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
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas de la memoria"""
        return {
            "total_ruts": len(self.data.get("rut_to_name", {})),
            "total_convenios_únicos": len(set(
                c for convs in self.data.get("rut_to_convenio", {}).values()
                for c in (convs.keys() if isinstance(convs, dict) else [convs])
            )),
            "procesados_total": sum(
                stats.get("count", 0) 
                for stats in self.data.get("rut_stats", {}).values()
            )
        }
    
    def clear(self):
        """Limpia toda la memoria"""
        self.data = {
            "rut_to_name": {},
            "rut_to_convenio": {},
            "rut_stats": {},
            "name_variations": {},
            "processing_history": []
        }
        self.save()