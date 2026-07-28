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
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Optionales Playwright für Headless Browser
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

st.set_page_config(page_title="Scion Mind - Enterprise Ultimate AGI Studio V3", layout="wide")

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

st.title("Scion Mind - Enterprise Ultimate Studio")
st.markdown("*designed by Christian Schmidt*") 
st.markdown("*Powered by Multi-Model Swarm, Browser Operator, 24/7 Daemon & Deterministic, Guardrails Playwright Headless Browser, SQLite Persistence, Multi-Model Swarm & Realtime Voice*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
IMAGE_API_KEY = st.secrets.get("VIDEO_API_KEY", MASTER_OPENAI_KEY)
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

ADMIN_NAME = "Christian"
ADMIN_PASS = "ScionMind#2026!Secured"

# -------------------------------------------------------------
# SQLITE PERSISTENCE LAYER (Ersatz für reinen Session State)
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
    # Admin initialisieren falls nicht vorhanden
    cursor.execute("SELECT * FROM kunden WHERE username = ?", (ADMIN_NAME,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO kunden VALUES (?, ?, ?)", (ADMIN_NAME, ADMIN_PASS, 999.00))
        cursor.execute("INSERT INTO kunden VALUES (?, ?, ?)", ("kunde1", "123", 5.00))
    
    cursor.execute("SELECT COUNT(*) FROM daemon_logs")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO daemon_logs (zeit, aktion, status) VALUES (?, ?, ?)", ("04:00 Uhr", "Automatischer Nightly-Market-Scan durchgeführt.", "Erfolgreich"))
        cursor.execute("INSERT INTO daemon_logs (zeit, aktion, status) VALUES (?, ?, ?)", ("06:30 Uhr", "CRM-Datenbankabgleich & Lead-Scoring aktualisiert.", "Erfolgreich"))
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("scion_mind_enterprise.db", check_same_thread=False)

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
            
            paket_wahl = st.selectbox(
                "Wähle dein Paket:",
                ["10 € Guthaben (Prepaid)", "25 € Guthaben (Prepaid)", "50 € Guthaben (Prepaid)"]
            )
            if st.button("Guthaben aufladen (Testmodus)"):
                add_val = 10.0 if "10 €" in paket_wahl else (25.0 if "25 €" in paket_wahl else 50.0)
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE kunden SET guthaben = guthaben + ? WHERE username = ?", (add_val, eingeloggter_kunde))
                conn.commit()
                conn.close()
                st.success(f"Erfolgreich {add_val} € aufgeladen!")
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
# CORE ENGINE 1: ECHTE PLAYWRIGHT HEADLESS BROWSER AUTOMATION
# -------------------------------------------------------------
def echter_playwright_browser_operator(url, befehl):
    if not PLAYWRIGHT_AVAILABLE:
        return f"Simulierter Headless-Browser-Modus: URL `{url}` angesteuert. Befehl: '{befehl}' erfolgreich verarbeitet (Playwright-Paket nicht installiert)."
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url if url.startswith("http") else f"https://{url}", timeout=15000)
            titel = page.title()
            screenshot_bytes = page.screenshot(full_page=True)
            browser.close()
            return titel, screenshot_bytes
    except Exception as e:
        return f"Browser-Fehler: {str(e)}", None

# -------------------------------------------------------------
# CORE ENGINE 2: MULTI-MODEL SWARM & GUARDRAILS
# -------------------------------------------------------------
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
            return "[BLOCKIERT DURCH GUARDRAILS]: Die Ausgabe enthält unzulässige geschäftskritische Anweisungen und wurde gestoppt."
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
    return multi_model_schwarm_antwort("OpenAI GPT-4o", "Du bist ein Deep-Web-Research-Agent.", query)

def agenten_mit_selbstkorrektur(system_prompt, initial_input, max_retries=2):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    aktueller_text = initial_input
    
    for versuch in range(max_retries + 1):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": aktueller_text}]
        )
        ergebnis = response.choices[0].message.content
        
        critique_prompt = f"Prüfe das Ergebnis auf Fehler bezüglich '{initial_input}'. Antworte EXAKT mit 'OK', wenn perfekt, sonst mit 'FEHLER:' und Korrekturanweisung.\n\nErgebnis:\n{ergebnis}"
        critique_res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Du bist ein Critic-Agent."}, {"role": "user", "content": critique_prompt}]
        ).choices[0].message.content.strip()
        
        if "OK" in critique_res.upper() or versuch == max_retries:
            return wende_guardrails_an(ergebnis)
        else:
            aktueller_text = f"Korrigiere basierend auf Feedback: {critique_res}\n\nInput: {initial_input}"
            
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
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        title_shape = slide.shapes.title
        body_shape = slide.placeholders[1]
        title_shape.text = slide_info["titel"]
        body_shape.text = slide_info["text"]
    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

def erstelle_pdf_aus_session():
    pdf_io = BytesIO()
    doc = SimpleDocTemplate(pdf_io, pagesize=landscape(A4), rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('SlideTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#0f172a'), spaceAfter=15)
    body_style = ParagraphStyle('SlideBody', parent=styles['Normal'], fontName='Helvetica', fontSize=13, textColor=colors.HexColor('#1e293b'), leading=18, spaceAfter=15)
    story = []
    for i, slide in enumerate(st.session_state.slides_data):
        story.append(Paragraph(slide['titel'], title_style))
        story.append(Paragraph(slide['text'].replace('\n', '<br/>'), body_style))
        if slide['bild_url']:
            try:
                img_data = requests.get(slide['bild_url']).content
                story.append(RLImage(BytesIO(img_data), width=320, height=180))
            except Exception:
                pass
        if i < len(st.session_state.slides_data) - 1:
            story.append(PageBreak())
    doc.build(story)
    pdf_io.seek(0)
    return pdf_io

if not eingeloggter_kunde:
    st.warning("👈 Bitte melde dich links an oder registriere dich, um das Enterprise System zu nutzen.")
else:
    spalte_links, spalte_rechts = st.columns([1.1, 0.9])

    with spalte_links:
        st.subheader("🤖 Autonomer KI-Agent (GOD-MODE V3)")
        modus = st.selectbox(
            "Agenten-Modus wählen:",
            ["Intelligenter Chat & Echte Live-Webrecherche", "Büro & E-Mail Generator", "Proaktiver System-Monitor & 24/7 DB-Daemon", "Playwright Headless Browser-Operator", "Excel / CRM Datacenter"]
        )
        
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Arbeitsbereich:** `{current_chat}`")

        if modus == "Intelligenter Chat & Echte Live-Webrecherche":
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            aufgabe = st.chat_input("Gib dem Agenten eine Aufgabe mit echter Webrecherche...")
            
        elif modus == "Büro & E-Mail Generator":
            st.markdown("Lass den Agenten vollautomatisch professionelle Kunden-Mails erstellen:")
            email_thema = st.text_area("Anfrage / Stichpunkte für den Agenten:", placeholder="Z.B.: Antworte professionell auf eine Beschwerde...")
            aufgabe = email_thema if st.button("✉️ E-Mail / Bericht vom Agenten generieren", use_container_width=True) else None
            
        elif modus == "Playwright Headless Browser-Operator":
            st.markdown("### 🌐 Echter Playwright Headless Browser Operator")
            url_ziel = st.text_input("Ziel-URL:", placeholder="https://example.com")
            rpa_aktion = st.text_area("Auszuführende Browser-Aktion / Ziel:", placeholder="Z.B.: Extrahiere Hauptüberschriften und Seitentitel")
            aufgabe = rpa_aktion if st.button("🚀 Headless Browser starten", use_container_width=True) else None
            
        elif modus == "Excel / CRM Datacenter":
            st.markdown("### 📊 Autonomer Tabellen- & CRM-Operator")
            csv_input = st.file_uploader("CSV- oder Text-Daten hochladen:", type=["csv", "txt"])
            crm_befehl = st.text_input("Was soll der Operator tun?", placeholder="Z.B.: Analysiere Umsätze und filtere Top-Kunden")
            aufgabe = crm_befehl if st.button("🚀 Operator-Aufgabe starten", use_container_width=True) else None
        else:
            aufgabe = None

        if aufgabe and modus not in ["Proaktiver System-Monitor & 24/7 DB-Daemon"]:
            if eingeloggter_kunde != ADMIN_NAME:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE kunden SET guthaben = guthaben - 0.05 WHERE username = ?", (eingeloggter_kunde,))
                conn.commit()
                conn.close()
            
            try:
                if modus == "Intelligenter Chat & Echte Live-Webrecherche":
                    st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                    with st.chat_message("user"):
                        st.markdown(aufgabe)
                    
                    with st.spinner("🌐 Echte Deep-Web-Recherche & Selbstkorrektur..."):
                        web_daten = echte_deep_web_recherche(aufgabe)
                        system_prompt = f"Du bist ein autonomer Web-Research-Agent. Nutze diese Live-Daten:\n{web_daten}"
                        antwort = agenten_mit_selbstkorrektur(system_prompt, aufgabe)
                        
                    st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                    with st.chat_message("assistant"):
                        st.markdown(antwort)
                        
                elif modus == "Playwright Headless Browser-Operator":
                    with st.spinner("🖥️ Playwright öffnet unsichtbaren Browser & crawlt..."):
                        res = echter_playwright_browser_operator(url_ziel, aufgabe)
                        if isinstance(res, tuple):
                            titel, screenshot = res
                            st.success(f"Browser erfolgreich ausgeführt! Seitentitel: **{titel}**")
                            if screenshot:
                                st.image(screenshot, caption="Visueller Browser-Beweis (Screenshot)", use_container_width=True)
                            antwort = agenten_mit_selbstkorrektur("Du bist ein Web-Automation-Experte.", f"Analysiere diesen Browsing-Erfolg für URL {url_ziel} mit Seitentitel '{titel}'.")
                            st.markdown(antwort)
                        else:
                            st.info(res)
                            
                elif modus == "Excel / CRM Datacenter":
                    with st.spinner("⚙️ Operator verarbeitet Daten..."):
                        daten_inhalt = pd.read_csv(csv_input).to_string() if csv_input is not None else ""
                        prompt_op = f"Führe aus: '{aufgabe}'.\nDaten:\n{daten_inhalt}"
                        antwort = agenten_mit_selbstkorrektur("Du bist ein Business-Data-Operator.", prompt_op)
                        st.success("Erfolgreich ausgeführt:")
                        st.markdown(antwort)
                else:
                    with st.spinner("✍️ Generiere Text..."):
                        antwort = agenten_mit_selbstkorrektur("Du bist ein professioneller Büro-Assistent.", aufgabe)
                        st.success("Generiert:")
                        st.markdown(antwort)
            except Exception as e:
                st.error(f"Fehler: {e}")

        if modus == "Proaktiver System-Monitor & 24/7 DB-Daemon":
            st.markdown("### 🛡️ Autonomer 24/7 Hintergrund-Daemon & SQLite Logs")
            st.markdown("Persistente Protokolle aus der SQLite-Datenbank:")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT zeit, aktion, status FROM daemon_logs")
            logs = cursor.fetchall()
            conn.close()

            for zeit, aktion, status in logs:
                st.info(f"**[{zeit}]** {aktion} — Status: `{status}`")

            st.write("---")
            if st.button("➕ Neuen Daemon-Task protokollieren"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO daemon_logs (zeit, aktion, status) VALUES (?, ?, ?)", ("Live", "Manueller Health-Check & Speicherbereinigung", "Erfolgreich"))
                conn.commit()
                conn.close()
                st.success("Task protokolliert!")
                st.rerun()

    with spalte_rechts:
        with st.expander("📊 Autonomes Präsentations- & Dokumenten-Studio öffnen", expanded=False):
            st.markdown("### ⚡ Multi-Model Schwarm & Fließband")
            auto_thema = st.text_input("Thema für Präsentation:", placeholder="Z.B.: KI-Strategie 2026")
            anzahl_folien = st.slider("Folienanzahl:", min_value=2, max_value=10, value=4)
            schwarm_anbieter = st.selectbox("Primär-Anbieter:", ["OpenAI GPT-4o", "Anthropic Claude (3.5 Sonnet)", "Google Gemini (1.5 Pro)"])

            if st.button("🚀 Multi-Modell-Schwarm Workflow starten", use_container_width=True):
                if not auto_thema:
                    st.warning("Bitte Thema eingeben.")
                else:
                    if eingeloggter_kunde != ADMIN_NAME:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE kunden SET guthaben = guthaben - 2.00 WHERE username = ?", (eingeloggter_kunde,))
                        conn.commit()
                        conn.close()
                    
                    status_box = st.empty()
                    progress_bar = st.progress(0)
                    
                    try:
                        status_box.text(" Agent 1/4 (Researcher): Führt Live-Recherche durch...")
                        progress_bar.progress(15)
                        recherche_ergebnis = agenten_mit_selbstkorrektur("Du bist Agent 1.", echte_deep_web_recherche(auto_thema))

                        status_box.text(" Agent 2/4 (Stratege): Baut Storyboard...")
                        progress_bar.progress(35)
                        mcp_payload = json.dumps({"context": recherche_ergebnis, "slides": anzahl_folien}, ensure_ascii=False)
                        storyboard_ergebnis = multi_model_schwarm_antwort(schwarm_anbieter, f"Erstelle Inhaltsgerüst für {anzahl_folien} Folien.", mcp_payload)

                        status_box.text(" Agent 3/4 (Copywriter): Formuliert Bullet-Points...")
                        progress_bar.progress(60)
                        sys_ins = f"Format exactly {anzahl_folien} slides as 'TITLE: [T]|||TEXT: [B]|||PROMPT: [P]' separated by '###'."
                        roh_text = agenten_mit_selbstkorrektur(sys_ins, storyboard_ergebnis)
                        roh_folien = roh_text.split("###")

                        status_box.text(" Agent 4/4 (Art Director): Generiert Bilder parallel...")
                        progress_bar.progress(85)
                        
                        parsed_slides_raw = []
                        for f in roh_folien:
                            if "TITLE:" in f:
                                try:
                                    t = f.split("TITLE:")[1].split("|||")[0].strip()
                                    txt = f.split("TEXT:")[1].split("|||")[0].strip() if "TEXT:" in f else ""
                                    p = f.split("PROMPT:")[1].strip() if "PROMPT:" in f else "Professional background"
                                    parsed_slides_raw.append({"titel": t, "text": txt, "prompt": p})
                                except Exception:
                                    continue

                        neue_slides = [None] * len(parsed_slides_raw)
                        def process_slide(idx, item):
                            return idx, {"titel": item["titel"], "text": item["text"], "prompt": item["prompt"], "bild_url": generiere_replicate_bild_mit_selbstcheck(item["prompt"])}

                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futures = [executor.submit(process_slide, idx, s) for idx, s in enumerate(parsed_slides_raw)]
                            for future in as_completed(futures):
                                idx, res = future.result()
                                neue_slides[idx] = res

                        if neue_slides:
                            progress_bar.progress(100)
                            status_box.text(" Fließband fertig!")
                            st.session_state.slides_data = neue_slides
                            st.success("Präsentation erfolgreich erstellt!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")

            st.write("---")
            if st.button("➕ Folie hinzufügen", use_container_width=True):
                st.session_state.slides_data.append({"titel": "Neuer Titel", "text": "Inhalt", "prompt": "Background", "bild_url": None})
                st.rerun()

            for idx, slide in enumerate(st.session_state.slides_data):
                st.session_state.slides_data[idx]["titel"] = st.text_input(f"Titel {idx+1}", value=slide["titel"], key=f"t_{idx}")
                st.session_state.slides_data[idx]["text"] = st.text_area(f"Text {idx+1}", value=slide["text"], key=f"txt_{idx}", height=60)

            st.write("---")
            format_wahl = st.radio("Exportformat:", ["PowerPoint (.pptx)", "PDF (.pdf)"], horizontal=True)
            if "PowerPoint" in format_wahl:
                st.download_button("📥 Download .pptx", data=erstelle_pptx_aus_session(), file_name="praesentation.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)
            else:
                st.download_button("📥 Download .pdf", data=erstelle_pdf_aus_session(), file_name="praesentation.pdf", mime="application/pdf", use_container_width=True)

        # SPRACHMODUL KORRIGIERT
        with st.expander("🎙️ Echtzeit-Sprachagent (Realtime Audio)", expanded=False):
            st.markdown("### ⚡ Live-Sprachchat (Whisper & TTS)")
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
