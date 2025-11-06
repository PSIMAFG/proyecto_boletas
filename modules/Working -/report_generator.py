# -*- coding: utf-8 -*-
# modules/report_generator.py
"""
Módulo de generación de informes en Excel con fórmulas dinámicas
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
            'percent': workbook.add_format({'num_format': '0.0%', 'align': 'center', 'border': 1})
        }

    def _create_main_dataframe(self, registros: List[Dict]) -> pd.DataFrame:
        """Crea el DataFrame principal con todos los datos, priorizando el período de servicio."""
        cols = [
            "nombre", "rut", "nro_boleta", "fecha_documento", "periodo_servicio",
            "monto", "convenio", "horas", "tipo", "glosa",
            "archivo", "paginas", "confianza", "confianza_max", "decreto_alcaldicio"
        ]

        df = pd.DataFrame(registros)

        # Asegurar columnas base
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        df = df[cols]

        # Normalizar nombres de columnas (por si vienen con tildes/ñ desde la extracción)
        df = _normalize_cols(df)

        # monto numérico
        df["monto_num"] = pd.to_numeric(df.get("monto", ""), errors="coerce")

        # fecha de documento (pago/emisión)
        df["fecha_dt"] = pd.to_datetime(df.get("fecha_documento", ""), errors="coerce", dayfirst=False)

        # ---------------- Fallback de periodo de servicio ----------------
        ps_col = df.get("periodo_servicio", pd.Series([""] * len(df))).fillna("").astype(str)

        # Completar 'periodo_servicio' vacío a partir de la glosa (p. ej. "SERVICIO MES DE MARZO 2025")
        meses_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        meses_regex = r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)'

        def _infer_ps_from_glosa(glosa, fecha_doc):
            if not isinstance(glosa, str) or not glosa:
                return ""
            m = re.search(rf'\b{meses_regex}\b(?:\s+de\s+(\d{{4}}))?', glosa, re.IGNORECASE)
            if not m:
                return ""
            mes_nombre = m.group(1).lower()
            mes_nombre = 'septiembre' if mes_nombre == 'setiembre' else mes_nombre
            mes = meses_map.get(mes_nombre)
            if not mes:
                return ""
            # Año explícito en glosa
            if m.group(2):
                try:
                    y = int(m.group(2))
                    if 2000 <= y <= 2035:
                        return f"{y:04d}-{mes:02d}"
                except Exception:
                    return ""
            # Inferir año desde fecha_doc
            if pd.notna(fecha_doc):
                y_doc = int(fecha_doc.year)
                m_doc = int(fecha_doc.month)
                y = y_doc - 1 if mes > m_doc else y_doc
                return f"{y:04d}-{mes:02d}"
            return ""

        if ps_col.eq("").any():
            ps_filled = []
            for gl, fdoc, ps in zip(df.get("glosa", ""), df["fecha_dt"], ps_col):
                ps_filled.append(ps if ps else _infer_ps_from_glosa(gl, fdoc))
            ps_col = pd.Series(ps_filled, index=df.index)

        # Convertir a datetime (primer día del mes del servicio)
        def _ps_to_dt(s):
            if not isinstance(s, str) or len(s) < 7 or s.startswith("XXXX"):
                return pd.NaT
            try:
                return pd.to_datetime(s + "-01", format="%Y-%m-%d", errors="coerce")
            except Exception:
                return pd.NaT

        df["periodo_dt"] = ps_col.apply(_ps_to_dt)

        # Elegir fuente para mes/año: preferir periodo_dt; si NaT, usar fecha_dt
        df["periodo_final"] = df["periodo_dt"].combine_first(df["fecha_dt"])

        df["mes"] = df["periodo_final"].dt.month
        df["anio"] = df["periodo_final"].dt.year
        df["mes_nombre"] = df["mes"].map(self.month_names)

        return df

    def _format_main_sheet(self, writer, sheet_name: str, df: pd.DataFrame, formats: Dict):
        """Aplica formato a la hoja principal"""
        worksheet = writer.sheets[sheet_name]

        column_widths = {
            'A': 30, 'B': 15, 'C': 12, 'D': 12, 'E': 15, 'F': 12, 'G': 15, 'H': 8,
            'I': 10, 'J': 40, 'K': 30, 'L': 8, 'M': 10, 'N': 12, 'O': 12,
        }
        for col, width in column_widths.items():
            worksheet.set_column(f'{col}:{col}', width)

        # Encabezados (ya están escritos por pandas; aquí los re-formateamos)
        for col_num, value in enumerate(df.columns[:15]):
            worksheet.write(0, col_num, value, formats['header'])

        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(df), 14)

    def _generate_convention_reports(self, writer, df_main: pd.DataFrame, formats: Dict):
        """Genera hojas de informe por cada convenio"""
        convenios = df_main[df_main['convenio'] != '']['convenio'].unique()
        if len(convenios) == 0:
            convenios = ['GENERAL']

        for convenio in convenios:
            sheet_name = self._sanitize_sheet_name(f"Informe_{convenio}")
            df_conv = df_main.copy() if convenio == 'GENERAL' else df_main[df_main['convenio'] == convenio].copy()
            if len(df_conv) == 0:
                continue
            self._create_convention_sheet(writer, sheet_name, convenio, df_conv, df_main, formats)

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
        worksheet.write(row, 4, "Personas Únicas:", formats['subtitle'])
        worksheet.write(row, 5, personas_unicas, formats['text_center'])
        row += 2

        # Años únicos
        anios = sorted(df_conv['anio'].dropna().unique())

        for anio in anios:
            df_anio = df_conv[df_conv['anio'] == anio]

            # Subtítulo año
            worksheet.merge_range(row, 0, row, 7, f"Año {int(anio)}", formats['subtitle'])
            row += 1

            # Meses del año
            meses = sorted(df_anio['mes'].dropna().unique())

            for mes in meses:
                df_mes = df_anio[df_anio['mes'] == mes]
                if len(df_mes) == 0:
                    continue

                # Título del mes
                mes_nombre = self.month_names.get(int(mes), f"Mes {int(mes)}")
                worksheet.write(row, 0, f"{mes_nombre} {int(anio)}:", formats['subtitle'])
                row += 1

                # Encabezados de la tabla mensual
                headers = ['Nombre', 'RUT', 'N° Boleta', 'Fecha', 'Monto', 'Decreto', 'Horas', 'Glosa']
                for col, header in enumerate(headers):
                    worksheet.write(row, col, header, formats['header'])
                row += 1

                # Filas del mes (con fórmulas referenciadas a la hoja principal)
                start_row_data = row
                for _, registro in df_mes.iterrows():
                    main_row = self._find_row_in_main(df_main, registro)
                    if main_row is not None:
                        worksheet.write_formula(row, 0, f"='Base de Datos'!A{main_row+2}", formats['text'])
                        worksheet.write_formula(row, 1, f"='Base de Datos'!B{main_row+2}", formats['text_center'])
                        worksheet.write_formula(row, 2, f"='Base de Datos'!C{main_row+2}", formats['text_center'])
                        worksheet.write_formula(row, 3, f"='Base de Datos'!D{main_row+2}", formats['date'])
                        worksheet.write_formula(row, 4, f"='Base de Datos'!F{main_row+2}", formats['currency'])
                        worksheet.write_formula(row, 5, f"='Base de Datos'!O{main_row+2}", formats['text_center'])
                        worksheet.write_formula(row, 6, f"='Base de Datos'!H{main_row+2}", formats['text_center'])
                        worksheet.write_formula(row, 7, f"='Base de Datos'!J{main_row+2}", formats['text'])
                    else:
                        worksheet.write(row, 0, registro.get('nombre', ''), formats['text'])
                        worksheet.write(row, 1, registro.get('rut', ''), formats['text_center'])
                        worksheet.write(row, 2, registro.get('nro_boleta', ''), formats['text_center'])
                        worksheet.write(row, 3, registro.get('fecha_documento', ''), formats['text_center'])
                        worksheet.write(row, 4, registro.get('monto_num', 0), formats['currency'])
                        worksheet.write(row, 5, registro.get('decreto_alcaldicio', ''), formats['text_center'])
                        worksheet.write(row, 6, registro.get('horas', ''), formats['text_center'])
                        worksheet.write(row, 7, registro.get('glosa', ''), formats['text'])

                    row += 1

                # Total del mes
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
        for anio in anios:
            df_anio = df_conv[df_conv['anio'] == anio]
            meses = sorted(df_anio['mes'].dropna().unique())

            for mes in meses:
                df_mes = df_anio[df_anio['mes'] == mes]
                mes_nombre = self.month_names.get(int(mes), f"Mes {int(mes)}")
                num_boletas = len(df_mes)
                total_mes = df_mes['monto_num'].sum()
                promedio_mes = df_mes['monto_num'].mean() if num_boletas > 0 else 0

                worksheet.write(row, 0, f"{mes_nombre} {int(anio)}", formats['text'])
                worksheet.write(row, 1, num_boletas, formats['text_center'])
                worksheet.write(row, 2, total_mes, formats['currency'])
                worksheet.write(row, 3, promedio_mes, formats['currency'])

                if total_monto > 0:
                    worksheet.write_formula(row, 4, f"=C{row+1}/{total_monto}", formats['percent'])
                else:
                    worksheet.write(row, 4, 0, formats['percent'])

                resumen_rows.append(row)
                row += 1

        # Total general
        if resumen_rows:
            worksheet.write(row, 0, "TOTAL GENERAL", formats['subtitle'])
            worksheet.write_formula(row, 1, f"=SUM(B{resumen_rows[0]+1}:B{row})", formats['total'])
            worksheet.write_formula(row, 2, f"=SUM(C{resumen_rows[0]+1}:C{row})", formats['total'])
            worksheet.write_formula(row, 3, f"=AVERAGE(D{resumen_rows[0]+1}:D{row})", formats['total'])
            worksheet.write(row, 4, "100%", formats['total'])

        # Anchos de columna
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
        Encuentra el índice de una fila en el DataFrame principal basándose en campos únicos
        """
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

    def generate_summary_report(self, df: pd.DataFrame, output_path: str):
        """
        Genera un informe resumido en un archivo Excel separado
        """
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        workbook = writer.book
        formats = self._create_formats(workbook)

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
        convenio_summary['Porcentaje'] = (convenio_summary['Monto_Total'] / total_monto * 100) if total_monto > 0 else 0
        convenio_summary = convenio_summary.sort_values('Monto_Total', ascending=False)

        for _, conv_row in convenio_summary.iterrows():
            convenio_name = conv_row['Convenio'] if conv_row['Convenio'] else '(Sin Convenio)'
            worksheet.write(row, 0, convenio_name, formats['text'])
            worksheet.write(row, 1, int(conv_row['Num_Boletas']), formats['text_center'])
            worksheet.write(row, 2, float(conv_row['Monto_Total']), formats['currency'])
            pct = float(conv_row['Porcentaje']) if total_monto > 0 else 0.0
            worksheet.write(row, 3, f"{pct:.1f}%", formats['text_center'])
            row += 1

        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 12)

        writer.close()
