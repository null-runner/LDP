"""
LDP Dashboard - Main Application Entry Point
Streamlit web app for comprehensive marketing funnel analysis
"""
import streamlit as st
from app.auth import check_authentication
from app.data_loader import load_meta_csvs, refresh_airtable_data, filter_data_by_period, calculate_total_spend
from app.analyzers import analyze_funnel, analyze_creative, analyze_setters, analyze_closers
from app.database import init_database
from app.ui_components import render_sidebar, render_main_dashboard, render_debug_audit_tab, render_historical_tab, render_parameters_tab


# Page config
st.set_page_config(
    page_title="LDP Dashboard",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Authentication check FIRST
authenticated, username = check_authentication()

# Welcome message
st.title("📊 LDP 360° Dashboard")
st.caption(f"Benvenuto, {username}!")

# Initialize database (only runs once)
with st.spinner("Inizializzazione database..."):
    init_database()

# Render sidebar and get inputs
uploaded_files, selected_period, params = render_sidebar()

# Main app logic
if uploaded_files and selected_period and any(uploaded_files.values()):
    st.success(f"✅ Analisi periodo: {selected_period['start']} → {selected_period['end']}")

    # Load Meta CSV files
    with st.spinner("Caricamento file CSV..."):
        meta_data = load_meta_csvs(
            uploaded_files['ads'],
            uploaded_files['adsets'],
            uploaded_files['campaigns']
        )

    # Refresh Airtable data
    with st.spinner("Aggiornamento dati Airtable..."):
        airtable_data = refresh_airtable_data(
            st.secrets["airtable"]["api_key"],
            st.secrets["airtable"]["base_id"]
        )

    # Filter data by period
    period_data = filter_data_by_period(
        {**meta_data, **airtable_data},
        selected_period['start'],
        selected_period['end']
    )

    # Calculate total spend
    total_spend = calculate_total_spend(period_data['ads'])

    # Run analysis
    with st.spinner("Analisi in corso..."):
        funnel = analyze_funnel(
            period_data['candidature'],
            period_data['calls'],
            meta_spend=total_spend
        )

        creative = analyze_creative(period_data['ads'])

        setters = analyze_setters(period_data['calls'])

        closers = analyze_closers(period_data['calls'])

    # Store in session state (not database yet - user must confirm)
    st.session_state['current_analysis'] = {
        'period_start': selected_period['start'],
        'period_end': selected_period['end'],
        'funnel': funnel,
        'creative': creative,
        'setters': setters,
        'closers': closers
    }

    # Render tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "🔍 Debug/Audit",
        "📈 Storico",
        "⚙️ Parametri"
    ])

    with tab1:
        render_main_dashboard(period_data, funnel, creative, setters, closers)

    with tab2:
        render_debug_audit_tab(funnel, creative)

    with tab3:
        render_historical_tab()

    with tab4:
        render_parameters_tab()

else:
    st.info("📤 Carica i file CSV dalla sidebar per iniziare l'analisi")

    # Show instructions
    with st.expander("📖 Istruzioni"):
        st.markdown("""
        ### Come utilizzare la dashboard

        1. **Carica i file CSV** dalla sidebar:
           - Ads CSV
           - AdSets CSV
           - Campaigns CSV

        2. **Seleziona il periodo** rilevato automaticamente dai nomi dei file

        3. **Visualizza l'analisi** nei vari tab:
           - **Dashboard**: Panoramica completa con KPI e grafici
           - **Debug/Audit**: Verifica calcoli e conferma salvataggio
           - **Storico**: Trend nel tempo e confronti
           - **Parametri**: Modifica soglie e target

        4. **Conferma il salvataggio** nel tab Debug/Audit per salvare l'analisi nel database

        ### Funzionalità principali

        - ✅ Analisi automatica del funnel (Candidature → Calls → Show Up → Chiusure)
        - ✅ Performance creative con CPL, CTR, retention
        - ✅ Performance setter (show-up rate, close rate)
        - ✅ Performance venditori (close rate, ticket medio, revenue)
        - ✅ Storico analisi con trend nel tempo
        - ✅ Calcoli trasparenti e verificabili
        - ✅ Backup automatico giornaliero (Supabase)

        ### Note

        - I dati Airtable vengono aggiornati automaticamente
        - Le analisi sono salvate per periodo (sovrascrivibili)
        - I parametri non modificano i calcoli, solo le raccomandazioni
        """)

# Footer
st.divider()
st.caption("LDP Dashboard v1.0 - Powered by Streamlit + Supabase")
