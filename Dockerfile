# --------------------------------------------------------
# 🧩 SRI ROBOT AUDIT - Dockerfile corregido (Render.com)
# Autor: Jorge / Revisión técnica: ChatGPT Asistente
# Fecha: 2025-10-18
# --------------------------------------------------------

# Imagen base recomendada
FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Crear carpeta de trabajo
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# --------------------------------------------------------
# 🧰 Instalar dependencias del sistema y librerías base
# --------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg unzip curl \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxrandr2 \
    libxdamage1 libpango-1.0-0 libasound2 \
    fonts-liberation libxshmfence1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------
# 🧠 Instalar dependencias Python
# --------------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------
# 🧩 Instalar Playwright + Chromium (sin sandbox)
# --------------------------------------------------------
RUN pip install --no-cache-dir playwright==1.47.0 && \
    python -m playwright install chromium

# Variables de entorno para compatibilidad con Render
ENV PLAYWRIGHT_BROWSERS_PATH=0
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# --------------------------------------------------------
# 📦 Copiar el resto del proyecto
# --------------------------------------------------------
COPY . .

# Crear carpeta de descargas (si no existe)
RUN mkdir -p /app/descargas

# --------------------------------------------------------
# 🚀 Comando de inicio de Streamlit
# --------------------------------------------------------
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
