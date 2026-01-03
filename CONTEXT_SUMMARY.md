# LDP Marketing Analysis - Context Summary

**Data:** 2025-12-16
**Progetto:** Analisi marketing LDP con attribuzione fonti

---

## 1. Obiettivo

Creare un sistema di analisi marketing che:
- Scarica dati da Meta Ads (CSV) e Airtable
- Calcola metriche di costo (CPL, CPC, CPSU, CPCl)
- Calcola ROAS su Revenue e Cash con attribuzione corretta
- Genera report per 3 timeframe (1w, 2w, 28d)

---

## 2. Metodologia Attribuzione

### Fonti UTM
| UTM Source | Categoria | Attribuzione |
|------------|-----------|--------------|
| `meta`, `facebook`, `fb` | Meta | 100% ads |
| vuoto/null | Vuoto | 50% conservativo, 100% panoramico |
| `instagram`, `telegram`, altro | Altro | 0% ads (separato) |

### Calcolo Revenue/Cash (CORRETTO)
```python
# Somma DIRETTA per fonte, NON proporzionale!
for closure in closures:
    source = closure['UTM Fonte (source)']
    if source == 'meta':
        attr_revenue += closure['Revenue']      # 100%
        attr_cash += closure['Cash Collected']  # 100%
    elif source == '' or source is None:
        attr_revenue += closure['Revenue'] * 0.5  # 50%
        attr_cash += closure['Cash Collected'] * 0.5
```

### Date usate
- **Candidature**: `Data Creazione` (quando creata)
- **Calls**: `Data Call` (quando avviene la chiamata, NON quando prenotata)

---

## 3. Struttura File

```
LDP/
├── .env                    # API keys (AIRTABLE_API_KEY, AIRTABLE_BASE_ID)
├── .env.example            # Template
├── .gitignore
├── scripts/
│   ├── config.py           # Configurazione (carica .env)
│   ├── attribution.py      # Logica attribuzione fonti
│   ├── analyzer.py         # Motore analisi principale
│   ├── report_generator.py # Generatore report MD
│   ├── run_analysis.py     # Script runner CLI
│   └── data_loader.py      # Caricamento dati
├── data/
│   ├── candidature_with_source.json  # ~30k record
│   ├── calls_full.json               # ~8.6k record
│   └── meta_exports/
│       ├── 1w/   # Dec 8-14
│       ├── 2w/   # Dec 1-14
│       └── 28d/  # Nov 17 - Dec 14
│           ├── campaigns.csv
│           ├── adsets.csv
│           └── ads.csv
├── reports/
│   ├── LDP_Report_1w_2025-12-14.md
│   ├── LDP_Report_2w_2025-12-14.md
│   ├── LDP_Report_28d_2025-12-14.md
│   └── LDP_Comparison_2025-12-14.md
└── docs/
    └── METODOLOGIA_CALCOLI.md
```

---

## 4. Airtable Config

- **Base ID**: `app76iRKXL8w1NghG`
- **Candidature Table**: `tblqLo4QdlQZnJWTq`
- **Calls Table**: `tblW3PtC9Lf6SrA4l`

### Campi Calls importanti
- `Data Call` - quando avviene la chiamata
- `Data Creazione` - quando prenotata
- `Stato` - No Show, Chiuso, etc.
- `UTM Fonte (source)` - per attribuzione
- `Conta Chiusure` - 0/1
- `Revenue` - valore vendita
- `Cash Collected` - incassato effettivo

### Campi Candidature importanti
- `Data Creazione`
- `UTM Source`
- `UTM Medium` (= Ad Set name)
- `UTM Campaign`

---

## 5. Metriche Calcolate

| Metrica | Formula |
|---------|---------|
| CPL | Spesa / Candidature_attr |
| CPC | Spesa / Calls_attr |
| CPSU | Spesa / ShowUp_attr |
| CPCl | Spesa / Chiusure_attr |
| ROAS Revenue | Revenue_attr / Spesa |
| ROAS Cash | Cash_attr / Spesa |

---

## 6. Risultati Ultimi (con Data Call)

| Metrica | 1w | 2w | 28d |
|---------|-----|-----|-----|
| Spesa | €3,786 | €6,749 | €12,630 |
| Candidature | 527 | 939 | 1,923 |
| Calls | 133 | 285 | 502 |
| Chiusure (attr.) | 2 | 11 | 28 |
| ROAS Cash (attr.) | 0.49x | **1.53x** | **2.32x** |
| ROAS Cash (tot.) | 1.19x | **2.14x** | **3.02x** |

---

## 7. Uso Script

```bash
cd /home/null-runner/Projects/SynthOps/LDP/scripts

# Tutti i periodi
python3 run_analysis.py all

# Singolo periodo
python3 run_analysis.py 2w

# Con JSON output
python3 run_analysis.py all --json

# Refresh cache Airtable
python3 run_analysis.py all --refresh
```

---

## 8. Problemi Risolti

1. **Calcolo ROAS proporzionale** → Corretto con somma diretta per fonte
2. **Data Creazione per Calls** → Corretto con Data Call
3. **API key hardcoded** → Spostata in .env
4. **Mancanza ROAS totale** → Aggiunto sia attribuito che totale

---

## 9. Campagne Escluse

- `Future mamme`
- `Trading`

---

## 10. Prossimi Step Potenziali

- [ ] Aggiungere export PDF automatico
- [ ] Breakdown per Ad Set con ROAS
- [ ] Analisi trend temporale
- [ ] Integrazione diretta Meta API (serve token)
