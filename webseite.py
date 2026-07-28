import streamlit as st
from openai import OpenAI
from pptx import Presentation
from io import BytesIO
import re
import requests
import time

st.set_page_config(page_title="Scion Mind", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #1e293b; color: white; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p { color: white !important; }
    .stButton button { background-color: #0f172a; color: white; border-radius: 8px; border: none; font-weight: bold; }
    .stButton button:hover { background-color: #334155; color: white; }
    input, textarea, [data-baseweb="input"] div, [data-baseweb="base-input"] { background-color: #ffffff !important; border-radius: 8px !important; border: 1px solid #cbd5e1 !important; }
    input:focus, textarea:focus, [data-baseweb="input"] input:focus { border-color: #0f172a !important; box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.1) !important; }
    [data-testid="stStatusWidget"] svg, [data-testid="stSpinner"] svg {
        width: 40px !important;
        height: 40px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Scion Mind")
st.markdown("*designed by Christian Schmidt*")
st.write("---")

MASTER_OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
VIDEO_API_KEY = st.secrets.get("VIDEO_API_KEY", MASTER_OPENAI_KEY)

ADMIN_NAME = "Christian"
ADMIN_PASS = "ScionMind#2026!Secured"

if "kunden_daten" not in st.session_state:
    st.session_state.kunden_daten = {
        ADMIN_NAME: {"passwort": ADMIN_PASS, "guthaben": 999.00},
        "kunde1": {"passwort": "123", "guthaben": 5.00}
    }

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

def bereinige_text(text):
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'___+', '', text)
    text = re.sub(r'---+', '', text)
    text = text.replace('###', '')
    return text.strip()

def erstelle_saubere_pptx(textinhalt):
    prs = Presentation()
    folien_teile = textinhalt.split("Folie")
    for f_text in folien_teile:
        if not f_text.strip():
            continue
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        title_shape = slide.shapes.title
        body_shape = slide.placeholders[1]
        
        zeilen = f_text.strip().split("\n")
        titel = bereinige_text(zeilen[0].replace(":", ""))
        title_shape.text = titel if titel else "Präsentation"
        
        inhalt_zeilen = []
        for z in zeilen[1:]:
            b = bereinige_text(z)
            if b:
                inhalt_zeilen.append(b)
                
        body_shape.text = "\n".join(inhalt_zeilen)
        
    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

# Hauptbereich-Prüfung
if not eingeloggter_kunde or eingeloggter_kunde not in st.session_state.kunden_daten:
    st.warning("👈 Bitte melde dich links an oder registriere dich, um den Service zu nutzen.")
elif eingeloggter_kunde != ADMIN_NAME and st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] <= 0:
    st.error("Dein Guthaben ist aufgebraucht. Bitte lade über das Menü links dein Konto auf.")
else:
    spalte_links, spalte_rechts = st.columns([1.2, 0.8])

    with spalte_links:
        st.subheader("🤖 KI-Arbeitsbereich (Skripte & Medien)")
        modus = st.selectbox(
            "Was möchtest du erstellen lassen?",
            ["Text-Recherche & Chat", "Präsentations-Struktur & Folien", "Video-Skript & Storyboard", "Profi-Präsentationsbilder (Replicate)"]
        )
        
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Chat:** `{current_chat}`")

        if modus in ["Text-Recherche & Chat", "Video-Skript & Storyboard"]:
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        st.markdown("🎤 **Oder per Spracheingabe steuern:**")
        Sprach_eingabe_chat = st.audio_input("Sprachnachricht aufnehmen", key="audio_chat")
        
        if Sprach_eingabe_chat is not None:
            try:
                client_stt = OpenAI(api_key=MASTER_OPENAI_KEY)
                transcript = client_stt.audio.transcriptions.create(
                    model="whisper-1",
                    file=("audio.wav", Sprach_eingabe_chat.read())
                )
                aufgabe = transcript.text
                st.info(f"Erkannter Text: \"{aufgabe}\"")
            except Exception as e:
                st.error(f"Spracherkennungsfehler: {e}")
                aufgabe = None
        else:
            if modus in ["Text-Recherche & Chat", "Video-Skript & Storyboard"]:
                aufgabe = st.chat_input("Stelle deine Frage oder lass dir ein Thema geben...")
            else:
                aufgabe_input = st.text_area("Beschreibe das gewünschte Bild für deine Präsentation:", height=120, placeholder="Z.B.: A professional modern corporate office with high-tech dashboard on screens...")
                Absenden = st.button("🚀 Profi-Bild jetzt generieren", use_container_width=True)
                aufgabe = aufgabe_input if Absenden else None

        if aufgabe and modus != "Profi-Präsentationsbilder (Replicate)":
            if eingeloggter_kunde != ADMIN_NAME:
                st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 0.05
            
            try:
                client = OpenAI(api_key=MASTER_OPENAI_KEY)
                
                st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                with st.chat_message("user"):
                    st.markdown(aufgabe)

                system_prompts = {
                    "Text-Recherche & Chat": "Du bist ein präziser, professioneller KI-Assistent. Antworte immer auf Deutsch.",
                    "Präsentations-Struktur & Folien": "Du bist ein Experte für Business-Präsentationen. Erstelle eine saubere Präsentation, bei der jede Folie mit 'Folie X: [Titel]' beginnt, gefolgt von prägnanten Stichpunkten. Antworte auf Deutsch.",
                    "Video-Skript & Storyboard": "Du bist ein professioneller Videoproduzent. Erstelle ein detailliertes Video-Skript für ein Video auf Deutsch."
                }
                
                messages_payload = [{"role": "system", "content": system_prompts.get(modus, "Du bist ein hilfreicher Assistent. Antworte immer auf Deutsch.")}]
                messages_payload.extend(st.session_state.chats[current_chat])

                with st.spinner("🦫 Das Arbeitstier schuftet im Hintergrund..."):
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages_payload
                    )
                    antwort = response.choices[0].message.content
                    
                    st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                    with st.chat_message("assistant"):
                        st.markdown(antwort)
                        
                        if modus == "Präsentations-Struktur & Folien":
                            pptx_datei = erstelle_saubere_pptx(antwort)
                            st.download_button(
                                label="📥 PowerPoint (.pptx) herunterladen",
                                data=pptx_datei,
                                file_name="Scion_Mind_Praesentation.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                use_container_width=True
                            )
                if modus == "Präsentations-Struktur & Folien":
                    st.rerun()
                                
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")

        # Direkte Bildgenerierung im linken Arbeitsbereich, wenn gewählt
        if modus == "Profi-Präsentationsbilder (Replicate)" and aufgabe:
            if eingeloggter_kunde != ADMIN_NAME:
                st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 0.10
            
            with st.spinner("🦫 Generiere hochprofessionelles Präsentationsbild..."):
                try:
                    headers = {
                        "Authorization": f"Bearer {VIDEO_API_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "respond-async"
                    }
                    # Flux Schnell Modell über Replicate für hochprofessionelle Bilder
                    data = {"input": {"prompt": aufgabe, "aspect_ratio": "16:9"}}
                    response = requests.post("https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions", json=data, headers=headers)
                    res_json = response.json()
                    
                    if "urls" in res_json:
                        get_url = res_json["urls"]["get"]
                        img_url = None
                        
                        for _ in range(30):
                            s_res = requests.get(get_url, headers={"Authorization": f"Bearer {VIDEO_API_KEY}"}).json()
                            if s_res.get("status") == "succeeded":
                                out = s_res["output"]
                                img_url = out[0] if isinstance(out, list) else out
                                break
                            elif s_res.get("status") == "failed":
                                break
                            time.sleep(3)
                            
                        if img_url:
                            st.success("Bild erfolgreich erstellt!")
                            st.image(img_url, caption="Dein professionelles Präsentationsbild", use_container_width=True)
                            
                            # Bild-Daten zum Download bereitstellen
                            img_data = requests.get(img_url).content
                            st.download_button("📥 Bild herunterladen (für PowerPoint)", data=img_data, file_name="praesentation_bild.jpg", mime="image/jpeg", use_container_width=True)
                        else:
                            st.error("Fehler beim Generieren des Bildes.")
                    else:
                        st.error("API-Verbindungsfehler zu Replicate.")
                except Exception as e:
                    st.error(f"Fehler: {e}")

    with spalte_rechts:
        st.subheader("🎬 5-Sekunden Video-Studio (Replicate)")
        
        st.markdown("Erstelle präzise 5-Sekunden-Videoszenen auf Basis von MiniMax:")
        video_prompt = st.text_area("Video-Prompt (auf Englisch):", height=100, placeholder="Z.B.: Cinematic drone shot over modern tech city...")
        
        if st.button("🚀 5-Sekunden Video generieren", use_container_width=True):
            if not video_prompt:
                st.warning("Bitte gib einen Prompt für das Video ein.")
            else:
                if eingeloggter_kunde != ADMIN_NAME:
                    st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 1.00
                
                status_text = st.empty()
                progress_bar = st.progress(0)
                
                try:
                    status_text.text("🦫 Generiere 5-Sekunden-Videoszene...")
                    progress_bar.progress(30)
                    
                    headers = {
                        "Authorization": f"Bearer {VIDEO_API_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "respond-async"
                    }
                    data = {"input": {"prompt": video_prompt}}
                    response = requests.post("https://api.replicate.com/v1/models/minimax/video-01/predictions", json=data, headers=headers)
                    res_json = response.json()
                    
                    if "urls" in res_json:
                        get_url = res_json["urls"]["get"]
                        v_url = None
                        
                        for _ in range(60):
                            s_res = requests.get(get_url, headers={"Authorization": f"Bearer {VIDEO_API_KEY}"}).json()
                            if s_res.get("status") == "succeeded":
                                out = s_res["output"]
                                v_url = out[0] if isinstance(out, list) else out
                                break
                            elif s_res.get("status") == "failed":
                                break
                            time.sleep(5)
                            
                        if v_url:
                            progress_bar.progress(100)
                            status_text.text("✅ Fertig!")
                            st.success("Deine 5-Sekunden-Szene:")
                            st.video(v_url)
                        else:
                            st.error("Fehler beim Generieren der Videoszene.")
                    else:
                        st.error("API-Fehler.")
                        
                except Exception as e:
                    st.error(f"Fehler im Studio: {e}")

        st.write("---")
        st.subheader("🎧 Text als Sprache ausgeben")
        vorlese_text = st.text_area("Text zum Vorlesen:", height=70, placeholder="Füge hier deinen Text ein...")
        einzel_stimme = st.selectbox("Wähle eine Stimme:", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], key="einzel_stimme")
        
        if st.button("🔊 Audio generieren", use_container_width=True):
            if not vorlese_text:
                st.warning("Bitte gib einen Text zum Vorlesen ein.")
            else:
                if eingeloggter_kunde != ADMIN_NAME:
                    st.session_state.kunden_daten[eingeloggter_kunde]["guthaben"] -= 0.02
                with st.spinner("🦫 Erstelle Sprachdatei..."):
                    try:
                        client = OpenAI(api_key=MASTER_OPENAI_KEY)
                        response = client.audio.speech.create(model="tts-1", voice=einzel_stimme, input=vorlese_text)
                        st.success("Audio erfolgreich generiert!")
                        st.audio(response.content, format="audio/mp3")
                    except Exception as e:
                        st.error(f"Fehler: {e}")
