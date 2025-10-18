# ============================================================
# 🧠 SRI ROBOT AUDIT — Dockerfile Multietapa Liviano
# Versión: Octubre 2025
# Compatible con Render / Railway / Docker Desktop
# ============================================================

# ---------- ETAPA 1: BUILD (instala dependencias y prepara entorno) ----------
FROM python:3.11-slim AS builder

# 1️⃣ Instalar dependencias mínimas del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget curl ca-certificates fonts-liberation \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libxkbcommon0 libxshmfence1 \
    libgbm1 libnss3 libxss1 libdrm2 libgtk-3-0 xvfb unzip && \
    rm -rf /var/lib/apt/lists/*

# 2️⃣ Crear directorio de trabajo
WORKDIR /app
COPY . /app

# 3️⃣ Instalar dependencias Python (sin caché)
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# 4️⃣ Instalar Playwright y Chromium (una sola vez)
RUN python -m playwright install chromium

# ---------- ETAPA 2: RUNTIME (solo copia lo esencial) ----------
FROM python:3.11-slim

# 1️⃣ Instalar librerías requeridas por Chromium
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-liberation libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libxkbcommon0 libxshmfence1 \
    libgbm1 libnss3 libxss1 libgtk-3-0 xvfb && \
    rm -rf /var/lib/apt/lists/*

# 2️⃣ Copiar desde la etapa anterior (solo lo necesario)
WORKDIR /app
COPY --from=builder /app /app
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# 3️⃣ Variables de entorno
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PYPPETEER_HOME=/root/.cache/ms-playwright
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV TZ=America/Guayaquil
ENV PYTHONUNBUFFERED=1

# 4️⃣ Exponer puerto y lanzar Streamlit
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
