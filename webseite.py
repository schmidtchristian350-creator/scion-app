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
    
    # Schlüssel-Eingabe mit automatischem Leerzeichen-Entferner (.strip())
    openai_key_eingabe = st.text_input("Trage hier deinen OpenAI API-Schlüssel ein:", type="password").strip()
    
    # Auswahl der gewünschten Funktion
    modus = st.selectbox(
        "Was möchtest du erstellen lassen?",
        ["Text-Recherche & Analyse", "Bild generieren (DALL-E)", "Präsentations-Struktur & Folien", "Video-Skript & Storyboard"]
    )
    
    aufgabe = st.text_area("Deine Beschreibung oder Aufgabe dafür:")

    if st.button("Ausführen"):
        if not openai_key_eingabe:
            st.warning("Bitte trage zuerst deinen OpenAI API-Schlüssel ein.")
        elif not aufgabe:
            st.warning("Bitte gib eine Beschreibung ein.")
        else:
            st.info("Die KI verarbeitet deine Anfrage...")
            try:
                client = OpenAI(api_key=openai_key_eingabe)
                
                # Modus 1: Bild generieren
                if modus == "Bild generieren (DALL-E)":
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
                
                # Modus 2: Präsentationen, Videos oder Text
                else:
                    system_prompts = {
                        "Text-Recherche & Analyse": "Du bist ein präziser professioneller Recherche-Assistent. Antworte immer auf Deutsch.",
                        "Präsentations-Struktur & Folien": "Du bist ein Experte für Business-Präsentationen. Erstelle eine klare, professionelle Folienstruktur mit Stichpunkten für jede Folie auf Deutsch.",
                        "Video-Skript & Storyboard": "Du bist ein professioneller Videoproduzent. Erstelle ein detailliertes Video-Skript mit Szenenbeschreibung, visuellen Hinweisen und Sprechtext auf Deutsch."
                    }
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompts.get(modus, "Du bist ein hilfreicher Assistent.")},
                            {"role": "user", "content": aufgabe}
                        ]
                    )
                    antwort = response.choices[0].message.content
                    st.success("Ergebnis:")
                    st.write(antwort)
                    
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")
