import streamlit as st
from openai import OpenAI

# Trage hier deinen echten OpenAI API-Schlüssel direkt in die Anführungszeichen ein
client = OpenAI(api_key="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")

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
    
    aufgabe = st.text_input("Deine Frage oder Recherche-Aufgabe:")

    if st.button("Analyse starten"):
        if aufgabe:
            st.info("Die KI verarbeitet deine Anfrage...")
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
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
        else:
            st.warning("Bitte trage zuerst eine Aufgabe ein.")
