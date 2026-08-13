# Dockerfile
# Imagen del frontend Streamlit. Pensada para docker-compose junto al backend
# (ver ../docker-compose.yml) -- no para Streamlit Community Cloud, que build-ea
# directo desde el repo sin este archivo.

FROM python:3.12-slim

WORKDIR /app

COPY streamlit_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streamlit_app/ .

EXPOSE 8501

# --server.address=0.0.0.0: sin esto, Streamlit puede quedar escuchando solo
# adentro del container -- ni el mapeo de puertos al host ni otros containers
# lo alcanzan, aunque el proceso este corriendo.
CMD streamlit run app.py --server.address=0.0.0.0 --server.port=8501
