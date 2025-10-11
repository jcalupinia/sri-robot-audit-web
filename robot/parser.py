from pathlib import Path
import pandas as pd
import xml.etree.ElementTree as ET

def _leer_xml(xml_path: Path) -> dict:
    d = {"archivo": xml_path.name}
    try:
        root = ET.parse(xml_path).getroot()
        d["fecha"] = root.findtext(".//fechaEmision", default="")
        d["rucEmisor"] = root.findtext(".//ruc", default="")
        d["razonSocial"] = root.findtext(".//razonSocial", default="")
        d["subtotal"] = float(root.findtext(".//totalSinImpuestos", default="0") or 0)
        d["iva"] = float(root.findtext(".//iva", default="0") or 0)
        d["total"] = float(root.findtext(".//importeTotal", default="0") or 0)
    except Exception as e:
        d["error"] = str(e)
    return d

def construir_reporte(carpeta_mes: Path, excel_salida: Path):
    rows = []
    for p in carpeta_mes.rglob("*.xml"):
        rows.append(_leer_xml(p))
    if not rows:
        return
    df = pd.DataFrame(rows)
    piv = df.groupby(["rucEmisor","razonSocial"], dropna=False)[["subtotal","iva","total"]].sum().reset_index()
    with pd.ExcelWriter(excel_salida, engine="openpyxl") as xls:
        df.to_excel(xls, index=False, sheet_name="Detalle")
        piv.to_excel(xls, index=False, sheet_name="Totales por Emisor")
