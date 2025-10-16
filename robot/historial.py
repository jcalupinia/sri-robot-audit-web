import json
from datetime import datetime
from pathlib import Path

HISTORIAL_PATH = Path("historial_descargas.json")

def _leer_historial():
    if HISTORIAL_PATH.exists():
        try:
            return json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _guardar_historial(historial):
    HISTORIAL_PATH.write_text(json.dumps(historial, indent=2, ensure_ascii=False))

def registrar_descarga(ruc: str, origen: str, anio: int, mes: int, tipo: str, resultado: dict):
    historial = _leer_historial()
    registro = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ruc": ruc,
        "origen": origen,
        "anio": anio,
        "mes": mes,
        "tipo": tipo,
        "estado": resultado.get("estado", "desconocido"),
        "xml_descargados": resultado.get("n_xml", 0),
        "pdf_descargados": resultado.get("n_pdf", 0),
        "ruta_txt": resultado.get("txt", ""),
    }
    historial = [h for h in historial if not (
        h["ruc"] == ruc and h["anio"] == anio and h["mes"] == mes and h["tipo"] == tipo and h["origen"] == origen
    )]
    historial.append(registro)
    _guardar_historial(historial)

def obtener_historial():
    return _leer_historial()
