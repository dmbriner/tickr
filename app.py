"""Streamlit dashboard for a 3-statement model with richer market data and valuation views."""

from __future__ import annotations

import copy
import dataclasses
import io
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from model_engine import (
    LINE_ITEM_META,
    CompanyProfile,
    ModelAssumptions,
    HistoricalData,
    analyze_historical_data,
    build_excel_bytes,
    build_research_pack,
    build_multi_output_sensitivity,
    build_tornado_chart,
    check_integrity,
    fmp_enabled,
    format_line_item_label,
    load_historical_data,
    reporting_frame,
    run_dcf,
    run_lbo,
    run_multiple_valuation,
    run_precedent_transactions,
    run_three_statement_model,
    search_companies,
    suggest_scenarios,
    valuation_summary_table,
    wacc_terminal_sensitivity,
)

PROJ_YEARS = 5
SCENARIO_COLORS = {"Base": "#0f4c81", "Bull": "#0d7a5f", "Bear": "#a13d2d"}
VALUE_METHOD_COLORS = ["#0f4c81", "#2d6a4f", "#b08968", "#9c6644", "#7f5539", "#5e3023"]

SLIDER_DEFAULTS: dict[str, float | int] = {
    "growth_y1": 0.05,
    "growth_yn": 0.03,
    "gm_y1": 0.30,
    "gm_yn": 0.29,
    "opex_pct": 0.15,
    "capex_pct": 0.05,
    "dep_pct": 0.12,
    "dso_days": 45,
    "dio_days": 15,
    "dpo_days": 30,
    "tax_rate": 0.24,
    "int_rate": 0.05,
    "div_payout": 0.30,
    "debt_amort": 500,
    "wacc": 0.09,
    "term_growth": 0.025,
}

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Lora:ital,wght@0,400;0,500;0,600;1,400&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');

:root {
    --bg: #f0f4f8;
    --panel: #ffffff;
    --panel-strong: #ffffff;
    --ink: #0f172a;
    --muted: #4e5d6c;
    --line: #dde3ec;
    --accent: #0f4c81;
    --accent-hover: #0a3764;
    --gold: #b58a38;
    --success: #15803d;
    --danger: #b91c1c;
    --sidebar-bg: #ffffff;
}

.stApp {
    font-family: 'Lora', Georgia, serif;
    color: var(--ink);
    background: #f0f4f8;
}

h1, h2, h3, h4 {
    font-family: 'Playfair Display', Georgia, serif;
    font-weight: 600;
    color: var(--ink);
}

[data-testid="stSidebar"] {
    background: var(--sidebar-bg);
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] * {
    font-family: 'Lora', Georgia, serif;
}

.block-container {
    padding-top: 1.4rem;
    padding-bottom: 4rem;
    max-width: 1240px;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

/* ── Buttons ── */
.stButton > button,
.stButton button {
    font-family: 'Lora', Georgia, serif !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    border: 1px solid var(--line) !important;
    background: var(--panel) !important;
    color: var(--ink) !important;
    padding: 0.38rem 0.75rem !important;
    transition: background 0.15s, border-color 0.15s, box-shadow 0.15s !important;
    white-space: nowrap !important;
}

.stButton > button:hover,
.stButton button:hover {
    background: #e8edf4 !important;
    border-color: #b0bec8 !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08) !important;
}

/* Primary buttons — Analyze Company, Enter Platform */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"],
.stButton button[data-baseweb="button"][kind="primary"] {
    background: var(--accent) !important;
    color: #ffffff !important;
    border-color: var(--accent) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background: var(--accent-hover) !important;
    border-color: var(--accent-hover) !important;
    box-shadow: 0 4px 14px rgba(15, 76, 129, 0.25) !important;
}

/* Secondary buttons in sidebar — Clear selection, small actions */
[data-testid="stSidebar"] .stButton > button {
    font-size: 0.82rem !important;
    padding: 0.3rem 0.5rem !important;
}

.stDownloadButton > button,
.stDownloadButton button {
    font-family: 'Lora', Georgia, serif !important;
    background: var(--success) !important;
    color: #ffffff !important;
    border: 1px solid var(--success) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    padding: 0.42rem 1rem !important;
    transition: background 0.15s, box-shadow 0.15s !important;
}

.stDownloadButton > button:hover {
    background: #126832 !important;
    border-color: #126832 !important;
    box-shadow: 0 4px 14px rgba(21, 128, 61, 0.25) !important;
}

/* ── Hero ── */
.hero-card {
    padding: 1.6rem 1.8rem;
    border-radius: 14px;
    background: linear-gradient(130deg, #0f172a 0%, #0f4c81 65%, #1a5a9a 100%);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 1.4rem;
    box-shadow: 0 8px 32px rgba(15, 23, 42, 0.18);
}

.hero-name {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.15;
    margin-top: 0.3rem;
}

.hero-subtle {
    opacity: 0.78;
    margin-top: 0.4rem;
    font-size: 0.95rem;
    letter-spacing: 0.01em;
}

/* ── Glossary pills ── */
.glossary-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0.4rem 0 1rem 0;
}

.glossary-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.65rem;
    border-radius: 5px;
    background: #e8edf4;
    border: 1px solid #c5d0dc;
    color: var(--accent);
    font-size: 0.84rem;
    cursor: help;
    font-family: 'Lora', Georgia, serif;
}

/* ── Landing cards ── */
.landing-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    margin: 1.2rem 0 1.4rem 0;
}

.landing-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.3rem 1.2rem;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

.landing-icon {
    margin-bottom: 0.55rem;
}

.landing-icon .material-icons {
    font-size: 2rem;
    color: var(--gold);
    display: block;
    font-family: 'Material Icons';
    font-weight: normal;
    font-style: normal;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    -webkit-font-feature-settings: 'liga';
    font-feature-settings: 'liga';
}

.landing-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.4rem;
    color: var(--ink);
}

.landing-copy {
    color: var(--muted);
    line-height: 1.55;
    font-size: 0.93rem;
}

/* ── Welcome screen ── */
.welcome-hero {
    max-width: 680px;
    margin: 4rem auto 0;
    text-align: center;
    padding: 0 1rem;
}

.welcome-hero h1 {
    font-size: 2.8rem;
    font-family: 'Playfair Display', Georgia, serif;
    font-weight: 700;
    line-height: 1.15;
    margin-bottom: 1rem;
    color: var(--ink);
    letter-spacing: -0.01em;
}

.welcome-hero p {
    color: var(--muted);
    font-size: 1.05rem;
    line-height: 1.6;
    margin-bottom: 1.8rem;
}

/* ── Sidebar content padding (prevents left-edge clipping) ── */
[data-testid="stSidebar"] > div:first-child {
    padding-left: 1rem;
    padding-right: 1rem;
}

/* ── Sidebar section boxes ── */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border: 1px solid var(--line);
    border-radius: 8px;
    margin-bottom: 0.5rem;
}

[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.5rem 0.75rem;
}

/* ── Misc ── */
.small-label {
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-size: 0.68rem;
    opacity: 0.7;
    font-family: 'Lora', Georgia, serif;
}

.section-note {
    color: var(--muted);
    font-size: 0.94rem;
    font-style: italic;
}

.site-footer {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
    margin-top: 3rem;
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-size: 0.86rem;
    font-style: italic;
}

.site-footer a {
    color: var(--accent);
    text-decoration: none;
    border-bottom: 1px solid rgba(15, 76, 129, 0.3);
}
</style>
"""


def _fm(v: float) -> str:
    return f"${v:,.0f}M"


def _fp(v: float) -> str:
    return f"{v * 100:.1f}%"


def _safe_float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _format_title_case(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [format_line_item_label(str(c)) for c in out.columns]
    return out


def _format_display_df(df: pd.DataFrame, pct_cols: set[str] | None = None, per_share_cols: set[str] | None = None) -> pd.DataFrame:
    pct_cols = pct_cols or set()
    per_share_cols = per_share_cols or set()
    out = df.copy()
    for col in out.columns:
        if col == "year" or col == "period_label":
            continue
        if col in pct_cols:
            out[col] = out[col].apply(_fp)
        elif col in per_share_cols:
            out[col] = out[col].apply(lambda v: f"${v:,.2f}")
        elif pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].apply(lambda v: f"${v:,.0f}M" if pd.notna(v) else "—")
    return _format_title_case(out)


def _glossary(keys: list[str]) -> None:
    pills = []
    for key in keys:
        meta = LINE_ITEM_META.get(key)
        if not meta:
            continue
        tooltip = f"{meta.definition} Formula: {meta.formula}"
        pills.append(f'<span class="glossary-pill" title="{tooltip}">{meta.label}</span>')
    if pills:
        st.markdown(f'<div class="glossary-row">{"".join(pills)}</div>', unsafe_allow_html=True)


def _init_session_state() -> None:
    for key, val in SLIDER_DEFAULTS.items():
        st.session_state.setdefault(key, val)
    st.session_state.setdefault("metrics", None)
    st.session_state.setdefault("selected_ticker", "")
    st.session_state.setdefault("search_query", "")
    st.session_state.setdefault("reporting_view", "Full Year")
    st.session_state.setdefault("is_authenticated", False)


def _interp(y1: float, yn: float, n: int = PROJ_YEARS) -> list[float]:
    if n == 1:
        return [y1]
    step = (yn - y1) / (n - 1)
    return [y1 + step * i for i in range(n)]


def _build_base_asm() -> ModelAssumptions:
    s = st.session_state
    n = PROJ_YEARS
    return ModelAssumptions(
        projection_years=n,
        revenue_growth=_interp(float(s["growth_y1"]), float(s["growth_yn"]), n),
        gross_margin=_interp(float(s["gm_y1"]), float(s["gm_yn"]), n),
        opex_pct_revenue=[float(s["opex_pct"])] * n,
        capex_pct_revenue=[float(s["capex_pct"])] * n,
        depreciation_pct_ppne=float(s["dep_pct"]),
        tax_rate=float(s["tax_rate"]),
        interest_rate_on_debt=float(s["int_rate"]),
        dividend_payout_ratio=float(s["div_payout"]),
        dso_days=[float(s["dso_days"])] * n,
        dio_days=[max(float(s["dio_days"]), 1.0)] * n,
        dpo_days=[max(float(s["dpo_days"]), 1.0)] * n,
        debt_amortization=[float(s["debt_amort"])] * n,
        target_min_cash_pct_revenue=0.03,
    )


def _shift_asm(base: ModelAssumptions, g_shift: float, m_shift: float) -> ModelAssumptions:
    asm = copy.deepcopy(base)
    asm.revenue_growth = [min(max(g + g_shift, -0.05), 0.30) for g in base.revenue_growth]
    asm.gross_margin = [min(max(m + m_shift, 0.03), 0.85) for m in base.gross_margin]
    return asm


def _asm_to_json(asm: ModelAssumptions) -> str:
    return json.dumps(dataclasses.asdict(asm), sort_keys=True)


@st.cache_data(show_spinner="Loading company data...")
def _load_data(ticker: str, csv_bytes: bytes | None) -> HistoricalData:
    if csv_bytes:
        hist = load_historical_data(ticker=ticker, csv_path=io.StringIO(csv_bytes.decode()))
    else:
        hist = load_historical_data(ticker=ticker)
    return hist


@st.cache_data(show_spinner="Searching tickers...")
def _search_company_options(query: str):
    return search_companies(query)


@st.cache_data(show_spinner="Loading research data...")
def _load_research_pack(ticker: str, profile_payload: str | None):
    profile = None
    if profile_payload:
        profile = CompanyProfile(**json.loads(profile_payload))
    return build_research_pack(ticker, profile=profile)


@st.cache_data(show_spinner="Running model...")
def _run_model(hist_json: str, ticker: str, asm_json: str):
    hist_df = pd.read_json(io.StringIO(hist_json))
    hist = HistoricalData(ticker=ticker, df=hist_df, annual_df=hist_df)
    asm = ModelAssumptions(**json.loads(asm_json))
    return run_three_statement_model(hist, asm)


@st.cache_data(show_spinner="Running sensitivity analysis...")
def _run_sensitivity(hist_json: str, ticker: str, asm_json: str, metric: str):
    hist_df = pd.read_json(io.StringIO(hist_json))
    hist = HistoricalData(ticker=ticker, df=hist_df, annual_df=hist_df)
    asm = ModelAssumptions(**json.loads(asm_json))
    return build_multi_output_sensitivity(hist, asm, output_metric=metric)


@st.cache_data(show_spinner="Building tornado chart...")
def _run_tornado(hist_json: str, ticker: str, asm_json: str, metric: str):
    hist_df = pd.read_json(io.StringIO(hist_json))
    hist = HistoricalData(ticker=ticker, df=hist_df, annual_df=hist_df)
    asm = ModelAssumptions(**json.loads(asm_json))
    return build_tornado_chart(hist, asm, output_metric=metric)


def _base_layout(height: int = 370) -> dict:
    return {
        "hovermode": "x unified",
        "height": height,
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        "margin": dict(l=18, r=18, t=52, b=18),
        "plot_bgcolor": "rgba(255,255,255,0.72)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font": dict(family="Lora, Georgia, serif", color="#0f172a"),
    }


def _line_chart(dfs: dict[str, pd.DataFrame], x: str, y: str, title: str, pct: bool = False) -> go.Figure:
    fig = go.Figure()
    for name, df in dfs.items():
        vals = df[y]
        texts = [_fp(v) for v in vals] if pct else [_fm(v) for v in vals]
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=vals,
                name=name,
                mode="lines+markers",
                line=dict(color=SCENARIO_COLORS[name], width=3),
                marker=dict(size=7),
                text=texts,
                hovertemplate="%{text}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_layout(title=title, **_base_layout())
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(31,41,51,0.08)", tickformat=".0%" if pct else None)
    return fig


def _single_line(df: pd.DataFrame, x: str, series: list[tuple[str, str, str]], title: str, pct: bool = False, height: int = 340) -> go.Figure:
    fig = go.Figure()
    for key, label, color in series:
        vals = df[key]
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=vals,
                name=label,
                mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(size=7),
                hovertemplate=("%{y:.1%}" if pct else "%{y:,.0f}") + f"<extra>{label}</extra>",
            )
        )
    fig.update_layout(title=title, **_base_layout(height))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(31,41,51,0.08)", tickformat=".0%" if pct else None)
    return fig


def _hero(profile_name: str | None, ticker: str, hist: HistoricalData) -> None:
    name = profile_name or ticker
    profile = hist.profile
    subtitle_bits = []
    if profile and profile.exchange:
        subtitle_bits.append(profile.exchange)
    if profile and profile.sector:
        subtitle_bits.append(profile.sector)
    if profile and profile.industry:
        subtitle_bits.append(profile.industry)
    subtitle = " • ".join(subtitle_bits) if subtitle_bits else "API-backed financial statements with annual and quarterly views"

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="small-label">Equity Research &amp; Forecasting Platform</div>
            <div class="hero-name">{name} <span style="opacity:0.65; font-weight:400;">({ticker})</span></div>
            <div class="hero-subtle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if profile:
        cols = st.columns(4)
        cols[0].metric("Current Price", f"${profile.current_price:,.2f}" if profile.current_price else "N/A")
        cols[1].metric("Market Cap", _fm(profile.market_cap / 1_000_000) if profile.market_cap else "N/A")
        cols[2].metric("Enterprise Value", _fm(profile.enterprise_value / 1_000_000) if profile.enterprise_value else "N/A")
        cols[3].metric("Shares Outstanding", f"{profile.shares_outstanding / 1_000_000:,.0f}M" if profile.shares_outstanding else "N/A")


def _profile_payload(hist: HistoricalData) -> str | None:
    if not hist.profile:
        return None
    return json.dumps(hist.profile.__dict__)


def _access_password() -> str | None:
    return os.getenv("APP_ACCESS_PASSWORD")


def _auth_gate() -> bool:
    password = _access_password()
    if not password:
        return True
    if st.session_state.get("is_authenticated"):
        return True

    st.markdown(
        """
        <div class="hero-card">
            <div class="small-label">Private Access</div>
            <div class="hero-name">Research Platform</div>
            <div class="hero-subtle">This deployment is access-restricted. Enter the password to continue.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    entered = st.text_input("Access password", type="password")
    if st.button("Enter Platform", type="primary", use_container_width=True):
        if entered == password:
            st.session_state["is_authenticated"] = True
            st.rerun()
        st.error("Incorrect password.")
    return False


def _sidebar_search() -> tuple[str, bytes | None, bool]:
    with st.sidebar:
        if _access_password():
            state = "Unlocked" if st.session_state.get("is_authenticated") else "Locked"
            st.caption(f"Access: {state}")

        st.markdown(
            """
            <div style="background:#e8f0f9;border:1px solid #b8cfe0;border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.6rem;">
                <div style="color:#0f4c81;font-family:'Playfair Display',Georgia,serif;font-size:1rem;font-weight:600;letter-spacing:0.01em;">
                    Search any public company
                </div>
                <div style="color:#4e5d6c;font-size:0.82rem;margin-top:0.2rem;">
                    Enter a name or ticker symbol below
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        query = st.text_input("Company name or ticker", key="search_query", placeholder="e.g. Apple, AAPL, Microsoft...")

        if len(query.strip()) >= 1:
            try:
                results = _search_company_options(query)
            except Exception as exc:
                results = []
                st.caption(f"Search unavailable: {exc}")
        else:
            results = []

        for idx, result in enumerate(results[:6]):
            with st.container(border=True):
                cols = st.columns([1, 3, 1.2])
                with cols[0]:
                    if result.logo_url:
                        try:
                            st.image(result.logo_url, width=30)
                        except Exception:
                            pass
                with cols[1]:
                    st.markdown(f"**{result.name or result.symbol}**")
                    st.caption(f"{result.symbol} • {result.exchange}")
                with cols[2]:
                    if st.button("Use ›", key=f"use_{result.symbol}_{idx}", use_container_width=True):
                        st.session_state["selected_ticker"] = result.symbol

        # Single source of truth: prefer explicitly selected ticker, else use typed query
        selected = st.session_state.get("selected_ticker", "")
        if selected:
            st.markdown(
                f"""
                <div style="background:#e8f0f9;border:1px solid #b8cfe0;border-radius:8px;padding:0.45rem 0.75rem;margin:0.4rem 0 0.2rem;">
                    <span style="font-size:0.75rem;color:#4e5d6c;font-family:'Lora',Georgia,serif;">Selected</span>
                    <span style="font-size:0.95rem;font-weight:600;color:#0f4c81;font-family:'Playfair Display',Georgia,serif;margin-left:0.4rem;">{selected}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Clear selection", key="clear_ticker", use_container_width=True):
                st.session_state["selected_ticker"] = ""
                st.rerun()
            ticker = selected
        else:
            ticker = query.strip().upper()

        st.divider()
        uploaded = st.file_uploader(
            "Or upload custom CSV",
            type=["csv"],
            help=(
                "For private companies or custom datasets only. "
                "Public company data is pulled automatically from SEC EDGAR and Yahoo Finance — no upload needed. "
                "See data/custom_historical_template.csv for the required column format."
            ),
        )
        csv_bytes = uploaded.read() if uploaded else None

        st.radio("Historical view", ["Full Year", "Quarterly"], horizontal=True, key="reporting_view")
        analyze_clicked = st.button("Analyze Company", use_container_width=True, type="primary")

        if ticker:
            st.divider()
            with st.expander("Forecast Assumptions", expanded=True):
                st.slider("Year 1 Revenue Growth", -0.10, 0.30, step=0.005, format="%.1f%%", key="growth_y1")
                st.slider(f"Year {PROJ_YEARS} Revenue Growth", -0.10, 0.30, step=0.005, format="%.1f%%", key="growth_yn")
                st.slider("Year 1 Gross Margin", 0.05, 0.85, step=0.005, format="%.1f%%", key="gm_y1")
                st.slider(f"Year {PROJ_YEARS} Gross Margin", 0.05, 0.85, step=0.005, format="%.1f%%", key="gm_yn")
                st.slider("OpEx % of Revenue", 0.01, 0.50, step=0.005, format="%.1f%%", key="opex_pct")
                st.slider("CapEx % of Revenue", 0.01, 0.20, step=0.005, format="%.1f%%", key="capex_pct")
                st.slider("Depreciation % of PP&E", 0.03, 0.35, step=0.005, format="%.1f%%", key="dep_pct")

            with st.expander("Working Capital", expanded=False):
                st.slider("DSO", 1, 120, step=1, key="dso_days")
                st.slider("DIO", 1, 120, step=1, key="dio_days")
                st.slider("DPO", 1, 120, step=1, key="dpo_days")

            with st.expander("Financing", expanded=False):
                st.slider("Tax Rate", 0.10, 0.40, step=0.005, format="%.1f%%", key="tax_rate")
                st.slider("Interest Rate on Debt", 0.01, 0.15, step=0.005, format="%.1f%%", key="int_rate")
                st.slider("Dividend Payout Ratio", 0.00, 0.80, step=0.01, format="%.0f%%", key="div_payout")
                st.slider("Annual Debt Amortization ($M)", 0, 5000, step=50, key="debt_amort")

            st.caption("Valuation covers DCF, trading comps, precedents, and LBO. Historical view toggles between annual and quarterly API pulls.")

    return ticker, csv_bytes, analyze_clicked


def _render_welcome() -> None:
    """Full-page welcome shown when no ticker is loaded yet."""
    st.markdown(
        """
        <div class="welcome-hero">
            <h1>Equity Research</h1>
            <p>
                Search any public company to load live financial statements, build a
                linked 3-statement model, run scenario and sensitivity analysis, and
                value the business across four methods — all in one workspace.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="landing-grid" style="max-width:900px; margin: 1.5rem auto 0;">
            <div class="landing-card">
                <div class="landing-icon"><span class="material-icons">analytics</span></div>
                <div class="landing-title">Market Data</div>
                <div class="landing-copy">Live peer comps, analyst price targets, earnings history, and precedent M&amp;A headlines pulled from the API.</div>
            </div>
            <div class="landing-card">
                <div class="landing-icon"><span class="material-icons">table_chart</span></div>
                <div class="landing-title">3-Statement Forecast</div>
                <div class="landing-copy">Annual and quarterly history auto-seeds a linked income statement, balance sheet, and cash flow — Base, Bull, and Bear.</div>
            </div>
            <div class="landing-card">
                <div class="landing-icon"><span class="material-icons">price_check</span></div>
                <div class="landing-title">4-Method Valuation</div>
                <div class="landing-copy">DCF, trading comps, precedent transactions, and LBO outputs displayed side by side for a complete valuation range.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="site-footer">
            Built by <a href="https://dmbriner.github.io/" target="_blank" rel="noopener noreferrer">Dana Briner</a>
            &nbsp;&middot;&nbsp; Equity research &amp; forecasting platform
        </div>
        """,
        unsafe_allow_html=True,
    )


def tab_home(hist: HistoricalData) -> None:
    name = hist.profile.name if hist.profile else hist.ticker
    st.markdown(
        f"""
        <div class="landing-grid">
            <div class="landing-card">
                <div class="landing-icon"><span class="material-icons">analytics</span></div>
                <div class="landing-title">Market Data</div>
                <div class="landing-copy">Live peer comps, analyst price targets, earnings history, and precedent M&amp;A headlines pulled directly from the API for {name}.</div>
            </div>
            <div class="landing-card">
                <div class="landing-icon"><span class="material-icons">table_chart</span></div>
                <div class="landing-title">3-Statement Forecast</div>
                <div class="landing-copy">Historical financials auto-seed a linked income statement, balance sheet, and cash flow across Base, Bull, and Bear scenarios.</div>
            </div>
            <div class="landing-card">
                <div class="landing-icon"><span class="material-icons">price_check</span></div>
                <div class="landing-title">4-Method Valuation</div>
                <div class="landing-copy">DCF, trading comps, precedent transactions, and LBO outputs displayed side by side for a complete valuation range.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Historical Views", "Annual + Quarterly")
    c2.metric("Valuation Methods", "4")
    c3.metric("Research Mode", "API-backed" if fmp_enabled() else "Ready")
    c4.metric("Export", "Excel")


def tab_overview(hist: HistoricalData, ticker: str) -> None:
    report_df, x_col = reporting_frame(hist, st.session_state["reporting_view"])
    annual_df = hist.annual().copy()
    base = annual_df.sort_values("year").iloc[-1]
    x_title = "Quarter" if st.session_state["reporting_view"] == "Quarterly" else "Fiscal Year"

    _glossary(["revenue", "cogs", "gross_profit", "ebitda", "cash", "debt"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", _fm(base["revenue"]))
    c2.metric("Gross Margin", _fp((base["revenue"] - base["cogs"]) / max(base["revenue"], 1)))
    c3.metric("Cash", _fm(base["cash"]))
    c4.metric("Debt", _fm(base["debt"]))

    report_df = report_df.copy()
    report_df["gross_profit"] = report_df["revenue"] - report_df["cogs"]
    report_df["gross_margin"] = report_df["gross_profit"] / report_df["revenue"].replace(0, pd.NA)
    report_df["ebitda"] = report_df["revenue"] - report_df["cogs"] - report_df["opex"]
    report_df["ebitda_margin"] = report_df["ebitda"] / report_df["revenue"].replace(0, pd.NA)

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=report_df[x_col], y=report_df["revenue"], name="Revenue", marker_color="#0f4c81"))
        fig.add_trace(go.Bar(x=report_df[x_col], y=-report_df["cogs"], name="COGS", marker_color="#b08968"))
        fig.update_layout(title=f"Revenue vs. COGS by {x_title}", barmode="relative", **_base_layout(360))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(31,41,51,0.08)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.plotly_chart(
            _single_line(
                report_df,
                x_col,
                [("gross_margin", "Gross Margin", "#0f4c81"), ("ebitda_margin", "EBITDA Margin", "#2d6a4f")],
                f"Historical Margins by {x_title}",
                pct=True,
                height=360,
            ),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(
            _single_line(
                report_df,
                x_col,
                [("cash", "Cash", "#0d7a5f"), ("debt", "Debt", "#a13d2d")],
                f"Cash and Debt by {x_title}",
            ),
            use_container_width=True,
        )
    with col4:
        report_df["nwc"] = report_df["accounts_receivable"] + report_df["inventory"] - report_df["accounts_payable"]
        st.plotly_chart(
            _single_line(
                report_df,
                x_col,
                [("accounts_receivable", "Accounts Receivable", "#0f4c81"), ("inventory", "Inventory", "#b08968"), ("nwc", "Net Working Capital", "#7f5539")],
                f"Working Capital Build by {x_title}",
            ),
            use_container_width=True,
        )

    with st.expander("Platform Scope", expanded=False):
        st.write(
            "This workspace now combines company search, logo/profile context, annual and quarterly history, "
            "driver analysis, linked-statement forecasting, sensitivity testing, and four valuation methods in one flow."
        )
        st.write(
            "The remaining limitation is data breadth for live peer sets and transaction comps. The current version lets you "
            "set market-based valuation assumptions directly, but it does not yet ingest a true comparable-company universe."
        )

    with st.expander("Historical Financial Data", expanded=False):
        show_cols = [c for c in [x_col, "revenue", "cogs", "opex", "depreciation", "interest_expense", "cash", "debt", "shares_outstanding", "capex"] if c in report_df.columns]
        st.dataframe(_format_display_df(report_df[show_cols]), use_container_width=True, hide_index=True)


def tab_drivers(metrics) -> None:
    _glossary(["revenue", "gross_profit", "ebitda", "tax_rate", "capex"])
    if metrics is None:
        st.info("Click Analyze Company to derive historical operating drivers and seed the model with company-specific defaults.")
        return

    top = st.columns(6)
    top[0].metric("Revenue CAGR", _fp(metrics.revenue_growth_cagr))
    top[1].metric("Avg Gross Margin", _fp(metrics.gross_margin_avg))
    top[2].metric("Avg EBITDA Margin", _fp(metrics.ebitda_margin_avg))
    top[3].metric("Avg DSO", f"{metrics.dso_avg:.0f} days")
    top[4].metric("Avg CapEx %", _fp(metrics.capex_pct_avg))
    top[5].metric("Avg Net Leverage", f"{metrics.net_leverage_avg:.1f}x")

    notes = [
        ("Growth", metrics.growth_note),
        ("Margins", metrics.margin_note),
        ("Capital Intensity", metrics.capex_note),
        ("Working Capital", metrics.wc_note),
        ("Financing", metrics.financing_note),
    ]
    for title, note in notes:
        with st.expander(title, expanded=True):
            st.write(note)


def tab_income(outputs: dict[str, object]) -> None:
    _glossary(["revenue", "cogs", "gross_profit", "ebitda", "ebit", "net_income", "eps"])

    row1 = st.columns(2)
    with row1[0]:
        st.plotly_chart(_line_chart({n: o.income_statement for n, o in outputs.items()}, "year", "revenue", "Revenue"), use_container_width=True)
    with row1[1]:
        st.plotly_chart(_line_chart({n: o.income_statement for n, o in outputs.items()}, "year", "ebitda", "EBITDA"), use_container_width=True)

    row2 = st.columns(2)
    with row2[0]:
        st.plotly_chart(_line_chart({n: o.income_statement for n, o in outputs.items()}, "year", "ebit", "EBIT"), use_container_width=True)
    with row2[1]:
        st.plotly_chart(_line_chart({n: o.income_statement for n, o in outputs.items()}, "year", "net_income", "Net Income"), use_container_width=True)

    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="income_scen")
    is_df = outputs[scen].income_statement.copy()
    is_df["gross_margin_%"] = is_df["gross_profit"] / is_df["revenue"].replace(0, pd.NA)
    is_df["ebitda_margin_%"] = is_df["ebitda"] / is_df["revenue"].replace(0, pd.NA)
    is_df["net_margin_%"] = is_df["net_income"] / is_df["revenue"].replace(0, pd.NA)

    st.plotly_chart(
        _single_line(
            is_df,
            "year",
            [("gross_margin_%", "Gross Margin", "#0f4c81"), ("ebitda_margin_%", "EBITDA Margin", "#2d6a4f"), ("net_margin_%", "Net Margin", "#a13d2d")],
            f"Margin Stack: {scen}",
            pct=True,
            height=340,
        ),
        use_container_width=True,
    )
    st.dataframe(
        _format_display_df(is_df, pct_cols={"gross_margin_%", "ebitda_margin_%", "net_margin_%"}, per_share_cols={"eps"}),
        use_container_width=True,
        hide_index=True,
    )


def tab_balance_sheet(outputs: dict[str, object]) -> None:
    _glossary(["cash", "accounts_receivable", "inventory", "accounts_payable", "ppne", "debt", "nwc"])
    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="bs_scen")
    output = outputs[scen]
    bs = output.balance_sheet.copy()
    integ = check_integrity(output)

    if integ.all_clear:
        st.success("All integrity checks passed.")
    else:
        for warning in integ.warnings[:6]:
            st.warning(warning)

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        for key, label, color in [
            ("cash", "Cash", "#0d7a5f"),
            ("accounts_receivable", "Accounts Receivable", "#0f4c81"),
            ("inventory", "Inventory", "#b08968"),
            ("ppne", "PP&E", "#7f5539"),
        ]:
            fig.add_trace(go.Bar(x=bs["year"], y=bs[key], name=label, marker_color=color))
        fig.update_layout(title=f"Asset Mix: {scen}", barmode="stack", **_base_layout(360))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(31,41,51,0.08)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.plotly_chart(
            _single_line(
                bs,
                "year",
                [("total_assets", "Total Assets", "#0f4c81"), ("total_liabilities_and_equity", "Liabilities + Equity", "#2d6a4f"), ("debt", "Debt", "#a13d2d")],
                f"Balance Sheet Structure: {scen}",
                height=360,
            ),
            use_container_width=True,
        )

    st.dataframe(_format_display_df(bs), use_container_width=True, hide_index=True)


def tab_cash_flow(outputs: dict[str, object]) -> None:
    _glossary(["cfo", "cfi", "cff", "fcf", "capex", "depreciation", "nwc"])
    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="cf_scen")
    output = outputs[scen]
    cf = output.cash_flow.copy()
    fcf = output.fcf.copy()

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        for label, col_name, color in [("CFO", "cfo", "#0f4c81"), ("CFI", "cfi", "#b08968"), ("CFF", "cff", "#7f5539")]:
            fig.add_trace(go.Bar(x=cf["year"], y=cf[col_name], name=label, marker_color=color))
        fig.add_trace(go.Scatter(x=cf["year"], y=cf["net_change_cash"], name="Net Change in Cash", mode="lines+markers", line=dict(color="#2d6a4f", width=3)))
        fig.update_layout(title=f"Cash Flow Components: {scen}", barmode="group", **_base_layout(370))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="rgba(31,41,51,0.08)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fcf["fcf_conversion"] = fcf["fcf"] / fcf["ebitda"].replace(0, pd.NA)
        st.plotly_chart(
            _single_line(
                fcf,
                "year",
                [("fcf", "Free Cash Flow", "#0d7a5f"), ("ebitda", "EBITDA", "#0f4c81")],
                f"FCF and EBITDA: {scen}",
                height=370,
            ),
            use_container_width=True,
        )

    st.plotly_chart(
        _single_line(
            fcf,
            "year",
            [("fcf_conversion", "FCF / EBITDA", "#a13d2d")],
            f"FCF Conversion: {scen}",
            pct=True,
            height=310,
        ),
        use_container_width=True,
    )

    st.dataframe(_format_display_df(cf), use_container_width=True, hide_index=True)


def tab_schedules(outputs: dict[str, object], base_asm: ModelAssumptions) -> None:
    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="sched_scen")
    output = outputs[scen]
    tabs = st.tabs(["PP&E", "Working Capital", "Debt", "Equity"])
    base_asm.normalize()

    with tabs[0]:
        _glossary(["ppne", "capex", "depreciation"])
        ppe = output.ppe_schedule.copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=ppe["year"], y=ppe["beginning_ppne"], name="Beginning PP&E", marker_color="#c8d5b9"))
        fig.add_trace(go.Bar(x=ppe["year"], y=ppe["capex"], name="CapEx", marker_color="#b08968"))
        fig.add_trace(go.Bar(x=ppe["year"], y=-ppe["depreciation"], name="Depreciation", marker_color="#a13d2d"))
        fig.add_trace(go.Scatter(x=ppe["year"], y=ppe["ending_ppne"], name="Ending PP&E", mode="lines+markers", line=dict(color="#0f4c81", width=3)))
        fig.update_layout(title=f"PP&E Schedule: {scen}", barmode="relative", **_base_layout(360))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(_format_display_df(ppe), use_container_width=True, hide_index=True)

    with tabs[1]:
        _glossary(["accounts_receivable", "inventory", "accounts_payable", "nwc"])
        wc_df = pd.DataFrame(
            {
                "year": output.balance_sheet["year"].tolist(),
                "dso": base_asm.dso_days[: len(output.balance_sheet)],
                "dio": base_asm.dio_days[: len(output.balance_sheet)],
                "dpo": base_asm.dpo_days[: len(output.balance_sheet)],
            }
        )
        st.plotly_chart(
            _single_line(
                wc_df,
                "year",
                [("dso", "DSO", "#0f4c81"), ("dio", "DIO", "#b08968"), ("dpo", "DPO", "#2d6a4f")],
                f"Working Capital Days: {scen}",
                height=330,
            ),
            use_container_width=True,
        )
        bs_wc = output.balance_sheet[["year", "accounts_receivable", "inventory", "accounts_payable", "nwc"]].copy()
        st.dataframe(_format_display_df(bs_wc), use_container_width=True, hide_index=True)

    with tabs[2]:
        _glossary(["debt", "interest_expense", "cash"])
        debt = output.debt_schedule.copy()
        st.plotly_chart(
            _single_line(
                debt,
                "year",
                [("beginning_debt", "Beginning Debt", "#a13d2d"), ("ending_debt", "Ending Debt", "#0f4c81"), ("interest_expense", "Interest Expense", "#7f5539")],
                f"Debt Schedule: {scen}",
                height=330,
            ),
            use_container_width=True,
        )
        st.dataframe(_format_display_df(debt), use_container_width=True, hide_index=True)

    with tabs[3]:
        eq = output.equity_schedule.copy()
        st.dataframe(_format_display_df(eq), use_container_width=True, hide_index=True)


def tab_sensitivity(outputs: dict[str, object], hist_df: pd.DataFrame, ticker: str, base_asm: ModelAssumptions) -> None:
    metric = st.selectbox(
        "Sensitivity metric",
        ["fcf", "ebitda", "net_income"],
        format_func=lambda x: {"fcf": "Free Cash Flow", "ebitda": "EBITDA", "net_income": "Net Income"}[x],
        key="sens_metric",
    )
    metric_label = {"fcf": "FCF", "ebitda": "EBITDA", "net_income": "Net Income"}[metric]
    _glossary(["fcf", "ebitda", "net_income"])

    cols = st.columns(3)
    for col, name in zip(cols, ["Base", "Bull", "Bear"]):
        frame = outputs[name].fcf if metric == "fcf" else outputs[name].income_statement
        col_name = "fcf" if metric == "fcf" else metric
        col.metric(f"{name} Avg {metric_label}", _fm(frame[col_name].mean()))

    hist_json = hist_df.to_json()
    asm_json = _asm_to_json(base_asm)
    sens_df = _run_sensitivity(hist_json, ticker, asm_json, metric)
    tornado_df = _run_tornado(hist_json, ticker, asm_json, metric)

    heat = px.imshow(
        sens_df.values.astype(float),
        x=[f"{v:+.0%}" for v in sens_df.columns],
        y=[f"{v:+.0%}" for v in sens_df.index],
        color_continuous_scale=["#a13d2d", "#f3e9dc", "#2d6a4f"],
        text_auto=".0f",
        labels={"x": "Gross Margin Shock", "y": "Revenue Growth Shock", "color": f"Avg {metric_label}"},
        title=f"Sensitivity: Avg {metric_label}",
    )
    heat.update_layout(**_base_layout(370))
    st.plotly_chart(heat, use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(y=tornado_df["assumption"], x=tornado_df["high_vs_base"], name="High case", orientation="h", marker_color="#2d6a4f"))
    fig.add_trace(go.Bar(y=tornado_df["assumption"], x=tornado_df["low_vs_base"], name="Low case", orientation="h", marker_color="#a13d2d"))
    fig.update_layout(title=f"Tornado: Impact on Avg {metric_label}", barmode="overlay", **_base_layout(max(320, len(tornado_df) * 44)))
    st.plotly_chart(fig, use_container_width=True)


def tab_valuation(outputs: dict[str, object], hist: HistoricalData) -> None:
    research = None
    if fmp_enabled():
        try:
            research = _load_research_pack(hist.ticker, _profile_payload(hist))
        except Exception:
            research = None

    scen = st.selectbox("Scenario to value", ["Base", "Bull", "Bear"], key="val_scen")
    output = outputs[scen]
    annual_df = hist.annual().sort_values("year")
    latest_hist = annual_df.iloc[-1]
    is_last = output.income_statement.iloc[-1]
    fcf_df = output.fcf.copy()
    fcf_list = fcf_df["fcf"].tolist()
    ebitda_list = fcf_df["ebitda"].tolist()
    shares = _safe_float(latest_hist["shares_outstanding"])
    net_debt = _safe_float(output.balance_sheet.iloc[-1]["debt"]) - _safe_float(output.balance_sheet.iloc[-1]["cash"])
    revenue = _safe_float(is_last["revenue"])
    ebitda = _safe_float(is_last["ebitda"])
    eps = _safe_float(is_last["eps"])

    current_ev = _safe_float(hist.profile.enterprise_value if hist.profile else None)
    current_price = _safe_float(hist.profile.current_price if hist.profile else None)
    comp_ev_rev_default = current_ev / revenue if current_ev and revenue else 2.0
    comp_ev_ebitda_default = current_ev / ebitda if current_ev and ebitda else 9.0
    comp_pe_default = current_price / eps if current_price and eps > 0 else 18.0
    if research and research.peers:
        peer_df = pd.DataFrame([p.__dict__ for p in research.peers])
        if "ev_revenue" in peer_df.columns and peer_df["ev_revenue"].notna().any():
            comp_ev_rev_default = float(peer_df["ev_revenue"].dropna().median())
        if "ev_ebitda" in peer_df.columns and peer_df["ev_ebitda"].notna().any():
            comp_ev_ebitda_default = float(peer_df["ev_ebitda"].dropna().median())
        if "pe_ratio" in peer_df.columns and peer_df["pe_ratio"].notna().any():
            comp_pe_default = float(peer_df["pe_ratio"].dropna().median())

    colw, colg = st.columns(2)
    with colw:
        wacc = st.slider("WACC", 0.05, 0.18, float(st.session_state.get("wacc", 0.09)), step=0.005, format="%.1f%%")
    with colg:
        tg = st.slider("Terminal Growth", 0.00, 0.05, float(st.session_state.get("term_growth", 0.025)), step=0.005, format="%.1f%%")

    if wacc <= tg:
        st.error("WACC must be greater than terminal growth.")
        return

    try:
        dcf_result = run_dcf(fcf_list, ebitda_list, wacc, tg, net_debt, shares)
    except ValueError as exc:
        st.error(str(exc))
        return

    st.markdown("#### Trading Comps")
    _glossary(["enterprise_value", "equity_value", "value_per_share", "revenue", "ebitda", "eps"])
    c1, c2, c3 = st.columns(3)
    with c1:
        comp_ev_rev = st.slider("EV / Revenue", 0.5, 12.0, float(min(max(comp_ev_rev_default, 0.5), 12.0)), step=0.1)
    with c2:
        comp_ev_ebitda = st.slider("EV / EBITDA", 2.0, 25.0, float(min(max(comp_ev_ebitda_default, 2.0), 25.0)), step=0.25)
    with c3:
        comp_pe = st.slider("P / E", 5.0, 40.0, float(min(max(comp_pe_default, 5.0), 40.0)), step=0.5)

    comps_results = [
        run_multiple_valuation("Trading EV / Revenue", revenue, comp_ev_rev, net_debt, shares, "Revenue"),
        run_multiple_valuation("Trading EV / EBITDA", ebitda, comp_ev_ebitda, net_debt, shares, "EBITDA"),
        run_multiple_valuation("Trading P / E", max(eps, 0.0) * shares, comp_pe, 0.0, shares, "Net Income"),
    ]

    st.markdown("#### Precedent Transactions")
    p1, p2, p3 = st.columns(3)
    with p1:
        precedent_rev = st.slider("Precedent EV / Revenue", 0.5, 14.0, float(min(max(comp_ev_rev + 0.4, 0.5), 14.0)), step=0.1)
    with p2:
        precedent_ebitda = st.slider("Precedent EV / EBITDA", 2.0, 30.0, float(min(max(comp_ev_ebitda + 1.0, 2.0), 30.0)), step=0.25)
    with p3:
        control_premium = st.slider("Control Premium", 0.0, 0.50, 0.25, step=0.01, format="%.0f%%")

    precedent_results = run_precedent_transactions(revenue, ebitda, net_debt, shares, precedent_rev, precedent_ebitda, control_premium)

    st.markdown("#### LBO")
    l1, l2, l3, l4 = st.columns(4)
    with l1:
        entry_multiple = st.slider("Entry EV / EBITDA", 4.0, 18.0, float(min(max(comp_ev_ebitda, 4.0), 18.0)), step=0.25)
    with l2:
        exit_multiple = st.slider("Exit EV / EBITDA", 4.0, 18.0, float(min(max(comp_ev_ebitda - 0.5, 4.0), 18.0)), step=0.25)
    with l3:
        debt_multiple = st.slider("Debt / EBITDA", 1.0, 8.0, 4.5, step=0.25)
    with l4:
        lbo_rate = st.slider("LBO Interest Rate", 0.04, 0.16, float(st.session_state.get("int_rate", 0.08)), step=0.005, format="%.1f%%")

    lbo_result = run_lbo(ebitda_list, fcf_list, net_debt, shares, entry_multiple, exit_multiple, debt_multiple, lbo_rate)
    summary = valuation_summary_table(dcf_result, comps_results, precedent_results, lbo_result)

    with st.expander("Valuation Framework", expanded=False):
        st.write("DCF values projected free cash flow using WACC and terminal growth.")
        st.write("Trading comps translate market multiples into implied enterprise and equity value.")
        st.write("Precedent transactions apply takeover-style multiples plus a control premium.")
        st.write("LBO estimates what a sponsor could pay while still reaching an acceptable exit return.")

    top = st.columns(4)
    top[0].metric("DCF Per Share", f"${dcf_result.value_per_share:,.2f}")
    top[1].metric("Comps Midpoint", f"${pd.Series([r.value_per_share for r in comps_results]).median():,.2f}")
    top[2].metric("Precedent Midpoint", f"${pd.Series([r.value_per_share for r in precedent_results]).median():,.2f}")
    top[3].metric("LBO Per Share", f"${lbo_result.value_per_share:,.2f}")

    fig = go.Figure(
        go.Bar(
            x=summary["Method"],
            y=summary["Per Share"],
            marker_color=VALUE_METHOD_COLORS[: len(summary)],
            text=[f"${v:,.2f}" for v in summary["Per Share"]],
            textposition="outside",
        )
    )
    fig.update_layout(title=f"Valuation Range by Method: {scen}", **_base_layout(380))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(31,41,51,0.08)")
    st.plotly_chart(fig, use_container_width=True)

    bridge = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "total", "relative", "total"],
            x=["PV of FCF", "PV of Terminal Value", "Enterprise Value", "Net Debt", "Equity Value"],
            y=[dcf_result.pv_fcf_sum, dcf_result.pv_terminal_value, 0, -dcf_result.net_debt, 0],
            increasing={"marker": {"color": "#2d6a4f"}},
            decreasing={"marker": {"color": "#a13d2d"}},
            totals={"marker": {"color": "#0f4c81"}},
        )
    )
    bridge.update_layout(title="DCF Bridge", **_base_layout(370))

    heat = px.imshow(
        wacc_terminal_sensitivity(fcf_list, ebitda_list, net_debt, shares).values.astype(float),
        x=[f"{v:.1%}" for v in wacc_terminal_sensitivity(fcf_list, ebitda_list, net_debt, shares).columns],
        y=[f"{v:.0%}" for v in wacc_terminal_sensitivity(fcf_list, ebitda_list, net_debt, shares).index],
        color_continuous_scale=["#a13d2d", "#f3e9dc", "#2d6a4f"],
        text_auto=".1f",
        labels={"x": "Terminal Growth", "y": "WACC", "color": "Per Share"},
        title="DCF Sensitivity Grid",
    )
    heat.update_layout(**_base_layout(370))

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(bridge, use_container_width=True)
    with col2:
        st.plotly_chart(heat, use_container_width=True)

    st.dataframe(_format_display_df(summary, per_share_cols={"Per Share"}), use_container_width=True, hide_index=True)

    lbo_cols = st.columns(5)
    lbo_cols[0].metric("LBO Entry EV", _fm(lbo_result.entry_ev))
    lbo_cols[1].metric("Debt Funding", _fm(lbo_result.debt_funding))
    lbo_cols[2].metric("Sponsor Equity", _fm(lbo_result.sponsor_equity))
    lbo_cols[3].metric("MOIC", f"{lbo_result.moic:.2f}x")
    lbo_cols[4].metric("IRR", _fp(lbo_result.irr))


def tab_research(hist: HistoricalData) -> None:
    st.markdown("### Research Workspace")
    if not fmp_enabled():
        st.info("Set `FMP_API_KEY` to enable live peer comps, analyst data, earnings events, and precedent transaction feeds.")
        return

    try:
        research = _load_research_pack(hist.ticker, _profile_payload(hist))
    except Exception as exc:
        st.warning(f"Research data is unavailable right now: {exc}")
        return

    st.caption(f"Provider: {research.provider}")

    tabs = st.tabs(["Peer Comps", "Analyst View", "Earnings", "Precedents"])

    with tabs[0]:
        if not research.peers:
            st.info("No peer set returned by the market-data provider.")
        else:
            peer_df = pd.DataFrame([peer.__dict__ for peer in research.peers])
            top = st.columns(4)
            top[0].metric("Peer Count", f"{len(peer_df)}")
            top[1].metric("Median EV / Revenue", f"{peer_df['ev_revenue'].dropna().median():.1f}x" if peer_df["ev_revenue"].notna().any() else "N/A")
            top[2].metric("Median EV / EBITDA", f"{peer_df['ev_ebitda'].dropna().median():.1f}x" if peer_df["ev_ebitda"].notna().any() else "N/A")
            top[3].metric("Median P / E", f"{peer_df['pe_ratio'].dropna().median():.1f}x" if peer_df["pe_ratio"].notna().any() else "N/A")

            fig = go.Figure()
            fig.add_trace(go.Bar(x=peer_df["symbol"], y=peer_df["ev_ebitda"], name="EV / EBITDA", marker_color="#0f4c81"))
            fig.add_trace(go.Scatter(x=peer_df["symbol"], y=peer_df["ev_revenue"], name="EV / Revenue", mode="lines+markers", line=dict(color="#b08968", width=3)))
            fig.update_layout(title="Peer Trading Multiples", **_base_layout(360))
            st.plotly_chart(fig, use_container_width=True)

            show_cols = ["symbol", "name", "sector", "industry", "market_cap", "enterprise_value", "price", "ev_revenue", "ev_ebitda", "pe_ratio"]
            formatted = peer_df[show_cols].copy()
            for col in ["market_cap", "enterprise_value"]:
                formatted[col] = formatted[col].apply(lambda v: _fm(v / 1_000_000) if pd.notna(v) else "—")
            formatted["price"] = formatted["price"].apply(lambda v: f"${v:,.2f}" if pd.notna(v) else "—")
            for col in ["ev_revenue", "ev_ebitda", "pe_ratio"]:
                formatted[col] = formatted[col].apply(lambda v: f"{v:.1f}x" if pd.notna(v) else "—")
            formatted.columns = ["Ticker", "Company", "Sector", "Industry", "Market Cap", "Enterprise Value", "Price", "EV / Revenue", "EV / EBITDA", "P / E"]
            st.dataframe(formatted, use_container_width=True, hide_index=True)

    with tabs[1]:
        snap = research.analyst_snapshot
        if snap is None:
            st.info("No analyst snapshot returned.")
        else:
            top = st.columns(5)
            top[0].metric("Consensus PT", f"${snap.target_consensus:,.2f}" if snap.target_consensus else "N/A")
            top[1].metric("Median PT", f"${snap.target_median:,.2f}" if snap.target_median else "N/A")
            top[2].metric("High PT", f"${snap.target_high:,.2f}" if snap.target_high else "N/A")
            top[3].metric("Low PT", f"${snap.target_low:,.2f}" if snap.target_low else "N/A")
            top[4].metric("Analysts", f"{snap.analyst_count}" if snap.analyst_count else "N/A")

            est_df = pd.DataFrame(
                [
                    {"Period": "Current Year", "Revenue Estimate": snap.revenue_estimate_current_year, "EPS Estimate": snap.eps_estimate_current_year},
                    {"Period": "Next Year", "Revenue Estimate": snap.revenue_estimate_next_year, "EPS Estimate": snap.eps_estimate_next_year},
                ]
            )
            est_df["Revenue Estimate"] = est_df["Revenue Estimate"].apply(lambda v: _fm(v / 1_000_000) if pd.notna(v) and v else "—")
            est_df["EPS Estimate"] = est_df["EPS Estimate"].apply(lambda v: f"${v:,.2f}" if pd.notna(v) and v else "—")
            st.dataframe(est_df, use_container_width=True, hide_index=True)

    with tabs[2]:
        if not research.earnings_events:
            st.info("No earnings events returned.")
        else:
            earn_df = pd.DataFrame([event.__dict__ for event in research.earnings_events])
            fig = go.Figure()
            fig.add_trace(go.Bar(x=earn_df["date"], y=earn_df["eps_estimated"], name="Estimated EPS", marker_color="#b08968"))
            fig.add_trace(go.Bar(x=earn_df["date"], y=earn_df["eps_actual"], name="Actual EPS", marker_color="#0f4c81"))
            fig.update_layout(title="Recent Earnings: Estimated vs Actual EPS", barmode="group", **_base_layout(340))
            st.plotly_chart(fig, use_container_width=True)
            for col in ["eps_estimated", "eps_actual"]:
                earn_df[col] = earn_df[col].apply(lambda v: f"${v:,.2f}" if pd.notna(v) else "—")
            for col in ["revenue_estimated", "revenue_actual"]:
                earn_df[col] = earn_df[col].apply(lambda v: _fm(v / 1_000_000) if pd.notna(v) and v else "—")
            earn_df.columns = ["Date", "Estimated EPS", "Actual EPS", "Estimated Revenue", "Actual Revenue", "Fiscal Period End"]
            st.dataframe(earn_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        if not research.precedents:
            st.info("No relevant precedent transactions returned.")
        else:
            prec_df = pd.DataFrame([event.__dict__ for event in research.precedents])
            prec_df.columns = ["Published Date", "Headline", "Link"]
            st.dataframe(prec_df, use_container_width=True, hide_index=True)


def tab_interpretation(outputs: dict[str, object], ticker: str, metrics) -> None:
    scen = st.selectbox("Scenario", ["Base", "Bull", "Bear"], key="interp_scen")
    output = outputs[scen]
    is_df = output.income_statement
    bs_df = output.balance_sheet
    fcf_df = output.fcf

    rev_y1 = is_df["revenue"].iloc[0]
    rev_yn = is_df["revenue"].iloc[-1]
    rev_cagr = (rev_yn / rev_y1) ** (1 / max(len(is_df) - 1, 1)) - 1 if rev_y1 > 0 and len(is_df) > 1 else 0
    gm_y1 = is_df["gross_profit"].iloc[0] / is_df["revenue"].iloc[0]
    gm_yn = is_df["gross_profit"].iloc[-1] / is_df["revenue"].iloc[-1]
    avg_fcf = fcf_df["fcf"].mean()
    avg_ebitda = is_df["ebitda"].mean()
    fcf_conv = avg_fcf / avg_ebitda if avg_ebitda > 0 else 0
    lev_y1 = (bs_df.iloc[0]["debt"] - bs_df.iloc[0]["cash"]) / max(is_df["ebitda"].iloc[0], 1)
    lev_yn = (bs_df.iloc[-1]["debt"] - bs_df.iloc[-1]["cash"]) / max(is_df["ebitda"].iloc[-1], 1)

    st.write(
        f"{ticker} is modeled to grow revenue from {_fm(rev_y1)} to {_fm(rev_yn)}, which implies a {_fp(rev_cagr)} CAGR. "
        f"Gross margin moves from {_fp(gm_y1)} to {_fp(gm_yn)}, while average annual FCF is {_fm(avg_fcf)} with {_fp(fcf_conv)} FCF conversion."
    )
    if metrics is not None:
        st.write(
            f"Relative to history, the forecast uses a trailing revenue CAGR benchmark of {_fp(metrics.revenue_growth_cagr)} "
            f"and average gross margin of {_fp(metrics.gross_margin_avg)}."
        )
    st.write(
        f"Net leverage changes from {lev_y1:.1f}x to {lev_yn:.1f}x over the forecast. Use the sensitivity and valuation tabs to test whether that "
        "capital structure stays acceptable across downside cases."
    )


def _render_export_button(outputs: dict, hist_df: pd.DataFrame, base_asm: ModelAssumptions) -> None:
    """Render an Excel download button in the sidebar using the Base scenario output."""
    base_out = outputs.get("Base")
    if base_out is None:
        return
    try:
        from model_engine.sensitivity import build_sensitivity_table
        sensitivity = build_sensitivity_table(
            HistoricalData(ticker="export", df=hist_df, annual_df=hist_df),
            base_asm,
        )
    except Exception:
        sensitivity = pd.DataFrame()
    try:
        excel_bytes = build_excel_bytes(base_out, sensitivity, hist_df)
    except Exception:
        return
    st.download_button(
        label="Export to Excel",
        data=excel_bytes,
        file_name="3statement_model.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def _inject_secrets() -> None:
    """Expose Streamlit secrets as environment variables so model_engine modules can read them."""
    _SECRET_KEYS = ("FMP_API_KEY", "FINANCIAL_MODELING_PREP_API_KEY", "ALPHA_VANTAGE_API_KEY", "APP_ACCESS_PASSWORD")
    try:
        for key in _SECRET_KEYS:
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass


def main() -> None:
    st.set_page_config(page_title="3-Statement Model", layout="wide", initial_sidebar_state="expanded")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    _inject_secrets()
    _init_session_state()
    if not _auth_gate():
        return

    ticker, csv_bytes, analyze_clicked = _sidebar_search()

    if not ticker and not csv_bytes:
        _render_welcome()
        return

    try:
        hist = _load_data(ticker, csv_bytes)
    except Exception as exc:
        msg = str(exc)
        st.error(f"Could not load data for **{ticker}**: {msg}")
        if "not found in SEC EDGAR" in msg or "not a US-listed" in msg:
            st.info(
                "This ticker wasn't found in SEC EDGAR. If it's a US public company, "
                "try the exact exchange symbol (e.g. BRK-B not BRKB). "
                "For international companies, data will load via Yahoo Finance — "
                "click **Analyze Company** again."
            )
        else:
            st.info("Try a different ticker or upload a CSV with historical financials.")
        return

    if analyze_clicked:
        try:
            metrics = analyze_historical_data(HistoricalData(ticker=ticker, df=hist.annual(), annual_df=hist.annual()))
            smart = suggest_scenarios(metrics, years=PROJ_YEARS)["Base"]
            st.session_state["metrics"] = metrics
            st.session_state["growth_y1"] = round(float(smart.revenue_growth[0]), 4)
            st.session_state["growth_yn"] = round(float(smart.revenue_growth[-1]), 4)
            st.session_state["gm_y1"] = round(float(smart.gross_margin[0]), 4)
            st.session_state["gm_yn"] = round(float(smart.gross_margin[-1]), 4)
            st.session_state["opex_pct"] = round(float(smart.opex_pct_revenue[0]), 4)
            st.session_state["capex_pct"] = round(float(smart.capex_pct_revenue[0]), 4)
            st.session_state["dep_pct"] = round(float(smart.depreciation_pct_ppne), 4)
            st.session_state["tax_rate"] = round(float(smart.tax_rate), 4)
            st.session_state["int_rate"] = round(float(smart.interest_rate_on_debt), 4)
            st.session_state["div_payout"] = round(float(smart.dividend_payout_ratio), 4)
            st.session_state["dso_days"] = max(int(round(smart.dso_days[0])), 1)
            st.session_state["dio_days"] = max(int(round(smart.dio_days[0])), 1)
            st.session_state["dpo_days"] = max(int(round(smart.dpo_days[0])), 1)
            st.session_state["debt_amort"] = int(round(float(smart.debt_amortization[0])))
        except Exception as exc:
            st.warning(f"Historical analysis could not auto-seed assumptions: {exc}")

    annual_df = hist.annual().copy()
    metrics = st.session_state.get("metrics")
    if metrics is None:
        try:
            metrics = analyze_historical_data(HistoricalData(ticker=ticker, df=annual_df, annual_df=annual_df))
            st.session_state["metrics"] = metrics
        except Exception:
            metrics = None

    profile_name = hist.profile.name if hist.profile else None
    _hero(profile_name, ticker, hist)

    base_asm = _build_base_asm()
    scenarios = {
        "Base": base_asm,
        "Bull": _shift_asm(base_asm, 0.025, 0.015),
        "Bear": _shift_asm(base_asm, -0.025, -0.02),
    }

    hist_json = annual_df.to_json()
    outputs = {name: _run_model(hist_json, ticker, _asm_to_json(asm)) for name, asm in scenarios.items()}

    with st.sidebar:
        st.divider()
        _render_export_button(outputs, annual_df, base_asm)

    tabs = st.tabs(
        ["Home", "Overview", "Research", "Drivers", "Income Statement", "Balance Sheet", "Cash Flow", "Schedules", "Sensitivity", "Valuation", "Interpretation"]
    )
    with tabs[0]:
        tab_home(hist)
    with tabs[1]:
        tab_overview(hist, ticker)
    with tabs[2]:
        tab_research(hist)
    with tabs[3]:
        tab_drivers(metrics)
    with tabs[4]:
        tab_income(outputs)
    with tabs[5]:
        tab_balance_sheet(outputs)
    with tabs[6]:
        tab_cash_flow(outputs)
    with tabs[7]:
        tab_schedules(outputs, base_asm)
    with tabs[8]:
        tab_sensitivity(outputs, annual_df, ticker, base_asm)
    with tabs[9]:
        tab_valuation(outputs, hist)
    with tabs[10]:
        tab_interpretation(outputs, ticker, metrics)

    st.markdown(
        """
        <div class="site-footer">
            Built by <a href="https://dmbriner.github.io/" target="_blank" rel="noopener noreferrer">Dana Briner</a>
            &nbsp;&middot;&nbsp;
            Equity research &amp; forecasting platform
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
