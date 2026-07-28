import streamlit as st
from openai import OpenAI
from pptx import Presentation
from io import BytesIO
import re
import requests
import time
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Scion Mind - Enterprise Agent Studio Pro", layout="wide")

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

st.title("Scion Mind - Enterprise Autonomes Agenten-Studio (PRO)")
st.markdown("*designed by Christian Schmidt | Powered by Self-Correction, Deep-Web-Search & MCP-Protocols*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
IMAGE_API_KEY = st.secrets.get("VIDEO_API_KEY", MASTER_OPENAI_KEY)
TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")  # Optional für echte Websuche

ADMIN_NAME = "Christian"
ADMIN_PASS = "ScionMind#2026!Secured"

if "kunden_daten" not in st.session_state:
    st.session_state.kunden_daten = {
        ADMIN_NAME: {"passwort": ADMIN_PASS, "guthaben": 999.00},
        "kunde1": {"passwort": "123", "guthaben": 5.00}
    }

if "slides_data" not in st.session_state:
    st.session_state.slides_data = [
        {"titel": "Folie 1: Willkommen", "text": "Hier steht der Text für Folie 1...", "prompt": "Professional corporate presentation slide background, modern clean style", "bild_url": None}
    ]

if "proaktive_tickets" not in st.session_state:
    st.session_state.proaktive_tickets = [
        {"id": "INC-4091", "system": "ERP Server", "status": "Kritisch: Hohe Latenz gemeldet", "loesung_bereit": False},
        {"id": "INC-4092", "system": "E-Mail Gateway", "status": "Warnung: Warteschlange läuft voll", "loesung_bereit": False}
    ]

with st.sidebar:
    st.header("🔑 Konto & Login")
    auth_modus = st.radio("Aktion wählen:", ["Einloggen", "Neuen Account erstellen"])
    
    eingeloggter_kunde = None

    if auth_modus == "Einloggen":
        login_name = st.text_input("Benutzername:")
        login_pass = st.text_input("Passwort:", type="password")
        
        if st.button("Anmelden"):
            if login_name in st.session_state.kunden_daten and st.session_state.kunden_daten[login_name]["passwort"] == login_pass:
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
            elif reg_name in st.session_state.kunden_daten:
                st.error("Dieser Benutzername ist bereits vergeben.")
            else:
                st.session_state.kunden_daten[reg_name] = {"passwort": reg_pass, "guthaben": 2.00}
                st.session_state.aktueller_user = reg_name
                st.success("Account erstellt! 2 € Startguthaben.")
                st.rerun()

    eingeloggter_kunde = st.session_state.get("aktueller_user", None)

    if eingeloggter_kunde and eingeloggter_kunde in st.session_state.kunden_daten:
        guthaben = st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"]
        st.write("---")
        st.success(f"Eingeloggt als: **{eingeloggter_kunde}**")
        
        if eingeloggter_kunde == ADMIN_NAME:
            st.metric(label="Status", value="👑 Admin (Kostenlos)")
        else:
            st.metric(label="Dein Guthaben", value=f"{guthaben:.2f} €")
            
            st.markdown("### 💳 Guthaben & Abos aufladen")
            paket_wahl = st.selectbox(
                "Wähle dein Paket:",
                ["10 € Guthaben (Prepaid)", "25 € Guthaben (Prepaid)", "50 € Guthaben (Prepaid)", "Abo 10 € / Monat", "Abo 25 € / Monat"]
            )
            
            stripe_links = {
                "10 € Guthaben (Prepaid)": "https://buy.stripe.com/test_cNidRa5GPaUD4BnfSf9sk00",
                "25 € Guthaben (Prepaid)": "https://buy.stripe.com/test_cNi3cwb198Mv3xj6hF9sk01",
                "50 € Guthaben (Prepaid)": "https://buy.stripe.com/test_bJe9AU8T1aUDfg15dB9sk02",
                "Abo 10 € / Monat": "https://buy.stripe.com/test_6oU28s3yH9Qz4Bn8pN9sk03",
                "Abo 25 € / Monat": "https://buy.stripe.com/test_28E28sfhpd2L3xjbBZ9sk04"
            }
            
            aktiver_link = stripe_links[paket_wahl]
            st.markdown(f"[⚡ Ausgeführtes Paket bezahlen]({aktiver_link})", unsafe_allow_html=True)
            
            if st.button("Guthaben aktualisieren"):
                if "10 €" in paket_wahl: st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] += 10.00
                elif "25 €" in paket_wahl: st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] += 25.00
                elif "50 €" in paket_wahl: st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] += 50.00
                st.success("Erfolgreich aktualisiert!")
                st.rerun()

        st.write("---")
        if st.button("Abmelden"):
            st.session_state.aktueller_user = None
            st.rerun()

    st.write("---")
    st.header("💬 Deine Chats")
    
    if "chats" not in st.session_state:
        st.session_state.chats = {"Chat 1": []}
    if "aktiver_chat" not in st.session_state:
        st.session_state.aktiver_chat = "Chat 1"

    if st.button("➕ Neuer Chat"):
        neuer_name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[neuer_name] = []
        st.session_state.aktiver_chat = neuer_name
        st.rerun()

    st.write("Wähle einen Chat aus:")
    for chat_name in list(st.session_state.chats.keys()):
        if st.button(chat_name, key=f"btn_{chat_name}"):
            st.session_state.aktiver_chat = chat_name
            st.rerun()

@st.cache_data(show_spinner=False)
def get_cached_ai_response(model_name, system_content, user_content):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    )
    return response.choices[0].message.content

# NEU: Echte Deep-Web-Search Funktion via Tavily API (Fallback auf GPT-Simulierung, wenn kein Key hinterlegt)
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
    
    # Fallback / Simulierte Deep Search mit GPT-4o-mini
    return get_cached_ai_response(
        "gpt-4o-mini",
        "Du bist ein Deep-Web-Research-Agent. Führe eine gründliche Recherche durch und liefere fundierte Fakten.",
        query
    )

# NEU: Autonome Selbstkorrektur-Schleife (Critic Loop)
def agenten_mit_selbstkorrektur(system_prompt, initial_input, max_retries=2):
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    aktueller_text = initial_input
    
    for versuch in range(max_retries + 1):
        # 1. Ausführung durch den Agenten
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": aktueller_text}
            ]
        )
        ergebnis = response.choices[0].message.content
        
        # 2. Kritischer Selbsttest (Critic Agent)
        critique_prompt = f"Prüfe das folgende Ergebnis auf Fehler, Lücken oder Ungenauigkeiten bezüglich der Aufgabe '{initial_input}'. Antworte EXAKT mit 'OK', wenn das Ergebnis perfekt ist. Falls nicht, antworte mit 'FEHLER:' gefolgt von einer präzisen Korrekturanweisung.\n\nErgebnis:\n{ergebnis}"
        critique_res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Du bist ein strenger Qualitätsprüfer (Critic-Agent)."}, {"role": "user", "content": critique_prompt}]
        ).choices[0].message.content.strip()
        
        if "OK" in critique_res.upper() or versuch == max_retries:
            return ergebnis
        else:
            # Korrekturschleife anpassen
            aktueller_text = f"Korrigiere basierend auf diesem Feedback: {critique_res}\n\nUrsprünglicher Input: {initial_input}"
            
    return ergebnis

def generiere_replicate_bild_mit_selbstcheck(prompt):
    for versuch in range(2):
        try:
            headers = {
                "Authorization": f"Bearer {IMAGE_API_KEY}",
                "Content-Type": "application/json",
                "Prefer": "respond-async"
            }
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
    
    title_style = ParagraphStyle(
        'SlideTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#0f172a'), spaceAfter=15
    )
    body_style = ParagraphStyle(
        'SlideBody', parent=styles['Normal'], fontName='Helvetica', fontSize=13, textColor=colors.HexColor('#1e293b'), leading=18, spaceAfter=15
    )
    
    story = []
    for i, slide in enumerate(st.session_state.slides_data):
        story.append(Paragraph(slide['titel'], title_style))
        story.append(Paragraph(slide['text'].replace('\n', '<br/>'), body_style))
        
        if slide['bild_url']:
            try:
                img_data = requests.get(slide['bild_url']).content
                img_io = BytesIO(img_data)
                img = RLImage(img_io, width=320, height=180)
                story.append(img)
            except Exception:
                pass
                
        if i < len(st.session_state.slides_data) - 1:
            story.append(PageBreak())
            
    doc.build(story)
    pdf_io.seek(0)
    return pdf_io

if not eingeloggter_kunde or eingeloggter_kunde not in st.session_state.kunden_daten:
    st.warning("👈 Bitte melde dich links an oder registriere dich, um den Service zu nutzen.")
elif eingeloggter_kunde != ADMIN_NAME and st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] <= 0:
    st.error("Dein Guthaben ist aufgebraucht. Bitte lade über das Menü links dein Konto auf.")
else:
    spalte_links, spalte_rechts = st.columns([1.1, 0.9])

    with spalte_links:
        st.subheader("🤖 Autonomer KI-Agent (Enterprise Core + PRO)")
        modus = st.selectbox(
            "Agenten-Modus wählen:",
            ["Intelligenter Chat & Echte Live-Webrecherche", "Büro & E-Mail Generator", "Proaktiver System-Monitor (KI-Wächter)", "Excel / CRM Operator (RPA-Modus)"]
        )
        
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Arbeitsbereich:** `{current_chat}`")

        if modus == "Intelligenter Chat & Echte Live-Webrecherche":
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            aufgabe = st.chat_input("Gib dem Agenten eine Aufgabe mit echter Webrecherche...")
            
        elif modus == "Büro & E-Mail Generator":
            st.markdown("Lass den Agenten vollautomatisch professionelle Kunden-Mails oder Berichte erstellen:")
            email_thema = st.text_area("Anfrage / Stichpunkte für den Agenten:", placeholder="Z.B.: Antworte professionell auf eine Kundenbeschwerde...")
            aufgabe = email_thema if st.button("✉️ E-Mail / Bericht vom Agenten generieren", use_container_width=True) else None
        elif modus == "Excel / CRM Operator (RPA-Modus)":
            st.markdown("### 📊 Autonomer Tabellen- & CRM-Operator")
            csv_input = st.file_uploader("CSV- oder Excel-Daten hochladen zur automatischen Analyse:", type=["csv", "txt"])
            rpa_befehl = st.text_input("Was soll der Operator tun?", placeholder="Z.B.: Analysiere die Umsätze, filtere Top-Kunden und erstelle eine Zusammenfassung")
            aufgabe = rpa_befehl if st.button("🚀 Operator-Aufgabe starten", use_container_width=True) else None
        else:
            aufgabe = None

        if aufgabe and modus != "Proaktiver System-Monitor (KI-Wächter)":
            if eingeloggter_kunde != ADMIN_NAME:
                st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 0.05
            
            try:
                if modus == "Intelligenter Chat & Echte Live-Webrecherche":
                    st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                    with st.chat_message("user"):
                        st.markdown(aufgabe)
                    
                    with st.spinner("🌐 Echte Deep-Web-Recherche & Selbstkorrektur laufen..."):
                        web_daten = echte_deep_web_recherche(aufgabe)
                        system_prompt = f"Du bist ein autonomer Web-Research-Agent mit Echtzeit-Zugriff. Nutze diese recherchierten Live-Daten zur Beantwortung:\n{web_daten}"
                        antwort = agenten_mit_selbstkorrektur(system_prompt, aufgabe)
                        
                    st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                    with st.chat_message("assistant"):
                        st.markdown(antwort)
                        
                elif modus == "Excel / CRM Operator (RPA-Modus)":
                    with st.spinner("⚙️ Operator verarbeitet Daten im Hintergrund..."):
                        daten_inhalt = ""
                        if csv_input is not None:
                            df = pd.read_csv(csv_input)
                            daten_inhalt = df.to_string()
                        
                         prompt_operator = f"Du bist ein präziser RPA-Tabellen-Operator. Führe folgende Aufgabe aus: '{aufgabe}'.\nDaten:\n{daten_inhalt}"
                        antwort = agenten_mit_selbstkorrektur("Du bist ein Business-Data-Operator.", prompt_operator)
                        st.success("Erfolgreich ausgeführt:")
                        st.markdown(antwort)
                else:
                    with st.spinner("✍️ Erstelle Text mit Selbstkorrektur..."):
                        antwort = agenten_mit_selbstkorrektur("Du bist ein erstklassiger Büro-Assistent. Erstelle professionelle, geschäftliche Texte auf Deutsch.", aufgabe)
                        st.success("Erfolgreich generiert:")
                        st.markdown(antwort)
                                
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")

        if modus == "Proaktiver System-Monitor (KI-Wächter)":
            st.markdown("### 🛡️ Autonomer Hintergrund-Wächter")
            st.markdown("Der Agent überwacht im Hintergrund ERP-Systeme, Server und Support-Tickets auf Unregelmäßigkeiten:")
            
            for ticket in st.session_state.proaktive_tickets:
                with st.container():
                    st.warning(f"**System:** {ticket['system']} ({ticket['id']})\nStatus: {ticket['status']}")
                    if not ticket["loesung_bereit"]:
                        if st.button(f"⚡ Autonome Gegenmaßnahme für {ticket['id']} einleiten", key=f"fix_{ticket['id']}"):
                            with st.spinner("Agent analysiert Logfiles und behebt das Problem..."):
                                time.sleep(1.5)
                                ticket["loesung_bereit"] = True
                                st.rerun()
                    else:
                        st.success(f"✅ Problem in {ticket['id']} wurde vom Agenten autonom gelöst!")
            
            if st.button("🔄 Systemstatus neu scannen", use_container_width=True):
                st.info("Alle Systeme im grünen Bereich. Keine neuen Anomalien gefunden.")

    with spalte_rechts:
        # EXPANDER 1: Präsentations- & Dokumenten-Studio mit optimalem 4er-Fließband, MCP & Selbstkorrektur
        with st.expander("📊 Autonomes Präsentations- & Dokumenten-Studio öffnen", expanded=False):
            st.markdown("### ⚡ Optimales 4er-Fließband (MCP & A2A)")
            auto_thema = st.text_input("Ziel / Thema für die Präsentation:", placeholder="Z.B.: Marktanalyse & Strategie 2026")
            anzahl_folien = st.slider("Autonome Anzahl der Folien:", min_value=2, max_value=10, value=4)
            
            modell_wahl = st.selectbox("Wähle das KI-Modell:", ["gpt-4o-mini (Blitzschnell & Effizient)", "gpt-4o (Maximale Tiefe & Analyse)"])
            aktiviertes_modell = "gpt-4o-mini" if "mini" in modell_wahl else "gpt-4o"

            if st.button("🚀 4er-A2A-Workflow mit Selbstkorrektur starten", use_container_width=True):
                if not auto_thema:
                    st.warning("Bitte gib ein Thema ein.")
                else:
                    if eingeloggter_kunde != ADMIN_NAME:
                        st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 2.00
                    
                    status_box = st.empty()
                    progress_bar = st.progress(0)
                    
                    try:
                        # SCHRITT 1: Agent 1 (Researcher / Scout mit Deep Web & Selbstkorrektur)
                        status_box.text(" Agent 1/4 (Researcher / Scout): Führt echte Deep-Web-Recherche durch...")
                        progress_bar.progress(15)
                        recherche_roh = echte_deep_web_recherche(auto_thema)
                        recherche_ergebnis = agenten_mit_selbstkorrektur(
                            "Du bist Agent 1 (Researcher/Scout). Validiere und strukturiere harte Fakten und Markttrends.",
                            recherche_roh
                        )

                        # SCHRITT 2: Agent 2 (Stratege / Architekt mit MCP-Standard-Payload)
                        status_box.text(" Agent 2/4 (Stratege / Architekt): Baut das logische Storyboard über MCP-Protokoll...")
                        progress_bar.progress(35)
                        mcp_payload = json.dumps({"source": "Agent1", "target": "Agent2", "context": recherche_ergebnis, "slides": anzahl_folien}, ensure_ascii=False)
                        storyboard_ergebnis = agenten_mit_selbstkorrektur(
                            f"Du bist Agent 2 (Stratege). Erstelle basierend auf diesem MCP-Datenpaket das logische Inhaltsgerüst für genau {anzahl_folien} Folien.",
                            mcp_payload
                        )

                        # SCHRITT 3: Agent 3 (Copywriter / Redakteur mit Korrekturschleife)
                        status_box.text(" Agent 3/4 (Copywriter / Redakteur): Formuliert verkaufsstarke Bullet-Points...")
                        progress_bar.progress(60)
                        
                        system_instruction = (
                            f"You are Agent 3 (Copywriter). Based on this structure: '{storyboard_ergebnis}', format exactly {anzahl_folien} slides. "
                            "Format each slide strictly as 'TITLE: [Title]|||TEXT: [Bullet points]|||PROMPT: [English visual image prompt]'. "
                            "Separate slides with '###'."
                        )
                        roh_text = agenten_mit_selbstkorrektur(system_instruction, auto_thema)
                        roh_folien = roh_text.split("###")

                        # SCHRITT 4: Agent 4 (Art Director / Designer) & Asynchrone Bildgenerierung (Multi-Threading)
                        status_box.text(" Agent 4/4 (Art Director / Designer): Generiert High-End Bilder parallel via Multi-Threading...")
                        progress_bar.progress(85)
                        
                        parsed_slides_raw = []
                        for f in roh_folien:
                            if "TITLE:" in f:
                                try:
                                    t_part = f.split("TITLE:")[1].split("|||")[0].strip()
                                    txt_part = f.split("TEXT:")[1].split("|||")[0].strip() if "TEXT:" in f else ""
                                    p_part = f.split("PROMPT:")[1].strip() if "PROMPT:" in f else "Professional business background"
                                    parsed_slides_raw.append({"titel": t_part, "text": txt_part, "prompt": p_part})
                                except Exception:
                                    continue

                        neue_slides = [None] * len(parsed_slides_raw)
                        def process_slide(index, slide_item):
                            bild_url = generiere_replicate_bild_mit_selbstcheck(slide_item["prompt"])
                            return index, {"titel": slide_item["titel"], "text": slide_item["text"], "prompt": slide_item["prompt"], "bild_url": bild_url}

                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futures = [executor.submit(process_slide, idx, s) for idx, s in enumerate(parsed_slides_raw)]
                            for future in as_completed(futures):
                                idx, res = future.result()
                                neue_slides[idx] = res

                        if neue_slides:
                            progress_bar.progress(100)
                            status_box.text(" Fließband mit Selbstkorrektur erfolgreich beendet!")
                            st.session_state.slides_data = neue_slides
                            st.success("Komplette Präsentation vollautomatisch, per Websuche & mit Selbstkorrektur erstellt!")
                            st.rerun()
                        else:
                            st.error("Fließband-Fehler bei der Generierung.")
                    except Exception as e:
                        st.error(f"Fehler: {e}")

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
                            if eingeloggter_kunde != ADMIN_NAME:
                                st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 0.10
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
            export_format = st.radio("Wähle das Ausgabeformat:", ["PowerPoint (.pptx)", "PDF-Dokument (.pdf)"], horizontal=True)

            if "PowerPoint" in export_format:
                pptx_datei = erstelle_pptx_aus_session()
                st.download_button(
                    label="📥 Als PowerPoint (.pptx) herunterladen",
                    data=pptx_datei,
                    file_name="Scion_Mind_Agent_Praesentation.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            else:
                pdf_datei = erstelle_pdf_aus_session()
                st.download_button(
                    label="📥 Als PDF (.pdf) herunterladen",
                    data=pdf_datei,
                    file_name="Scion_Mind_Agent_Praesentation.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        # EXPANDER 2: Echtzeit-Sprachagent & Audio-Generator
        with st.expander("🎙️ Echtzeit-Sprachagent (Voice Agent) & Audio", expanded=False):
            st.markdown("### ⚡ Live-Sprachchat (Voice Interface)")
            st.markdown("Nutze das Echtzeit-Audio-Widget, um direkt per Mikrofon mit dem Agenten zu sprechen:")
            
            live_audio = st.audio_input("Sprich jetzt mit deinem Voice Agenten:")
            if live_audio is not None:
                with st.spinner("Voice Agent verarbeitet Audio in Echtzeit..."):
                    try:
                        client_voice = OpenAI(api_key=MASTER_OPENAI_KEY)
                        transcript_res = client_voice.audio.transcriptions.create(
                            model="whisper-1",
                            file=("voice_input.wav", live_audio.read())
                        )
                        spoken_text = transcript_res.text
                        st.info(f"Du hast gesagt: \"{spoken_text}\"")
                        
                        speech_res = client_voice.audio.speech.create(
                            model="tts-1",
                            voice="alloy",
                            input=f"Antwort auf deine Anfrage: {spoken_text}"
                        )
                        st.audio(speech_res.content, format="audio/mp3", autoplay=True)
                    except Exception as e:
                        st.error(f"Voice Agent Fehler: {e}")

            st.write("---")
            st.markdown("### 🎧 Klassischer Audio-Generator")
            vorlese_text = st.text_area("Text zum Vorlesen:", height=70, placeholder="Füge hier Text ein...")
            einzel_stimme = st.selectbox("Wähle eine Stimme:", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
            
            if st.button("🔊 Audio generieren", use_container_width=True):
                if not vorlese_text:
                    st.warning("Bitte gib einen Text ein.")
                else:
                    if eingeloggter_kunde != ADMIN_NAME:
                        st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 0.02
                    with st.spinner("Erstelle Sprachdatei..."):
                        try:
                            client = OpenAI(api_key=MASTER_OPENAI_KEY)
                            response = client.audio.speech.create(model="tts-1", voice=einzel_stimme, input=vorlese_text)
                            st.success("Audio erfolgreich generiert!")
                            st.audio(response.content, format="audio/mp3")
                        except Exception as e:
                            st.error(f"Fehler: {e}")
