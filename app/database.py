"""
Database Module for LDP Dashboard
Handles Supabase PostgreSQL connection and historical data storage
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import streamlit as st


def get_supabase_connection():
    """
    Get connection to Supabase PostgreSQL.
    Uses connection string from st.secrets.

    Returns:
        psycopg2 connection object
    """
    try:
        return psycopg2.connect(
            st.secrets["supabase"]["connection_string"],
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        raise


def init_database():
    """
    Create tables if not exist.
    Run once on first deployment.
    """
    schema_sql = """
    -- Analysis runs table
    CREATE TABLE IF NOT EXISTS analysis_runs (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        period_start DATE NOT NULL,
        period_end DATE NOT NULL,

        total_spend DECIMAL(10,2),
        impressions INTEGER,
        reach INTEGER,

        candidature INTEGER,
        calls INTEGER,
        show_ups INTEGER,
        closures INTEGER,

        cand_to_call_rate DECIMAL(5,2),
        call_to_showup_rate DECIMAL(5,2),
        showup_to_close_rate DECIMAL(5,2),

        revenue DECIMAL(10,2),
        cash DECIMAL(10,2),
        ticket_medio DECIMAL(10,2),

        cpl DECIMAL(10,2),
        cpc DECIMAL(10,2),
        cpsu DECIMAL(10,2),
        cpcl DECIMAL(10,2),

        roas_revenue DECIMAL(5,2),
        roas_cash DECIMAL(5,2),

        UNIQUE(period_start, period_end)
    );

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
    """

    try:
        conn = get_supabase_connection()
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Failed to initialize database: {e}")
        return False


def save_analysis_run(period_start, period_end, funnel_data, creative_data, setter_data, closer_data):
    """
    Save complete analysis to database using UPSERT.
    Overwrites existing record for same period if user confirmed.

    Args:
        period_start: Date string (YYYY-MM-DD)
        period_end: Date string (YYYY-MM-DD)
        funnel_data: Dict from analyze_funnel()
        creative_data: List from analyze_creative()
        setter_data: Dict from analyze_setters()
        closer_data: Dict from analyze_closers()

    Returns:
        run_id or None if failed
    """
    try:
        conn = get_supabase_connection()
        cursor = conn.cursor()

        # Upsert main analysis run
        cursor.execute("""
            INSERT INTO analysis_runs (
                period_start, period_end, total_spend, impressions, reach,
                candidature, calls, show_ups, closures,
                cand_to_call_rate, call_to_showup_rate, showup_to_close_rate,
                revenue, cash, ticket_medio,
                cpl, cpc, cpsu, cpcl,
                roas_revenue, roas_cash
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (period_start, period_end)
            DO UPDATE SET
                updated_at = NOW(),
                total_spend = EXCLUDED.total_spend,
                impressions = EXCLUDED.impressions,
                reach = EXCLUDED.reach,
                candidature = EXCLUDED.candidature,
                calls = EXCLUDED.calls,
                show_ups = EXCLUDED.show_ups,
                closures = EXCLUDED.closures,
                cand_to_call_rate = EXCLUDED.cand_to_call_rate,
                call_to_showup_rate = EXCLUDED.call_to_showup_rate,
                showup_to_close_rate = EXCLUDED.showup_to_close_rate,
                revenue = EXCLUDED.revenue,
                cash = EXCLUDED.cash,
                ticket_medio = EXCLUDED.ticket_medio,
                cpl = EXCLUDED.cpl,
                cpc = EXCLUDED.cpc,
                cpsu = EXCLUDED.cpsu,
                cpcl = EXCLUDED.cpcl,
                roas_revenue = EXCLUDED.roas_revenue,
                roas_cash = EXCLUDED.roas_cash
            RETURNING id
        """, (
            period_start, period_end, funnel_data.get('total_spend', 0), 0, 0,
            funnel_data.get('candidature', 0), funnel_data.get('calls', 0),
            funnel_data.get('show_ups', 0), funnel_data.get('closures', 0),
            funnel_data.get('cand_to_call_rate', 0), funnel_data.get('call_to_showup_rate', 0),
            funnel_data.get('showup_to_close_rate', 0),
            funnel_data.get('revenue', 0), funnel_data.get('cash', 0),
            funnel_data.get('ticket_medio', 0),
            funnel_data.get('cpl', 0), funnel_data.get('cpc', 0),
            funnel_data.get('cpsu', 0), funnel_data.get('cpcl', 0),
            funnel_data.get('roas_revenue', 0), funnel_data.get('roas_cash', 0)
        ))

        run_id = cursor.fetchone()['id']

        # Delete old creative/setter/closer data for this run
        cursor.execute("DELETE FROM creative_performance WHERE run_id = %s", (run_id,))
        cursor.execute("DELETE FROM setter_performance WHERE run_id = %s", (run_id,))
        cursor.execute("DELETE FROM closer_performance WHERE run_id = %s", (run_id,))

        # Insert creative performance (top 50 only to save space)
        creative_values = []
        for creative in sorted(creative_data, key=lambda x: x.get('cpl', 999999))[:50]:
            creative_values.append((
                run_id, period_start, period_end,
                creative.get('name', 'Unknown'),
                creative.get('spend', 0),
                creative.get('leads', 0),
                creative.get('cpl', 0),
                creative.get('ctr', 0),
                creative.get('impressions', 0),
                creative.get('clicks', 0)
            ))

        if creative_values:
            execute_values(cursor, """
                INSERT INTO creative_performance (
                    run_id, period_start, period_end, creative_name,
                    spend, leads, cpl, ctr, impressions, clicks
                ) VALUES %s
            """, creative_values)

        # Insert setter performance
        setter_values = []
        for setter_name, stats in setter_data.items():
            setter_values.append((
                run_id, period_start, period_end, setter_name,
                stats.get('calls', 0),
                stats.get('show_ups', 0),
                stats.get('closures', 0),
                stats.get('no_shows', 0),
                stats.get('show_up_rate', 0),
                stats.get('close_rate', 0),
                stats.get('revenue', 0)
            ))

        if setter_values:
            execute_values(cursor, """
                INSERT INTO setter_performance (
                    run_id, period_start, period_end, setter_name,
                    calls, show_ups, closures, no_shows,
                    show_up_rate, close_rate, revenue
                ) VALUES %s
            """, setter_values)

        # Insert closer performance
        closer_values = []
        for closer_name, stats in closer_data.items():
            if closer_name != 'Unassigned':  # Skip unassigned
                closer_values.append((
                    run_id, period_start, period_end, closer_name,
                    stats.get('show_ups', 0),
                    stats.get('closures', 0),
                    stats.get('scartati', 0),
                    stats.get('unclosable', 0),
                    stats.get('close_rate', 0),
                    stats.get('revenue', 0),
                    stats.get('ticket_medio', 0)
                ))

        if closer_values:
            execute_values(cursor, """
                INSERT INTO closer_performance (
                    run_id, period_start, period_end, closer_name,
                    show_ups, closures, scartati, unclosable,
                    close_rate, revenue, ticket_medio
                ) VALUES %s
            """, closer_values)

        conn.commit()
        conn.close()

        return run_id

    except Exception as e:
        st.error(f"Failed to save analysis: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return None


def check_period_exists(period_start, period_end):
    """
    Check if an analysis for this period already exists.

    Args:
        period_start: Date string (YYYY-MM-DD)
        period_end: Date string (YYYY-MM-DD)

    Returns:
        Dict with existing record or None
    """
    try:
        conn = get_supabase_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, created_at, updated_at FROM analysis_runs
            WHERE period_start = %s AND period_end = %s
        """, (period_start, period_end))

        result = cursor.fetchone()
        conn.close()

        return result

    except Exception as e:
        st.error(f"Failed to check period: {e}")
        return None


def get_historical_runs(limit=10):
    """
    Fetch recent analysis runs for trend comparison.
    Ordered by period_end DESC.

    Args:
        limit: Max number of runs to return

    Returns:
        List of run records
    """
    try:
        conn = get_supabase_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM analysis_runs
            ORDER BY period_end DESC
            LIMIT %s
        """, (limit,))

        runs = cursor.fetchall()
        conn.close()

        return runs

    except Exception as e:
        st.error(f"Failed to fetch historical runs: {e}")
        return []


def get_period_comparison(period_start_1, period_end_1, period_start_2, period_end_2):
    """
    Compare two periods side-by-side.

    Args:
        period_start_1, period_end_1: First period dates
        period_start_2, period_end_2: Second period dates

    Returns:
        Dict with both periods' metrics
    """
    try:
        conn = get_supabase_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM analysis_runs
            WHERE (period_start = %s AND period_end = %s)
               OR (period_start = %s AND period_end = %s)
            ORDER BY period_start
        """, (period_start_1, period_end_1, period_start_2, period_end_2))

        periods = cursor.fetchall()
        conn.close()

        return {
            'period_1': periods[0] if len(periods) > 0 else None,
            'period_2': periods[1] if len(periods) > 1 else None
        }

    except Exception as e:
        st.error(f"Failed to compare periods: {e}")
        return {'period_1': None, 'period_2': None}
