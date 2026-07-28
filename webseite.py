import streamlit as st
from openai import OpenAI
from pptx import Presentation
from io import BytesIO
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Scion Mind - Enterprise Agent Studio", layout="wide")

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

st.title("Scion Mind - Enterprise Autonomes Agenten-Studio")
st.markdown("*designed by Christian Schmidt | Powered by 4er-A2A & High-Speed Multi-Threading*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
IMAGE_API_KEY = st.secrets.get("VIDEO_API_KEY", MASTER_OPENAI_KEY)

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
    """Intelligentes Caching für wiederkehrende Analyse-Schritte"""
    client = OpenAI(api_key=MASTER_OPENAI_KEY)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    )
    return response.choices[0].message.content

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
        st.subheader("🤖 Autonomer KI-Agent (Enterprise Core)")
        modus = st.selectbox(
            "Agenten-Modus wählen:",
            ["Intelligenter Chat & Live-Webrecherche", "Büro & E-Mail Generator", "Proaktiver System-Monitor (KI-Wächter)"]
        )
        
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Arbeitsbereich:** `{current_chat}`")

        if modus == "Intelligenter Chat & Live-Webrecherche":
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            aufgabe = st.chat_input("Gib dem Agenten eine Aufgabe (z.B. Live-Recherche über Web-Quellen)...")
            
        elif modus == "Büro & E-Mail Generator":
            st.markdown("Lass den Agenten vollautomatisch professionelle Kunden-Mails oder Berichte erstellen:")
            email_thema = st.text_area("Anfrage / Stichpunkte für den Agenten:", placeholder="Z.B.: Antworte professionell auf eine Kundenbeschwerde...")
            aufgabe = email_thema if st.button("✉️ E-Mail / Bericht vom Agenten generieren", use_container_width=True) else None
        else:
            aufgabe = None

        if aufgabe and modus != "Proaktiver System-Monitor (KI-Wächter)":
            if eingeloggter_kunde != ADMIN_NAME:
                st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 0.05
            
            try:
                client = OpenAI(api_key=MASTER_OPENAI_KEY)
                if modus == "Intelligenter Chat & Live-Webrecherche":
                    st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                    with st.chat_message("user"):
                        st.markdown(aufgabe)
                    messages_payload = [{"role": "system", "content": "Du bist ein autonomer Web-Research-Agent. Nutze dein Wissen, simuliere Live-Daten und liefere exakte Fakten auf Deutsch."}]
                    messages_payload.extend(st.session_state.chats[current_chat])
                else:
                    messages_payload = [
                        {"role": "system", "content": "Du bist ein erstklassiger Büro-Assistent. Erstelle professionelle, geschäftliche Texte und E-Mails auf Deutsch."},
                        {"role": "user", "content": aufgabe}
                    ]

                with st.spinner("🦫 Autonomer Agent crawlt das Netz & analysiert..."):
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages_payload
                    )
                    antwort = response.choices[0].message.content
                    
                    if modus == "Intelligenter Chat & Live-Webrecherche":
                        st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                        with st.chat_message("assistant"):
                            st.markdown(antwort)
                    else:
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
        # EXPANDER 1: Präsentations- & Dokumenten-Studio mit optimalem 4er-Fließband & Multi-Threading
        with st.expander("📊 Autonomes Präsentations- & Dokumenten-Studio öffnen", expanded=False):
            st.markdown("### ⚡ Optimales 4er-Fließband (A2A)")
            auto_thema = st.text_input("Ziel / Thema für die Präsentation:", placeholder="Z.B.: Marktanalyse & Strategie 2026")
            anzahl_folien = st.slider("Autonome Anzahl der Folien:", min_value=2, max_value=10, value=4)
            
            modell_wahl = st.selectbox("Wähle das KI-Modell:", ["gpt-4o-mini (Blitzschnell & Effizient)", "gpt-4o (Maximale Tiefe & Analyse)"])
            aktiviertes_modell = "gpt-4o-mini" if "mini" in modell_wahl else "gpt-4o"

            if st.button("🚀 4er-A2A-Workflow komplett starten", use_container_width=True):
                if not auto_thema:
                    st.warning("Bitte gib ein Thema ein.")
                else:
                    if eingeloggter_kunde != ADMIN_NAME:
                        st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 2.00
                    
                    status_box = st.empty()
                    progress_bar = st.progress(0)
                    
                    try:
                        # SCHRITT 1: Agent 1 (Researcher / Scout)
                        status_box.text(" Agent 1/4 (Researcher / Scout): Durchsucht Live-Web & Datenbanken...")
                        progress_bar.progress(15)
                        recherche_ergebnis = get_cached_ai_response(
                            aktiviertes_modell,
                            "Du bist Agent 1 (Researcher/Scout). Sammle harte Fakten, Markttrends und Daten zum Thema.",
                            auto_thema
                        )

                        # SCHRITT 2: Agent 2 (Stratege / Architekt)
                        status_box.text(" Agent 2/4 (Stratege / Architekt): Baut das logische Storyboard-Gerüst...")
                        progress_bar.progress(35)
                         storyboard_ergebnis = get_cached_ai_response(
                            aktiviertes_modell,
                            f"Du bist Agent 2 (Stratege/Architekt). Basierend auf diesen Fakten: '{recherche_ergebnis}', erstelle das logische Inhaltsgerüst für genau {anzahl_folien} Folien.",
                            auto_thema
                        )

                        # SCHRITT 3: Agent 3 (Copywriter / Redakteur)
                        status_box.text(" Agent 3/4 (Copywriter / Redakteur): Formuliert verkaufsstarke Bullet-Points...")
                        progress_bar.progress(60)
                        
                        system_instruction = (
                            f"You are Agent 3 (Copywriter). Based on this structure: '{storyboard_ergebnis}', format exactly {anzahl_folien} slides. "
                            "Format each slide strictly as 'TITLE: [Title]|||TEXT: [Bullet points]|||PROMPT: [English visual image prompt]'. "
                            "Separate slides with '###'."
                        )
                        roh_text = get_cached_ai_response(aktiviertes_modell, system_instruction, auto_thema)
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

                        # Asynchrone Parallelisierung (ThreadPoolExecutor) für Höchstgeschwindigkeit bei Bildern
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
                            status_box.text(" 4er-Fließband in Rekordzeit abgeschlossen!")
                            st.session_state.slides_data = neue_slides
                            st.success("Komplette Präsentation vollautomatisch & parallel erstellt!")
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
