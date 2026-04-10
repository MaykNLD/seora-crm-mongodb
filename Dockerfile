# Dockerfile para CRM Flask
FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el codigo fuente
COPY . .

# Exponer el puerto
EXPOSE 3000

# Ejecutar Gunicorn en Producción en lugar del server de desarrollo
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "app:app"]
