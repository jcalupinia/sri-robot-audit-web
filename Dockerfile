# ============================================================
# DOCKERFILE: Playwright + Streamlit + Chromium (Render Ready)
# ============================================================
FROM python:3.13-slim

# ==============================
# 1️⃣ Instalar dependencias mínimas del sistema
# ==============================
RUN apt-get update && apt-get install -y wget gnupg ca-certificates && rm -rf /var/lib/apt/lists/*

# ==============================
# 2️⃣ Crear directorio de trabajo
# ==============================
WORKDIR /app
COPY . /app

# ==============================
# 3️⃣ Instalar dependencias Python y Playwright
# ==============================
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Instalar dependencias del navegador y Chromium
RUN python -m playwright install-deps && \
    mkdir -p /root/.cache/ms-playwright && \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright python -m playwright install chromium

# ==============================
# 4️⃣ Variables de entorno globales
# ==============================
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PYPPETEER_HOME=/root/.cache/ms-playwright
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# ==============================
# 5️⃣ Exponer puerto y ejecutar la app
# ==============================
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
