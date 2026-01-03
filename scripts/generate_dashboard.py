#!/usr/bin/env python3
"""
LDP 360° DASHBOARD GENERATOR
Genera report completo con tutte le metriche: Funnel, Setter, Venditori, Creative
"""
import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import subprocess
import sys

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
META_DIR = DATA_DIR / "meta_exports/28d"
REPORTS_DIR = BASE_DIR / "reports"

# Crea reports dir se non esiste
REPORTS_DIR.mkdir(exist_ok=True)

# Stati
SHOW_UP_STATES = ['Chiuso', 'Scartato', 'Unclosable', 'Riprogrammare', 'In Attesa', 'Contratto Firmato', 'BIE']
CLOSED_STATES = ['Chiuso', 'Contratto Firmato']


def check_data_freshness():
    """Controlla quanto sono recenti i dati."""

    checks = {}

    # Airtable data
    for file in ['candidature_full.json', 'calls_full.json']:
        filepath = DATA_DIR / file
        if filepath.exists():
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age_hours = (datetime.now() - mtime).total_seconds() / 3600
            checks[file] = {
                'exists': True,
                'last_updated': mtime.strftime('%Y-%m-%d %H:%M'),
                'age_hours': age_hours,
                'fresh': age_hours < 24
            }
        else:
            checks[file] = {'exists': False}

    # Meta CSVs
    for file in ['ads.csv', 'adsets.csv', 'campaigns.csv']:
        filepath = META_DIR / file
        if filepath.exists():
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age_hours = (datetime.now() - mtime).total_seconds() / 3600

            # Extract date range from first row
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)
                date_range = f"{first_row.get('Reporting starts', 'N/A')} → {first_row.get('Reporting ends', 'N/A')}" if first_row else 'N/A'

            checks[f'meta/{file}'] = {
                'exists': True,
                'last_updated': mtime.strftime('%Y-%m-%d %H:%M'),
                'age_hours': age_hours,
                'date_range': date_range,
                'fresh': age_hours < 168  # Meta data weekly refresh is ok
            }
        else:
            checks[f'meta/{file}'] = {'exists': False}

    return checks


def load_all_data(date_start, date_end):
    """Carica tutti i dati."""

    # Meta Ads
    ads = []
    spend_total = 0
    impressions_total = 0
    reach_total = 0

    if (META_DIR / "ads.csv").exists():
        with open(META_DIR / "ads.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Ad name'):
                    ads.append(row)

    if (META_DIR / "adsets.csv").exists():
        with open(META_DIR / "adsets.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            first_row = next(reader, None)
            if first_row and not first_row.get('Ad set name'):
                # This is the totals row
                spend_total = float(first_row.get('Amount spent (EUR)', '0') or 0)
                impressions_total = int(first_row.get('Impressions', '0') or 0)
                reach_total = int(first_row.get('Reach', '0') or 0)

    # Candidature
    candidature = []
    if (DATA_DIR / "candidature_full.json").exists():
        with open(DATA_DIR / "candidature_full.json", 'r') as f:
            data = json.load(f)
            candidature = [r for r in data['records']
                          if date_start <= r.get('fields', {}).get('Data Creazione', '')[:10] < date_end]

    # Calls
    calls = []
    if (DATA_DIR / "calls_full.json").exists():
        with open(DATA_DIR / "calls_full.json", 'r') as f:
            data = json.load(f)
            calls = [r for r in data['records']
                    if r.get('fields', {}).get('Data Call', '') and
                    date_start <= r.get('fields', {}).get('Data Call', '')[:10] <= date_end]

    return {
        'ads': ads,
        'candidature': candidature,
        'calls': calls,
        'meta_totals': {
            'spend': spend_total,
            'impressions': impressions_total,
            'reach': reach_total
        }
    }


def analyze_funnel(candidature, calls):
    """Analizza funnel completo."""

    total_cand = len(candidature)
    total_calls = len(calls)

    by_status = defaultdict(int)
    show_ups = 0
    closures = 0
    total_revenue = 0
    total_cash = 0

    for call in calls:
        fields = call.get('fields', {})
        status = fields.get('Stato', '')
        by_status[status] += 1

        if status in SHOW_UP_STATES:
            show_ups += 1

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
        'rates': {
            'cand_to_call': (total_calls / total_cand * 100) if total_cand > 0 else 0,
            'call_to_showup': (show_ups / total_calls * 100) if total_calls > 0 else 0,
            'showup_to_close': (closures / show_ups * 100) if show_ups > 0 else 0,
        },
        'ticket_medio': total_revenue / closures if closures > 0 else 0
    }


def analyze_creative(ads):
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

            creative_stats.append({
                'name': ad['Ad name'],
                'spend': spend,
                'leads': leads,
                'cpl': spend / leads if leads > 0 else 999999,
                'ctr': (clicks / reach * 100) if reach > 0 else 0,
                'impressions': impressions,
            })
        except:
            continue

    return sorted(creative_stats, key=lambda x: x['cpl'])


def analyze_setters(calls):
    """Analizza performance setter."""

    setter_stats = defaultdict(lambda: {
        'calls': 0, 'show_ups': 0, 'closures': 0,
        'no_shows': 0, 'revenue': 0
    })

    for call in calls:
        fields = call.get('fields', {})
        setter = fields.get('Setter (Candidature)')
        if setter and isinstance(setter, list):
            setter = setter[0] if setter else 'Unknown'
        elif not setter:
            setter = 'Unknown'

        status = fields.get('Stato', '')
        setter_stats[setter]['calls'] += 1

        if status in SHOW_UP_STATES:
            setter_stats[setter]['show_ups'] += 1
        if status == 'No Show':
            setter_stats[setter]['no_shows'] += 1
        if status in CLOSED_STATES:
            setter_stats[setter]['closures'] += 1
            setter_stats[setter]['revenue'] += fields.get('Revenue', 0) or 0

    # Calculate rates
    for stats in setter_stats.values():
        stats['show_up_rate'] = (stats['show_ups'] / stats['calls'] * 100) if stats['calls'] > 0 else 0
        stats['close_rate'] = (stats['closures'] / stats['show_ups'] * 100) if stats['show_ups'] > 0 else 0

    return dict(setter_stats)


def analyze_closers(calls):
    """Analizza performance venditori."""

    closer_stats = defaultdict(lambda: {
        'show_ups': 0, 'closures': 0, 'revenue': 0,
        'scartati': 0, 'unclosable': 0
    })

    for call in calls:
        fields = call.get('fields', {})
        closer = fields.get('Venditore')
        if closer and isinstance(closer, list):
            closer = closer[0] if closer else 'Unassigned'
        elif not closer:
            closer = 'Unassigned'

        status = fields.get('Stato', '')

        if status in SHOW_UP_STATES:
            closer_stats[closer]['show_ups'] += 1
            if status == 'Scartato':
                closer_stats[closer]['scartati'] += 1
            elif status == 'Unclosable':
                closer_stats[closer]['unclosable'] += 1

        if status in CLOSED_STATES:
            closer_stats[closer]['closures'] += 1
            closer_stats[closer]['revenue'] += fields.get('Revenue', 0) or 0

    # Calculate rates
    for stats in closer_stats.values():
        stats['close_rate'] = (stats['closures'] / stats['show_ups'] * 100) if stats['show_ups'] > 0 else 0
        stats['ticket_medio'] = (stats['revenue'] / stats['closures']) if stats['closures'] > 0 else 0

    return {k: v for k, v in closer_stats.items() if k != 'Unassigned' and v['closures'] > 0}


def generate_markdown_report(data, funnel, creative, setters, closers, meta_totals, freshness):
    """Genera report markdown completo."""

    now = datetime.now()

    md = f"""# 📊 LDP 360° DASHBOARD

**Generato:** {now.strftime('%Y-%m-%d %H:%M:%S')}
**Periodo:** {data.get('date_start', 'N/A')} → {data.get('date_end', 'N/A')}

---

## ⚙️ Stato Dati

| Fonte | Ultimo Aggiornamento | Età | Periodo | Status |
|-------|---------------------|-----|---------|--------|
"""

    for name, check in freshness.items():
        if check.get('exists'):
            age_str = f"{check['age_hours']:.1f}h"
            status = "✅" if check.get('fresh') else "⚠️"
            date_range = check.get('date_range', '-')
            md += f"| {name} | {check['last_updated']} | {age_str} | {date_range} | {status} |\n"
        else:
            md += f"| {name} | N/A | N/A | N/A | ❌ MANCANTE |\n"

    md += f"""

---

## 🎯 EXECUTIVE SUMMARY

"""

    # Funnel Overview
    md += f"""### Funnel Overview

```
Candidature:  {funnel['candidature']:,}
    ↓ ({funnel['rates']['cand_to_call']:.1f}%)
Calls:        {funnel['calls']:,}
    ↓ ({funnel['rates']['call_to_showup']:.1f}%)
Show Up:      {funnel['show_ups']:,}
    ↓ ({funnel['rates']['showup_to_close']:.1f}%)
Chiusure:     {funnel['closures']:,}
```

### Metriche Chiave

| Metrica | Valore |
|---------|--------|
| **Spesa ADS** | €{meta_totals['spend']:,.2f} |
| **Revenue** | €{funnel['revenue']:,.2f} |
| **Cash** | €{funnel['cash']:,.2f} |
| **ROAS Revenue** | {funnel['revenue'] / meta_totals['spend'] if meta_totals['spend'] > 0 else 0:.2f}x |
| **ROAS Cash** | {funnel['cash'] / meta_totals['spend'] if meta_totals['spend'] > 0 else 0:.2f}x |
| **Ticket Medio** | €{funnel['ticket_medio']:,.2f} |
| **CPL** | €{meta_totals['spend'] / funnel['candidature'] if funnel['candidature'] > 0 else 0:.2f} |
| **CPC (Call)** | €{meta_totals['spend'] / funnel['calls'] if funnel['calls'] > 0 else 0:.2f} |
| **CPSU** | €{meta_totals['spend'] / funnel['show_ups'] if funnel['show_ups'] > 0 else 0:.2f} |
| **CPCl** | €{meta_totals['spend'] / funnel['closures'] if funnel['closures'] > 0 else 0:.2f} |

---

## 🎨 CREATIVE PERFORMANCE

### Top 10 per CPL

| Rank | Creative | CPL | Leads | Spesa | CTR |
|------|----------|-----|-------|-------|-----|
"""

    for i, ad in enumerate(creative[:10], 1):
        md += f"| {i} | {ad['name'][:50]} | €{ad['cpl']:.2f} | {ad['leads']} | €{ad['spend']:,.0f} | {ad['ctr']:.2f}% |\n"

    md += f"""

### Worst 5 per CPL (da ottimizzare/fermare)

| Creative | CPL | Leads | Spesa |
|----------|-----|-------|-------|
"""

    worst = [a for a in creative if a['leads'] > 0][-5:]
    for ad in reversed(worst):
        md += f"| {ad['name'][:50]} | €{ad['cpl']:.2f} | {ad['leads']} | €{ad['spend']:,.0f} |\n"

    md += f"""

---

## 👥 SETTER PERFORMANCE

### Top 10 per Volume

| Setter | Calls | Show Up | Close | SU% | Close% | Revenue |
|--------|-------|---------|-------|-----|--------|---------|
"""

    top_setters = sorted(setters.items(), key=lambda x: -x[1]['calls'])[:10]
    for name, stats in top_setters:
        md += f"| {name[:20]} | {stats['calls']} | {stats['show_ups']} | {stats['closures']} | {stats['show_up_rate']:.1f}% | {stats['close_rate']:.1f}% | €{stats['revenue']:,.0f} |\n"

    # Best/Worst
    qualified = {k: v for k, v in setters.items() if v['calls'] >= 20}
    if qualified:
        best = max(qualified.items(), key=lambda x: x[1]['show_up_rate'])
        worst = min(qualified.items(), key=lambda x: x[1]['show_up_rate'])
        md += f"\n🏆 **Best Show Up**: {best[0]} ({best[1]['show_up_rate']:.1f}%)  \n"
        md += f"⚠️ **Worst Show Up**: {worst[0]} ({worst[1]['show_up_rate']:.1f}%)  \n"

    md += f"""

---

## 💰 CLOSER/VENDITORE PERFORMANCE

| Venditore | Show Up | Chiusi | Scartati | Uncl. | Close% | Revenue | Ticket |
|-----------|---------|--------|----------|-------|--------|---------|--------|
"""

    top_closers = sorted(closers.items(), key=lambda x: -x[1]['revenue'])
    for name, stats in top_closers:
        md += f"| {name[:20]} | {stats['show_ups']} | {stats['closures']} | {stats['scartati']} | {stats['unclosable']} | {stats['close_rate']:.1f}% | €{stats['revenue']:,.0f} | €{stats['ticket_medio']:,.0f} |\n"

    if closers:
        best = max(closers.items(), key=lambda x: x[1]['close_rate'])
        worst = min(closers.items(), key=lambda x: x[1]['close_rate'])
        md += f"\n🏆 **Best Close**: {best[0]} ({best[1]['close_rate']:.1f}%)  \n"
        md += f"⚠️ **Worst Close**: {worst[0]} ({worst[1]['close_rate']:.1f}%)  \n"

    md += f"""

---

## 📊 BREAKDOWN STATI CALLS

| Stato | Count | % |
|-------|-------|---|
"""

    for status, count in sorted(funnel['by_status'].items(), key=lambda x: -x[1])[:10]:
        pct = (count / funnel['calls'] * 100) if funnel['calls'] > 0 else 0
        indicator = "✅" if status in SHOW_UP_STATES else "❌"
        md += f"| {indicator} {status} | {count} | {pct:.1f}% |\n"

    md += f"""

---

## 🎯 ACTION ITEMS

### 🟢 Da Scalare

"""

    # Top 3 creative per efficienza con volume significativo
    avg_cpl = funnel['revenue'] / funnel['candidature'] if funnel['candidature'] > 0 else 999
    scalable = [a for a in creative if a['leads'] >= 20 and a['cpl'] < avg_cpl][:3]
    for ad in scalable:
        md += f"- **{ad['name'][:50]}** (CPL €{ad['cpl']:.2f}, {ad['leads']} leads)\n"

    md += f"""

### 🔴 Da Fermare

"""

    # Worst 3 con spesa significativa
    killable = [a for a in creative if a['spend'] > 100 and a['leads'] > 0][-3:]
    for ad in reversed(killable):
        potential_saving = ad['spend']
        md += f"- **{ad['name'][:50]}** (CPL €{ad['cpl']:.2f}, risparmio €{potential_saving:.0f})\n"

    md += f"""

### ⚠️ Da Monitorare

"""

    # Setter con show up rate sotto 45%
    weak_setters = [(k, v) for k, v in setters.items() if v['calls'] >= 20 and v['show_up_rate'] < 45]
    if weak_setters:
        md += "**Setter con Show Up basso:**\n"
        for name, stats in weak_setters[:3]:
            md += f"- {name}: {stats['show_up_rate']:.1f}% ({stats['calls']} calls)\n"

    # Closer con close rate sotto 15%
    weak_closers = [(k, v) for k, v in closers.items() if v['show_ups'] >= 10 and v['close_rate'] < 15]
    if weak_closers:
        md += "\n**Closer con Close Rate basso:**\n"
        for name, stats in weak_closers[:3]:
            md += f"- {name}: {stats['close_rate']:.1f}% ({stats['show_ups']} show ups)\n"

    md += f"""

---

*Report generato automaticamente da LDP Dashboard Generator*
"""

    return md


def main():
    """Main function."""

    print("🔄 Generazione LDP 360° Dashboard...\n")

    # Check data freshness
    print("📊 Controllo freschezza dati...")
    freshness = check_data_freshness()

    # Show warnings
    warnings = []
    for name, check in freshness.items():
        if not check.get('exists'):
            warnings.append(f"❌ {name} MANCANTE")
        elif not check.get('fresh', True):
            warnings.append(f"⚠️  {name} vecchio ({check['age_hours']:.0f}h)")

    if warnings:
        print("\n⚠️  ATTENZIONE:")
        for w in warnings:
            print(f"   {w}")
        print()

    # Date range
    date_end = datetime.now().strftime('%Y-%m-%d')
    date_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-01')

    # Usa date range da Meta CSV se disponibile
    if (META_DIR / "adsets.csv").exists():
        with open(META_DIR / "adsets.csv", 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            first_row = next(reader, None)
            if first_row:
                date_start = first_row.get('Reporting starts', date_start)
                date_end = first_row.get('Reporting ends', date_end)

    print(f"📅 Periodo analisi: {date_start} → {date_end}\n")

    # Load data
    print("💾 Caricamento dati...")
    data = load_all_data(date_start, date_end)
    data['date_start'] = date_start
    data['date_end'] = date_end

    # Analyze
    print("🔍 Analisi funnel...")
    funnel = analyze_funnel(data['candidature'], data['calls'])

    print("🎨 Analisi creative...")
    creative = analyze_creative(data['ads'])

    print("👥 Analisi setter...")
    setters = analyze_setters(data['calls'])

    print("💰 Analisi closers...")
    closers = analyze_closers(data['calls'])

    # Generate report
    print("📝 Generazione report...\n")
    report = generate_markdown_report(
        data, funnel, creative, setters, closers,
        data['meta_totals'], freshness
    )

    # Save report
    report_path = REPORTS_DIR / f"Dashboard_LDP_{date_end}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Dashboard generata: {report_path}\n")

    # Print summary
    print("="*80)
    print("📊 QUICK SUMMARY")
    print("="*80)
    print(f"Spesa:      €{data['meta_totals']['spend']:,.2f}")
    print(f"Revenue:    €{funnel['revenue']:,.2f}")
    print(f"ROAS Cash:  {funnel['cash'] / data['meta_totals']['spend'] if data['meta_totals']['spend'] > 0 else 0:.2f}x")
    print(f"Candidature: {funnel['candidature']:,}")
    print(f"Calls:       {funnel['calls']:,} ({funnel['rates']['cand_to_call']:.1f}%)")
    print(f"Show Up:     {funnel['show_ups']:,} ({funnel['rates']['call_to_showup']:.1f}%)")
    print(f"Chiusure:    {funnel['closures']:,} ({funnel['rates']['showup_to_close']:.1f}%)")
    print("="*80)

    return report_path


if __name__ == "__main__":
    main()
