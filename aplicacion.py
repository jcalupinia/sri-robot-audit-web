# aplicacion.py — SRI Robot Audit (versión corregida)
import os
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from historial import registrar_descarga, obtener_historial
from robot.downloader import descargar_sri
from robot.parser import construir_reporte

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(
    page_title="SRI Robot Audit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Respetar variables del entorno (Docker/Render) y dar fallback local
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright")
os.environ.setdefault("PYPPETEER_HOME", "/ms-playwright")

BASE_DIR = Path(__file__).parent
DESC_DIR = BASE_DIR / "descargas"
DESC_DIR.mkdir(exist_ok=True, parents=True)

# ==============================
# SIDEBAR CORPORATIVO
# ==============================
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Logo_SRI_Ecuador.svg/2560px-Logo_SRI_Ecuador.svg.png",
        width=180,
    )
    st.markdown("### 🤖 Auditoría Web SRI Robot")
    st.write("Automatiza descargas, valida comprobantes y genera reportes tributarios.")
    st.markdown("---")
    st.markdown("**Versión:** 1.0  \n**Actualizado:** Octubre 2025")

# ==============================
# INTERFAZ PRINCIPAL
# ==============================
st.title("🧾 SRI Robot Audit — Descarga y Reporte Automático")

tab1, tab2 = st.tabs(["📥 Descarga de Comprobantes", "📊 Reportes e Historial"])

# =====================================================
# TAB 1 — DESCARGA Y PROCESAMIENTO AUTOMÁTICO
# =====================================================
with tab1:
    st.markdown("#### 1️⃣ Ingreso de Credenciales y Filtros")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        ruc = st.text_input("RUC", placeholder="Ejemplo: 0999999999001")
        clave = st.text_input("Clave del SRI", type="password", placeholder="••••••••")
    with col2:
        anio = st.number_input(
            "Año", min_value=2015, max_value=datetime.now().year, value=datetime.now().year
        )
        mes = st.number_input(
            "Mes (1–12)", min_value=1, max_value=12, value=datetime.now().month
        )
    with col3:
        tipo = st.selectbox(
            "Tipo de comprobante",
            ["Facturas", "Retenciones", "Notas de crédito", "Notas de débito", "Liquidación de compra"],
        )

    col4, col5 = st.columns([2, 2])
    with col4:
        origen = st.selectbox("Origen de comprobantes", ["Recibidos", "Emitidos"], index=0)
    with col5:
        formatos = st.multiselect("Formatos a descargar", ["XML", "PDF"], default=["XML", "PDF"])

    st.markdown("---")

    if st.button("🚀 Iniciar proceso", use_container_width=True, type="primary"):
        if not ruc or not clave:
            st.warning("⚠️ Ingresa RUC y clave antes de continuar.")
        else:
            destino = DESC_DIR / ruc / f"{anio:04d}" / f"{mes:02d}"
            destino.mkdir(parents=True, exist_ok=True)

            with st.spinner(f"🔍 Conectando al SRI ({origen}) y procesando comprobantes..."):
                resultado = descargar_sri(
                    ruc, clave, anio, mes, tipo, formatos, destino, origen=origen
                )

            # Registrar en historial (resultado resumido para trazabilidad)
            registrar_descarga(ruc, origen, anio, mes, tipo, resultado)

            # Mostrar resultados dinámicos
            estado = resultado.get("estado", "")
            if estado == "sin_descargas":
                st.warning("⚠️ No se encontraron comprobantes para el período seleccionado.")
            elif origen == "Emitidos":
                n_regs = resultado.get("n_registros", 0)
                st.success(f"✅ Reporte de emitidos generado con {n_regs} registros.")
                reporte_path = resultado.get("reporte")
                if reporte_path and Path(reporte_path).exists():
                    with open(reporte_path, "rb") as f:
                        st.download_button(
                            "📊 Descargar reporte Excel (Emitidos)",
                            f,
                            file_name=Path(reporte_path).name,
                            use_container_width=True,
                        )
            else:
                n_xml = resultado.get("n_xml", 0)
                n_pdf = resultado.get("n_pdf", 0)
                st.success(f"✅ Descarga completada. XML: {n_xml} | PDF: {n_pdf}")

                txt_path = resultado.get("txt")
                if txt_path and Path(txt_path).exists():
                    with open(txt_path, "rb") as f:
                        st.download_button(
                            "⬇️ Descargar TXT semilla",
                            f,
                            file_name=Path(txt_path).name,
                            use_container_width=True,
                        )

                if n_xml > 0:
                    xml_folder = destino / "XML"
                    excel_path = destino / f"reporte_{anio}_{mes:02d}.xlsx"
                    construir_reporte(xml_folder, excel_path)
                    if excel_path.exists():
                        with open(excel_path, "rb") as f:
                            st.download_button(
                                "📈 Descargar reporte Excel (Recibidos)",
                                f,
                                file_name=excel_path.name,
                                use_container_width=True,
                            )

                zip_path = destino.with_suffix(".zip")
                shutil.make_archive(str(destino), "zip", destino)
                if zip_path.exists():
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            "📦 Descargar ZIP completo",
                            f,
                            file_name=zip_path.name,
                            use_container_width=True,
                        )

# =====================================================
# TAB 2 — HISTORIAL Y REPORTE DE ACTIVIDAD
# =====================================================
with tab2:
    st.markdown("#### 📜 Historial de ejecuciones recientes")
    historial = obtener_historial()

    # Evitar "valor de verdad ambiguo" en DataFrame
    if isinstance(historial, pd.DataFrame) and not historial.empty:
        st.dataframe(historial, use_container_width=True)
        st.success(f"📂 Total de operaciones registradas: {len(historial)}")
    else:
        st.info("Aún no hay registros de descargas o reportes.")
