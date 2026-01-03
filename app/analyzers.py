"""
Core Analysis Logic for LDP Dashboard
Extracted from generate_dashboard.py for reuse in Streamlit app
"""
from collections import defaultdict

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


def analyze_funnel(candidature, calls, meta_spend=0):
    """
    Analizza il funnel completo.

    Args:
        candidature: Lista di record candidature
        calls: Lista di record calls
        meta_spend: Spesa Meta ADS totale

    Returns:
        Dict con metriche funnel
    """
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

    # Calcola metriche
    cand_to_call_rate = (total_calls / total_cand * 100) if total_cand > 0 else 0
    call_to_showup_rate = (show_ups / total_calls * 100) if total_calls > 0 else 0
    showup_to_close_rate = (closures / show_ups * 100) if show_ups > 0 else 0

    ticket_medio = (total_revenue / closures) if closures > 0 else 0

    # Cost metrics
    cpl = (meta_spend / total_cand) if total_cand > 0 else 0
    cpc = (meta_spend / total_calls) if total_calls > 0 else 0
    cpsu = (meta_spend / show_ups) if show_ups > 0 else 0
    cpcl = (meta_spend / closures) if closures > 0 else 0

    # ROAS
    roas_revenue = (total_revenue / meta_spend) if meta_spend > 0 else 0
    roas_cash = (total_cash / meta_spend) if meta_spend > 0 else 0

    return {
        'candidature': total_cand,
        'calls': total_calls,
        'show_ups': show_ups,
        'closures': closures,
        'revenue': total_revenue,
        'cash': total_cash,
        'ticket_medio': ticket_medio,
        'by_status': dict(by_status),
        'cand_to_call_rate': cand_to_call_rate,
        'call_to_showup_rate': call_to_showup_rate,
        'showup_to_close_rate': showup_to_close_rate,
        'cpl': cpl,
        'cpc': cpc,
        'cpsu': cpsu,
        'cpcl': cpcl,
        'roas_revenue': roas_revenue,
        'roas_cash': roas_cash,
        'total_spend': meta_spend
    }


def analyze_creative(ads):
    """
    Analizza performance creative.

    Args:
        ads: Lista di dict con dati ads from Meta CSV

    Returns:
        Lista di dict con performance creative
    """
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
                'name': ad.get('Ad name', 'Unknown'),
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
    """
    Analizza performance setter.

    Args:
        calls: Lista di record calls

    Returns:
        Dict con performance per setter
    """
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
    """
    Analizza performance venditori/closer.

    Args:
        calls: Lista di record calls

    Returns:
        Dict con performance per closer
    """
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
