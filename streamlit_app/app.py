"""Frontend Streamlit: chat contra el agente RAG (consume /chat y /feedback)."""

import os
import uuid

import requests
import streamlit as st

# Prioridad: variable de entorno (docker-compose le pasa BACKEND_URL asi) >
# st.secrets (como configura Streamlit Cloud, que no usa env vars) > localhost
# (dev local suelto, sin compose ni secrets.toml).
BACKEND_URL = os.environ.get("BACKEND_URL")
if not BACKEND_URL:
    try:
        # st.secrets levanta StreamlitSecretNotFoundError si no existe NINGUN
        # secrets.toml (no solo si falta la key) -- pasa siempre en dev local,
        # donde no creamos ese archivo a proposito.
        BACKEND_URL = st.secrets["BACKEND_URL"]
    except Exception:
        BACKEND_URL = "http://localhost:8000"

ASSISTANT_AVATAR = "🔧"
USER_AVATAR = "🙋"

st.set_page_config(page_title="Field Instrumentation Support", page_icon="🔧")
st.title("🔧 Field Instrumentation Assistant")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("About this project")
    st.markdown(
        "RAG agent for technical support on field instrumentation "
        "(water supply and sanitation): answers with source citations "
        "from real manuals (Emerson/Siemens/Endress+Hauser) and escalates "
        "to a ticket when a human technician is needed."
    )
    st.caption("Stack: FastAPI · LangGraph · pgvector/Supabase · LangSmith")
    st.divider()
    if st.button("🆕 New conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()


def send_feedback(run_id: str, score: float) -> bool:
    try:
        response = requests.post(
            f"{BACKEND_URL}/feedback",
            json={"run_id": run_id, "thread_id": st.session_state.thread_id, "score": score},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False


for i, msg in enumerate(st.session_state.messages):
    avatar = ASSISTANT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and msg.get("tool_calls_used"):
            st.caption("🔍 Searched the documentation (`rag_search`)"
                       if "rag_search" in msg["tool_calls_used"]
                       else f"🛠️ Used: {', '.join(msg['tool_calls_used'])}")

        if msg["role"] == "assistant" and msg.get("run_id"):
            if msg.get("feedback") is not None:
                st.caption("Thanks for your feedback" + (" 👍" if msg["feedback"] == "up" else " 👎"))
            else:
                col_up, col_down, _ = st.columns([1, 1, 10])
                if col_up.button("👍", key=f"up_{i}"):
                    if send_feedback(msg["run_id"], 1.0):
                        msg["feedback"] = "up"
                    else:
                        st.toast("Couldn't register your feedback, please try again.", icon="⚠️")
                    st.rerun()
                if col_down.button("👎", key=f"down_{i}"):
                    if send_feedback(msg["run_id"], 0.0):
                        msg["feedback"] = "down"
                    else:
                        st.toast("Couldn't register your feedback, please try again.", icon="⚠️")
                    st.rerun()

if prompt := st.chat_input("Ask me about transmitters, calibration, maintenance..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={"message": prompt, "thread_id": st.session_state.thread_id},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 429:
                    st.error("There's a lot of demand right now. Wait a minute and try again.")
                else:
                    st.error("An error occurred while querying the agent. Try again in a few seconds.")
                st.stop()
            except requests.exceptions.RequestException:
                st.error("Couldn't connect to the backend. Try again in a few seconds.")
                st.stop()
        st.markdown(data["response"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": data["response"],
        "run_id": data["run_id"],
        "tool_calls_used": data["tool_calls_used"],
        "feedback": None,
    })
    st.rerun()
