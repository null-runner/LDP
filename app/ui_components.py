"""
UI Components for LDP Dashboard
Streamlit-based interface sections
"""
import streamlit as st
import pandas as pd
from app.data_loader import detect_periods_from_filenames
from app.database import check_period_exists, save_analysis_run, get_historical_runs, get_period_comparison
from app.charts import create_funnel_chart, create_creative_performance_chart, create_setter_performance_chart, create_closer_performance_chart, create_trend_chart
from app.analyzers import SHOW_UP_STATES, CLOSED_STATES


def render_sidebar():
    """
    Render sidebar with file upload and period selection.

    Returns:
        Tuple: (uploaded_files, selected_period, params)
    """
    with st.sidebar:
        st.header("📂 Carica Dati")

        # CSV File Upload
        ads_file = st.file_uploader("Ads CSV", type=['csv'], key='ads')
        adsets_file = st.file_uploader("AdSets CSV", type=['csv'], key='adsets')
        campaigns_file = st.file_uploader("Campaigns CSV", type=['csv'], key='campaigns')

        uploaded_files = {
            'ads': ads_file,
            'adsets': adsets_file,
            'campaigns': campaigns_file
        }

        # Detect periods from filenames
        periods = []
        if any(uploaded_files.values()):
            periods = detect_periods_from_filenames(uploaded_files)

        selected_period = None
        if periods:
            st.success(f"✅ Rilevati {len(periods)} periodi")

            # Period selector
            period_labels = [p['label'] for p in periods]
            selected_label = st.selectbox("Seleziona Periodo", period_labels)

            # Find selected period
            for p in periods:
                if p['label'] == selected_label:
                    selected_period = p
                    break

            st.info(f"Periodo: {selected_period['start']} → {selected_period['end']}")
        else:
            st.warning("Carica i file CSV per iniziare")

        st.divider()

        # Parameters
        st.header("⚙️ Parametri")

        params = {
            'show_up_threshold': st.slider("Target Show Up Rate (%)", 0, 100, 50),
            'close_rate_threshold': st.slider("Target Close Rate (%)", 0, 100, 20),
            'cpl_target': st.number_input("Target CPL (€)", min_value=0.0, value=10.0, step=0.5),
            'roas_minimum': st.number_input("ROAS Minimo", min_value=0.0, value=2.0, step=0.1)
        }

    return uploaded_files, selected_period, params


def render_main_dashboard(period_data, funnel, creative, setters, closers):
    """
    Render main dashboard with KPIs and visualizations.

    Args:
        period_data: Dict with filtered data
        funnel: Dict from analyze_funnel()
        creative: List from analyze_creative()
        setters: Dict from analyze_setters()
        closers: Dict from analyze_closers()
    """
    st.header("📊 Dashboard Principale")

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "ROAS Cash",
            f"{funnel.get('roas_cash', 0):.2f}x",
            help="Return on Ad Spend (Cash)"
        )

    with col2:
        st.metric(
            "CPL",
            f"€{funnel.get('cpl', 0):.2f}",
            help="Cost Per Lead"
        )

    with col3:
        st.metric(
            "Show Up Rate",
            f"{funnel.get('call_to_showup_rate', 0):.1f}%",
            help="Percentuale di show-up sulle call"
        )

    with col4:
        st.metric(
            "Close Rate",
            f"{funnel.get('showup_to_close_rate', 0):.1f}%",
            help="Percentuale di chiusura sugli show-up"
        )

    st.divider()

    # Funnel Visualization
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Funnel Conversione")
        fig = create_funnel_chart(funnel)
        st.plotly_chart(fig, use_container_width=True)

        # Spiegazione metriche funnel
        with st.expander("ℹ️ Cosa significano le percentuali?"):
            st.markdown("""
            **% of initial** (% del totale iniziale)
            - Percentuale rispetto alle Candidature iniziali
            - Esempio: 30 Show Up su 100 Candidature = 30% of initial
            - Utile per: Capire quante persone arrivano fino a quel punto dall'inizio

            **% of previous** (% dello step precedente)
            - Percentuale rispetto allo step immediatamente prima
            - Esempio: 30 Show Up su 50 Calls = 60% of previous
            - Utile per: **Conversion rate tra step consecutivi** (dove perdi più gente)

            **% of total** (% del totale)
            - Uguale a "% of initial"
            - Percentuale sul totale delle Candidature iniziali
            """)

    with col2:
        st.subheader("Metriche Chiave")
        st.metric("Candidature", f"{funnel.get('candidature', 0):,}")
        st.metric("Calls", f"{funnel.get('calls', 0):,}")
        st.metric("Show Up", f"{funnel.get('show_ups', 0):,}")
        st.metric("Chiusure", f"{funnel.get('closures', 0):,}")
        st.metric("Revenue", f"€{funnel.get('revenue', 0):,.2f}")
        st.metric("Ticket Medio", f"€{funnel.get('ticket_medio', 0):,.2f}")

    st.divider()

    # Creative Performance
    st.subheader("🎨 Performance Creative")
    if creative:
        fig = create_creative_performance_chart(creative, top_n=10)
        st.plotly_chart(fig, use_container_width=True)

        # Top/Worst tables
        col1, col2 = st.columns(2)

        with col1:
            st.caption("Top 5 per CPL")
            top_5 = sorted(creative, key=lambda x: x.get('cpl', 999999))[:5]
            df = pd.DataFrame(top_5)[['name', 'cpl', 'leads', 'spend']]
            df['cpl'] = df['cpl'].apply(lambda x: f"€{x:.2f}")
            df['spend'] = df['spend'].apply(lambda x: f"€{x:.2f}")
            st.dataframe(df, hide_index=True, use_container_width=True)

        with col2:
            st.caption("Worst 5 per CPL")
            worst_5 = sorted(creative, key=lambda x: -x.get('cpl', 0))[:5]
            df = pd.DataFrame(worst_5)[['name', 'cpl', 'leads', 'spend']]
            df['cpl'] = df['cpl'].apply(lambda x: f"€{x:.2f}")
            df['spend'] = df['spend'].apply(lambda x: f"€{x:.2f}")
            st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nessun dato creativo disponibile")

    st.divider()

    # Setter Performance
    st.subheader("👥 Performance Setter")
    if setters:
        fig = create_setter_performance_chart(setters, metric="show_up_rate")
        st.plotly_chart(fig, use_container_width=True)

        # Table
        setter_list = []
        for name, stats in setters.items():
            setter_list.append({
                'Setter': name,
                'Calls': stats.get('calls', 0),
                'Show Up': stats.get('show_ups', 0),
                'Close': stats.get('closures', 0),
                'SU%': f"{stats.get('show_up_rate', 0):.1f}%",
                'Close%': f"{stats.get('close_rate', 0):.1f}%",
                'Revenue': f"€{stats.get('revenue', 0):,.0f}"
            })

        df = pd.DataFrame(setter_list).sort_values('Calls', ascending=False)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nessun dato setter disponibile")

    st.divider()

    # Closer Performance
    st.subheader("💰 Performance Venditori")
    if closers:
        fig = create_closer_performance_chart(closers)
        st.plotly_chart(fig, use_container_width=True)

        # Table
        closer_list = []
        for name, stats in closers.items():
            if name != 'Unassigned':
                closer_list.append({
                    'Venditore': name,
                    'Show Up': stats.get('show_ups', 0),
                    'Chiusi': stats.get('closures', 0),
                    'Scartati': stats.get('scartati', 0),
                    'Uncl.': stats.get('unclosable', 0),
                    'Close%': f"{stats.get('close_rate', 0):.1f}%",
                    'Revenue': f"€{stats.get('revenue', 0):,.0f}",
                    'Ticket': f"€{stats.get('ticket_medio', 0):,.0f}"
                })

        df = pd.DataFrame(closer_list).sort_values('Revenue', ascending=False)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nessun dato venditori disponibile")


def render_debug_audit_tab(funnel, creative):
    """
    Render debug/audit tab with calculation breakdowns and confirmation button.

    Args:
        funnel: Dict from analyze_funnel()
        creative: List from analyze_creative()
    """
    st.header("🔍 Debug & Audit")

    # Confirmation Button
    render_confirmation_button()

    st.divider()

    # Funnel Calculation Breakdown
    with st.expander("📊 Funnel Calculation Breakdown", expanded=True):
        breakdown = f"""
Candidature: {funnel.get('candidature', 0):,}

Calls: {funnel.get('calls', 0):,}
  → Calculation: count(calls in period)
  → Cand→Call Rate: {funnel.get('calls', 0)} / {funnel.get('candidature', 0)} = {funnel.get('cand_to_call_rate', 0):.1f}%

Show Ups: {funnel.get('show_ups', 0):,}
  → States counted as Show Up: {', '.join(SHOW_UP_STATES)}
  → Call→Show Up Rate: {funnel.get('show_ups', 0)} / {funnel.get('calls', 0)} = {funnel.get('call_to_showup_rate', 0):.1f}%

Closures: {funnel.get('closures', 0):,}
  → States counted as Closed: {', '.join(CLOSED_STATES)}
  → Show Up→Close Rate: {funnel.get('closures', 0)} / {funnel.get('show_ups', 0)} = {funnel.get('showup_to_close_rate', 0):.1f}%

Revenue: €{funnel.get('revenue', 0):,.2f}
  → Calculation: sum(Revenue) for calls with Stato in {CLOSED_STATES}
  → Ticket Medio: €{funnel.get('revenue', 0):,.2f} / {funnel.get('closures', 0)} = €{funnel.get('ticket_medio', 0):,.2f}

Cost Metrics:
  → Spesa Totale: €{funnel.get('total_spend', 0):,.2f}
  → CPL: €{funnel.get('total_spend', 0):,.2f} / {funnel.get('candidature', 0)} = €{funnel.get('cpl', 0):.2f}
  → CPC: €{funnel.get('total_spend', 0):,.2f} / {funnel.get('calls', 0)} = €{funnel.get('cpc', 0):.2f}
  → CPSU: €{funnel.get('total_spend', 0):,.2f} / {funnel.get('show_ups', 0)} = €{funnel.get('cpsu', 0):.2f}
  → CPCl: €{funnel.get('total_spend', 0):,.2f} / {funnel.get('closures', 0)} = €{funnel.get('cpcl', 0):.2f}

ROAS:
  → Revenue: €{funnel.get('revenue', 0):,.2f} / €{funnel.get('total_spend', 0):,.2f} = {funnel.get('roas_revenue', 0):.2f}x
  → Cash: €{funnel.get('cash', 0):,.2f} / €{funnel.get('total_spend', 0):,.2f} = {funnel.get('roas_cash', 0):.2f}x
        """
        st.code(breakdown, language="")

    # State Classification Breakdown
    with st.expander("📋 State Classification"):
        status_df = pd.DataFrame([
            {'Stato': status, 'Count': count, 'Tipo': '✅ Show Up' if status in SHOW_UP_STATES else '❌ No Show'}
            for status, count in sorted(funnel.get('by_status', {}).items(), key=lambda x: -x[1])
        ])
        st.dataframe(status_df, hide_index=True, use_container_width=True)

    # Raw Data Preview
    with st.expander("🔢 Raw Funnel Data"):
        st.json(funnel, expanded=False)


def render_confirmation_button():
    """
    Render confirmation button to save analysis to database.
    Checks if period already exists and shows warning.
    """
    if 'current_analysis' not in st.session_state:
        st.warning("Nessuna analisi da salvare. Carica i dati prima.")
        return

    analysis = st.session_state['current_analysis']

    # Check if period already exists
    existing = check_period_exists(analysis['period_start'], analysis['period_end'])

    if existing:
        st.warning(f"⚠️ Esiste già un'analisi per il periodo {analysis['period_start']} → {analysis['period_end']}")
        st.info(f"Analisi esistente: Creata {existing['created_at']}, Aggiornata {existing['updated_at']}")

    confirm_button = st.button(
        "✅ Conferma e Salva Analisi",
        type="primary",
        help="Salva questa analisi nel database. Se esiste già, verrà sovrascritta.",
        use_container_width=True
    )

    if confirm_button:
        with st.spinner("Salvataggio in corso..."):
            run_id = save_analysis_run(
                analysis['period_start'],
                analysis['period_end'],
                analysis['funnel'],
                analysis['creative'],
                analysis['setters'],
                analysis['closers']
            )

        if run_id:
            st.success("✅ Analisi salvata con successo!")
            st.balloons()
        else:
            st.error("❌ Errore durante il salvataggio")


def render_historical_tab():
    """
    Render historical trends tab with comparisons.
    """
    st.header("📈 Storico Analisi")

    # Fetch historical runs
    runs = get_historical_runs(limit=20)

    if not runs:
        st.info("Nessuna analisi storica disponibile. Salva la prima analisi per iniziare.")
        return

    # Trend Chart
    st.subheader("Trend nel Tempo")

    metric_options = {
        'ROAS Cash': 'roas_cash',
        'ROAS Revenue': 'roas_revenue',
        'CPL': 'cpl',
        'Show Up Rate': 'call_to_showup_rate',
        'Close Rate': 'showup_to_close_rate'
    }

    selected_metric_label = st.selectbox("Seleziona Metrica", list(metric_options.keys()))
    selected_metric = metric_options[selected_metric_label]

    fig = create_trend_chart(runs, metric=selected_metric)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Historical Table
    st.subheader("Elenco Analisi")

    historical_data = []
    for run in runs:
        historical_data.append({
            'Periodo': f"{run['period_start']} → {run['period_end']}",
            'ROAS Cash': f"{run.get('roas_cash', 0):.2f}x",
            'CPL': f"€{run.get('cpl', 0):.2f}",
            'Revenue': f"€{run.get('revenue', 0):,.0f}",
            'Chiusure': run.get('closures', 0),
            'Aggiornata': run.get('updated_at', 'N/A')
        })

    df = pd.DataFrame(historical_data)
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_parameters_tab():
    """
    Render parameters modification tab.
    """
    st.header("⚙️ Parametri Modificabili")

    st.info("Questi parametri vengono usati per le soglie e le raccomandazioni, ma NON modificano i calcoli sottostanti.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Soglie Performance")
        show_up_threshold = st.slider("Target Show Up Rate (%)", 0, 100, 50, key='param_su')
        close_rate_threshold = st.slider("Target Close Rate (%)", 0, 100, 20, key='param_cr')

    with col2:
        st.subheader("Target Costi")
        cpl_target = st.number_input("Target CPL (€)", min_value=0.0, value=10.0, step=0.5, key='param_cpl')
        roas_minimum = st.number_input("ROAS Minimo", min_value=0.0, value=2.0, step=0.1, key='param_roas')

    # Save to session state
    st.session_state['params'] = {
        'show_up_threshold': show_up_threshold,
        'close_rate_threshold': close_rate_threshold,
        'cpl_target': cpl_target,
        'roas_minimum': roas_minimum
    }

    st.success("Parametri aggiornati!")
