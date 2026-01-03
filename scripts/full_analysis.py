#!/usr/bin/env python3
"""
LDP Marketing Analysis - Full Pipeline
Analizza dati ads + Airtable (candidature e calls)
Esclude campagne: Future mamme, Trading
"""

import json
import csv
import os
from datetime import datetime

# Config
DATA_DIR = "/home/null-runner/Projects/SynthOps/LDP/data"
ANALYSIS_DIR = "/home/null-runner/Projects/SynthOps/LDP/analysis"
REPORTS_DIR = "/home/null-runner/Projects/SynthOps/LDP/reports"

# Campagne da escludere
EXCLUDED_CAMPAIGNS = ["future mamme", "trading"]

def load_ads_data():
    """Carica dati spesa ads dal CSV"""
    ads = {}
    total_spend = 0
    
    with open(f"{DATA_DIR}/ads_dec_2025.csv", encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 26:
                name = row[2].strip()
                try:
                    spend = float(row[25]) if row[25] else 0
                    leads = int(row[20]) if row[20] else 0
                except:
                    spend = 0
                    leads = 0
                
                if spend > 0:
                    # Aggregate by ad name (some might be duplicated)
                    if name in ads:
                        ads[name]['spend'] += spend
                        ads[name]['leads'] += leads
                    else:
                        ads[name] = {'spend': spend, 'leads': leads}
                    total_spend += spend
    
    return ads, total_spend

def load_airtable_data():
    """Carica dati Airtable già scaricati"""
    # Candidature
    with open('/tmp/all_candidature.json') as f:
        all_cands = json.load(f)
    
    # Calls  
    with open('/tmp/all_calls.json') as f:
        all_calls = json.load(f)
    
    # Revenue from closed calls
    with open('/tmp/closed_calls.json') as f:
        closed = json.load(f)
    
    return all_cands, all_calls, closed

def filter_by_date(records, start_date, end_date, date_field='Data Creazione'):
    """Filtra record per data"""
    filtered = []
    for r in records.get('records', records) if isinstance(records, dict) else records:
        date = r.get('fields', {}).get(date_field)
        if date and date >= start_date and date < end_date:
            filtered.append(r)
    return filtered

def is_excluded_campaign(campaign):
    """Check if campaign should be excluded"""
    if not campaign:
        return False
    campaign_lower = campaign.lower()
    for excluded in EXCLUDED_CAMPAIGNS:
        if excluded in campaign_lower:
            return True
    return False

def analyze_data(ads, cands, calls, closed, date_range="1-14 Dic"):
    """Analisi completa dei dati"""
    
    # Aggregate by UTM Medium
    cands_by_utm = {}
    for c in cands:
        utm = c.get('fields', {}).get('UTM Medium', '').strip()
        campaign = c.get('fields', {}).get('UTM Campaign', '')
        
        # Skip excluded campaigns
        if is_excluded_campaign(campaign):
            continue
            
        if not utm:
            continue
        if utm not in cands_by_utm:
            cands_by_utm[utm] = 0
        cands_by_utm[utm] += 1
    
    calls_by_utm = {}
    for c in calls:
        utm = c.get('fields', {}).get('UTM Adset (medium)', '').strip()
        campaign = c.get('fields', {}).get('UTM Campagna (campaign)', '')
        
        if is_excluded_campaign(campaign):
            continue
            
        if not utm:
            continue
        if utm not in calls_by_utm:
            calls_by_utm[utm] = {'total': 0, 'chiuso': 0, 'no_show': 0, 'scartato': 0, 'show_up': 0}
        
        calls_by_utm[utm]['total'] += 1
        stato = c.get('fields', {}).get('Stato', '')
        
        if stato == 'Chiuso':
            calls_by_utm[utm]['chiuso'] += 1
            calls_by_utm[utm]['show_up'] += 1
        elif stato == 'No Show':
            calls_by_utm[utm]['no_show'] += 1
        elif stato == 'Scartato':
            calls_by_utm[utm]['scartato'] += 1
            calls_by_utm[utm]['show_up'] += 1
        elif stato in ['Riprogrammare', 'In Attesa', 'Unclosable', 'BIE', 'Sconosciuto']:
            calls_by_utm[utm]['show_up'] += 1
    
    # Revenue by UTM
    revenue_by_utm = {}
    cash_by_utm = {}
    for r in closed.get('records', []):
        utm = r.get('fields', {}).get('UTM Adset (medium)', '')
        if utm:
            rev = r.get('fields', {}).get('Revenue', 0) or 0
            cash = r.get('fields', {}).get('Cash Collected', 0) or 0
            revenue_by_utm[utm] = revenue_by_utm.get(utm, 0) + rev
            cash_by_utm[utm] = cash_by_utm.get(utm, 0) + cash
    
    # Combine with ads data
    results = []
    totals = {'spend': 0, 'cands': 0, 'calls': 0, 'show_up': 0, 'chiusure': 0, 'revenue': 0, 'cash': 0}
    
    for ad_name, ad_data in ads.items():
        spend = ad_data['spend']
        
        # Find matching UTM
        utm_match = None
        for utm in list(cands_by_utm.keys()) + list(calls_by_utm.keys()):
            if ad_name == utm or ad_name.replace(' - Copy', '').strip() == utm or utm in ad_name or ad_name in utm:
                utm_match = utm
                break
        
        cands_count = cands_by_utm.get(utm_match, 0)
        calls_data = calls_by_utm.get(utm_match, {'total': 0, 'chiuso': 0, 'no_show': 0, 'show_up': 0})
        revenue = revenue_by_utm.get(utm_match, 0)
        cash = cash_by_utm.get(utm_match, 0)
        
        # Calculate metrics
        cpl = spend / cands_count if cands_count > 0 else 0
        cpc = spend / calls_data['total'] if calls_data['total'] > 0 else 0
        cps = spend / calls_data['show_up'] if calls_data['show_up'] > 0 else 0
        cpch = spend / calls_data['chiuso'] if calls_data['chiuso'] > 0 else 0
        roas = revenue / spend if spend > 0 else 0
        roas_cash = cash / spend if spend > 0 else 0
        
        results.append({
            'name': ad_name,
            'spend': spend,
            'cands': cands_count,
            'calls': calls_data['total'],
            'show_up': calls_data['show_up'],
            'no_show': calls_data['no_show'],
            'chiusure': calls_data['chiuso'],
            'revenue': revenue,
            'cash': cash,
            'cpl': cpl,
            'cpc': cpc,
            'cps': cps,
            'cpch': cpch,
            'roas': roas,
            'roas_cash': roas_cash
        })
        
        totals['spend'] += spend
        totals['cands'] += cands_count
        totals['calls'] += calls_data['total']
        totals['show_up'] += calls_data['show_up']
        totals['chiusure'] += calls_data['chiuso']
        totals['revenue'] += revenue
        totals['cash'] += cash
    
    # Calculate total metrics
    totals['avg_cpl'] = totals['spend'] / totals['cands'] if totals['cands'] > 0 else 0
    totals['avg_cpc'] = totals['spend'] / totals['calls'] if totals['calls'] > 0 else 0
    totals['avg_cps'] = totals['spend'] / totals['show_up'] if totals['show_up'] > 0 else 0
    totals['avg_cpch'] = totals['spend'] / totals['chiusure'] if totals['chiusure'] > 0 else 0
    totals['roas'] = totals['revenue'] / totals['spend'] if totals['spend'] > 0 else 0
    totals['roas_cash'] = totals['cash'] / totals['spend'] if totals['spend'] > 0 else 0
    
    results.sort(key=lambda x: -x['spend'])
    
    return results, totals

def generate_report(results, totals, date_range):
    """Genera report MD"""
    
    md = f"""# 📊 LDP Marketing Analysis
## Periodo: {date_range} 2025
### Escluse: Future mamme, Trading

---

## 📈 Metriche Generali

| Metrica | Valore |
|---------|-------:|
| **Spesa Totale** | €{totals['spend']:,.2f} |
| **Candidature** | {totals['cands']:,} |
| **Calls** | {totals['calls']:,} |
| **Show Up** | {totals['show_up']:,} ({totals['show_up']/totals['calls']*100:.1f}%) |
| **Chiusure** | {totals['chiusure']:,} ({totals['chiusure']/totals['show_up']*100:.1f}% su SU) |
| **Revenue** | €{totals['revenue']:,.2f} |
| **Cash Collected** | €{totals['cash']:,.2f} |

---

## 💰 KPI

| KPI | Valore |
|-----|-------:|
| **CPL** | €{totals['avg_cpl']:.2f} |
| **CPC** | €{totals['avg_cpc']:.2f} |
| **CPSU** | €{totals['avg_cps']:.2f} |
| **CPCl** | €{totals['avg_cpch']:.2f} |
| **ROAS (Rev)** | {totals['roas']:.2f}x |
| **ROAS (Cash)** | {totals['roas_cash']:.2f}x |

---

## 📊 Performance per Ad Set

| Ad Set | Spesa | Cand | Call | SU | Cl | CPL | ROAS |
|--------|------:|-----:|-----:|---:|---:|----:|-----:|
"""
    
    for r in results:
        name_short = r['name'][:40] + "..." if len(r['name']) > 40 else r['name']
        cpl_str = f"€{r['cpl']:.2f}" if r['cpl'] > 0 else "-"
        roas_str = f"{r['roas']:.2f}x" if r['roas'] > 0 else "-"
        md += f"| {name_short} | €{r['spend']:.0f} | {r['cands']} | {r['calls']} | {r['show_up']} | {r['chiusure']} | {cpl_str} | {roas_str} |\n"
    
    md += f"""
---

## 🏆 Top Performers (ROAS)

"""
    sorted_roas = sorted([r for r in results if r['roas'] > 0], key=lambda x: -x['roas'])
    for i, r in enumerate(sorted_roas[:5], 1):
        md += f"{i}. **{r['name'][:45]}** - {r['roas']:.2f}x (€{r['revenue']:.0f}/€{r['spend']:.0f})\n"
    
    md += """
## ⚠️ Worst Performers (alta spesa, 0 chiusure)

"""
    worst = sorted([r for r in results if r['spend'] > 150 and r['chiusure'] == 0], key=lambda x: -x['spend'])
    for r in worst[:5]:
        md += f"- **{r['name'][:45]}** - €{r['spend']:.0f} | {r['calls']} calls | 0 chiusure\n"
    
    md += f"""
---

## 📉 Grafici

```
COSTO PER LEAD (CPL)
"""
    sorted_cpl = sorted([r for r in results if r['cpl'] > 0], key=lambda x: x['cpl'])
    for r in sorted_cpl[:8]:
        bar = '█' * int(r['cpl'] / 2)
        md += f"{r['name'][:18]:<18} {bar} €{r['cpl']:.2f}\n"
    
    md += """```

```
ROAS
"""
    for r in sorted_roas[:8]:
        bar = '█' * int(r['roas'] * 5)
        md += f"{r['name'][:18]:<18} {bar} {r['roas']:.2f}x\n"
    
    md += f"""```

---

*Report generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}*
"""
    
    return md

def main():
    print("=" * 80)
    print("LDP MARKETING ANALYSIS")
    print("=" * 80)
    print()
    
    # Load data
    print("Loading ads data...")
    ads, total_ads_spend = load_ads_data()
    print(f"  {len(ads)} ad sets, €{total_ads_spend:.2f} total spend")
    
    print("Loading Airtable data...")
    all_cands, all_calls, closed = load_airtable_data()
    print(f"  {len(all_cands['records'])} candidature, {len(all_calls['records'])} calls")
    
    # Filter for Dec 1-14
    print("\nFiltering for Dec 1-14, 2025...")
    cands = filter_by_date(all_cands, '2025-12-01', '2025-12-15')
    calls = filter_by_date(all_calls, '2025-12-01', '2025-12-15')
    print(f"  {len(cands)} candidature, {len(calls)} calls in period")
    
    # Scale ads spend to 14 days
    for name in ads:
        ads[name]['spend'] *= (14/15)
    
    # Analyze
    print("\nAnalyzing data (excluding Future mamme, Trading)...")
    results, totals = analyze_data(ads, cands, calls, closed, "1-14 Dic")
    
    # Print summary
    print()
    print("=" * 80)
    print("RISULTATI")
    print("=" * 80)
    print(f"Spesa:      €{totals['spend']:,.2f}")
    print(f"Candidature: {totals['cands']}")
    print(f"Calls:       {totals['calls']}")
    print(f"Show Up:     {totals['show_up']}")
    print(f"Chiusure:    {totals['chiusure']}")
    print(f"Revenue:     €{totals['revenue']:,.2f}")
    print(f"ROAS:        {totals['roas']:.2f}x")
    print()
    
    # Save analysis JSON
    with open(f"{ANALYSIS_DIR}/analysis_dec_1-14.json", 'w') as f:
        json.dump({'results': results, 'totals': totals}, f, indent=2)
    print(f"Analysis saved to {ANALYSIS_DIR}/analysis_dec_1-14.json")
    
    # Generate MD report
    md = generate_report(results, totals, "1-14 Dicembre")
    with open(f"{REPORTS_DIR}/report_dec_1-14.md", 'w') as f:
        f.write(md)
    print(f"Report saved to {REPORTS_DIR}/report_dec_1-14.md")
    
    return results, totals

if __name__ == "__main__":
    main()
