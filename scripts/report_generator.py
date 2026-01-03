"""
LDP Marketing Analysis - Report Generator
==========================================
Genera report in formato Markdown e PDF.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict

from config import REPORTS_DIR


def generate_markdown_report(results: dict) -> str:
    """Genera report in formato Markdown."""

    period = results.get('period', '')
    date_start = results.get('date_start', '')
    date_end = results.get('date_end', '')
    totals = results.get('meta_totals', {})

    md = f"""# LDP Marketing Report - {period.upper()}

**Periodo:** {date_start} → {date_end}
**Generato:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 1. Riepilogo Spesa ADS

| Metrica | Valore |
|---------|--------|
| **Spesa Totale** | €{totals.get('spend', 0):,.2f} |
| **Impressions** | {totals.get('impressions', 0):,} |
| **Reach** | {totals.get('reach', 0):,} |

### Spesa per Campagna

| Campagna | Spesa |
|----------|-------|
"""

    for camp in results.get('campaigns', []):
        md += f"| {camp['name']} | €{camp['spend']:,.2f} |\n"

    # Vista Conservativa
    cons = results['views'].get('conservative', {})
    cons_m = cons.get('metrics', {})

    md += f"""

---

## 2. Vista Conservativa (Meta + 50% fonte vuota)

> Attribuzione: fonte "meta" al 100% + 50% delle fonti vuote (arrotondato per eccesso)

### Funnel

| Step | Count |
|------|-------|
| Candidature | {cons.get('candidature', 0)} |
| Calls | {cons.get('calls', 0)} |
| Show Up | {cons.get('show_ups', 0)} |
| Chiusure | {cons.get('closures', 0)} |

### Metriche Costo

| Metrica | Valore |
|---------|--------|
| **CPL** (Cost per Lead) | €{cons_m.get('CPL', 0):,.2f} |
| **CPC** (Cost per Call) | €{cons_m.get('CPC', 0):,.2f} |
| **CPSU** (Cost per Show Up) | €{cons_m.get('CPSU', 0):,.2f} |
| **CPCl** (Cost per Closure) | €{cons_m.get('CPCl', 0):,.2f} |

### Performance

| Metrica | Valore |
|---------|--------|
| **Show Up Rate** | {cons_m.get('show_up_rate', 0)}% |
| **Close Rate** | {cons_m.get('close_rate', 0)}% |

### Revenue vs Cash

| Metrica | Valore |
|---------|--------|
| **Revenue** (valore vendite) | €{cons_m.get('revenue', 0):,.2f} |
| **ROAS Revenue** | {cons_m.get('ROAS_revenue', 0)}x |
| **Cash** (incassato) | €{cons_m.get('cash', 0):,.2f} |
| **ROAS Cash** | {cons_m.get('ROAS_cash', 0)}x |

"""

    # Vista Panoramica
    pan = results['views'].get('panoramic', {})
    pan_m = pan.get('metrics', {})

    md += f"""
---

## 3. Vista Panoramica (Meta + 100% fonte vuota)

> Attribuzione: fonte "meta" al 100% + 100% delle fonti vuote

### Funnel

| Step | Count |
|------|-------|
| Candidature | {pan.get('candidature', 0)} |
| Calls | {pan.get('calls', 0)} |
| Show Up | {pan.get('show_ups', 0)} |
| Chiusure | {pan.get('closures', 0)} |

### Metriche Costo

| Metrica | Valore |
|---------|--------|
| **CPL** (Cost per Lead) | €{pan_m.get('CPL', 0):,.2f} |
| **CPC** (Cost per Call) | €{pan_m.get('CPC', 0):,.2f} |
| **CPSU** (Cost per Show Up) | €{pan_m.get('CPSU', 0):,.2f} |
| **CPCl** (Cost per Closure) | €{pan_m.get('CPCl', 0):,.2f} |

### Performance

| Metrica | Valore |
|---------|--------|
| **Show Up Rate** | {pan_m.get('show_up_rate', 0)}% |
| **Close Rate** | {pan_m.get('close_rate', 0)}% |

### Revenue vs Cash

| Metrica | Valore |
|---------|--------|
| **Revenue** (valore vendite) | €{pan_m.get('revenue', 0):,.2f} |
| **ROAS Revenue** | {pan_m.get('ROAS_revenue', 0)}x |
| **Cash** (incassato) | €{pan_m.get('cash', 0):,.2f} |
| **ROAS Cash** | {pan_m.get('ROAS_cash', 0)}x |

"""

    # Altre fonti
    other = results['views'].get('other_sources', {})

    md += f"""
---

## 4. Altre Fonti (Non attribuite ADS)

### Candidature per fonte

| Fonte | Count |
|-------|-------|
"""
    for source, count in sorted(other.get('candidature', {}).items(), key=lambda x: -x[1]):
        md += f"| {source} | {count} |\n"

    md += """
### Calls per fonte

| Fonte | Count |
|-------|-------|
"""
    for source, count in sorted(other.get('calls', {}).items(), key=lambda x: -x[1]):
        md += f"| {source} | {count} |\n"

    # Breakdown fonti
    breakdown = results.get('source_breakdown', {})
    cand_bd = breakdown.get('candidature', {})

    md += f"""

---

## 5. Breakdown Fonti (Candidature)

| Fonte | Count | % |
|-------|-------|---|
| Meta | {cand_bd.get('meta', {}).get('count', 0)} | {cand_bd.get('meta', {}).get('pct', 0)}% |
| Vuoto | {cand_bd.get('vuoto', {}).get('count', 0)} | {cand_bd.get('vuoto', {}).get('pct', 0)}% |
| Altre | {cand_bd.get('altri_total', 0)} | - |

"""

    # ROAS Totale
    totals_all = results.get('totals', {})
    md += f"""

---

## 6. ROAS Totale (Tutte le Fonti)

> Include TUTTE le chiusure del periodo, indipendentemente dalla fonte UTM.

| Metrica | Attribuito (Meta) | Totale |
|---------|-------------------|--------|
| **Chiusure** | {cons.get('closures', 0)} | {totals_all.get('closures', 0)} |
| **Revenue** | €{cons_m.get('revenue', 0):,.2f} | €{totals_all.get('revenue', 0):,.2f} |
| **ROAS Revenue** | {cons_m.get('ROAS_revenue', 0)}x | {totals_all.get('ROAS_revenue', 0)}x |
| **Cash** | €{cons_m.get('cash', 0):,.2f} | €{totals_all.get('cash', 0):,.2f} |
| **ROAS Cash** | {cons_m.get('ROAS_cash', 0)}x | {totals_all.get('ROAS_cash', 0)}x |

"""

    # Top AdSets
    md += """
---

## 7. Top 10 Ad Sets per Spesa

| Ad Set | Campagna | Spesa |
|--------|----------|-------|
"""
    for adset in results.get('top_adsets', []):
        name = adset['name'][:40] + '...' if len(adset['name']) > 40 else adset['name']
        md += f"| {name} | {adset['campaign']} | €{adset['spend']:,.2f} |\n"

    md += f"""

---

*Report generato automaticamente - LDP Marketing Analysis*
"""

    return md


def save_report(results: dict, format: str = 'md') -> Path:
    """
    Salva report su file.

    Args:
        results: Risultati dell'analisi
        format: 'md' o 'pdf'

    Returns:
        Path del file salvato
    """
    period = results.get('period', 'unknown')
    date_end = results.get('date_end', datetime.now().strftime('%Y-%m-%d'))

    REPORTS_DIR.mkdir(exist_ok=True)

    if format == 'md':
        filename = f"LDP_Report_{period}_{date_end}.md"
        filepath = REPORTS_DIR / filename

        content = generate_markdown_report(results)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    elif format == 'pdf':
        # Prima genera MD
        md_path = save_report(results, 'md')

        # Poi converti in PDF usando pandoc/chrome
        pdf_filename = f"LDP_Report_{period}_{date_end}.pdf"
        pdf_path = REPORTS_DIR / pdf_filename

        import subprocess

        # Prova con pandoc
        try:
            subprocess.run([
                'pandoc', str(md_path),
                '-o', str(pdf_path),
                '--pdf-engine=xelatex'
            ], check=True)
        except:
            # Fallback: converti via HTML + Chrome
            html_path = REPORTS_DIR / f"temp_{period}.html"

            subprocess.run([
                'pandoc', str(md_path),
                '-o', str(html_path),
                '--standalone',
                '--metadata', 'title=LDP Report'
            ], check=True)

            # Chrome headless
            chrome_cmd = [
                'google-chrome', '--headless', '--disable-gpu',
                f'--print-to-pdf={pdf_path}',
                str(html_path)
            ]
            subprocess.run(chrome_cmd, check=True)

            html_path.unlink()  # Rimuovi temp

        return pdf_path

    return None


if __name__ == "__main__":
    # Test con dati mock
    test_results = {
        'period': 'test',
        'date_start': '2025-12-01',
        'date_end': '2025-12-14',
        'meta_totals': {'spend': 6748.92, 'impressions': 1000000, 'reach': 500000},
        'campaigns': [{'name': 'Test LDP', 'spend': 5000}],
        'views': {
            'conservative': {
                'candidature': 500, 'calls': 200, 'show_ups': 100, 'closures': 10,
                'metrics': {'CPL': 13.5, 'CPC': 33.7, 'CPSU': 67.5, 'CPCl': 674.9, 'ROAS': 1.5, 'show_up_rate': 50, 'close_rate': 10, 'revenue': 10000}
            },
            'panoramic': {
                'candidature': 600, 'calls': 250, 'show_ups': 120, 'closures': 12,
                'metrics': {'CPL': 11.2, 'CPC': 27.0, 'CPSU': 56.2, 'CPCl': 562.4, 'ROAS': 1.8, 'show_up_rate': 48, 'close_rate': 10, 'revenue': 12000}
            },
            'other_sources': {'candidature': {'Instagram': 50}, 'calls': {'Instagram': 20}}
        },
        'source_breakdown': {
            'candidature': {'meta': {'count': 300, 'pct': 50}, 'vuoto': {'count': 200, 'pct': 33}, 'altri_total': 100}
        },
        'top_adsets': [{'name': 'Test AdSet', 'campaign': 'Test LDP', 'spend': 1000}]
    }

    path = save_report(test_results, 'md')
    print(f"Report salvato: {path}")
