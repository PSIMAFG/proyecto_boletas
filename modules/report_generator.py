# SPDX-License-Identifier: BUSL-1.1
# © 2025 Matías A. Fernández

# modules/report_generator.py
"""
Módulo de generación de informes en Excel con fórmulas dinámicas
"""
import pandas as pd
import xlsxwriter
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config import *
from modules.utils import get_month_year_from_date, format_currency

class ReportGenerator:
    """Generador de informes en Excel con hojas por convenio y resúmenes mensuales"""
    
    def __init__(self):
        self.month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
    
    def create_excel_with_reports(self, registros: List[Dict], output_path: str, generate_reports: bool = True):
        """
        Crea un archivo Excel con los datos y opcionalmente informes por convenio
        
        Args:
            registros: Lista de diccionarios con los datos de las boletas
            output_path: Ruta del archivo Excel de salida
            generate_reports: Si True, genera hojas adicionales con informes por convenio
        """
        # Crear el writer de Excel
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        workbook = writer.book
        
        # Definir formatos
        formats = self._create_formats(workbook)
        
        # Crear DataFrame principal
        df_main = self._create_main_dataframe(registros)
        
        # Escribir hoja principal (Base de Datos)
        df_main.to_excel(writer, sheet_name='Base de Datos', index=False)
        self._format_main_sheet(writer, 'Base de Datos', df_main, formats)
        
        # Si se solicitan informes, generar hojas por convenio
        if generate_reports:
            self._generate_convention_reports(writer, df_main, formats)
        
        # Guardar el archivo
        writer.close()
        
        return df_main
    
    def _create_formats(self, workbook) -> Dict:
        """Crea los formatos para el libro de Excel"""
        return {
            'header': workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center',
                'fg_color': '#D9E2F3',
                'border': 1
            }),
            'currency': workbook.add_format({
                'num_format': '#,##0',
                'align': 'right',
                'border': 1
            }),
            'currency_bold': workbook.add_format({
                'num_format': '#,##0',
                'align': 'right',
                'bold': True,
                'border': 1,
                'fg_color': '#E7E6E6'
            }),
            'date': workbook.add_format({
                'num_format': 'dd/mm/yyyy',
                'align': 'center',
                'border': 1
            }),
            'text': workbook.add_format({
                'text_wrap': True,
                'valign': 'vcenter',
                'border': 1
            }),
            'text_center': workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            }),
            'title': workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center',
                'valign': 'vcenter',
                'fg_color': '#4472C4',
                'font_color': 'white'
            }),
            'subtitle': workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'left',
                'valign': 'vcenter',
                'fg_color': '#D9E2F3'
            }),
            'total': workbook.add_format({
                'bold': True,
                'num_format': '#,##0',
                'align': 'right',
                'border': 1,
                'fg_color': '#FFE699'
            }),
            'percent': workbook.add_format({
                'num_format': '0.0%',
                'align': 'center',
                'border': 1
            })
        }
    
    def _create_main_dataframe(self, registros: List[Dict]) -> pd.DataFrame:
        """Crea el DataFrame principal con todos los datos"""
        cols = [
            "nombre", "rut", "nro_boleta", "fecha_documento", "monto",
            "convenio", "horas", "tipo", "glosa",
            "archivo", "paginas", "confianza", "confianza_max",
            "decreto_alcaldicio"
        ]
        
        df = pd.DataFrame(registros)
        
        # Asegurar que todas las columnas existen
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        
        # Reordenar columnas
        df = df[cols]
        
        # Convertir monto a numérico
        df["monto_num"] = pd.to_numeric(df["monto"], errors="coerce")
        
        # Convertir fecha a datetime
        df["fecha_dt"] = pd.to_datetime(df["fecha_documento"], errors="coerce")
        
        # Agregar columnas de mes y año
        df["mes"] = df["fecha_dt"].dt.month
        df["año"] = df["fecha_dt"].dt.year
        df["mes_nombre"] = df["mes"].map(self.month_names)
        
        return df
    
    def _format_main_sheet(self, writer, sheet_name: str, df: pd.DataFrame, formats: Dict):
        """Aplica formato a la hoja principal"""
        worksheet = writer.sheets[sheet_name]
        
        # Ajustar anchos de columna
        column_widths = {
            'A': 30,  # nombre
            'B': 15,  # rut
            'C': 12,  # nro_boleta
            'D': 12,  # fecha_documento
            'E': 12,  # monto
            'F': 15,  # convenio
            'G': 8,   # horas
            'H': 10,  # tipo
            'I': 40,  # glosa
            'J': 30,  # archivo
            'K': 8,   # paginas
            'L': 10,  # confianza
            'M': 12,  # confianza_max
            'N': 12,  # decreto_alcaldicio
        }
        
        for col, width in column_widths.items():
            worksheet.set_column(f'{col}:{col}', width)
        
        # Aplicar formato a los encabezados
        for col_num, value in enumerate(df.columns[:14]):
            worksheet.write(0, col_num, value, formats['header'])
        
        # Congelar paneles
        worksheet.freeze_panes(1, 0)
        
        # Agregar filtros
        worksheet.autofilter(0, 0, len(df), 13)
    
    def _generate_convention_reports(self, writer, df_main: pd.DataFrame, formats: Dict):
        """Genera hojas de informe por cada convenio"""
        # Obtener convenios únicos (excluyendo vacíos)
        convenios = df_main[df_main['convenio'] != '']['convenio'].unique()
        
        if len(convenios) == 0:
            # Si no hay convenios, crear un informe general
            convenios = ['GENERAL']
        
        for convenio in convenios:
            sheet_name = self._sanitize_sheet_name(f"Informe_{convenio}")
            
            # Filtrar datos del convenio
            if convenio == 'GENERAL':
                df_conv = df_main.copy()
            else:
                df_conv = df_main[df_main['convenio'] == convenio].copy()
            
            if len(df_conv) == 0:
                continue
            
            # Crear la hoja del convenio
            self._create_convention_sheet(writer, sheet_name, convenio, df_conv, df_main, formats)
    
    def _sanitize_sheet_name(self, name: str) -> str:
        """Sanitiza el nombre de la hoja de Excel (máx 31 caracteres)"""
        # Eliminar caracteres no válidos
        invalid_chars = ['\\', '/', '*', '?', ':', '[', ']']
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Limitar a 31 caracteres
        if len(name) > 31:
            name = name[:28] + '...'
        
        return name
    
    def _create_convention_sheet(self, writer, sheet_name: str, convenio: str, 
                                 df_conv: pd.DataFrame, df_main: pd.DataFrame, formats: Dict):
        """Crea una hoja de informe para un convenio específico"""
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)
        
        row = 0
        
        # Título
        worksheet.merge_range(row, 0, row, 7, f"Informe de Convenio: {convenio}", formats['title'])
        row += 2
        
        # Información general
        total_boletas = len(df_conv)
        total_monto = df_conv['monto_num'].sum()
        personas_unicas = df_conv['rut'].nunique()
        
        worksheet.write(row, 0, "Total Boletas:", formats['subtitle'])
        worksheet.write(row, 1, total_boletas, formats['text_center'])
        worksheet.write(row, 2, "Total Monto:", formats['subtitle'])
        worksheet.write(row, 3, total_monto, formats['currency_bold'])
        worksheet.write(row, 4, "Personas Únicas:", formats['subtitle'])
        worksheet.write(row, 5, personas_unicas, formats['text_center'])
        row += 2
        
        # Obtener años únicos
        años = sorted(df_conv['año'].dropna().unique())
        
        for año in años:
            df_año = df_conv[df_conv['año'] == año]
            
            # Título del año
            worksheet.merge_range(row, 0, row, 7, f"Año {int(año)}", formats['subtitle'])
            row += 1
            
            # Obtener meses únicos del año
            meses = sorted(df_año['mes'].dropna().unique())
            
            for mes in meses:
                df_mes = df_año[df_año['mes'] == mes]
                
                if len(df_mes) == 0:
                    continue
                
                # Título del mes
                mes_nombre = self.month_names.get(int(mes), f"Mes {int(mes)}")
                worksheet.write(row, 0, f"{mes_nombre} {int(año)}:", formats['subtitle'])
                row += 1
                
                # Encabezados de la tabla mensual
                headers = ['Nombre', 'RUT', 'N° Boleta', 'Fecha', 'Monto', 'Decreto', 'Horas', 'Glosa']
                for col, header in enumerate(headers):
                    worksheet.write(row, col, header, formats['header'])
                row += 1
                
                # Datos del mes usando fórmulas que referencian la hoja principal
                start_row_data = row
                for idx, (_, registro) in enumerate(df_mes.iterrows()):
                    # Encontrar la fila en la base de datos principal
                    main_row = self._find_row_in_main(df_main, registro)
                    
                    if main_row is not None:
                        # Usar fórmulas para referenciar la hoja principal
                        worksheet.write_formula(row, 0, f"='Base de Datos'!A{main_row+2}", formats['text'])  # Nombre
                        worksheet.write_formula(row, 1, f"='Base de Datos'!B{main_row+2}", formats['text_center'])  # RUT
                        worksheet.write_formula(row, 2, f"='Base de Datos'!C{main_row+2}", formats['text_center'])  # N° Boleta
                        worksheet.write_formula(row, 3, f"='Base de Datos'!D{main_row+2}", formats['date'])  # Fecha
                        worksheet.write_formula(row, 4, f"='Base de Datos'!E{main_row+2}", formats['currency'])  # Monto
                        worksheet.write_formula(row, 5, f"='Base de Datos'!N{main_row+2}", formats['text_center'])  # Decreto
                        worksheet.write_formula(row, 6, f"='Base de Datos'!G{main_row+2}", formats['text_center'])  # Horas
                        worksheet.write_formula(row, 7, f"='Base de Datos'!I{main_row+2}", formats['text'])  # Glosa
                    else:
                        # Si no se encuentra, escribir valores directamente
                        worksheet.write(row, 0, registro['nombre'], formats['text'])
                        worksheet.write(row, 1, registro['rut'], formats['text_center'])
                        worksheet.write(row, 2, registro['nro_boleta'], formats['text_center'])
                        worksheet.write(row, 3, registro['fecha_documento'], formats['text_center'])
                        worksheet.write(row, 4, registro['monto_num'], formats['currency'])
                        worksheet.write(row, 5, registro.get('decreto_alcaldicio', ''), formats['text_center'])
                        worksheet.write(row, 6, registro.get('horas', ''), formats['text_center'])
                        worksheet.write(row, 7, registro.get('glosa', ''), formats['text'])
                    
                    row += 1
                
                # Total del mes con fórmula
                worksheet.write(row, 3, "Total Mes:", formats['subtitle'])
                worksheet.write_formula(row, 4, f"=SUM(E{start_row_data+1}:E{row})", formats['total'])
                row += 2
        
        # Resumen anual al final
        row += 1
        worksheet.merge_range(row, 0, row, 4, "RESUMEN ANUAL", formats['title'])
        row += 1
        
        # Encabezados del resumen
        worksheet.write(row, 0, "Mes", formats['header'])
        worksheet.write(row, 1, "N° Boletas", formats['header'])
        worksheet.write(row, 2, "Total Monto", formats['header'])
        worksheet.write(row, 3, "Promedio", formats['header'])
        worksheet.write(row, 4, "% del Total", formats['header'])
        row += 1
        
        # Datos del resumen por mes
        resumen_rows = []
        for año in años:
            df_año = df_conv[df_conv['año'] == año]
            meses = sorted(df_año['mes'].dropna().unique())
            
            for mes in meses:
                df_mes = df_año[df_año['mes'] == mes]
                mes_nombre = self.month_names.get(int(mes), f"Mes {int(mes)}")
                num_boletas = len(df_mes)
                total_mes = df_mes['monto_num'].sum()
                promedio_mes = df_mes['monto_num'].mean() if num_boletas > 0 else 0
                
                worksheet.write(row, 0, f"{mes_nombre} {int(año)}", formats['text'])
                worksheet.write(row, 1, num_boletas, formats['text_center'])
                worksheet.write(row, 2, total_mes, formats['currency'])
                worksheet.write(row, 3, promedio_mes, formats['currency'])
                
                # Porcentaje con fórmula
                if total_monto > 0:
                    worksheet.write_formula(row, 4, f"=C{row+1}/{total_monto}", formats['percent'])
                else:
                    worksheet.write(row, 4, 0, formats['percent'])
                
                resumen_rows.append(row)
                row += 1
        
        # Total general
        worksheet.write(row, 0, "TOTAL GENERAL", formats['subtitle'])
        worksheet.write_formula(row, 1, f"=SUM(B{resumen_rows[0]+1}:B{row})", formats['total'])
        worksheet.write_formula(row, 2, f"=SUM(C{resumen_rows[0]+1}:C{row})", formats['total'])
        worksheet.write_formula(row, 3, f"=AVERAGE(D{resumen_rows[0]+1}:D{row})", formats['total'])
        worksheet.write(row, 4, "100%", formats['total'])
        
        # Ajustar anchos de columna
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
        worksheet.set_column('F:F', 10)
        worksheet.set_column('G:G', 8)
        worksheet.set_column('H:H', 40)
    
    def _find_row_in_main(self, df_main: pd.DataFrame, registro: pd.Series) -> Optional[int]:
        """
        Encuentra el índice de una fila en el DataFrame principal
        basándose en campos únicos
        """
        # Buscar por combinación de RUT y número de boleta
        mask = (df_main['rut'] == registro['rut']) & \
               (df_main['nro_boleta'] == registro['nro_boleta'])
        
        matches = df_main[mask]
        
        if len(matches) == 1:
            return matches.index[0]
        elif len(matches) > 1:
            # Si hay múltiples coincidencias, usar también la fecha
            mask = mask & (df_main['fecha_documento'] == registro['fecha_documento'])
            matches = df_main[mask]
            if len(matches) > 0:
                return matches.index[0]
        
        return None
    
    def generate_summary_report(self, df: pd.DataFrame, output_path: str):
        """
        Genera un informe resumido en un archivo Excel separado
        """
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        workbook = writer.book
        formats = self._create_formats(workbook)
        
        # Hoja de resumen general
        worksheet = workbook.add_worksheet('Resumen General')
        
        row = 0
        
        # Título
        worksheet.merge_range(row, 0, row, 5, "RESUMEN GENERAL DE BOLETAS DE HONORARIOS", formats['title'])
        row += 2
        
        # Estadísticas generales
        total_registros = len(df)
        total_monto = df['monto_num'].sum()
        personas_unicas = df['rut'].nunique()
        convenios_unicos = df[df['convenio'] != '']['convenio'].nunique()
        
        stats = [
            ("Total de Boletas:", total_registros),
            ("Monto Total:", f"${total_monto:,.0f}"),
            ("Personas Únicas:", personas_unicas),
            ("Convenios Identificados:", convenios_unicos),
            ("Promedio por Boleta:", f"${df['monto_num'].mean():,.0f}" if total_registros > 0 else "$0"),
            ("Mediana por Boleta:", f"${df['monto_num'].median():,.0f}" if total_registros > 0 else "$0")
        ]
        
        for label, value in stats:
            worksheet.write(row, 0, label, formats['subtitle'])
            worksheet.write(row, 1, value, formats['text'])
            row += 1
        
        row += 1
        
        # Resumen por convenio
        worksheet.merge_range(row, 0, row, 3, "RESUMEN POR CONVENIO", formats['subtitle'])
        row += 1
        
        headers = ['Convenio', 'N° Boletas', 'Monto Total', '% del Total']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, formats['header'])
        row += 1
        
        # Agrupar por convenio
        convenio_summary = df.groupby('convenio').agg({
            'nro_boleta': 'count',
            'monto_num': 'sum'
        }).reset_index()
        
        convenio_summary.columns = ['Convenio', 'Num_Boletas', 'Monto_Total']
        convenio_summary['Porcentaje'] = convenio_summary['Monto_Total'] / total_monto * 100
        convenio_summary = convenio_summary.sort_values('Monto_Total', ascending=False)
        
        for _, conv_row in convenio_summary.iterrows():
            convenio_name = conv_row['Convenio'] if conv_row['Convenio'] else '(Sin Convenio)'
            worksheet.write(row, 0, convenio_name, formats['text'])
            worksheet.write(row, 1, conv_row['Num_Boletas'], formats['text_center'])
            worksheet.write(row, 2, conv_row['Monto_Total'], formats['currency'])
            worksheet.write(row, 3, f"{conv_row['Porcentaje']:.1f}%", formats['text_center'])
            row += 1
        
        # Ajustar anchos de columna
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 12)
        
        writer.close()

