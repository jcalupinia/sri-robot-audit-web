# --------------------------------------------------------
# 🤖 SRI ROBOT AUDIT — DOCKERFILE FINAL (Render OK)
# Autor: Jorge / Revisión técnica: ChatGPT Asistente
# Fecha: 2025-10-18
# --------------------------------------------------------

# Imagen base oficial con Playwright y Python (incluye todas las dependencias)
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Evitar prompts y mejorar logs
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Crear carpeta de trabajo
WORKDIR /app

# Copiar dependencias del proyecto
COPY requirements.txt .

# --------------------------------------------------------
# 🧠 Instalar compiladores, dependencias y navegador Chromium
# --------------------------------------------------------
RUN pip install --upgrade pip==24.2 setuptools wheel && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libxml2-dev libxslt1-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt && \
    # 🔹 Instalar navegador Chromium dentro de la imagen y dar permisos
    mkdir -p /ms-playwright && \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright python -m playwright install chromium && \
    chmod -R 777 /ms-playwright

# --------------------------------------------------------
# 📂 Copiar el resto del código del proyecto
# --------------------------------------------------------
COPY . .

# Crear carpeta de descargas si no existe
RUN mkdir -p /app/descargas

# --------------------------------------------------------
# ⚙️ Variables de entorno para ejecución
# --------------------------------------------------------
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PYPPETEER_HOME=/ms-playwright

# --------------------------------------------------------
# 🚀 Comando de inicio para Render (puerto 8501)
# --------------------------------------------------------
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
