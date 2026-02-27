from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ModelAssumptions
from .data import HistoricalData


@dataclass
class ModelOutput:
    income_statement: pd.DataFrame
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    fcf: pd.DataFrame


def _base_year(df: pd.DataFrame) -> pd.Series:
    return df.sort_values("year").iloc[-1]


def run_three_statement_model(historical_data: HistoricalData, assumptions: ModelAssumptions) -> ModelOutput:
    assumptions.normalize()
    hist = historical_data.df
    base = _base_year(hist)

    years = [int(base["year"]) + i for i in range(1, assumptions.projection_years + 1)]

    income_rows: list[dict] = []
    balance_rows: list[dict] = []
    cash_rows: list[dict] = []
    fcf_rows: list[dict] = []

    prev_revenue = float(base["revenue"])
    prev_ar = float(base["accounts_receivable"])
    prev_inventory = float(base["inventory"])
    prev_ap = float(base["accounts_payable"])
    prev_ppne = float(base["ppne"])
    prev_debt = float(base["debt"])
    prev_cash = float(base["cash"])
    shares = max(float(base["shares_outstanding"]), 1.0)

    for i, year in enumerate(years):
        revenue = prev_revenue * (1 + assumptions.revenue_growth[i])
        gross_profit = revenue * assumptions.gross_margin[i]
        cogs = revenue - gross_profit
        opex = revenue * assumptions.opex_pct_revenue[i]

        ebitda = gross_profit - opex
        depreciation = prev_ppne * assumptions.depreciation_pct_ppne
        ebit = ebitda - depreciation

        average_debt = (prev_debt + max(prev_debt - assumptions.debt_amortization[i], 0.0)) / 2
        interest_expense = average_debt * assumptions.interest_rate_on_debt
        ebt = ebit - interest_expense
        taxes = max(ebt, 0.0) * assumptions.tax_rate
        net_income = ebt - taxes

        ar = revenue / 365.0 * assumptions.dso_days[i]
        inventory = cogs / 365.0 * assumptions.dio_days[i]
        ap = cogs / 365.0 * assumptions.dpo_days[i]
        nwc = ar + inventory - ap
        prev_nwc = prev_ar + prev_inventory - prev_ap
        change_nwc = nwc - prev_nwc

        capex = revenue * assumptions.capex_pct_revenue[i]
        ppne = prev_ppne + capex - depreciation

        debt_repayment = min(prev_debt, assumptions.debt_amortization[i])
        debt = max(prev_debt - debt_repayment, 0.0)

        cfo = net_income + depreciation - change_nwc
        cfi = -capex
        dividends = max(net_income, 0.0) * assumptions.dividend_payout_ratio
        cff_pre_cash_sweep = -debt_repayment - dividends

        ending_cash = prev_cash + cfo + cfi + cff_pre_cash_sweep
        min_cash = revenue * assumptions.target_min_cash_pct_revenue

        debt_draw = 0.0
        excess_cash_sweep = 0.0
        if ending_cash < min_cash:
            debt_draw = min_cash - ending_cash
            ending_cash = min_cash
            debt += debt_draw
        elif ending_cash > min_cash * 1.5:
            excess_cash_sweep = ending_cash - min_cash * 1.5
            debt_paydown = min(excess_cash_sweep, debt)
            debt -= debt_paydown
            ending_cash -= debt_paydown

        cff = cff_pre_cash_sweep + debt_draw - excess_cash_sweep
        free_cash_flow = ebit * (1 - assumptions.tax_rate) + depreciation - capex - change_nwc

        income_rows.append(
            {
                "year": year,
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross_profit,
                "opex": opex,
                "ebitda": ebitda,
                "depreciation": depreciation,
                "ebit": ebit,
                "interest_expense": interest_expense,
                "ebt": ebt,
                "taxes": taxes,
                "net_income": net_income,
                "eps": net_income / shares,
            }
        )

        balance_rows.append(
            {
                "year": year,
                "cash": ending_cash,
                "accounts_receivable": ar,
                "inventory": inventory,
                "ppne": ppne,
                "total_assets_proxy": ending_cash + ar + inventory + ppne,
                "accounts_payable": ap,
                "debt": debt,
                "nwc": nwc,
            }
        )

        cash_rows.append(
            {
                "year": year,
                "cfo": cfo,
                "cfi": cfi,
                "cff": cff,
                "debt_draw": debt_draw,
                "debt_repayment": debt_repayment + excess_cash_sweep,
                "dividends": dividends,
                "net_change_cash": cfo + cfi + cff,
            }
        )

        fcf_rows.append(
            {
                "year": year,
                "nopat": ebit * (1 - assumptions.tax_rate),
                "depreciation": depreciation,
                "capex": capex,
                "change_nwc": change_nwc,
                "fcf": free_cash_flow,
            }
        )

        prev_revenue = revenue
        prev_ar = ar
        prev_inventory = inventory
        prev_ap = ap
        prev_ppne = ppne
        prev_debt = debt
        prev_cash = ending_cash

    income_df = pd.DataFrame(income_rows)
    balance_df = pd.DataFrame(balance_rows)
    cash_df = pd.DataFrame(cash_rows)
    fcf_df = pd.DataFrame(fcf_rows)

    for frame in (income_df, balance_df, cash_df, fcf_df):
        numeric_cols = [c for c in frame.columns if c != "year"]
        frame[numeric_cols] = frame[numeric_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    return ModelOutput(
        income_statement=income_df,
        balance_sheet=balance_df,
        cash_flow=cash_df,
        fcf=fcf_df,
    )
