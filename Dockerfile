# --------------------------------------------------------
# 🧩 SRI ROBOT AUDIT — DOCKERFILE FINAL (Render.com OK)
# Autor: Jorge / Revisión técnica: ChatGPT Asistente
# Fecha: 2025-10-18
# --------------------------------------------------------

# Imagen base oficial de Playwright (trae Chromium y fuentes preinstaladas)
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Evitar prompts y logs truncados
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Carpeta de trabajo
WORKDIR /app

# Copiar dependencias del proyecto
COPY requirements.txt .

# --------------------------------------------------------
# 🧠 Instalar compiladores + fijar versión de pip estable
# --------------------------------------------------------
RUN pip install --upgrade pip==24.2 setuptools wheel && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libxml2-dev libxslt1-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------
# 📦 Instalar librerías del proyecto
# --------------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------
# 📂 Copiar el resto del código
# --------------------------------------------------------
COPY . .

# Crear carpeta de descargas (por si no existe)
RUN mkdir -p /app/descargas

# --------------------------------------------------------
# ⚙️ Variables Playwright para Render
# --------------------------------------------------------
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# --------------------------------------------------------
# 🚀 Comando de inicio de Streamlit
# --------------------------------------------------------
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
