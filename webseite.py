import streamlit as st
from openai import OpenAI
from pptx import Presentation
from pptx.util import Inches
from io import BytesIO
import re
import requests

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

GEHEIMES_PASSWORT = "scion2026"

with st.sidebar:
    st.header("🔑 Authentifizierung")
    passwort_eingabe = st.text_input("Passwort:", type="password")
    openai_key_eingabe = st.text_input("OpenAI API-Schlüssel:", type="password").strip()
    
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

def erstelle_pptx_mit_bildern(textinhalt, client):
    prs = Presentation()
    folien_teile = textinhalt.split("Folie")
    
    for f_text in folien_teile:
        if not f_text.strip():
            continue
            
        slide_layout = prs.slide_layouts[6] # Leeres Layout für perfekte Platzierung
        slide = prs.slides.add_slide(slide_layout)
        
        zeilen = f_text.strip().split("\n")
        titel = bereinige_text(zeilen[0].replace(":", ""))
        
        # Titel oben hinzufügen
        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.5), Inches(1.0))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = titel if titel else "Präsentation"
        p.font.size = 32
        p.font.bold = True
        
        # Inhalt links hinzufügen
        inhalt_zeilen = []
        for z in zeilen[1:]:
            bereinigt = bereinige_text(z)
            if bereinigt:
                inhalt_zeilen.append("• " + bereinigt)
                
        contentBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(6.0), Inches(5.0))
        tf_content = contentBox.text_frame
        tf_content.word_wrap = True
        tf_content.text = "\n".join(inhalt_zeilen)
        
        # Passendes Bild via DALL-E generieren und rechts einfügen
        try:
            img_response = client.images.generate(
                model="dall-e-3",
                prompt=f"Professional business illustration or photo representing: {titel}",
                size="1024x1024",
                quality="standard",
                n=1,
            )
            img_url = img_response.data[0].url
            img_data = requests.get(img_url).content
            img_stream = BytesIO(img_data)
            
            # Bild rechts auf der Folie platzieren
            slide.shapes.add_picture(img_stream, Inches(7.2), Inches(1.8), width=Inches(5.0))
        except Exception:
            pass # Falls ein Bild fehlschlägt, läuft die Erstellung stabil weiter
            
    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

if passwort_eingabe != GEHEIMES_PASSWORT:
    if passwort_eingabe != "":
        st.error("Falsches Passwort oder ungültiger Schlüssel.")
    st.warning("Bitte gib links dein Passwort ein, um den Service zu nutzen.")
else:
    spalte_links, spalte_rechts = st.columns([1.2, 0.8])

    with spalte_links:
        st.subheader("🤖 KI-Arbeitsbereich")
        modus = st.selectbox(
            "Was möchtest du erstellen lassen?",
            ["Text-Recherche & Chat", "Bild generieren (DALL-E)", "Präsentations-Struktur & Folien", "Video-Skript & Storyboard"]
        )
        
        current_chat = st.session_state.aktiver_chat
        st.markdown(f"**Aktiver Chat:** `{current_chat}`")

        st.markdown("🎙️ **Sprachaufnahme (optional):**")
        audio_aufnahme = st.audio_input("Klicke zum Aufnehmen auf das Mikrofon:")
        
        sprach_text = ""
        if audio_aufnahme is not None:
            if not openai_key_eingabe:
                st.warning("Bitte trage erst deinen API-Schlüssel ein, um Sprachaufnahmen zu transkribieren.")
            else:
                with st.spinner("Wandle Sprache in Text um..."):
                    try:
                        client = OpenAI(api_key=openai_key_eingabe)
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=("audio.wav", audio_aufnahme.read(), "audio/wav")
                        )
                        sprach_text = transcript.text
                        st.success(f"Erkannter Text: {sprach_text}")
                    except Exception as e:
                        st.error(f"Fehler bei der Spracherkennung: {e}")

        if modus == "Text-Recherche & Chat":
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        standard_text = sprach_text if sprach_text else ""
        
        if modus == "Text-Recherche & Chat":
            aufgabe = st.chat_input("Stelle deine Frage oder Aufgabe...")
        else:
            aufgabe_input = st.text_area("Deine Beschreibung oder Aufgabe dafür:", value=standard_text, height=120)
            Absenden = st.button("🚀 Aufgabe jetzt ausführen", use_container_width=True)
            aufgabe = aufgabe_input if Absenden else None

        if aufgabe:
            if not openai_key_eingabe:
                st.warning("Bitte trage in der linken Seitenleiste zuerst deinen OpenAI API-Schlüssel ein.")
            else:
                try:
                    client = OpenAI(api_key=openai_key_eingabe)
                    
                    if modus == "Bild generieren (DALL-E)":
                        with st.spinner("Die KI generiert dein Bild..."):
                            response = client.images.generate(
                                model="dall-e-3",
                                prompt=aufgabe,
                                size="1024x1024",
                                quality="standard",
                                n=1,
                            )
                            image_url = response.data[0].url
                            st.success("Dein Bild wurde erfolgreich erstellt:")
                            st.image(image_url, caption=aufgabe)
                    
                    else:
                        st.session_state.chats[current_chat].append({"role": "user", "content": aufgabe})
                        with st.chat_message("user"):
                            st.markdown(aufgabe)

                        system_prompts = {
                            "Text-Recherche & Chat": "Du bist ein präziser, professioneller KI-Assistent. Antworte immer auf Deutsch.",
                            "Präsentations-Struktur & Folien": "Du bist ein Experte für Business-Präsentationen. Erstelle eine saubere Präsentation, bei der jede Folie mit 'Folie X: [Titel]' beginnt, gefolgt von prägnanten Stichpunkten. Vermeide überflüssige Sonderzeichen.",
                            "Video-Skript & Storyboard": "Du bist ein professioneller Videoproduzent. Erstelle ein detailliertes Video-Skript mit Szenenbeschreibung, visuellen Hinweisen und Sprechtext auf Deutsch."
                        }
                        
                        messages_payload = [{"role": "system", "content": system_prompts.get(modus, "Du bist ein hilfreicher Assistent.")}]
                        messages_payload.extend(st.session_state.chats[current_chat])

                        with st.spinner("Die KI verarbeitet deine Anfrage und generiert passende Bilder für jede Folie..."):
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=messages_payload
                            )
                            antwort = response.choices[0].message.content
                            
                            st.session_state.chats[current_chat].append({"role": "assistant", "content": antwort})
                            with st.chat_message("assistant"):
                                st.markdown(antwort)
                                
                                if modus == "Präsentations-Struktur & Folien":
                                    pptx_datei = erstelle_pptx_mit_bildern(antwort, client)
                                    st.download_button(
                                        label="📥 PowerPoint mit Bildern (.pptx) herunterladen",
                                        data=pptx_datei,
                                        file_name="Scion_Mind_Praesentation_mit_Bildern.pptx",
                                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                        use_container_width=True
                                    )
                                
                except Exception as e:
                    st.error(f"Ein Fehler ist aufgetreten: {e}")

    with spalte_rechts:
        st.subheader("🎧 Text vorlesen lassen")
        st.markdown("Kopiere hier deinen Text hinein. Zu lange Texte werden automatisch aufgeteilt.")
        
        vorlese_text = st.text_area("Text zum Vorlesen:", height=200, placeholder="Füge hier deinen Text ein...")
        stimme = st.selectbox("Wähle eine Stimme:", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
        
        if st.button("🔊 Audio generieren", use_container_width=True):
            if not openai_key_eingabe:
                st.warning("Bitte trage in der linken Seitenleiste deinen API-Schlüssel ein.")
            elif not vorlese_text:
                st.warning("Bitte gib einen Text zum Vorlesen ein.")
            else:
                with st.spinner("Erstelle Sprachdatei..."):
                    try:
                        client = OpenAI(api_key=openai_key_eingabe)
                        chunks = [vorlese_text[i:i + 4000] for i in range(0, len(vorlese_text), 4000)]
                        audio_bytes_gesammt = bytearray()
                        
                        for chunk in chunks:
                            response = client.audio.speech.create(model="tts-1", voice=stimme, input=chunk)
                            audio_bytes_gesammt.extend(response.content)
                        
                        st.success("Audio erfolgreich generiert!")
                        st.audio(bytes(audio_bytes_gesammt), format="audio/mp3")
                        st.info("💡 **Tipp:** Du kannst die Geschwindigkeit im Player rechts unten auf **1.2x**, **1.4x** oder **1.6x** einstellen!")
                    except Exception as e:
                        st.error(f"Fehler bei der Audioerstellung: {e}")
