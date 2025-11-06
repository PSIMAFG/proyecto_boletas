# AGREGAR ESTOS MÉTODOS A LA CLASE BatchMemory en data_processing.py (después de _normalize_name)

def normalize_by_rut_decreto(self, registros: List[Dict], log_callback=None) -> List[Dict]:
    """
    NUEVO v4.1: Normaliza montos/horas cuando RUT + Decreto coinciden
    Si hay múltiples valores, usa el más común
    """
    # Construir mapeo RUT+Decreto → [montos, horas]
    rd_map = defaultdict(lambda: {"montos": [], "horas": [], "registros": []})
    
    for r in registros:
        rut = r.get('rut', '').strip()
        decreto = r.get('decreto_alcaldicio', '').strip()
        monto = r.get('monto', '').strip()
        horas = r.get('horas', '').strip()
        
        if rut and decreto:
            key = f"{rut}_{decreto}"
            if monto:
                rd_map[key]["montos"].append(monto)
            if horas:
                rd_map[key]["horas"].append(horas)
            rd_map[key]["registros"].append(r)
    
    # Calcular valores más comunes (canónicos) para cada RUT+Decreto
    rd_canonical = {}
    normalizaciones = 0
    
    for key, values in rd_map.items():
        canonical = {}
        
        # Monto más común
        if values["montos"]:
            monto_counter = Counter(values["montos"])
            canonical["monto"] = monto_counter.most_common(1)[0][0]
            canonical["monto_count"] = monto_counter.most_common(1)[0][1]
        
        # Horas más comunes
        if values["horas"]:
            horas_counter = Counter(values["horas"])
            canonical["horas"] = horas_counter.most_common(1)[0][0]
            canonical["horas_count"] = horas_counter.most_common(1)[0][1]
        
        rd_canonical[key] = canonical
    
    # Aplicar normalización a registros que no coincidan con el canónico
    for r in registros:
        rut = r.get('rut', '').strip()
        decreto = r.get('decreto_alcaldicio', '').strip()
        
        if rut and decreto:
            key = f"{rut}_{decreto}"
            if key in rd_canonical:
                canonical = rd_canonical[key]
                
                # Normalizar monto si es diferente
                monto_actual = r.get('monto', '').strip()
                if canonical.get("monto") and monto_actual != canonical["monto"]:
                    # Solo normalizar si el canónico tiene suficiente soporte
                    if canonical.get("monto_count", 0) >= 2:
                        r['monto'] = canonical["monto"]
                        r['monto_origen'] = 'normalizado_rut_decreto'
                        r['monto_confidence'] = 0.90
                        normalizaciones += 1
                
                # Normalizar horas si son diferentes
                horas_actual = r.get('horas', '').strip()
                if canonical.get("horas") and horas_actual != canonical["horas"]:
                    if canonical.get("horas_count", 0) >= 2:
                        r['horas'] = canonical["horas"]
                        r['horas_origen'] = 'normalizado_rut_decreto'
                        normalizaciones += 1
    
    if log_callback and normalizaciones > 0:
        log_callback(f"   ✓ {normalizaciones} campos normalizados por RUT+Decreto", "success")
    
    return registros

def get_canonical_payment(self, rut: str, decreto: str) -> Dict:
    """
    NUEVO v4.1: Obtiene el pago canónico para un RUT + Decreto en el batch actual
    Retorna: {"monto": str, "horas": str} o {}
    """
    if not rut or not decreto:
        return {}
    
    key = f"{rut}_{decreto}"
    montos = []
    horas_list = []
    
    for registro in self.registros:
        if (registro.get('rut', '').strip() == rut and 
            registro.get('decreto_alcaldicio', '').strip() == decreto):
            
            monto = registro.get('monto', '').strip()
            horas = registro.get('horas', '').strip()
            
            if monto:
                montos.append(monto)
            if horas:
                horas_list.append(horas)
    
    result = {}
    if montos:
        result["monto"] = Counter(montos).most_common(1)[0][0]
    if horas_list:
        result["horas"] = Counter(horas_list).most_common(1)[0][0]
    
    return result
