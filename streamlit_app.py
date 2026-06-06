import os

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Airline AI Support", page_icon="✈️", layout="centered")

api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
api_url = f"{api_base}/support/query"
swagger_url = f"{api_base}/docs"

tab_chat, tab_swagger = st.tabs(["Support Chat", "API Swagger"])

with tab_chat:
    st.title("✈️ Airline Customer Support")
    st.markdown(
        """
Ask about **flight status**, **delays**, **cancellations**, **baggage policies**, and more.
This interface sends your question to the FastAPI backend, which applies input/output guardrails,
routes the query to SQL or RAG pipelines, and returns a safe response.
"""
    )

    st.markdown("#### Example queries")
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Flight data (SQL)")
        st.code("What is the status of flight SG528?")
        st.code("How many seats are available on flight AI101?")
    with col2:
        st.caption("Policy (RAG) / Invalid queries")
        st.code("How much free baggage is allowed for domestic flights?")
        st.code("select from flights where PNR=ABC123  ← not supported")

    query = st.text_area("Enter your question", height=140, placeholder="Type your airline support question here...")

    if st.button("Send query", type="primary"):
        if not query.strip():
            st.warning("Please type a query before sending.")
        else:
            with st.spinner("Processing your query through guardrails and routing..."):
                try:
                    response = requests.post(api_url, json={"query": query.strip()}, timeout=120)
                    response.raise_for_status()
                    data = response.json()
                except requests.RequestException as exc:
                    st.error(f"Request failed: {exc}")
                    st.info("Make sure the FastAPI server is running: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`")
                else:
                    input_guardrail = data.get("input_guardrail")
                    output_guardrail = data.get("output_guardrail")
                    category = data.get("category")
                    answer = data.get("response", "No response returned.")

                    if input_guardrail and input_guardrail.startswith("UNSAFE"):
                        st.error("Input blocked by guardrail")
                    elif output_guardrail and output_guardrail.startswith("UNSAFE"):
                        st.error("Output blocked by guardrail")
                    else:
                        st.success("Response received")

                    if category:
                        st.markdown(f"**Routed to:** `{category}`")
                    if input_guardrail:
                        st.markdown(f"**Input guardrail:** `{input_guardrail}`")
                    if output_guardrail:
                        st.markdown(f"**Output guardrail:** `{output_guardrail}`")

                    st.markdown("### Answer")
                    st.write(answer)

with tab_swagger:
    st.title("API Swagger")
    st.markdown(
        f"""
Browse and test all API endpoints interactively.

**Available endpoints:**
- `GET /health` — server health check
- `POST /support/query` — process a support question

[Open Swagger in a new tab]({swagger_url})
"""
    )
    components.iframe(swagger_url, height=720, scrolling=True)
