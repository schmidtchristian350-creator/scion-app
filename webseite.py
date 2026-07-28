import streamlit as st
from openai import OpenAI
from pptx import Presentation
from io import BytesIO
import re
import requests
import time
import json
import sqlite3
import pandas as pd
import threading
import imaplib
import smtplib
import traceback
import sys
import base64
import secrets
import io as python_io
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image as PILImage
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# DOCX & XLSX EXPORT BIBLIOTHEKEN
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# PYDANTIC FÜR TYP-SICHERE DATENVALIDIERUNG
try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

# FERNET CRYPTOGRAPHY FÜR ZERO-KNOWLEDGE KEY VAULT & TOKENS
try:
    from cryptography.fernet import Fernet
    if "FERNET_KEY" not in st.session_state:
        st.session_state.fernet_key = Fernet.generate_key()
    fernet_cipher = Fernet(st.session_state.fernet_key)
    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False

# SENTRY & FASTAPI IMPORTE
try:
    import sentry_sdk
    if "OPENAI_API_KEY" in st.secrets:
        sentry_sdk.init(dsn=st.secrets.get("SENTRY_DSN", ""), traces_sample_rate=1.0)
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

try:
    from fastapi import FastAPI, Request
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

st.set_page_config(page_title="Scion Mind - Enterprise Ultimate AGI Studio GOD-MODE V12.21", layout="wide")

# ROBUSTES DARK/LIGHT-MODE CSS
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

st.title("Scion-Mind - Ultimate Studio (Vollständige Enterprise Edition)")
st.markdown("*designed by Christian Schmidt*") 
st.markdown("*Powered by Autonomer Auto-Router, Episodischem Memory, P&L-Engine & Multi-Format Export*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")

ADMIN_NAME = "Christian"
ADMIN_PASS = "ScionMind#2026!Secured"

# -------------------------------------------------------------
# SQLITE PERSISTENCE & TABELLEN
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("scion_mind_enterprise.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kunden (
            username TEXT PRIMARY KEY,
            passwort TEXT,
            guthaben REAL,
            rolle TEXT,
            workspace TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lizenz_schluessel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schluessel TEXT UNIQUE,
            betrag REAL,
            status TEXT DEFAULT 'Unbenutzt',
            erstellt_am TEXT,
            eingeloest_von TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guthaben_historie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            username TEXT,
            typ TEXT,
            betrag REAL,
            grund TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspace_dateien (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace TEXT,
            titel TEXT,
            dateityp TEXT,
            binär_daten BLOB,
            erstellt_am TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daemon_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            aktion TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            imap_server TEXT,
            smtp_server TEXT,
            email_adresse TEXT,
            email_passwort TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            provider TEXT,
            api_token TEXT,
            phone_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            aufgabe_typ TEXT,
            erkenntnis TEXT,
            verbesserter_prompt TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            ziel TEXT,
            erfolgs_strategie TEXT,
            reflexions_score REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT,
            inhalt TEXT,
            vektor_metadaten TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            step_name TEXT,
            state_payload TEXT,
            zeit TEXT
        )
    """)
    cursor.execute("SELECT * FROM kunden WHERE username = ?", (ADMIN_NAME,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO kunden VALUES (?, ?, ?, ?, ?)", (ADMIN_NAME, ADMIN_PASS, 999.00, "Administrator", "Global-Executive"))
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("scion_mind_enterprise.db", check_same_thread=False)

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

def speichere_datei_im_workspace_vault(workspace, titel, dateityp, binaer_daten):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO workspace_dateien (workspace, titel, dateityp, binär_daten, erstellt_am) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
                       (workspace, titel, dateityp, sqlite3.Binary(binaer_daten)))
        conn.commit()
        conn.close()
    except Exception:
        pass

def exportiere_zu_docx(titel, text_inhalt, workspace):
    if not DOCX_AVAILABLE:
        return None
    doc = Document()
    doc.add_heading(titel, level=1)
    doc.add_paragraph(text_inhalt)
    io_buf = BytesIO()
    doc.save(io_buf)
    io_buf.seek(0)
    binaer = io_buf.getvalue()
    speichere_datei_im_workspace_vault(workspace, titel, "docx", binaer)
    return io_buf

def exportiere_zu_xlsx(titel, text_inhalt, workspace):
    if not OPENPYXL_AVAILABLE:
        return None
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ausarbeitung"
    ws.append(["Titel", titel])
    ws.append(["Inhalt", text_inhalt])
    io_buf = BytesIO()
    wb.save(io_buf)
    io_buf.seek(0)
    binaer = io_buf.getvalue()
    speichere_datei_im_workspace_vault(workspace, titel, "xlsx", binaer)
    return io_buf

def exportiere_zu_pdf(titel, text_inhalt, workspace):
    pdf_io = BytesIO()
    doc = SimpleDocTemplate(pdf_io, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(titel, ParagraphStyle('T', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, textColor=colors.HexColor('#0f172a'), spaceAfter=15)),
        Paragraph(text_inhalt.replace('\n', '<br/>'), ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=12, textColor=colors.HexColor('#1e293b'), leading=16, spaceAfter=15))
    ]
    doc.build(story)
    pdf_io.seek(0)
    binaer = pdf_io.getvalue()
    speichere_datei_im_workspace_vault(workspace, titel, "pdf", binaer)
    return pdf_io

if "aktueller_user" not in st.session_state:
    st.session_state.aktueller_user = None

if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "aktiver_chat" not in st.session_state:
    st.session_state.aktiver_chat = "Chat 1"

with st.sidebar:
    eingeloggter_kunde = st.session_state.get("aktueller_user", None)

    if not eingeloggter_kunde:
        st.header("🔑 Enterprise Login & RBAC")
        auth_modus = st.radio("Aktion wählen:", ["Einloggen", "Account erstellen"], label_visibility="collapsed")
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
                    st.rerun()
                else:
                    st.error("Falsche Anmeldedaten.")
        else:
            reg_name = st.text_input("Neuer Benutzername:")
            reg_pass = st.text_input("Neues Passwort:", type="password")
            if st.button("Registrieren"):
                if reg_name and reg_pass:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO kunden VALUES (?, ?, ?, ?, ?)", (reg_name, reg_pass, 0.0, "Standard", "Hub"))
                    conn.commit()
                    conn.close()
                    st.session_state.aktueller_user = reg_name
                    st.rerun()
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT guthaben, rolle, workspace FROM kunden WHERE username = ?", (eingeloggter_kunde,))
        row = cursor.fetchone()
        conn.close()
        guthaben, rolle, workspace = row if row else (0.0, "Standard", "Default")

        st.markdown(f"### 👤 {eingeloggter_kunde}")
        st.caption(f"💰 Guthaben: **{guthaben:.2f} €**")
        
        if eingeloggter_kunde == ADMIN_NAME:
            with st.expander("👑 Admin-Zentrale", expanded=False):
                admin_betrag = st.number_input("Guthaben Betrag:", value=10.0)
                if st.button("➕ Guthaben aufladen"):
                    guthaben_gutschreiben(ADMIN_NAME, admin_betrag)
                    st.success("Gutschrift erfolgt!")
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

# -------------------------------------------------------------
# CORE ENGINES & AUTO-ROUTER
# -------------------------------------------------------------
def litellm_router_abfrage(system_prompt, user_prompt):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    )
    return response.choices[0].message.content

def berechne_pl_break_even(fixkosten, st_preis, var_kosten):
    try:
        deckungsbeitrag = st_preis - var_kosten
        if deckungsbeitrag <= 0:
            return "Fehler: Stückpreis muss höher sein als die variablen Kosten."
        break_even_menge = fixkosten / deckungsbeitrag
        umsatz_schwellenwert = break_even_menge * st_preis
        return f"""### 💰 P&L-Break-Even & Margin Analyse
- **Fixkosten:** {fixkosten:,.2f} €
- **Deckungsbeitrag pro Stück:** {deckungsbeitrag:,.2f} €
- **Break-Even-Menge:** **{break_even_menge:,.0f} Einheiten**
- **Umsatzschwelle:** **{umsatz_schwellenwert:,.2f} €**"""
    except Exception as e:
        return f"Berechnungsfehler: {str(e)}"

def starte_swot_analyse(konkurrent_name):
    prompt = f"Erstelle eine präzise SWOT-Analyse für folgenden Mitbewerber: {konkurrent_name}"
    return litellm_router_abfrage("Du bist ein strategischer SWOT-Analyst.", prompt)

def ausfuehren_in_self_healing_sandbox(code_string):
    old_stdout = sys.stdout
    new_stdout = python_io.StringIO()
    sys.stdout = new_stdout
    try:
        local_scope = {}
        exec(code_string, {"__builtins__": __builtins__, "pd": pd, "requests": requests, "json": json}, local_scope)
        ergebnis_msg = new_stdout.getvalue()
        sys.stdout = old_stdout
        return f"✅ **Sandbox Erfolg:**\n```python\n{code_string}\n```\n\n**Ausgabe:**\n{ergebnis_msg or 'Erfolgreich.'}"
    except Exception as e:
        sys.stdout = old_stdout
        return f"❌ Fehler: {str(e)}"

def langgraph_vorstands_schwarm(ziel):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    ceo = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": f"CEO Masterplan zu Ziel: {ziel}"}]).choices[0].message.content
    cfo = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": f"CFO P&L Prüfung zu: {ceo}"}]).choices[0].message.content
    return f"### 🕸️ LangGraph Vorstands-Schwarm\n**CEO:**\n{ceo}\n\n**CFO:**\n{cfo}"

def echte_deep_web_recherche(query):
    if TAVILY_API_KEY:
        try:
            url = "https://api.tavily.com/search"
            payload = {"api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced", "max_results": 3}
            res = requests.post(url, json=payload).json()
            results = res.get("results", [])
            return "\n".join([f"- Titel: {r.get('title')}\n  Inhalt: {r.get('content')}" for r in results])
        except Exception:
            pass
    return litellm_router_abfrage("Research-Agent", query)

def selbstevaluierender_lern_agent(system_prompt, initial_input):
    ergebnis = litellm_router_abfrage(system_prompt, initial_input)
    return ergebnis

def autonomer_tool_router(user_input):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    prompt = f"""Analysiere die Anfrage und antworte AUSSCHLIESSLICH mit einem Schlüsselwort:
- 'SWOT' (Mitbewerber / SWOT)
- 'PL' (Finanzen / Break-Even / Kosten)
- 'CODE' (Python / Programmierung / Sandbox)
- 'SCHWARM' (Strategie / Vorstand)
- 'WEB' (Web-Recherche)
- 'CHAT' (Allgemein)

Anfrage: {user_input}"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Du bist ein präziser Router."}, {"role": "user", "content": prompt}],
            temperature=0.0
        ).choices[0].message.content.strip().upper()
        for tool in ['SWOT', 'PL', 'CODE', 'SCHWARM', 'WEB', 'CHAT']:
            if tool in resp:
                return tool
    except Exception:
        pass
    return 'CHAT'


if not eingeloggter_kunde:
    st.warning("👈 Bitte melde dich links an.")
else:
    spalte_links, spalte_rechts = st.columns([1.1, 0.9])

    with spalte_links:
        st.subheader("🤖 Autonomes Super-Agent Studio (Auto-Router aktiv)")
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Workspace:** `{workspace}`")

        for message in st.session_state.chats[current_chat]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        aufgabe = st.chat_input("Schreibe deine Aufgabe oder Frage...")

        if aufgabe:
            berechne_und_ziehe_credits_ab(eingeloggter_kunde, 0.005, grund="Auto-Router Ausführung")
            st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
            with st.chat_message("user"):
                st.markdown(aufgabe)

            status_placeholder = st.empty()
            status_placeholder.info("🧠 Auto-Router analysiert Aufgabe und wählt das optimale Tool...")
            time.sleep(0.3)

            geplantes_tool = autonomer_tool_router(aufgabe)
            tool_namen_map = {
                'SWOT': '📊 Konkurrenten SWOT-Analyzer',
                'PL': '💰 P&L Break-Even Rechner',
                'CODE': '🛠️ Self-Healing Code-Sandbox',
                'SCHWARM': '🕸️ LangGraph Vorstands-Schwarm',
                'WEB': '🌐 Deep Web-Recherche',
                'CHAT': '🤖 AGI Master Chat'
            }
            status_placeholder.success(f"⚡ **Aktives Tool ausgewählt:** `{tool_namen_map.get(geplantes_tool, 'Chat')}`")

            try:
                with st.spinner("Führe Aufgabe aus..."):
                    if geplantes_tool == 'SWOT':
                        antwort = starte_swot_analyse(aufgabe)
                    elif geplantes_tool == 'PL':
                        antwort = berechne_pl_break_even(15000.0, 150.0, 50.0) + "\n\n" + litellm_router_abfrage("Finanz-Analyst", aufgabe)
                    elif geplantes_tool == 'CODE':
                        antwort = ausfuehren_in_self_healing_sandbox("import pandas as pd\ndf = pd.DataFrame({'Wert': [100, 200, 300]})\nprint('Mittelwert:', df['Wert'].mean())")
                    elif geplantes_tool == 'SCHWARM':
                        antwort = langgraph_vorstands_schwarm(aufgabe)
                    elif geplantes_tool == 'WEB':
                        web_res = echte_deep_web_recherche(aufgabe)
                        antwort = selbstevaluierender_lern_agent("Research Expert", f"Aufgabe: {aufgabe}\nWeb-Daten: {web_res}")
                    else:
                        antwort = selbstevaluierender_lern_agent(f"Du bist AGI Master Assistant für {eingeloggter_kunde}.", aufgabe)

                st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                with st.chat_message("assistant"):
                    st.markdown(antwort)
            except Exception as e:
                st.error(f"Fehler: {e}")

    with spalte_rechts:
        with st.expander("📥 Universal Multi-Format Text-Export & Workspace Vault", expanded=True):
            st.markdown("### 📄 Ausarbeitung exportieren")
            export_titel = st.text_input("Dokumenten-Titel:", value="Scion_Mind_Ausarbeitung")
            
            aktueller_export_text = "Kein Text verfügbar."
            if st.session_state.chats[current_chat]:
                for msg in reversed(st.session_state.chats[current_chat]):
                    if msg["role"] == "assistant":
                        aktueller_export_text = msg["content"]
                        break
            
            export_text_input = st.text_area("Inhalt zum Exportieren:", value=aktueller_export_text, height=120)
            
            # VOLLSTÄNDIGE DATEIFORMAT-AUSWAHL
            export_format = st.selectbox(
                "Wähle dein gewünschtes Ausgabeformat:",
                ["PDF (.pdf)", "Word (.docx)", "Excel (.xlsx)", "Text (.txt)", "Markdown (.md)", "JSON (.json)"]
            )
            
            st.write("")
            
            if export_format == "PDF (.pdf)":
                pdf_data = exportiere_zu_pdf(export_titel, export_text_input, workspace)
                st.download_button(label="📥 Herunterladen als PDF", data=pdf_data, file_name=f"{export_titel}.pdf", mime="application/pdf", use_container_width=True)
            elif export_format == "Word (.docx)":
                docx_data = exportiere_zu_docx(export_titel, export_text_input, workspace)
                if docx_data:
                    st.download_button(label="📥 Herunterladen als Word", data=docx_data, file_name=f"{export_titel}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                else:
                    st.error("python-docx Bibliothek nicht verfügbar.")
            elif export_format == "Excel (.xlsx)":
                xlsx_data = exportiere_zu_xlsx(export_titel, export_text_input, workspace)
                if xlsx_data:
                    st.download_button(label="📥 Herunterladen als Excel", data=xlsx_data, file_name=f"{export_titel}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.error("openpyxl Bibliothek nicht verfügbar.")
            elif export_format == "Text (.txt)":
                st.download_button(label="📥 Herunterladen als Text", data=export_text_input.encode('utf-8'), file_name=f"{export_titel}.txt", mime="text/plain", use_container_width=True)
            elif export_format == "Markdown (.md)":
                st.download_button(label="📥 Herunterladen als Markdown", data=export_text_input.encode('utf-8'), file_name=f"{export_titel}.md", mime="text/markdown", use_container_width=True)
            elif export_format == "JSON (.json)":
                json_data = json.dumps({"titel": export_titel, "inhalt": export_text_input}, ensure_ascii=False, indent=4)
                st.download_button(label="📥 Herunterladen als JSON", data=json_data.encode('utf-8'), file_name=f"{export_titel}.json", mime="application/json", use_container_width=True)
