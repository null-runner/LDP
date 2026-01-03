# ✅ LDP Dashboard - Setup Checklist

## 🎉 Tutto Pronto per il Setup!

### Cosa è già fatto:
- ✅ App completa (12 file Python)
- ✅ Secrets.toml con credenziali Airtable
- ✅ Password predefinita: **ldp2025** (hash bcrypt già generato)
- ✅ SQL schema pronto per Supabase
- ✅ Tutti i file hanno sintassi Python valida
- ✅ Gitignore configurato (secrets.toml NON verrà committato)

---

## 🚀 Prossimi Passi (15 minuti totali)

### 1️⃣ Setup Supabase (10 minuti)

**A. Crea progetto** (2 minuti):
```
1. Vai su https://supabase.com
2. Login/Signup (gratuito)
3. "New project"
   - Nome: LDP-Dashboard
   - Password database: SCEGLI UNA PASSWORD FORTE (salvala!)
   - Region: Europe West (Ireland)
4. Aspetta 2 minuti per il provisioning
```

**B. Crea tabelle** (3 minuti):
```
1. Nella dashboard Supabase > SQL Editor
2. Apri il file: supabase_schema.sql
3. Copia TUTTO il contenuto
4. Incolla nel SQL Editor
5. Clicca "RUN"
6. Verifica output: "Success! 4 tabelle create"
```

**C. Copia connection string** (2 minuti):
```
1. Supabase > Project Settings (icona ingranaggio)
2. Database (menu a sinistra)
3. Scroll fino a "Connection string"
4. Seleziona "Connection pooling" (NON Session mode!)
5. Copia la stringa (es: postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres)
6. Sostituisci [YOUR-PASSWORD] con la password che hai scelto al punto A
```

**D. Aggiorna secrets.toml** (1 minuto):
```
1. Apri: .streamlit/secrets.toml
2. Trova la riga: connection_string = "PLACEHOLDER_SETUP_SUPABASE_FIRST"
3. Sostituisci con la connection string del punto C
4. Salva il file
```

**E. Verifica backup automatici** (1 minuto):
```
1. Supabase > Database > Backups
2. Dovresti vedere: "Daily backups enabled" ✅
```

---

### 2️⃣ Test Locale (5 minuti)

**A. Installa dipendenze**:
```bash
cd /home/null-runner/Projects/SynthOps/LDP
pip install -r requirements.txt
```

**B. Avvia app**:
```bash
streamlit run streamlit_app.py
```

**C. Testa login**:
```
1. Browser si apre automaticamente
2. Username: admin
3. Password: ldp2025
4. Dovresti vedere la dashboard
```

**D. Testa upload**:
```
1. Carica 3 CSV dalla sidebar:
   - Ads CSV
   - AdSets CSV
   - Campaigns CSV
2. Seleziona periodo (auto-rilevato)
3. Verifica che mostri le analisi
4. Vai su "Debug/Audit" tab
5. Clicca "Conferma e Salva Analisi"
6. Se non ci sono errori = SUCCESSO!
```

---

### 3️⃣ Deploy su Streamlit Cloud (OPZIONALE)

**A. Push su GitHub**:
```bash
git add streamlit_app.py app/ requirements.txt .streamlit/config.toml QUICKSTART_DASHBOARD.md
git commit -m "feat: add LDP Dashboard web app with Supabase"
git push origin main
```

**B. Deploy**:
```
1. Vai su https://share.streamlit.io
2. Login con GitHub
3. "New app"
4. Repository: SynthOps/LDP
5. Main file: streamlit_app.py
6. "Deploy"
```

**C. Configura secrets cloud**:
```
1. Nella dashboard Streamlit Cloud > Settings > Secrets
2. Copia TUTTO il contenuto di .streamlit/secrets.toml
3. Incolla
4. Save
```

---

## 🔐 Credenziali Predefinite

| Campo | Valore | Nota |
|-------|--------|------|
| **Username** | admin | Puoi cambiare in secrets.toml |
| **Password** | ldp2025 | CAMBIALA dopo il primo login! |
| **Airtable API** | Già configurato | Trovato nel .env esistente |
| **Supabase** | DA CONFIGURARE | Segui Step 1 |

---

## 📊 Come Usare la Dashboard

1. **Login** con admin/ldp2025
2. **Carica CSV** nella sidebar
3. **Visualizza analisi** nel tab Dashboard
4. **Verifica calcoli** nel tab Debug/Audit
5. **Conferma salvataggio** (bottone verde)
6. **Vedi storico** nel tab Storico

---

## ❓ Troubleshooting

### "Failed to connect to Supabase"
→ Controlla che la connection_string in secrets.toml sia corretta

### "Authentication failed"
→ Username: admin, Password: ldp2025 (esattamente così, minuscolo)

### "Period not detected"
→ Il nome del CSV deve contenere date tipo: Ads-Dec-1-2025-Dec-31-2025.csv

### "Airtable error"
→ Le credenziali sono corrette, controlla che le tabelle si chiamino esattamente:
   - "Candidature"
   - "Calls"

---

## 📝 File Importanti

| File | Scopo |
|------|-------|
| `streamlit_app.py` | Entry point principale |
| `.streamlit/secrets.toml` | Credenziali (MAI committare!) |
| `supabase_schema.sql` | SQL da eseguire su Supabase |
| `QUICKSTART_DASHBOARD.md` | Documentazione completa |
| `requirements.txt` | Dipendenze Python |

---

## 🎯 Prossimi Step Dopo Setup

1. ✅ Testa con dati di Dicembre
2. Cambia password predefinita
3. Invita team members (se deploy su cloud)
4. Configura backup schedule su Supabase (già automatico)
5. Monitora storage usage (500MB free = 20+ anni)

---

**Hai finito? Testa ora con:**
```bash
streamlit run streamlit_app.py
```

**Domande? Controlla:**
- QUICKSTART_DASHBOARD.md (documentazione estesa)
- /home/null-runner/.claude/plans/gleaming-humming-simon.md (piano tecnico completo)
