# TODO - LDP Dashboard

## ✅ Completato Oggi (2026-01-03)

- ✅ Setup Streamlit web app
- ✅ Integrazione Supabase PostgreSQL (database cloud)
- ✅ Autenticazione con streamlit-authenticator (username/password)
- ✅ Upload CSV Multi-periodo con auto-detection date
- ✅ Cache Airtable giornaliera (24h)
- ✅ Nessun dato salvato su disco (solo RAM + Supabase)
- ✅ Repository pubblico senza dati sensibili
- ✅ Deploy su Streamlit Cloud
- ✅ Fix compatibilità Python 3.13
- ✅ Update API streamlit-authenticator 0.4.2
- ✅ Font più grandi nel grafico funnel
- ✅ Tooltip spiegazione metriche funnel

---

## 🔴 DA FARE - Priorità Alta

### 1. Verifica Calcoli
**Obiettivo**: Assicurarsi che tutti i calcoli siano corretti e accurati

**Task**:
- [ ] Testare calcolo funnel con dati noti
  - [ ] Candidature → Calls conversion
  - [ ] Calls → Show Up conversion
  - [ ] Show Up → Closures conversion
- [ ] Verificare CPL (Cost Per Lead)
  - [ ] Formula: Total Spend / Candidature
  - [ ] Confrontare con calcoli manuali
- [ ] Verificare ROAS (Return on Ad Spend)
  - [ ] ROAS Revenue: Revenue / Spend
  - [ ] ROAS Cash: Cash / Spend
- [ ] Verificare Ticket Medio
  - [ ] Formula: Revenue / Closures
- [ ] Testare calcoli Creative Performance
  - [ ] CPL per creative
  - [ ] CTR per creative
- [ ] Testare calcoli Setter Performance
  - [ ] Show up rate
  - [ ] Close rate
- [ ] Testare calcoli Closer Performance
  - [ ] Close rate
  - [ ] Revenue per closer

**Come testare**:
1. Caricare CSV con dati noti
2. Calcolare manualmente le metriche attese (Excel/Google Sheets)
3. Confrontare risultati app vs calcoli manuali
4. Documentare discrepanze

---

### 2. Test Sistema Completo
**Obiettivo**: Testare ogni funzionalità end-to-end

**Task**:
- [ ] Test Upload CSV
  - [ ] File singolo periodo
  - [ ] File multi-periodo
  - [ ] Errore file corrotto/formato sbagliato
- [ ] Test Airtable Integration
  - [ ] Refresh dati
  - [ ] Cache funzionante (non riscarica se stesso giorno)
  - [ ] Gestione errori API
- [ ] Test Supabase Database
  - [ ] Salvataggio analisi
  - [ ] Conferma sovrascrittura periodo esistente
  - [ ] Visualizzazione storico
  - [ ] Query period comparison
- [ ] Test Autenticazione
  - [ ] Login corretto
  - [ ] Login errato (password sbagliata)
  - [ ] Logout
  - [ ] Session persistence
- [ ] Test UI/UX
  - [ ] Tutti i grafici visualizzano correttamente
  - [ ] Tooltip e help funzionano
  - [ ] Responsive design (mobile/tablet)

---

### 3. Messa Online (Produzione)
**Obiettivo**: Deploy stabile e sicuro

**Task**:
- [ ] Verifica deployment Streamlit Cloud
  - [ ] App accessibile pubblicamente
  - [ ] Secrets configurati correttamente
  - [ ] Nessun errore nei log
- [ ] Sicurezza
  - [ ] Cambiare password default `ldp2025`
  - [ ] Verificare che secrets.toml non sia committato
  - [ ] Test login con collaboratori
- [ ] Documentazione
  - [ ] Aggiornare QUICKSTART_DASHBOARD.md
  - [ ] Creare video/screenshot tutorial
  - [ ] Documentare workflow: Upload → Analisi → Conferma → Storico
- [ ] Performance
  - [ ] Test con CSV grandi (>50MB)
  - [ ] Verificare tempi di caricamento
  - [ ] Ottimizzare query Supabase se lente
- [ ] Backup
  - [ ] Verificare backup automatici Supabase attivi
  - [ ] Test restore da backup

---

## 🟡 DA FARE - Priorità Media

- [ ] Aggiungere filtri avanzati (per creative, setter, closer)
- [ ] Export risultati analisi in PDF/Excel
- [ ] Grafici trend multi-periodo (comparazione)
- [ ] Notifiche email quando ROAS < threshold
- [ ] Dashboard mobile-ottimizzata
- [ ] Multi-utente (più account con ruoli diversi)

---

## 🟢 DA FARE - Priorità Bassa (Nice to Have)

- [ ] Dark mode
- [ ] Personalizzazione tema colori
- [ ] Logo personalizzato
- [ ] Grafici real-time (aggiornamento automatico)
- [ ] API REST per integrazioni esterne
- [ ] Webhooks per eventi (nuova analisi salvata, etc.)

---

## 📝 Note Tecniche

### Stack Attuale
- **Frontend**: Streamlit 1.40+
- **Database**: Supabase PostgreSQL (500MB free tier)
- **Auth**: streamlit-authenticator 0.4.2
- **Charts**: Plotly 5.24+
- **Data**: Pandas 2.2+
- **Deploy**: Streamlit Cloud (free tier)
- **Python**: 3.13.9

### Workflow Dati
1. User carica CSV → **solo RAM** (mai disco)
2. Airtable scaricato → **cache 24h in Streamlit session state**
3. Analisi eseguita → **risultati mostrati in UI**
4. User conferma → **solo risultati salvati in Supabase**
5. CSV/JSON Airtable → **mai salvati permanentemente**

### Credenziali Produzione
- Username: `admin`
- Password: `ldp2025` ⚠️ **DA CAMBIARE**
- Supabase: `aws-1-eu-central-1.pooler.supabase.com:6543`
- Airtable: Base `app76iRKXL8w1NghG`

---

**Ultimo aggiornamento**: 2026-01-03
**Prossimo checkpoint**: Dopo verifica calcoli e test completo
