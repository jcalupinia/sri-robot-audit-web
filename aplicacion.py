import os
import streamlit as st
from pathlib import Path
from robot.downloader import descargar_sri
from robot.parser import construir_reporte
import shutil
from datetime import datetime

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(
    page_title="SRI Robot Audit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ Cambio clave: usar carpeta persistente en Render
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/render/project/.playwright"
os.environ["PYPPETEER_HOME"] = "/opt/render/project/.playwright"

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

# Tabs (pestañas visuales)
tab1, tab2 = st.tabs(["📥 Descarga de Comprobantes", "📊 Reportes y Resultados"])

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
        tipo = st.selectbox("Tipo de comprobante", ["Facturas", "Retenciones", "Notas de crédito"])
        formatos = st.multiselect("Formatos", ["XML", "PDF"], default=["XML"])

    st.markdown("---")

    if st.button("🚀 Iniciar descarga", use_container_width=True, type="primary"):
        if not ruc or not clave:
            st.warning("⚠️ Ingresa RUC y clave antes de continuar.")
        else:
            destino = DESC_DIR / ruc / f"{anio:04d}" / f"{mes:02d}"
            destino.mkdir(parents=True, exist_ok=True)

            with st.spinner("🔍 Conectando con el SRI y descargando comprobantes..."):
                resultado = descargar_sri(ruc, clave, anio, mes, tipo, formatos, destino)

            st.success(f"✅ Descarga completada: {resultado['n_archivos']} archivos encontrados.")

            # ==============================
            # GENERAR REPORTE EXCEL
            # ==============================
            if "XML" in formatos and resultado["n_archivos"] > 0:
                excel_path = destino / f"reporte_{anio}_{mes:02d}.xlsx"
                construir_reporte(destino, excel_path)
                with open(excel_path, "rb") as f:
                    st.download_button(
                        "⬇️ Descargar reporte Excel",
                        f,
                        file_name=excel_path.name,
                        use_container_width=True,
                    )

            # ==============================
            # DESCARGAR ZIP
            # ==============================
            zip_path = destino.with_suffix(".zip")
            shutil.make_archive(str(destino), "zip", destino)
            with open(zip_path, "rb") as f:
                st.download_button(
                    "📦 Descargar ZIP de comprobantes",
                    f,
                    file_name=zip_path.name,
                    use_container_width=True,
                )

with tab2:
    st.markdown("#### 📈 Próximamente: dashboard de auditoría visual")
    st.info("Aquí podrás ver indicadores y gráficos con las descargas procesadas.")
