# LDP - Metodologia Calcoli Marketing

## 1. Fonti Dati

### 1.1 Dati ADS (Meta Ads Manager)
- **Fonte**: Export CSV da Meta Ads Manager
- **Gerarchia**: Campaign → Ad Set → Ad

| File | Livello | Campi Chiave | Mapping Airtable |
|------|---------|--------------|------------------|
| `campaigns_dec_2025.csv` | Campaign | Campaign Name, Amount Spent | - |
| `ads_dec_2025.csv` | Ad Set | Ad Set Name, Amount Spent | UTM Medium |
| `ads_detail_dec_2025.csv` | Ad | Ad Name, Amount Spent | UTM Content |

### 1.2 Dati Commerciali (Airtable)
- **Fonte**: Tabelle Candidature e Calls
- **Campi chiave**:
  - Candidature: UTM Source, UTM Medium, UTM Campaign, Data Creazione
  - Calls: UTM Source, UTM Medium, Show Up, Stato Contatto, Importo Chiusura

---

## 2. Metodologia Attribuzione

### 2.1 Regola Base
L'attribuzione ai costi pubblicitari si basa sul campo `UTM Source`:

| UTM Source | Attribuzione ADS | Note |
|------------|------------------|------|
| `meta` | 100% | Traffico diretto da Meta Ads |
| `vuoto/null` | 50% o 100% | Traffico probabilmente da ads (tracking perso) |
| `instagram` | 0% | Traffico organico IG |
| `telegram` | 0% | Traffico organico TG |
| Altre fonti | 0% | Traffico non ads |

### 2.2 Le Tre Viste

#### Vista 1: Conservativa (Meta + 50% Vuote)
```
Conteggio = (record con source="meta") + ceil((record con source vuoto) / 2)
```
- Usata per: **Calcoli costi realistici**
- Arrotondamento: Per eccesso (ceil)

#### Vista 2: Panoramica (Meta + 100% Vuote)
```
Conteggio = (record con source="meta") + (record con source vuoto)
```
- Usata per: **Visione massima del traffico ads**

#### Vista 3: Altre Fonti (Separata)
```
Conteggio per fonte = raggruppamento per UTM Source (esclusi meta e vuoto)
```
- Usata per: **Analisi canali organici**
- Non attribuita ai costi ads

---

## 3. Metriche Calcolate

### 3.1 Funnel Marketing

```
OPTIN → CANDIDATURA → CALL → SHOW UP → CHIUSURA
```

### 3.2 Formule Costi

| Metrica | Formula | Significato |
|---------|---------|-------------|
| **CPL** | Spesa / Candidature | Costo per Lead (candidatura) |
| **CPC** | Spesa / Calls | Costo per Call prenotata |
| **CPSU** | Spesa / Show Up | Costo per Show Up |
| **CPCl** | Spesa / Chiusure | Costo per Chiusura (vendita) |

### 3.3 Formule Performance

| Metrica | Formula | Significato |
|---------|---------|-------------|
| **ROAS** | Revenue / Spesa | Return On Ad Spend |
| **Tasso Show Up** | Show Up / Calls × 100 | % che si presenta |
| **Tasso Chiusura** | Chiusure / Show Up × 100 | % che compra |
| **Tasso Conversione** | Chiusure / Candidature × 100 | % conversione totale |

---

## 4. Filtri Standard

### 4.1 Periodo
- Filtro su `Data Creazione` delle Candidature
- Formato: YYYY-MM-DD

### 4.2 Esclusioni Campagne
- `Future mamme` - campagna esclusa
- `Trading` - campagna esclusa (prodotto diverso)

### 4.3 Matching ADS ↔ Airtable
- Join su: `Ad Set Name` (ADS) = `UTM Medium` (Airtable)
- Nota: I nomi possono essere troncati nel CSV

---

## 5. Flusso Calcolo

```
1. Carica dati ADS (CSV) → dizionario {adset: spesa}
2. Carica Candidature (JSON) → filtra per data e campagna
3. Carica Calls (JSON) → filtra per data e campagna
4. Per ogni record:
   a. Categorizza UTM Source (meta/vuoto/altro)
   b. Estrai UTM Medium (adset)
5. Aggrega per adset:
   a. Vista 1: meta + ceil(vuoto/2)
   b. Vista 2: meta + vuoto
   c. Vista 3: altre fonti separate
6. Calcola metriche per adset
7. Calcola totali
```

---

## 6. Output Report

### 6.1 Sezioni Report
1. **Riepilogo Totale** - Vista 1 (Conservativa)
2. **Riepilogo Totale** - Vista 2 (Panoramica)
3. **Altre Fonti** - Vista 3 (Non ADS)
4. **Dettaglio per Ad Set** - Breakdown per creativa

### 6.2 Formati
- Markdown (.md) - per revisione
- PDF - per condivisione

---

*Documentazione creata: 16/12/2025*
*Progetto: LDP Marketing Analysis*
