import os
import streamlit as st
from openai import OpenAI

# OpenAI Client initialisieren
client = OpenAI(api_key="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")

# --- BENUTZEROBERFLÄCHE ---
st.title("Scion Mind")
st.markdown("*designed by Christian Schmidt*")
st.write("---")

# Sichere Login-Schranke für deine Kunden
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
                # Direkte, schnelle Abfrage über die OpenAI-Schnittstelle
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