# =====================================================
# 📜 MÓDULO: HISTORIAL DE DESCARGAS Y AUDITORÍA
# =====================================================
# Guarda y recupera el historial de ejecuciones del robot.
# Estructura de archivo: historial_descargas.json
# =====================================================

import json
from datetime import datetime
from pathlib import Path
import pandas as pd

# Ruta base (Render / Docker / local)
BASE_DIR = Path(__file__).resolve().parent.parent
HIST_PATH = BASE_DIR / "historial_descargas.json"

# =====================================================
# 🧾 REGISTRAR DESCARGA
# =====================================================
def registrar_descarga(ruc, origen, anio, mes, tipo, resultado):
    """
    Registra una ejecución del robot en el archivo JSON.
    Crea el historial si no existe.
    """
    registro = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ruc": ruc,
        "origen": origen,
        "anio": int(anio),
        "mes": int(mes),
        "tipo": tipo,
        "estado": resultado.get("estado", "finalizado"),
        "n_xml": resultado.get("n_xml", 0),
        "n_pdf": resultado.get("n_pdf", 0),
        "n_registros": resultado.get("n_registros", 0),
    }

    # Leer historial existente o iniciar lista vacía
    if HIST_PATH.exists():
        try:
            with open(HIST_PATH, "r", encoding="utf-8") as f:
                historial = json.load(f)
                if not isinstance(historial, list):
                    historial = []
        except Exception:
            historial = []
    else:
        historial = []

    # Agregar nuevo registro y guardar
    historial.append(registro)
    with open(HIST_PATH, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

    return registro


# =====================================================
# 📊 OBTENER HISTORIAL
# =====================================================
def obtener_historial():
    """
    Devuelve el historial como DataFrame ordenado (más recientes primero).
    Si no existe, devuelve un DataFrame vacío.
    """
    if not HIST_PATH.exists():
        return pd.DataFrame()

    try:
        with open(HIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values(by="timestamp", ascending=False).reset_index(drop=True)
        return df
    except Exception:
        # Si el JSON está corrupto, devolver vacío
        return pd.DataFrame()
