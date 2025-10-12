import os

# 👇 AGREGAR ESTAS DOS LÍNEAS ANTES DE TODO
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/tmp/ms-playwright"
os.environ["PYPPETEER_HOME"] = "/tmp"

import streamlit as st
from pathlib import Path
from robot.downloader import descargar_sri
from robot.parser import construir_reporte
import shutil

BASE_DIR = Path(__file__).parent
DESC_DIR = BASE_DIR / "descargas"
DESC_DIR.mkdir(exist_ok=True)

st.title("Robot SRI-Audit — Descarga y Reporte")

col1, col2 = st.columns(2)
with col1:
    ruc = st.text_input("RUC")
    clave = st.text_input("Clave SRI", type="password")
with col2:
    anio = st.number_input("Año", min_value=2015, max_value=2100, value=2024)
    mes = st.number_input("Mes (1-12)", min_value=1, max_value=12, value=1)

tipo = st.selectbox("Tipo de comprobante", ["Facturas", "Retenciones", "Notas de crédito"])
formatos = st.multiselect("Formato a descargar", ["XML", "PDF"], default=["XML"])

if st.button("Iniciar descarga"):
    if not ruc or not clave:
        st.warning("Por favor ingresa RUC y clave.")
    else:
        destino = DESC_DIR / ruc / f"{anio:04d}" / f"{mes:02d}"
        destino.mkdir(parents=True, exist_ok=True)
        with st.spinner("Conectando con SRI y descargando..."):
            resultado = descargar_sri(ruc, clave, anio, mes, tipo, formatos, destino)
        st.success(f"Descarga completada: {resultado['n_archivos']} archivos.")

        if "XML" in formatos and resultado['n_archivos'] > 0:
            excel_path = destino / f"reporte_{anio}_{mes:02d}.xlsx"
            construir_reporte(destino, excel_path)
            with open(excel_path, "rb") as f:
                st.download_button("Descargar reporte Excel", f, file_name=excel_path.name)

        zip_path = destino.with_suffix(".zip")
        shutil.make_archive(str(destino), "zip", destino)
        with open(zip_path, "rb") as f:
            st.download_button("Descargar ZIP de archivos", f, file_name=zip_path.name)
