"""
LDP Marketing Analysis - Advanced Projection Engine
=====================================================
Modulo avanzato per proiezioni ROAS con:
- Cohort Analysis (filtro per Data Creazione)
- Calcolo LAG e distribuzione maturità
- Bayesian Shrinkage / Fallback gerarchico per tassi
- Rolling Window adattiva con Backtesting automatico
- Confidence Interval per proiezioni
- Trend Detection

Autore: Claude Code
Data: 2025-12-17
"""

import json
import csv
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import warnings

# Suppress numpy warnings for clean output
warnings.filterwarnings('ignore')


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RateEstimate:
    """Stima di un tasso con incertezza."""
    value: float
    confidence: str  # 'high', 'medium', 'low'
    sample_size: int
    source: str  # 'specific', 'blended', 'global'

    def to_dict(self) -> dict:
        return {
            'value': round(self.value, 4),
            'confidence': self.confidence,
            'sample_size': self.sample_size,
            'source': self.source
        }


@dataclass
class ProjectionResult:
    """Risultato di una proiezione con doppio tracking: Revenue e Cash Collected."""

    # Revenue (valore contratti)
    revenue_actual: float
    revenue_projected_base: float
    revenue_projected_pessimistic: float
    revenue_projected_optimistic: float
    revenue_projected_corrected: float

    # Cash Collected (incasso effettivo)
    cash_actual: float
    cash_projected_base: float
    cash_projected_pessimistic: float
    cash_projected_optimistic: float
    cash_projected_corrected: float

    # Bias correction
    bias_correction_factor: float

    # Calls
    calls_completed: int
    calls_pending: int
    completion_rate: float

    # ROAS Revenue (profittabilità)
    roas_actual: float
    roas_projected_base: float
    roas_projected_pessimistic: float
    roas_projected_optimistic: float
    roas_projected_corrected: float

    # ROAS Cash (cash flow reale)
    roas_cash_actual: float
    roas_cash_projected_base: float
    roas_cash_projected_pessimistic: float
    roas_cash_projected_optimistic: float
    roas_cash_projected_corrected: float

    rates_used: Dict[str, RateEstimate]
    reliability: str  # 'consolidated', 'partial', 'early'

    def to_dict(self) -> dict:
        return {
            'revenue': {
                'actual': round(self.revenue_actual, 2),
                'projected_base': round(self.revenue_projected_base, 2),
                'projected_corrected': round(self.revenue_projected_corrected, 2),
                'projected_pessimistic': round(self.revenue_projected_pessimistic, 2),
                'projected_optimistic': round(self.revenue_projected_optimistic, 2),
            },
            'cash': {
                'actual': round(self.cash_actual, 2),
                'projected_base': round(self.cash_projected_base, 2),
                'projected_corrected': round(self.cash_projected_corrected, 2),
                'projected_pessimistic': round(self.cash_projected_pessimistic, 2),
                'projected_optimistic': round(self.cash_projected_optimistic, 2),
            },
            'calls': {
                'completed': self.calls_completed,
                'pending': self.calls_pending,
                'completion_rate': round(self.completion_rate * 100, 1),
            },
            'roas': {
                'actual': round(self.roas_actual, 2),
                'projected_base': round(self.roas_projected_base, 2),
                'projected_corrected': round(self.roas_projected_corrected, 2),
                'projected_pessimistic': round(self.roas_projected_pessimistic, 2),
                'projected_optimistic': round(self.roas_projected_optimistic, 2),
            },
            'roas_cash': {
                'actual': round(self.roas_cash_actual, 2),
                'projected_base': round(self.roas_cash_projected_base, 2),
                'projected_corrected': round(self.roas_cash_projected_corrected, 2),
                'projected_pessimistic': round(self.roas_cash_projected_pessimistic, 2),
                'projected_optimistic': round(self.roas_cash_projected_optimistic, 2),
            },
            'bias_correction': {
                'factor': round(self.bias_correction_factor, 3),
                'applied': self.bias_correction_factor < 1.0,
            },
            'rates_used': {k: v.to_dict() for k, v in self.rates_used.items()},
            'reliability': self.reliability
        }


@dataclass
class BacktestResult:
    """Risultato di un backtest."""
    window_days: int
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    bias: float  # Systematic over/under estimation
    n_periods: int

    def to_dict(self) -> dict:
        return {
            'window_days': self.window_days,
            'mape': round(self.mape * 100, 2),
            'rmse': round(self.rmse, 2),
            'bias': round(self.bias * 100, 2),
            'n_periods': self.n_periods
        }


# =============================================================================
# PROJECTION ENGINE
# =============================================================================

class ProjectionEngine:
    """
    Motore di proiezione avanzato per analisi ROAS.

    Implementa:
    1. Cohort Analysis basata su Data Creazione
    2. Calcolo LAG con distribuzione statistica
    3. Bayesian Shrinkage per tassi con sample size ridotto
    4. Rolling Window adattiva con backtesting
    5. Confidence Interval per proiezioni
    """

    # Configurazione default
    DEFAULT_CONFIG = {
        'maturity_buffer_days': 7,      # Giorni da escludere per maturità
        'min_sample_size': 30,          # Sample minimo per tasso specifico
        'shrinkage_threshold': 50,      # Sotto questo, blend con globale
        'backtest_periods': 4,          # Periodi per backtest
        'window_candidates': [14, 21, 28],  # Finestre candidate per backtest
        'confidence_pessimistic': 0.65,  # Moltiplicatore scenario pessimistico
        'confidence_optimistic': 1.40,   # Moltiplicatore scenario ottimistico
        'trend_threshold': 0.15,         # Soglia per rilevare trend
        'bias_correction_threshold': 0.05,  # Applica correzione se bias > 5%
    }

    def __init__(self, calls: List[dict], candidature: List[dict], config: dict = None):
        """
        Inizializza il motore di proiezione.

        Args:
            calls: Lista di record calls da Airtable
            candidature: Lista di record candidature da Airtable
            config: Configurazione opzionale
        """
        self.calls = calls
        self.candidature = candidature
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Parse dates
        self._parse_dates()

        # Calcola statistiche base
        self.lag_stats = self._calculate_lag_distribution()
        self.global_rates = None  # Lazy loading

    def _parse_dates(self):
        """Converte le date string in oggetti datetime."""
        for call in self.calls:
            fields = call.get('fields', {})

            # Data Creazione
            dc = fields.get('Data Creazione', '')
            if dc:
                try:
                    if 'T' in dc:
                        fields['_data_creazione'] = datetime.fromisoformat(
                            dc.replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                    else:
                        fields['_data_creazione'] = datetime.strptime(dc, '%Y-%m-%d')
                except:
                    fields['_data_creazione'] = None
            else:
                fields['_data_creazione'] = None

            # Data Call
            dcall = fields.get('Data Call', '')
            if dcall:
                try:
                    if 'T' in dcall:
                        fields['_data_call'] = datetime.fromisoformat(
                            dcall.replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                    else:
                        fields['_data_call'] = datetime.strptime(dcall, '%Y-%m-%d')
                except:
                    fields['_data_call'] = None
            else:
                fields['_data_call'] = None

        # Candidature
        for cand in self.candidature:
            fields = cand.get('fields', {})
            dc = fields.get('Data Creazione', '')
            if dc:
                try:
                    if 'T' in dc:
                        fields['_data_creazione'] = datetime.fromisoformat(
                            dc.replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                    else:
                        fields['_data_creazione'] = datetime.strptime(dc, '%Y-%m-%d')
                except:
                    fields['_data_creazione'] = None

    # =========================================================================
    # LAG ANALYSIS
    # =========================================================================

    def _calculate_lag_distribution(self) -> dict:
        """
        Calcola la distribuzione del LAG (Data Call - Data Creazione).

        Returns:
            Dict con statistiche LAG
        """
        lags = []

        for call in self.calls:
            fields = call.get('fields', {})
            dc = fields.get('_data_creazione')
            dcall = fields.get('_data_call')

            if dc and dcall:
                lag = (dcall - dc).days
                if 0 <= lag <= 60:  # Ignora outlier
                    lags.append(lag)

        if not lags:
            return {'mean': 5, 'median': 4, 'p75': 7, 'p90': 10, 'p95': 14}

        lags = np.array(lags)

        return {
            'mean': float(np.mean(lags)),
            'median': float(np.median(lags)),
            'std': float(np.std(lags)),
            'p75': float(np.percentile(lags, 75)),
            'p90': float(np.percentile(lags, 90)),
            'p95': float(np.percentile(lags, 95)),
            'min': int(np.min(lags)),
            'max': int(np.max(lags)),
            'n_samples': len(lags)
        }

    def get_maturity_window(self) -> int:
        """
        Restituisce la finestra di maturazione consigliata (P90 del LAG).
        """
        return int(np.ceil(self.lag_stats.get('p90', 10)))

    # =========================================================================
    # RATE CALCULATION
    # =========================================================================

    def calculate_rates_for_window(
        self,
        window_start: datetime,
        window_end: datetime,
        source_filter: str = None
    ) -> Dict[str, RateEstimate]:
        """
        Calcola i tassi (show rate, close rate, AOV) per una finestra temporale.

        Args:
            window_start: Inizio finestra (Data Creazione)
            window_end: Fine finestra (Data Creazione)
            source_filter: Filtra per fonte UTM (opzionale)

        Returns:
            Dict con RateEstimate per ogni tasso
        """
        # Filtra calls per Data Creazione nella finestra
        # E che siano MATURE (Data Call avvenuta)
        filtered = []

        for call in self.calls:
            fields = call.get('fields', {})
            dc = fields.get('_data_creazione')
            dcall = fields.get('_data_call')

            if not dc or not dcall:
                continue

            if not (window_start <= dc <= window_end):
                continue

            # Opzionale: filtra per source
            if source_filter:
                source = (fields.get('UTM Fonte (source)', '') or '').lower()
                if source_filter == 'meta':
                    if source not in ['meta', 'facebook', 'fb']:
                        continue
                elif source_filter == 'vuoto':
                    if source:
                        continue
                elif source != source_filter:
                    continue

            filtered.append(call)

        n = len(filtered)

        if n == 0:
            return self._get_fallback_rates()

        # Calcola metriche
        no_shows = sum(1 for c in filtered
                      if c.get('fields', {}).get('Conta No Show', 0) > 0)
        show_ups = n - no_shows
        closures = sum(1 for c in filtered
                      if c.get('fields', {}).get('Conta Chiusure', 0) > 0)

        # Calcola sia Revenue che Cash Collected per ogni chiusura
        revenues = [c.get('fields', {}).get('Revenue', 0) or 0
                   for c in filtered
                   if c.get('fields', {}).get('Conta Chiusure', 0) > 0]
        cash_collected = [c.get('fields', {}).get('Cash Collected', 0) or 0
                         for c in filtered
                         if c.get('fields', {}).get('Conta Chiusure', 0) > 0]

        # Calcola tassi
        show_rate = show_ups / n if n > 0 else 0
        close_rate = closures / show_ups if show_ups > 0 else 0
        aov = np.mean(revenues) if revenues else 0  # AOV = Ticket Medio (valore contratto)
        aov_cash = np.mean(cash_collected) if cash_collected else 0  # AOV Cash = incasso medio

        # Determina confidence e source
        if n >= self.config['min_sample_size']:
            confidence = 'high'
            source = 'specific'
        elif n >= 15:
            confidence = 'medium'
            source = 'blended'
            # Blend con tassi globali
            global_rates = self._get_global_rates(window_end)
            blend_weight = n / self.config['shrinkage_threshold']
            show_rate = show_rate * blend_weight + global_rates['show_rate'] * (1 - blend_weight)
            close_rate = close_rate * blend_weight + global_rates['close_rate'] * (1 - blend_weight)
            aov = aov * blend_weight + global_rates['aov'] * (1 - blend_weight) if aov > 0 else global_rates['aov']
            aov_cash = aov_cash * blend_weight + global_rates['aov_cash'] * (1 - blend_weight) if aov_cash > 0 else global_rates['aov_cash']
        else:
            confidence = 'low'
            source = 'global'
            global_rates = self._get_global_rates(window_end)
            show_rate = global_rates['show_rate']
            close_rate = global_rates['close_rate']
            aov = global_rates['aov']
            aov_cash = global_rates['aov_cash']

        return {
            'show_rate': RateEstimate(show_rate, confidence, n, source),
            'close_rate': RateEstimate(close_rate, confidence, n, source),
            'aov': RateEstimate(aov, confidence, n, source),  # Ticket Medio (contratti)
            'aov_cash': RateEstimate(aov_cash, confidence, n, source)  # Incasso Medio (cash)
        }

    def _get_global_rates(self, as_of_date: datetime) -> dict:
        """Calcola tassi globali sui dati maturi."""
        if self.global_rates:
            return self.global_rates

        # Usa ultimi 60 giorni maturi
        end = as_of_date - timedelta(days=self.config['maturity_buffer_days'])
        start = end - timedelta(days=60)

        filtered = []
        for call in self.calls:
            fields = call.get('fields', {})
            dc = fields.get('_data_creazione')
            dcall = fields.get('_data_call')

            if dc and dcall and start <= dc <= end:
                filtered.append(call)

        n = len(filtered)
        if n == 0:
            return {'show_rate': 0.70, 'close_rate': 0.20, 'aov': 2000, 'aov_cash': 1500}

        no_shows = sum(1 for c in filtered
                      if c.get('fields', {}).get('Conta No Show', 0) > 0)
        show_ups = n - no_shows
        closures = sum(1 for c in filtered
                      if c.get('fields', {}).get('Conta Chiusure', 0) > 0)

        # Calcola sia Revenue che Cash Collected
        revenues = [c.get('fields', {}).get('Revenue', 0) or 0
                   for c in filtered
                   if c.get('fields', {}).get('Conta Chiusure', 0) > 0]
        cash_collected = [c.get('fields', {}).get('Cash Collected', 0) or 0
                         for c in filtered
                         if c.get('fields', {}).get('Conta Chiusure', 0) > 0]

        self.global_rates = {
            'show_rate': show_ups / n if n > 0 else 0.70,
            'close_rate': closures / show_ups if show_ups > 0 else 0.20,
            'aov': np.mean(revenues) if revenues else 2000,
            'aov_cash': np.mean(cash_collected) if cash_collected else 1500
        }

        return self.global_rates

    def _get_fallback_rates(self) -> Dict[str, RateEstimate]:
        """Tassi di fallback quando non ci sono dati."""
        return {
            'show_rate': RateEstimate(0.70, 'low', 0, 'fallback'),
            'close_rate': RateEstimate(0.20, 'low', 0, 'fallback'),
            'aov': RateEstimate(2000, 'low', 0, 'fallback'),
            'aov_cash': RateEstimate(1500, 'low', 0, 'fallback')
        }

    # =========================================================================
    # TREND DETECTION
    # =========================================================================

    def detect_trend(self, metric: str, weeks: int = 8) -> dict:
        """
        Rileva trend settimanale per una metrica.

        Args:
            metric: 'show_rate', 'close_rate', 'aov'
            weeks: Numero di settimane da analizzare

        Returns:
            Dict con trend analysis
        """
        today = datetime.now()
        weekly_values = []

        for w in range(weeks, 0, -1):
            week_end = today - timedelta(days=7*w + self.config['maturity_buffer_days'])
            week_start = week_end - timedelta(days=7)

            rates = self.calculate_rates_for_window(week_start, week_end)
            if metric in rates:
                weekly_values.append({
                    'week': w,
                    'start': week_start.strftime('%Y-%m-%d'),
                    'end': week_end.strftime('%Y-%m-%d'),
                    'value': rates[metric].value,
                    'sample_size': rates[metric].sample_size
                })

        if len(weekly_values) < 3:
            return {'trend': 'insufficient_data', 'values': weekly_values}

        # Calcola trend con regressione lineare
        values = [v['value'] for v in weekly_values]
        x = np.arange(len(values))

        # Coefficiente di correlazione
        if np.std(values) > 0:
            correlation = np.corrcoef(x, values)[0, 1]
        else:
            correlation = 0

        # Slope normalizzato
        mean_value = np.mean(values)
        if mean_value > 0:
            slope = np.polyfit(x, values, 1)[0]
            normalized_slope = slope / mean_value
        else:
            normalized_slope = 0

        # Determina trend
        if abs(correlation) < 0.5:
            trend = 'stable'
        elif normalized_slope < -self.config['trend_threshold']:
            trend = 'strong_negative' if normalized_slope < -0.20 else 'moderate_negative'
        elif normalized_slope > self.config['trend_threshold']:
            trend = 'moderate_positive' if normalized_slope < 0.20 else 'strong_positive'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'correlation': round(correlation, 3),
            'normalized_slope': round(normalized_slope, 3),
            'latest_value': values[-1] if values else None,
            'mean_value': round(mean_value, 4),
            'values': weekly_values
        }

    # =========================================================================
    # BACKTESTING
    # =========================================================================

    def backtest_windows(self, periods: int = None) -> Dict[int, BacktestResult]:
        """
        Esegue backtesting per determinare la finestra ottimale.

        Simula proiezioni su periodi passati e confronta con realtà.

        Args:
            periods: Numero di periodi settimanali da testare

        Returns:
            Dict con BacktestResult per ogni finestra candidata
        """
        periods = periods or self.config['backtest_periods']
        windows = self.config['window_candidates']
        results = {}

        today = datetime.now()

        for window_days in windows:
            errors = []

            for p in range(1, periods + 1):
                # Periodo da testare (settimane fa)
                period_end = today - timedelta(days=7*p + self.config['maturity_buffer_days'])
                period_start = period_end - timedelta(days=7)

                # Finestra per calcolare tassi (prima del periodo)
                rate_window_end = period_start - timedelta(days=self.config['maturity_buffer_days'])
                rate_window_start = rate_window_end - timedelta(days=window_days)

                # Calcola tassi dalla finestra
                rates = self.calculate_rates_for_window(rate_window_start, rate_window_end)

                # Ottieni dati reali del periodo
                actual = self._get_period_actual(period_start, period_end)

                if actual['calls'] == 0:
                    continue

                # Proietta
                projected_closures = actual['calls'] * rates['show_rate'].value * rates['close_rate'].value
                projected_revenue = projected_closures * rates['aov'].value

                # Calcola errore
                if actual['revenue'] > 0:
                    error = (projected_revenue - actual['revenue']) / actual['revenue']
                    errors.append(error)

            if errors:
                errors = np.array(errors)
                results[window_days] = BacktestResult(
                    window_days=window_days,
                    mape=float(np.mean(np.abs(errors))),
                    rmse=float(np.sqrt(np.mean(errors**2))),
                    bias=float(np.mean(errors)),
                    n_periods=len(errors)
                )

        return results

    def get_optimal_window(self) -> int:
        """
        Restituisce la finestra ottimale basata su backtesting.
        """
        backtest = self.backtest_windows()

        if not backtest:
            return 21  # Default

        # Scegli finestra con MAPE minore
        best = min(backtest.values(), key=lambda x: x.mape)
        return best.window_days

    def get_bias_analysis(self) -> dict:
        """
        Analisi completa del bias con test di stabilità.

        Calcola:
        - Media degli errori (bias)
        - Deviazione standard degli errori (stabilità)
        - Decisione se applicare correzione

        Returns:
            dict con bias, std, stability, correction_factor, should_apply
        """
        backtest = self.backtest_windows()

        if not backtest:
            return {
                'bias': 0,
                'std': 0,
                'stability': 'unknown',
                'correction_factor': 1.0,
                'should_apply': False,
                'reason': 'no_backtest_data'
            }

        # Prendi gli errori da tutti i periodi di backtest
        # (non solo dalla finestra ottimale)
        optimal_window = self.get_optimal_window()
        best_result = backtest.get(optimal_window)

        if not best_result:
            return {
                'bias': 0,
                'std': 0,
                'stability': 'unknown',
                'correction_factor': 1.0,
                'should_apply': False,
                'reason': 'no_optimal_window'
            }

        # Ricalcola errori individuali per calcolare std
        errors = self._get_backtest_errors(optimal_window)

        if len(errors) < 2:
            return {
                'bias': best_result.bias,
                'std': 0,
                'stability': 'insufficient_data',
                'correction_factor': 1.0,
                'should_apply': False,
                'reason': 'need_more_periods'
            }

        bias = np.mean(errors)
        std = np.std(errors)

        # Determina stabilità
        # std < 10% → stabile, 10-20% → moderato, >20% → instabile
        if std < 0.10:
            stability = 'stable'
        elif std < 0.20:
            stability = 'moderate'
        else:
            stability = 'unstable'

        # Decidi se applicare correzione
        # POLICY: Solo correzione piena se STABILE, altrimenti dati grezzi + warning
        threshold = self.config['bias_correction_threshold']

        if bias > threshold:
            if stability == 'stable':
                # Bias significativo e stabile → applica correzione piena
                correction_factor = 1.0 / (1.0 + bias)
                should_apply = True
                reason = 'stable_positive_bias'
            else:
                # Bias instabile o moderato → NO correzione, troppo rischioso
                # Mostra dati grezzi con warning
                correction_factor = 1.0
                should_apply = False
                reason = 'unstable_bias_raw_data_with_warning'
        elif bias < -threshold:
            # Sottostima → per prudenza non correggiamo al rialzo
            correction_factor = 1.0
            should_apply = False
            reason = 'negative_bias_no_upward_correction'
        else:
            # Bias sotto soglia
            correction_factor = 1.0
            should_apply = False
            reason = 'bias_below_threshold'

        return {
            'bias': float(bias),
            'std': float(std),
            'stability': stability,
            'correction_factor': correction_factor,
            'should_apply': should_apply,
            'reason': reason,
            'n_periods': len(errors),
            'errors': [round(e, 3) for e in errors]
        }

    def _get_backtest_errors(self, window_days: int) -> List[float]:
        """Ricalcola gli errori individuali per una finestra."""
        periods = self.config['backtest_periods']
        today = datetime.now()
        errors = []

        for p in range(1, periods + 1):
            period_end = today - timedelta(days=7*p + self.config['maturity_buffer_days'])
            period_start = period_end - timedelta(days=7)

            rate_window_end = period_start - timedelta(days=self.config['maturity_buffer_days'])
            rate_window_start = rate_window_end - timedelta(days=window_days)

            rates = self.calculate_rates_for_window(rate_window_start, rate_window_end)
            actual = self._get_period_actual(period_start, period_end)

            if actual['calls'] == 0 or actual['revenue'] == 0:
                continue

            projected_closures = actual['calls'] * rates['show_rate'].value * rates['close_rate'].value
            projected_revenue = projected_closures * rates['aov'].value

            error = (projected_revenue - actual['revenue']) / actual['revenue']
            errors.append(error)

        return errors

    def get_bias_correction_factor(self) -> float:
        """
        Calcola il fattore di correzione del bias dalla finestra ottimale.

        Usa il test di stabilità per decidere se applicare.

        Returns:
            float: Fattore di correzione (1.0 se nessuna correzione)
        """
        analysis = self.get_bias_analysis()
        return analysis['correction_factor']

    def _get_period_actual(self, start: datetime, end: datetime) -> dict:
        """Ottieni metriche reali per un periodo."""
        calls = 0
        closures = 0
        revenue = 0
        cash = 0

        for call in self.calls:
            fields = call.get('fields', {})
            dc = fields.get('_data_creazione')

            if dc and start <= dc <= end:
                calls += 1
                if fields.get('Conta Chiusure', 0) > 0:
                    closures += 1
                    revenue += fields.get('Revenue', 0) or 0
                    cash += fields.get('Cash Collected', 0) or 0

        return {
            'calls': calls,
            'closures': closures,
            'revenue': revenue,
            'cash': cash
        }

    # =========================================================================
    # PROJECTION
    # =========================================================================

    def project_period(
        self,
        period_start: datetime,
        period_end: datetime,
        spend: float,
        source_filter: str = None
    ) -> ProjectionResult:
        """
        Calcola proiezione ROAS per un periodo.

        Args:
            period_start: Inizio periodo (Data Creazione)
            period_end: Fine periodo (Data Creazione)
            spend: Spesa pubblicitaria del periodo
            source_filter: Filtra per fonte (opzionale)

        Returns:
            ProjectionResult con tutti i dettagli
        """
        today = datetime.now()

        # Filtra calls per Data Creazione nel periodo
        period_calls = []
        for call in self.calls:
            fields = call.get('fields', {})
            dc = fields.get('_data_creazione')

            if dc and period_start <= dc <= period_end:
                # Opzionale: filtra per source
                if source_filter:
                    source = (fields.get('UTM Fonte (source)', '') or '').lower()
                    if source_filter == 'meta' and source not in ['meta', 'facebook', 'fb']:
                        continue
                    elif source_filter == 'vuoto' and source:
                        continue

                period_calls.append(call)

        # Separa completed vs pending
        completed = []
        pending = []

        for call in period_calls:
            fields = call.get('fields', {})
            if fields.get('_data_call'):
                completed.append(call)
            else:
                pending.append(call)

        # Revenue attuale (da calls completate) - valore contratti
        revenue_actual = sum(
            c.get('fields', {}).get('Revenue', 0) or 0
            for c in completed
            if c.get('fields', {}).get('Conta Chiusure', 0) > 0
        )

        # Cash Collected attuale (da calls completate) - incasso effettivo
        cash_actual = sum(
            c.get('fields', {}).get('Cash Collected', 0) or 0
            for c in completed
            if c.get('fields', {}).get('Conta Chiusure', 0) > 0
        )

        # Calcola tassi per proiezione
        # Usa finestra ottimale basata su backtesting
        optimal_window = self.get_optimal_window()

        # Finestra per tassi (dati maturi prima del periodo)
        rate_window_end = period_start - timedelta(days=1)
        rate_window_start = rate_window_end - timedelta(days=optimal_window)

        rates = self.calculate_rates_for_window(rate_window_start, rate_window_end, source_filter)

        # Applica trend adjustment se necessario
        trend = self.detect_trend('close_rate')
        if trend['trend'] in ['strong_negative', 'moderate_negative']:
            # Applica haircut del 10% per trend negativo
            rates['close_rate'] = RateEstimate(
                rates['close_rate'].value * 0.90,
                rates['close_rate'].confidence,
                rates['close_rate'].sample_size,
                rates['close_rate'].source + '_trend_adjusted'
            )

        # Proietta revenue da pending calls (valore contratti)
        if pending:
            pending_revenue_base = (
                len(pending) *
                rates['show_rate'].value *
                rates['close_rate'].value *
                rates['aov'].value
            )
            # Proietta cash da pending calls (incasso effettivo)
            pending_cash_base = (
                len(pending) *
                rates['show_rate'].value *
                rates['close_rate'].value *
                rates['aov_cash'].value
            )
        else:
            pending_revenue_base = 0
            pending_cash_base = 0

        # === SCENARI REVENUE (profittabilità) ===
        revenue_projected_base = revenue_actual + pending_revenue_base
        revenue_projected_pessimistic = revenue_actual + pending_revenue_base * self.config['confidence_pessimistic']
        revenue_projected_optimistic = revenue_actual + pending_revenue_base * self.config['confidence_optimistic']

        # === SCENARI CASH (cash flow reale) ===
        cash_projected_base = cash_actual + pending_cash_base
        cash_projected_pessimistic = cash_actual + pending_cash_base * self.config['confidence_pessimistic']
        cash_projected_optimistic = cash_actual + pending_cash_base * self.config['confidence_optimistic']

        # ROAS Revenue (profittabilità)
        roas_actual = revenue_actual / spend if spend > 0 else 0
        roas_projected_base = revenue_projected_base / spend if spend > 0 else 0
        roas_projected_pessimistic = revenue_projected_pessimistic / spend if spend > 0 else 0
        roas_projected_optimistic = revenue_projected_optimistic / spend if spend > 0 else 0

        # ROAS Cash (cash flow reale per decisioni di scaling)
        roas_cash_actual = cash_actual / spend if spend > 0 else 0
        roas_cash_projected_base = cash_projected_base / spend if spend > 0 else 0
        roas_cash_projected_pessimistic = cash_projected_pessimistic / spend if spend > 0 else 0
        roas_cash_projected_optimistic = cash_projected_optimistic / spend if spend > 0 else 0

        # === BIAS CORRECTION ===
        # Se il backtest rileva sovrastima sistematica, correggiamo la proiezione
        bias_correction_factor = self.get_bias_correction_factor()

        # Applica correzione solo alla parte proiettata (pending)
        # Gli actual sono reali, non vanno corretti
        if bias_correction_factor < 1.0 and pending_revenue_base > 0:
            revenue_projected_corrected = revenue_actual + pending_revenue_base * bias_correction_factor
            cash_projected_corrected = cash_actual + pending_cash_base * bias_correction_factor
        else:
            revenue_projected_corrected = revenue_projected_base
            cash_projected_corrected = cash_projected_base

        roas_projected_corrected = revenue_projected_corrected / spend if spend > 0 else 0
        roas_cash_projected_corrected = cash_projected_corrected / spend if spend > 0 else 0

        # Completion rate
        total_calls = len(completed) + len(pending)
        completion_rate = len(completed) / total_calls if total_calls > 0 else 1.0

        # Reliability
        if completion_rate >= 0.90:
            reliability = 'consolidated'
        elif completion_rate >= 0.50:
            reliability = 'partial'
        else:
            reliability = 'early'

        return ProjectionResult(
            # Revenue (contratti)
            revenue_actual=revenue_actual,
            revenue_projected_base=revenue_projected_base,
            revenue_projected_pessimistic=revenue_projected_pessimistic,
            revenue_projected_optimistic=revenue_projected_optimistic,
            revenue_projected_corrected=revenue_projected_corrected,
            # Cash (incasso)
            cash_actual=cash_actual,
            cash_projected_base=cash_projected_base,
            cash_projected_pessimistic=cash_projected_pessimistic,
            cash_projected_optimistic=cash_projected_optimistic,
            cash_projected_corrected=cash_projected_corrected,
            # Bias
            bias_correction_factor=bias_correction_factor,
            # Calls
            calls_completed=len(completed),
            calls_pending=len(pending),
            completion_rate=completion_rate,
            # ROAS Revenue
            roas_actual=roas_actual,
            roas_projected_base=roas_projected_base,
            roas_projected_pessimistic=roas_projected_pessimistic,
            roas_projected_optimistic=roas_projected_optimistic,
            roas_projected_corrected=roas_projected_corrected,
            # ROAS Cash
            roas_cash_actual=roas_cash_actual,
            roas_cash_projected_base=roas_cash_projected_base,
            roas_cash_projected_pessimistic=roas_cash_projected_pessimistic,
            roas_cash_projected_optimistic=roas_cash_projected_optimistic,
            roas_cash_projected_corrected=roas_cash_projected_corrected,
            # Meta
            rates_used=rates,
            reliability=reliability
        )

    # =========================================================================
    # HIERARCHICAL ANALYSIS (Campaign > AdSet > Ad)
    # =========================================================================

    def analyze_by_hierarchy(
        self,
        period_start: datetime,
        period_end: datetime,
        meta_data: dict,
        level: str = 'adset'
    ) -> List[dict]:
        """
        Analisi gerarchica con Bayesian Shrinkage.

        Args:
            period_start: Inizio periodo
            period_end: Fine periodo
            meta_data: Dati Meta Ads
            level: 'campaign', 'adset', 'ad'

        Returns:
            Lista di risultati per entità
        """
        results = []

        # Prepara mapping UTM -> entità Meta
        if level == 'campaign':
            entities = meta_data.get('campaigns', [])
            name_field = 'Campaign name'
            utm_field = 'UTM Campagna (campaign)'
        elif level == 'adset':
            entities = meta_data.get('adsets', [])
            name_field = 'Ad set name'
            utm_field = 'UTM Adset (medium)'
        else:
            entities = meta_data.get('ads', [])
            name_field = 'Ad name'
            utm_field = None  # Non abbiamo UTM per singoli ads

        # Calcola tassi globali per fallback
        global_rates = self._get_global_rates(period_end)

        for entity in entities:
            name = entity.get(name_field, '')
            spend = float(entity.get('Amount spent (EUR)', 0))

            if not name or spend <= 0:
                continue

            # Trova calls per questa entità
            entity_calls = []
            for call in self.calls:
                fields = call.get('fields', {})
                dc = fields.get('_data_creazione')

                if not dc or not (period_start <= dc <= period_end):
                    continue

                # Match by UTM
                if utm_field:
                    call_utm = fields.get(utm_field, '') or ''
                    # Fuzzy match (il nome AdSet può essere troncato negli UTM)
                    if name.lower()[:20] in call_utm.lower() or call_utm.lower()[:20] in name.lower():
                        entity_calls.append(call)

            # Calcola metriche
            n = len(entity_calls)

            # Completed vs pending
            completed = [c for c in entity_calls if c.get('fields', {}).get('_data_call')]
            pending = [c for c in entity_calls if not c.get('fields', {}).get('_data_call')]

            # Revenue attuale (contratti)
            revenue_actual = sum(
                c.get('fields', {}).get('Revenue', 0) or 0
                for c in completed
                if c.get('fields', {}).get('Conta Chiusure', 0) > 0
            )

            # Cash Collected attuale (incasso)
            cash_actual = sum(
                c.get('fields', {}).get('Cash Collected', 0) or 0
                for c in completed
                if c.get('fields', {}).get('Conta Chiusure', 0) > 0
            )

            # Calcola tassi con shrinkage
            if n >= self.config['min_sample_size']:
                # Usa tassi specifici
                no_shows = sum(1 for c in completed if c.get('fields', {}).get('Conta No Show', 0) > 0)
                show_ups = len(completed) - no_shows
                closures = sum(1 for c in completed if c.get('fields', {}).get('Conta Chiusure', 0) > 0)

                show_rate = show_ups / len(completed) if completed else global_rates['show_rate']
                close_rate = closures / show_ups if show_ups > 0 else global_rates['close_rate']

                revenues = [c.get('fields', {}).get('Revenue', 0) or 0
                           for c in completed if c.get('fields', {}).get('Conta Chiusure', 0) > 0]
                cash_values = [c.get('fields', {}).get('Cash Collected', 0) or 0
                              for c in completed if c.get('fields', {}).get('Conta Chiusure', 0) > 0]
                aov = np.mean(revenues) if revenues else global_rates['aov']
                aov_cash = np.mean(cash_values) if cash_values else global_rates['aov_cash']

                rate_source = 'specific'
                confidence = 'high'

            elif n >= 10:
                # Blend con globale (Bayesian shrinkage)
                no_shows = sum(1 for c in completed if c.get('fields', {}).get('Conta No Show', 0) > 0)
                show_ups = len(completed) - no_shows
                closures = sum(1 for c in completed if c.get('fields', {}).get('Conta Chiusure', 0) > 0)

                specific_show = show_ups / len(completed) if completed else 0
                specific_close = closures / show_ups if show_ups > 0 else 0

                # Blend weight based on sample size
                weight = n / self.config['shrinkage_threshold']

                show_rate = specific_show * weight + global_rates['show_rate'] * (1 - weight)
                close_rate = specific_close * weight + global_rates['close_rate'] * (1 - weight)
                aov = global_rates['aov']  # Ticket difficile da stimare con pochi dati
                aov_cash = global_rates['aov_cash']

                rate_source = 'blended'
                confidence = 'medium'

            else:
                # Usa globale
                show_rate = global_rates['show_rate']
                close_rate = global_rates['close_rate']
                aov = global_rates['aov']
                aov_cash = global_rates['aov_cash']

                rate_source = 'global'
                confidence = 'low'

            # Proiezione Revenue
            pending_revenue = len(pending) * show_rate * close_rate * aov
            revenue_projected = revenue_actual + pending_revenue

            # Proiezione Cash
            pending_cash = len(pending) * show_rate * close_rate * aov_cash
            cash_projected = cash_actual + pending_cash

            # ROAS Revenue (profittabilità)
            roas_actual = revenue_actual / spend if spend > 0 else 0
            roas_projected = revenue_projected / spend if spend > 0 else 0

            # ROAS Cash (cash flow)
            roas_cash_actual = cash_actual / spend if spend > 0 else 0
            roas_cash_projected = cash_projected / spend if spend > 0 else 0

            completion_rate = len(completed) / n if n > 0 else 1.0

            results.append({
                'name': name,
                'campaign': entity.get('Campaign name', ''),
                'spend': round(spend, 2),
                'calls_total': n,
                'calls_completed': len(completed),
                'calls_pending': len(pending),
                'completion_rate': round(completion_rate * 100, 1),
                'revenue_actual': round(revenue_actual, 2),
                'revenue_projected': round(revenue_projected, 2),
                'cash_actual': round(cash_actual, 2),
                'cash_projected': round(cash_projected, 2),
                'roas_actual': round(roas_actual, 2),
                'roas_projected': round(roas_projected, 2),
                'roas_cash_actual': round(roas_cash_actual, 2),
                'roas_cash_projected': round(roas_cash_projected, 2),
                'rates': {
                    'show_rate': round(show_rate, 3),
                    'close_rate': round(close_rate, 3),
                    'aov': round(aov, 2),
                    'aov_cash': round(aov_cash, 2),
                    'source': rate_source
                },
                'confidence': confidence
            })

        # Ordina per spesa
        results.sort(key=lambda x: x['spend'], reverse=True)

        return results

    # =========================================================================
    # SUMMARY REPORT
    # =========================================================================

    def generate_summary(
        self,
        period_start: datetime,
        period_end: datetime,
        spend: float,
        meta_data: dict = None
    ) -> dict:
        """
        Genera report completo con tutte le analisi.

        Returns:
            Dict con summary completo
        """
        summary = {
            'period': {
                'start': period_start.strftime('%Y-%m-%d'),
                'end': period_end.strftime('%Y-%m-%d'),
                'days': (period_end - period_start).days + 1
            },
            'spend': round(spend, 2),
            'lag_stats': self.lag_stats,
            'optimal_window': self.get_optimal_window(),
        }

        # Proiezione principale
        projection = self.project_period(period_start, period_end, spend)
        summary['projection'] = projection.to_dict()

        # Proiezione per fonte Meta
        projection_meta = self.project_period(period_start, period_end, spend, 'meta')
        summary['projection_meta'] = projection_meta.to_dict()

        # Backtest results
        backtest = self.backtest_windows()
        summary['backtest'] = {k: v.to_dict() for k, v in backtest.items()}

        # Bias analysis con test di stabilità
        summary['bias_analysis'] = self.get_bias_analysis()

        # Trend analysis
        summary['trends'] = {
            'show_rate': self.detect_trend('show_rate'),
            'close_rate': self.detect_trend('close_rate'),
            'aov': self.detect_trend('aov')
        }

        # Hierarchical analysis (se meta_data fornito)
        if meta_data:
            summary['by_adset'] = self.analyze_by_hierarchy(
                period_start, period_end, meta_data, 'adset'
            )[:15]  # Top 15

        return summary


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def load_data(data_dir: str) -> Tuple[List[dict], List[dict]]:
    """Carica dati da file JSON."""
    data_path = Path(data_dir)

    # Calls
    calls_file = data_path / 'calls_full.json'
    if calls_file.exists():
        with open(calls_file) as f:
            calls = json.load(f).get('records', [])
    else:
        calls = []

    # Candidature
    cand_file = data_path / 'candidature_with_source.json'
    if cand_file.exists():
        with open(cand_file) as f:
            candidature = json.load(f).get('records', [])
    else:
        candidature = []

    return calls, candidature


def load_meta_data(meta_dir: str, period: str) -> dict:
    """Carica dati Meta Ads da CSV."""
    period_path = Path(meta_dir) / period
    meta_data = {}

    # Campaigns
    campaigns_file = period_path / 'campaigns.csv'
    if campaigns_file.exists():
        with open(campaigns_file, encoding='utf-8') as f:
            meta_data['campaigns'] = list(csv.DictReader(f))

    # AdSets
    adsets_file = period_path / 'adsets.csv'
    if adsets_file.exists():
        with open(adsets_file, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
            # Prima riga senza nome è il totale
            meta_data['adsets'] = [r for r in rows if r.get('Ad set name')]
            for r in rows:
                if not r.get('Ad set name'):
                    meta_data['totals'] = {
                        'spend': float(r.get('Amount spent (EUR)', 0)),
                        'date_start': r.get('Reporting starts'),
                        'date_end': r.get('Reporting ends')
                    }

    # Ads
    ads_file = period_path / 'ads.csv'
    if ads_file.exists():
        with open(ads_file, encoding='utf-8') as f:
            meta_data['ads'] = [r for r in csv.DictReader(f) if r.get('Ad name')]

    return meta_data


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='LDP Projection Engine')
    parser.add_argument('period', choices=['1w', '2w', '28d'], help='Period to analyze')
    parser.add_argument('--fixed-costs', type=float, default=25000, help='Monthly fixed costs (default: 25000)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--backtest', action='store_true', help='Run backtesting only')
    parser.add_argument('--trend', action='store_true', help='Show trend analysis only')

    args = parser.parse_args()

    # Paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    meta_dir = data_dir / 'meta_exports'

    # Load data
    print("📊 Caricamento dati...")
    calls, candidature = load_data(data_dir)
    meta_data = load_meta_data(meta_dir, args.period)

    print(f"   Calls: {len(calls)}")
    print(f"   Candidature: {len(candidature)}")

    # Initialize engine
    engine = ProjectionEngine(calls, candidature)

    if args.backtest:
        print("\n🔬 Backtesting finestre...")
        backtest = engine.backtest_windows()
        for window, result in sorted(backtest.items()):
            print(f"\n   Finestra {window} giorni:")
            print(f"   MAPE: {result.mape*100:.1f}%")
            print(f"   RMSE: {result.rmse:.0f}")
            print(f"   Bias: {result.bias*100:+.1f}%")

        optimal = engine.get_optimal_window()
        print(f"\n✅ Finestra ottimale: {optimal} giorni")

    elif args.trend:
        print("\n📈 Analisi Trend...")
        for metric in ['show_rate', 'close_rate', 'aov']:
            trend = engine.detect_trend(metric)
            print(f"\n   {metric}: {trend['trend']}")
            print(f"   Correlazione: {trend['correlation']}")
            print(f"   Slope normalizzato: {trend['normalized_slope']}")

    else:
        # Full analysis
        totals = meta_data.get('totals', {})
        spend = totals.get('spend', 0)
        date_start = datetime.strptime(totals.get('date_start', '2024-01-01'), '%Y-%m-%d')
        date_end = datetime.strptime(totals.get('date_end', '2024-01-07'), '%Y-%m-%d')

        print(f"\n📅 Periodo: {date_start.date()} → {date_end.date()}")
        print(f"💰 Spesa: €{spend:,.2f}")

        summary = engine.generate_summary(date_start, date_end, spend, meta_data)

        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            proj = summary['projection']

            # =====================================================
            # OUTPUT BUSINESS-ORIENTED con Target ROAS Dinamico
            # =====================================================

            # Parametri
            MONTHLY_FIXED_COSTS = args.fixed_costs
            MIN_ROAS_THRESHOLD = 2.2  # Soglia minima di sicurezza

            # Calcola giorni e quota costi fissi
            days_in_period = summary['period']['days']
            ad_spend = summary['spend']
            fixed_costs_period = (MONTHLY_FIXED_COSTS / 30) * days_in_period
            total_costs = fixed_costs_period + ad_spend

            # TARGET ROAS DINAMICO (Break-Even Point)
            target_roas = total_costs / ad_spend if ad_spend > 0 else 999

            # ROAS da usare (già scelto dalla logica pessimistica/corretta)
            bias_info = summary.get('bias_analysis', {})
            stability = bias_info.get('stability', 'unknown')
            backtest = summary.get('backtest', {})
            optimal_bt = backtest.get(summary['optimal_window'], {})
            mape = optimal_bt.get('mape', 0)

            # Calcola sia Revenue che Cash ROAS
            if proj['bias_correction']['applied']:
                # Revenue (profittabilità)
                roas_rev_atteso = proj['roas']['projected_corrected']
                revenue_attesa = proj['revenue']['projected_corrected']
                # Cash (cash flow reale)
                roas_cash_atteso = proj['roas_cash']['projected_corrected']
                cash_atteso = proj['cash']['projected_corrected']
            elif stability in ['unstable', 'moderate'] or mape > 30:
                roas_rev_atteso = proj['roas']['projected_pessimistic']
                revenue_attesa = proj['revenue']['projected_pessimistic']
                roas_cash_atteso = proj['roas_cash']['projected_pessimistic']
                cash_atteso = proj['cash']['projected_pessimistic']
            else:
                roas_rev_atteso = proj['roas']['projected_base']
                revenue_attesa = proj['revenue']['projected_base']
                roas_cash_atteso = proj['roas_cash']['projected_base']
                cash_atteso = proj['cash']['projected_base']

            # Mantieni roas_atteso per compatibilità (usa Cash per decisioni scaling)
            roas_atteso = roas_cash_atteso

            # Calcola cash flow (su cash reale, non revenue)
            cash_flow = cash_atteso - total_costs

            # Determina STATUS e AZIONE
            tolerance = 0.10  # ±10%

            if roas_atteso >= target_roas * (1 + tolerance):
                # PROFIT: Sopra target +10%
                status = "🟢 PROFITABLE"
                azione = "SCALARE"
                messaggio = "Cash flow positivo. I lead acquisiti sono gratis + margine."
                colore = "verde"
            elif roas_atteso >= MIN_ROAS_THRESHOLD and roas_atteso < target_roas:
                # INVESTMENT: Tra soglia minima e target
                status = "🟡 INVESTMENT MODE"
                azione = "MONITORARE"
                investimento = total_costs - revenue_attesa
                messaggio = f"Stai investendo €{investimento:,.0f} di cassa per acquisire lead. OK se previsto."
                colore = "giallo"
            elif roas_atteso >= target_roas * (1 - tolerance) and roas_atteso < target_roas * (1 + tolerance):
                # NEAR TARGET: Vicino al break-even
                status = "🟡 BREAK-EVEN"
                azione = "ATTENDERE"
                messaggio = "Vicino al pareggio. Attendi dati più consolidati prima di decidere."
                colore = "giallo"
            else:
                # DANGER: Sotto soglia minima
                status = "🔴 CASH BURN"
                azione = "TAGLIARE"
                perdita = total_costs - revenue_attesa
                messaggio = f"Stai perdendo €{perdita:,.0f}. Costo acquisizione lead insostenibile."
                colore = "rosso"

            # Giorni alla certezza
            lag_p90 = summary['lag_stats'].get('p90', 7)
            days_since_end = (datetime.now() - date_end).days
            days_to_certainty = max(0, lag_p90 - days_since_end)

            completion = proj['calls']['completion_rate']

            # ============ OUTPUT ============

            print(f"\n{'='*60}")
            print(f"  REPORT LDP - {args.period.upper()}")
            print(f"  {summary['period']['start']} → {summary['period']['end']}")
            print(f"{'='*60}")

            # --- STRUTTURA COSTI ---
            print(f"\n  ─── STRUTTURA COSTI ({days_in_period} giorni) ───")
            print(f"  • Spesa Ads:         €{ad_spend:>10,.0f}")
            print(f"  • Costi Fissi (est): €{fixed_costs_period:>10,.0f}  (quota team)")
            print(f"  • TOTALE COSTI:      €{total_costs:>10,.0f}")
            print(f"")
            print(f"  🎯 TARGET ROAS (Break-Even): {target_roas:.2f}x")
            print(f"     Sotto questo valore il cash flow è negativo")

            # --- RISULTATO DOPPIO: Revenue vs Cash ---
            print(f"\n  ─── RISULTATO ───")
            print(f"  {'Metrica':<20} {'Valore':>12} {'ROAS':>10}")
            print(f"  {'-'*20} {'-'*12} {'-'*10}")
            print(f"  {'Revenue (contratti)':<20} €{revenue_attesa:>10,.0f} {roas_rev_atteso:>9.2f}x")
            print(f"  {'Cash (incassato)':<20} €{cash_atteso:>10,.0f} {roas_cash_atteso:>9.2f}x")
            print(f"  {'-'*20} {'-'*12} {'-'*10}")
            print(f"  {'Cash Flow Reale':<20} €{cash_flow:>+10,.0f}")

            # Interpretazione differenza Revenue vs Cash
            if roas_rev_atteso > 0:
                cash_ratio = roas_cash_atteso / roas_rev_atteso
            else:
                cash_ratio = 1.0

            if cash_ratio >= 0.85:
                cash_interpretation = "✅ Incasso allineato ai contratti"
            elif cash_ratio >= 0.60:
                cash_interpretation = "⚠️ Rateizzazione alta - cash arriverà"
            else:
                cash_interpretation = "🔴 Gap significativo - verifica payment plan"
            print(f"\n  {cash_interpretation}")

            # --- BOX DECISIONE ---
            print(f"\n  ┌──────────────────────────────────────────────────┐")
            print(f"  │  {status:<44} │")
            print(f"  │                                                  │")
            print(f"  │  AZIONE: {azione:<38} │")
            print(f"  └──────────────────────────────────────────────────┘")
            print(f"\n  {messaggio}")

            # --- AFFIDABILITÀ ---
            if completion < 90:
                print(f"\n  ⏳ Dato al {completion:.0f}% - Mancano ~{days_to_certainty} giorni per consolidamento")
            else:
                print(f"\n  ✅ Dato consolidato ({completion:.0f}%)")

            # --- WARNING ---
            warnings = []
            for metric, trend in summary['trends'].items():
                if trend['trend'] in ['strong_negative', 'moderate_negative']:
                    warnings.append(f"{metric} in calo")
            if mape > 30:
                warnings.append(f"Modello instabile (±{mape:.0f}%)")
            if warnings:
                print(f"\n  ⚠️  {', '.join(warnings)}")

            # --- SCALING SENSITIVITY MATRIX ---
            print(f"\n{'='*60}")
            print(f"  📊 SCALING SENSITIVITY MATRIX")
            print(f"  Costi Fissi: €{MONTHLY_FIXED_COSTS:,.0f}/mese")
            print(f"{'='*60}")

            daily_spend = ad_spend / days_in_period

            print(f"\n  {'Incremento':<12} {'Budget/Day':>12} {'Target ROAS':>14} {'Variazione':>12}")
            print(f"  {'-'*12} {'-'*12} {'-'*14} {'-'*12}")

            base_target = target_roas

            # Genera step dal -20% al +100%
            steps = [-0.20, -0.10, 0, 0.10, 0.20, 0.30, 0.50, 0.75, 1.0]

            for step in steps:
                new_daily = daily_spend * (1 + step)
                new_monthly = new_daily * 30
                new_total = new_monthly + MONTHLY_FIXED_COSTS
                new_target = new_total / new_monthly if new_monthly > 0 else 0
                delta = new_target - base_target

                if step == 0:
                    label = "► ATTUALE"
                    delta_str = "-"
                elif step > 0:
                    label = f"+{step*100:.0f}%"
                    delta_str = f"📉 {delta:+.2f}"
                else:
                    label = f"{step*100:.0f}%"
                    delta_str = f"📈 {delta:+.2f}"

                print(f"  {label:<12} €{new_daily:>10,.0f} {new_target:>13.2f}x {delta_str:>12}")

            print(f"\n  💡 Se aumenti il budget, il Target scende (economie di scala).")
            print(f"     Finché ROAS Reale > Target, sei in profitto.")

            # ============================================================
            # DUAL-SCENARIO SCALING ANALYSIS (Sunny Day vs Rainy Day)
            # ============================================================
            # Gemini's insight: Use 28d for cash flow, 7-14d for decisions

            # Try to load alternative period data for comparison
            alt_periods = {'1w': None, '2w': None, '28d': None}
            current_roas = roas_atteso

            for p in ['1w', '2w', '28d']:
                if p == args.period:
                    alt_periods[p] = {'roas': roas_atteso, 'spend': ad_spend, 'is_current': True}
                    continue
                try:
                    alt_meta = load_meta_data(meta_dir, p)
                    if 'totals' in alt_meta:
                        alt_totals = alt_meta['totals']
                        alt_spend = alt_totals.get('spend', 0)
                        alt_start = datetime.strptime(alt_totals.get('date_start', '2024-01-01'), '%Y-%m-%d')
                        alt_end = datetime.strptime(alt_totals.get('date_end', '2024-01-07'), '%Y-%m-%d')

                        # Quick ROAS calculation for this period
                        alt_summary = engine.generate_summary(alt_start, alt_end, alt_spend, alt_meta)
                        alt_proj = alt_summary['projection']

                        # Get ROAS (pessimistic if unstable)
                        alt_bias = alt_summary.get('bias_analysis', {})
                        alt_bt = alt_summary.get('backtest', {})
                        alt_opt = alt_bt.get(alt_summary['optimal_window'], {})
                        alt_mape = alt_opt.get('mape', 0)

                        if alt_proj['bias_correction']['applied']:
                            alt_roas = alt_proj['roas']['projected_corrected']
                        elif alt_bias.get('stability') in ['unstable', 'moderate'] or alt_mape > 30:
                            alt_roas = alt_proj['roas']['projected_pessimistic']
                        else:
                            alt_roas = alt_proj['roas']['projected_base']

                        alt_periods[p] = {'roas': alt_roas, 'spend': alt_spend, 'is_current': False}
                except:
                    pass

            # Determine Sunny Day (longer period) and Rainy Day (shorter period)
            sunny_roas = None
            rainy_roas = None
            sunny_label = ""
            rainy_label = ""

            # Priority: 28d for BEST CASE, 2w for CURRENT REALITY
            # (1w is too volatile, 2w is the sweet spot: recent + stable)
            if alt_periods['28d']:
                sunny_roas = alt_periods['28d']['roas']
                sunny_label = "28d"

            # Prefer 2w over 1w for stability
            if alt_periods['2w']:
                rainy_roas = alt_periods['2w']['roas']
                rainy_label = "2w"
            elif alt_periods['1w']:
                rainy_roas = alt_periods['1w']['roas']
                rainy_label = "1w"

            # If we don't have both, use current for both
            if not sunny_roas:
                sunny_roas = roas_atteso
                sunny_label = args.period
            if not rainy_roas:
                rainy_roas = roas_atteso
                rainy_label = args.period

            # Show comparison only if we have different periods
            if sunny_label != rainy_label:
                print(f"\n{'='*60}")
                print(f"  ⚡ SCALING STRESS TEST")
                print(f"  BEST CASE vs CURRENT REALITY")
                print(f"{'='*60}")

                print(f"\n  📌 NOTA: Questi sono ROAS PROIETTATI (includono call future stimate)")
                print(f"     Non sono dati 'incompleti' - lo script ha già calcolato le chiusure attese.")

                print(f"\n  ROAS PROIETTATO di riferimento:")
                print(f"  • BEST CASE ({sunny_label}):       {sunny_roas:.2f}x  (se torniamo alla media)")
                print(f"  • CURRENT REALITY ({rainy_label}): {rainy_roas:.2f}x  (trend ultime 2 settimane)")

                print(f"\n  {'Budget':<12} │ {'Target':>8} │ {'BEST CASE':>20} │ {'CURRENT':>20}")
                print(f"  {'-'*12} │ {'-'*8} │ {'-'*20} │ {'-'*20}")

                scaling_steps = [
                    (0, "ATTUALE"),
                    (0.30, "+30%"),
                    (0.50, "+50%"),
                    (1.0, "+100%"),
                    (2.0, "+200%"),
                ]

                results_sunny = []
                results_rainy = []

                for mult, label in scaling_steps:
                    new_spend_month = (ad_spend / days_in_period * 30) * (1 + mult)
                    new_total = new_spend_month + MONTHLY_FIXED_COSTS
                    new_target = new_total / new_spend_month if new_spend_month > 0 else 999

                    # ROAS degradation factors (realistic scaling effects)
                    if mult <= 0.3:
                        degrade = 0.95  # 5% degradation
                    elif mult <= 0.5:
                        degrade = 0.90  # 10% degradation
                    elif mult <= 1.0:
                        degrade = 0.85  # 15% degradation
                    else:
                        degrade = 0.75  # 25% degradation at 3x

                    sunny_scaled = sunny_roas * degrade
                    rainy_scaled = rainy_roas * degrade

                    sunny_ok = "🟢" if sunny_scaled >= new_target else ("🟡" if sunny_scaled >= 1.5 else "🔴")
                    rainy_ok = "🟢" if rainy_scaled >= new_target else ("🟡" if rainy_scaled >= 1.5 else "🔴")

                    results_sunny.append((mult, sunny_scaled, new_target, sunny_scaled >= new_target))
                    results_rainy.append((mult, rainy_scaled, new_target, rainy_scaled >= new_target))

                    sunny_str = f"{sunny_scaled:.2f}x {sunny_ok}"
                    rainy_str = f"{rainy_scaled:.2f}x {rainy_ok}"

                    print(f"  {label:<12} │ {new_target:>7.2f}x │ {sunny_str:>20} │ {rainy_str:>20}")

                # Find max safe scaling
                max_safe_sunny = 0
                max_safe_rainy = 0
                for mult, roas, target, ok in results_sunny:
                    if ok:
                        max_safe_sunny = mult
                for mult, roas, target, ok in results_rainy:
                    if ok:
                        max_safe_rainy = mult

                print(f"\n  ─── RACCOMANDAZIONE ───")

                # Decision logic based on Gemini's advice
                trend_deteriorating = rainy_roas < sunny_roas * 0.85  # >15% drop from avg

                if trend_deteriorating:
                    print(f"\n  ⚠️  TREND IN DETERIORAMENTO RILEVATO")
                    print(f"     Il ROAS recente ({rainy_roas:.2f}x) è {((1 - rainy_roas/sunny_roas)*100):.0f}% sotto la media ({sunny_roas:.2f}x)")
                    print(f"")
                    print(f"  ❌ NON SCALARE ORA")
                    print(f"     Se scali oggi, stai scalando il {rainy_roas:.2f}x, non il {sunny_roas:.2f}x!")
                    print(f"")
                    print(f"  ✅ AZIONI IMMEDIATE:")
                    print(f"     1. FREEZE budget attuale")
                    print(f"     2. DIAGNOSTICA: trova il problema (CPL? Show Rate? Close Rate?)")
                    print(f"     3. OBIETTIVO: riporta ROAS a ~{sunny_roas * 0.9:.1f}x prima di scalare")
                    print(f"")
                    if max_safe_rainy > 0:
                        print(f"  📊 Quando torni a {sunny_roas * 0.9:.1f}x puoi scalare fino a +{max_safe_rainy*100:.0f}%")
                    else:
                        print(f"  📊 Col ROAS attuale ({rainy_roas:.2f}x) lo scaling è rischioso")
                else:
                    if max_safe_rainy >= 0.5:
                        print(f"\n  🟢 VIA LIBERA ALLO SCALING")
                        print(f"     Anche nello scenario pessimistico, hai margine fino a +{max_safe_rainy*100:.0f}%")
                        print(f"")
                        print(f"  STRATEGIA CONSIGLIATA:")
                        print(f"     Incrementi graduali +20-30% ogni 2 settimane")
                        print(f"     Monitora: se ROAS scende sotto {sunny_roas * 0.7:.1f}x → fermati")
                    elif max_safe_rainy >= 0.3:
                        print(f"\n  🟡 SCALING MODERATO POSSIBILE")
                        print(f"     Puoi provare +30% ma monitora strettamente")
                        print(f"     Soglia di stop: ROAS sotto {rainy_roas * 0.85:.1f}x")
                    else:
                        print(f"\n  🔴 SCALING SCONSIGLIATO")
                        print(f"     Il margine è troppo sottile. Prima ottimizza le ads.")

                # ============================================================
                # DIAGNOSTICA FUNNEL COMPLETO
                # VSL → VideoAsk → VSL2 → Calendly → Triage → Sales
                # ============================================================
                if trend_deteriorating:
                    print(f"\n{'='*60}")
                    print(f"  🕵️  DIAGNOSTICA: DOVE SI BLOCCA IL FUNNEL?")
                    print(f"{'='*60}")

                    # Calculate metrics for both periods
                    def calc_funnel_metrics(period_data, spend, all_calls, all_cands):
                        """Calculate full funnel metrics for a period."""
                        if not period_data or spend <= 0:
                            return None

                        try:
                            p_start = datetime.strptime(period_data.get('date_start', '2024-01-01'), '%Y-%m-%d')
                            p_end = datetime.strptime(period_data.get('date_end', '2024-01-07'), '%Y-%m-%d')
                        except:
                            return None

                        # 1. Candidature (VideoAsk completed)
                        n_cand = 0
                        for cand in all_cands:
                            fields = cand.get('fields', {})
                            date_str = fields.get('Data Creazione', '')
                            if not date_str:
                                continue
                            try:
                                if 'T' in date_str:
                                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                else:
                                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                                if p_start <= dt <= p_end + timedelta(days=1):
                                    n_cand += 1
                            except:
                                continue

                        # 2. Calls & Outcomes
                        # IMPORTANTE: Usa Data Creazione (quando è stata prenotata la call)
                        # NON Data Call (quando avviene la call)
                        # Questo mantiene la coerenza con la cohort analysis
                        n_calls_booked = 0
                        n_show = 0
                        n_close = 0
                        n_scartati = 0  # Disqualified in Triage

                        for call in all_calls:
                            fields = call.get('fields', {})
                            # USA Data Creazione per cohort analysis
                            date_str = fields.get('Data Creazione', '')
                            if not date_str:
                                continue
                            try:
                                if 'T' in date_str:
                                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                else:
                                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                                if p_start <= dt <= p_end + timedelta(days=1):
                                    n_calls_booked += 1
                                    status = fields.get('Stato', '')
                                    no_show_flag = fields.get('Conta No Show', 0)
                                    close_flag = fields.get('Conta Chiusure', 0)

                                    # === DEFINIZIONI CORRETTE (da export completo Airtable) ===
                                    #
                                    # STATI POSSIBILI:
                                    # - No Show: non si è presentato alla call
                                    # - Scartato: disqualificato (dal setter o venditore)
                                    # - Sconosciuto: deve ancora fare la call (pending)
                                    # - Riprogrammare: call spostata (pending)
                                    # - Unclosable: si è presentato, non ha comprato
                                    # - Chiuso: si è presentato, ha comprato
                                    # - In Attesa: si è presentato, sta pensando
                                    # - BIE: si è presentato, attesa bonifico
                                    #
                                    # PRIORITÀ: Venditore > Setter
                                    # Se venditore segna No Show, prevale su Scartato del setter

                                    # Scartati = Stato = 'Scartato' (e NON No Show)
                                    if status == 'Scartato' and no_show_flag == 0:
                                        n_scartati += 1

                                    # Show Up = chi si presenta alla SALES CALL
                                    # DEFINIZIONE INCLUSIVA: solo stati che indicano presenza
                                    SHOW_UP_STATI = ['Unclosable', 'Chiuso', 'In Attesa', 'BIE']
                                    if status in SHOW_UP_STATI:
                                        n_show += 1

                                    if close_flag > 0:
                                        n_close += 1
                            except:
                                continue

                        if n_cand == 0 or n_calls_booked == 0:
                            return None

                        # Triage Pass = qualified leads / total calls booked
                        n_qualified = n_calls_booked - n_scartati
                        triage_pass = n_qualified / n_calls_booked if n_calls_booked > 0 else 0

                        # Close Rate = closes / qualified (not scartati)
                        close_rate = n_close / n_qualified if n_qualified > 0 else 0

                        # Calculate AOV (Average Order Value) from closes
                        # Calcola sia Revenue (contratti) che Cash Collected (incasso)
                        total_revenue = 0
                        total_cash = 0
                        for call in all_calls:
                            fields = call.get('fields', {})
                            date_str = fields.get('Data Creazione', '')
                            if not date_str:
                                continue
                            try:
                                if 'T' in date_str:
                                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                else:
                                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                                if p_start <= dt <= p_end + timedelta(days=1):
                                    if fields.get('Conta Chiusure', 0) > 0:
                                        total_revenue += fields.get('Revenue', 0) or 0
                                        total_cash += fields.get('Cash Collected', 0) or 0
                            except:
                                continue
                        aov = total_revenue / n_close if n_close > 0 else 0
                        aov_cash = total_cash / n_close if n_close > 0 else 0

                        # Calculate Time-to-Call LAG (Data Creazione → Data Call)
                        lag_days = []
                        for call in all_calls:
                            fields = call.get('fields', {})
                            create_str = fields.get('Data Creazione', '')
                            call_str = fields.get('Data Call', '')
                            if not create_str or not call_str:
                                continue
                            try:
                                if 'T' in create_str:
                                    dt_create = datetime.fromisoformat(create_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                else:
                                    dt_create = datetime.strptime(create_str, '%Y-%m-%d')
                                if 'T' in call_str:
                                    dt_call = datetime.fromisoformat(call_str.replace('Z', '+00:00')).replace(tzinfo=None)
                                else:
                                    dt_call = datetime.strptime(call_str, '%Y-%m-%d')

                                # Only for calls created in this period
                                if p_start <= dt_create <= p_end + timedelta(days=1):
                                    lag = (dt_call - dt_create).days
                                    if lag >= 0:  # Ignore negative lags (data errors)
                                        lag_days.append(lag)
                            except:
                                continue
                        avg_lag = sum(lag_days) / len(lag_days) if lag_days else 0

                        # No-Show post-triage = qualificati che non si presentano alla Sales Call
                        n_noshow_post_triage = n_qualified - n_show
                        noshow_post_triage_rate = n_noshow_post_triage / n_qualified if n_qualified > 0 else 0

                        return {
                            'cpl': spend / n_cand,
                            'booking_rate': n_calls_booked / n_cand,  # VideoAsk → Calendly
                            'triage_pass': triage_pass,               # % not disqualified
                            'show_rate': n_show / n_qualified if n_qualified > 0 else 0,  # FIXED: esclusi scartati
                            'close_rate': close_rate,                 # Closes / Qualified
                            'noshow_post_triage_rate': noshow_post_triage_rate,  # % qualificati che non si presentano
                            'aov': aov,                               # Ticket Medio (contratti)
                            'aov_cash': aov_cash,                     # Incasso Medio (cash)
                            'avg_lag': avg_lag,                       # Days from booking to call
                            'n_cand': n_cand,
                            'n_calls': n_calls_booked,
                            'n_qualified': n_qualified,
                            'n_scartati': n_scartati,
                            'n_show': n_show,
                            'n_noshow_post_triage': n_noshow_post_triage,
                            'n_close': n_close,
                        }

                    # Get metrics for both periods
                    sunny_meta = load_meta_data(meta_dir, sunny_label) if sunny_label != args.period else meta_data
                    rainy_meta = load_meta_data(meta_dir, rainy_label) if rainy_label != args.period else meta_data

                    sunny_totals = sunny_meta.get('totals', {}) if sunny_meta else {}
                    rainy_totals = rainy_meta.get('totals', {}) if rainy_meta else {}

                    m_best = calc_funnel_metrics(sunny_totals, sunny_totals.get('spend', 0), calls, candidature)
                    m_curr = calc_funnel_metrics(rainy_totals, rainy_totals.get('spend', 0), calls, candidature)

                    if m_best and m_curr:
                        # Funnel stages header
                        print(f"\n  📊 FUNNEL: Ads → VideoAsk → Calendly → Triage → Sales")
                        print(f"\n  Confronto: {sunny_label} (Standard) vs {rainy_label} (Attuale)")
                        print(f"\n  {'STEP FUNNEL':<18} │ {'STANDARD':>10} │ {'ATTUALE':>10} │ {'Δ':>10}")
                        print(f"  {'-'*18} │ {'-'*10} │ {'-'*10} │ {'-'*10}")

                        def print_row(label, val_old, val_new, is_currency=False, inverse=False):
                            """Print a row and return the delta for logic."""
                            diff = (val_new - val_old) / val_old if val_old > 0 else 0

                            if is_currency:
                                s_old = f"€{val_old:.2f}"
                                s_new = f"€{val_new:.2f}"
                            else:
                                s_old = f"{val_old*100:.1f}%"
                                s_new = f"{val_new*100:.1f}%"

                            good = (diff >= 0) if not inverse else (diff <= 0)

                            if abs(diff) < 0.05:
                                icon = "⚪"
                            elif good:
                                icon = "🟢"
                            else:
                                icon = "🔴"

                            print(f"  {label:<18} │ {s_old:>10} │ {s_new:>10} │ {icon} {diff:+.0%}")
                            return diff

                        d_cpl = print_row("① Costo Candidat.", m_best['cpl'], m_curr['cpl'], is_currency=True, inverse=True)
                        d_br = print_row("② Booking Rate", m_best['booking_rate'], m_curr['booking_rate'])
                        d_tp = print_row("③ Triage Pass", m_best['triage_pass'], m_curr['triage_pass'])
                        d_sr = print_row("④ Show Rate", m_best['show_rate'], m_curr['show_rate'])
                        d_cl = print_row("⑤ Close Rate", m_best['close_rate'], m_curr['close_rate'])
                        d_ns = print_row("⑥ No-Show Post-Tri", m_best['noshow_post_triage_rate'], m_curr['noshow_post_triage_rate'], inverse=True)

                        # Additional metrics: AOV (Revenue + Cash) and LAG
                        print(f"  {'-'*18} │ {'-'*10} │ {'-'*10} │ {'-'*10}")
                        d_aov = print_row("💰 Ticket Medio (Rev)", m_best['aov'], m_curr['aov'], is_currency=True)
                        d_aov_cash = print_row("💵 Incasso Medio", m_best['aov_cash'], m_curr['aov_cash'], is_currency=True)

                        # LAG: special handling (lower is better)
                        lag_diff = (m_curr['avg_lag'] - m_best['avg_lag']) / m_best['avg_lag'] if m_best['avg_lag'] > 0 else 0
                        if lag_diff > 0.20:
                            lag_icon = "🔴"
                        elif lag_diff < -0.10:
                            lag_icon = "🟢"
                        else:
                            lag_icon = "⚪"
                        print(f"  {'⏱️ Tempo Attesa':<18} │ {m_best['avg_lag']:>9.1f}d │ {m_curr['avg_lag']:>9.1f}d │ {lag_icon} {lag_diff:+.0%}")
                        d_lag = lag_diff

                        # Volume context con Show Up e No-Show post-triage
                        print(f"\n  Volumi attuali: {m_curr['n_cand']} candidature → {m_curr['n_calls']} call")
                        print(f"                  → {m_curr['n_qualified']} qualificati ({m_curr['n_scartati']} scartati)")
                        print(f"                  → {m_curr['n_show']} show up ({m_curr['n_noshow_post_triage']} no-show post-triage)")
                        print(f"                  → {m_curr['n_close']} vendite")

                        # ─── THE NARRATIVE VERDICT ───
                        print(f"\n  {'─'*56}")
                        print(f"  🕵️  VERDETTO")
                        print(f"  {'─'*56}")

                        # === PATTERN DETECTION (in order of priority) ===

                        # 0a. CHECK "GHIACCIO" - Calendario pieno, lead si raffreddano
                        if d_lag > 0.30 and m_curr['avg_lag'] > 5:
                            print(f"\n  🧊 PROBLEMA: CALENDARIO TROPPO PIENO (Lead 'Ghiacciati')")
                            print(f"")
                            print(f"  Cosa sta succedendo:")
                            print(f"  • Tempo medio di attesa: {m_best['avg_lag']:.1f}d → {m_curr['avg_lag']:.1f}d (+{d_lag*100:.0f}%)")
                            print(f"  • I lead aspettano troppo e si 'raffreddano'")
                            print(f"  • Nell'High Ticket, l'emozione è tutto!")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. URGENTE: Apri più slot nel calendario")
                            print(f"  2. Assumi/attiva più setter/closer")
                            print(f"  3. Considera turni weekend o fasce serali")

                        # 0b. CHECK "SVENDITA" - Close ok ma AOV crolla
                        elif d_aov < -0.15 and abs(d_cl) < 0.10:
                            print(f"\n  💸 PROBLEMA: SVENDITA DA PANICO (Dumping Prezzi)")
                            print(f"")
                            print(f"  Cosa sta succedendo:")
                            print(f"  • Il Close Rate è stabile ({d_cl:+.0%})")
                            print(f"  • Ma il Ticket Medio è crollato ({d_aov:+.0%})")
                            print(f"  • I venditori 'comprano' le chiusure con sconti")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. Audit immediato: chi sta scontando e perché?")
                            print(f"  2. Verifica policy sconti e downsell")
                            print(f"  3. Ascolta le call - stanno negoziando troppo?")

                        # 0c. CHECK NO-SHOW POST-TRIAGE - Confronta con Show Rate generale
                        elif d_ns > 0.10:  # No-Show Post-Triage aumentato >10%
                            # Scenario 1: Show Rate generale cala proporzionalmente
                            if d_sr < -0.10:
                                print(f"\n  👻 PROBLEMA: GHOSTING GENERALIZZATO")
                                print(f"")
                                print(f"  Cosa sta succedendo:")
                                print(f"  • Show Rate generale: {d_sr:+.0%}")
                                print(f"  • No-Show Post-Triage: {d_ns:+.0%}")
                                print(f"  • Il calo è SISTEMICO, non solo post-triage")
                                print(f"  • I lead spariscono a tutti i livelli del funnel")
                                print(f"")
                                print(f"  ✅ COSA FARE:")
                                print(f"  1. Audit COMPLETO sistema reminder (email + SMS + WhatsApp)")
                                print(f"  2. Verifica deliverability messaggi")
                                print(f"  3. Controlla se i lead ricevono le comunicazioni")
                                print(f"  4. Considera reminder più aggressivi (chiamata pre-call)")

                            # Scenario 2: Triage Pass aumenta E No-Show Post-Triage peggiora
                            elif d_tp > 0.10:
                                print(f"\n  🚪 PROBLEMA: TRIAGE TROPPO PERMISSIVO")
                                print(f"")
                                print(f"  Cosa sta succedendo:")
                                print(f"  • Triage Pass: {d_tp:+.0%} (passano più lead)")
                                print(f"  • No-Show Post-Triage: {d_ns:+.0%} (ma poi non vengono)")
                                print(f"  • Il triage sta qualificando lead non motivati")
                                print(f"  • Passano il filtro ma non hanno vero interesse")
                                print(f"")
                                print(f"  ✅ COSA FARE:")
                                print(f"  1. Alza i criteri di qualificazione al triage")
                                print(f"  2. Aggiungi domande di commitment ('Sei sicuro di poter venire?')")
                                print(f"  3. Verifica che il triage non stia 'regalando' appuntamenti")

                            # Scenario 3: Show Rate stabile ma No-Show Post-Triage peggiora
                            else:
                                print(f"\n  🎯 PROBLEMA: GHOSTING POST-TRIAGE SPECIFICO")
                                print(f"")
                                print(f"  Cosa sta succedendo:")
                                print(f"  • Show Rate generale: {d_sr:+.0%} (stabile)")
                                print(f"  • No-Show Post-Triage: {d_ns:+.0%} (in aumento)")
                                print(f"  • Il problema è SPECIFICO tra triage e sales call")
                                print(f"  • I lead si 'raffreddano' dopo essere stati qualificati")
                                print(f"")
                                print(f"  ✅ COSA FARE:")
                                print(f"  1. Riduci tempo tra triage e sales call")
                                print(f"  2. Aggiungi reminder SPECIFICO post-triage")
                                print(f"  3. Invia contenuto di valore tra triage e call")
                                print(f"  4. Considera chiamata di conferma 24h prima")

                        # 1. CPL Exploded (Ads → VideoAsk problem)
                        elif d_cpl > 0.20:
                            print(f"\n  🔴 PROBLEMA: COSTI ADS / TRAFFICO")
                            print(f"")
                            print(f"  Dove si blocca: Ads → VideoAsk")
                            print(f"  • Il costo per candidatura è salito del {d_cpl:+.0%}")
                            print(f"  • Le creative sono stanche o l'audience è satura")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. Spegni ads con CPL sopra €{m_curr['cpl']*1.2:.0f}")
                            print(f"  2. Lancia nuove creative")
                            print(f"  3. Controlla che il VideoAsk non abbia problemi tecnici")

                        # 2. Booking Rate Crashed (VideoAsk → Calendly problem)
                        elif d_br < -0.15:
                            print(f"\n  🔴 PROBLEMA: SOVRACCARICO SETTER / VSL2 INEFFICACE")
                            print(f"")
                            print(f"  Dove si blocca: VideoAsk → Calendly")
                            print(f"  • Le persone compilano VideoAsk ma NON prenotano ({d_br:+.0%})")
                            print(f"  • Il booking automatico (VSL 2) non converte")
                            print(f"  • I Setter devono inseguire manualmente i lead")
                            print(f"")
                            print(f"  ⚠️  RISCHIO: Collo di bottiglia operativo")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. URGENTE: Controlla disponibilità calendario!")
                            print(f"  2. Ottimizza VSL 2 (il percorso post-VideoAsk)")
                            print(f"  3. Valuta se i Setter sono sovraccarichi di outbound")

                        # 3. Triage Pass Crashed (troppi scartati)
                        elif d_tp < -0.10:
                            print(f"\n  🔴 PROBLEMA: QUALITÀ LEAD (Triage Massacre)")
                            print(f"")
                            print(f"  Dove si blocca: Triage Call")
                            print(f"  • Stiamo scartando {abs(d_tp)*100:.0f}% in più di lead")
                            print(f"  • Le ads portano gente non qualificata (no budget/tempo)")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. Indurisci le domande del VideoAsk")
                            print(f"  2. L'ad promette cose troppo facili? Rivedi il copy")
                            print(f"  3. Aggiungi domande filtro su budget/disponibilità")

                        # 4. Booking UP + Close DOWN = "Turisti"
                        elif d_cl < -0.15 and d_br > 0.10:
                            print(f"\n  🔴 PROBLEMA: EFFETTO 'TURISTI'")
                            print(f"")
                            print(f"  Pattern rilevato:")
                            print(f"  • Più persone prenotano call ({d_br:+.0%})")
                            print(f"  • Ma molte meno comprano ({d_cl:+.0%})")
                            print(f"  • Arrivano curiosi, non compratori")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. Indurisci il VideoAsk (domande più qualificanti)")
                            print(f"  2. Rivedi le creative - troppo 'clickbait'?")
                            print(f"  3. Escludi audience fredde dal targeting")

                        # 5. Show Rate Crashed (No-Show problem)
                        elif d_sr < -0.10:
                            print(f"\n  🔴 PROBLEMA: NO-SHOW")
                            print(f"")
                            print(f"  Dove si blocca: Prima della call")
                            print(f"  • La gente prenota ma non si presenta ({d_sr:+.0%})")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. Migliora reminder (WhatsApp/SMS 24h e 1h prima)")
                            print(f"  2. Fai chiamare i setter PRIMA della call")
                            print(f"  3. Verifica coerenza messaggio ads vs landing")

                        # 6. Close Rate Crashed (pure sales problem)
                        elif d_cl < -0.15:
                            print(f"\n  🔴 PROBLEMA: CHIUSURA VENDITA")
                            print(f"")
                            print(f"  Dove si blocca: Sales Call")
                            print(f"  • I lead superano il Triage ma non comprano ({d_cl:+.0%})")
                            print(f"  • Il problema è nel processo di vendita")
                            print(f"")
                            print(f"  ⚠️  NOTA: Verifica anche i No-Show post-triage!")
                            print(f"     Se i qualificati non si presentano alla Sales Call,")
                            print(f"     il problema non è il venditore ma il follow-up.")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. Ascolta le ultime 5 call perse")
                            print(f"  2. Controlla No-Show post-triage (reminder?)")
                            print(f"  3. Nuove obiezioni? Offerta competitiva?")

                        # 7. No clear culprit
                        else:
                            print(f"\n  🟡 CALO DIFFUSO")
                            print(f"")
                            print(f"  Non c'è un singolo punto di rottura evidente.")
                            print(f"  Piccoli cali su più step del funnel.")
                            print(f"")
                            print(f"  ✅ COSA FARE:")
                            print(f"  1. Riduci budget 20% per stabilizzare")
                            print(f"  2. Audit completo: ads, form, follow-up, sales")
                            print(f"  3. Monitora 7 giorni prima di altre mosse")
