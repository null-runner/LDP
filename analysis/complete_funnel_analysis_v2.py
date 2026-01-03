#!/usr/bin/env python3
"""
ANALISI COMPLETA FUNNEL LDP - Dicembre 2025 (CORRETTA)
Classificazione stati corretta
"""
import json
import csv
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
META_DIR = DATA_DIR / "meta_exports/28d"

# Date range
DATE_START = "2025-12-01"
DATE_END = "2025-12-31"

# Stati che rappresentano show up (persona si è presentata)
SHOW_UP_STATES = [
    'Chiuso',
    'Scartato',
    'Unclosable',
    'Riprogrammare',
    'In Attesa',
    'Contratto Firmato',
    'BIE'
]

# Stati che rappresentano chiusura
CLOSED_STATES = ['Chiuso', 'Contratto Firmato']

def load_data():
    """Carica tutti i dati necessari."""

    # Meta Ads
    ads = []
    with open(META_DIR / "ads.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Ad name'):
                ads.append(row)

    # Candidature
    with open(DATA_DIR / "candidature_full.json", 'r') as f:
        data = json.load(f)
        candidature = [r for r in data['records']
                      if DATE_START <= r.get('fields', {}).get('Data Creazione', '')[:10] < DATE_END]

    # Calls
    with open(DATA_DIR / "calls_full.json", 'r') as f:
        data = json.load(f)
        calls = [r for r in data['records']
                if r.get('fields', {}).get('Data Call', '') and
                DATE_START <= r.get('fields', {}).get('Data Call', '')[:10] <= DATE_END]

    return ads, candidature, calls

def analyze_funnel(candidature, calls):
    """Analizza il funnel completo con classificazione corretta."""

    total_cand = len(candidature)
    total_calls = len(calls)

    # Count by status
    by_status = defaultdict(int)
    show_ups = 0
    closures = 0
    total_revenue = 0
    total_cash = 0

    for call in calls:
        fields = call.get('fields', {})
        status = fields.get('Stato', '')
        by_status[status] += 1

        # Show up = tutti gli stati tranne No Show
        if status in SHOW_UP_STATES:
            show_ups += 1

        # Chiusura = solo Chiuso e Contratto Firmato
        if status in CLOSED_STATES:
            closures += 1
            total_revenue += fields.get('Revenue', 0) or 0
            total_cash += fields.get('Cash Collected', 0) or 0

    return {
        'candidature': total_cand,
        'calls': total_calls,
        'show_ups': show_ups,
        'closures': closures,
        'revenue': total_revenue,
        'cash': total_cash,
        'by_status': dict(by_status),
        'cand_to_call_rate': (total_calls / total_cand * 100) if total_cand > 0 else 0,
        'call_to_showup_rate': (show_ups / total_calls * 100) if total_calls > 0 else 0,
        'showup_to_close_rate': (closures / show_ups * 100) if show_ups > 0 else 0,
    }

def analyze_ads(ads):
    """Analizza performance creative."""

    creative_stats = []

    for ad in ads:
        try:
            spend = float(ad.get('Amount spent (EUR)', '0') or 0)
            if spend == 0:
                continue

            leads = int(ad.get('Leads', '0') or 0)
            impressions = int(ad.get('Impressions', '0') or 0)
            clicks = int(ad.get('Unique link clicks', '0') or 0)
            reach = int(ad.get('Reach', '0') or 0)

            plays_100 = int(ad.get('Video plays at 100%', '0') or 0)

            creative_stats.append({
                'name': ad['Ad name'],
                'spend': spend,
                'leads': leads,
                'cpl': spend / leads if leads > 0 else 999999,
                'impressions': impressions,
                'clicks': clicks,
                'ctr': (clicks / reach * 100) if reach > 0 else 0,
                'retention_100': (plays_100 / impressions * 100) if impressions > 0 else 0,
            })
        except:
            continue

    return creative_stats

def analyze_setters(calls):
    """Analizza performance setter con classificazione corretta."""

    setter_stats = defaultdict(lambda: {
        'calls': 0,
        'show_ups': 0,
        'closures': 0,
        'no_shows': 0,
        'revenue': 0,
        'cash': 0
    })

    for call in calls:
        fields = call.get('fields', {})

        # Get setter
        setter = fields.get('Setter (Candidature)')
        if setter and isinstance(setter, list):
            setter = setter[0] if setter else 'Unknown'
        elif not setter:
            setter = fields.get('Setter (manuale)', 'Unknown')

        status = fields.get('Stato', '')

        setter_stats[setter]['calls'] += 1

        if status in SHOW_UP_STATES:
            setter_stats[setter]['show_ups'] += 1

        if status == 'No Show':
            setter_stats[setter]['no_shows'] += 1

        if status in CLOSED_STATES:
            setter_stats[setter]['closures'] += 1
            setter_stats[setter]['revenue'] += fields.get('Revenue', 0) or 0
            setter_stats[setter]['cash'] += fields.get('Cash Collected', 0) or 0

    # Calculate rates
    for setter, stats in setter_stats.items():
        stats['show_up_rate'] = (stats['show_ups'] / stats['calls'] * 100) if stats['calls'] > 0 else 0
        stats['close_rate'] = (stats['closures'] / stats['show_ups'] * 100) if stats['show_ups'] > 0 else 0
        stats['no_show_rate'] = (stats['no_shows'] / stats['calls'] * 100) if stats['calls'] > 0 else 0

    return dict(setter_stats)

def analyze_closers(calls):
    """Analizza performance venditori/closer."""

    closer_stats = defaultdict(lambda: {
        'calls': 0,
        'show_ups': 0,
        'closures': 0,
        'revenue': 0,
        'cash': 0,
        'ticket_medio': 0,
        'scartati': 0,
        'unclosable': 0
    })

    for call in calls:
        fields = call.get('fields', {})

        # Get closer/venditore
        closer = fields.get('Venditore')
        if closer and isinstance(closer, list):
            closer = closer[0] if closer else 'Unknown'
        elif not closer:
            closer = 'Unassigned'

        status = fields.get('Stato', '')

        # Count show ups for this closer
        if status in SHOW_UP_STATES:
            closer_stats[closer]['show_ups'] += 1
            closer_stats[closer]['calls'] += 1

            if status == 'Scartato':
                closer_stats[closer]['scartati'] += 1
            elif status == 'Unclosable':
                closer_stats[closer]['unclosable'] += 1

        if status in CLOSED_STATES:
            closer_stats[closer]['closures'] += 1
            revenue = fields.get('Revenue', 0) or 0
            cash = fields.get('Cash Collected', 0) or 0
            closer_stats[closer]['revenue'] += revenue
            closer_stats[closer]['cash'] += cash

    # Calculate metrics
    for closer, stats in closer_stats.items():
        stats['close_rate'] = (stats['closures'] / stats['show_ups'] * 100) if stats['show_ups'] > 0 else 0
        stats['ticket_medio'] = (stats['revenue'] / stats['closures']) if stats['closures'] > 0 else 0

    return dict(closer_stats)

def print_report(funnel, ads, setters, closers):
    """Stampa report completo."""

    print("\n" + "="*80)
    print("📊 ANALISI COMPLETA FUNNEL LDP - DICEMBRE 2025 (CORRETTA)")
    print("="*80)

    # FUNNEL OVERVIEW
    print("\n🎯 1. FUNNEL OVERVIEW")
    print("-" * 80)
    print(f"Candidature:  {funnel['candidature']:,}")
    print(f"    ↓ ({funnel['cand_to_call_rate']:.1f}% call booking)")
    print(f"Calls Booked: {funnel['calls']:,}")
    print(f"    ↓ ({funnel['call_to_showup_rate']:.1f}% show up)")
    print(f"Show Up:      {funnel['show_ups']:,}")
    print(f"    ↓ ({funnel['showup_to_close_rate']:.1f}% close)")
    print(f"Chiusure:     {funnel['closures']:,}")
    print(f"\nRevenue totale: €{funnel['revenue']:,.2f}")
    print(f"Cash totale:    €{funnel['cash']:,.2f}")
    print(f"Ticket medio:   €{funnel['revenue'] / funnel['closures'] if funnel['closures'] > 0 else 0:,.2f}")

    print(f"\n📊 Breakdown per Stato:")
    for status, count in sorted(funnel['by_status'].items(), key=lambda x: -x[1])[:10]:
        pct = (count / funnel['calls'] * 100) if funnel['calls'] > 0 else 0
        indicator = "✅" if status in SHOW_UP_STATES else "❌"
        print(f"  {indicator} {status:20s}: {count:4d} ({pct:5.1f}%)")

    # TOP CREATIVE
    print("\n\n🎨 2. TOP 10 CREATIVE PER EFFICIENZA (CPL)")
    print("-" * 80)
    top_ads = sorted([a for a in ads if a['leads'] > 0], key=lambda x: x['cpl'])[:10]
    for i, ad in enumerate(top_ads, 1):
        print(f"{i:2d}. {ad['name'][:60]}")
        print(f"    CPL: €{ad['cpl']:.2f} | Leads: {ad['leads']} | Spesa: €{ad['spend']:,.2f} | CTR: {ad['ctr']:.2f}%")

    # SETTER PERFORMANCE
    print("\n\n👥 3. PERFORMANCE SETTER (Top 10 per volume)")
    print("-" * 80)
    top_setters = sorted(setters.items(), key=lambda x: -x[1]['calls'])[:10]
    print(f"{'Setter':<25} {'Calls':>6} {'Show':>5} {'Close':>6} {'SU%':>6} {'NS%':>6} {'Close%':>7} {'Revenue':>10}")
    print("-" * 80)
    for setter, stats in top_setters:
        print(f"{setter[:24]:<25} {stats['calls']:>6} {stats['show_ups']:>5} "
              f"{stats['closures']:>6} {stats['show_up_rate']:>5.1f}% "
              f"{stats['no_show_rate']:>5.1f}% "
              f"{stats['close_rate']:>6.1f}% €{stats['revenue']:>9,.0f}")

    # Best/Worst setter by show up rate (min 20 calls)
    qualified_setters = {k: v for k, v in setters.items() if v['calls'] >= 20}
    if qualified_setters:
        best_setter = max(qualified_setters.items(), key=lambda x: x[1]['show_up_rate'])
        worst_setter = min(qualified_setters.items(), key=lambda x: x[1]['show_up_rate'])

        print(f"\n🏆 Best Show Up Rate: {best_setter[0]} ({best_setter[1]['show_up_rate']:.1f}%)")
        print(f"⚠️  Worst Show Up Rate: {worst_setter[0]} ({worst_setter[1]['show_up_rate']:.1f}%)")

    # CLOSER/VENDITORE PERFORMANCE
    print("\n\n💰 4. PERFORMANCE VENDITORI (Closer)")
    print("-" * 80)
    # Filter out Unassigned
    real_closers = {k: v for k, v in closers.items() if k != 'Unassigned' and v['closures'] > 0}
    top_closers = sorted(real_closers.items(), key=lambda x: -x[1]['revenue'])

    print(f"{'Venditore':<25} {'Show':>5} {'Close':>6} {'Scart':>6} {'Uncl':>5} {'Cl%':>6} {'Revenue':>10} {'Ticket':>8}")
    print("-" * 80)
    for closer, stats in top_closers:
        print(f"{closer[:24]:<25} {stats['show_ups']:>5} "
              f"{stats['closures']:>6} {stats['scartati']:>6} {stats['unclosable']:>5} "
              f"{stats['close_rate']:>5.1f}% "
              f"€{stats['revenue']:>9,.0f} €{stats['ticket_medio']:>7,.0f}")

    if real_closers:
        best_closer = max(real_closers.items(), key=lambda x: x[1]['close_rate'])
        worst_closer = min(real_closers.items(), key=lambda x: x[1]['close_rate'])

        print(f"\n🏆 Best Close Rate: {best_closer[0]} ({best_closer[1]['close_rate']:.1f}%)")
        print(f"⚠️  Worst Close Rate: {worst_closer[0]} ({worst_closer[1]['close_rate']:.1f}%)")

    # INSIGHTS
    print("\n\n💡 5. INSIGHTS & RACCOMANDAZIONI")
    print("-" * 80)

    # Funnel optimization
    print(f"📊 FUNNEL:")
    print(f"   • Cand→Call: {funnel['cand_to_call_rate']:.1f}% (benchmark: 25-35%)")
    if funnel['cand_to_call_rate'] < 25:
        print(f"     ⚠️ BASSO - Verifica qualità lead e follow-up setter")
    elif funnel['cand_to_call_rate'] > 35:
        print(f"     ✅ OTTIMO - Sopra benchmark!")

    print(f"   • Call→Show Up: {funnel['call_to_showup_rate']:.1f}% (benchmark: 50-65%)")
    if funnel['call_to_showup_rate'] < 50:
        print(f"     ⚠️ BASSO - Migliora reminder e qualifica setter")
    else:
        print(f"     ✅ BUONO")

    print(f"   • Show Up→Close: {funnel['showup_to_close_rate']:.1f}% (benchmark: 15-25%)")
    if funnel['showup_to_close_rate'] < 15:
        print(f"     ⚠️ BASSO - Training venditori necessario")
    elif funnel['showup_to_close_rate'] > 25:
        print(f"     ✅ ECCELLENTE - Team vendita molto forte!")
    else:
        print(f"     ✅ BUONO")

    print("\n" + "="*80)

if __name__ == "__main__":
    print("Caricamento dati...")
    ads, candidature, calls = load_data()

    print("Analisi funnel...")
    funnel = analyze_funnel(candidature, calls)

    print("Analisi creative...")
    creative_stats = analyze_ads(ads)

    print("Analisi setter...")
    setter_stats = analyze_setters(calls)

    print("Analisi venditori...")
    closer_stats = analyze_closers(calls)

    print_report(funnel, creative_stats, setter_stats, closer_stats)
