# --------------------------------------------------------
# 🧩 SRI ROBOT AUDIT — DOCKERFILE FINAL (Render OK)
# Autor: Jorge / Revisión técnica: ChatGPT Asistente
# Fecha: 2025-10-18
# --------------------------------------------------------

# Imagen base oficial de Playwright con Python + Chromium listo
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Evitar prompts interactivos y asegurar logs visibles
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Crear carpeta de trabajo
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# --------------------------------------------------------
# 🧠 Instalar dependencias de compilación y versiones estables de pip
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
# 📂 Copiar el resto del proyecto
# --------------------------------------------------------
COPY . .

# Crear carpeta de descargas
RUN mkdir -p /app/descargas

# --------------------------------------------------------
# ⚙️ Variables de entorno Playwright
# --------------------------------------------------------
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# --------------------------------------------------------
# 🚀 Comando de inicio (Render detecta el puerto 8501)
# --------------------------------------------------------
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
