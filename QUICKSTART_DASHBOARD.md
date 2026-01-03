# LDP Dashboard - Quick Start Guide

## ✅ Implementation Complete!

The LDP 360° Dashboard web app has been successfully implemented with the following features:

### Features
- 📊 **Complete funnel analysis** (Candidature → Calls → Show Up → Closures)
- 🎨 **Creative performance tracking** (CPL, CTR, retention)
- 👥 **Setter performance** (show-up rate, close rate)
- 💰 **Closer/Venditore performance** (close rate, ticket medio, revenue)
- 📈 **Historical trends** with period comparisons
- 🔐 **Authentication** (username/password with bcrypt)
- 💾 **Automatic backups** (Supabase daily backups)
- ✅ **User confirmation** required before saving analysis
- 🔍 **Debug/Audit section** for calculation transparency

## 📁 File Structure

```
LDP/
├── app/
│   ├── __init__.py
│   ├── analyzers.py          # Core analysis logic
│   ├── auth.py                # Authentication
│   ├── charts.py              # Plotly visualizations
│   ├── data_loader.py         # Multi-period detection + Airtable
│   ├── database.py            # Supabase PostgreSQL
│   └── ui_components.py       # Streamlit UI sections
├── streamlit_app.py           # Main entry point
├── requirements.txt           # Dependencies
├── .streamlit/
│   ├── config.toml            # Streamlit configuration
│   └── secrets.toml.template  # Secrets template
└── data/
    └── meta_exports/          # CSV uploads (gitignored)
```

## 🚀 Setup Instructions

### Step 1: Create Supabase Database (10 minutes)

1. Go to https://supabase.com and create free account
2. Create new project (choose closest region)
3. Wait ~2 minutes for provisioning

4. **Create database tables**: Go to SQL Editor and run this script:

```sql
-- Copy the CREATE TABLE statements from the plan:
-- /home/null-runner/.claude/plans/gleaming-humming-simon.md
-- Section: "Database Schema (Supabase PostgreSQL)"
```

5. **Get connection string**:
   - Project Settings > Database
   - Copy "Connection string" (Connection pooling mode)
   - Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
   - Save for secrets.toml

### Step 2: Configure Secrets

1. **Copy template**:
   ```bash
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   ```

2. **Generate password hash**:
   ```bash
   pip install streamlit-authenticator
   python3 -c "import streamlit_authenticator as stauth; print(stauth.Hasher(['your_chosen_password']).generate()[0])"
   ```

3. **Fill in secrets.toml**:
   ```toml
   [airtable]
   api_key = "YOUR_AIRTABLE_API_KEY"
   base_id = "YOUR_AIRTABLE_BASE_ID"

   [supabase]
   connection_string = "postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"

   [auth]
   username = "admin"
   name = "Admin LDP"
   password_hash = "$2b$12$..."  # Output from step 2
   cookie_name = "ldp_dashboard_auth"
   cookie_key = "RANDOM_32_CHAR_SECRET_KEY"  # Generate random string
   ```

### Step 3: Test Locally

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run locally**:
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Test the app**:
   - Login with credentials from secrets.toml
   - Upload test CSV files
   - Verify calculations match CLI version
   - Check database writes in Supabase dashboard

### Step 4: Deploy to Streamlit Cloud (5 minutes)

1. **Push to GitHub**:
   ```bash
   git add streamlit_app.py app/ requirements.txt .streamlit/config.toml
   git commit -m "feat: add LDP Dashboard web app"
   git push origin main
   ```

2. **Deploy**:
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"
   - Repository: `SynthOps/LDP`
   - Main file: `streamlit_app.py`
   - Click "Deploy"

3. **Configure secrets in Streamlit Cloud**:
   - Settings > Secrets
   - Paste entire contents of your local `secrets.toml`
   - Click "Save"

## 📖 Usage Guide

### Uploading Data

1. **Prepare CSV files** from Meta Ads Manager:
   - Export Ads, Ad Sets, and Campaigns
   - Filename should include dates: `...-Dec-1-2025-Dec-31-2025.csv`

2. **Upload in sidebar**:
   - Ads CSV
   - AdSets CSV
   - Campaigns CSV

3. **Select period** (auto-detected from filenames)

### Analyzing Data

1. **Dashboard tab**: View KPIs, funnel, creative/setter/closer performance
2. **Debug/Audit tab**: Verify calculations and CONFIRM to save
3. **Storico tab**: View trends and compare periods
4. **Parametri tab**: Modify thresholds (doesn't affect calculations)

### Saving Analysis

**IMPORTANT**: Analysis is NOT saved automatically!

1. Go to **Debug/Audit** tab
2. Review calculations
3. Click **"Conferma e Salva Analisi"**
4. If period exists, it will warn you before overwriting

## 🔒 Security Features

- ✅ Username/password authentication (bcrypt hashed)
- ✅ Session cookies (30-day expiry)
- ✅ Secrets never committed to git
- ✅ Database credentials encrypted in Streamlit Cloud

## 💾 Backup & Data Persistence

- **Automatic daily backups** via Supabase (7-day retention)
- **Manual backups**: Supabase Dashboard > Database > Backups > Download
- **Data organized by period**, not execution time
- **500MB free storage** = ~20 years of daily analyses

## 🆘 Troubleshooting

### "Failed to connect to Supabase"
- Check connection string in secrets.toml
- Verify password is correct
- Ensure Supabase project is active

### "Authentication failed"
- Verify password_hash was generated correctly
- Check username matches secrets.toml

### "Airtable error"
- Verify API key and base_id
- Check table names are exactly: `Candidature` and `Calls`

### "Period not detected"
- CSV filenames must include date range
- Format: `...-Month-Day-Year-Month-Day-Year.csv`
- Example: `Ads-Dec-1-2025-Dec-31-2025.csv`

## 📊 Cost Breakdown

| Service | Free Tier | Cost if Outgrown |
|---------|-----------|------------------|
| Supabase | 500MB, unlimited users | $25/month (8GB) |
| Streamlit Cloud | Public apps | $20/month/user (private apps) |
| **Total** | **€0/month** | **€45/month** (years from now) |

## 🎯 Next Steps

1. ✅ Complete setup steps above
2. Test locally with December data
3. Deploy to Streamlit Cloud
4. Share URL with team
5. Monitor Supabase storage usage

## 📝 Notes

- **CLI version still works**: `scripts/generate_dashboard.py`
- **Database vs File**: Supabase = permanent, CLI = one-time reports
- **Multi-period support**: Upload multiple periods, app detects them
- **Calculations**: Same logic as CLI (`complete_funnel_analysis_v2.py`)

---

**Need help?** Check the implementation plan:
`/home/null-runner/.claude/plans/gleaming-humming-simon.md`
