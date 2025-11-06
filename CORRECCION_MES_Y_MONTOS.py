# ============================================================================
# CORRECCIÓN 1: Agregar al método _on_save de ImprovedReviewDialog en main.py
# ============================================================================

# BUSCAR esta sección (líneas 186-200 aproximadamente):
"""
    def _on_save(self):
        '''Guarda los cambios'''
        result = self.row.copy()
        
        for field, var in self.vars.items():
            if isinstance(var, tk.Text):
                result[field] = var.get("1.0", "end").strip()
            else:
                result[field] = var.get().strip()
        
        result['needs_review'] = False
        result['manually_reviewed'] = True
        
        self.result = result
        self.destroy()
"""

# REEMPLAZAR CON:
"""
    def _on_save(self):
        '''Guarda los cambios'''
        result = self.row.copy()
        
        for field, var in self.vars.items():
            if isinstance(var, tk.Text):
                result[field] = var.get("1.0", "end").strip()
            else:
                result[field] = var.get().strip()
        
        result['needs_review'] = False
        result['manually_reviewed'] = True
        
        # CRITICAL: Recalcular mes_nombre basándose en la fecha_documento actualizada
        result = self._recalculate_period_fields(result)
        
        self.result = result
        self.destroy()
    
    def _recalculate_period_fields(self, campos: Dict) -> Dict:
        '''Recalcula mes, año y mes_nombre basándose en fecha_documento'''
        month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        
        fecha_doc = (campos.get('fecha_documento') or '').strip()
        
        if fecha_doc:
            try:
                dt = datetime.strptime(fecha_doc, "%Y-%m-%d")
                campos['mes'] = dt.month
                campos['anio'] = dt.year
                campos['mes_nombre'] = month_names.get(dt.month, f"Mes {dt.month}")
                campos['periodo_servicio'] = f"{dt.year:04d}-{dt.month:02d}"
                campos['fecha_dt'] = dt
                campos['periodo_dt'] = dt.replace(day=1)
                campos['periodo_final'] = dt
                return campos
            except Exception:
                pass
        
        # Si no hay fecha válida, intentar con periodo_servicio
        periodo_iso = (campos.get('periodo_servicio') or '').strip()
        if periodo_iso and not periodo_iso.startswith('XXXX-'):
            try:
                yy = int(periodo_iso[:4])
                mm = int(periodo_iso[5:7])
                campos['mes'] = mm
                campos['anio'] = yy
                campos['mes_nombre'] = month_names.get(mm, f"Mes {mm}")
            except Exception:
                pass
        
        return campos
"""


# ============================================================================
# CORRECCIÓN 2: Agregar cálculo de monto_num en reportes individuales
# ============================================================================

# BUSCAR en report_generator.py el método _group_by_professional 
# (línea 331 aproximadamente):

"""
    def _group_by_professional(self, df: pd.DataFrame) -> Dict:
        '''Agrupa registros por profesional, verificando coherencia nombre-RUT'''
        profesionales = {}
        
        # Agrupar por RUT
        for rut in df['rut'].unique():
            if not rut or pd.isna(rut):
                continue
            
            registros_rut = df[df['rut'] == rut].copy()
"""

# REEMPLAZAR CON:
"""
    def _group_by_professional(self, df: pd.DataFrame) -> Dict:
        '''Agrupa registros por profesional, verificando coherencia nombre-RUT'''
        profesionales = {}
        
        # CRITICAL: Asegurar que monto_num existe
        if 'monto_num' not in df.columns:
            df['monto_num'] = pd.to_numeric(df.get('monto', 0), errors='coerce').fillna(0)
        
        # Agrupar por RUT
        for rut in df['rut'].unique():
            if not rut or pd.isna(rut):
                continue
            
            registros_rut = df[df['rut'] == rut].copy()
"""


# ============================================================================
# INSTRUCCIONES DE INSTALACIÓN
# ============================================================================

print("""
╔═══════════════════════════════════════════════════════════════════════╗
║  CORRECCIONES PARA MES INCORRECTO Y MONTOS EN 0                      ║
╚═══════════════════════════════════════════════════════════════════════╝

PROBLEMA 1: Mes incorrecto después de revisión manual
------------------------------------------------------
El mes_nombre no se actualiza cuando corriges la fecha en revisión manual.

SOLUCIÓN:
1. Abre main.py
2. Busca el método _on_save (línea ~186)
3. Reemplaza todo el método con el código marcado como "CORRECCIÓN 1" arriba
4. Esto agregará el método _recalculate_period_fields que recalcula 
   automáticamente mes, año y mes_nombre cuando cambias la fecha


PROBLEMA 2: Montos en 0 en reportes individuales
-------------------------------------------------
Los reportes individuales no muestran los montos correctamente.

SOLUCIÓN:
1. Abre modules/report_generator.py
2. Busca el método _group_by_professional (línea ~331)
3. Agrega las 2 líneas marcadas como "CRITICAL" en "CORRECCIÓN 2" arriba
4. Estas líneas aseguran que monto_num esté calculado antes de procesar


PASOS DETALLADOS:
-----------------

PASO 1 - Corregir main.py:

   a) Abre main.py con un editor de texto
   
   b) Busca (Ctrl+F): def _on_save(self):
   
   c) Reemplaza desde "def _on_save(self):" hasta "self.destroy()" 
      (14 líneas) con el código de CORRECCIÓN 1 (58 líneas)
   
   d) Guarda el archivo


PASO 2 - Corregir report_generator.py:

   a) Abre modules/report_generator.py
   
   b) Busca (Ctrl+F): def _group_by_professional
   
   c) Después de la línea "profesionales = {}", agrega estas 2 líneas:
   
      # CRITICAL: Asegurar que monto_num existe
      if 'monto_num' not in df.columns:
          df['monto_num'] = pd.to_numeric(df.get('monto', 0), errors='coerce').fillna(0)
   
   d) Guarda el archivo


PASO 3 - Probar:

   a) Ejecuta python main.py
   
   b) Procesa las boletas
   
   c) Cuando llegues a revisión manual y corrijas la fecha:
      - El mes_nombre ahora se actualizará correctamente
   
   d) Los reportes individuales ahora mostrarán los montos correctos


VERIFICACIÓN:
-------------
✓ Después de revisión manual con fecha 2025-04-01, debería decir "Abril 2025"
✓ Los reportes individuales deben mostrar montos > 0
✓ La columna "Total Monto" en reportes debe sumar correctamente


Si tienes problemas, revisa:
1. Que la indentación sea correcta (4 espacios por nivel)
2. Que no hayas borrado líneas accidentalmente
3. Que los nombres de métodos coincidan exactamente

""")
