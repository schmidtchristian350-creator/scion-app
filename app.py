import streamlit as st
import pandas as pd
from openai import OpenAI
from database import init_db, get_db_connection
from engines import litellm_router_abfrage, autonomer_browser_agent, generiere_desktop_befehl, verarbeite_sprachbefehl
from exporters import exportiere_zu_pdf, exportiere_zu_xlsx, exportiere_zu_docx, erstelle_pptx_aus_session

init_db()
st.set_page_config(page_title="Scion Mind - Enterprise Ultimate AGI Studio", layout="wide")

st.title("Scion-Mind - Ultimate Studio")
st.markdown("*designed by Christian Schmidt*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
ADMIN_NAME = "Christian"

if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "aktiver_chat" not in st.session_state:
    st.session_state.aktiver_chat = "Chat 1"
if "pending_desktop_action" not in st.session_state:
    st.session_state.pending_desktop_action = None

with st.sidebar:
    st.markdown("### 🎙️ iPhone Sprach-Eingang")
    voice_input = st.text_input("Sprachbefehl eingeben:")
    if voice_input:
        with st.spinner("Verarbeite..."):
            antwort = verarbeite_sprachbefehl(voice_input, MASTER_OPENAI_KEY)
            st.success(antwort)

current_chat = st.session_state.aktiver_chat
for message in st.session_state.chats[current_chat]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

aufgabe = st.chat_input("Gib dem Agenten eine Aufgabe...")
if aufgabe:
    st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
    with st.chat_message("user"):
        st.markdown(aufgabe)

    with st.spinner("Agent arbeitet..."):
        lower = aufgabe.lower()
        if "surfe" in lower or "webseite" in lower:
            antwort = autonomer_browser_agent("https://google.com", aufgabe, MASTER_OPENAI_KEY)
        elif "programm" in lower or "app" in lower:
            st.session_state.pending_desktop_action = generiere_desktop_befehl("System", aufgabe, MASTER_OPENAI_KEY)
            antwort = f"⚠️ **Sicherheitsabfrage:** Möchtest du diesen Befehl auf der Hardware ausführen?\n```bash\n{st.session_state.pending_desktop_action}\n```"
        else:
            antwort = litellm_router_abfrage("Du bist ein hilfreicher Assistent.", aufgabe, master_openai_key=MASTER_OPENAI_KEY)

    st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
    with st.chat_message("assistant"):
        st.markdown(antwort)

if st.session_state.pending_desktop_action:
    if st.button("✅ Aktion bestätigen"):
        st.success("Ausgeführt!")
        st.session_state.pending_desktop_action = None
        st.rerun()
