from pathlib import Path
import pandas as pd
import xml.etree.ElementTree as ET
from openpyxl.utils import get_column_letter
from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.colors import ColorChoice
from openpyxl.drawing.fill import PatternFillProperties


# ============================================================
# LECTURA Y PARSEO DE XMLS SRI
# ============================================================

def _leer_xml(xml_path: Path) -> dict:
    """
    Lee un archivo XML del SRI y extrae campos clave.
    Devuelve un diccionario con la información del comprobante.
    """
    d = {"archivo": xml_path.name}
    try:
        root = ET.parse(xml_path).getroot()

        d["fecha"] = root.findtext(".//fechaEmision", default="").strip()
        d["rucEmisor"] = root.findtext(".//ruc", default="").strip()
        d["razonSocial"] = root.findtext(".//razonSocial", default="").strip()

        def _num(val):
            try:
                return float(val) if val else 0.0
            except ValueError:
                return 0.0

        d["subtotal"] = _num(root.findtext(".//totalSinImpuestos", default="0"))
        d["iva"] = _num(root.findtext(".//iva", default="0"))
        d["total"] = _num(root.findtext(".//importeTotal", default="0"))

    except Exception as e:
        d["error"] = f"Error leyendo {xml_path.name}: {e}"
    return d


# ============================================================
# CONSTRUCCIÓN DEL REPORTE EN EXCEL
# ============================================================

def construir_reporte(carpeta_mes: Path, excel_salida: Path):
    """
    Genera un Excel con detalle, totales por emisor y errores (si los hay),
    incluyendo gráfico de barras con estilo corporativo SRI.
    """
    rows = []
    for xml in carpeta_mes.rglob("*.xml"):
        rows.append(_leer_xml(xml))

    if not rows:
        print("⚠️ No se encontraron archivos XML en la carpeta.")
        return

    df = pd.DataFrame(rows)
    errores = df[df["error"].notna()] if "error" in df.columns else pd.DataFrame()

    piv = (
        df.groupby(["rucEmisor", "razonSocial"], dropna=False)[["subtotal", "iva", "total"]]
        .sum()
        .reset_index()
    )

    with pd.ExcelWriter(excel_salida, engine="openpyxl") as xls:
        df.to_excel(xls, index=False, sheet_name="Detalle")
        piv.to_excel(xls, index=False, sheet_name="Totales por Emisor")
        if not errores.empty:
            errores.to_excel(xls, index=False, sheet_name="Errores")

    _ajustar_columnas_excel(excel_salida)
    _insertar_grafico_corporativo(excel_salida)
    print(f"✅ Reporte generado: {excel_salida.name}")


# ============================================================
# AJUSTE DE COLUMNAS
# ============================================================

def _ajustar_columnas_excel(archivo_excel: Path):
    wb = load_workbook(archivo_excel)
    for ws in wb.worksheets:
        for col in ws.columns:
            max_length = 0
            column = get_column_letter(col[0].column)
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            ws.column_dimensions[column].width = max(10, min(max_length + 2, 50))
    wb.save(archivo_excel)


# ============================================================
# GRÁFICO CORPORATIVO SRI (azul y gris)
# ============================================================

def _insertar_grafico_corporativo(archivo_excel: Path):
    wb = load_workbook(archivo_excel)
    if "Totales por Emisor" not in wb.sheetnames:
        return

    ws = wb["Totales por Emisor"]
    num_filas = ws.max_row
    if num_filas < 2:
        wb.save(archivo_excel)
        return

    chart = BarChart()
    chart.title = "Totales por Emisor (SRI Audit)"
    chart.x_axis.title = "Razón Social"
    chart.y_axis.title = "Total ($)"
    chart.height = 10
    chart.width = 20

    # Datos y categorías
    data = Reference(ws, min_col=4, min_row=1, max_row=num_filas)  # columna "total"
    cats = Reference(ws, min_col=2, min_row=2, max_row=num_filas)  # columna "razonSocial"
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)

    # 🎨 Estilo corporativo SRI
    azul_sri = "1E4AA8"      # Azul institucional
    gris_suave = "A0A0A0"    # Gris complementario
    chart.graphicalProperties = GraphicalProperties(
        ln=ColorChoice(prstClr=gris_suave)
    )
    chart.graphicalProperties.solidFill = azul_sri

    # Mostrar valores encima de las barras
    from openpyxl.chart.label import DataLabelList
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = True

    # Insertar gráfico en celda H2
    ws.add_chart(chart, "H2")
    wb.save(archivo_excel)
