"""
LDP Marketing Analysis - Main Analyzer
======================================
Modulo principale per calcolare tutte le metriche marketing.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    EXCLUDED_CAMPAIGNS, DEFAULT_TICKET_VALUE,
    DATA_DIR, META_EXPORTS_DIR, REPORTS_DIR
)
from attribution import (
    calculate_attributed_metrics,
    calculate_metrics_by_adset,
    get_attribution_breakdown,
    categorize_source
)


class LDPAnalyzer:
    """Analizzatore marketing LDP."""

    def __init__(self, period: str):
        """
        Inizializza l'analizzatore.

        Args:
            period: '1w', '2w', '28d' - cartella con dati Meta
        """
        self.period = period
        self.meta_data = {}
        self.candidature = []
        self.calls = []
        self.date_start = None
        self.date_end = None

    def load_meta_data(self):
        """Carica dati Meta Ads dai CSV."""
        period_dir = META_EXPORTS_DIR / self.period

        # Load campaigns
        campaigns_file = period_dir / "campaigns.csv"
        if campaigns_file.exists():
            with open(campaigns_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.meta_data['campaigns'] = [
                    r for r in reader
                    if r.get('Campaign name', '') and
                    r.get('Campaign name', '') not in EXCLUDED_CAMPAIGNS
                ]

        # Load adsets
        adsets_file = period_dir / "adsets.csv"
        if adsets_file.exists():
            with open(adsets_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Prima riga senza nome è il totale
                for row in rows:
                    if not row.get('Ad set name', ''):
                        self.date_start = row.get('Reporting starts', '')
                        self.date_end = row.get('Reporting ends', '')
                        self.meta_data['totals'] = {
                            'spend': float(row.get('Amount spent (EUR)', '0')),
                            'impressions': int(row.get('Impressions', '0') or 0),
                            'reach': int(row.get('Reach', '0') or 0),
                        }
                        break

                # Filtra adsets escludendo campagne
                self.meta_data['adsets'] = [
                    r for r in rows
                    if r.get('Ad set name', '') and
                    r.get('Campaign name', '') not in EXCLUDED_CAMPAIGNS
                ]

        # Load ads
        ads_file = period_dir / "ads.csv"
        if ads_file.exists():
            with open(ads_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.meta_data['ads'] = [
                    r for r in reader
                    if r.get('Ad name', '') and
                    r.get('Campaign name', '') not in EXCLUDED_CAMPAIGNS
                ]

    def load_airtable_data(self):
        """Carica dati Airtable (candidature e calls)."""
        # Carica candidature
        cand_file = DATA_DIR / "candidature_with_source.json"
        if cand_file.exists():
            with open(cand_file, 'r') as f:
                data = json.load(f)
                self.candidature = self._filter_by_date(
                    data.get('records', []),
                    'Data Creazione'
                )

        # Carica calls - usa Data Call (quando avviene la chiamata)
        # invece di Data Creazione (quando è stata prenotata)
        calls_file = DATA_DIR / "calls_full.json"
        if calls_file.exists():
            with open(calls_file, 'r') as f:
                data = json.load(f)
                self.calls = self._filter_by_date(
                    data.get('records', []),
                    'Data Call'
                )

    def _filter_by_date(self, records: List[dict], date_field: str) -> List[dict]:
        """Filtra record per periodo e campagne escluse."""
        if not self.date_start or not self.date_end:
            return records

        filtered = []
        start = datetime.strptime(self.date_start, '%Y-%m-%d').date()
        end = datetime.strptime(self.date_end, '%Y-%m-%d').date()

        for record in records:
            fields = record.get('fields', {})

            # Filtra per campagne escluse
            campaign = fields.get('UTM Campaign', '') or fields.get('UTM Campagna (campaign)', '')
            if campaign in EXCLUDED_CAMPAIGNS:
                continue

            # Filtra per data
            date_str = fields.get(date_field, '')
            if not date_str:
                continue

            try:
                if 'T' in date_str:
                    record_date = datetime.fromisoformat(
                        date_str.replace('Z', '+00:00')
                    ).date()
                else:
                    record_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                if start <= record_date <= end:
                    filtered.append(record)
            except:
                continue

        return filtered

    def calculate_all_metrics(self) -> dict:
        """Calcola tutte le metriche."""
        results = {
            'period': self.period,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'meta_totals': self.meta_data.get('totals', {}),
            'campaigns': [],
            'views': {}
        }

        total_spend = results['meta_totals'].get('spend', 0)

        # === CANDIDATURE ===
        cand_breakdown = get_attribution_breakdown(
            self.candidature,
            'UTM Source'
        )

        # === CALLS ===
        calls_breakdown = get_attribution_breakdown(
            self.calls,
            'UTM Fonte (source)'
        )

        # === SHOW UP ===
        show_ups = [
            c for c in self.calls
            if c.get('fields', {}).get('Stato', '') not in ['No Show', 'Scartato', 'Cancellato']
            and c.get('fields', {}).get('Conta No Show', 0) == 0
        ]
        showup_breakdown = get_attribution_breakdown(
            show_ups,
            'UTM Fonte (source)'
        )

        # === CHIUSURE ===
        closures = [
            c for c in self.calls
            if c.get('fields', {}).get('Conta Chiusure', 0) > 0
        ]
        closure_breakdown = get_attribution_breakdown(
            closures,
            'UTM Fonte (source)'
        )

        # === REVENUE E CASH ===
        # Revenue = valore vendita singola
        # Cash Collected = incassato effettivo
        # IMPORTANTE: calcolo diretto per fonte, NON proporzionale!

        total_revenue = 0
        total_cash = 0
        attr_revenue_cons = 0  # Conservativo: meta 100% + vuoto 50%
        attr_cash_cons = 0
        attr_revenue_pan = 0   # Panoramico: meta 100% + vuoto 100%
        attr_cash_pan = 0

        for c in closures:
            fields = c.get('fields', {})
            source = fields.get('UTM Fonte (source)', '') or ''
            rev = fields.get('Revenue', 0) or 0
            cash = fields.get('Cash Collected', 0) or 0

            total_revenue += rev
            total_cash += cash

            source_cat = categorize_source(source)

            if source_cat == 'meta':
                # 100% attribuito
                attr_revenue_cons += rev
                attr_cash_cons += cash
                attr_revenue_pan += rev
                attr_cash_pan += cash
            elif source_cat == 'vuoto':
                # Conservativo: 50%, Panoramico: 100%
                attr_revenue_cons += rev * 0.5
                attr_cash_cons += cash * 0.5
                attr_revenue_pan += rev
                attr_cash_pan += cash
            # else: fonte "altro" - non attribuire

        # === VISTA 1: Conservativa (Meta + 50% vuoto) ===
        cons_cand, _ = calculate_attributed_metrics(
            self.candidature, 'UTM Source', 'conservative'
        )
        cons_calls, _ = calculate_attributed_metrics(
            self.calls, 'UTM Fonte (source)', 'conservative'
        )
        cons_su, _ = calculate_attributed_metrics(
            show_ups, 'UTM Fonte (source)', 'conservative'
        )
        cons_cl, _ = calculate_attributed_metrics(
            closures, 'UTM Fonte (source)', 'conservative'
        )

        results['views']['conservative'] = {
            'name': 'Conservativa (Meta + 50% vuoto)',
            'candidature': cons_cand,
            'calls': cons_calls,
            'show_ups': cons_su,
            'closures': cons_cl,
            'metrics': self._calc_cost_metrics_direct(total_spend, cons_cand, cons_calls, cons_su, cons_cl, attr_revenue_cons, attr_cash_cons)
        }

        # === VISTA 2: Panoramica (Meta + 100% vuoto) ===
        pan_cand, _ = calculate_attributed_metrics(
            self.candidature, 'UTM Source', 'panoramic'
        )
        pan_calls, _ = calculate_attributed_metrics(
            self.calls, 'UTM Fonte (source)', 'panoramic'
        )
        pan_su, _ = calculate_attributed_metrics(
            show_ups, 'UTM Fonte (source)', 'panoramic'
        )
        pan_cl, _ = calculate_attributed_metrics(
            closures, 'UTM Fonte (source)', 'panoramic'
        )

        results['views']['panoramic'] = {
            'name': 'Panoramica (Meta + 100% vuoto)',
            'candidature': pan_cand,
            'calls': pan_calls,
            'show_ups': pan_su,
            'closures': pan_cl,
            'metrics': self._calc_cost_metrics_direct(total_spend, pan_cand, pan_calls, pan_su, pan_cl, attr_revenue_pan, attr_cash_pan)
        }

        # === VISTA 3: Altre fonti ===
        results['views']['other_sources'] = {
            'candidature': cand_breakdown['altri'],
            'calls': calls_breakdown['altri'],
            'show_ups': showup_breakdown['altri'],
            'closures': closure_breakdown['altri']
        }

        # === ROAS TOTALE (tutte le fonti) ===
        results['totals'] = {
            'closures': len(closures),
            'revenue': total_revenue,
            'cash': total_cash,
            'ROAS_revenue': round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
            'ROAS_cash': round(total_cash / total_spend, 2) if total_spend > 0 else 0,
        }

        # === BREAKDOWN FONTI ===
        results['source_breakdown'] = {
            'candidature': cand_breakdown,
            'calls': calls_breakdown
        }

        # === CAMPAGNE ===
        for campaign in self.meta_data.get('campaigns', []):
            name = campaign.get('Campaign name', '')
            spend = float(campaign.get('Amount spent (EUR)', '0'))
            if spend > 0:
                results['campaigns'].append({
                    'name': name,
                    'spend': spend,
                    'impressions': int(campaign.get('Impressions', '0') or 0),
                    'reach': int(campaign.get('Reach', '0') or 0),
                })

        # === ADSETS TOP 10 ===
        adsets_sorted = sorted(
            self.meta_data.get('adsets', []),
            key=lambda x: float(x.get('Amount spent (EUR)', '0')),
            reverse=True
        )[:10]

        results['top_adsets'] = [
            {
                'name': a.get('Ad set name', ''),
                'campaign': a.get('Campaign name', ''),
                'spend': float(a.get('Amount spent (EUR)', '0')),
                'impressions': int(a.get('Impressions', '0') or 0),
            }
            for a in adsets_sorted
        ]

        return results

    def _calc_cost_metrics_direct(
        self,
        spend: float,
        cand: int,
        calls: int,
        show_ups: int,
        closures: int,
        attr_revenue: float,
        attr_cash: float
    ) -> dict:
        """
        Calcola metriche di costo con Revenue e Cash già calcolati per fonte.

        IMPORTANTE: attr_revenue e attr_cash sono già calcolati sommando
        direttamente i valori delle chiusure per fonte (non proporzionali!).
        """
        return {
            'CPL': round(spend / cand, 2) if cand > 0 else 0,
            'CPC': round(spend / calls, 2) if calls > 0 else 0,
            'CPSU': round(spend / show_ups, 2) if show_ups > 0 else 0,
            'CPCl': round(spend / closures, 2) if closures > 0 else 0,
            'show_up_rate': round(show_ups / calls * 100, 1) if calls > 0 else 0,
            'close_rate': round(closures / show_ups * 100, 1) if show_ups > 0 else 0,
            # Revenue (valore vendite attribuite)
            'revenue': round(attr_revenue, 2),
            'ROAS_revenue': round(attr_revenue / spend, 2) if spend > 0 else 0,
            # Cash (incassato attribuito)
            'cash': round(attr_cash, 2),
            'ROAS_cash': round(attr_cash / spend, 2) if spend > 0 else 0,
        }


def run_analysis(period: str) -> dict:
    """Esegui analisi completa per un periodo."""
    analyzer = LDPAnalyzer(period)

    print(f"📊 Caricamento dati Meta ({period})...")
    analyzer.load_meta_data()

    print(f"📥 Caricamento dati Airtable...")
    analyzer.load_airtable_data()

    print(f"🔢 Calcolo metriche...")
    results = analyzer.calculate_all_metrics()

    print(f"✅ Analisi completata per {period}")
    return results


if __name__ == "__main__":
    # Test
    results = run_analysis("2w")
    print(json.dumps(results, indent=2, default=str))
