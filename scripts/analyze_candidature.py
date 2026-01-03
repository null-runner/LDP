#!/usr/bin/env python3
"""Analisi candidature SUSY 1-15 dicembre 2025"""
import json
from datetime import datetime
from collections import Counter

# Dati inline (inseriti manualmente dai risultati Airtable)
# Filtro: UTM Medium = 'M/F_25-45_ADV+:  SUSY_-_Vuoi_guadagnare_senza_fare_niente'
# Periodo: 1-15 dicembre 2025

data = []  # Placeholder - i dati verranno caricati da file

def load_data(filepath):
    """Carica dati da file JSON"""
    with open(filepath, 'r') as f:
        return json.load(f)

def filter_by_date(records, start_date, end_date):
    """Filtra record per data creazione"""
    filtered = []
    for r in records:
        created = r.get('fields', {}).get('Data Creazione', '')
        if created:
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            if start_date <= dt.date() <= end_date:
                filtered.append(r)
    return filtered

def analyze_stato_contatto(records):
    """Analizza distribuzione Stato Contatto"""
    stati = []
    for r in records:
        stato = r.get('fields', {}).get('Stato Contatto', 'Non assegnato')
        if stato is None:
            stato = 'Non assegnato'
        stati.append(stato)

    counter = Counter(stati)
    total = len(stati)

    print(f"\n{'='*60}")
    print(f"CANDIDATURE SUSY - 1-15 DICEMBRE 2025")
    print(f"{'='*60}")
    print(f"\nTotale candidature: {total}")
    print(f"\n{'STATO CONTATTO':<35} {'COUNT':>8} {'%':>8}")
    print(f"{'-'*55}")

    for stato, count in sorted(counter.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total > 0 else 0
        print(f"{stato:<35} {count:>8} {pct:>7.1f}%")

    return counter, total

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        data = load_data(filepath)
    else:
        print("Usage: python analyze_candidature.py <data.json>")
        print("\nCreating sample analysis from embedded data...")
        # Dati di esempio basati sui risultati parziali
        data = []

    # Filtro date: 1-15 dicembre 2025
    from datetime import date
    start = date(2025, 12, 1)
    end = date(2025, 12, 15)

    if data:
        filtered = filter_by_date(data, start, end)
        analyze_stato_contatto(filtered)
    else:
        print("Nessun dato caricato.")
