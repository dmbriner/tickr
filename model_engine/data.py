from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "year",
    "revenue",
    "cogs",
    "opex",
    "depreciation",
    "interest_expense",
    "tax_rate",
    "cash",
    "accounts_receivable",
    "inventory",
    "accounts_payable",
    "ppne",
    "debt",
    "shares_outstanding",
    "capex",
]


@dataclass
class HistoricalData:
    ticker: str
    df: pd.DataFrame


def _validate_historical_df(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Historical input is missing required columns: {missing}")

    cleaned = df.copy()
    cleaned = cleaned[REQUIRED_COLUMNS]
    cleaned = cleaned.sort_values("year").reset_index(drop=True)
    return cleaned


def _load_from_csv(csv_path: str | Path, ticker: str) -> HistoricalData:
    df = pd.read_csv(csv_path)
    return HistoricalData(ticker=ticker, df=_validate_historical_df(df))


def _load_from_yfinance(ticker: str) -> HistoricalData:
    import yfinance as yf

    tk = yf.Ticker(ticker)
    is_df = tk.financials.T
    bs_df = tk.balance_sheet.T
    cf_df = tk.cashflow.T

    if is_df.empty or bs_df.empty or cf_df.empty:
        raise ValueError(f"Could not fetch complete financial statements for {ticker}")

    rows = []
    year_index = is_df.index.intersection(bs_df.index).intersection(cf_df.index)

    for dt in sorted(year_index):
        year = dt.year

        def get(df: pd.DataFrame, key: str, default: float = 0.0) -> float:
            if key in df.columns and pd.notna(df.loc[dt, key]):
                return float(df.loc[dt, key])
            return default

        revenue = get(is_df, "Total Revenue")
        cogs = abs(get(is_df, "Cost Of Revenue"))
        opex = abs(get(is_df, "Operating Expense"))
        depreciation = abs(get(cf_df, "Depreciation And Amortization"))
        interest_expense = abs(get(is_df, "Interest Expense"))
        pretax_income = get(is_df, "Pretax Income")
        tax_expense = abs(get(is_df, "Tax Provision"))
        tax_rate = (tax_expense / pretax_income) if pretax_income else 0.24

        rows.append(
            {
                "year": year,
                "revenue": revenue,
                "cogs": cogs,
                "opex": opex,
                "depreciation": depreciation,
                "interest_expense": interest_expense,
                "tax_rate": min(max(tax_rate, 0.0), 0.45),
                "cash": get(bs_df, "Cash And Cash Equivalents"),
                "accounts_receivable": get(bs_df, "Accounts Receivable"),
                "inventory": get(bs_df, "Inventory"),
                "accounts_payable": get(bs_df, "Accounts Payable"),
                "ppne": get(bs_df, "Net PPE"),
                "debt": get(bs_df, "Total Debt"),
                "shares_outstanding": get(bs_df, "Ordinary Shares Number", default=1.0),
                "capex": abs(get(cf_df, "Capital Expenditure")),
            }
        )

    df = pd.DataFrame(rows)
    df = df[df["revenue"] > 0]
    if df.empty:
        raise ValueError(f"No valid annual rows returned from yfinance for {ticker}")

    return HistoricalData(ticker=ticker, df=_validate_historical_df(df))


def load_historical_data(ticker: str, csv_path: str | Path | None = None) -> HistoricalData:
    """Load historical data from CSV or yfinance.

    CSV takes precedence when provided.
    """
    if csv_path:
        return _load_from_csv(csv_path, ticker=ticker)

    return _load_from_yfinance(ticker)
