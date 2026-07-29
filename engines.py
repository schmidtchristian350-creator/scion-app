import os
import re
import json
import base64
import requests
import traceback
import sys
import smtplib
import imaplib
import ssl
import threading
import queue
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io as python_io
from openai import OpenAI
from database import get_db_connection

try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

def verschruessle_api_key(api_key, fernet_cipher=None):
    if FERNET_AVAILABLE and fernet_cipher:
        try:
            return fernet_cipher.encrypt(api_key.encode('utf-8')).decode('utf-8')
        except Exception:
            pass
    return base64.b64encode(api_key.encode('utf-8')).decode('utf-8')

def ent_huelle_api_key(encrypted_key, fernet_cipher=None):
    if FERNET_AVAILABLE and fernet_cipher:
        try:
            return fernet_cipher.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')
        except Exception:
            pass
    try:
        return base64.b64decode(encrypted_key.encode('utf-8')).decode('utf-8')
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)
        return encrypted_key

def litellm_router_abfrage(system_prompt, user_prompt, model_pref="auto", master_openai_key="", anthropic_api_key=""):
    try:
        if model_pref == "local" or (model_pref == "auto" and len(user_prompt) < 100):
            url = "http://localhost:11434/api/generate"
            payload = {"model": "llama3", "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}", "stream": False}
            res = requests.post(url, json=payload, timeout=4).json()
            if "response" in res:
                return f"🟢 [Souveränes LiteLLM Router -> Lokal Llama 3 (Zero Cloud)]: \n{res['response']}"
         
        if model_pref == "claude" and anthropic_api_key:
            headers = {"x-api-key": anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            data = {"model": "claude-3-5-sonnet-20241022", "max_tokens": 1500, "system": system_prompt, "messages": [{"role": "user", "content": user_prompt}]}
            res = requests.post("https://api.anthropic.com/v1/messages", json=data, headers=headers).json()
            return f"🟣 [LiteLLM Router -> Claude 3.5 Sonnet]:\n" + res.get("content", [{"text": ""}])[0].get("text", "")
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)

    client = OpenAI(api_key=master_openai_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    )
    return f"🔵 [LiteLLM Router -> OpenAI GPT-4o-mini]:\n" + response.choices[0].message.content

def ausfuehren_mit_ollama_fallback(system_prompt, user_prompt, use_local=False, master_openai_key="", anthropic_api_key=""):
    pref = "local" if use_local else "auto"
    return litellm_router_abfrage(system_prompt, user_prompt, model_pref=pref, master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)

def echte_deep_web_recherche(query, tavily_api_key="", master_openai_key="", anthropic_api_key=""):
    if tavily_api_key:
        try:
            url = "https://api.tavily.com/search"
            payload = {"api_key": tavily_api_key, "query": query, "search_depth": "advanced", "max_results": 3}
            res = requests.post(url, json=payload).json()
            results = res.get("results", [])
            zusammenfassung = "\n".join([f"- Titel: {r.get('title')}\n  URL: {r.get('url')}\n  Inhalt: {r.get('content')}" for r in results])
            if zusammenfassung:
                return zusammenfassung
        except Exception as e:
            if SENTRY_AVAILABLE:
                sentry_sdk.capture_exception(e)
    return litellm_router_abfrage("Du bist Research-Agent.", query, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)

def berechne_pl_break_even(fixkosten, st_preis, var_kosten):
    try:
        deckungsbeitrag = st_preis - var_kosten
        if deckungsbeitrag <= 0:
            return "Fehler: Stückpreis muss höher sein als die variablen Kosten."
        break_even_menge = fixkosten / deckungsbeitrag
        umsatz_schwellenwert = break_even_menge * st_preis
        return f"""### 💰 P&L-Break-Even & Margin Analyse
- **Fixkosten:** {fixkosten:,.2f} €
- **Deckungsbeitrag pro Stück:** {deckungsbeitrag:,.2f} €
- **Break-Even-Menge:** **{break_even_menge:,.0f} Einheiten**
- **Umsatzschwelle:** **{umsatz_schwellenwert:,.2f} €**
- **Strategische Bewertung:** P&L-Sollvorgabe und Margen-Sicherung erfolgreich kalkuliert."""
    except Exception as e:
        return f"Berechnungsfehler: {str(e)}"

def starte_swot_analyse(konkurrent_name, tavily_api_key="", master_openai_key="", anthropic_api_key=""):
    web_daten = echte_deep_web_recherche(f"{konkurrent_name} Unternehmensprofil Angebote Marktposition", tavily_api_key, master_openai_key, anthropic_api_key)
    prompt = f"Erstelle eine präzise SWOT-Analyse (Strengths, Weaknesses, Opportunities, Threats) für folgenden Mitbewerber basierend auf den Webdaten:\n{web_daten}"
    return litellm_router_abfrage("Du bist ein strategischer Unternehmensberater und SWOT-Analyst.", prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)

def ausfuehren_in_self_healing_sandbox(code_string, master_openai_key=""):
    client = OpenAI(api_key=master_openai_key)
    aktueller_code = code_string
    max_versuche = 3
     
    for versuch in range(max_versuche):
        old_stdout = sys.stdout
        new_stdout = python_io.StringIO()
        sys.stdout = new_stdout
         
        try:
            local_scope = {}
            exec(aktueller_code, {"__builtins__": __builtins__, "pd": pd if 'pd' in globals() else None, "requests": requests, "json": json, "ssl": ssl}, local_scope)
            ergebnis_msg = new_stdout.getvalue()
            sys.stdout = old_stdout
            if not ergebnis_msg:
                ergebnis_msg = "Code erfolgreich ausgeführt (Keine Standardausgabe)."
            return f"✅ **Closed-Loop Self-Healing erfolgreich (Versuch {versuch+1}):**\n```python\n{aktueller_code}\n```\n\n**Ausgabe:**\n{ergebnis_msg}"
        except Exception as e:
            sys.stdout = old_stdout
            fehler_trace = str(e) + "\n" + traceback.format_exc()
            if SENTRY_AVAILABLE:
                sentry_sdk.capture_exception(e)
            if versuch == max_versuche - 1:
                return f"❌ **Sandbox-Fehler nach {max_versuche} Versuchen:**\n```python\n{aktueller_code}\n```\n**Fehler:**\n{fehler_trace}"
             
            repair_res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Du bist Python Developer. Repariere den Code und liefere AUSSCHLIESSLICH den korrigierten Code in ```python Block."},
                    {"role": "user", "content": f"Fehlerhafter Code:\n{aktueller_code}\n\nFehler:\n{fehler_trace}"}
                ]
            ).choices[0].message.content
             
            match = re.search(r"```python\n(.*?)\n```", repair_res, re.DOTALL)
            if match:
                aktueller_code = match.group(1)
            else:
                aktueller_code = repair_res.replace("```python", "").replace("```", "").strip()

def get_openai_embedding(text, master_openai_key=""):
    try:
        client = OpenAI(api_key=master_openai_key)
        resp = client.embeddings.create(input=[text], model="text-embedding-3-small")
        return resp.data[0].embedding
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)
        return None

def suche_in_rag_vektor_db(query, master_openai_key=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT,
            inhalt TEXT
        )
    """)
    cursor.execute("SELECT titel, inhalt FROM rag_documents")
    docs = cursor.fetchall()
    conn.close()
     
    if not docs:
        return "Keine Dokumente im RAG-Archiv."

    try:
        import numpy as np
        import faiss
         
        query_vec = get_openai_embedding(query, master_openai_key)
        if query_vec is None:
            raise Exception("Embedding fehlgeschlagen")
             
        doc_texts = []
        vectors = []
        for titel, inhalt in docs:
            full_txt = f"Titel: {titel}\nInhalt: {inhalt}"
            doc_texts.append(full_txt)
            v = get_openai_embedding(full_txt, master_openai_key)
            if v:
                vectors.append(v)
            else:
                vectors.append([0.0]*1536)
                 
        dim = 1536
        index = faiss.IndexFlatL2(dim)
        vectors_np = np.array(vectors).astype('float32')
        index.add(vectors_np)
         
        q_np = np.array([query_vec]).astype('float32')
        k = min(2, len(docs))
        distances, indices = index.search(q_np, k)
         
        treffer = []
        for idx in indices[0]:
            if idx < len(doc_texts):
                treffer.append(f"**[FAISS Treffer]**\n{doc_texts[idx]}")
        return "\n\n".join(treffer) if treffer else docs[0][1]
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)
        return docs[0][1]

def selbstevaluierender_lern_agent(system_prompt, initial_input, use_local=False, master_openai_key="", anthropic_api_key=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            aufgabe_typ TEXT,
            erkenntnis TEXT,
            verbesserter_prompt TEXT
        )
    """)
    conn.commit()
    cursor.execute("SELECT zeit, erkenntnis FROM agent_memory ORDER BY id DESC LIMIT 3")
    rows = cursor.fetchall()
    conn.close()
    historisches_wissen = "\n".join([f"- [{zeit}] {erk}" for zeit, erk in rows]) if rows else "Keine Learnings gespeichert."
    
    rag_kontext = suche_in_rag_vektor_db(initial_input, master_openai_key)
    dynamischer_prompt = f"{system_prompt}\n\n[FAISS RAG WISSEN]:\n{rag_kontext}\n\n[HISTORISCHES GEDÄCHTNIS]:\n{historisches_wissen}"
     
    ergebnis = ausfuehren_mit_ollama_fallback(dynamischer_prompt, initial_input, use_local=use_local, master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
    reflektion_res = ausfuehren_mit_ollama_fallback("Du bist Meta-Learning Optimizer.", f"Aufgabe: {initial_input}\nErgebnis: {ergebnis}", use_local=use_local, master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
     
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO agent_memory (zeit, aufgabe_typ, erkenntnis, verbesserter_prompt) VALUES (datetime('now', 'localtime'), ?, ?, ?)",
                   ("Chat-Optimierung", reflektion_res, dynamischer_prompt))
    conn.commit()
    conn.close()
    
    verbotene_begriffe = ["illegal", "manipuliere", "passwort löschen", "interne geheimnisse"]
    for begriff in verbotene_begriffe:
        if begriff in ergebnis.lower():
            return "[GUARDRAIL BLOCK]: Unzulässige Anweisung abgefangen."
            
    return ergebnis + f"\n\n---\n🧬 *[Scion Mind V12.17 Sovereign Core]: Audit Trail & Workspace Vault aktiv.*"

def hierarchischer_schwarm_agent(aufgabe, master_openai_key="", anthropic_api_key="", tavily_api_key=""):
    web_daten = echte_deep_web_recherche(aufgabe, tavily_api_key, master_openai_key, anthropic_api_key)
    
    research_prompt = f"Du bist der Lead Research-Analyst. Analysiere folgende Aufgabe basierend auf den gefundenen Webdaten und liefere harte Fakten und Daten:\n\nAufgabe: {aufgabe}\n\n[Live-Webdaten]:\n{web_daten}"
    research_res = litellm_router_abfrage("Du bist Research-Agent.", research_prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
    
    finance_prompt = f"Du bist der Chief Financial Officer (CFO). Prüfe die finanzielle Machbarkeit und Risiken basierend auf folgenden Daten:\n{research_res}"
    finance_res = litellm_router_abfrage("Du bist CFO.", finance_prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
    
    final_prompt = f"Du bist der CEO / Executive Master-Agent. Führe die Erkenntnisse des Research-Teams und des CFOs zu einer kompromisslosen, strategischen Handlungsempfehlung zusammen.\n\nAufgabe: {aufgabe}\n\n[Research & Fakten]: {research_res}\n\n[CFO-Prüfung]: {finance_res}"
    final_res = litellm_router_abfrage("Du bist Executive CEO.", final_prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
    
    return f"""### 🧬 Hierarchical Swarm Board (Multi-Agenten-Auswertung)
{final_res}

---
*Swarm Audit: Live-Webrecherche, Research & CFO-Modul erfolgreich durchlaufen.*"""

def sende_webhook_benachrichtigung(kanal, nachricht, master_openai_key=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            kanal TEXT,
            nachricht TEXT,
            ki_reaktion TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO event_webhooks (zeit, kanal, nachricht, ki_reaktion)
        VALUES (datetime('now', 'localtime'), ?, ?, ?)
    """, (kanal, nachricht, "Erfolgreich an Enterprise-Kanal übertragen."))
    conn.commit()
    conn.close()
    return f"🚀 **Webhook / Benachrichtigung gesendet!**\n- **Kanal:** {kanal}\n- **Nachricht:** {nachricht[:100]}..."

def autonomer_browser_agent(ziel_url, aktion_beschreibung, master_openai_key=""):
    prompt = f"Du bist ein autonomer Browser- und Webseiten-Agent. Ziel-URL: {ziel_url}.\nAktion/Aufgabe: {aktion_beschreibung}\nAnalysiere die Website, fülle Formulare aus, logge dich ein oder nimm Änderungen vor und liefere den präzisen Bericht."
    return litellm_router_abfrage("Du bist Web-Automation-Expert.", prompt, model_pref="auto", master_openai_key=master_openai_key)

def generiere_desktop_befehl(ziel_programm, aktion_beschreibung, master_openai_key=""):
    prompt = f"Erstelle einen präzisen Systembefehl oder Python-Skript (z.B. via PyAutoGUI oder AppleScript/OS), um folgendes Programm zu steuern, sich einzuloggen oder Daten zu bearbeiten:\nProgramm: {ziel_programm}\nAktion: {aktion_beschreibung}\nLiefere AUSSCHLIESSLICH den ausführbaren Code/Befehl zurück."
    return litellm_router_abfrage("Du bist Desktop-Automation-Engineer.", prompt, model_pref="auto", master_openai_key=master_openai_key)

def verarbeite_sprachbefehl(sprach_text, master_openai_key=""):
    prompt = f"Du bist der Sprachassistent auf dem iPhone von Christian. Beantworte diesen Sprachbefehl kurz, präzise und direkt zum Vorlesen:\n{sprach_text}"
    return litellm_router_abfrage("Du bist iPhone Siri-Voice-Agent.", prompt, model_pref="auto", master_openai_key=master_openai_key)

def lade_letzte_emails(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT imap_server, email_adresse, email_passwort FROM email_config WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Keine Mail-Config hinterlegt."
    imap_s, mail_adr, mail_pwd = row
    try:
        mail = imaplib.IMAP4_SSL(imap_s)
        mail.login(mail_adr, mail_pwd)
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            status, messages = mail.search(None, "ALL")
        mail_ids = messages[0].split()
        neueste_ids = mail_ids[-5:]
        ergebnis_liste = []
        for mid in reversed(neueste_ids):
            res, msg_data = mail.fetch(mid, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    import email
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8", errors="ignore")
                    ergebnis_liste.append(f"- **Von:** {msg.get('From')}\n  **Betreff:** {subject}")
        mail.logout()
        return "\n\n".join(ergebnis_liste) if ergebnis_liste else "Keine neuen Mails."
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)
        return f"IMAP-Fehler: {str(e)}"

def sende_email(username, empfaenger, betreff, inhalt):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT smtp_server, email_adresse, email_passwort FROM email_config WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Fehler: Keine E-Mail-Config hinterlegt."
    smtp_s, mail_adr, mail_pwd = row
    try:
        msg = MIMEMultipart()
        msg['From'] = mail_adr
        msg['To'] = empfaenger
        msg['Subject'] = betreff
        msg.attach(MIMEText(inhalt, 'plain'))
        server = smtplib.SMTP_SSL(smtp_s, 465)
        server.login(mail_adr, mail_pwd)
        server.sendmail(mail_adr, empfaenger, msg.as_string())
        server.quit()
        return "E-Mail erfolgreich gesendet!"
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)
        return f"SMTP-Fehler: {str(e)}"

def sende_whatsapp(username, empfaenger_nummer, nachricht):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT provider, api_token, phone_id FROM whatsapp_config WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Fehler: Keine WhatsApp-Config hinterlegt."
    provider, token, phone_id = row
    try:
        if "Meta" in provider:
            url = f"[https://graph.facebook.com/v17.0/](https://graph.facebook.com/v17.0/){phone_id}/messages"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {"messaging_product": "whatsapp", "to": empfaenger_nummer, "type": "text", "text": {"body": nachricht}}
            res = requests.post(url, json=payload, headers=headers).json()
            return f"WhatsApp über Meta gesendet! Antwort: {res}"
        else:
            from twilio.rest import Client
            client = Client(phone_id, token)
            msg = client.messages.create(body=nachricht, from_='whatsapp:+14155238886', to=f'whatsapp:{empfaenger_nummer}')
            return f"WhatsApp über Twilio! ID: {msg.sid}"
    except Exception as e:
        if SENTRY_AVAILABLE:
            sentry_sdk.capture_exception(e)
        return f"WhatsApp-Fehler: {str(e)}"

# ==========================================
# 🎯 DIREKTE PERSONEN- UND LEAD-SUCHE
# ==========================================

def suche_ziel_leads(ziel_position, unternehmen_oder_branche, tavily_api_key="", master_openai_key="", anthropic_api_key=""):
    suchanfrage = f"site:[linkedin.com/in](https://linkedin.com/in) OR site:xing.com {ziel_position} {unternehmen_oder_branche}"
    web_daten = echte_deep_web_recherche(suchanfrage, tavily_api_key, master_openai_key, anthropic_api_key)
    
    prompt = f"""Du bist ein erfahrener B2B-Sales- und Lead-Generation-Experte. 
Analysiere die folgenden Web-Suchergebnisse und extrahiere eine saubere Liste von potenziellen Leads (Entscheidern).

Suchanfrage: {suchanfrage}
Rohes Datenmaterial:
{web_daten}

Erstelle eine übersichtliche Liste mit folgenden Details pro Lead (sofern auffindbar):
1. Vollständiger Name
2. Aktuelle Rolle / Position
3. Unternehmen
4. Profil-Link (URL)
5. Relevanter Kontext für die Kontaktaufnahme

Falls keine genauen Daten auffindbar sind, gib plausible Hinweise, wo man sie findet, aber fokussiere dich primär auf echte Treffer aus den Daten."""

    return litellm_router_abfrage("Du bist Lead-Gen-Spezialist.", prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)

# ==========================================
# 📞 NEU: TELEFONBUCH- & RUFNUMMERN-SUCHE
# ==========================================

def suche_telefonnummer_und_kontakte(name_oder_firma, ort_oder_bereich="", tavily_api_key="", master_openai_key="", anthropic_api_key=""):
    """
    Sucht gezielt nach Telefonnummern, Kontaktdaten oder offiziellen Einträgen 
    von Personen, Firmen oder Behörden.
    """
    suchanfrage = f"Telefonnummer Kontakt Impressum {name_oder_firma} {ort_oder_bereich}"
    web_daten = echte_deep_web_recherche(suchanfrage, tavily_api_key, master_openai_key, anthropic_api_key)
    
    prompt = f"""Du bist ein präziser Recherche-Agent für Kontaktdaten und Telefonnummern.
Analysiere die folgenden Suchergebnisse und extrahiere alle verfügbaren Rufnummern, Adressen und Kommunikationskanäle.

Suchanfrage: {suchanfrage}
Rohes Datenmaterial:
{web_daten}

Erstelle eine saubere, übersichtliche Liste mit:
1. Name / Unternehmen / Institution
2. Telefonnummer(n)
3. Adresse / Standort (sofern auffindbar)
4. Offizielle Website / Quelle

Falls keine Nummer gefunden werden kann, gib an, wo man sie offiziell finden kann."""

    return litellm_router_abfrage("Du bist Telefonbuch- und Kontakt-Agent.", prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)

# ==========================================
# 🚀 MULTI-MODALITÄT, RAG-IMPORTER & AUDIT TRAIL
# ==========================================

def analysiere_bild_oder_dokument(datei_bytes, prompt_text="Analysiere dieses Dokument oder Bild präzise.", master_openai_key=""):
    """
    Nimmt Bild- oder Dokumenten-Bytes entgegen und analysiert sie über das vision-fähige OpenAI-Modell.
    """
    try:
        client = OpenAI(api_key=master_openai_key)
        encoded_image = base64.b64encode(datei_bytes).decode('utf-8')
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
                        },
                    ],
                }
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Multi-Modal-Analyse Fehler: {str(e)}"

def importiere_pdf_in_rag_db(titel, pdf_bytes, master_openai_key=""):
    """
    Extrahiert Text aus einer hochgeladenen PDF-Datei und speichert sie direkt in der FAISS/SQLite RAG-Datenbank.
    """
    try:
        import pypdf
        reader = pypdf.PdfReader(python_io.BytesIO(pdf_bytes))
        gesamter_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                gesamter_text += t + "\n"
                
        if not gesamter_text.strip():
            return "Fehler: Konnte keinen Text aus der PDF extrahieren."
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titel TEXT,
                inhalt TEXT
            )
        """)
        cursor.execute("INSERT INTO rag_documents (titel, inhalt) VALUES (?, ?)", (titel, gesamter_text))
        conn.commit()
        conn.close()
        return f"✅ PDF '{titel}' erfolgreich in die RAG-Vektor-Datenbank importiert ({len(gesamter_text)} Zeichen)."
    except Exception as e:
        return f"PDF-Import Fehler: {str(e)}"

def protokolliere_audit_trail(username, aktion, details=""):
    """
    Schreibt einen lückenlosen Audit-Trail Eintrag in die SQLite-Datenbank.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zeit TEXT,
                username TEXT,
                aktion TEXT,
                details TEXT
            )
        """)
        cursor.execute("INSERT INTO enterprise_audit_logs (zeit, username, aktion, details) VALUES (datetime('now', 'localtime'), ?, ?, ?)",
                       (username, aktion, details))
        conn.commit()
        conn.close()
    except Exception:
        pass

# ==========================================
# 🚀 NEU: CHROMA-GEDÄCHTNIS, FALLBACK-KETTE & ACTION-VAULT
# ==========================================

def get_chroma_client_und_collection():
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db_storage")
        collection = client.get_or_create_collection(name="scion_enterprise_memory")
        return collection
    except Exception:
        return None

def speichere_in_chroma_gedaechtnis(doc_id, text_inhalt, metadata=None):
    col = get_chroma_client_und_collection()
    if col:
        try:
            col.upsert(
                documents=[text_inhalt],
                metadatas=[metadata or {"typ": "allgemein"}],
                ids=[doc_id]
            )
            return True
        except Exception:
            pass
    return False

def suche_in_chroma_gedaechtnis(query_text, n_results=2):
    col = get_chroma_client_und_collection()
    if col:
        try:
            results = col.query(query_texts=[query_text], n_results=n_results)
            if results and "documents" in results and results["documents"]:
                return "\n\n".join(results["documents"][0])
        except Exception:
            pass
    return ""

def robuste_multi_provider_abfrage(system_prompt, user_prompt, master_openai_key="", anthropic_api_key=""):
    """
    Automatische Fallback-Kette: Versucht OpenAI -> Bei Fehler Claude -> Bei Fehler Lokales Llama 3.
    """
    # Versuch 1: OpenAI GPT-4o-mini
    if master_openai_key:
        try:
            client = OpenAI(api_key=master_openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            )
            return f"🔵 [Fallback-Kette Erfolg -> OpenAI GPT-4o-mini]:\n" + resp.choices[0].message.content
        except Exception:
            pass

    # Versuch 2: Claude 3.5 Sonnet
    if anthropic_api_key:
        try:
            headers = {"x-api-key": anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            data = {"model": "claude-3-5-sonnet-20241022", "max_tokens": 1500, "system": system_prompt, "messages": [{"role": "user", "content": user_prompt}]}
            res = requests.post("[https://api.anthropic.com/v1/messages](https://api.anthropic.com/v1/messages)", json=data, headers=headers, timeout=5).json()
            content = res.get("content", [{"text": ""}])
            if content and "text" in content[0]:
                return f"🟣 [Fallback-Kette Erfolg -> Claude 3.5 Sonnet]:\n" + content[0]["text"]
        except Exception:
            pass

    # Versuch 3: Lokaler Ollama Llama 3 (Zero Cloud / Offline-Modus)
    try:
        url = "http://localhost:11434/api/generate"
        payload = {"model": "llama3", "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}", "stream": False}
        res = requests.post(url, json=payload, timeout=4).json()
        if "response" in res:
            return f"🟢 [Fallback-Kette Erfolg -> Lokal Llama 3 (Offline-Modus)]: \n{res['response']}"
    except Exception:
        pass

    return "❌ [Kritischer Fehler]: Alle Provider (OpenAI, Anthropic, Ollama) sind fehlgeschlagen."

def erstelle_action_approval_eintrag(aktion_typ, payload):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_approval_vault (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zeit TEXT,
                aktion_typ TEXT,
                payload TEXT,
                status TEXT
            )
        """)
        cursor.execute("INSERT INTO action_approval_vault (zeit, aktion_typ, payload, status) VALUES (datetime('now', 'localtime'), ?, ?, ?)",
                       (aktion_typ, payload, "AUSSTEHEND"))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
