import os
import textwrap
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Airline Support Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

CHART_LAYOUT = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=13),
)

TABLE_COLUMN_META: dict[str, dict[str, str]] = {
    "Rank": {"width": "64px", "align": "center", "valign": "middle"},
    "Count": {"width": "72px", "align": "center", "valign": "middle"},
    "Query": {"width": "auto", "align": "left", "valign": "top"},
    "Category": {"width": "auto", "align": "left", "valign": "top"},
    "Time": {"width": "130px", "align": "left", "valign": "top"},
    "Session": {"width": "90px", "align": "center", "valign": "middle"},
    "Response preview": {"width": "auto", "align": "left", "valign": "top"},
}

st.markdown(
    """
    <style>
        .analytics-table-card {
            width: 100%;
            border: 1px solid var(--border-color, #d5dae3);
            border-radius: 0.5rem;
            overflow: hidden;
            margin-bottom: 0.75rem;
            background: var(--secondary-background-color, #f8f9fb);
            color: var(--text-color, #31333f);
        }
        .analytics-table {
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            font-size: 0.875rem;
            color: var(--text-color, #31333f);
        }
        .analytics-table thead th {
            background: var(--secondary-background-color, #eef1f6);
            color: var(--text-color, #31333f);
            font-weight: 600;
            padding: 0.65rem 0.75rem;
            border-bottom: 1px solid var(--border-color, #d5dae3);
            white-space: nowrap;
        }
        .analytics-table tbody td {
            padding: 0.7rem 0.75rem;
            border-bottom: 1px solid var(--border-color, #e3e7ee);
            color: var(--text-color, #31333f);
            background: var(--background-color, #ffffff);
            line-height: 1.45;
            word-break: break-word;
            overflow-wrap: anywhere;
        }
        .analytics-table tbody tr:nth-child(even) td {
            background: var(--secondary-background-color, #f4f6f9);
        }
        .analytics-table tbody tr:last-child td {
            border-bottom: none;
        }
        [data-theme="dark"] .analytics-table-card,
        .stApp[data-theme="dark"] .analytics-table-card {
            border-color: #3d4450;
            background: #1a1d24;
            color: #fafafa;
        }
        [data-theme="dark"] .analytics-table thead th,
        .stApp[data-theme="dark"] .analytics-table thead th {
            background: #262a33;
            color: #fafafa;
            border-bottom-color: #3d4450;
        }
        [data-theme="dark"] .analytics-table tbody td,
        .stApp[data-theme="dark"] .analytics-table tbody td {
            color: #fafafa;
            background: #0e1117;
            border-bottom-color: #2d333d;
        }
        [data-theme="dark"] .analytics-table tbody tr:nth-child(even) td,
        .stApp[data-theme="dark"] .analytics-table tbody tr:nth-child(even) td {
            background: #161920;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def fetch_summary(days: int) -> dict:
    resp = requests.get(f"{API_BASE}/analytics/summary", params={"days": days}, timeout=30)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def fetch_top_queries(limit: int, days: int) -> dict:
    resp = requests.get(
        f"{API_BASE}/analytics/top-queries",
        params={"limit": limit, "days": days},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def fetch_recent(limit: int, days: int) -> dict:
    resp = requests.get(
        f"{API_BASE}/analytics/recent",
        params={"limit": limit, "days": days},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def fetch_daily_volume(days: int) -> dict:
    resp = requests.get(f"{API_BASE}/analytics/daily-volume", params={"days": days}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def format_timestamp(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def wrap_label(text: str, width: int = 28) -> str:
    """Wrap long labels for Plotly axes (HTML line breaks)."""
    if len(text) <= width:
        return text
    wrapped = textwrap.wrap(text, width=width)
    return "<br>".join(wrapped) if wrapped else text


def _column_meta(
    column: str,
    widths: dict[str, str] | None = None,
) -> dict[str, str]:
    meta = TABLE_COLUMN_META.get(column, {"width": "auto", "align": "left", "valign": "top"}).copy()
    if widths and column in widths:
        meta["width"] = widths[column]
    return meta


def _cell_style(column: str, widths: dict[str, str] | None = None) -> str:
    meta = _column_meta(column, widths)
    return (
        f"width:{meta['width']};text-align:{meta['align']};"
        f"vertical-align:{meta['valign']};"
    )


def render_analytics_table(
    df: pd.DataFrame,
    wrap_columns: dict[str, int] | None = None,
    widths: dict[str, str] | None = None,
) -> None:
    """Render a styled analytics table with aligned columns and wrapped text."""
    wrap_columns = wrap_columns or {}
    display = df.copy()
    for column, width in wrap_columns.items():
        display[column] = display[column].apply(lambda value: wrap_label(str(value), width))

    colgroup = "".join(
        f"<col style='width:{_column_meta(col, widths)['width']};' />" for col in display.columns
    )
    headers = "".join(
        f"<th style='{_cell_style(col, widths)}'>{col}</th>" for col in display.columns
    )
    rows = []
    for _, row in display.iterrows():
        cells = "".join(
            f"<td style='{_cell_style(col, widths)}'>{row[col]}</td>" for col in display.columns
        )
        rows.append(f"<tr>{cells}</tr>")

    st.markdown(
        f"""
        <div class="analytics-table-card">
            <table class="analytics-table">
                <colgroup>{colgroup}</colgroup>
                <thead><tr>{headers}</tr></thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def top_queries_bar_chart(df: pd.DataFrame) -> go.Figure:
    chart_df = df.copy()
    chart_df["Label"] = chart_df["Query"].apply(lambda q: wrap_label(q, width=26))
    line_counts = chart_df["Label"].str.count("<br>").add(1)
    chart_height = max(380, int(line_counts.sum() * 34 + 80))

    fig = px.bar(
        chart_df,
        x="Count",
        y="Label",
        orientation="h",
        title="Queries by Frequency",
        color_discrete_sequence=["#3b82f6"],
        text="Count",
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate="<b>%{customdata[0]}</b><br>Count: %{x}<extra></extra>",
        customdata=chart_df[["Query"]],
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=chart_height,
        yaxis=dict(
            autorange="reversed",
            title="",
            tickfont=dict(size=11),
            automargin=True,
        ),
        xaxis=dict(title="Count", gridcolor="#e5e7eb"),
        margin=dict(l=16, r=48, t=56, b=24),
        showlegend=False,
    )
    return fig


def daily_volume_line_chart(df: pd.DataFrame) -> go.Figure:
    fig = px.line(
        df,
        x="Date",
        y="Count",
        title="Query Volume Over Time",
        markers=True,
        color_discrete_sequence=["#2563eb"],
    )
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Queries: %{y}<extra></extra>",
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=340,
        margin=dict(l=24, r=24, t=56, b=24),
        xaxis=dict(title="", gridcolor="#e5e7eb"),
        yaxis=dict(title="Queries", gridcolor="#e5e7eb", rangemode="tozero"),
        hovermode="x unified",
    )
    return fig


with st.sidebar:
    st.markdown("## 📊 Support Analytics")
    st.caption("Track frequent customer queries and recent conversations.")
    st.divider()
    days = st.slider("Lookback period (days)", min_value=1, max_value=90, value=30)
    top_n = st.slider("Top queries to show", min_value=5, max_value=20, value=10)
    recent_n = st.slider("Recent conversations", min_value=10, max_value=100, value=25)
    st.divider()
    st.link_button("Open customer chat", "http://localhost:8501", width="stretch")
    st.link_button("API Docs (Swagger)", f"{API_BASE}/docs", width="stretch")

if "last_refreshed" not in st.session_state:
    st.session_state.last_refreshed = datetime.now()

header_left, header_right = st.columns([5, 1])
with header_left:
    st.title("Airline Support Dashboard")
    st.caption("Monitor the latest frequent queries so your team can resolve recurring issues quickly.")
    st.caption(f"Last updated: {st.session_state.last_refreshed.strftime('%Y-%m-%d %H:%M:%S')}")
with header_right:
    st.write("")
    if st.button("🔄 Refresh", type="primary", width="stretch"):
        st.cache_data.clear()
        st.session_state.last_refreshed = datetime.now()
        st.rerun()

try:
    summary = fetch_summary(days)
    top_data = fetch_top_queries(top_n, days)
    recent_data = fetch_recent(recent_n, days)
    volume_data = fetch_daily_volume(days)
except requests.RequestException as exc:
    st.error(
        "Could not load analytics. Make sure the FastAPI server is running:\n\n"
        "`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`\n\n"
        f"Error: {exc}"
    )
    st.stop()

metric_cols = st.columns(3)
metric_cols[0].metric("Queries in period", summary["total_queries"])
metric_cols[1].metric("Queries today", summary["queries_today"])
metric_cols[2].metric("Lookback", f"{summary['period_days']} days")

st.divider()

volume_items = volume_data["items"]
if volume_items:
    volume_df = pd.DataFrame([{"Date": item["date"], "Count": item["count"]} for item in volume_items])
    st.plotly_chart(daily_volume_line_chart(volume_df), width="stretch")
else:
    st.info("Query volume trend will appear after conversations are logged.")

st.divider()

st.subheader(f"Top {top_n} frequent queries")
top_items = top_data["items"]
if not top_items:
    st.info("No conversations logged yet. Use the customer chat to generate data.")
else:
    top_df = pd.DataFrame(
        [
            {
                "Rank": item["rank"],
                "Query": item["query"],
                "Count": item["count"],
                "Category": item.get("latest_category") or "—",
                "Last seen": format_timestamp(item.get("last_seen")),
            }
            for item in top_items
        ]
    )
    render_analytics_table(
        top_df[["Rank", "Query", "Count"]],
        wrap_columns={"Query": 24},
        widths={"Rank": "56px", "Count": "64px", "Query": "auto"},
    )
    st.plotly_chart(top_queries_bar_chart(top_df), width="stretch")

st.divider()
st.subheader("Latest conversations")

recent_items = recent_data["items"]
if not recent_items:
    st.info("No recent conversations to display.")
else:
    recent_df = pd.DataFrame(
        [
            {
                "Time": format_timestamp(item.get("created_at")),
                "Query": item["query"],
                "Category": item.get("category") or "—",
                "Session": (item.get("session_id") or "—")[:8],
                "Response preview": item["response"][:120] + ("…" if len(item["response"]) > 120 else ""),
            }
            for item in recent_items
        ]
    )
    render_analytics_table(
        recent_df,
        wrap_columns={"Query": 28, "Response preview": 36},
        widths={
            "Time": "12%",
            "Query": "24%",
            "Category": "12%",
            "Session": "8%",
            "Response preview": "44%",
        },
    )

    with st.expander("View full conversation details"):
        for item in recent_items:
            st.markdown(f"**{format_timestamp(item.get('created_at'))}** · `{item.get('category') or 'Unknown'}`")
            st.markdown(f"**Customer:** {item['query']}")
            st.markdown(f"**Assistant:** {item['response']}")
            st.divider()
