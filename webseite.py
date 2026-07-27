import streamlit as st
from openai import OpenAI

# Dein echter, neuer Schlüssel ist hier hinterlegt
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
        else:
            st.warning("Bitte trage zuerst eine Aufgabe ein.")
