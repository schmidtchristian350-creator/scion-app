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
