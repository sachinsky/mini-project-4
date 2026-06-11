import os
import uuid

import requests
import streamlit as st

st.set_page_config(
    page_title="Airline Support",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="expanded",
)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
API_URL = f"{API_BASE}/support/query"
SWAGGER_URL = f"{API_BASE}/docs"

SUGGESTIONS = [
    "What is the status of flight SG528?",
    "Are there flights from Delhi to Mumbai?",
    "How much free baggage is allowed for domestic flights?",
    "What is the cancellation policy?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.markdown(
    """
    <style>
        .route-badge {
            display: inline-block;
            font-size: 0.72rem;
            padding: 2px 8px;
            border-radius: 999px;
            background: #1f2937;
            color: #93c5fd;
            margin-bottom: 0.4rem;
        }
        /* Prevent chat history from touching the input */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            margin-bottom: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def query_api(text: str, history: list[dict] | None = None) -> dict:
    payload = {
        "query": text.strip(),
        "session_id": st.session_state.session_id,
    }
    if history:
        payload["conversation_history"] = history
    resp = requests.post(API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def route_label(category: str | None) -> str:
    labels = {
        "Need SQL": "Flight data",
        "Non SQL": "Policy & FAQ",
        "Out of Context": "General",
        "Unsupported": "Not supported",
        "Safety": "Safety check",
        "Clarification": "Need more info",
    }
    return labels.get(category or "", category or "Support")


def render_message(msg: dict) -> None:
    role = msg["role"]
    with st.chat_message(role, avatar="🧑‍💼" if role == "user" else "✈️"):
        if role == "assistant" and msg.get("category"):
            st.markdown(
                f'<span class="route-badge">{route_label(msg["category"])}</span>',
                unsafe_allow_html=True,
            )
        st.markdown(msg["content"])
        if role == "assistant" and msg.get("meta"):
            with st.expander("Response details"):
                meta = msg["meta"]
                if meta.get("category"):
                    st.write(f"**Route:** {meta['category']}")
                if meta.get("input_guardrail"):
                    st.write(f"**Input guardrail:** {meta['input_guardrail']}")
                if meta.get("output_guardrail"):
                    st.write(f"**Output guardrail:** {meta['output_guardrail']}")


def add_exchange(user_text: str) -> None:
    prior_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages[-8:]
    ]
    st.session_state.messages.append({"role": "user", "content": user_text})
    try:
        data = query_api(user_text, history=prior_history)
        answer = data.get("response", "No response returned.")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "category": data.get("category"),
                "meta": data,
            }
        )
    except requests.RequestException as exc:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "I couldn't reach the support service right now. "
                    "Please make sure the API server is running.\n\n"
                    f"`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`\n\n"
                    f"Error: {exc}"
                ),
                "category": "Error",
            }
        )


with st.sidebar:
    st.markdown("## ✈️ Airline Support")
    st.caption("AI Customer Support")
    st.divider()
    st.markdown("**Try asking:**")
    for suggestion in SUGGESTIONS:
        if st.button(suggestion, width="stretch", key=f"sug_{suggestion[:20]}"):
            add_exchange(suggestion)
            st.rerun()
    st.divider()
    if st.button("🗑️ Clear conversation", width="stretch"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.link_button("📄 API Docs (Swagger)", SWAGGER_URL, width="stretch")
    st.link_button("📊 Analytics Dashboard", "http://localhost:8502", width="stretch")

st.markdown("### Airline Customer Support")
st.caption("Ask about flights, baggage, cancellations, and policies.")

chat_panel = st.container(border=True)
with chat_panel:
    history = st.container(height=480, border=False)
    with history:
        if not st.session_state.messages:
            st.markdown(
                """
                👋 **Welcome!** I'm your airline support assistant.

                I can help with:
                - **Flight status**, gates, delays, and seat availability
                - **Baggage**, refund, and cancellation policies
                - **Travel rules** from our airline knowledge base

                Type your question in the box below.
                """
            )
        else:
            for msg in st.session_state.messages:
                render_message(msg)

    st.divider()

    if prompt := st.chat_input("Ask about flights, baggage, policies..."):
        add_exchange(prompt)
        st.rerun()
