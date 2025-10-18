# ============================================================
# 🧠 SRI ROBOT AUDIT — Dockerfile Final (Render OK)
# Corrige error de fuentes "ttf-unifont" y dependencias Playwright
# ============================================================

FROM python:3.11-slim

# -------------------------------
# 1️⃣ Instalar dependencias del sistema necesarias
# -------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip gnupg ca-certificates \
    libnss3 libxss1 libasound2 fonts-liberation \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libgtk-3-0 xvfb fontconfig && \
    rm -rf /var/lib/apt/lists/*

# -------------------------------
# 2️⃣ Crear directorio de trabajo
# -------------------------------
WORKDIR /app
COPY . /app

# -------------------------------
# 3️⃣ Fijar versión estable de pip (evita conflictos)
# -------------------------------
RUN python -m pip install --upgrade "pip==23.3.1" setuptools wheel

# -------------------------------
# 4️⃣ Instalar dependencias Python
# -------------------------------
RUN pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# -------------------------------
# 5️⃣ Instalar Playwright y Chromium
# -------------------------------
RUN pip install --no-cache-dir playwright==1.47.0 && \
    python -m playwright install --with-deps chromium || true

# -------------------------------
# 6️⃣ Variables de entorno
# -------------------------------
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
ENV PYPPETEER_HOME=/root/.cache/ms-playwright
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Guayaquil

# -------------------------------
# 7️⃣ Exponer puerto y ejecutar
# -------------------------------
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
