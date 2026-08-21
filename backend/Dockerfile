FROM python:3.11-slim

# Evitar escritura de archivos .pyc y forzar buffer no interactivo en stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalar dependencias de sistema necesarias para psycopg2 y compilación ligera
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de requerimientos e instalar dependencias de Python
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente completo del proyecto
COPY . /app/

# Exponer el puerto del servidor FastAPI en el contenedor
EXPOSE 8000

# Comando por defecto para iniciar la aplicación Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
