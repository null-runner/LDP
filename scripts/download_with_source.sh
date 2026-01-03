#!/bin/bash
API_KEY="pat122b9CeLsyPcjO.2f5f94a49418e945e03ba965ba1238ba472376e975f0091802a32758db0d4294"
BASE_ID="app76iRKXL8w1NghG"
DATA_DIR="/home/null-runner/Projects/SynthOps/LDP/data"

echo "=== DOWNLOADING CANDIDATURE con UTM Source ==="
TABLE_CAND="tblqLo4QdlQZnJWTq"
OFFSET=""
PAGE=1
rm -f /tmp/cand_src_page_*.json 2>/dev/null

while true; do
    echo "Candidature page $PAGE..."
    if [ -z "$OFFSET" ]; then
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CAND}?fields%5B%5D=Data%20Creazione&fields%5B%5D=UTM%20Medium&fields%5B%5D=UTM%20Source&fields%5B%5D=UTM%20Campaign&fields%5B%5D=Stato%20Contatto&pageSize=100"
    else
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CAND}?fields%5B%5D=Data%20Creazione&fields%5B%5D=UTM%20Medium&fields%5B%5D=UTM%20Source&fields%5B%5D=UTM%20Campaign&fields%5B%5D=Stato%20Contatto&pageSize=100&offset=${OFFSET}"
    fi
    curl -s "$URL" -H "Authorization: Bearer ${API_KEY}" > "/tmp/cand_src_page_${PAGE}.json"
    OFFSET=$(jq -r '.offset // empty' "/tmp/cand_src_page_${PAGE}.json")
    PAGE=$((PAGE + 1))
    [ -z "$OFFSET" ] && break
    sleep 0.12
done
jq -s '{ records: map(.records) | add }' /tmp/cand_src_page_*.json > "${DATA_DIR}/candidature_with_source.json"
rm -f /tmp/cand_src_page_*.json 2>/dev/null
echo "Candidature: $(jq '.records | length' ${DATA_DIR}/candidature_with_source.json)"

echo ""
echo "=== DOWNLOADING CALLS con UTM Source ==="
TABLE_CALLS="tblW3PtC9Lf6SrA4l"
OFFSET=""
PAGE=1
rm -f /tmp/calls_src_page_*.json 2>/dev/null

while true; do
    echo "Calls page $PAGE..."
    if [ -z "$OFFSET" ]; then
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CALLS}?fields%5B%5D=Data%20Creazione&fields%5B%5D=UTM%20Adset%20(medium)&fields%5B%5D=UTM%20Fonte%20(source)&fields%5B%5D=UTM%20Campagna%20(campaign)&fields%5B%5D=Stato&fields%5B%5D=Cash%20Collected&fields%5B%5D=Revenue&pageSize=100"
    else
        URL="https://api.airtable.com/v0/${BASE_ID}/${TABLE_CALLS}?fields%5B%5D=Data%20Creazione&fields%5B%5D=UTM%20Adset%20(medium)&fields%5B%5D=UTM%20Fonte%20(source)&fields%5B%5D=UTM%20Campagna%20(campaign)&fields%5B%5D=Stato&fields%5B%5D=Cash%20Collected&fields%5B%5D=Revenue&pageSize=100&offset=${OFFSET}"
    fi
    curl -s "$URL" -H "Authorization: Bearer ${API_KEY}" > "/tmp/calls_src_page_${PAGE}.json"
    OFFSET=$(jq -r '.offset // empty' "/tmp/calls_src_page_${PAGE}.json")
    PAGE=$((PAGE + 1))
    [ -z "$OFFSET" ] && break
    sleep 0.12
done
jq -s '{ records: map(.records) | add }' /tmp/calls_src_page_*.json > "${DATA_DIR}/calls_with_source.json"
rm -f /tmp/calls_src_page_*.json 2>/dev/null
echo "Calls: $(jq '.records | length' ${DATA_DIR}/calls_with_source.json)"

echo ""
echo "=== UTM Source unici (Candidature) ==="
jq -r '[.records[].fields["UTM Source"] // "VUOTO"] | group_by(.) | map({source: .[0], count: length}) | sort_by(-.count) | .[:10] | .[] | "\(.source): \(.count)"' "${DATA_DIR}/candidature_with_source.json"

echo ""
echo "=== UTM Source unici (Calls) ==="
jq -r '[.records[].fields["UTM Fonte (source)"] // "VUOTO"] | group_by(.) | map({source: .[0], count: length}) | sort_by(-.count) | .[:10] | .[] | "\(.source): \(.count)"' "${DATA_DIR}/calls_with_source.json"
