"""
Chart Generation for LDP Dashboard
Uses Plotly Express for interactive visualizations
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def create_funnel_chart(funnel_data):
    """
    Create funnel visualization: Candidature → Calls → Show Up → Closures

    Args:
        funnel_data: Dict from analyze_funnel()

    Returns:
        Plotly Figure
    """
    stages = ['Candidature', 'Calls', 'Show Up', 'Chiusure']
    values = [
        funnel_data.get('candidature', 0),
        funnel_data.get('calls', 0),
        funnel_data.get('show_ups', 0),
        funnel_data.get('closures', 0)
    ]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textposition="inside",
        textinfo="value+percent initial",
        marker={"color": ["#3498db", "#2ecc71", "#f39c12", "#e74c3c"]}
    ))

    fig.update_layout(
        title="Funnel Conversione",
        height=400,
        showlegend=False
    )

    return fig


def create_creative_performance_chart(creative_data, sort_by="cpl", top_n=10):
    """
    Bar chart of top/worst creatives by CPL.

    Args:
        creative_data: List from analyze_creative()
        sort_by: Metric to sort by (default: "cpl")
        top_n: Number of creatives to show

    Returns:
        Plotly Figure
    """
    if not creative_data:
        return go.Figure()

    # Sort and take top N
    sorted_data = sorted(creative_data, key=lambda x: x.get(sort_by, 999999))[:top_n]

    df = pd.DataFrame(sorted_data)

    fig = px.bar(
        df,
        x='cpl',
        y='name',
        orientation='h',
        title=f'Top {top_n} Creative per CPL',
        labels={'cpl': 'CPL (€)', 'name': 'Creative'},
        color='cpl',
        color_continuous_scale='RdYlGn_r',
        hover_data={'leads': True, 'spend': ':.2f', 'ctr': ':.2f'}
    )

    fig.update_layout(
        height=max(400, top_n * 40),
        xaxis_title="CPL (€)",
        yaxis_title="",
        showlegend=False
    )

    return fig


def create_setter_performance_chart(setter_data, metric="show_up_rate"):
    """
    Horizontal bar chart of setter performance.

    Args:
        setter_data: Dict from analyze_setters()
        metric: Metric to visualize (default: "show_up_rate")

    Returns:
        Plotly Figure
    """
    if not setter_data:
        return go.Figure()

    # Convert to DataFrame
    data = []
    for setter, stats in setter_data.items():
        data.append({
            'setter': setter,
            'show_up_rate': stats.get('show_up_rate', 0),
            'close_rate': stats.get('close_rate', 0),
            'calls': stats.get('calls', 0),
            'revenue': stats.get('revenue', 0)
        })

    df = pd.DataFrame(data)
    df = df.sort_values(by=metric, ascending=True)

    metric_labels = {
        'show_up_rate': 'Show Up Rate (%)',
        'close_rate': 'Close Rate (%)',
        'calls': 'Calls',
        'revenue': 'Revenue (€)'
    }

    fig = px.bar(
        df,
        x=metric,
        y='setter',
        orientation='h',
        title=f'Performance Setter - {metric_labels.get(metric, metric)}',
        labels={metric: metric_labels.get(metric, metric), 'setter': 'Setter'},
        color=metric,
        color_continuous_scale='Blues',
        hover_data={'calls': True, 'revenue': ':.0f'}
    )

    fig.update_layout(
        height=max(400, len(setter_data) * 30),
        xaxis_title=metric_labels.get(metric, metric),
        yaxis_title="",
        showlegend=False
    )

    return fig


def create_closer_performance_chart(closer_data):
    """
    Scatter plot: close_rate vs revenue per closer.

    Args:
        closer_data: Dict from analyze_closers()

    Returns:
        Plotly Figure
    """
    if not closer_data:
        return go.Figure()

    # Convert to DataFrame
    data = []
    for closer, stats in closer_data.items():
        if closer != 'Unassigned':
            data.append({
                'closer': closer,
                'close_rate': stats.get('close_rate', 0),
                'revenue': stats.get('revenue', 0),
                'closures': stats.get('closures', 0),
                'show_ups': stats.get('show_ups', 0)
            })

    df = pd.DataFrame(data)

    fig = px.scatter(
        df,
        x='close_rate',
        y='revenue',
        size='closures',
        hover_name='closer',
        title='Performance Venditori - Close Rate vs Revenue',
        labels={'close_rate': 'Close Rate (%)', 'revenue': 'Revenue (€)'},
        color='close_rate',
        color_continuous_scale='Greens',
        hover_data={'show_ups': True, 'closures': True}
    )

    fig.update_layout(
        height=500,
        xaxis_title="Close Rate (%)",
        yaxis_title="Revenue (€)"
    )

    return fig


def create_trend_chart(historical_data, metric="roas_cash"):
    """
    Line chart showing metric over time.

    Args:
        historical_data: List of dicts from get_historical_runs()
        metric: Metric to plot (default: "roas_cash")

    Returns:
        Plotly Figure
    """
    if not historical_data:
        return go.Figure()

    # Convert to DataFrame
    df = pd.DataFrame(historical_data)

    # Create period label
    df['period_label'] = df['period_start'].astype(str) + ' → ' + df['period_end'].astype(str)

    metric_labels = {
        'roas_cash': 'ROAS Cash',
        'roas_revenue': 'ROAS Revenue',
        'cpl': 'CPL (€)',
        'close_rate': 'Close Rate (%)',
        'show_up_rate': 'Show Up Rate (%)'
    }

    fig = px.line(
        df,
        x='period_end',
        y=metric,
        title=f'Trend - {metric_labels.get(metric, metric)}',
        labels={'period_end': 'Periodo', metric: metric_labels.get(metric, metric)},
        markers=True,
        hover_data={'period_label': True}
    )

    fig.update_layout(
        height=400,
        xaxis_title="Periodo",
        yaxis_title=metric_labels.get(metric, metric)
    )

    return fig


def create_kpi_card(title, value, delta=None, format_str="{:.2f}"):
    """
    Create a simple KPI card metric.

    Args:
        title: Metric name
        value: Metric value
        delta: Optional delta vs previous period
        format_str: Format string for value

    Returns:
        Dict with formatted values for Streamlit metric display
    """
    formatted_value = format_str.format(value) if value is not None else "N/A"

    return {
        'title': title,
        'value': formatted_value,
        'delta': delta
    }
