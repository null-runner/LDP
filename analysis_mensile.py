#!/usr/bin/env python3
import json
from datetime import datetime
from collections import defaultdict

# Carica i dati
with open('./data/calls_full.json', 'r') as f:
    data = json.load(f)

# Strutture per aggregare i dati
vendite_per_mese = defaultdict(lambda: {'count': 0, 'revenue': 0, 'chiusure': 0, 'no_show': 0})
totali_per_anno = defaultdict(lambda: {'count': 0, 'revenue': 0, 'chiusure': 0})

# Processa ogni record
for record in data['records']:
    fields = record.get('fields', {})

    # Estrai data call
    data_call = fields.get('Data Call')
    if not data_call:
        continue

    try:
        dt = datetime.fromisoformat(data_call.replace('Z', '+00:00'))
        anno = dt.year
        mese = dt.month
        chiave = f"{anno}-{mese:02d}"

        # Conta solo 2024 e 2025
        if anno not in [2024, 2025]:
            continue

        # Aggregazione
        vendite_per_mese[chiave]['count'] += 1
        vendite_per_mese[chiave]['revenue'] += fields.get('Lifetime Value', 0)
        vendite_per_mese[chiave]['chiusure'] += fields.get('Conta Chiusure', 0)
        vendite_per_mese[chiave]['no_show'] += fields.get('Conta No Show', 0)

        totali_per_anno[anno]['count'] += 1
        totali_per_anno[anno]['revenue'] += fields.get('Lifetime Value', 0)
        totali_per_anno[anno]['chiusure'] += fields.get('Conta Chiusure', 0)

    except Exception as e:
        continue

# Ordina per data
mesi_ordinati = sorted(vendite_per_mese.keys())

# Stampa risultati
print("\n" + "="*80)
print("ANALISI VENDITE 2024-2025 - CONFRONTO PRIMI MESI vs RESTO ANNO")
print("="*80)

# 2024
print("\n📊 ANNO 2024:")
print("-" * 80)
print(f"{'Mese':<15} {'Calls':<10} {'Chiusure':<12} {'Revenue €':<15} {'Tasso Conv.':<12}")
print("-" * 80)

primi_3_mesi_2024 = {'count': 0, 'revenue': 0, 'chiusure': 0}
altri_mesi_2024 = {'count': 0, 'revenue': 0, 'chiusure': 0}

for mese in mesi_ordinati:
    if not mese.startswith('2024'):
        continue

    dati = vendite_per_mese[mese]
    tasso_conv = (dati['chiusure'] / dati['count'] * 100) if dati['count'] > 0 else 0

    mese_num = int(mese.split('-')[1])
    mese_nome = datetime(2024, mese_num, 1).strftime('%B')

    print(f"{mese_nome:<15} {dati['count']:<10} {dati['chiusure']:<12} €{dati['revenue']:<14,.0f} {tasso_conv:<11.1f}%")

    if mese_num in [1, 2, 3]:
        primi_3_mesi_2024['count'] += dati['count']
        primi_3_mesi_2024['revenue'] += dati['revenue']
        primi_3_mesi_2024['chiusure'] += dati['chiusure']
    else:
        altri_mesi_2024['count'] += dati['count']
        altri_mesi_2024['revenue'] += dati['revenue']
        altri_mesi_2024['chiusure'] += dati['chiusure']

print("\n" + "="*80)
print("CONFRONTO 2024:")
if primi_3_mesi_2024['count'] > 0:
    tasso_primi = (primi_3_mesi_2024['chiusure'] / primi_3_mesi_2024['count'] * 100)
    print(f"Gen-Feb-Mar:    {primi_3_mesi_2024['count']} calls, {primi_3_mesi_2024['chiusure']} chiusure, €{primi_3_mesi_2024['revenue']:,.0f}, Conv: {tasso_primi:.1f}%")
if altri_mesi_2024['count'] > 0:
    tasso_altri = (altri_mesi_2024['chiusure'] / altri_mesi_2024['count'] * 100)
    print(f"Altri mesi:     {altri_mesi_2024['count']} calls, {altri_mesi_2024['chiusure']} chiusure, €{altri_mesi_2024['revenue']:,.0f}, Conv: {tasso_altri:.1f}%")

    if primi_3_mesi_2024['count'] > 0:
        diff_calls = ((primi_3_mesi_2024['count'] / 3) / (altri_mesi_2024['count'] / 9) - 1) * 100
        diff_revenue = ((primi_3_mesi_2024['revenue'] / 3) / (altri_mesi_2024['revenue'] / 9) - 1) * 100
        print(f"\n💡 Primi 3 mesi vs media altri: Calls {diff_calls:+.1f}%, Revenue {diff_revenue:+.1f}%")

# 2025
print("\n\n📊 ANNO 2025:")
print("-" * 80)
print(f"{'Mese':<15} {'Calls':<10} {'Chiusure':<12} {'Revenue €':<15} {'Tasso Conv.':<12}")
print("-" * 80)

primi_3_mesi_2025 = {'count': 0, 'revenue': 0, 'chiusure': 0}
altri_mesi_2025 = {'count': 0, 'revenue': 0, 'chiusure': 0}

for mese in mesi_ordinati:
    if not mese.startswith('2025'):
        continue

    dati = vendite_per_mese[mese]
    tasso_conv = (dati['chiusure'] / dati['count'] * 100) if dati['count'] > 0 else 0

    mese_num = int(mese.split('-')[1])
    mese_nome = datetime(2025, mese_num, 1).strftime('%B')

    print(f"{mese_nome:<15} {dati['count']:<10} {dati['chiusure']:<12} €{dati['revenue']:<14,.0f} {tasso_conv:<11.1f}%")

    if mese_num in [1, 2, 3]:
        primi_3_mesi_2025['count'] += dati['count']
        primi_3_mesi_2025['revenue'] += dati['revenue']
        primi_3_mesi_2025['chiusure'] += dati['chiusure']
    else:
        altri_mesi_2025['count'] += dati['count']
        altri_mesi_2025['revenue'] += dati['revenue']
        altri_mesi_2025['chiusure'] += dati['chiusure']

print("\n" + "="*80)
print("CONFRONTO 2025:")
if primi_3_mesi_2025['count'] > 0:
    tasso_primi = (primi_3_mesi_2025['chiusure'] / primi_3_mesi_2025['count'] * 100)
    print(f"Gen-Feb-Mar:    {primi_3_mesi_2025['count']} calls, {primi_3_mesi_2025['chiusure']} chiusure, €{primi_3_mesi_2025['revenue']:,.0f}, Conv: {tasso_primi:.1f}%")
if altri_mesi_2025['count'] > 0:
    tasso_altri = (altri_mesi_2025['chiusure'] / altri_mesi_2025['count'] * 100)
    print(f"Altri mesi:     {altri_mesi_2025['count']} calls, {altri_mesi_2025['chiusure']} chiusure, €{altri_mesi_2025['revenue']:,.0f}, Conv: {tasso_altri:.1f}%")

    num_altri_mesi = len([m for m in mesi_ordinati if m.startswith('2025') and int(m.split('-')[1]) > 3])
    if primi_3_mesi_2025['count'] > 0 and num_altri_mesi > 0:
        diff_calls = ((primi_3_mesi_2025['count'] / 3) / (altri_mesi_2025['count'] / num_altri_mesi) - 1) * 100
        if altri_mesi_2025['revenue'] > 0:
            diff_revenue = ((primi_3_mesi_2025['revenue'] / 3) / (altri_mesi_2025['revenue'] / num_altri_mesi) - 1) * 100
            print(f"\n💡 Primi 3 mesi vs media altri: Calls {diff_calls:+.1f}%, Revenue {diff_revenue:+.1f}%")

print("\n" + "="*80)
print("\n")
