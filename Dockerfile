# ============================================================
# DOCKERFILE: Playwright + Streamlit + Chromium (Render Ready)
# ============================================================
FROM python:3.13-slim

# ==============================
# 1️⃣ Instalar dependencias del sistema necesarias para Chromium
# ==============================
RUN apt-get update && \
    apt-get install -y wget gnupg ca-certificates fonts-liberation \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libxkbcommon0 libxshmfence1 \
    libgbm1 libnss3 libxss1 libdrm2 libxkbfile1 libgtk-3-0 xvfb && \
    rm -rf /var/lib/apt/lists/*

# ==============================
# 2️⃣ Crear el directorio de trabajo
# ==============================
WORKDIR /app
COPY . /app

# ==============================
# 3️⃣ Instalar dependencias de Python y Playwright
# ==============================
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN python -m playwright install --with-deps chromium

# ==============================
# 4️⃣ Variables de entorno
# ==============================
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PYPPETEER_HOME=/root/.cache/ms-playwright
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# ==============================
# 5️⃣ Exponer puerto y lanzar Streamlit
# ==============================
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
