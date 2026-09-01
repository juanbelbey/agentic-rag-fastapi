"""Dashboard de monitoring: requests, latencia, costo, tools y feedback (consume GET /stats)."""

import os

import altair as alt
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

# Paleta validada (colorblind-safe, ver skill dataviz de Claude Code) --
# mismos hex en todo el dashboard, no elegidos a ojo.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
MUTED = "#898781"

st.set_page_config(page_title="Monitoring", page_icon="📊")
st.title("📊 Monitoring")
st.caption("Real metrics from the backend, read live from Postgres -- not demo data.")

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

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total requests", len(chat_logs))
col2.metric("Average latency", f"{chat_logs['latency_ms'].mean() / 1000:.1f} s")
col3.metric("Total estimated cost", f"${chat_logs['estimated_cost_usd'].sum():.4f}")
col3.caption("Excludes the internal query-rewriting call, so it's slightly below the real total.")
if not feedback.empty:
    positive_pct = (feedback["score"] >= 0.5).mean() * 100
    col4.metric("Positive feedback", f"{positive_pct:.0f}%")
else:
    col4.metric("Positive feedback", "no data")

# 24h y no "total" a proposito: la tasa de error historica se diluye a medida
# que se acumulan requests viejos, y lo que importa operacionalmente es "¿esta
# fallando ahora?", no "¿cuanto fallo desde que existe el proyecto?".
last_24h = chat_logs[chat_logs["created_at"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24)]
if not last_24h.empty and "status" in last_24h.columns:
    error_pct = (last_24h["status"] == "error").mean() * 100
    col5.metric("Error rate (24h)", f"{error_pct:.0f}%")
else:
    col5.metric("Error rate (24h)", "no data")

st.divider()


# Barra unica (sin leyenda: un solo color = un solo titulo ya la nombra),
# 24px maximo, extremo superior redondeado (4px) y base cuadrada, grid en
# gris tenue de un solo paso respecto de la superficie, tooltip al pasar
# el mouse. Especificacion de la skill dataviz de Claude Code.
def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    x_title: str,
    y_title: str,
    color: str = BLUE,
    y_format: str = ",.0f",
    tooltip_format: str | None = None,
    integer_ticks: bool = False,
) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(
            size=24,
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
            color=color,
        )
        .encode(
            x=alt.X(
                f"{x}:O",
                title=x_title,
                axis=alt.Axis(domainColor=AXIS_LINE, tickColor=AXIS_LINE, labelColor=MUTED, labelAngle=0),
            ),
            y=alt.Y(
                f"{y}:Q",
                title=y_title,
                # tickMinStep=1 evita que Altair proponga ticks en medios
                # enteros (0, 0.5, 1...) en rangos chicos de conteos -- con
                # format=",.0f" esos medios se redondean y el eje muestra
                # etiquetas duplicadas ("1", "1").
                axis=alt.Axis(
                    format=y_format,
                    gridColor=GRIDLINE,
                    domainColor=AXIS_LINE,
                    tickColor=AXIS_LINE,
                    labelColor=MUTED,
                    **({"tickMinStep": 1} if integer_ticks else {}),
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{x}:O", title=x_title),
                alt.Tooltip(f"{y}:Q", title=y_title, format=tooltip_format or y_format),
            ],
        )
        .properties(height=280)
    )


# Barra con un color por categoria (dominio fijo, no por ranking) para que
# cada categoria se distinga sin depender de una leyenda -- el eje X ya la
# nombra directamente.
def categorical_bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    x_title: str,
    y_title: str,
    domain: list[str],
    range_: list[str],
) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(size=24, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                f"{x}:N",
                title=x_title,
                sort=domain,
                axis=alt.Axis(domainColor=AXIS_LINE, tickColor=AXIS_LINE, labelColor=MUTED, labelAngle=0),
            ),
            y=alt.Y(
                f"{y}:Q",
                title=y_title,
                axis=alt.Axis(
                    format=",.0f",
                    gridColor=GRIDLINE,
                    domainColor=AXIS_LINE,
                    tickColor=AXIS_LINE,
                    labelColor=MUTED,
                    tickMinStep=1,
                ),
            ),
            color=alt.Color(f"{x}:N", scale=alt.Scale(domain=domain, range=range_), legend=None),
            tooltip=[alt.Tooltip(f"{x}:N", title=x_title), alt.Tooltip(f"{y}:Q", title=y_title, format=",.0f")],
        )
        .properties(height=280)
    )


st.subheader("Requests per day")
requests_per_day = chat_logs.groupby("date").size().rename("requests").reset_index()
requests_per_day["date"] = requests_per_day["date"].astype(str)
st.altair_chart(
    bar_chart(requests_per_day, "date", "requests", "Date", "Requests", integer_ticks=True),
    use_container_width=True,
)

st.subheader("Average latency per day")
chat_logs["latency_s"] = chat_logs["latency_ms"] / 1000
latency_per_day = chat_logs.groupby("date")["latency_s"].mean().rename("latency_s").reset_index()
latency_per_day["date"] = latency_per_day["date"].astype(str)
st.altair_chart(
    bar_chart(latency_per_day, "date", "latency_s", "Date", "Latency (s)", y_format=",.1f"),
    use_container_width=True,
)

st.subheader("Cumulative estimated cost")
cost_by_day = chat_logs.groupby("date")["estimated_cost_usd"].sum().cumsum().rename("cumulative_cost_usd")
cost_by_day = cost_by_day.reset_index()
cost_by_day["date"] = cost_by_day["date"].astype(str)
st.altair_chart(
    bar_chart(
        cost_by_day,
        "date",
        "cumulative_cost_usd",
        "Date",
        "Cumulative cost (USD)",
        color=ORANGE,
        y_format="$,.4f",
        tooltip_format="$,.4f",
    ),
    use_container_width=True,
)

st.subheader("Tool usage")
tool_counts: dict[str, int] = {}
for row in chat_logs["tool_calls_used"]:
    tools = row or []
    if not tools:
        key = "no tool (direct answer)"
        tool_counts[key] = tool_counts.get(key, 0) + 1
    for tool_name in tools:
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
tool_domain = ["rag_search", "create_ticket", "no tool (direct answer)"]
tool_df = pd.DataFrame(
    [{"tool": name, "requests": tool_counts[name]} for name in tool_domain if name in tool_counts]
)
st.altair_chart(
    categorical_bar_chart(
        tool_df, "tool", "requests", "Tool", "Requests", domain=tool_domain, range_=[BLUE, ORANGE, AQUA]
    ),
    use_container_width=True,
)

st.subheader("Errors by type")
errors_df = chat_logs[chat_logs["status"] == "error"] if "status" in chat_logs.columns else pd.DataFrame()
if errors_df.empty:
    st.info("No errors logged in the last 500 requests.")
else:
    error_counts = errors_df["error_type"].fillna("unknown").value_counts().rename("count").reset_index()
    error_counts.columns = ["error_type", "count"]
    st.altair_chart(
        bar_chart(error_counts, "error_type", "count", "Error type", "Count", color=CRITICAL, integer_ticks=True),
        use_container_width=True,
    )

st.subheader("User feedback")
if feedback.empty:
    st.info("No feedback logged yet.")
else:
    feedback_counts = (
        feedback["score"].apply(lambda s: "👍" if s >= 0.5 else "👎").value_counts().rename("votes")
    )
    feedback_df = feedback_counts.reset_index()
    feedback_df.columns = ["vote", "votes"]
    st.altair_chart(
        categorical_bar_chart(
            feedback_df, "vote", "votes", "Vote", "Votes", domain=["👍", "👎"], range_=[GOOD, CRITICAL]
        ),
        use_container_width=True,
    )
