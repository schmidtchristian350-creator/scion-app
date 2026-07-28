import streamlit as st
import time
import json
import base64
import secrets
import threading
import pandas as pd
from openai import OpenAI

from database import init_db, get_db_connection
from engines import (
    litellm_router_abfrage, ausfuehren_mit_ollama_fallback, echte_deep_web_recherche,
    berechne_pl_break_even, starte_swot_analyse, ausfuehren_in_self_healing_sandbox,
    suche_in_rag_vektor_db, selbstevaluierender_lern_agent, verschruessle_api_key, ent_huelle_api_key
)
from exporters import (
    exportiere_zu_docx, exportiere_zu_xlsx, exportiere_zu_pdf, erstelle_pptx_aus_session, erstelle_pdf_aus_session
)

# Initialisierung der Datenbank
init_db()

st.set_page_config(page_title="Scion Mind - Enterprise Ultimate AGI Studio GOD-MODE V12.17", layout="wide")

# CSS Styling
st.markdown("""
    <style>
    .stApp { background-color: var(--background-color); color: var(--text-color); }
    [data-testid="stSidebar"] { background-color: #1e293b; color: #ffffff !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #ffffff !important; }
    .stButton button { background-color: #0f172a; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%; }
    .stButton button:hover { background-color: #334155; color: white; }
    input, textarea, [data-baseweb="input"] div, [data-baseweb="base-input"] { border-radius: 8px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("Scion-Mind - Ultimate Studio")
st.markdown("*designed by Christian Schmidt*") 
st.markdown("*Powered by Hierarchical Swarm Board • Multi-Agent-Systems • Live-Terminal Streaming • Ollama Local Fallback • OCR • Analytics • Self-Coding*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
IMAGE_API_KEY = st.secrets.get("VIDEO_API_KEY", MASTER_OPENAI_KEY)
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

ADMIN_NAME = "Christian"
ADMIN_PASS = "ScionMind#2026!Secured"

if "session_verrauchter_betrag" not in st.session_state:
    st.session_state.session_verrauchter_betrag = 0.0

def berechne_und_ziehe_credits_ab(username, kosten, grund="Agenten-Nutzung"):
    if username != ADMIN_NAME:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE kunden SET guthaben = MAX(0.0, guthaben - ?) WHERE username = ?", (kosten, username))
        cursor.execute("INSERT INTO guthaben_historie (zeit, username, typ, betrag, grund) VALUES (datetime('now', 'localtime'), ?, 'Abzug', ?, ?)",
                       (username, kosten, grund))
        conn.commit()
        conn.close()
    st.session_state.session_verrauchter_betrag += kosten

def guthaben_gutschreiben(username, betrag, grund="Admin-Gutschrift"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE kunden SET guthaben = guthaben + ? WHERE username = ?", (betrag, username))
    cursor.execute("INSERT INTO guthaben_historie (zeit, username, typ, betrag, grund) VALUES (datetime('now', 'localtime'), ?, 'Gutschrift', ?, ?)",
                   (username, betrag, grund))
    conn.commit()
    conn.close()

def guthaben_einziehen(username, betrag, grund="Admin-Einzug"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE kunden SET guthaben = MAX(0.0, guthaben - ?) WHERE username = ?", (betrag, username))
    cursor.execute("INSERT INTO guthaben_historie (zeit, username, typ, betrag, grund) VALUES (datetime('now', 'localtime'), ?, 'Abzug', ?, ?)",
                   (username, betrag, grund))
    conn.commit()
    conn.close()

if "aktueller_user" not in st.session_state:
    st.session_state.aktueller_user = None

if "slides_data" not in st.session_state:
    st.session_state.slides_data = [
        {"titel": "Folie 1: Willkommen", "text": "Hier steht der Text für Folie 1...", "prompt": "Professional corporate presentation slide background, modern clean style", "bild_url": None}
    ]

if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "aktiver_chat" not in st.session_state:
    st.session_state.aktiver_chat = "Chat 1"

with st.sidebar:
    eingeloggter_kunde = st.session_state.get("aktueller_user", None)

    if not eingeloggter_kunde:
        st.header("🔑 Enterprise Login & RBAC")
        auth_modus = st.radio("Aktion wählen:", ["Einloggen", "Neuen Account erstellen"], label_visibility="collapsed")
        
        if auth_modus == "Einloggen":
            login_name = st.text_input("Benutzername:")
            login_pass = st.text_input("Passwort:", type="password")
            
            if st.button("Anmelden"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT passwort FROM kunden WHERE username = ?", (login_name,))
                res = cursor.fetchone()
                conn.close()
                
                if res and res[0] == login_pass:
                    st.session_state.aktueller_user = login_name
                    st.success(f"Willkommen zurück, {login_name}!")
                    st.rerun()
                else:
                    st.error("Falscher Benutzername oder Passwort.")
        else:
            reg_name = st.text_input("Neuer Benutzername:")
            reg_pass = st.text_input("Neues Passwort:", type="password")
            reg_rolle = st.selectbox("Unternehmens-Rolle (RBAC):", ["Vertriebsleiter", "Support-Agent", "Externer Partner", "Analyst"])
            reg_workspace = st.text_input("Workspace Name:", value="Department-Hub")
            
            if st.button("Account registrieren"):
                if not reg_name or not reg_pass:
                    st.warning("Bitte fülle alle Pflichtfelder aus.")
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM kunden WHERE username = ?", (reg_name,))
                    if cursor.fetchone():
                        st.error("Dieser Benutzername ist bereits vergeben.")
                    else:
                        cursor.execute("INSERT INTO kunden VALUES (?, ?, ?, ?, ?)", (reg_name, reg_pass, 0.0, reg_rolle, reg_workspace))
                        conn.commit()
                        st.session_state.aktueller_user = reg_name
                        st.success("Account & Workspace erstellt!")
                        st.rerun()
                    conn.close()
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT guthaben, rolle, workspace FROM kunden WHERE username = ?", (eingeloggter_kunde,))
        row = cursor.fetchone()
        conn.close()
        guthaben, rolle, workspace = row if row else (0.0, "Standard", "Default")

        st.markdown(f"### 👤 {eingeloggter_kunde}")
        st.caption(f"🛡️ Rolle: **{rolle}**\n\n🏢 Workspace: `{workspace}`")
        st.caption(f"💰 Guthaben: **{guthaben:.2f} €**")
        st.caption(f"⚡ Session-Verbrauch: **{st.session_state.session_verrauchter_betrag:.3f} €**")
        
        with st.expander("💳 Guthaben mit Einmal-Key aufladen", expanded=False):
            key_input = st.text_input("Lizenzschlüssel eingeben:", type="password", placeholder="SCION-KEY-...")
            if st.button("Schlüssel einlösen"):
                if key_input:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, betrag, status FROM lizenz_schluessel WHERE schluessel = ?", (key_input,))
                    key_row = cursor.fetchone()
                    
                    if key_row:
                        kid, kbetrag, kstatus = key_row
                        if kstatus == "Unbenutzt":
                            cursor.execute("UPDATE lizenz_schluessel SET status = 'Eingelöst', eingeloest_von = ? WHERE id = ?", (eingeloggter_kunde, kid))
                            conn.commit()
                            conn.close()
                            guthaben_gutschreiben(eingeloggter_kunde, kbetrag, grund=f"Lizenzschlüssel eingelöst ({key_input})")
                            st.success(f"Erfolgreich! {kbetrag:.2f} € gutgeschrieben.")
                            st.rerun()
                        else:
                            conn.close()
                            st.error("Schlüssel bereits verwendet.")
                    else:
                        conn.close()
                        st.error("Unbekannter Schlüssel.")

        if eingeloggter_kunde == ADMIN_NAME:
            with st.expander("👑 Admin-Zentrale", expanded=True):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT username, guthaben FROM kunden")
                user_Rows = cursor.fetchall()
                conn.close()
                user_dict = {f"{u[0]} (Guthaben: {u[1]:.2f} €)": u[0] for u in user_Rows} if user_Rows else {}
                if user_dict:
                    ausgewaehlte_anzeige = st.selectbox("Account wählen:", list(user_dict.keys()))
                    ausgewaehlter_user = user_dict[ausgewaehlte_anzeige]
                    betrag_input = st.number_input("Betrag in €:", value=1.00, step=0.50)
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        if st.button("➕ Gutschreiben"):
                            guthaben_gutschreiben(ausgewaehlter_user, betrag_input)
                            st.rerun()
                    with col_a2:
                        if st.button("➖ Einziehen"):
                            guthaben_einziehen(ausgewaehlter_user, betrag_input)
                            st.rerun()

        st.write("---")
        st.markdown("### 💬 Deine Chats")
        if st.button("➕ Neuer Chat"):
            neuer_name = f"Chat {len(st.session_state.chats) + 1}"
            st.session_state.chats[neuer_name] = []
            st.session_state.aktiver_chat = neuer_name
            st.rerun()

        for chat_name in list(st.session_state.chats.keys()):
            if st.button(chat_name, key=f"btn_{chat_name}"):
                st.session_state.aktiver_chat = chat_name
                st.rerun()

        st.write("---")
        if st.button("Abmelden"):
            st.session_state.aktueller_user = None
            st.rerun()

if not eingeloggter_kunde:
    st.warning("👈 Bitte melde dich links an oder registriere dich.")
else:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT guthaben, rolle, workspace FROM kunden WHERE username = ?", (eingeloggter_kunde,))
    row = cursor.fetchone()
    conn.close()
    guthaben, rolle, workspace = row if row else (0.0, "Standard", "Default")

    if eingeloggter_kunde != ADMIN_NAME and guthaben <= 0.0:
        st.error("🛑 **PAYWALL AKTIV:** Dein Guthaben ist aufgebraucht (0.00 €). Bitte löse einen Einmal-Lizenzschlüssel ein.")
    else:
        spalte_links, spalte_rechts = st.columns([1.1, 0.9])

        with spalte_links:
            st.subheader("🤖 Autonomer KI-Agent (GOD-MODE V12.17)")
            modus = st.selectbox(
                "Agenten-Modus wählen:",
                [
                    "Intelligenter Chat & Live-Webrecherche", 
                    "📊 Analytics & P&L Break-Even Rechner",
                    "📊 Konkurrenten SWOT-Analyzer",
                    "🛠️ Closed-Loop Self-Healing Sandbox (REPL)",
                    "📚 Vektor-DB & RAG (Wissens-Archiv)",
                    "🟢 Lokaler Ollama Fallback (Zero-Cloud)"
                ]
            )
            
            current_chat = st.session_state.aktiver_chat
            
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            aufgabe = st.chat_input("Gib dem Agenten eine Aufgabe...")
            if aufgabe:
                berechne_und_ziehe_credits_ab(eingeloggter_kunde, 0.005, grund="Agenten-Aktion")
                st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                with st.chat_message("user"):
                    st.markdown(aufgabe)

                with st.spinner("🤖 Agent arbeitet..."):
                    if "Break-Even" in modus:
                        antwort = berechne_pl_break_even(15000.0, 150.0, 50.0)
                    elif "SWOT" in modus:
                        antwort = starte_swot_analyse(aufgabe, TAVILY_API_KEY, MASTER_OPENAI_KEY, ANTHROPIC_API_KEY)
                    elif "Sandbox" in modus:
                        antwort = ausfuehren_in_self_healing_sandbox(aufgabe, MASTER_OPENAI_KEY)
                    elif "RAG" in modus:
                        antwort = suche_in_rag_vektor_db(aufgabe, MASTER_OPENAI_KEY)
                    elif "Ollama" in modus:
                        antwort = ausfuehren_mit_ollama_fallback("Du bist ein Assistent.", aufgabe, use_local=True, master_openai_key=MASTER_OPENAI_KEY, anthropic_api_key=ANTHROPIC_API_KEY)
                    else:
                        antwort = selbstevaluierender_lern_agent(f"Du bist Assistent für {eingeloggter_kunde}.", aufgabe, use_local=False, master_openai_key=MASTER_OPENAI_KEY, anthropic_api_key=ANTHROPIC_API_KEY)

                st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                with st.chat_message("assistant"):
                    st.markdown(antwort)

        with spalte_rechts:
            with st.expander("📊 Präsentations- & Export-Studio", expanded=True):
                export_titel = st.text_input("Dokumenten-Titel:", value="Scion_Mind_Ausarbeitung")
                aktueller_export_text = st.session_state.chats[current_chat][-1]["content"] if st.session_state.chats[current_chat] else "Kein Text"
                
                ex_col1, ex_col2 = st.columns(2)
                with ex_col1:
                    pdf_data = exportiere_zu_pdf(export_titel, aktueller_export_text, workspace)
                    st.download_button("📥 Als PDF", data=pdf_data, file_name=f"{export_titel}.pdf", mime="application/pdf", use_container_width=True)
                with ex_col2:
                    docx_data = exportiere_zu_docx(export_titel, aktueller_export_text, workspace)
                    if docx_data:
                        st.download_button("📥 Als Word (.docx)", data=docx_data, file_name=f"{export_titel}.docx", use_container_width=True)