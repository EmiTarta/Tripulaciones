# Utiliza una imagen base ligera de Python
FROM python:3.9-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos requeridos al contenedor
COPY requirements.txt requirements.txt
COPY app.py app.py

# Instalar dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar la aplicación Flask
CMD ["python", "app.py"]