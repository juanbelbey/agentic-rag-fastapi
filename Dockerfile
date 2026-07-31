# Dockerfile
# Imagen de la API FastAPI del agente. No incluye datos (docs/pdfs) ni
# secretos (.env) -- eso se pasa en runtime, ver README para el comando
# de docker run.

FROM python:3.12-slim

WORKDIR /app

# Copiar solo requirements.txt primero: Docker cachea esta capa y no
# reinstala dependencias si despues solo cambia el codigo en src/.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
