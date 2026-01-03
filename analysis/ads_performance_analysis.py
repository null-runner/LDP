#!/usr/bin/env python3
"""
Analisi dettagliata performance ADS - Dicembre 2025
"""
import csv
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
ADS_CSV = BASE_DIR / "data/meta_exports/28d/ads.csv"

def analyze_ads():
    """Analizza performance delle singole ads."""

    ads = []
    with open(ADS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip summary row and inactive
            if not row.get('Ad name'):
                continue

            try:
                spend = float(row.get('Amount spent (EUR)', '0') or 0)
                leads = int(row.get('Leads', '0') or 0)
                impressions = int(row.get('Impressions', '0') or 0)
                reach = int(row.get('Reach', '0') or 0)
                clicks = int(row.get('Unique link clicks', '0') or 0)

                # Skip ads with no spend
                if spend == 0:
                    continue

                cpl = spend / leads if leads > 0 else 999999
                ctr = (clicks / reach * 100) if reach > 0 else 0
                cpm = float(row.get('CPM (cost per 1,000 impressions) (EUR)', '0') or 0)

                # Video metrics
                plays_25 = int(row.get('Video plays at 25%', '0') or 0)
                plays_50 = int(row.get('Video plays at 50%', '0') or 0)
                plays_100 = int(row.get('Video plays at 100%', '0') or 0)

                retention_25 = (plays_25 / impressions * 100) if impressions > 0 else 0
                retention_50 = (plays_50 / impressions * 100) if impressions > 0 else 0
                retention_100 = (plays_100 / impressions * 100) if impressions > 0 else 0

                ads.append({
                    'name': row['Ad name'],
                    'status': row['Ad delivery'],
                    'spend': spend,
                    'leads': leads,
                    'cpl': cpl,
                    'impressions': impressions,
                    'reach': reach,
                    'clicks': clicks,
                    'ctr': ctr,
                    'cpm': cpm,
                    'retention_25': retention_25,
                    'retention_50': retention_50,
                    'retention_100': retention_100,
                })
            except:
                continue

    return ads

def print_analysis(ads):
    """Stampa analisi dettagliata."""

    # Sort by different metrics
    by_spend = sorted(ads, key=lambda x: x['spend'], reverse=True)
    by_leads = sorted(ads, key=lambda x: x['leads'], reverse=True)
    by_cpl = sorted([a for a in ads if a['leads'] > 0], key=lambda x: x['cpl'])
    by_ctr = sorted(ads, key=lambda x: x['ctr'], reverse=True)

    print("\n" + "="*80)
    print("📊 ANALISI PERFORMANCE ADS - DICEMBRE 2025")
    print("="*80)

    # Overview
    total_spend = sum(a['spend'] for a in ads)
    total_leads = sum(a['leads'] for a in ads)
    avg_cpl = total_spend / total_leads if total_leads > 0 else 0

    print(f"\n🎯 OVERVIEW:")
    print(f"   Ads totali attive: {len(ads)}")
    print(f"   Ads con leads: {len([a for a in ads if a['leads'] > 0])}")
    print(f"   Spesa totale: €{total_spend:,.2f}")
    print(f"   Leads totali: {total_leads:,}")
    print(f"   CPL medio: €{avg_cpl:.2f}")

    # Top 5 per spesa
    print(f"\n💰 TOP 5 PER SPESA:")
    for i, ad in enumerate(by_spend[:5], 1):
        print(f"   {i}. {ad['name'][:60]}")
        print(f"      Spesa: €{ad['spend']:,.2f} | Leads: {ad['leads']} | CPL: €{ad['cpl']:.2f}")

    # Top 5 per leads
    print(f"\n🎯 TOP 5 PER LEADS GENERATI:")
    for i, ad in enumerate(by_leads[:5], 1):
        print(f"   {i}. {ad['name'][:60]}")
        print(f"      Leads: {ad['leads']} | Spesa: €{ad['spend']:,.2f} | CPL: €{ad['cpl']:.2f}")

    # Top 5 per CPL (più efficiente)
    print(f"\n✨ TOP 5 PIÙ EFFICIENTI (CPL più basso):")
    for i, ad in enumerate(by_cpl[:5], 1):
        print(f"   {i}. {ad['name'][:60]}")
        print(f"      CPL: €{ad['cpl']:.2f} | Leads: {ad['leads']} | Spesa: €{ad['spend']:,.2f}")

    # Worst 5 per CPL
    print(f"\n❌ WORST 5 (CPL più alto - da ottimizzare):")
    for i, ad in enumerate(reversed(by_cpl[-5:]), 1):
        print(f"   {i}. {ad['name'][:60]}")
        print(f"      CPL: €{ad['cpl']:.2f} | Leads: {ad['leads']} | Spesa: €{ad['spend']:,.2f}")

    # Top 5 per CTR
    print(f"\n👆 TOP 5 PER CTR (Click-Through Rate):")
    for i, ad in enumerate(by_ctr[:5], 1):
        print(f"   {i}. {ad['name'][:60]}")
        print(f"      CTR: {ad['ctr']:.2f}% | Clicks: {ad['clicks']} | Reach: {ad['reach']:,}")

    # Video retention analysis
    print(f"\n📺 TOP 5 VIDEO RETENTION (% che guarda fino in fondo):")
    by_retention = sorted(ads, key=lambda x: x['retention_100'], reverse=True)
    for i, ad in enumerate(by_retention[:5], 1):
        print(f"   {i}. {ad['name'][:60]}")
        print(f"      100%: {ad['retention_100']:.1f}% | 50%: {ad['retention_50']:.1f}% | 25%: {ad['retention_25']:.1f}%")

    # Insights
    print(f"\n💡 INSIGHTS:")

    # Best ROI ad
    best_cpl = by_cpl[0]
    worst_cpl = by_cpl[-1]
    print(f"   🏆 AD più efficiente: '{best_cpl['name'][:50]}' con CPL €{best_cpl['cpl']:.2f}")
    print(f"   ⚠️  AD meno efficiente: '{worst_cpl['name'][:50]}' con CPL €{worst_cpl['cpl']:.2f}")
    print(f"   📊 Differenza: {worst_cpl['cpl'] / best_cpl['cpl']:.1f}x peggiore")

    # High spend low performance
    print(f"\n   🔍 ADS con alta spesa ma basso ROI (CPL > €15):")
    inefficient = [a for a in ads if a['cpl'] > 15 and a['spend'] > 200]
    for ad in sorted(inefficient, key=lambda x: x['spend'], reverse=True)[:3]:
        print(f"      • {ad['name'][:60]}")
        print(f"        Spesa: €{ad['spend']:,.2f} | CPL: €{ad['cpl']:.2f} | Leads: {ad['leads']}")
        print(f"        → Potenziale risparmio: €{(ad['cpl'] - avg_cpl) * ad['leads']:.2f}")

    # Active vs inactive
    active = [a for a in ads if a['status'] == 'active']
    inactive = [a for a in ads if a['status'] != 'active']
    print(f"\n   📊 Status:")
    print(f"      Active: {len(active)} ({sum(a['spend'] for a in active):,.2f}€)")
    print(f"      Not delivering/Inactive: {len(inactive)} ({sum(a['spend'] for a in inactive):,.2f}€)")

    print("\n" + "="*80)

if __name__ == "__main__":
    ads = analyze_ads()
    print_analysis(ads)
