#!/bin/bash
API_KEY="pat122b9CeLsyPcjO.2f5f94a49418e945e03ba965ba1238ba472376e975f0091802a32758db0d4294"
BASE_ID="app76iRKXL8w1NghG"
DATA_DIR="/home/null-runner/Projects/SynthOps/LDP/data"

echo "=== DOWNLOAD COMPLETO AIRTABLE (tutte le colonne) ==="
echo "Start: $(date)"

# CANDIDATURE - TUTTE LE COLONNE
echo ""
echo "=== CANDIDATURE (tutte le colonne) ==="
TABLE_CAND="tblqLo4QdlQZnJWTq"
OFFSET=""
PAGE=1
rm -f /tmp/full_cand_page_*.json 2>/dev/null

while true; do
    echo "Candidature page $PAGE..."
    if [ -z "$OFFSET" ]; then
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CAND}?pageSize=100"
    else
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CAND}?pageSize=100&offset=${OFFSET}"
    fi
    curl -s "$URL" -H "Authorization: Bearer ${API_KEY}" > "/tmp/full_cand_page_${PAGE}.json"
    OFFSET=$(jq -r '.offset // empty' "/tmp/full_cand_page_${PAGE}.json")
    PAGE=$((PAGE + 1))
    [ -z "$OFFSET" ] && break
    sleep 0.1
done
echo "Merging candidature..."
jq -s '{ records: map(.records) | add }' /tmp/full_cand_page_*.json > "${DATA_DIR}/candidature_full.json"
rm -f /tmp/full_cand_page_*.json 2>/dev/null
echo "Candidature: $(jq '.records | length' ${DATA_DIR}/candidature_full.json) records"
echo "Size: $(ls -lh ${DATA_DIR}/candidature_full.json | awk '{print $5}')"

# CALLS - TUTTE LE COLONNE
echo ""
echo "=== CALLS (tutte le colonne) ==="
TABLE_CALLS="tblW3PtC9Lf6SrA4l"
OFFSET=""
PAGE=1
rm -f /tmp/full_calls_page_*.json 2>/dev/null

while true; do
    echo "Calls page $PAGE..."
    if [ -z "$OFFSET" ]; then
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CALLS}?pageSize=100"
    else
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CALLS}?pageSize=100&offset=${OFFSET}"
    fi
    curl -s "$URL" -H "Authorization: Bearer ${API_KEY}" > "/tmp/full_calls_page_${PAGE}.json"
    OFFSET=$(jq -r '.offset // empty' "/tmp/full_calls_page_${PAGE}.json")
    PAGE=$((PAGE + 1))
    [ -z "$OFFSET" ] && break
    sleep 0.1
done
echo "Merging calls..."
jq -s '{ records: map(.records) | add }' /tmp/full_calls_page_*.json > "${DATA_DIR}/calls_full.json"
rm -f /tmp/full_calls_page_*.json 2>/dev/null
echo "Calls: $(jq '.records | length' ${DATA_DIR}/calls_full.json) records"
echo "Size: $(ls -lh ${DATA_DIR}/calls_full.json | awk '{print $5}')"

# OPTIN - TUTTE LE COLONNE
echo ""
echo "=== OPTIN (tutte le colonne) ==="
TABLE_OPTIN="tblJGBuINDiosmxGM"
OFFSET=""
PAGE=1
rm -f /tmp/full_optin_page_*.json 2>/dev/null

while true; do
    echo "Optin page $PAGE..."
    if [ -z "$OFFSET" ]; then
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_OPTIN}?pageSize=100"
    else
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_OPTIN}?pageSize=100&offset=${OFFSET}"
    fi
    curl -s "$URL" -H "Authorization: Bearer ${API_KEY}" > "/tmp/full_optin_page_${PAGE}.json"
    OFFSET=$(jq -r '.offset // empty' "/tmp/full_optin_page_${PAGE}.json")
    PAGE=$((PAGE + 1))
    [ -z "$OFFSET" ] && break
    sleep 0.1
done
echo "Merging optin..."
jq -s '{ records: map(.records) | add }' /tmp/full_optin_page_*.json > "${DATA_DIR}/optin_full.json"
rm -f /tmp/full_optin_page_*.json 2>/dev/null
echo "Optin: $(jq '.records | length' ${DATA_DIR}/optin_full.json) records"
echo "Size: $(ls -lh ${DATA_DIR}/optin_full.json | awk '{print $5}')"

# OPTIN ADS - TUTTE LE COLONNE
echo ""
echo "=== OPTIN ADS (tutte le colonne) ==="
TABLE_OPTIN_ADS="tblzaJbXDoYQXUhgf"
OFFSET=""
PAGE=1
rm -f /tmp/full_optin_ads_page_*.json 2>/dev/null

while true; do
    echo "Optin ADs page $PAGE..."
    if [ -z "$OFFSET" ]; then
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_OPTIN_ADS}?pageSize=100"
    else
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_OPTIN_ADS}?pageSize=100&offset=${OFFSET}"
    fi
    curl -s "$URL" -H "Authorization: Bearer ${API_KEY}" > "/tmp/full_optin_ads_page_${PAGE}.json"
    OFFSET=$(jq -r '.offset // empty' "/tmp/full_optin_ads_page_${PAGE}.json")
    PAGE=$((PAGE + 1))
    [ -z "$OFFSET" ] && break
    sleep 0.1
done
echo "Merging optin ads..."
jq -s '{ records: map(.records) | add }' /tmp/full_optin_ads_page_*.json > "${DATA_DIR}/optin_ads_full.json"
rm -f /tmp/full_optin_ads_page_*.json 2>/dev/null
echo "Optin ADs: $(jq '.records | length' ${DATA_DIR}/optin_ads_full.json) records"
echo "Size: $(ls -lh ${DATA_DIR}/optin_ads_full.json | awk '{print $5}')"

echo ""
echo "=== DOWNLOAD COMPLETATO ==="
echo "End: $(date)"
echo ""
ls -lh ${DATA_DIR}/*_full.json
