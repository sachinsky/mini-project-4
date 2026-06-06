import streamlit as st
import requests

st.set_page_config(page_title="Airline AI Support", page_icon="✈️", layout="centered")
st.title("Airline Customer Support Demo")
st.write(
    "Ask about flight status, delays, cancellations, baggage policies, or booking changes. "
    "This Streamlit app sends your question to a FastAPI backend and displays the AI-powered response."
)

api_url = st.text_input("FastAPI backend URL", value="http://localhost:8000/support/query")
query = st.text_area("Enter your question", height=160)

if st.button("Send query"):
    if not query.strip():
        st.warning("Please type a query before sending.")
    else:
        with st.spinner("Contacting the airline support engine..."):
            try:
                response = requests.post(api_url, json={"query": query.strip()}, timeout=20)
                response.raise_for_status()
                data = response.json()
                st.success("Response received")
                st.markdown("### Answer")
                st.write(data.get("answer", "No answer returned."))

                flights = data.get("retrieved_flights", [])
                if flights:
                    st.markdown("### Retrieved Flights")
                    for flight in flights:
                        st.write(
                            f"**{flight['flight_no']}** — {flight['airline_name']} | "
                            f"{flight['origin']} → {flight['destination']} | {flight['departure_date']} {flight['departure_time']} | "
                            f"Status: {flight['status']}"
                        )
                if data.get("knowledge_snippet"):
                    st.markdown("### Policy Guidance")
                    st.code(data["knowledge_snippet"])
            except requests.RequestException as exc:
                st.error(f"Request failed: {exc}")
