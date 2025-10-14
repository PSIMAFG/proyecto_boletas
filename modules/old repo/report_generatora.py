# ============================================================================
# modules/report_generator.py
# ============================================================================
"""
Generador de reportes Excel
"""
import pandas as pd
import xlsxwriter
from pathlib import Path
from datetime import datetime
from .config import Config

class ReportGenerator:
    """Genera reportes en Excel con informes por convenio"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate_excel(self, data, output_path, generate_reports=True):
        """Genera el archivo Excel con los resultados"""
        # Crear DataFrame
        df = pd.DataFrame(data)
        
        # Limpiar datos
        df = self.clean_dataframe(df)
        
        # Crear writer de Excel
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        workbook = writer.book
        
        # Definir formatos
        formats = self.create_formats(workbook)
        
        # Escribir hoja principal
        df.to_excel(writer, sheet_name='Base de Datos', index=False)
        self.format_main_sheet(writer, df, formats)
        
        # Generar reportes por convenio si se solicita
        if generate_reports and 'convenio' in df.columns:
            self.generate_convention_reports(writer, df, formats)
        
        # Guardar
        writer.close()
        
        return output_path
    
    def clean_dataframe(self, df):
        """Limpia y prepara el DataFrame"""
        # Asegurar columnas necesarias
        required_columns = [
            'nombre', 'rut', 'nro_boleta', 'fecha_documento', 'monto',
            'convenio', 'horas', 'tipo', 'glosa', 'decreto_alcaldicio',
            'archivo', 'confianza'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Convertir monto a numérico
        df['monto_num'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0)
        
        # Convertir fecha
        df['fecha_dt'] = pd.to_datetime(df['fecha_documento'], errors='coerce')
        
        # Agregar mes y año
        df['mes'] = df['fecha_dt'].dt.month
        df['año'] = df['fecha_dt'].dt.year
        
        return df
    
    def create_formats(self, workbook):
        """Crea formatos para el Excel"""
        return {
            'header': workbook.add_format({
                'bold': True,
                'bg_color': '#D9E2F3',
                'border': 1
            }),
            'currency': workbook.add_format({
                'num_format': '#,##0',
                'border': 1
            }),
            'date': workbook.add_format({
                'num_format': 'dd/mm/yyyy',
                'border': 1
            }),
            'percent': workbook.add_format({
                'num_format': '0.0%',
                'border': 1
            })
        }
    
    def format_main_sheet(self, writer, df, formats):
        """Formatea la hoja principal"""
        worksheet = writer.sheets['Base de Datos']
        
        # Ajustar anchos de columna
        worksheet.set_column('A:A', 30)  # Nombre
        worksheet.set_column('B:B', 15)  # RUT
        worksheet.set_column('C:C', 12)  # N° Boleta
        worksheet.set_column('D:D', 12)  # Fecha
        worksheet.set_column('E:E', 12)  # Monto
        worksheet.set_column('F:F', 15)  # Convenio
        worksheet.set_column('G:G', 8)   # Horas
        worksheet.set_column('H:H', 10)  # Tipo
        worksheet.set_column('I:I', 40)  # Glosa
        worksheet.set_column('J:J', 15)  # Decreto
        
        # Congelar primera fila
        worksheet.freeze_panes(1, 0)
        
        # Agregar autofiltro
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
    
    def generate_convention_reports(self, writer, df, formats):
        """Genera reportes por convenio"""
        convenios = df[df['convenio'] != '']['convenio'].unique()
        
        for convenio in convenios:
            # Filtrar datos
            df_conv = df[df['convenio'] == convenio].copy()
            
            if len(df_conv) == 0:
                continue
            
            # Crear nombre de hoja válido
            sheet_name = f"Conv_{convenio[:20]}"
            sheet_name = re.sub(r'[^\w\s]', '_', sheet_name)
            
            # Crear resumen
            summary = self.create_convention_summary(df_conv)
            
            # Escribir en nueva hoja
            summary.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Formatear
            worksheet = writer.sheets[sheet_name]
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 12)
    
    def create_convention_summary(self, df):
        """Crea un resumen para un convenio"""
        # Agrupar por mes
        summary = df.groupby(['año', 'mes']).agg({
            'nro_boleta': 'count',
            'monto_num': 'sum',
            'rut': 'nunique'
        }).reset_index()
        
        summary.columns = ['Año', 'Mes', 'N° Boletas', 'Total', 'Personas']
        
        # Agregar nombre del mes
        months = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        summary['Mes'] = summary['Mes'].map(months)
        
        return summary