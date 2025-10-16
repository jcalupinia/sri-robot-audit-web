import os
import streamlit as st
from pathlib import Path
from datetime import datetime
import shutil
import pandas as pd
import matplotlib.pyplot as plt
from robot.downloader import descargar_sri
from robot.parser import construir_reporte
from robot.historial import obtener_historial

# ==============================
# CONFIGURACIÓN GENERAL (Docker / Render)
# ==============================
st.set_page_config(
    page_title="SRI Robot Audit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Variables de entorno Playwright
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/root/.cache/ms-playwright"
os.environ["PYPPETEER_HOME"] = "/root/.cache/ms-playwright"

BASE_DIR = Path(__file__).parent
DESC_DIR = BASE_DIR / "descargas"
DESC_DIR.mkdir(exist_ok=True)

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

tab1, tab2 = st.tabs(["📥 Descarga de Comprobantes", "📊 Reportes y Resultados"])

# ============================================================
# TAB 1 — DESCARGA DE COMPROBANTES
# ============================================================
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

    # ==============================
    # BOTÓN DE DESCARGA
    # ==============================
    if st.button("🚀 Iniciar descarga", use_container_width=True, type="primary"):
        if not ruc or not clave:
            st.warning("⚠️ Ingresa RUC y clave antes de continuar.")
        else:
            destino = DESC_DIR / ruc / f"{anio:04d}" / f"{mes:02d}"
            destino.mkdir(parents=True, exist_ok=True)

            with st.spinner(f"🔍 Conectando al SRI ({origen}) y descargando comprobantes..."):
                resultado = descargar_sri(ruc, clave, anio, mes, tipo, formatos, destino, origen=origen)

            if resultado["estado"] == "sin_descargas":
                st.warning("⚠️ No se encontraron comprobantes para el período seleccionado.")
            elif resultado["estado"] == "error":
                st.error(f"❌ Error durante la descarga: {resultado.get('mensaje', 'desconocido')}")
            else:
                st.success(
                    f"✅ Descarga completada ({origen}). "
                    f"XML: {resultado['n_xml']} | PDF: {resultado['n_pdf']}"
                )

                # TXT semilla
                if "txt" in resultado and Path(resultado["txt"]).exists():
                    with open(resultado["txt"], "rb") as f:
                        st.download_button(
                            "⬇️ Descargar TXT semilla",
                            f,
                            file_name=Path(resultado["txt"]).name,
                            use_container_width=True,
                        )

                # Reporte Excel
                if resultado["n_xml"] > 0:
                    xml_folder = destino / "XML"
                    excel_path = destino / f"reporte_{anio}_{mes:02d}.xlsx"
                    construir_reporte(xml_folder, excel_path)
                    with open(excel_path, "rb") as f:
                        st.download_button(
                            "📊 Descargar reporte Excel",
                            f,
                            file_name=excel_path.name,
                            use_container_width=True,
                        )

                # ZIP completo
                zip_path = destino.with_suffix(".zip")
                shutil.make_archive(str(destino), "zip", destino)
                with open(zip_path, "rb") as f:
                    st.download_button(
                        "📦 Descargar ZIP de comprobantes",
                        f,
                        file_name=zip_path.name,
                        use_container_width=True,
                    )

# ============================================================
# TAB 2 — DASHBOARD DE REPORTES E HISTORIAL
# ============================================================
with tab2:
    st.markdown("### 📊 Reportes y Resultados — Historial de Descargas")

    data = obtener_historial()
    if not data:
        st.info("Aún no hay descargas registradas. Ejecuta una descarga para comenzar.")
    else:
        df = pd.DataFrame(data)
        df["Periodo"] = df["anio"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2)

        # --- Métricas generales ---
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 XML descargados", int(df["xml_descargados"].sum()))
        col2.metric("📘 PDF descargados", int(df["pdf_descargados"].sum()))
        col3.metric("✅ Éxito de procesos", f"{(df['estado'].eq('ok').mean() * 100):.1f}%")

        # --- Tabla de historial ---
        st.markdown("#### 📋 Historial completo")
        st.dataframe(
            df.sort_values("timestamp", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        # --- Gráfico: descargas por mes y tipo ---
        st.markdown("#### 📈 Volumen mensual de descargas")
        resumen = (
            df.groupby(["Periodo", "origen"])[["xml_descargados", "pdf_descargados"]]
            .sum()
            .reset_index()
        )

        fig, ax = plt.subplots(figsize=(10, 5))
        for origen, subset in resumen.groupby("origen"):
            ax.plot(subset["Periodo"], subset["xml_descargados"], marker="o", label=f"{origen} (XML)")
            ax.plot(subset["Periodo"], subset["pdf_descargados"], marker="s", linestyle="--", label=f"{origen} (PDF)")

        ax.set_title("Tendencia mensual de comprobantes descargados", fontsize=13)
        ax.set_xlabel("Periodo (Año-Mes)")
        ax.set_ylabel("Cantidad de archivos")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.xticks(rotation=45)
        st.pyplot(fig)

        # --- Totales por tipo de comprobante ---
        st.markdown("#### 🧾 Totales por tipo de comprobante")
        totales_tipo = (
            df.groupby(["tipo", "origen"])[["xml_descargados", "pdf_descargados"]]
            .sum()
            .reset_index()
        )
        st.dataframe(totales_tipo, use_container_width=True, hide_index=True)
