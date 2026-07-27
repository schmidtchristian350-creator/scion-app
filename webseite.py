import streamlit as st
from openai import OpenAI

st.title("Scion Mind")
st.markdown("*designed by Christian Schmidt*")
st.write("---")

GEHEIMES_PASSWORT = "scion2026"
passwort_eingabe = st.text_input("Bitte gib deinen Lizenz-Schlüssel bzw. dein Passwort ein:", type="password")

if passwort_eingabe != GEHEIMES_PASSWORT:
    if passwort_eingabe != "":
        st.error("Falsches Passwort oder ungültiger Schlüssel.")
    st.warning("Bitte authentifiziere dich, um den Service zu nutzen.")
else:
    st.success("Zugriff erfolgreich! Willkommen bei Scion Mind.")
    
    # Schlüssel-Eingabe
    openai_key_eingabe = st.text_input("Trage hier deinen OpenAI API-Schlüssel ein:", type="password").strip()
    
    # Auswahl der gewünschten Funktion
    modus = st.selectbox(
        "Was möchtest du erstellen lassen?",
        ["Text-Recherche & Chat", "Bild generieren (DALL-E)", "Präsentations-Struktur & Folien", "Video-Skript & Storyboard"]
    )
    
    # Chat-Verlauf im Speicher der App behalten, wenn der Modus wechselt
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Zeige den bisherigen Chatverlauf an (nur im Text-Modus sinnvoll)
    if modus == "Text-Recherche & Chat":
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Eingabefeld für die neue Frage/Aufgabe
    if aufgabe := st.chat_input("Stelle deine Frage oder Aufgabe...") if modus == "Text-Recherche & Chat" else st.text_area("Deine Beschreibung oder Aufgabe dafür:"):
        
        if not openai_key_eingabe:
            st.warning("Bitte trage zuerst deinen OpenAI API-Schlüssel ein.")
        else:
            try:
                client = OpenAI(api_key=openai_key_eingabe)
                
                # Modus: Bild generieren
                if modus == "Bild generieren (DALL-E)":
                    with st.info("Die KI generiert dein Bild..."):
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
                
                # Modus: Chat / Text / Präsentation / Video
                else:
                    # Benutzer-Nachricht dem Verlauf hinzufügen
                    st.session_state.messages.append({"role": "user", "content": aufgabe})
                    with st.chat_message("user"):
                        st.markdown(aufgabe)

                    system_prompts = {
                        "Text-Recherche & Chat": "Du bist ein präziser, professioneller KI-Assistent. Antworte immer auf Deutsch.",
                        "Präsentations-Struktur & Folien": "Du bist ein Experte für Business-Präsentationen. Erstelle eine klare, professionelle Folienstruktur mit Stichpunkten für jede Folie auf Deutsch.",
                        "Video-Skript & Storyboard": "Du bist ein professioneller Videoproduzent. Erstelle ein detailliertes Video-Skript mit Szenenbeschreibung, visuellen Hinweisen und Sprechtext auf Deutsch."
                    }
                    
                    # Gesamten Chatverlauf an OpenAI übergeben
                    messages_payload = [{"role": "system", "content": system_prompts.get(modus, "Du bist ein hilfreicher Assistent.")}]
                    messages_payload.extend(st.session_state.messages)

                    with st.spinner("Die KI verarbeitet deine Anfrage..."):
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages_payload
                        )
                        antwort = response.choices[0].message.content
                        
                        # Assistenten-Antwort dem Verlauf hinzufügen
                        st.session_state.messages.append({"role": "assistant", "content": antwort})
                        with st.chat_message("assistant"):
                            st.markdown(antwort)
                            
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")
