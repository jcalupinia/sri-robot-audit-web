# --------------------------------------------------------
# 🤖 SRI ROBOT AUDIT — DOCKERFILE FINAL (Render OK)
# Autor: Jorge / Revisión técnica: ChatGPT Asistente
# Fecha: 2025-10-18
# --------------------------------------------------------

# Imagen base oficial con soporte Playwright + Python
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Evitar prompts interactivos y forzar salida limpia
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Crear carpeta de trabajo
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# --------------------------------------------------------
# 🧠 Instalar compiladores y navegador Chromium
# --------------------------------------------------------
RUN pip install --upgrade pip==24.2 setuptools wheel && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libxml2-dev libxslt1-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # 🔹 Instalar dependencias del proyecto
    pip install --no-cache-dir -r requirements.txt && \
    # 🔹 Instalar navegador Chromium dentro de la imagen
    python -m playwright install chromium

# --------------------------------------------------------
# 📂 Copiar el resto del proyecto
# --------------------------------------------------------
COPY . .

# Crear carpeta de descargas (si no existe)
RUN mkdir -p /app/descargas

# --------------------------------------------------------
# ⚙️ Variables para compatibilidad general
# --------------------------------------------------------
ENV PYPPETEER_HOME=/root/.cache/ms-playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# --------------------------------------------------------
# 🚀 Comando de inicio
# --------------------------------------------------------
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
