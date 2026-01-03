"""
LDP Marketing Analysis - Data Loader
====================================
Funzioni per caricare dati da Meta Ads CSV e Airtable.
"""

import csv
import json
import requests
from datetime import datetime
from pathlib import Path
from config import (
    AIRTABLE_API_KEY, AIRTABLE_BASE_ID,
    CANDIDATURE_TABLE_ID, CALLS_TABLE_ID,
    DATA_DIR, META_EXPORTS_DIR
)

# Assicura che DATA_DIR e META_EXPORTS_DIR siano Path
DATA_DIR = Path(DATA_DIR)
META_EXPORTS_DIR = Path(META_EXPORTS_DIR)


def load_meta_campaigns(period: str) -> list:
    """Carica dati campagne Meta per un periodo."""
    filepath = os.path.join(META_EXPORTS_DIR, period, "campaigns.csv")
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get('Campaign name', '')]


def load_meta_adsets(period: str) -> list:
    """Carica dati adsets Meta per un periodo."""
    filepath = os.path.join(META_EXPORTS_DIR, period, "adsets.csv")
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get('Ad set name', '')]


def load_meta_ads(period: str) -> list:
    """Carica dati ads Meta per un periodo."""
    filepath = os.path.join(META_EXPORTS_DIR, period, "ads.csv")
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get('Ad name', '')]


def get_meta_totals(period: str) -> dict:
    """Ottieni totali spesa dal file adsets (prima riga senza nome)."""
    filepath = os.path.join(META_EXPORTS_DIR, period, "adsets.csv")

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('Ad set name', ''):
                return {
                    'date_start': row.get('Reporting starts', ''),
                    'date_end': row.get('Reporting ends', ''),
                    'total_spend': float(row.get('Amount spent (EUR)', '0')),
                    'impressions': int(row.get('Impressions', '0') or 0),
                    'reach': int(row.get('Reach', '0') or 0),
                }
    return {}


def load_airtable_candidature(date_start: str = None, date_end: str = None) -> list:
    """
    Carica candidature da Airtable.

    Args:
        date_start: Data inizio (YYYY-MM-DD)
        date_end: Data fine (YYYY-MM-DD)
    """
    cache_file = os.path.join(DATA_DIR, "candidature_cache.json")

    # Usa cache se recente (< 1 ora)
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if (datetime.now().timestamp() - mtime) < 3600:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return filter_by_date(data['records'], date_start, date_end, 'Data Creazione')

    # Scarica da Airtable
    records = download_airtable_table(
        CANDIDATURE_TABLE_ID,
        fields=['Data Creazione', 'UTM Source', 'UTM Medium', 'UTM Campaign',
                'Stato Contatto', 'Nome', 'Email']
    )

    # Salva cache
    with open(cache_file, 'w') as f:
        json.dump({'records': records, 'updated': datetime.now().isoformat()}, f)

    return filter_by_date(records, date_start, date_end, 'Data Creazione')


def load_airtable_calls(date_start: str = None, date_end: str = None) -> list:
    """
    Carica calls da Airtable.

    Args:
        date_start: Data inizio (YYYY-MM-DD)
        date_end: Data fine (YYYY-MM-DD)
    """
    cache_file = os.path.join(DATA_DIR, "calls_cache.json")

    # Usa cache se recente (< 1 ora)
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if (datetime.now().timestamp() - mtime) < 3600:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return filter_by_date(data['records'], date_start, date_end, 'Data Creazione')

    # Scarica da Airtable
    records = download_airtable_table(
        CALLS_TABLE_ID,
        fields=['Data Creazione', 'Data Call', 'Stato', 'UTM Fonte (source)',
                'UTM Adset (medium)', 'UTM Campagna (campaign)',
                'Conta Chiusure', 'Conta No Show', 'Show Up',
                'Lifetime Value', 'Total Paid Real']
    )

    # Salva cache
    with open(cache_file, 'w') as f:
        json.dump({'records': records, 'updated': datetime.now().isoformat()}, f)

    return filter_by_date(records, date_start, date_end, 'Data Creazione')


def download_airtable_table(table_id: str, fields: list = None) -> list:
    """Scarica tutti i record da una tabella Airtable."""
    records = []
    offset = None

    base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_id}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}

    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        if fields:
            params["fields[]"] = fields

        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()

        if 'records' in data:
            records.extend(data['records'])

        offset = data.get('offset')
        if not offset:
            break

    return records


def filter_by_date(records: list, date_start: str, date_end: str, date_field: str) -> list:
    """Filtra record per range di date."""
    if not date_start and not date_end:
        return records

    filtered = []
    for record in records:
        fields = record.get('fields', {})
        date_str = fields.get(date_field, '')

        if not date_str:
            continue

        # Parse date (handle both date and datetime formats)
        try:
            if 'T' in date_str:
                record_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            else:
                record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            continue

        # Apply filters
        if date_start:
            start = datetime.strptime(date_start, '%Y-%m-%d').date()
            if record_date < start:
                continue

        if date_end:
            end = datetime.strptime(date_end, '%Y-%m-%d').date()
            if record_date > end:
                continue

        filtered.append(record)

    return filtered


def refresh_cache():
    """Forza refresh della cache Airtable."""
    cache_files = ['candidature_cache.json', 'calls_cache.json']
    for f in cache_files:
        path = os.path.join(DATA_DIR, f)
        if os.path.exists(path):
            os.remove(path)
    print("Cache pulita. Il prossimo caricamento scaricherà dati freschi.")


if __name__ == "__main__":
    # Test
    print("Testing data loader...")
    totals = get_meta_totals("2w")
    print(f"Meta totals 2w: {totals}")
