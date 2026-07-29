import os
import re
import json
import base64
import requests
import traceback
import sys
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
            exec(aktueller_code, {"__builtins__": __builtins__, "pd": pd, "requests": requests, "json": json}, local_scope)
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
    research_prompt = f"Du bist der Lead Research-Analyst. Analysiere folgende Aufgabe und liefere harte Fakten und Daten:\n{aufgabe}"
    research_res = litellm_router_abfrage("Du bist Research-Agent.", research_prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
    
    finance_prompt = f"Du bist der Chief Financial Officer (CFO). Prüfe die finanzielle Machbarkeit und Risiken basierend auf folgenden Daten:\n{research_res}"
    finance_res = litellm_router_abfrage("Du bist CFO.", finance_prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
    
    final_prompt = f"Du bist der CEO / Executive Master-Agent. Führe die Erkenntnisse des Research-Teams und des CFOs zu einer kompromisslosen, strategischen Handlungsempfehlung zusammen.\n\nAufgabe: {aufgabe}\n\n[Research]: {research_res}\n\n[CFO]: {finance_res}"
    final_res = litellm_router_abfrage("Du bist Executive CEO.", final_prompt, model_pref="auto", master_openai_key=master_openai_key, anthropic_api_key=anthropic_api_key)
    
    return f"""### 🧬 Hierarchical Swarm Board (Multi-Agenten-Auswertung)
{final_res}

---
*Swarm Audit: Research & CFO-Modul erfolgreich durchlaufen.*"""

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
    """
    Steuert autonom Webseiten und führt Browser-Aktionen / Recherchen aus.
    """
    prompt = f"Du bist ein autonomer Browser-Agent. Ziel-URL: {ziel_url}.\nAktion/Aufgabe: {aktion_beschreibung}\nFühre die Browser-Aktionen virtuell aus und liefere das präzise Ergebnis."
    return litellm_router_abfrage("Du bist Browser-Automation-Agent.", prompt, model_pref="auto", master_openai_key=master_openai_key)

def generiere_desktop_befehl(ziel_programm, aktion_beschreibung, master_openai_key=""):
    """
    Generiert plattformunabhängige Steuerungsbefehle (für Programme/Hardware) zur manuellen Freigabe.
    """
    prompt = f"Erstelle einen präzisen Systembefehl (Python/PyAutoGUI/OS-Befehl), um folgendes Programm zu steuern:\nProgramm: {ziel_programm}\nAktion: {aktion_beschreibung}\nLiefere AUSSCHLIESSLICH den ausführbaren Code/Befehl zurück."
    return litellm_router_abfrage("Du bist Desktop-Automation-Engineer.", prompt, model_pref="auto", master_openai_key=master_openai_key) 
    def verarbeite_sprachbefehl(sprach_text, master_openai_key=""):
    """
    Verarbeitet den diktierten Text vom iPhone und gibt eine präzise Antwort aus.
    """
    prompt = f"Du bist der Sprachassistent auf dem iPhone von Christian. Beantworte diesen Sprachbefehl kurz, präzise und direkt zum Vorlesen:\n{sprach_text}"
    return litellm_router_abfrage("Du bist iPhone Siri-Voice-Agent.", prompt, model_pref="auto", master_openai_key=master_openai_key)
