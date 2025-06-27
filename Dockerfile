FROM python:3.11-slim

# Configurar directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para archivos estáticos si no existe
RUN mkdir -p app/static

# Exponer puerto (Cloud Run usa PORT dinámico)
EXPOSE 8080

# Comando para ejecutar la aplicación
# Cloud Run proporciona PORT como variable de entorno
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"] 