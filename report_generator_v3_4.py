# modules/report_generator.py (v3.4 - Con reportes por profesional)
"""
Módulo de generación de informes en Excel con fórmulas dinámicas
Versión 3.4 - Incluye reportes por profesional (una hoja por persona)
"""
import pandas as pd
import unicodedata
import xlsxwriter
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import sys
import re

sys.path.append(str(Path(__file__).parent.parent))

from config import *
from modules.utils import get_month_year_from_date, format_currency


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas a ASCII:
    - Minúsculas
    - Espacios -> _
    - Elimina tildes/ñ -> n
    """
    new_cols = []
    for c in df.columns:
        s = str(c).strip().lower().replace(" ", "_")
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        new_cols.append(s)
    out = df.copy()
    out.columns = new_cols
    return out


class ReportGenerator:
    """Generador de informes en Excel con hojas por convenio Y por profesional"""

    def __init__(self):
        self.month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }

    def create_excel_with_reports(self, registros: List[Dict], output_path: str, 
                                 generate_reports: bool = True, 
                                 generate_professional_reports: bool = True):
        """
        Crea un archivo Excel con los datos y opcionalmente informes por convenio y por profesional

        Args:
            registros: Lista de diccionarios con los datos de las boletas
            output_path: Ruta del archivo Excel de salida
            generate_reports: Si True, genera hojas adicionales con informes por convenio
            generate_professional_reports: Si True, genera hojas por profesional (NUEVO)
        """
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        workbook = writer.book

        formats = self._create_formats(workbook)

        # Crear DataFrame principal
        df_main = self._create_main_dataframe(registros)

        # Escribir hoja principal (Base de Datos)
        df_main.to_excel(writer, sheet_name='Base de Datos', index=False)
        self._format_main_sheet(writer, 'Base de Datos', df_main, formats)

        # Hojas por convenio
        if generate_reports:
            self._generate_convention_reports(writer, df_main, formats)

        # NUEVO: Hojas por profesional
        if generate_professional_reports:
            self._generate_professional_reports(writer, df_main, formats)

        # Hoja de resumen general
        self._generate_summary_sheet(writer, df_main, formats)

        writer.close()
        return df_main

    def _create_formats(self, workbook) -> Dict:
        """Crea los formatos para el libro de Excel"""
        return {
            'header': workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
                'fg_color': '#D9E2F3', 'border': 1
            }),
            'currency': workbook.add_format({'num_format': '#,##0', 'align': 'right', 'border': 1}),
            'currency_bold': workbook.add_format({
                'num_format': '#,##0', 'align': 'right', 'bold': True, 'border': 1, 'fg_color': '#E7E6E6'
            }),
            'date': workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'center', 'border': 1}),
            'text': workbook.add_format({'text_wrap': True, 'valign': 'vcenter', 'border': 1}),
            'text_center': workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1}),
            'title': workbook.add_format({
                'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
                'fg_color': '#4472C4', 'font_color': 'white'
            }),
            'subtitle': workbook.add_format({
                'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter', 'fg_color': '#D9E2F3'
            }),
            'total': workbook.add_format({
                'bold': True, 'num_format': '#,##0', 'align': 'right', 'border': 1, 'fg_color': '#FFE699'
            }),
            'percent': workbook.add_format({'num_format': '0.0%', 'align': 'center', 'border': 1}),
            'professional_header': workbook.add_format({
                'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter',
                'fg_color': '#70AD47', 'font_color': 'white'
            })
        }

    def _create_main_dataframe(self, registros: List[Dict]) -> pd.DataFrame:
        """Crea el DataFrame principal con todos los datos, priorizando el período de servicio."""
        cols = [
            "nombre", "rut", "nro_boleta", "fecha_documento", "periodo_servicio",
            "monto", "convenio", "horas", "tipo", "glosa",
            "archivo", "paginas", "confianza", "confianza_max", "decreto_alcaldicio",
            "mes", "anio", "mes_nombre"  # Incluir mes_nombre
        ]

        df = pd.DataFrame(registros)

        # Asegurar columnas base
        for c in cols:
            if c not in df.columns:
                if c == 'mes_nombre':
                    df[c] = 'Sin Periodo'  # Valor por defecto NUNCA vacío
                else:
                    df[c] = ""
        df = df[cols]

        # Normalizar nombres de columnas
        df = _normalize_cols(df)

        # monto numérico
        df["monto_num"] = pd.to_numeric(df.get("monto", ""), errors="coerce")

        # fecha de documento
        df["fecha_dt"] = pd.to_datetime(df.get("fecha_documento", ""), errors="coerce", dayfirst=False)

        # Si faltan mes/año/mes_nombre, intentar calcularlos
        for idx, row in df.iterrows():
            if pd.isna(row.get('mes')) or pd.isna(row.get('anio')) or row.get('mes_nombre') == 'Sin Periodo':
                # Intentar desde periodo_servicio
                periodo = row.get('periodo_servicio', '')
                if periodo and not periodo.startswith('XXXX'):
                    try:
                        year = int(periodo[:4])
                        month = int(periodo[5:7])
                        df.at[idx, 'mes'] = month
                        df.at[idx, 'anio'] = year
                        df.at[idx, 'mes_nombre'] = self.month_names.get(month, f'Mes {month}')
                    except:
                        pass
                
                # Si no, intentar desde fecha_documento (mes anterior)
                if df.at[idx, 'mes_nombre'] == 'Sin Periodo' and pd.notna(row['fecha_dt']):
                    fecha = row['fecha_dt']
                    if fecha.month == 1:
                        df.at[idx, 'mes'] = 12
                        df.at[idx, 'anio'] = fecha.year - 1
                    else:
                        df.at[idx, 'mes'] = fecha.month - 1
                        df.at[idx, 'anio'] = fecha.year
                    df.at[idx, 'mes_nombre'] = self.month_names.get(df.at[idx, 'mes'], 'Sin Periodo')

        return df

    def _format_main_sheet(self, writer, sheet_name: str, df: pd.DataFrame, formats: Dict):
        """Aplica formato a la hoja principal"""
        worksheet = writer.sheets[sheet_name]

        column_widths = {
            'A': 30, 'B': 15, 'C': 12, 'D': 12, 'E': 15, 'F': 12, 'G': 15, 'H': 8,
            'I': 10, 'J': 40, 'K': 30, 'L': 8, 'M': 10, 'N': 12, 'O': 12, 'P': 8,
            'Q': 8, 'R': 15
        }
        for col, width in column_widths.items():
            worksheet.set_column(f'{col}:{col}', width)

        # Encabezados
        for col_num, value in enumerate(df.columns[:18]):
            worksheet.write(0, col_num, value, formats['header'])

        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(df), min(17, len(df.columns)-1))

    def _generate_professional_reports(self, writer, df_main: pd.DataFrame, formats: Dict):
        """NUEVO: Genera hojas de informe por cada profesional"""
        # Agrupar por RUT (identificador único de profesional)
        profesionales = df_main[df_main['rut'] != ''].groupby('rut').first()[['nombre']].reset_index()
        
        print(f"\nGenerando reportes para {len(profesionales)} profesionales...")
        
        for _, prof in profesionales.iterrows():
            rut = prof['rut']
            nombre = prof['nombre'] if prof['nombre'] else f"RUT_{rut}"
            
            # Obtener todas las boletas de este profesional
            df_prof = df_main[df_main['rut'] == rut].copy()
            
            if len(df_prof) == 0:
                continue
            
            # Crear nombre de hoja (máx 31 caracteres, sin caracteres especiales)
            sheet_name = self._create_professional_sheet_name(nombre)
            
            # Crear la hoja
            self._create_professional_sheet(writer, sheet_name, nombre, rut, df_prof, formats)

    def _create_professional_sheet_name(self, nombre: str) -> str:
        """Crea un nombre válido de hoja para un profesional"""
        # Tomar solo el primer nombre y primer apellido
        partes = nombre.split()
        if len(partes) >= 2:
            nombre_corto = f"{partes[0]} {partes[1]}"
        else:
            nombre_corto = nombre
        
        # Limpiar caracteres especiales
        nombre_limpio = re.sub(r'[^\w\s]', '', nombre_corto)
        nombre_limpio = nombre_limpio.replace(' ', '_')
        
        # Limitar a 31 caracteres
        if len(nombre_limpio) > 31:
            nombre_limpio = nombre_limpio[:28] + '...'
        
        return nombre_limpio

    def _create_professional_sheet(self, writer, sheet_name: str, nombre: str, rut: str,
                                  df_prof: pd.DataFrame, formats: Dict):
        """Crea una hoja de informe para un profesional específico"""
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)
        
        row = 0
        
        # Encabezado principal
        worksheet.merge_range(row, 0, row, 7, f"INFORME DE BOLETAS - {nombre.upper()}", 
                            formats['professional_header'])
        row += 1
        worksheet.merge_range(row, 0, row, 7, f"RUT: {rut}", formats['subtitle'])
        row += 2
        
        # Resumen general
        total_boletas = len(df_prof)
        total_monto = df_prof['monto_num'].sum()
        convenios_trabajados = df_prof['convenio'].nunique()
        meses_trabajados = df_prof[df_prof['mes_nombre'] != 'Sin Periodo']['mes_nombre'].nunique()
        
        # Información resumen
        worksheet.write(row, 0, "RESUMEN GENERAL", formats['subtitle'])
        row += 1
        worksheet.write(row, 0, "Total de Boletas:", formats['text'])
        worksheet.write(row, 1, total_boletas, formats['text_center'])
        worksheet.write(row, 2, "Monto Total:", formats['text'])
        worksheet.write(row, 3, total_monto, formats['currency_bold'])
        row += 1
        worksheet.write(row, 0, "Convenios:", formats['text'])
        worksheet.write(row, 1, convenios_trabajados, formats['text_center'])
        worksheet.write(row, 2, "Meses Trabajados:", formats['text'])
        worksheet.write(row, 3, meses_trabajados, formats['text_center'])
        row += 2
        
        # Detalle por mes
        worksheet.merge_range(row, 0, row, 7, "DETALLE POR MES", formats['subtitle'])
        row += 1
        
        # Agrupar por año y mes
        df_prof_sorted = df_prof.sort_values(['anio', 'mes'])
        
        for (anio, mes), grupo in df_prof_sorted.groupby(['anio', 'mes']):
            if pd.isna(anio) or pd.isna(mes) or anio == 0:
                continue
            
            mes_nombre = self.month_names.get(int(mes), f"Mes {int(mes)}")
            
            # Título del mes
            worksheet.write(row, 0, f"{mes_nombre} {int(anio)}:", formats['subtitle'])
            row += 1
            
            # Encabezados de tabla
            headers = ['N° Boleta', 'Fecha', 'Convenio', 'Monto', 'Horas', 'Tipo', 'Decreto']
            for col, header in enumerate(headers):
                worksheet.write(row, col, header, formats['header'])
            row += 1
            
            # Datos del mes
            subtotal_mes = 0
            for _, boleta in grupo.iterrows():
                worksheet.write(row, 0, boleta.get('nro_boleta', ''), formats['text_center'])
                worksheet.write(row, 1, boleta.get('fecha_documento', ''), formats['text_center'])
                worksheet.write(row, 2, boleta.get('convenio', ''), formats['text_center'])
                worksheet.write(row, 3, boleta.get('monto_num', 0), formats['currency'])
                worksheet.write(row, 4, boleta.get('horas', ''), formats['text_center'])
                worksheet.write(row, 5, boleta.get('tipo', ''), formats['text_center'])
                worksheet.write(row, 6, boleta.get('decreto_alcaldicio', ''), formats['text_center'])
                subtotal_mes += boleta.get('monto_num', 0)
                row += 1
            
            # Subtotal del mes
            worksheet.write(row, 2, "Subtotal Mes:", formats['subtitle'])
            worksheet.write(row, 3, subtotal_mes, formats['total'])
            row += 2
        
        # Resumen por convenio
        row += 1
        worksheet.merge_range(row, 0, row, 4, "RESUMEN POR CONVENIO", formats['subtitle'])
        row += 1
        
        headers_conv = ['Convenio', 'N° Boletas', 'Monto Total', 'Promedio', '% del Total']
        for col, header in enumerate(headers_conv):
            worksheet.write(row, col, header, formats['header'])
        row += 1
        
        # Agrupar por convenio
        for convenio, grupo_conv in df_prof.groupby('convenio'):
            if not convenio:
                convenio = '(Sin Convenio)'
            
            num_boletas = len(grupo_conv)
            monto_conv = grupo_conv['monto_num'].sum()
            promedio = grupo_conv['monto_num'].mean()
            porcentaje = (monto_conv / total_monto * 100) if total_monto > 0 else 0
            
            worksheet.write(row, 0, convenio, formats['text'])
            worksheet.write(row, 1, num_boletas, formats['text_center'])
            worksheet.write(row, 2, monto_conv, formats['currency'])
            worksheet.write(row, 3, promedio, formats['currency'])
            worksheet.write(row, 4, f"{porcentaje:.1f}%", formats['text_center'])
            row += 1
        
        # Total final
        row += 1
        worksheet.write(row, 0, "TOTAL GENERAL", formats['subtitle'])
        worksheet.write(row, 1, total_boletas, formats['total'])
        worksheet.write(row, 2, total_monto, formats['total'])
        
        # Configurar anchos de columna
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 8)
        worksheet.set_column('F:F', 10)
        worksheet.set_column('G:G', 10)
        worksheet.set_column('H:H', 10)

    def _generate_convention_reports(self, writer, df_main: pd.DataFrame, formats: Dict):
        """Genera hojas de informe por cada convenio"""
        convenios = df_main[df_main['convenio'] != '']['convenio'].unique()
        if len(convenios) == 0:
            convenios = ['GENERAL']

        for convenio in convenios:
            sheet_name = self._sanitize_sheet_name(f"Conv_{convenio}")
            df_conv = df_main.copy() if convenio == 'GENERAL' else df_main[df_main['convenio'] == convenio].copy()
            if len(df_conv) == 0:
                continue
            self._create_convention_sheet(writer, sheet_name, convenio, df_conv, df_main, formats)

    def _generate_summary_sheet(self, writer, df_main: pd.DataFrame, formats: Dict):
        """Genera una hoja de resumen general"""
        workbook = writer.book
        worksheet = workbook.add_worksheet('Resumen General')
        
        row = 0
        
        # Título
        worksheet.merge_range(row, 0, row, 5, "RESUMEN GENERAL DE BOLETAS", formats['title'])
        row += 2
        
        # Estadísticas generales
        total_registros = len(df_main)
        total_monto = df_main['monto_num'].sum()
        personas_unicas = df_main['rut'].nunique()
        convenios_unicos = df_main[df_main['convenio'] != '']['convenio'].nunique()
        
        stats = [
            ("Total de Boletas:", total_registros),
            ("Monto Total:", f"${total_monto:,.0f}"),
            ("Personas Unicas:", personas_unicas),
            ("Convenios Identificados:", convenios_unicos),
            ("Promedio por Boleta:", f"${df_main['monto_num'].mean():,.0f}" if total_registros > 0 else "$0"),
            ("Mediana por Boleta:", f"${df_main['monto_num'].median():,.0f}" if total_registros > 0 else "$0")
        ]
        
        for label, value in stats:
            worksheet.write(row, 0, label, formats['subtitle'])
            worksheet.write(row, 1, value, formats['text'])
            row += 1
        
        row += 2
        
        # Top 10 profesionales por monto
        worksheet.merge_range(row, 0, row, 3, "TOP 10 PROFESIONALES POR MONTO", formats['subtitle'])
        row += 1
        
        headers_top = ['Nombre', 'RUT', 'Total Boletas', 'Monto Total']
        for col, header in enumerate(headers_top):
            worksheet.write(row, col, header, formats['header'])
        row += 1
        
        # Agrupar por RUT y obtener top 10
        top_profesionales = df_main.groupby(['rut', 'nombre']).agg({
            'nro_boleta': 'count',
            'monto_num': 'sum'
        }).reset_index()
        top_profesionales.columns = ['RUT', 'Nombre', 'Num_Boletas', 'Monto_Total']
        top_profesionales = top_profesionales.sort_values('Monto_Total', ascending=False).head(10)
        
        for _, prof in top_profesionales.iterrows():
            worksheet.write(row, 0, prof['Nombre'], formats['text'])
            worksheet.write(row, 1, prof['RUT'], formats['text_center'])
            worksheet.write(row, 2, int(prof['Num_Boletas']), formats['text_center'])
            worksheet.write(row, 3, float(prof['Monto_Total']), formats['currency'])
            row += 1
        
        # Configurar anchos
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)

    def _sanitize_sheet_name(self, name: str) -> str:
        """Sanitiza el nombre de la hoja de Excel (máx 31 caracteres)"""
        for ch in ['\\', '/', '*', '?', ':', '[', ']']:
            name = name.replace(ch, '_')
        return name if len(name) <= 31 else (name[:28] + '...')

    def _create_convention_sheet(self, writer, sheet_name: str, convenio: str,
                                 df_conv: pd.DataFrame, df_main: pd.DataFrame, formats: Dict):
        """Crea una hoja de informe para un convenio específico"""
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)

        row = 0

        # Título
        worksheet.merge_range(row, 0, row, 7, f"Informe de Convenio: {convenio}", formats['title'])
        row += 2

        # Info general
        total_boletas = len(df_conv)
        total_monto = df_conv['monto_num'].sum()
        personas_unicas = df_conv['rut'].nunique()

        worksheet.write(row, 0, "Total Boletas:", formats['subtitle'])
        worksheet.write(row, 1, total_boletas, formats['text_center'])
        worksheet.write(row, 2, "Total Monto:", formats['subtitle'])
        worksheet.write(row, 3, total_monto, formats['currency_bold'])
        worksheet.write(row, 4, "Personas Unicas:", formats['subtitle'])
        worksheet.write(row, 5, personas_unicas, formats['text_center'])
        row += 2

        # Detalle mensual
        self._add_monthly_detail(worksheet, df_conv, formats, row)

    def _add_monthly_detail(self, worksheet, df_conv: pd.DataFrame, formats: Dict, start_row: int):
        """Agrega detalle mensual a una hoja"""
        row = start_row
        
        # Agrupar por año y mes
        df_sorted = df_conv.sort_values(['anio', 'mes'])
        
        for (anio, mes), grupo in df_sorted.groupby(['anio', 'mes']):
            if pd.isna(anio) or pd.isna(mes) or anio == 0:
                continue
            
            mes_nombre = self.month_names.get(int(mes), f"Mes {int(mes)}")
            
            # Título del mes
            worksheet.merge_range(row, 0, row, 7, f"{mes_nombre} {int(anio)}", formats['subtitle'])
            row += 1
            
            # Encabezados
            headers = ['Nombre', 'RUT', 'N° Boleta', 'Fecha', 'Monto', 'Decreto', 'Horas', 'Tipo']
            for col, header in enumerate(headers):
                worksheet.write(row, col, header, formats['header'])
            row += 1
            
            # Datos
            subtotal = 0
            for _, registro in grupo.iterrows():
                worksheet.write(row, 0, registro.get('nombre', ''), formats['text'])
                worksheet.write(row, 1, registro.get('rut', ''), formats['text_center'])
                worksheet.write(row, 2, registro.get('nro_boleta', ''), formats['text_center'])
                worksheet.write(row, 3, registro.get('fecha_documento', ''), formats['text_center'])
                worksheet.write(row, 4, registro.get('monto_num', 0), formats['currency'])
                worksheet.write(row, 5, registro.get('decreto_alcaldicio', ''), formats['text_center'])
                worksheet.write(row, 6, registro.get('horas', ''), formats['text_center'])
                worksheet.write(row, 7, registro.get('tipo', ''), formats['text_center'])
                subtotal += registro.get('monto_num', 0)
                row += 1
            
            # Subtotal
            worksheet.write(row, 3, "Subtotal Mes:", formats['subtitle'])
            worksheet.write(row, 4, subtotal, formats['total'])
            row += 2
        
        # Configurar anchos
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 10)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
        worksheet.set_column('F:F', 10)
        worksheet.set_column('G:G', 8)
        worksheet.set_column('H:H', 10)

    def _find_row_in_main(self, df_main: pd.DataFrame, registro: pd.Series) -> Optional[int]:
        """Encuentra el índice de una fila en el DataFrame principal"""
        mask = (df_main['rut'] == registro.get('rut')) & (df_main['nro_boleta'] == registro.get('nro_boleta'))
        matches = df_main[mask]

        if len(matches) == 1:
            return matches.index[0]
        elif len(matches) > 1:
            mask = mask & (df_main['fecha_documento'] == registro.get('fecha_documento'))
            matches = df_main[mask]
            if len(matches) > 0:
                return matches.index[0]
        return None
