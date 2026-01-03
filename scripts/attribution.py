"""
LDP Marketing Analysis - Attribution Engine
============================================
Logica di attribuzione delle conversioni ai canali ads.

Metodologia:
- UTM Source = "meta" → 100% attribuito ads
- UTM Source = vuoto/null → 50% attribuito (conservativo) o 100% (panoramico)
- UTM Source = altro → 0% ads (conteggio separato)
"""

import math
from typing import Dict, List, Tuple
from config import META_SOURCES, OTHER_SOURCES


def categorize_source(source: str) -> str:
    """
    Categorizza una fonte UTM.

    Returns:
        'meta': fonte da ads Meta
        'vuoto': fonte non specificata
        'altro': altra fonte identificata
    """
    if not source or source.strip() == '':
        return 'vuoto'

    source_lower = source.lower().strip()

    # Check if it's a Meta source
    for meta in META_SOURCES:
        if meta in source_lower:
            return 'meta'

    # It's another identified source
    return 'altro'


def get_source_name(source: str) -> str:
    """Normalizza il nome della fonte per raggruppamento."""
    if not source or source.strip() == '':
        return 'Vuoto'

    source_lower = source.lower().strip()

    # Normalize known sources
    if 'instagram' in source_lower:
        return 'Instagram'
    if 'telegram' in source_lower:
        return 'Telegram'
    if 'google' in source_lower:
        return 'Google'
    if 'youtube' in source_lower:
        return 'YouTube'
    if 'tiktok' in source_lower:
        return 'TikTok'
    if any(m in source_lower for m in META_SOURCES):
        return 'Meta'

    return source.strip()


def calculate_attributed_metrics(
    records: List[dict],
    source_field: str,
    mode: str = 'conservative'
) -> Tuple[float, Dict[str, int]]:
    """
    Calcola metriche con attribuzione.

    Args:
        records: Lista di record Airtable
        source_field: Campo contenente UTM Source
        mode: 'conservative' (meta + 50% vuoto) o 'panoramic' (meta + 100% vuoto)

    Returns:
        Tuple[attributed_count, other_sources_dict]
    """
    meta_count = 0
    empty_count = 0
    other_sources = {}

    for record in records:
        fields = record.get('fields', {})
        source = fields.get(source_field, '')
        category = categorize_source(source)

        if category == 'meta':
            meta_count += 1
        elif category == 'vuoto':
            empty_count += 1
        else:
            source_name = get_source_name(source)
            other_sources[source_name] = other_sources.get(source_name, 0) + 1

    # Calculate attributed count based on mode
    if mode == 'conservative':
        # Meta + 50% empty (rounded up)
        attributed = meta_count + math.ceil(empty_count / 2)
    elif mode == 'panoramic':
        # Meta + 100% empty
        attributed = meta_count + empty_count
    else:
        attributed = meta_count

    return attributed, other_sources


def calculate_metrics_by_adset(
    records: List[dict],
    source_field: str,
    medium_field: str,
    mode: str = 'conservative'
) -> Dict[str, dict]:
    """
    Calcola metriche raggruppate per ad set.

    Returns:
        Dict con adset_name -> {meta: n, vuoto: n, altro: n, attributed: n}
    """
    adsets = {}

    for record in records:
        fields = record.get('fields', {})
        source = fields.get(source_field, '')
        adset = fields.get(medium_field, '') or 'Non specificato'

        if adset not in adsets:
            adsets[adset] = {'meta': 0, 'vuoto': 0, 'altro': 0}

        category = categorize_source(source)
        adsets[adset][category] = adsets[adset].get(category, 0) + 1

    # Calculate attributed for each adset
    for adset, counts in adsets.items():
        if mode == 'conservative':
            counts['attributed'] = counts['meta'] + math.ceil(counts['vuoto'] / 2)
        else:
            counts['attributed'] = counts['meta'] + counts['vuoto']
        counts['total'] = counts['meta'] + counts['vuoto'] + counts['altro']

    return adsets


def get_attribution_breakdown(records: List[dict], source_field: str) -> dict:
    """
    Ottieni breakdown completo delle fonti.

    Returns:
        {
            'meta': {'count': n, 'pct': x},
            'vuoto': {'count': n, 'pct': x},
            'altri': {'Instagram': n, 'Telegram': n, ...}
        }
    """
    meta_count = 0
    empty_count = 0
    other_sources = {}
    total = len(records)

    for record in records:
        fields = record.get('fields', {})
        source = fields.get(source_field, '')
        category = categorize_source(source)

        if category == 'meta':
            meta_count += 1
        elif category == 'vuoto':
            empty_count += 1
        else:
            source_name = get_source_name(source)
            other_sources[source_name] = other_sources.get(source_name, 0) + 1

    return {
        'meta': {
            'count': meta_count,
            'pct': round(meta_count / total * 100, 1) if total > 0 else 0
        },
        'vuoto': {
            'count': empty_count,
            'pct': round(empty_count / total * 100, 1) if total > 0 else 0
        },
        'altri': other_sources,
        'altri_total': sum(other_sources.values())
    }


if __name__ == "__main__":
    # Test
    test_records = [
        {'fields': {'source': 'meta'}},
        {'fields': {'source': 'meta'}},
        {'fields': {'source': ''}},
        {'fields': {'source': ''}},
        {'fields': {'source': ''}},
        {'fields': {'source': 'instagram'}},
    ]

    attr, others = calculate_attributed_metrics(test_records, 'source', 'conservative')
    print(f"Conservative: {attr} attributed")  # Should be 2 + ceil(3/2) = 4

    attr, others = calculate_attributed_metrics(test_records, 'source', 'panoramic')
    print(f"Panoramic: {attr} attributed")  # Should be 2 + 3 = 5

    print(f"Other sources: {others}")  # Should be {'Instagram': 1}
