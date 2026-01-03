"""
LDP Marketing Analysis - Configurazione
========================================
Configurazione centralizzata per l'analisi marketing LDP.
Le API keys sono caricate da .env (mai committare!)
"""

import os
from pathlib import Path

# Load .env file
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"

def load_env():
    """Carica variabili da .env file."""
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# === AIRTABLE (da .env) ===
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "")

if not AIRTABLE_API_KEY:
    print("⚠️  AIRTABLE_API_KEY non trovata! Crea file .env (vedi .env.example)")

# Table IDs
CANDIDATURE_TABLE_ID = "tblqLo4QdlQZnJWTq"
CALLS_TABLE_ID = "tblW3PtC9Lf6SrA4l"

# === CAMPAGNE DA ESCLUDERE ===
EXCLUDED_CAMPAIGNS = [
    "Future mamme",
    "Trading",
]

# === ATTRIBUZIONE ===
# Fonti considerate "Meta" (100% attribuzione ads)
META_SOURCES = ["meta", "facebook", "fb"]

# Fonti da conteggiare separatamente (0% attribuzione ads)
OTHER_SOURCES = ["instagram", "telegram", "google", "youtube", "tiktok", "organic"]

# === VALORI REVENUE (se non disponibili da Airtable) ===
DEFAULT_TICKET_VALUE = 1327  # EUR - Ticket medio per chiusura

# === PATHS ===
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
META_EXPORTS_DIR = DATA_DIR / "meta_exports"

# Crea directories se non esistono
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
