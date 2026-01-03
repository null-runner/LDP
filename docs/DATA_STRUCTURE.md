# LDP Data Structure Documentation

**Ultimo aggiornamento:** 2025-12-17

---

## 1. Overview

Il sistema utilizza due fonti dati principali:
- **Airtable**: Dati CRM (Candidature + Calls)
- **Meta Ads Export**: Dati pubblicitari (CSV)

### Join Logic
```
Airtable.UTM Campaign  ↔  Meta.Campaign name
Airtable.UTM Medium    ↔  Meta.Ad set name
Airtable.UTM Source    →  Attribuzione (meta/vuoto/altro)
```

---

## 2. CALLS (Airtable)

**Totale record:** ~8,673
**Tabella ID:** `tblW3PtC9Lf6SrA4l`

| Campo | Tipo | Fill Rate | Descrizione |
|-------|------|-----------|-------------|
| `Data Creazione` | datetime | 100% | Quando la call è stata prenotata |
| `Data Call` | datetime | 98.8% | Quando la call è avvenuta |
| `Stato` | string | 100% | Stato della call (No Show, Chiuso, etc.) |
| `UTM Fonte (source)` | string | 81.4% | Fonte UTM per attribuzione |
| `UTM Adset (medium)` | string | 41% | Nome AdSet per join con Meta |
| `UTM Campagna (campaign)` | string | 40.6% | Nome Campagna per join con Meta |
| `Conta Chiusure` | int | 100% | 0 o 1 - indica se chiusura |
| `Conta No Show` | int | 100% | 0 o 1 - indica se no show |
| `Show Up` | bool | 30.5% | True se si è presentato |
| `Revenue` | float | 15.3% | Valore vendita (solo se chiusura) |
| `Cash Collected` | float | 15.1% | Incassato effettivo |

### Stati possibili
- `No Show` - Non si è presentato
- `Chiuso` - Vendita effettuata
- `Non Chiuso` - Presentato ma non ha comprato
- `Scartato` - Lead non qualificato
- `Cancellato` - Call cancellata

### Calcolo LAG
```python
LAG = Data Call - Data Creazione  # in giorni
```

---

## 3. CANDIDATURE (Airtable)

**Totale record:** ~30,349
**Tabella ID:** `tblqLo4QdlQZnJWTq`

| Campo | Tipo | Fill Rate | Descrizione |
|-------|------|-----------|-------------|
| `Data Creazione` | datetime | 100% | Quando il lead è stato creato |
| `UTM Source` | string | 90.4% | Fonte per attribuzione |
| `UTM Campaign` | string | 74% | Nome campagna per join |
| `UTM Medium` | string | 74.3% | Nome AdSet per join |
| `Stato Contatto` | string | 99.4% | Stato del contatto |

### Stati Contatto
- `Autonomo`
- `Mai Risposto`
- `Contatto`
- `No Call`
- etc.

---

## 4. META ADS CSV

### 4.1 Campaigns
| Campo | Descrizione |
|-------|-------------|
| `Campaign name` | Nome campagna (per join) |
| `Amount spent (EUR)` | Spesa totale |
| `Impressions` | Impressioni |
| `Reach` | Copertura unica |
| `Leads` | Lead generati (pixel) |
| `Results` | Conversioni |
| `Reporting starts` | Data inizio report |
| `Reporting ends` | Data fine report |

### 4.2 Ad Sets
| Campo | Descrizione |
|-------|-------------|
| `Ad set name` | Nome AdSet (per join con UTM Medium) |
| `Campaign name` | Campagna parent |
| `Amount spent (EUR)` | Spesa AdSet |
| `Leads` | Lead generati |
| `Cost per lead (EUR)` | CPL |

### 4.3 Ads
| Campo | Descrizione |
|-------|-------------|
| `Ad name` | Nome Ad |
| `Ad set name` | AdSet parent |
| `Campaign name` | Campagna parent |
| `Amount spent (EUR)` | Spesa Ad |

---

## 5. Attribuzione Fonti

### Logica di categorizzazione
```python
if source in ['meta', 'facebook', 'fb']:
    return 'meta'      # 100% attribuito
elif source == '' or source is None:
    return 'vuoto'     # 50% conservativo, 100% panoramico
else:
    return 'altro'     # 0% ads (es. instagram, telegram)
```

### Modi di attribuzione
1. **Conservativo**: Meta 100% + Vuoto 50%
2. **Panoramico**: Meta 100% + Vuoto 100%

---

## 6. Struttura Directory

```
LDP/
├── data/
│   ├── candidature_with_source.json  # Export Airtable
│   ├── calls_full.json               # Export Airtable
│   └── meta_exports/
│       ├── 1w/                        # Ultima settimana
│       │   ├── campaigns.csv
│       │   ├── adsets.csv
│       │   └── ads.csv
│       ├── 2w/                        # Ultime 2 settimane
│       └── 28d/                       # Ultimi 28 giorni
├── scripts/
│   ├── config.py
│   ├── data_loader.py
│   ├── attribution.py
│   ├── analyzer.py
│   ├── projection_engine.py          # NUOVO - Proiezioni avanzate
│   ├── report_generator.py
│   └── run_analysis.py
└── reports/
    └── *.md
```

---

## 7. Metriche Chiave

### Funnel Metrics
| Metrica | Formula |
|---------|---------|
| CPL | Spesa / Candidature |
| CPC | Spesa / Calls |
| CPSU | Spesa / Show Ups |
| CPCl | Spesa / Chiusure |

### Rate Metrics
| Metrica | Formula |
|---------|---------|
| Call Rate | Calls / Candidature |
| Show Rate | Show Ups / Calls |
| Close Rate | Chiusure / Show Ups |

### Revenue Metrics
| Metrica | Formula |
|---------|---------|
| ROAS Revenue | Revenue / Spesa |
| ROAS Cash | Cash Collected / Spesa |
| AOV (Ticket Medio) | Revenue / Chiusure |

---

## 8. Note Importanti

1. **Data Creazione vs Data Call**: Usa SEMPRE Data Creazione per l'attribuzione (cohort analysis)

2. **Finestra Maturazione**: Attendere ~7 giorni dopo fine periodo per dati completi

3. **Campagne Escluse**:
   - `Future mamme`
   - `Trading`

4. **UTM Tracking Gap**: ~19% delle calls non ha UTM Source (attribuzione incerta)
