"""SEC EDGAR data source — completely free, no API key required.

Uses two public EDGAR endpoints:
  - https://www.sec.gov/files/company_tickers.json   (ticker → CIK lookup)
  - https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json  (all XBRL facts)

All dollar values are returned in $M (millions) to match the app's internal units.
Shares outstanding are returned in millions of shares.
"""
from __future__ import annotations

import functools

import pandas as pd
import requests

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_BASE = "https://data.sec.gov"

_TIMEOUT = 20
_FACTS_TIMEOUT = 60  # company facts JSON can be 10-20 MB

# SEC requires a descriptive User-Agent; bots without it get 403s
_HEADERS = {
    "User-Agent": "3StatementModelApp/1.0 (research@3statementmodel.io)",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json",
}

# ── XBRL concept priority lists ─────────────────────────────────────
# First matching concept with data wins.

_REVENUE = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueGoodsNet",
    "RevenueFromContractWithCustomerProductAndServiceExcludingAssessedTax",
]
_COGS = [
    "CostOfGoodsSold",
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
]
_GROSS_PROFIT = ["GrossProfit"]
_OPEX = [
    "SellingGeneralAndAdministrativeExpense",
    "GeneralAndAdministrativeExpense",
    "OperatingExpenses",
]
_EBIT = ["OperatingIncomeLoss"]
_INTEREST = [
    "InterestExpense",
    "InterestExpenseDebt",
    "InterestAndDebtExpense",
]
_NET_INCOME = [
    "NetIncomeLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
    "ProfitLoss",
]
_TAX = ["IncomeTaxExpenseBenefit"]
_PRETAX = [
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossBeforeIncomeTaxes",
]
_DA = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
    "Depreciation",
]
_CAPEX = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsForCapitalImprovements",
]
_CASH = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsAndShortTermInvestments",
    "Cash",
]
_AR = ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"]
_INVENTORY = ["InventoryNet", "Inventories"]
_AP = ["AccountsPayableCurrent", "AccountsPayable"]
_PPE = [
    "PropertyPlantAndEquipmentNet",
    "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization",
]
_LT_DEBT = [
    "LongTermDebt",
    "LongTermDebtNoncurrent",
    "LongTermDebtAndCapitalLeaseObligations",
]
_ST_DEBT = ["ShortTermBorrowings", "DebtCurrent"]
_TOTAL_ASSETS = ["Assets"]
_EQUITY = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
]
_SHARES = [
    "CommonStockSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


@functools.lru_cache(maxsize=1)
def _ticker_index() -> dict[str, int]:
    """Load SEC ticker→CIK mapping. Cached for the process lifetime."""
    resp = _session().get(TICKERS_URL, timeout=_TIMEOUT)
    resp.raise_for_status()
    return {v["ticker"].upper(): int(v["cik_str"]) for v in resp.json().values()}


def ticker_to_cik(ticker: str) -> int | None:
    """Return SEC CIK integer for a ticker, or None if not a US-listed company."""
    try:
        return _ticker_index().get(ticker.upper().strip())
    except Exception:
        return None


def _load_facts(cik: int) -> dict:
    url = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik:010d}.json"
    resp = _session().get(url, timeout=_FACTS_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _usd_map(us_gaap: dict, concepts: list[str], require_fy: bool = True) -> dict[str, float]:
    """Return {period_end_date: value_in_USD} for the first concept that has data.

    Args:
        require_fy: If True, only accept entries with fp='FY' (income/cash flow items).
                    If False, accept any fp from a 10-K (balance sheet items).
    """
    for concept in concepts:
        if concept not in us_gaap:
            continue
        entries = us_gaap[concept].get("units", {}).get("USD", [])
        if not entries:
            continue
        # latest-filed wins for each period-end date
        best: dict[str, tuple[str, float]] = {}
        for e in entries:
            if e.get("form") not in ("10-K", "10-K/A"):
                continue
            if require_fy and e.get("fp") != "FY":
                continue
            end = e.get("end", "")
            filed = e.get("filed", "")
            val = e.get("val")
            if not end or val is None:
                continue
            if end not in best or filed > best[end][0]:
                best[end] = (filed, float(val))
        if best:
            return {d: v for d, (_, v) in best.items()}
    return {}


def _shares_map(us_gaap: dict, concepts: list[str]) -> dict[str, float]:
    """Return {period_end_date: share_count} from 10-K filings."""
    for concept in concepts:
        if concept not in us_gaap:
            continue
        entries = us_gaap[concept].get("units", {}).get("shares", [])
        if not entries:
            continue
        best: dict[str, tuple[str, float]] = {}
        for e in entries:
            if e.get("form") not in ("10-K", "10-K/A"):
                continue
            end = e.get("end", "")
            filed = e.get("filed", "")
            val = e.get("val")
            if not end or val is None:
                continue
            if end not in best or filed > best[end][0]:
                best[end] = (filed, float(val))
        if best:
            return {d: v for d, (_, v) in best.items()}
    return {}


def build_annual_df(facts: dict) -> pd.DataFrame:
    """Parse EDGAR company facts JSON → annual DataFrame with values in $M.

    All dollar amounts are divided by 1,000,000 (full $ → $M).
    Shares outstanding are divided by 1,000,000 (actual count → millions of shares).
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    if not us_gaap:
        raise ValueError("No us-gaap XBRL facts in EDGAR response")

    M = 1_000_000  # conversion factor: full dollars → $M

    # ── Income statement / cash flow (flow items, require FY) ──
    rev_raw = _usd_map(us_gaap, _REVENUE, require_fy=True)
    cogs_raw = _usd_map(us_gaap, _COGS, require_fy=True)
    gross_raw = _usd_map(us_gaap, _GROSS_PROFIT, require_fy=True)
    opex_raw = _usd_map(us_gaap, _OPEX, require_fy=True)
    ebit_raw = _usd_map(us_gaap, _EBIT, require_fy=True)
    interest_raw = _usd_map(us_gaap, _INTEREST, require_fy=True)
    tax_raw = _usd_map(us_gaap, _TAX, require_fy=True)
    pretax_raw = _usd_map(us_gaap, _PRETAX, require_fy=True)
    da_raw = _usd_map(us_gaap, _DA, require_fy=True)
    capex_raw = _usd_map(us_gaap, _CAPEX, require_fy=True)

    # ── Balance sheet (point-in-time; some filers omit fp='FY') ──
    cash_raw = _usd_map(us_gaap, _CASH, require_fy=False)
    ar_raw = _usd_map(us_gaap, _AR, require_fy=False)
    inv_raw = _usd_map(us_gaap, _INVENTORY, require_fy=False)
    ap_raw = _usd_map(us_gaap, _AP, require_fy=False)
    ppe_raw = _usd_map(us_gaap, _PPE, require_fy=False)
    lt_debt_raw = _usd_map(us_gaap, _LT_DEBT, require_fy=False)
    st_debt_raw = _usd_map(us_gaap, _ST_DEBT, require_fy=False)
    total_assets_raw = _usd_map(us_gaap, _TOTAL_ASSETS, require_fy=False)
    equity_raw = _usd_map(us_gaap, _EQUITY, require_fy=False)
    shares_raw = _shares_map(us_gaap, _SHARES)

    dates = sorted(rev_raw.keys())
    if not dates:
        raise ValueError("No annual revenue data found in EDGAR XBRL facts")

    rows = []
    for dt in dates:
        rev = rev_raw.get(dt, 0.0) / M
        if rev <= 0:
            continue

        gross = gross_raw.get(dt, 0.0) / M
        cogs = cogs_raw.get(dt, 0.0) / M
        # Derive COGS from Gross Profit if not explicitly reported
        if cogs == 0 and gross > 0:
            cogs = max(rev - gross, 0.0)

        ebit = ebit_raw.get(dt, 0.0) / M
        opex = opex_raw.get(dt, 0.0) / M
        gross_actual = gross if gross > 0 else max(rev - cogs, 0.0)
        # Derive OpEx from EBIT if not explicitly reported
        if opex == 0 and ebit != 0 and gross_actual > 0:
            opex = max(gross_actual - ebit, 0.0)

        da = da_raw.get(dt, 0.0) / M
        interest = abs(interest_raw.get(dt, 0.0)) / M
        capex = abs(capex_raw.get(dt, 0.0)) / M

        tax = abs(tax_raw.get(dt, 0.0)) / M
        pretax = pretax_raw.get(dt, 0.0) / M
        tax_rate = (tax / pretax) if pretax > 0 and tax > 0 else 0.21
        tax_rate = min(max(tax_rate, 0.0), 0.45)

        cash = cash_raw.get(dt, 0.0) / M
        ar = ar_raw.get(dt, 0.0) / M
        inv = inv_raw.get(dt, 0.0) / M
        ap = ap_raw.get(dt, 0.0) / M
        ppe = ppe_raw.get(dt, 0.0) / M
        lt_debt = lt_debt_raw.get(dt, 0.0) / M
        st_debt = st_debt_raw.get(dt, 0.0) / M
        debt = lt_debt + st_debt
        equity = equity_raw.get(dt, 0.0) / M
        total_assets = total_assets_raw.get(dt, 0.0) / M

        explicit_assets = cash + ar + inv + ppe
        other_assets = max(total_assets - explicit_assets, 0.0) if total_assets > 0 else 0.0

        # Shares: EDGAR reports actual share count → divide by M to get millions
        shares_val = shares_raw.get(dt, 0.0)
        shares = max(shares_val / M, 1.0)

        try:
            ts = pd.Timestamp(dt)
        except Exception:
            continue

        rows.append({
            "year": int(ts.year),
            "period_end": dt,
            "period_label": f"FY {ts.year}",
            "fiscal_quarter": 4,
            "revenue": rev,
            "cogs": cogs,
            "opex": opex,
            "depreciation": da,
            "interest_expense": interest,
            "tax_rate": tax_rate,
            "cash": cash,
            "accounts_receivable": ar,
            "inventory": inv,
            "accounts_payable": ap,
            "ppne": ppe,
            "debt": debt,
            "shares_outstanding": shares,
            "capex": capex,
            "equity": equity,
            "other_assets": other_assets,
            "other_liabilities": 0.0,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    return (
        df[df["revenue"] > 0]
        .drop_duplicates(subset=["year"], keep="last")
        .sort_values("year")
        .reset_index(drop=True)
    )


def load_from_edgar(ticker: str) -> tuple[pd.DataFrame, str, int]:
    """Fetch and parse annual financial data for a US-listed company from SEC EDGAR.

    Returns:
        (annual_df, entity_name, cik)
        annual_df columns match HistoricalData requirements; values in $M.

    Raises:
        ValueError: If ticker not found on SEC or data cannot be parsed.
    """
    cik = ticker_to_cik(ticker)
    if cik is None:
        raise ValueError(
            f"'{ticker}' not found in SEC EDGAR — it may not be a US-listed public company, "
            "or the ticker may have changed. Try loading via CSV or check the symbol."
        )
    facts = _load_facts(cik)
    entity_name: str = facts.get("entityName", ticker)
    annual_df = build_annual_df(facts)
    if annual_df.empty:
        raise ValueError(
            f"Could not extract financial statements for {ticker} from EDGAR XBRL data. "
            "The company may not file structured XBRL or uses non-standard concept names."
        )
    return annual_df, entity_name, cik
