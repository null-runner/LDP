#!/usr/bin/env python3
"""
LDP Marketing Analysis - Runner
===============================
Script principale per eseguire l'analisi e generare report.

Uso:
    python run_analysis.py              # Tutti i periodi
    python run_analysis.py 2w           # Solo periodo specifico
    python run_analysis.py --refresh    # Forza refresh cache Airtable
"""

import argparse
import json
import sys
from pathlib import Path

# Aggiungi script dir al path
sys.path.insert(0, str(Path(__file__).parent))

from analyzer import run_analysis
from report_generator import save_report, generate_markdown_report
from config import DATA_DIR, REPORTS_DIR


PERIODS = {
    '1w': 'Ultima Settimana',
    '2w': '2 Settimane',
    '28d': '28 Giorni'
}


def refresh_cache():
    """Rimuove i file cache per forzare download fresh."""
    cache_files = list(DATA_DIR.glob('*_cache.json'))
    for f in cache_files:
        f.unlink()
        print(f"🗑️  Rimosso: {f.name}")


def run_single(period: str, save_json: bool = False) -> dict:
    """Esegue analisi per un singolo periodo."""
    print(f"\n{'='*60}")
    print(f"📊 ANALISI {PERIODS.get(period, period).upper()}")
    print(f"{'='*60}")

    results = run_analysis(period)

    # Salva report MD
    md_path = save_report(results, 'md')
    print(f"📝 Report MD: {md_path}")

    # Salva JSON (opzionale)
    if save_json:
        json_path = REPORTS_DIR / f"LDP_Data_{period}_{results['date_end']}.json"
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📦 Data JSON: {json_path}")

    # Stampa riepilogo
    print_summary(results)

    return results


def print_summary(results: dict):
    """Stampa riepilogo a console."""
    totals = results.get('meta_totals', {})
    cons = results['views'].get('conservative', {})
    cons_m = cons.get('metrics', {})

    print(f"\n📈 RIEPILOGO RAPIDO")
    print(f"   Spesa: €{totals.get('spend', 0):,.2f}")
    print(f"   Candidature (attr.): {cons.get('candidature', 0)}")
    print(f"   Calls (attr.): {cons.get('calls', 0)}")
    print(f"   Show Up (attr.): {cons.get('show_ups', 0)}")
    print(f"   Chiusure (attr.): {cons.get('closures', 0)}")
    print(f"   ---")
    print(f"   CPL: €{cons_m.get('CPL', 0):,.2f}")
    print(f"   CPSU: €{cons_m.get('CPSU', 0):,.2f}")
    print(f"   CPCl: €{cons_m.get('CPCl', 0):,.2f}")
    print(f"   ---")
    print(f"   Revenue (attr.): €{cons_m.get('revenue', 0):,.2f}")
    print(f"   ROAS Revenue (attr.): {cons_m.get('ROAS_revenue', 0)}x")
    print(f"   Cash (attr.): €{cons_m.get('cash', 0):,.2f}")
    print(f"   ROAS Cash (attr.): {cons_m.get('ROAS_cash', 0)}x")

    # Totali (tutte le fonti)
    totals_all = results.get('totals', {})
    print(f"   ---")
    print(f"   📊 TOTALE (tutte le fonti):")
    print(f"   Revenue: €{totals_all.get('revenue', 0):,.2f}")
    print(f"   ROAS Revenue: {totals_all.get('ROAS_revenue', 0)}x")
    print(f"   Cash: €{totals_all.get('cash', 0):,.2f}")
    print(f"   ROAS Cash: {totals_all.get('ROAS_cash', 0)}x")


def run_all(save_json: bool = False) -> dict:
    """Esegue analisi per tutti i periodi."""
    all_results = {}

    for period in PERIODS:
        all_results[period] = run_single(period, save_json)

    # Genera report comparativo
    generate_comparison_report(all_results)

    return all_results


def generate_comparison_report(all_results: dict):
    """Genera report comparativo tra periodi."""
    md = """# LDP Marketing - Confronto Periodi

"""

    # Tabella comparativa
    md += "| Metrica | 1 Settimana | 2 Settimane | 28 Giorni |\n"
    md += "|---------|-------------|-------------|------------|\n"

    metrics = ['spend', 'candidature', 'calls', 'show_ups', 'closures', 'CPL', 'CPSU', 'CPCl', 'revenue_attr', 'ROAS_rev_attr', 'cash_attr', 'ROAS_cash_attr', 'revenue_tot', 'ROAS_rev_tot', 'cash_tot', 'ROAS_cash_tot']

    for metric in metrics:
        row = f"| **{metric}** |"
        for period in ['1w', '2w', '28d']:
            results = all_results.get(period, {})
            cons = results.get('views', {}).get('conservative', {})
            cons_m = cons.get('metrics', {})
            totals = results.get('totals', {})

            if metric == 'spend':
                val = results.get('meta_totals', {}).get('spend', 0)
                row += f" €{val:,.2f} |"
            elif metric in ['CPL', 'CPSU', 'CPCl']:
                val = cons_m.get(metric, 0)
                row += f" €{val:,.2f} |"
            # Attribuito
            elif metric == 'revenue_attr':
                val = cons_m.get('revenue', 0)
                row += f" €{val:,.2f} |"
            elif metric == 'cash_attr':
                val = cons_m.get('cash', 0)
                row += f" €{val:,.2f} |"
            elif metric == 'ROAS_rev_attr':
                val = cons_m.get('ROAS_revenue', 0)
                row += f" {val}x |"
            elif metric == 'ROAS_cash_attr':
                val = cons_m.get('ROAS_cash', 0)
                row += f" {val}x |"
            # Totale
            elif metric == 'revenue_tot':
                val = totals.get('revenue', 0)
                row += f" €{val:,.2f} |"
            elif metric == 'cash_tot':
                val = totals.get('cash', 0)
                row += f" €{val:,.2f} |"
            elif metric == 'ROAS_rev_tot':
                val = totals.get('ROAS_revenue', 0)
                row += f" {val}x |"
            elif metric == 'ROAS_cash_tot':
                val = totals.get('ROAS_cash', 0)
                row += f" {val}x |"
            else:
                val = cons.get(metric, 0)
                row += f" {val:,} |"

        md += row + "\n"

    # Salva
    comparison_path = REPORTS_DIR / f"LDP_Comparison_{all_results.get('2w', {}).get('date_end', 'latest')}.md"
    with open(comparison_path, 'w') as f:
        f.write(md)

    print(f"\n📊 Report comparativo: {comparison_path}")


def main():
    parser = argparse.ArgumentParser(description='LDP Marketing Analysis')
    parser.add_argument('period', nargs='?', choices=['1w', '2w', '28d', 'all'],
                       default='all', help='Periodo da analizzare')
    parser.add_argument('--refresh', action='store_true',
                       help='Forza refresh cache Airtable')
    parser.add_argument('--json', action='store_true',
                       help='Salva anche dati JSON')

    args = parser.parse_args()

    if args.refresh:
        print("🔄 Refresh cache...")
        refresh_cache()

    if args.period == 'all':
        run_all(args.json)
    else:
        run_single(args.period, args.json)

    print("\n✅ Analisi completata!")


if __name__ == "__main__":
    main()
