import streamlit as st
from openai import OpenAI
from pptx import Presentation
from io import BytesIO
import re

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
    </style>
""", unsafe_allow_html=True)

st.title("Scion Mind")
st.markdown("*designed by Christian Schmidt*")
st.write("---")

# DEIN MASTER-SCHLÜSSEL
MASTER_OPENAI_KEY = "sk-DEIN-ECHTER-OPENAI-API-SCHLUESSEL-HIER-EINTRAGEN"

# Kundendatenbank im Speicher
if "kunden_guthaben" not in st.session_state:
    st.session_state.kunden_guthaben = {
        "kunde1": 5.00,
        "kunde2": 10.00
    }

with st.sidebar:
    st.header("🔑 Kunden-Login")
    kunden_name = st.text_input("Dein Kunden-Token / Name:")
    
    if kunden_name in st.session_state.kunden_guthaben:
        guthaben = st.session_state.kunden_guthaben[kunden_name]
        st.success(f"Eingeloggt als: {kunden_name}")
        st.metric(label="Dein Guthaben", value=f"{guthaben:.2f} €")
        if guthaben <= 0:
            st.error("Dein Guthaben ist leer. Bitte lade dein Konto auf!")
    elif kunden_name != "":
        st.error("Unbekannter Token / Kein Guthaben gefunden.")

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
        
        # Hier behoben: klassische, saubere Schleife ohne Syntax-Fehler
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
if not kunden_name or kunden_name not in st.session_state.kunden_guthaben:
    st.warning("👈 Bitte gib links deinen Kundennamen / Token ein, um den Service zu starten.")
elif st.session_state.kunden_guthaben[kunden_name] <= 0:
    st.error("Dein Prepaid-Guthaben ist aufgebraucht. Bitte wende dich an den Administrator, um neues Guthaben aufzuladen.")
else:
    spalte_links, spalte_rechts = st.columns([1.2, 0.8])

    with spalte_links:
        st.subheader("🤖 KI-Arbeitsbereich")
        modus = st.selectbox(
            "Was möchtest du erstellen lassen?",
            ["Text-Recherche & Chat", "Präsentations-Struktur & Folien", "Video-Skript & Storyboard"]
        )
        
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Chat:** `{current_chat}`")

        if modus == "Text-Recherche & Chat":
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if modus == "Text-Recherche & Chat":
            aufgabe = st.chat_input("Stelle deine Frage oder Aufgabe...")
        else:
            aufgabe_input = st.text_area("Deine Beschreibung oder Aufgabe dafür:", height=120)
            Absenden = st.button("🚀 Aufgabe jetzt ausführen", use_container_width=True)
            aufgabe = aufgabe_input if Absenden else None

        if aufgabe:
            st.session_state.kunden_guthaben[kunden_name] -= 0.05
            
            try:
                client = OpenAI(api_key=MASTER_OPENAI_KEY)
                
                st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                with st.chat_message("user"):
                    st.markdown(aufgabe)

                system_prompts = {
                    "Text-Recherche & Chat": "Du bist ein präziser, professioneller KI-Assistent. Antworte immer auf Deutsch.",
                    "Präsentations-Struktur & Folien": "Du bist ein Experte für Business-Präsentationen. Erstelle eine saubere Präsentation, bei der jede Folie mit 'Folie X: [Titel]' beginnt, gefolgt von prägnanten Stichpunkten.",
                    "Video-Skript & Storyboard": "Du bist ein professioneller Videoproduzent. Erstelle ein detailliertes Video-Skript mit Szenenbeschreibung und Sprechtext auf Deutsch."
                }
                
                messages_payload = [{"role": "system", "content": system_prompts.get(modus, "Du bist ein hilfreicher Assistent.")}]
                messages_payload.extend(st.session_state.chats[current_chat])

                with st.spinner("Die KI verarbeitet deine Anfrage..."):
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
                st.rerun()
                                
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")

    with spalte_rechts:
        st.subheader("🎧 Text vorlesen lassen")
        vorlese_text = st.text_area("Text zum Vorlesen:", height=200, placeholder="Füge hier deinen Text ein...")
        stimme = st.selectbox("Wähle eine Stimme:", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
        
        if st.button("🔊 Audio generieren", use_container_width=True):
            if not vorlese_text:
                st.warning("Bitte gib einen Text zum Vorlesen ein.")
            else:
                st.session_state.kunden_guthaben[kunden_name] -= 0.02
                with st.spinner("Erstelle Sprachdatei..."):
                    try:
                        client = OpenAI(api_key=MASTER_OPENAI_KEY)
                        chunks = [vorlese_text[i:i + 4000] for i in range(0, len(vorlese_text), 4000)]
                        audio_bytes_gesammt = bytearray()
                        
                        for chunk in chunks:
                            response = client.audio.speech.create(model="tts-1", voice=stimme, input=chunk)
                            audio_bytes_gesammt.extend(response.content)
                        
                        st.success("Audio erfolgreich generiert!")
                        st.audio(bytes(audio_bytes_gesammt), format="audio/mp3")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler bei der Audioerstellung: {e}")
