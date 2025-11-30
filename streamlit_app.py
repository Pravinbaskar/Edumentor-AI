import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="EduMentor AI", page_icon="🎓", layout="centered")
st.title("🎓 EduMentor AI")
st.caption("An Intelligent Multi-Agent Learning Companion")

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.form(key="chat_form", clear_on_submit=True):
    user_message = st.text_input("Ask EduMentor a question or request a study plan:")
    submitted = st.form_submit_button("Send")

if submitted and user_message:
    try:
        payload = {
            "user_id": "demo_user",
            "message": user_message,
            "session_id": st.session_state.session_id,
        }
        resp = requests.post(f"{BACKEND_URL}/chat", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        st.session_state.session_id = data["session_id"]
        reply = data["reply"]
        st.session_state.chat_history.append(("You", user_message))
        st.session_state.chat_history.append(("EduMentor", reply))
    except Exception as e:
        st.error(f"Error contacting backend: {e}")

st.markdown("---")
st.subheader("Conversation")

if not st.session_state.chat_history:
    st.info(
        "Try asking: `Solve 2x + 3 = 11 step by step` or "
        "`Create a study plan for my algebra test in 5 days`."
    )
else:
    for speaker, text in st.session_state.chat_history:
        if speaker == "You":
            st.markdown(f"**🧑 {speaker}:** {text}")
        else:
            st.markdown(f"**🤖 {speaker}:** {text}")
