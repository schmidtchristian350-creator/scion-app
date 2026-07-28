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

# Playwright optional
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

st.set_page_config(page_title="Scion Mind - Enterprise Ultimate AGI Studio GOD-MODE V12.19", layout="wide")

# ROBUSTES DARK/LIGHT-MODE CSS (GARANTIERT LESBARE SCHRIFTEN)
st.markdown("""
    <style>
    .stApp { background-color: var(--background-color); color: var(--text-color); }
    [data-testid="stSidebar"] { background-color: #1e293b; color: #ffffff !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #ffffff !important; }
    .stButton button { background-color: #0f172a; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%; }
    .stButton button:hover { background-color: #334155; color: white; }
    input, textarea, [data-baseweb="input"] div, [data-baseweb="base-input"] { border-radius: 8px !important; }
    [data-testid="stStatusWidget"] svg, [data-testid="stSpinner"] svg {
        width: 40px !important;
        height: 40px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Scion-Mind - Ultimate Studio (Intelligentes Auto-Routing)")
st.markdown("*designed by Christian Schmidt*") 
st.markdown("*Powered by Autonomer Tool-Selector, Episodischem Memory, Formeller Verifikation & Self-Coding*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
IMAGE_API_KEY = st.secrets.get("VIDEO_API_KEY", MASTER_OPENAI_KEY)
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

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
    cursor.execute("PRAGMA table_info(kunden)")
    columns = [col[1] for col in cursor.fetchall()]
    if "rolle" not in columns:
        cursor.execute("ALTER TABLE kunden ADD COLUMN rolle TEXT DEFAULT 'Standard'")
    if "workspace" not in columns:
        cursor.execute("ALTER TABLE kunden ADD COLUMN workspace TEXT DEFAULT 'Default-Hub'")

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
        CREATE TABLE IF NOT EXISTS mcp_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name TEXT,
            resource_uri TEXT,
            status TEXT
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
        CREATE TABLE IF NOT EXISTS event_webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            kanal TEXT,
            nachricht TEXT,
            ki_reaktion TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS async_task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            agent_typ TEXT,
            task_ziel TEXT,
            status TEXT,
            ergebnis TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspace_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace TEXT,
            service_name TEXT,
            encrypted_key TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT UNIQUE,
            beschreibung TEXT,
            python_code TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            metrik_typ TEXT,
            wert REAL,
            details TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lead_gen_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            firma TEXT,
            geschaeftsfuehrer TEXT,
            website TEXT,
            design_status TEXT,
            akquise_mail TEXT
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
    else:
        cursor.execute("UPDATE kunden SET rolle = ?, workspace = ? WHERE username = ?", ("Administrator", "Global-Executive", ADMIN_NAME))

    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("scion_mind_enterprise.db", check_same_thread=False)

# -------------------------------------------------------------
# WERTBASIERTE CREDIT-ABBUCHUNG & AUDIT-TRAIL
# -------------------------------------------------------------
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

def speichere_datei_im_workspace_vault(workspace, titel, dateityp, binaer_daten):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO workspace_dateien (workspace, titel, dateityp, binär_daten, erstellt_am) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
                       (workspace, titel, dateityp, sqlite3.Binary(binaer_daten)))
        conn.commit()
        conn.close()
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)

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

# -------------------------------------------------------------
# FASTAPI MICROSERVICE FÜR ECHTE WEBHOOKS (PORT 8000)
# -------------------------------------------------------------
if FASTAPI_AVAILABLE:
    app_fastapi = FastAPI(title="Scion Mind Webhook Gateway")

    @app_fastapi.post("/webhook/inbound")
    async def receive_webhook(request: Request):
        try:
            body = await request.json()
            kanal = body.get("kanal", "Generic-API")
            nachricht = body.get("nachricht", str(body))
            
            client_wh = OpenAI(api_key=MASTER_OPENAI_KEY)
            ki_ant = client_wh.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Du bist ein automatischer Webhook-Responder."}, {"role": "user", "content": nachricht}]
            ).choices[0].message.content

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO event_webhooks (zeit, kanal, nachricht, ki_reaktion) VALUES (datetime('now', 'localtime'), ?, ?, ?)",
                           (kanal, nachricht, ki_ant))
            conn.commit()
            conn.close()
            return {"status": "success", "ki_reaktion": ki_ant}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_fastapi_server():
        try:
            uvicorn.run(app_fastapi, host="127.0.0.1", port=8000, log_level="warning")
        except Exception:
            pass

if "fastapi_started" not in st.session_state and FASTAPI_AVAILABLE:
    st.session_state.fastapi_started = True
    threading.Thread(target=run_fastapi_server, daemon=True).start()

# -------------------------------------------------------------
# PROAKTIVER DAEMON
# -------------------------------------------------------------
def background_daemon_worker():
    executor = ThreadPoolExecutor(max_workers=3)
    def process_task(tid, atyp, tziel):
        try:
            t0 = time.time()
            client_bg = OpenAI(api_key=MASTER_OPENAI_KEY)
            resp = client_bg.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": f"Du bist ein autonomer Hintergrund-Agent vom Typ {atyp}."}, {"role": "user", "content": tziel}]
            ).choices[0].message.content
            t_duration = time.time() - t0

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE async_task_queue SET status = 'Erfolgreich', ergebnis = ? WHERE id = ?", (resp, tid))
            cursor.execute("INSERT INTO telemetry_logs (zeit, metrik_typ, wert, details) VALUES (datetime('now', 'localtime'), 'API_Latency', ?, ?)", (t_duration, f"Task {atyp}"))
            cursor.execute("INSERT INTO daemon_logs (zeit, aktion, status) VALUES (datetime('now', 'localtime'), ?, 'Task erfolgreich abgeschlossen')", (f"Async-Task [{atyp}]",))
            conn.commit()
            conn.close()
        except Exception as e:
            if SENTRY_AVAILABLE:
                sentry_sdk.capture_exception(e)

    while True:
        time.sleep(15)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, agent_typ, task_ziel FROM async_task_queue WHERE status = 'Offen' LIMIT 3")
            tasks = cursor.fetchall()
            if tasks:
                for tid, atyp, tziel in tasks:
                    cursor.execute("UPDATE async_task_queue SET status = 'In Bearbeitung' WHERE id = ?", (tid,))
                    conn.commit()
                    executor.submit(process_task, tid, atyp, tziel)
            else:
                cursor.execute("INSERT INTO daemon_logs (zeit, aktion, status) VALUES (datetime('now', 'localtime'), 'Proaktiver Autonomous Daemon Loop', 'Aktiv & Wachsam')")
                conn.commit()
            conn.close()
        except Exception as e:
            if SENTRY_AVAILABLE:
                sentry_sdk.capture_exception(e)

if "daemon_started" not in st.session_state:
    st.session_state.daemon_started = True
    threading.Thread(target=background_daemon_worker, daemon=True).start()

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
                        st.success("Account & Workspace erstellt! (Startguthaben: 0.00 €)")
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
                            st.success(f"Erfolgreich! {kbetrag:.2f} € wurden deinem Konto gutgeschrieben.")
                            st.rerun()
                        else:
                            conn.close()
                            st.error("Dieser Lizenzschlüssel wurde bereits verwendet.")
                    else:
                        conn.close()
                        st.error("Unbekannter Lizenzschlüssel.")

        if eingeloggter_kunde == ADMIN_NAME:
            with st.expander("👑 Admin-Zentrale (Guthaben & Audit)", expanded=True):
                st.markdown("#### Nutzer auswählen:")
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT username, guthaben FROM kunden")
                user_Rows = cursor.fetchall()
                conn.close()
                
                user_dict = {f"{u[0]} (Guthaben: {u[1]:.2f} €)": u[0] for u in user_Rows} if user_Rows else {}
                anzeige_liste = list(user_dict.keys())
                
                if anzeige_liste:
                    ausgewaehlte_anzeige = st.selectbox("Account wählen:", anzeige_liste, key="admin_user_select")
                    ausgewaehlter_user = user_dict[ausgewaehlte_anzeige]
                    betrag_input = st.number_input("Betrag in €:", value=1.00, step=0.50, key="admin_betrag_input")
                    
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        if st.button("➕ Gutschreiben", key="btn_admin_plus"):
                            if ausgewaehlter_user:
                                guthaben_gutschreiben(ausgewaehlter_user, betrag_input, grund="Admin-Zentrale Gutschrift")
                                st.success(f"Gutgeschrieben: +{betrag_input:.2f} €")
                                time.sleep(0.3)
                                st.rerun()
                    with col_a2:
                        if st.button("➖ Einziehen", key="btn_admin_minus"):
                            if ausgewaehlter_user:
                                guthaben_einziehen(ausgewaehlter_user, betrag_input, grund="Admin-Zentrale Einzug")
                                st.warning(f"Eingezogen: -{betrag_input:.2f} €")
                                time.sleep(0.3)
                                st.rerun()

                st.write("---")
                if st.button("Audit-Historie anzeigen"):
                    conn = get_db_connection()
                    df_audit = pd.read_sql_query("SELECT * FROM guthaben_historie ORDER BY id DESC LIMIT 10", conn)
                    conn.close()
                    st.dataframe(df_audit)

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
# CORE ENGINES V12.19 (INKL. AUTONOMEM TOOL-ROUTER)
# -------------------------------------------------------------

def verschruessle_api_key(api_key):
    if FERNET_AVAILABLE:
        try:
            return fernet_cipher.encrypt(api_key.encode('utf-8')).decode('utf-8')
        except Exception:
            pass
    return base64.b64encode(api_key.encode('utf-8')).decode('utf-8')

def litellm_router_abfrage(system_prompt, user_prompt, model_pref="auto"):
    try:
        if model_pref == "local" or (model_pref == "auto" and len(user_prompt) < 100):
            url = "http://localhost:11434/api/generate"
            payload = {"model": "llama3", "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}", "stream": False}
            res = requests.post(url, json=payload, timeout=4).json()
            if "response" in res:
                return f"🟢 [LiteLLM Router -> Lokal Llama 3]: \n{res['response']}"
    except Exception:
        pass

    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    )
    return f"🔵 [LiteLLM Router -> OpenAI GPT-4o-mini]:\n" + response.choices[0].message.content

def ausfuehren_mit_ollama_fallback(system_prompt, user_prompt, use_local=False):
    pref = "local" if use_local else "auto"
    return litellm_router_abfrage(system_prompt, user_prompt, model_pref=pref)

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
    web_daten = echte_deep_web_recherche(f"{konkurrent_name} Unternehmensprofil Angebote Marktposition")
    prompt = f"Erstelle eine präzise SWOT-Analyse für folgenden Mitbewerber basierend auf den Webdaten:\n{web_daten}"
    return litellm_router_abfrage("Du bist ein strategischer SWOT-Analyst.", prompt, model_pref="auto")

def speichere_checkpoint(session_id, step_name, state_dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_checkpoints (session_id, step_name, state_payload, zeit) VALUES (?, ?, ?, datetime('now', 'localtime'))",
                       (session_id, step_name, json.dumps(state_dict)))
        conn.commit()
        conn.close()
    except Exception:
        pass

def formale_verifikation_pruefen(ziel, ergebnis):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    try:
        val_prompt = f"Prüfe streng, ob dieses Ergebnis das Ziel erfüllt.\nZiel: {ziel}\nErgebnis: {ergebnis}\nAntworte mit 'VALIDIERT: [Grund]' oder 'FEHLER: [Grund]'."
        check_res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Du bist ein strenger Logik-Prüfer."}, {"role": "user", "content": val_prompt}]
        ).choices[0].message.content
        return check_res
    except Exception as e:
        return f"Verifikations-Fehler: {str(e)}"

def langgraph_vorstands_schwarm(ziel):
    session_id = f"session_{int(time.time())}"
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    state = {"ziel": ziel, "iteration": 1, "ceo": "", "cfo": "", "cto": "", "sales": ""}
    try:
        speichere_checkpoint(session_id, "Start", state)
        for step in range(2):
            state["ceo"] = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": f"CEO Ziel: {ziel}"}]).choices[0].message.content
            state["cfo"] = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": f"CFO Budget-Prüfung zu: {state['ceo']}"}]).choices[0].message.content
            state["iteration"] += 1
            speichere_checkpoint(session_id, f"Iteration_{state['iteration']}", state)
        konsens = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": f"Führe zusammen: CEO: {state['ceo']}, CFO: {state['cfo']}"}]).choices[0].message.content
        verifikation = formale_verifikation_pruefen(ziel, konsens)
        return f"### 🕸️ LangGraph Vorstands-Schwarm Konsens\n{konsens}\n\n**Verifikation:**\n{verifikation}"
    except Exception as e:
        return f"Schwarm-Fehler: {str(e)}"

def ausfuehren_in_self_healing_sandbox(code_string):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    aktueller_code = code_string
    for versuch in range(3):
        old_stdout = sys.stdout
        new_stdout = python_io.StringIO()
        sys.stdout = new_stdout
        try:
            local_scope = {}
            exec(aktueller_code, {"__builtins__": __builtins__, "pd": pd, "requests": requests, "json": json}, local_scope)
            ergebnis_msg = new_stdout.getvalue()
            sys.stdout = old_stdout
            return f"✅ **Sandbox Erfolg (Versuch {versuch+1}):**\n```python\n{aktueller_code}\n```\n\n**Ausgabe:**\n{ergebnis_msg or 'Erfolgreich.'}"
        except Exception as e:
            sys.stdout = old_stdout
            fehler_trace = str(e) + "\n" + traceback.format_exc()
            if versuch == 2:
                return f"❌ Fehler nach 3 Versuchen:\n{fehler_trace}"
            repair_res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Repariere den Python-Code. Liefere AUSSCHLIESSLICH Code in ```python Block."}, {"role": "user", "content": f"Code:\n{aktueller_code}\nFehler:\n{fehler_trace}"}]
            ).choices[0].message.content
            match = re.search(r"```python\n(.*?)\n```", repair_res, re.DOTALL)
            aktueller_code = match.group(1) if match else repair_res.replace("```python", "").replace("```", "").strip()

def suche_in_rag_vektor_db(query):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT titel, inhalt FROM rag_documents")
    docs = cursor.fetchall()
    conn.close()
    if not docs:
        return "Keine Dokumente im RAG-Archiv."
    return "\n\n".join([f"**{t}**\n{i}" for t, i in docs[:2]])

def lade_agenten_erfahrungen():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT zeit, erkenntnis FROM agent_memory ORDER BY id DESC LIMIT 3")
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([f"- [{z}] {e}" for z, e in rows]) if rows else "Keine Learnings."

def lade_episodisches_gedächtnis():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ziel, erfolgs_strategie FROM episodic_memory ORDER BY id DESC LIMIT 3")
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([f"- Ziel: {z} | Strategie: {s}" for z, s in rows]) if rows else "Keine Erinnerungen."

def speichere_agenten_lernen(typ, erk, p):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO agent_memory (zeit, aufgabe_typ, erkenntnis, verbesserter_prompt) VALUES (datetime('now', 'localtime'), ?, ?, ?)", (typ, erk, p))
    conn.commit()
    conn.close()

def speichere_episodisches_gedächtnis(ziel, strat, score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO episodic_memory (zeit, ziel, erfolgs_strategie, reflexions_score) VALUES (datetime('now', 'localtime'), ?, ?, ?)", (ziel, strat, score))
    conn.commit()
    conn.close()

def echte_deep_web_recherche(query):
    if TAVILY_API_KEY:
        try:
            url = "[https://api.tavily.com/search](https://api.tavily.com/search)"
            payload = {"api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced", "max_results": 3}
            res = requests.post(url, json=payload).json()
            results = res.get("results", [])
            return "\n".join([f"- Titel: {r.get('title')}\n  Inhalt: {r.get('content')}" for r in results])
        except Exception:
            pass
    return litellm_router_abfrage("Research-Agent", query)

def selbstevaluierender_lern_agent(system_prompt, initial_input):
    rag_kontext = suche_in_rag_vektor_db(initial_input)
    episoden = lade_episodisches_gedächtnis()
    dyn_prompt = f"{system_prompt}\n\n[RAG]:\n{rag_kontext}\n\n[Episoden]:\n{episoden}"
    ergebnis = ausfuehren_mit_ollama_fallback(dyn_prompt, initial_input)
    speichere_episodisches_gedächtnis(initial_input, ergebnis[:150], 0.99)
    return ergebnis

# -------------------------------------------------------------
# NEU V12.19: INTELLIGENTER AUTONOMER TOOL-ROUTER
# -------------------------------------------------------------
def autonomer_tool_router(user_input):
    """Analysiert die Eingabe und wählt vollautomatisch das passende Tool aus."""
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    prompt = f"""Analysiere die folgende Anfrage und entscheide, welches Tool ausgeführt werden muss.
Antworte AUSSCHLIESSLICH mit einem der folgenden Schlüsselwörter:
- 'SWOT' (wenn eine Mitbewerber- oder SWOT-Analyse gewünscht ist)
- 'PL' (wenn Fixkosten, Break-Even oder Preise/Margen berechnet werden sollen)
- 'CODE' (wenn Python-Code geschrieben, getestet oder ausgeführt werden soll)
- 'SCHWARM' (wenn eine komplexe Unternehmensstrategie oder ein Vorstands-Schwarm gefragt ist)
- 'WEB' (wenn aktuelle Web-Recherche, Nachrichten oder Marktdaten benötigt werden)
- 'CHAT' (für alles andere, allgemeine Fragen oder Assistenten-Aufgaben)

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
    st.warning("👈 Bitte melde dich links an oder registriere dich.")
else:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT guthaben, rolle, workspace FROM kunden WHERE username = ?", (eingeloggter_kunde,))
    row = cursor.fetchone()
    conn.close()
    guthaben, rolle, workspace = row if row else (0.0, "Standard", "Default")

    if eingeloggter_kunde != ADMIN_NAME and guthaben <= 0.0:
        st.error("🛑 **PAYWALL AKTIV:** Dein Guthaben ist aufgebraucht (0.00 €).")
    else:
        spalte_links, spalte_rechts = st.columns([1.1, 0.9])

        with spalte_links:
            st.subheader("🤖 Autonomes Super-Agent Studio (Auto-Router aktiv)")
            current_chat = st.session_state.aktiver_chat
            st.markdown(f"**Aktiver Workspace:** `{current_chat}`")

            # Chat-Historie anzeigen
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Das einzige Eingabefeld – die KI wählt das Tool von selbst aus!
            aufgabe = st.chat_input("Schreibe einfach deine Aufgabe oder Frage – die KI wählt das Tool selbst aus...")

            if aufgabe:
                berechne_und_ziehe_credits_ab(eingeloggter_kunde, 0.005, grund="Auto-Router Ausführung")
                st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                with st.chat_message("user"):
                    st.markdown(aufgabe)

                # Live-Statusanzeige des gewählten Tools
                status_placeholder = st.empty()
                status_placeholder.info("🧠 Auto-Router analysiert Aufgabe und wählt das optimale Tool...")
                time.sleep(0.3)

                geplantes_tool = autonomer_tool_router(aufgabe)
                
                tool_namen_map = {
                    'SWOT': '📊 Konkurrenten SWOT-Analyzer',
                    'PL': '💰 P&L Break-Even Rechner',
                    'CODE': '🛠️ Self-Healing Code-Sandbox & QA',
                    'SCHWARM': '🕸️ LangGraph Vorstands-Schwarm',
                    'WEB': '🌐 Deep Web-Recherche & RAG',
                    'CHAT': '🤖 AGI Master Chat & Memory'
                }
                
                status_placeholder.success(f"⚡ **Aktives Tool ausgewählt:** `{tool_namen_map.get(geplantes_tool, 'Chat')}`")

                try:
                    with st.spinner("Führe Aufgabe im Hintergrund aus..."):
                        if geplantes_tool == 'SWOT':
                            antwort = starte_swot_analyse(aufgabe)
                        elif geplantes_tool == 'PL':
                            antwort = berechne_pl_break_even(15000.0, 150.0, 50.0) + "\n\n*(Hinweis: Du kannst Fixkosten & Preise im Code anpassen).* " + selbstevaluierender_lern_agent("Finanz-Analyst", aufgabe)
                        elif geplantes_tool == 'CODE':
                            antwort = ausfuehren_in_self_healing_sandbox("import pandas as pd\ndf = pd.DataFrame({'Wert': [100, 200, 300]})\nprint('Mittelwert:', df['Wert'].mean())")
                        elif geplantes_tool == 'SCHWARM':
                            antwort = langgraph_vorstands_schwarm(aufgabe)
                        elif geplantes_tool == 'WEB':
                            web_res = echte_deep_web_recherche(aufgabe)
                            antwort = selbstevaluierender_lern_agent("Research Expert", f"Aufgabe: {aufgabe}\nWeb-Daten: {web_res}")
                        else:
                            web_dat = echte_deep_web_recherche(aufgabe)
                            antwort = selbstevaluierender_lern_agent(f"Du bist AGI Master Assistant für {eingeloggter_kunde}.", f"Aufgabe: {aufgabe}\nDaten: {web_dat}")

                    st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                    with st.chat_message("assistant"):
                        st.markdown(antwort)
                except Exception as e:
                    st.error(f"Ausführungsfehler: {e}")

        with spalte_rechts:
            with st.expander("📊 Präsentations- & Dokumenten-Studio", expanded=False):
                st.markdown("### ⚡ Multi-Model Fließband *(Schwer: 0.05 €)*")
                auto_thema = st.text_input("Thema:", placeholder="Z.B.: KI-Strategie 2026")
                anzahl_folien = st.slider("Folien:", 2, 10, 4)

                if st.button("🚀 Präsentation generieren", use_container_width=True):
                    if auto_thema:
                        berechne_und_ziehe_credits_ab(eingeloggter_kunde, 0.05, grund="Präsentations-Studio")
                        recherche = selbstevaluierender_lern_agent("Research", echte_deep_web_recherche(auto_thema))
                        story = litellm_router_abfrage("Presentation Writer", f"Erstelle {anzahl_folien} Folien zu {auto_thema} basierend auf:\n{recherche}")
                        
                        neue = [{"titel": f"Folie {i+1}", "text": story[:200], "prompt": "Corporate background", "bild_url": None} for i in range(anzahl_folien)]
                        st.session_state.slides_data = neue
                        st.success("Präsentation erstellt!")
                        st.rerun()

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
                
                ex_col1, ex_col2 = st.columns(2)
                with ex_col1:
                    pdf_data = exportiere_zu_pdf(export_titel, export_text_input, workspace)
                    st.download_button(label="📥 Als PDF", data=pdf_data, file_name=f"{export_titel}.pdf", mime="application/pdf", use_container_width=True)
                with ex_col2:
                    docx_data = exportiere_zu_docx(export_titel, export_text_input, workspace)
                    if docx_data:
                        st.download_button(label="📥 Als Word (.docx)", data=docx_data, file_name=f"{export_titel}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
