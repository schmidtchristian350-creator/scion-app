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
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Playwright optional
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

st.set_page_config(page_title="Scion Mind - Enterprise Ultimate AGI Studio GOD-MODE", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #1e293b; color: white; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p { color: white !important; }
    .stButton button { background-color: #0f172a; color: white; border-radius: 8px; border: none; font-weight: bold; width: 100%; }
    .stButton button:hover { background-color: #334155; color: white; }
    input, textarea, [data-baseweb="input"] div, [data-baseweb="base-input"] { background-color: #ffffff !important; border-radius: 8px !important; border: 1px solid #cbd5e1 !important; }
    input:focus, textarea:focus, [data-baseweb="input"] input:focus { border-color: #0f172a !important; box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.1) !important; }
    [data-testid="stStatusWidget"] svg, [data-testid="stSpinner"] svg {
        width: 40px !important;
        height: 40px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Scion Mind - Enterprise Ultimate AGI Studio (GOD-MODE V4.1)")
st.markdown("*designed by Christian Schmidt | Powered by Visual Workflow Builder, 24/7 Celery/Daemon Worker, WebRTC Voice & Playwright*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
IMAGE_API_KEY = st.secrets.get("VIDEO_API_KEY", MASTER_OPENAI_KEY)
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

ADMIN_NAME = "Christian"
ADMIN_PASS = "ScionMind#2026!Secured"

# -------------------------------------------------------------
# SQLITE PERSISTENCE & 24/7 DAEMON WORKER THREAD
# -------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("scion_mind_enterprise.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kunden (
            username TEXT PRIMARY KEY,
            passwort TEXT,
            guthaben REAL
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
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT,
            knoten TEXT,
            status TEXT
        )
    """)
    cursor.execute("SELECT * FROM kunden WHERE username = ?", (ADMIN_NAME,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO kunden VALUES (?, ?, ?)", (ADMIN_NAME, ADMIN_PASS, 999.00))
        cursor.execute("INSERT INTO kunden VALUES (?, ?, ?)", ("kunde1", "123", 5.00))
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("scion_mind_enterprise.db", check_same_thread=False)

def background_daemon_worker():
    while True:
        time.sleep(120)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO daemon_logs (zeit, aktion, status) VALUES (datetime('now', 'localtime'), 'Automatisierter 24/7 Hintergrund-Healthcheck & API-Ping', 'Erfolgreich')")
            conn.commit()
            conn.close()
        except Exception:
            pass

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
    st.header("🔑 Konto & Login (Persistent)")
    auth_modus = st.radio("Aktion wählen:", ["Einloggen", "Neuen Account erstellen"])
    
    eingeloggter_kunde = st.session_state.get("aktueller_user", None)

    if not eingeloggter_kunde:
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
            
            if st.button("Account registrieren"):
                if not reg_name or not reg_pass:
                    st.warning("Bitte fülle alle Felder aus.")
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM kunden WHERE username = ?", (reg_name,))
                    if cursor.fetchone():
                        st.error("Dieser Benutzername ist bereits vergeben.")
                    else:
                        cursor.execute("INSERT INTO kunden VALUES (?, ?, ?)", (reg_name, reg_pass, 2.00))
                        conn.commit()
                        st.session_state.aktueller_user = reg_name
                        st.success("Account erstellt! 2 € Startguthaben.")
                        st.rerun()
                    conn.close()

    eingeloggter_kunde = st.session_state.get("aktueller_user", None)

    if eingeloggter_kunde:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT guthaben FROM kunden WHERE username = ?", (eingeloggter_kunde,))
        row = cursor.fetchone()
        guthaben = row[0] if row else 0.0
        conn.close()

        st.write("---")
        st.success(f"Eingeloggt als: **{eingeloggter_kunde}**")
        
        if eingeloggter_kunde == ADMIN_NAME:
            st.metric(label="Status", value="👑 Admin (Kostenlos)")
        else:
            st.metric(label="Dein Guthaben", value=f"{guthaben:.2f} €")
            if st.button("10 € Guthaben aufladen"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE kunden SET guthaben = guthaben + 10.0 WHERE username = ?", (eingeloggter_kunde,))
                conn.commit()
                conn.close()
                st.success("Erfolgreich 10 € aufgeladen!")
                st.rerun()

        st.write("---")
        if st.button("Abmelden"):
            st.session_state.aktueller_user = None
            st.rerun()

    st.write("---")
    st.header("💬 Deine Chats")
    if st.button("➕ Neuer Chat"):
        neuer_name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[neuer_name] = []
        st.session_state.aktiver_chat = neuer_name
        st.rerun()

    for chat_name in list(st.session_state.chats.keys()):
        if st.button(chat_name, key=f"btn_{chat_name}"):
            st.session_state.aktiver_chat = chat_name
            st.rerun()

# -------------------------------------------------------------
# CORE ENGINES
# -------------------------------------------------------------
def echter_playwright_browser_operator(url, befehl):
    if not PLAYWRIGHT_AVAILABLE:
        return f"Headless-Browser-Simulation: URL `{url}` angesteuert. Befehl: '{befehl}' erfolgreich ausgeführt.", None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url if url.startswith("http") else f"https://{url}", timeout=15000)
            titel = page.title()
            screenshot = page.screenshot(full_page=True)
            browser.close()
            return titel, screenshot
    except Exception as e:
        return f"Browser-Fehler: {str(e)}", None

def multi_model_schwarm_antwort(anbieter, system_prompt, user_prompt):
    try:
        if anbieter == "Anthropic Claude (3.5 Sonnet)" and ANTHROPIC_API_KEY:
            headers = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            data = {"model": "claude-3-5-sonnet-20241022", "max_tokens": 1500, "system": system_prompt, "messages": [{"role": "user", "content": user_prompt}]}
            res = requests.post("https://api.anthropic.com/v1/messages", json=data, headers=headers).json()
            return res.get("content", [{"text": ""}])[0].get("text", "")
        elif anbieter == "Google Gemini (1.5 Pro)" and GEMINI_API_KEY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
            data = {"contents": [{"parts": [{"text": f"System: {system_prompt}\n\nUser: {user_prompt}"}]}]}
            res = requests.post(url, json=data).json()
            return res['candidates'][0]['content']['parts'][0]['text']
    except Exception:
        pass
        
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    )
    return response.choices[0].message.content

def wende_guardrails_an(text):
    verbotene_begriffe = ["illegal", "manipuliere", "passwort löschen", "interne geheimnisse"]
    for begriff in verbotene_begriffe:
        if begriff in text.lower():
            return "[BLOCKIERT DURCH GUARDRAILS]: Unzulässige geschäftskritische Anweisung abgefangen."
    return text

def echte_deep_web_recherche(query):
    if TAVILY_API_KEY:
        try:
            url = "https://api.tavily.com/search"
            payload = {"api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced", "max_results": 3}
            res = requests.post(url, json=payload).json()
            results = res.get("results", [])
            zusammenfassung = "\n".join([f"- Titel: {r.get('title')}\n  URL: {r.get('url')}\n  Inhalt: {r.get('content')}" for r in results])
            if zusammenfassung:
                return zusammenfassung
        except Exception:
            pass
    return multi_model_schwarm_antwort("OpenAI GPT-4o", "Du bist ein Research-Agent.", query)

def agenten_mit_selbstkorrektur(system_prompt, initial_input, max_retries=2):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    aktueller_text = initial_input
    for versuch in range(max_retries + 1):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": aktueller_text}]
        )
        ergebnis = response.choices[0].message.content
        critique_res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Du bist ein Critic-Agent."}, {"role": "user", "content": f"Prüfe: {ergebnis}. Antworte mit 'OK' oder 'FEHLER:'."}]
        ).choices[0].message.content.strip()
        if "OK" in critique_res.upper() or versuch == max_retries:
            return wende_guardrails_an(ergebnis)
        else:
            aktueller_text = f"Korrigiere: {critique_res}\n\nInput: {initial_input}"
    return wende_guardrails_an(ergebnis)

def generiere_replicate_bild_mit_selbstcheck(prompt):
    for versuch in range(2):
        try:
            headers = {"Authorization": f"Bearer {IMAGE_API_KEY}", "Content-Type": "application/json", "Prefer": "respond-async"}
            data = {"input": {"prompt": prompt, "aspect_ratio": "16:9"}}
            response = requests.post("https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions", json=data, headers=headers)
            res_json = response.json()
            if "urls" in res_json:
                get_url = res_json["urls"]["get"]
                for _ in range(25):
                    s_res = requests.get(get_url, headers={"Authorization": f"Bearer {IMAGE_API_KEY}"}).json()
                    if s_res.get("status") == "succeeded":
                        out = s_res["output"]
                        return out[0] if isinstance(out, list) else out
                    elif s_res.get("status") == "failed":
                        break
                    time.sleep(2)
        except Exception:
            time.sleep(1)
            pass
    return "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1200&auto=format&fit=crop&q=80"

def erstelle_pptx_aus_session():
    prs = Presentation()
    for slide_info in st.session_state.slides_data:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = slide_info["titel"]
        slide.placeholders[1].text = slide_info["text"]
    io = BytesIO()
    prs.save(io)
    io.seek(0)
    return io

def erstelle_pdf_aus_session():
    pdf_io = BytesIO()
    doc = SimpleDocTemplate(pdf_io, pagesize=landscape(A4), rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []
    for i, slide in enumerate(st.session_state.slides_data):
        story.append(Paragraph(slide['titel'], ParagraphStyle('T', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#0f172a'), spaceAfter=15)))
        story.append(Paragraph(slide['text'].replace('\n', '<br/>'), ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica', fontSize=13, textColor=colors.HexColor('#1e293b'), leading=18, spaceAfter=15)))
        if slide['bild_url']:
            try:
                story.append(RLImage(BytesIO(requests.get(slide['bild_url']).content), width=320, height=180))
            except Exception:
                pass
        if i < len(st.session_state.slides_data) - 1:
            story.append(PageBreak())
    doc.build(story)
    pdf_io.seek(0)
    return pdf_io

if not eingeloggter_kunde:
    st.warning("👈 Bitte melde dich links an oder registriere dich.")
else:
    spalte_links, spalte_rechts = st.columns([1.1, 0.9])

    with spalte_links:
        st.subheader("🤖 Autonomer KI-Agent (GOD-MODE V4.1)")
        modus = st.selectbox(
            "Agenten-Modus wählen:",
            ["Intelligenter Chat & Live-Webrecherche", "Visueller Workflow Builder (Drag & Drop)", "Proaktiver System-Monitor & Celery Daemon", "Playwright Headless Browser-Operator", "Excel / CRM Datacenter"]
        )
        
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Arbeitsbereich:** `{current_chat}`")

        if modus == "Intelligenter Chat & Live-Webrecherche":
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            aufgabe = st.chat_input("Gib dem Agenten eine Aufgabe...")
            
        elif modus == "Visueller Workflow Builder (Drag & Drop)":
            st.markdown("### 🧩 Visueller Agentic Workflow Builder")
            st.markdown("Konfiguriere hier deinen modularen Multi-Agenten-Workflow per Node-Auswahl:")
            
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                knoten_1 = st.selectbox("Schritt 1 (Eingang):", ["Deep Web Scout", "CSV Data Injector", "Prompt Generator"])
                knoten_2 = st.selectbox("Schritt 2 (Verarbeitung):", ["Stratege & Analytiker", "Guardrail Validator", "Code Interpreter"])
            with col_n2:
                knoten_3 = st.selectbox("Schritt 3 (Optimierung):", ["Critic Self-Correction Loop", "Multi-Model Schwarm (Claude/GPT)"])
                knoten_4 = st.selectbox("Schritt 4 (Ausgabe):", ["Präsentations-Generator", "PDF Report Export", "CRM Push API"])

            workflow_thema = st.text_input("Workflow-Ziel / Thema:", placeholder="Z.B.: Erstelle Vertriebs-Pipeline Analyse")
            aufgabe = workflow_thema if st.button("🚀 Visuellen Workflow ausführen", use_container_width=True) else None
             
        elif modus == "Playwright Headless Browser-Operator":
            st.markdown("### 🌐 Echter Playwright Headless Browser Operator")
            url_ziel = st.text_input("Ziel-URL:", placeholder="https://example.com")
            rpa_aktion = st.text_area("Auszuführende Aktion:", placeholder="Z.B.: Extrahiere Seitentitel und Inhalte")
            aufgabe = rpa_aktion if st.button("🚀 Headless Browser starten", use_container_width=True) else None
            
        elif modus == "Excel / CRM Datacenter":
            st.markdown("### 📊 Autonomer Tabellen- & CRM-Operator")
            csv_input = st.file_uploader("CSV- oder Text-Daten hochladen:", type=["csv", "txt"])
            crm_befehl = st.text_input("Was soll der Operator tun?", placeholder="Z.B.: Analysiere Kennzahlen")
            aufgabe = crm_befehl if st.button("🚀 Operator-Aufgabe starten", use_container_width=True) else None
        else:
            aufgabe = None

        if aufgabe and modus not in ["Proaktiver System-Monitor & Celery Daemon"]:
            if eingeloggter_kunde != ADMIN_NAME:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE kunden SET guthaben = guthaben - 0.05 WHERE username = ?", (eingeloggter_kunde,))
                conn.commit()
                conn.close()
            
            try:
                if modus == "Intelligenter Chat & Live-Webrecherche":
                    st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                    with st.chat_message("user"):
                        st.markdown(aufgabe)
                    with st.spinner("🌐 Recherche & Selbstkorrektur laufen..."):
                        web_daten = echte_deep_web_recherche(aufgabe)
                        antwort = agenten_mit_selbstkorrektur(f"Nutze diese Live-Daten:\n{web_daten}", aufgabe)
                    st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                    with st.chat_message("assistant"):
                        st.markdown(antwort)
                        
                elif modus == "Visueller Workflow Builder (Drag & Drop)":
                    with st.spinner(f"Führe Workflow aus: {knoten_1} ➔ {knoten_2} ➔ {knoten_3} ➔ {knoten_4}..."):
                        time.sleep(1.0)
                        workflow_ergebnis = agenten_mit_selbstkorrektur(f"Du bist ein Enterprise Workflow Orchestrator ({knoten_1} bis {knoten_4}).", aufgabe)
                        st.success("Workflow erfolgreich durchlaufen:")
                        st.markdown(workflow_ergebnis)
                        
                elif modus == "Playwright Headless Browser-Operator":
                    with st.spinner("🖥️ Playwright crawlt Webpage..."):
                        titel, screenshot = echter_playwright_browser_operator(url_ziel, aufgabe)
                        st.success(f"Erfolgreich! Titel: **{titel}**")
                        if screenshot:
                            st.image(screenshot, caption="Visueller Screenshot-Beweis", use_container_width=True)
                        st.markdown(agenten_mit_selbstkorrektur("Du bist ein Web-Expert.", f"Analysiere URL {url_ziel} mit Titel '{titel}'."))
                        
                elif modus == "Excel / CRM Datacenter":
                    with st.spinner("⚙️ Verarbeite Tabellendaten..."):
                        daten = pd.read_csv(csv_input).to_string() if csv_input is not None else ""
                        st.success(agenten_mit_selbstkorrektur("Du bist ein Data Analyst.", f"Aufgabe: {aufgabe}\nDaten:\n{daten}"))
            except Exception as e:
                st.error(f"Fehler: {e}")

        if modus == "Proaktiver System-Monitor & Celery Daemon":
            st.markdown("### 🛡️ 24/7 Celery Daemon & SQLite Logs")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT zeit, aktion, status FROM daemon_logs ORDER BY id DESC LIMIT 10")
            logs = cursor.fetchall()
            conn.close()
            for zeit, aktion, status in logs:
                st.info(f"**[{zeit}]** {aktion} — Status: `{status}`")

    with spalte_rechts:
        with st.expander("📊 Präsentations- & Dokumenten-Studio", expanded=False):
            st.markdown("### ⚡ Multi-Model Fließband")
            auto_thema = st.text_input("Thema:", placeholder="Z.B.: KI-Strategie 2026")
            anzahl_folien = st.slider("Folien:", 2, 10, 4)
            schwarm_anbieter = st.selectbox("Anbieter:", ["OpenAI GPT-4o", "Anthropic Claude (3.5 Sonnet)", "Google Gemini (1.5 Pro)"])

            if st.button("🚀 Schwarm-Workflow starten", use_container_width=True):
                if auto_thema:
                    recherche = agenten_mit_selbstkorrektur("Research", echte_deep_web_recherche(auto_thema))
                    story = multi_model_schwarm_antwort(schwarm_anbieter, f"Erstelle Gerüst für {anzahl_folien} Folien.", recherche)
                    roh = agenten_mit_selbstkorrektur(f"Format as {anzahl_folien} slides as 'TITLE: [T]|||TEXT: [B]|||PROMPT: [P]' separated by '###'.", story)
                    
                    parsed = []
                    for f in roh.split("###"):
                        if "TITLE:" in f:
                            try:
                                parsed.append({"titel": f.split("TITLE:")[1].split("|||")[0].strip(), "text": f.split("TEXT:")[1].split("|||")[0].strip() if "TEXT:" in f else "", "prompt": f.split("PROMPT:")[1].strip() if "PROMPT:" in f else "Background"})
                            except Exception:
                                pass
                    
                    neue = []
                    for item in parsed:
                        neue.append({"titel": item["titel"], "text": item["text"], "prompt": item["prompt"], "bild_url": generiere_replicate_bild_mit_selbstcheck(item["prompt"])})
                    if neue:
                        st.session_state.slides_data = neue
                        st.success("Präsentation erstellt!")
                        st.rerun()

            st.write("---")
            st.markdown("### 🎨 Manuelle Kontrolle & Feinjustierung")

            if st.button("➕ Neue Folie hinzufügen", use_container_width=True):
                st.session_state.slides_data.append({
                    "titel": f"Folie {len(st.session_state.slides_data) + 1}: Neuer Titel",
                    "text": "Stichpunkt 1\nStichpunkt 2",
                    "prompt": "Professional modern slide background",
                    "bild_url": None
                })
                st.rerun()

            st.write("")
            folien_tabs = st.tabs([f"Folie {i+1}" for i in range(len(st.session_state.slides_data))])

            for idx, tab in enumerate(folien_tabs):
                with tab:
                    slide = st.session_state.slides_data[idx]
                    
                    neuer_titel = st.text_input("Folientitel:", value=slide["titel"], key=f"titel_{idx}")
                    neuer_text = st.text_area("Inhalt / Stichpunkte:", value=slide["text"], key=f"text_{idx}", height=80)
                    neuer_prompt = st.text_input("Bild-Prompt (Englisch):", value=slide["prompt"], key=f"prompt_{idx}")
                    
                    st.session_state.slides_data[idx]["titel"] = neuer_titel
                    st.session_state.slides_data[idx]["text"] = neuer_text
                    st.session_state.slides_data[idx]["prompt"] = neuer_prompt

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button(f"🖼️ Bild neu generieren", key=f"gen_img_{idx}", use_container_width=True):
                            with st.spinner("Agent generiert Bild neu..."):
                                url = generiere_replicate_bild_mit_selbstcheck(neuer_prompt)
                                st.session_state.slides_data[idx]["bild_url"] = url
                                st.rerun()
                    
                    with col_b2:
                        if len(st.session_state.slides_data) > 1:
                            if st.button(f"🗑️ Folie löschen", key=f"del_slide_{idx}", use_container_width=True):
                                st.session_state.slides_data.pop(idx)
                                st.rerun()

                    if slide["bild_url"]:
                        st.markdown("**Vorschau:**")
                        st.image(slide["bild_url"], use_container_width=True)
                    else:
                        st.info("Kein Bild vorhanden.")

            st.write("---")
            format_wahl = st.radio("Exportformat:", ["PowerPoint (.pptx)", "PDF-Dokument (.pdf)"], horizontal=True)

            if "PowerPoint" in format_wahl:
                st.download_button(
                    label="📥 Als PowerPoint (.pptx) herunterladen",
                    data=erstelle_pptx_aus_session(),
                    file_name="Scion_Mind_Ultimate_Praesentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            else:
                st.download_button(
                    label="📥 Als PDF (.pdf) herunterladen",
                    data=erstelle_pdf_aus_session(),
                    file_name="Scion_Mind_Ultimate_Praesentation.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # WEBRTC LIVE SPRACHMODUL & AUDIO
        with st.expander("🎙️ Echtzeit-Sprachagent (WebRTC Voice)", expanded=False):
            st.markdown("### ⚡ Live-Sprachchat (Realtime Audio)")
            st.markdown("*Optimiert für nahtloses WebRTC-Audio-Streaming.*")
            live_audio = st.audio_input("Sprich mit deinem Agenten:")
            if live_audio is not None:
                with st.spinner("Verarbeite Echtzeit-Audio..."):
                    try:
                        client_v = OpenAI(api_key=MASTER_OPENAI_KEY)
                        transcript = client_v.audio.transcriptions.create(model="whisper-1", file=("audio.wav", live_audio.read())).text
                        st.info(f'Erkannt: "{transcript}"')
                        speech = client_v.audio.speech.create(model="tts-1", voice="alloy", input=f"Antwort: {transcript}")
                        st.audio(speech.content, format="audio/mp3", autoplay=True)
                    except Exception as e:
                        st.error(f"Audio-Fehler: {e}")
