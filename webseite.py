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
    
    # Hier tippst du den Schlüssel gleich einfach selbst ein
    openai_key_eingabe = st.text_input("Trage hier deinen OpenAI API-Schlüssel ein:", type="password")
    
    aufgabe = st.text_input("Deine Frage oder Recherche-Aufgabe:")

    if st.button("Analyse starten"):
        if not openai_key_eingabe:
            st.warning("Bitte trage zuerst deinen OpenAI API-Schlüssel ein.")
        elif not aufgabe:
            st.warning("Bitte trage eine Recherche-Aufgabe ein.")
        else:
            st.info("Die KI verarbeitet deine Anfrage...")
            try:
                client = OpenAI(api_key=openai_key_eingabe)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Du bist ein professioneller, präziser KI-Assistent für Markt- und Web-Recherchen. Antworte immer auf Deutsch."},
                        {"role": "user", "content": aufgabe}
                    ]
                )
                antwort = response.choices[0].message.content
                st.success("Ergebnis:")
                st.write(antwort)
            except Exception as e:
                st.error(f"Ein Fehler ist aufgetreten: {e}")
