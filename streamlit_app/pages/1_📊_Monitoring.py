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
    "Real metrics from the backend, read from Postgres. Cost is an "
    "estimate based on the main chat LLM's tokens -- it doesn't include "
    "the internal query rewriting call, so it comes in slightly below "
    "the actual total cost."
)

try:
    response = requests.get(f"{BACKEND_URL}/stats", timeout=15)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException:
    st.error("Couldn't connect to the backend to fetch the metrics.")
    st.stop()

chat_logs = pd.DataFrame(data["chat_logs"])
feedback = pd.DataFrame(data["feedback"])

if chat_logs.empty:
    st.info("No conversations logged yet.")
    st.stop()

chat_logs["created_at"] = pd.to_datetime(chat_logs["created_at"])
chat_logs["date"] = chat_logs["created_at"].dt.date

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total requests", len(chat_logs))
col2.metric("Average latency", f"{chat_logs['latency_ms'].mean() / 1000:.1f} s")
col3.metric("Total estimated cost", f"${chat_logs['estimated_cost_usd'].sum():.4f}")
if not feedback.empty:
    positive_pct = (feedback["score"] >= 0.5).mean() * 100
    col4.metric("Positive feedback", f"{positive_pct:.0f}%")
else:
    col4.metric("Positive feedback", "no data")

st.divider()

st.subheader("Requests per day")
st.bar_chart(chat_logs.groupby("date").size().rename("requests"))

st.subheader("Average latency per day")
# bar_chart en vez de line_chart -- con un solo dia de datos, line_chart no
# tiene un segundo punto para trazar el segmento y queda vacio.
st.bar_chart(chat_logs.groupby("date")["latency_ms"].mean().rename("latency_ms"))

st.subheader("Cumulative estimated cost")
cost_by_day = chat_logs.groupby("date")["estimated_cost_usd"].sum().cumsum()
st.bar_chart(cost_by_day.rename("cumulative_cost_usd"))

st.subheader("Tool usage")
tool_counts: dict[str, int] = {}
for row in chat_logs["tool_calls_used"]:
    tools = row or []
    if not tools:
        key = "no tool (direct answer)"
        tool_counts[key] = tool_counts.get(key, 0) + 1
    for tool_name in tools:
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
st.bar_chart(pd.Series(tool_counts, name="requests"))

st.subheader("User feedback")
if feedback.empty:
    st.info("No feedback logged yet.")
else:
    feedback_counts = feedback["score"].apply(lambda s: "👍" if s >= 0.5 else "👎").value_counts()
    st.bar_chart(feedback_counts.rename("votes"))
