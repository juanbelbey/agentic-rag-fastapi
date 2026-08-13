"""Dashboard de monitoring: requests, latencia, costo, tools y feedback (consume GET /stats)."""

import os

import pandas as pd
import requests
import streamlit as st

# Mismo patron que app.py: env var (docker-compose) > st.secrets (Streamlit
# Cloud) > localhost (dev local suelto).
BACKEND_URL = os.environ.get("BACKEND_URL")
if not BACKEND_URL:
    try:
        # st.secrets levanta StreamlitSecretNotFoundError si no existe NINGUN
        # secrets.toml, no solo si falta la key.
        BACKEND_URL = st.secrets["BACKEND_URL"]
    except Exception:
        BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Monitoring", page_icon="📊")
st.title("📊 Monitoring")
st.caption(
    "Métricas reales del backend, leídas de Postgres. El costo es una "
    "estimación a partir de los tokens del LLM principal del chat -- no "
    "incluye la llamada interna de query rewriting, así que queda algo por "
    "debajo del costo real total."
)

try:
    response = requests.get(f"{BACKEND_URL}/stats", timeout=15)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException:
    st.error("No se pudo conectar con el backend para traer las métricas.")
    st.stop()

chat_logs = pd.DataFrame(data["chat_logs"])
feedback = pd.DataFrame(data["feedback"])

if chat_logs.empty:
    st.info("Todavía no hay conversaciones registradas.")
    st.stop()

chat_logs["created_at"] = pd.to_datetime(chat_logs["created_at"])
chat_logs["date"] = chat_logs["created_at"].dt.date

col1, col2, col3, col4 = st.columns(4)
col1.metric("Requests totales", len(chat_logs))
col2.metric("Latencia promedio", f"{chat_logs['latency_ms'].mean():.0f} ms")
col3.metric("Costo estimado total", f"${chat_logs['estimated_cost_usd'].sum():.4f}")
if not feedback.empty:
    positive_pct = (feedback["score"] >= 0.5).mean() * 100
    col4.metric("Feedback positivo", f"{positive_pct:.0f}%")
else:
    col4.metric("Feedback positivo", "sin datos")

st.divider()

st.subheader("Requests por día")
st.bar_chart(chat_logs.groupby("date").size().rename("requests"))

st.subheader("Latencia promedio por día")
st.line_chart(chat_logs.groupby("date")["latency_ms"].mean().rename("latencia_ms"))

st.subheader("Costo estimado acumulado")
cost_by_day = chat_logs.groupby("date")["estimated_cost_usd"].sum().cumsum()
st.line_chart(cost_by_day.rename("costo_acumulado_usd"))

st.subheader("Uso de tools")
tool_counts: dict[str, int] = {}
for row in chat_logs["tool_calls_used"]:
    tools = row or []
    if not tools:
        key = "sin tool (respuesta directa)"
        tool_counts[key] = tool_counts.get(key, 0) + 1
    for tool_name in tools:
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
st.bar_chart(pd.Series(tool_counts, name="requests"))

st.subheader("Feedback de usuarios")
if feedback.empty:
    st.info("Todavía no hay feedback registrado.")
else:
    feedback_counts = feedback["score"].apply(lambda s: "👍" if s >= 0.5 else "👎").value_counts()
    st.bar_chart(feedback_counts.rename("votos"))
