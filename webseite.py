import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Scion-Mind", layout="wide")

st.title("Scion Mind")
st.markdown("*designed by Christian Schmidt*")
st.write("---")

GEHEIMES_PASSWORT = "scion2026"

# Sidebar für die Chat-Historie und Einstellungen
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

# Hauptbereichprüfung
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

        if modus == "Text-Recherche & Chat":
            for message in st.session_state.chats[current_chat]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        if aufgabe := st.chat_input("Stelle deine Frage oder Aufgabe...") if modus == "Text-Recherche & Chat" else st.text_area("Deine Beschreibung oder Aufgabe dafür:"):
            
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
                            "Präsentations-Struktur & Folien": "Du bist ein Experte für Business-Präsentationen. Erstelle eine klare, professionelle Folienstruktur mit Stichpunkten für jede Folie auf Deutsch.",
                            "Video-Skript & Storyboard": "Du bist ein professioneller Videoproduzent. Erstelle ein detailliertes Video-Skript mit Szenenbeschreibung, visuellen Hinweisen und Sprechtext auf Deutsch."
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
                                
                except Exception as e:
                    st.error(f"Ein Fehler ist aufgetreten: {e}")

    # Rechte Spalte: Vorlese-Fenster mit automatischem Längen-Check
    with spalte_rechts:
        st.subheader("🎧 Text vorlesen lassen")
        st.markdown("Kopiere hier deinen Text hinein. Zu lange Texte werden automatisch aufgeteilt.")
        
        vorlese_text = st.text_area("Text zum Vorlesen:", height=200, placeholder="Füge hier deinen Text ein...")
        
        stimme = st.selectbox("Wähle eine Stimme:", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
        
        if st.button("Audio generieren"):
            if not openai_key_eingabe:
                st.warning("Bitte trage in der linken Seitenleiste deinen API-Schlüssel ein.")
            elif not vorlese_text:
                st.warning("Bitte gib einen Text zum Vorlesen ein.")
            else:
                with st.spinner("Erstelle Sprachdatei (kann bei langen Texten einen Moment dauern)..."):
                    try:
                        client = OpenAI(api_key=openai_key_eingabe)
                        
                        # Text in 4000er-Häppchen aufteilen, falls er zu lang ist
                        chunks = [vorlese_text[i:i + 4000] for i in range(0, len(vorlese_text), 4000)]
                        audio_bytes_gesammt = bytearray()
                        
                        for chunk in chunks:
                            response = client.audio.speech.create(
                                model="tts-1",
                                voice=stimme,
                                input=chunk
                            )
                            audio_bytes_gesammt.extend(response.content)
                        
                        st.success("Audio erfolgreich generiert!")
                        st.audio(bytes(audio_bytes_gesammt), format="audio/mp3")
                        
                        st.info("💡 **Tipp:** Du kannst die Geschwindigkeit im Player rechts unten (über die drei Punkte `...`) auf **1.2x**, **1.4x** oder **1.6x** einstellen!")
                        
                    except Exception as e:
                        st.error(f"Fehler bei der Audioerstellung: {e}")
