import sqlite3
import pandas as pd

DB_NAME = "scion_mind_enterprise.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kunden (
            username TEXT PRIMARY KEY,
            passwort TEXT,
            guthaben REAL,
            rolle TEXT,
            workspace TEXT
        )
    """)
    cursor.execute("PRAGMA table_info(kunden)")
    columns = [col[1] for col in cursor.fetchall()]
    if "rolle" not in columns:
        cursor.execute("ALTER TABLE kunden ADD COLUMN rolle TEXT DEFAULT 'Standard'")
    if "workspace" not in columns:
        cursor.execute("ALTER TABLE kunden ADD COLUMN workspace TEXT DEFAULT 'Default-Hub'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lizenz_schluessel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schluessel TEXT UNIQUE,
            betrag REAL,
            status TEXT DEFAULT 'Unbenutzt',
            erstellt_am TEXT,
            eingeloest_von TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guthaben_historie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            username TEXT,
            typ TEXT,
            betrag REAL,
            grund TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspace_dateien (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace TEXT,
            titel TEXT,
            dateityp TEXT,
            binär_daten BLOB,
            erstellt_am TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daemon_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            aktion TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            imap_server TEXT,
            smtp_server TEXT,
            email_adresse TEXT,
            email_passwort TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            provider TEXT,
            api_token TEXT,
            phone_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mcp_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_name TEXT,
            resource_uri TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            aufgabe_typ TEXT,
            erkennnis TEXT,
            verbesserter_prompt TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titel TEXT,
            inhalt TEXT,
            vektor_metadaten TEXT
        )
    """)
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
        CREATE TABLE IF NOT EXISTS async_task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            agent_typ TEXT,
            task_ziel TEXT,
            status TEXT,
            ergebnis TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspace_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace TEXT,
            service_name TEXT,
            encrypted_key TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT UNIQUE,
            beschreibung TEXT,
            python_code TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            metrik_typ TEXT,
            wert REAL,
            details TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lead_gen_vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            firma TEXT,
            geschaeftsfuehrer TEXT,
            website TEXT,
            design_status TEXT,
            akquise_mail TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            step_name TEXT,
            state_payload TEXT,
            zeit TEXT
        )
    """)
    
    # Administrator-Account fest hinterlegen
    cursor.execute("""
        INSERT OR REPLACE INTO kunden (username, passwort, guthaben, rolle, workspace)
        VALUES ('Christian', 'ScionMind#2026!Secured', 999.00, 'Administrator', 'Global-Executive')
    """)

    conn.commit()
    conn.close() 
import sqlite3

def init_db():
    # Stellt sicher, dass die Datenbank und die wichtige Tabelle existieren
    conn = sqlite3.connect("scion_mind.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zeit TEXT,
            erkenntnis TEXT
        )
    """)
    conn.commit()
    conn.close()

# Das hier stößt die Erstellung direkt an
init_db()
