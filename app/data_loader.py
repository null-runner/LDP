"""
Data Loader for LDP Dashboard
Handles CSV uploads, multi-period detection, and Airtable integration
"""
import re
import csv
import json
from datetime import datetime
from pathlib import Path
import streamlit as st
from pyairtable import Api


# Month name to number mapping
MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}


def parse_filename_dates(filename):
    """
    Parse date range from CSV filename.

    Example: "CL---MD---info-1-Ads-Dec-1-2025-Dec-31-2025.csv"
    Returns: ("2025-12-01", "2025-12-31") or (None, None)
    """
    # Pattern: Month-Day-Year to Month-Day-Year
    pattern = r'([A-Z][a-z]{2})-(\d+)-(\d{4})-([A-Z][a-z]{2})-(\d+)-(\d{4})'
    match = re.search(pattern, filename)

    if match:
        month1, day1, year1, month2, day2, year2 = match.groups()

        # Convert month name to number
        if month1 in MONTH_MAP and month2 in MONTH_MAP:
            start_date = f"{year1}-{MONTH_MAP[month1]:02d}-{int(day1):02d}"
            end_date = f"{year2}-{MONTH_MAP[month2]:02d}-{int(day2):02d}"
            return start_date, end_date

    return None, None


def detect_periods_from_filenames(uploaded_files):
    """
    Detect unique periods from uploaded CSV filenames.

    Args:
        uploaded_files: Dict with keys 'ads', 'adsets', 'campaigns' containing UploadedFile objects

    Returns:
        List of dicts: [{"start": "2025-12-01", "end": "2025-12-31", "label": "Dec 1-31, 2025"}, ...]
    """
    periods_set = set()

    for file_type, file in uploaded_files.items():
        if file is not None:
            start, end = parse_filename_dates(file.name)
            if start and end:
                periods_set.add((start, end))

    # Convert to list of dicts and sort by date
    periods = []
    for start, end in sorted(periods_set):
        # Create human-readable label
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        label = f"{start_dt.strftime('%b %d')}-{end_dt.strftime('%d, %Y')}"

        periods.append({
            "start": start,
            "end": end,
            "label": label
        })

    return periods


def load_meta_csvs(ads_file, adsets_file, campaigns_file):
    """
    Load and parse Meta CSV files.

    Args:
        ads_file: UploadedFile for ads.csv
        adsets_file: UploadedFile for adsets.csv
        campaigns_file: UploadedFile for campaigns.csv

    Returns:
        Dict with 'ads', 'adsets', 'campaigns' lists
    """
    result = {
        'ads': [],
        'adsets': [],
        'campaigns': []
    }

    # Load ads
    if ads_file is not None:
        ads_file.seek(0)
        content = ads_file.read().decode('utf-8')
        reader = csv.DictReader(content.splitlines())
        result['ads'] = [row for row in reader if row.get('Ad name')]

    # Load adsets
    if adsets_file is not None:
        adsets_file.seek(0)
        content = adsets_file.read().decode('utf-8')
        reader = csv.DictReader(content.splitlines())
        # Filter out totals row
        result['adsets'] = [row for row in reader if row.get('Ad set name') and 'Total' not in row.get('Ad set name', '')]

    # Load campaigns
    if campaigns_file is not None:
        campaigns_file.seek(0)
        content = campaigns_file.read().decode('utf-8')
        reader = csv.DictReader(content.splitlines())
        result['campaigns'] = [row for row in reader if row.get('Campaign name')]

    return result


@st.cache_data(ttl=86400)  # Cache for 24 hours (daily refresh)
def refresh_airtable_data(api_key, base_id):
    """
    Fetch latest candidature and calls from Airtable.
    Cached daily to avoid rate limits and unnecessary API calls.

    Data is ONLY stored in Streamlit's in-memory cache, NOT on disk.
    Cache expires daily or when manually cleared via Streamlit UI.

    Args:
        api_key: Airtable API key
        base_id: Airtable base ID

    Returns:
        Dict with 'candidature' and 'calls' lists
    """
    api = Api(api_key)

    try:
        candidature_table = api.table(base_id, 'Candidature')
        calls_table = api.table(base_id, 'Calls')

        candidature = candidature_table.all()
        calls = calls_table.all()

        # Data is ONLY in Streamlit cache (RAM), NOT written to disk
        # This ensures no business data persists locally or in repository

        return {
            'candidature': candidature,
            'calls': calls,
            'last_updated': datetime.now().isoformat()
        }
    except Exception as e:
        st.error(f"Error fetching Airtable data: {e}")
        return {'candidature': [], 'calls': [], 'last_updated': None}


def filter_data_by_period(data, period_start, period_end):
    """
    Filter candidature, calls, and ads by date range.

    Args:
        data: Dict with 'candidature', 'calls', 'ads' lists
        period_start: Start date string (YYYY-MM-DD)
        period_end: End date string (YYYY-MM-DD)

    Returns:
        Dict with filtered data
    """
    filtered = {
        'candidature': [],
        'calls': [],
        'ads': data.get('ads', []),  # Ads are pre-filtered by filename
        'adsets': data.get('adsets', []),
        'campaigns': data.get('campaigns', [])
    }

    # Filter candidature by Data Creazione
    for record in data.get('candidature', []):
        fields = record.get('fields', {})
        data_creazione = fields.get('Data Creazione', '')

        if data_creazione:
            date_str = data_creazione[:10]  # Extract YYYY-MM-DD
            if period_start <= date_str <= period_end:
                filtered['candidature'].append(record)

    # Filter calls by Data Call
    for record in data.get('calls', []):
        fields = record.get('fields', {})
        data_call = fields.get('Data Call', '')

        if data_call:
            date_str = data_call[:10]  # Extract YYYY-MM-DD
            if period_start <= date_str <= period_end:
                filtered['calls'].append(record)

    return filtered


def calculate_total_spend(ads):
    """
    Calculate total Meta ADS spend from ads list.

    Args:
        ads: List of ad dicts with 'Amount spent (EUR)' field

    Returns:
        Total spend as float
    """
    total_spend = 0.0

    for ad in ads:
        try:
            spend = float(ad.get('Amount spent (EUR)', '0') or 0)
            total_spend += spend
        except:
            continue

    return total_spend
