#!/usr/bin/env python3
"""
LDP Marketing Analysis - Con Attribuzione Fonti
- Vista 1: Meta + 50% vuote (conservativo)
- Vista 2: Meta + 100% vuote (panoramica)
- Vista 3: Altre fonti (Instagram, Telegram, etc.) separate
"""

import json
import csv
import math
from datetime import datetime

DATA_DIR = "/home/null-runner/Projects/SynthOps/LDP/data"
REPORTS_DIR = "/home/null-runner/Projects/SynthOps/LDP/reports"
ANALYSIS_DIR = "/home/null-runner/Projects/SynthOps/LDP/analysis"

EXCLUDED_CAMPAIGNS = ["future mamme", "trading"]

def is_meta_source(source):
    """Check if source is Meta"""
    if not source:
        return False
    s = source.lower().strip()
    return s in ['meta', 'meta ads', 'facebook', 'fb']

def is_empty_source(source):
    """Check if source is empty/null"""
    return not source or source.strip() == '' or source.lower() == 'vuoto'

def get_source_category(source):
    """Categorize source"""
    if not source or source.strip() == '':
        return 'vuoto'
    s = source.lower().strip()
    if s in ['meta', 'meta ads', 'facebook', 'fb']:
        return 'meta'
    elif s == 'instagram':
        return 'instagram'
    elif s == 'telegram':
        return 'telegram'
    elif s in ['tiktok']:
        return 'tiktok'
    elif s in ['whatsapp']:
        return 'whatsapp'
    elif 'email' in s:
        return 'email'
    else:
        return 'altro'

def is_excluded(campaign):
    if not campaign:
        return False
    c = campaign.lower()
    return any(exc in c for exc in EXCLUDED_CAMPAIGNS)

def load_data():
    """Load all data"""
    with open(f"{DATA_DIR}/candidature_with_source.json") as f:
        cands = json.load(f)
    with open(f"{DATA_DIR}/calls_with_source.json") as f:
        calls = json.load(f)
    
    # Load ads
    ads = {}
    with open(f"{DATA_DIR}/ads_dec_2025.csv", encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 26:
                name = row[2].strip()
                try:
                    spend = float(row[25]) if row[25] else 0
                except:
                    spend = 0
                if spend > 0:
                    if name in ads:
                        ads[name]['spend'] += spend
                    else:
                        ads[name] = {'spend': spend}
    
    return cands, calls, ads

def filter_period(records, start, end):
    """Filter records by date"""
    filtered = []
    for r in records.get('records', records):
        date = r.get('fields', {}).get('Data Creazione')
        if date and date >= start and date < end:
            filtered.append(r)
    return filtered

def calculate_attributed_count(records, source_field, mode='meta_50'):
    """
    Calculate attributed count based on mode:
    - meta_100: only meta sources (100%)
    - meta_50: meta (100%) + empty (50% rounded up)
    - meta_full: meta (100%) + empty (100%)
    - other: specific other sources
    """
    meta_count = 0
    empty_count = 0
    other_counts = {}
    
    for r in records:
        source = r.get('fields', {}).get(source_field, '')
        cat = get_source_category(source)
        
        if cat == 'meta':
            meta_count += 1
        elif cat == 'vuoto':
            empty_count += 1
        else:
            other_counts[cat] = other_counts.get(cat, 0) + 1
    
    if mode == 'meta_100':
        return meta_count
    elif mode == 'meta_50':
        return meta_count + math.ceil(empty_count / 2)
    elif mode == 'meta_full':
        return meta_count + empty_count
    elif mode == 'other':
        return other_counts
    else:
        return {'meta': meta_count, 'empty': empty_count, 'other': other_counts}

def analyze_by_utm(records, source_field, status_field=None, closed_status=None):
    """Analyze records grouped by UTM Medium with source attribution"""
    by_utm = {}
    
    for r in records:
        utm = r.get('fields', {}).get('UTM Medium') or r.get('fields', {}).get('UTM Adset (medium)', '')
        if not utm:
            continue
        utm = utm.strip()
        
        source = r.get('fields', {}).get(source_field, '')
        cat = get_source_category(source)
        stato = r.get('fields', {}).get(status_field, '') if status_field else None
        
        if utm not in by_utm:
            by_utm[utm] = {
                'meta': {'total': 0, 'show_up': 0, 'chiuso': 0, 'no_show': 0, 'revenue': 0, 'cash': 0},
                'empty': {'total': 0, 'show_up': 0, 'chiuso': 0, 'no_show': 0, 'revenue': 0, 'cash': 0},
                'other': {'total': 0, 'show_up': 0, 'chiuso': 0, 'no_show': 0, 'revenue': 0, 'cash': 0}
            }
        
        bucket = 'meta' if cat == 'meta' else ('empty' if cat == 'vuoto' else 'other')
        by_utm[utm][bucket]['total'] += 1
        
        if status_field and stato:
            if stato == closed_status:
                by_utm[utm][bucket]['chiuso'] += 1
                by_utm[utm][bucket]['show_up'] += 1
                by_utm[utm][bucket]['revenue'] += r.get('fields', {}).get('Revenue', 0) or 0
                by_utm[utm][bucket]['cash'] += r.get('fields', {}).get('Cash Collected', 0) or 0
            elif stato == 'No Show':
                by_utm[utm][bucket]['no_show'] += 1
            elif stato in ['Scartato', 'Riprogrammare', 'In Attesa', 'Unclosable', 'BIE', 'Sconosciuto']:
                by_utm[utm][bucket]['show_up'] += 1
    
    return by_utm

def main():
    print("=" * 80)
    print("LDP ANALYSIS - CON ATTRIBUZIONE FONTI")
    print("=" * 80)
    
    # Load data
    print("\nLoading data...")
    cands_all, calls_all, ads = load_data()
    
    # Filter Dec 1-14
    print("Filtering Dec 1-14...")
    cands = filter_period(cands_all, '2025-12-01', '2025-12-15')
    calls = filter_period(calls_all, '2025-12-01', '2025-12-15')
    
    # Exclude campaigns
    cands = [c for c in cands if not is_excluded(c.get('fields', {}).get('UTM Campaign'))]
    calls = [c for c in calls if not is_excluded(c.get('fields', {}).get('UTM Campagna (campaign)'))]
    
    print(f"Candidature filtrate: {len(cands)}")
    print(f"Calls filtrate: {len(calls)}")
    
    # Count by source
    print("\n=== DISTRIBUZIONE FONTI (1-14 Dic) ===")
    cand_sources = calculate_attributed_count(cands, 'UTM Source', 'all')
    call_sources = calculate_attributed_count(calls, 'UTM Fonte (source)', 'all')
    
    print(f"\nCANDIDATURE:")
    print(f"  Meta: {cand_sources['meta']}")
    print(f"  Vuote: {cand_sources['empty']}")
    print(f"  Altre: {cand_sources['other']}")
    
    print(f"\nCALLS:")
    print(f"  Meta: {call_sources['meta']}")
    print(f"  Vuote: {call_sources['empty']}")
    print(f"  Altre: {call_sources['other']}")
    
    # Analyze by UTM with source breakdown
    cands_by_utm = analyze_by_utm(cands, 'UTM Source')
    calls_by_utm = analyze_by_utm(calls, 'UTM Fonte (source)', 'Stato', 'Chiuso')
    
    # Scale ads spend to 14 days
    total_spend = sum(a['spend'] * (14/15) for a in ads.values())
    
    # Calculate metrics for each view
    results = {'meta_50': [], 'meta_full': [], 'other_sources': {}}
    
    for ad_name, ad_data in ads.items():
        spend = ad_data['spend'] * (14/15)
        
        # Find matching UTM
        utm_match = None
        for utm in set(list(cands_by_utm.keys()) + list(calls_by_utm.keys())):
            if ad_name == utm or ad_name.replace(' - Copy', '').strip() == utm or utm in ad_name or ad_name in utm:
                utm_match = utm
                break
        
        cand_data = cands_by_utm.get(utm_match, {'meta': {'total': 0}, 'empty': {'total': 0}, 'other': {'total': 0}})
        call_data = calls_by_utm.get(utm_match, {'meta': {'total': 0, 'show_up': 0, 'chiuso': 0, 'revenue': 0, 'cash': 0}, 
                                                  'empty': {'total': 0, 'show_up': 0, 'chiuso': 0, 'revenue': 0, 'cash': 0},
                                                  'other': {'total': 0, 'show_up': 0, 'chiuso': 0, 'revenue': 0, 'cash': 0}})
        
        # Vista 1: Meta + 50% vuote
        cands_50 = cand_data['meta']['total'] + math.ceil(cand_data['empty']['total'] / 2)
        calls_50 = call_data['meta']['total'] + math.ceil(call_data['empty']['total'] / 2)
        su_50 = call_data['meta']['show_up'] + math.ceil(call_data['empty']['show_up'] / 2)
        cl_50 = call_data['meta']['chiuso'] + math.ceil(call_data['empty']['chiuso'] / 2)
        rev_50 = call_data['meta']['revenue'] + (call_data['empty']['revenue'] / 2)
        cash_50 = call_data['meta']['cash'] + (call_data['empty']['cash'] / 2)
        
        # Vista 2: Meta + 100% vuote
        cands_full = cand_data['meta']['total'] + cand_data['empty']['total']
        calls_full = call_data['meta']['total'] + call_data['empty']['total']
        su_full = call_data['meta']['show_up'] + call_data['empty']['show_up']
        cl_full = call_data['meta']['chiuso'] + call_data['empty']['chiuso']
        rev_full = call_data['meta']['revenue'] + call_data['empty']['revenue']
        cash_full = call_data['meta']['cash'] + call_data['empty']['cash']
        
        results['meta_50'].append({
            'name': ad_name,
            'spend': spend,
            'cands': cands_50,
            'calls': calls_50,
            'show_up': su_50,
            'chiusure': cl_50,
            'revenue': rev_50,
            'cash': cash_50,
            'cpl': spend / cands_50 if cands_50 > 0 else 0,
            'cpc': spend / calls_50 if calls_50 > 0 else 0,
            'cpsu': spend / su_50 if su_50 > 0 else 0,
            'cpcl': spend / cl_50 if cl_50 > 0 else 0,
            'roas': rev_50 / spend if spend > 0 else 0
        })
        
        results['meta_full'].append({
            'name': ad_name,
            'spend': spend,
            'cands': cands_full,
            'calls': calls_full,
            'show_up': su_full,
            'chiusure': cl_full,
            'revenue': rev_full,
            'cash': cash_full,
            'cpl': spend / cands_full if cands_full > 0 else 0,
            'cpc': spend / calls_full if calls_full > 0 else 0,
            'cpsu': spend / su_full if su_full > 0 else 0,
            'cpcl': spend / cl_full if cl_full > 0 else 0,
            'roas': rev_full / spend if spend > 0 else 0
        })
    
    # Sort by spend
    results['meta_50'].sort(key=lambda x: -x['spend'])
    results['meta_full'].sort(key=lambda x: -x['spend'])
    
    # Calculate totals
    def calc_totals(data):
        t = {'spend': 0, 'cands': 0, 'calls': 0, 'show_up': 0, 'chiusure': 0, 'revenue': 0, 'cash': 0}
        for r in data:
            for k in t:
                t[k] += r[k]
        t['cpl'] = t['spend'] / t['cands'] if t['cands'] > 0 else 0
        t['cpc'] = t['spend'] / t['calls'] if t['calls'] > 0 else 0
        t['cpsu'] = t['spend'] / t['show_up'] if t['show_up'] > 0 else 0
        t['cpcl'] = t['spend'] / t['chiusure'] if t['chiusure'] > 0 else 0
        t['roas'] = t['revenue'] / t['spend'] if t['spend'] > 0 else 0
        return t
    
    totals_50 = calc_totals(results['meta_50'])
    totals_full = calc_totals(results['meta_full'])
    
    # Print results
    print("\n" + "=" * 100)
    print("VISTA 1: META + 50% VUOTE (Conservativo)")
    print("=" * 100)
    print(f"Spesa: €{totals_50['spend']:,.2f} | Cand: {totals_50['cands']} | Calls: {totals_50['calls']} | SU: {totals_50['show_up']} | Cl: {totals_50['chiusure']}")
    print(f"CPL: €{totals_50['cpl']:.2f} | CPC: €{totals_50['cpc']:.2f} | CPSU: €{totals_50['cpsu']:.2f} | CPCl: €{totals_50['cpcl']:.2f}")
    print(f"Revenue: €{totals_50['revenue']:,.2f} | ROAS: {totals_50['roas']:.2f}x")
    
    print("\n" + "=" * 100)
    print("VISTA 2: META + 100% VUOTE (Panoramica)")
    print("=" * 100)
    print(f"Spesa: €{totals_full['spend']:,.2f} | Cand: {totals_full['cands']} | Calls: {totals_full['calls']} | SU: {totals_full['show_up']} | Cl: {totals_full['chiusure']}")
    print(f"CPL: €{totals_full['cpl']:.2f} | CPC: €{totals_full['cpc']:.2f} | CPSU: €{totals_full['cpsu']:.2f} | CPCl: €{totals_full['cpcl']:.2f}")
    print(f"Revenue: €{totals_full['revenue']:,.2f} | ROAS: {totals_full['roas']:.2f}x")
    
    print("\n" + "=" * 100)
    print("VISTA 3: ALTRE FONTI (non attribuibili a Meta)")
    print("=" * 100)
    other_cands = sum(c.get('other', {}).get('total', 0) for c in cands_by_utm.values())
    other_calls = sum(c.get('other', {}).get('total', 0) for c in calls_by_utm.values())
    other_su = sum(c.get('other', {}).get('show_up', 0) for c in calls_by_utm.values())
    other_cl = sum(c.get('other', {}).get('chiuso', 0) for c in calls_by_utm.values())
    print(f"Candidature da altre fonti: {other_cands}")
    print(f"Calls da altre fonti: {other_calls}")
    print(f"Show Up da altre fonti: {other_su}")
    print(f"Chiusure da altre fonti: {other_cl}")
    print(f"\nDettaglio fonti:")
    for src, count in sorted(call_sources['other'].items(), key=lambda x: -x[1]):
        print(f"  {src}: {count} calls")
    
    # Save results
    with open(f"{ANALYSIS_DIR}/analysis_attributed.json", 'w') as f:
        json.dump({
            'meta_50': {'results': results['meta_50'], 'totals': totals_50},
            'meta_full': {'results': results['meta_full'], 'totals': totals_full},
            'other_sources': {'cands': other_cands, 'calls': other_calls, 'show_up': other_su, 'chiusure': other_cl}
        }, f, indent=2)
    
    # Generate MD report
    md = f"""# 📊 LDP Marketing Analysis - Con Attribuzione Fonti
## Periodo: 1-14 Dicembre 2025
### Escluse: Future mamme, Trading

---

## 📐 Metodologia Attribuzione

| Fonte | Attribuzione |
|-------|-------------|
| `utm_source = meta` | 100% ads |
| `utm_source = vuoto` | 50% ads (arrotondato per eccesso) o 100% per panoramica |
| Altre fonti (IG, TG, etc.) | 0% ads (conteggiate separatamente) |

---

## 📈 VISTA 1: Meta + 50% Vuote (Conservativo)

| Metrica | Valore |
|---------|-------:|
| **Spesa** | €{totals_50['spend']:,.2f} |
| **Candidature** | {totals_50['cands']} |
| **Calls** | {totals_50['calls']} |
| **Show Up** | {totals_50['show_up']} |
| **Chiusure** | {totals_50['chiusure']} |
| **CPL** | €{totals_50['cpl']:.2f} |
| **CPC** | €{totals_50['cpc']:.2f} |
| **CPSU** | €{totals_50['cpsu']:.2f} |
| **CPCl** | €{totals_50['cpcl']:.2f} |
| **Revenue** | €{totals_50['revenue']:,.2f} |
| **ROAS** | {totals_50['roas']:.2f}x |

---

## 📈 VISTA 2: Meta + 100% Vuote (Panoramica)

| Metrica | Valore |
|---------|-------:|
| **Spesa** | €{totals_full['spend']:,.2f} |
| **Candidature** | {totals_full['cands']} |
| **Calls** | {totals_full['calls']} |
| **Show Up** | {totals_full['show_up']} |
| **Chiusure** | {totals_full['chiusure']} |
| **CPL** | €{totals_full['cpl']:.2f} |
| **CPC** | €{totals_full['cpc']:.2f} |
| **CPSU** | €{totals_full['cpsu']:.2f} |
| **CPCl** | €{totals_full['cpcl']:.2f} |
| **Revenue** | €{totals_full['revenue']:,.2f} |
| **ROAS** | {totals_full['roas']:.2f}x |

---

## 📊 VISTA 3: Altre Fonti (non Meta)

| Fonte | Candidature | Calls |
|-------|------------:|------:|
"""
    
    for src, count in sorted(cand_sources['other'].items(), key=lambda x: -x[1]):
        call_count = call_sources['other'].get(src, 0)
        md += f"| {src} | {count} | {call_count} |\n"
    
    md += f"""
**Totale altre fonti:**
- Candidature: {other_cands}
- Calls: {other_calls}
- Show Up: {other_su}
- Chiusure: {other_cl}

---

## 📊 Dettaglio per Ad Set (Vista Conservativa)

| Ad Set | Spesa | Cand | Call | SU | Cl | CPL | CPSU | ROAS |
|--------|------:|-----:|-----:|---:|---:|----:|-----:|-----:|
"""
    
    for r in results['meta_50'][:20]:
        name_short = r['name'][:35] + "..." if len(r['name']) > 35 else r['name']
        cpl = f"€{r['cpl']:.2f}" if r['cpl'] > 0 else "-"
        cpsu = f"€{r['cpsu']:.2f}" if r['cpsu'] > 0 else "-"
        roas = f"{r['roas']:.2f}x" if r['roas'] > 0 else "-"
        md += f"| {name_short} | €{r['spend']:.0f} | {r['cands']} | {r['calls']} | {r['show_up']} | {r['chiusure']} | {cpl} | {cpsu} | {roas} |\n"
    
    md += f"""
---

*Report generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}*
"""
    
    with open(f"{REPORTS_DIR}/report_attributed.md", 'w') as f:
        f.write(md)
    
    print(f"\nReport salvato in {REPORTS_DIR}/report_attributed.md")
    
    return results, totals_50, totals_full

if __name__ == "__main__":
    main()
