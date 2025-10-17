import json
from datetime import datetime
from pathlib import Path
import pandas as pd

# ==============================
# CONFIGURACIÓN
# ==============================
HISTORIAL_PATH = Path("historial_descargas.json")


# ============================================================
# FUNCIONES BÁSICAS DE LECTURA Y ESCRITURA
# ============================================================
def _leer_historial() -> list:
    """
    Carga el historial desde el archivo JSON si existe.
    Retorna una lista de registros.
    """
    if HISTORIAL_PATH.exists():
        try:
            data = json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _guardar_historial(historial: list):
    """
    Guarda el historial completo en formato JSON.
    """
    try:
        HISTORIAL_PATH.write_text(json.dumps(historial, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[WARN] No se pudo guardar historial: {e}")


# ============================================================
# REGISTRO DE UNA NUEVA DESCARGA / REPORTE
# ============================================================
def registrar_descarga(ruc: str, origen: str, anio: int, mes: int, tipo: str, resultado: dict):
    """
    Registra una nueva ejecución (descarga o generación de reporte).
    Evita duplicados (mismo RUC + periodo + tipo + origen).
    """
    historial = _leer_historial()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    registro = {
        "Fecha": timestamp,
        "RUC": ruc,
        "Origen": origen,
        "Año": anio,
        "Mes": mes,
        "Tipo": tipo,
        "Estado": resultado.get("estado", "desconocido"),
        "XML descargados": resultado.get("n_xml", 0),
        "PDF descargados": resultado.get("n_pdf", 0),
        "Registros (Emitidos)": resultado.get("n_registros", 0),
        "Archivo TXT": resultado.get("txt", ""),
        "Reporte Excel": resultado.get("reporte", ""),
    }

    # Eliminar duplicados (misma combinación)
    historial = [
        h for h in historial
        if not (
            h.get("RUC") == ruc
            and h.get("Origen") == origen
            and h.get("Año") == anio
            and h.get("Mes") == mes
            and h.get("Tipo") == tipo
        )
    ]

    historial.append(registro)
    _guardar_historial(historial)


# ============================================================
# OBTENER HISTORIAL EN FORMATO TABULAR (para Streamlit)
# ============================================================
def obtener_historial() -> pd.DataFrame:
    """
    Devuelve el historial en formato pandas.DataFrame
    para visualización directa en Streamlit.
    """
    data = _leer_historial()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    # Ordenar por fecha descendente
    if "Fecha" in df.columns:
        df = df.sort_values("Fecha", ascending=False)
    return df

