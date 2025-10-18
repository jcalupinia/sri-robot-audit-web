# --------------------------------------------------------
# 🧩 SRI ROBOT AUDIT - Dockerfile FINAL (Playwright OK)
# Basado en imagen oficial de Microsoft Playwright
# --------------------------------------------------------

FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Evita prompts
ENV DEBIAN_FRONTEND=noninteractive

# Crea carpeta de trabajo
WORKDIR /app

# Copia dependencias
COPY requirements.txt .

# Instala librerías adicionales si las necesitas
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el proyecto
COPY . .

# Crear carpeta de descargas
RUN mkdir -p /app/descargas

# Variables de entorno para compatibilidad con Render
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Exponer puerto y lanzar app
EXPOSE 8501
CMD ["streamlit", "run", "aplicacion.py", "--server.port=8501", "--server.address=0.0.0.0"]
