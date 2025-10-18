# ============================================================
# SRI ROBOT AUDIT — Dockerfile Final (Render Ready)
# Resolución de dependencias flexible y Playwright estable
# ============================================================

FROM python:3.11-slim

# ==============================
# 1️⃣ Instalar dependencias del sistema
# ==============================
RUN apt-get update && \
    apt-get install -y wget gnupg ca-certificates fonts-liberation \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libxkbcommon0 libxshmfence1 \
    libgbm1 libnss3 libxss1 libdrm2 libxkbfile1 libgtk-3-0 xvfb unzip && \
    rm -rf /var/lib/apt/lists/*

# ==============================
# 2️⃣ Crear el directorio de trabajo
# ==============================
WORKDIR /app
COPY . /app

# ==============================
# 3️⃣ Instalar dependencias de Python y Playwright
# ==============================
RUN pip install --upgrade pip setuptools wheel --no-cache-dir
# 🚨 Desactivar resolución estricta y permitir paquetes de sistema
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt || true
RUN pip install --no-cache-dir playwright==1.47.0
RUN python -m playwright install --with-deps chromium

# ==============================
# 4️⃣ Variables de entorno (Render + Docker)
# ==============================
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PYPPETEER_HOME=/root/.cache/ms-playwright
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Guayaquil

# ==============================
# 5️⃣ Exponer puerto y lanzar aplicación
# ==============================
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
