-- ========================================
-- LDP Dashboard - Supabase Database Schema
-- ========================================
-- ISTRUZIONI:
-- 1. Vai su https://supabase.com
-- 2. Crea nuovo progetto (o usa esistente)
-- 3. Vai su SQL Editor
-- 4. Copia e incolla questo intero script
-- 5. Clicca "Run" per creare tutte le tabelle
-- ========================================

-- Analysis runs table (tabella principale analisi)
CREATE TABLE IF NOT EXISTS analysis_runs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Meta ADS Data
    total_spend DECIMAL(10,2),
    impressions INTEGER,
    reach INTEGER,

    -- Funnel Metrics
    candidature INTEGER,
    calls INTEGER,
    show_ups INTEGER,
    closures INTEGER,

    -- Conversion Rates
    cand_to_call_rate DECIMAL(5,2),
    call_to_showup_rate DECIMAL(5,2),
    showup_to_close_rate DECIMAL(5,2),

    -- Revenue
    revenue DECIMAL(10,2),
    cash DECIMAL(10,2),
    ticket_medio DECIMAL(10,2),

    -- Cost Metrics
    cpl DECIMAL(10,2),
    cpc DECIMAL(10,2),
    cpsu DECIMAL(10,2),
    cpcl DECIMAL(10,2),

    -- ROAS
    roas_revenue DECIMAL(5,2),
    roas_cash DECIMAL(5,2),

    -- Unique constraint: una sola analisi per periodo
    UNIQUE(period_start, period_end)
);

-- Index for faster period queries
CREATE INDEX IF NOT EXISTS idx_period ON analysis_runs(period_start, period_end);

-- Creative performance table
CREATE TABLE IF NOT EXISTS creative_performance (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    creative_name TEXT NOT NULL,
    spend DECIMAL(10,2),
    leads INTEGER,
    cpl DECIMAL(10,2),
    ctr DECIMAL(5,2),
    impressions INTEGER,
    clicks INTEGER
);

CREATE INDEX IF NOT EXISTS idx_creative_period ON creative_performance(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_creative_run ON creative_performance(run_id);

-- Setter performance table
CREATE TABLE IF NOT EXISTS setter_performance (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    setter_name TEXT NOT NULL,
    calls INTEGER,
    show_ups INTEGER,
    closures INTEGER,
    no_shows INTEGER,
    show_up_rate DECIMAL(5,2),
    close_rate DECIMAL(5,2),
    revenue DECIMAL(10,2)
);

CREATE INDEX IF NOT EXISTS idx_setter_period ON setter_performance(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_setter_run ON setter_performance(run_id);

-- Closer performance table
CREATE TABLE IF NOT EXISTS closer_performance (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES analysis_runs(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    closer_name TEXT NOT NULL,
    show_ups INTEGER,
    closures INTEGER,
    scartati INTEGER,
    unclosable INTEGER,
    close_rate DECIMAL(5,2),
    revenue DECIMAL(10,2),
    ticket_medio DECIMAL(10,2)
);

CREATE INDEX IF NOT EXISTS idx_closer_period ON closer_performance(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_closer_run ON closer_performance(run_id);

-- ========================================
-- VERIFICA TABELLE CREATE
-- ========================================
-- Esegui questa query per verificare:
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
--
-- Dovresti vedere:
-- - analysis_runs
-- - creative_performance
-- - setter_performance
-- - closer_performance
-- ========================================

-- SUCCESS! Le tabelle sono state create.
-- Prossimi passi:
-- 1. Vai su Project Settings > Database
-- 2. Copia la "Connection string" (pooling mode)
-- 3. Incollala in .streamlit/secrets.toml nel campo connection_string
-- 4. Sostituisci [YOUR-PASSWORD] con la password del database
-- ========================================
