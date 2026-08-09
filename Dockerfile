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

# Forma shell (no exec/array) para que ${PORT:-8000} se expanda: Render inyecta
# su propio $PORT en runtime y espera que el proceso escuche ahi (no siempre
# 8000); localmente sin $PORT seteado, cae al 8000 de siempre. `exec` reemplaza
# el proceso de sh por uvicorn (no lo deja como hijo) para que reciba SIGTERM
# de Render directo, en vez de que se pierda en la capa del shell.
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
