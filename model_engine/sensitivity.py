from __future__ import annotations

import pandas as pd

from .config import ModelAssumptions
from .data import HistoricalData
from .model import run_three_statement_model


def build_sensitivity_table(
    historical_data: HistoricalData,
    assumptions: ModelAssumptions,
    growth_shocks: list[float] | None = None,
    margin_shocks: list[float] | None = None,
) -> pd.DataFrame:
    """2D sensitivity for average FCF against growth/margin shocks."""
    growth_shocks = growth_shocks or [-0.02, -0.01, 0.0, 0.01, 0.02]
    margin_shocks = margin_shocks or [-0.015, -0.01, 0.0, 0.01, 0.015]

    table = pd.DataFrame(index=growth_shocks, columns=margin_shocks, dtype=float)

    for g in growth_shocks:
        for m in margin_shocks:
            scenario = ModelAssumptions(**assumptions.__dict__)
            scenario.revenue_growth = [x + g for x in assumptions.revenue_growth]
            scenario.gross_margin = [max(0.01, min(0.9, x + m)) for x in assumptions.gross_margin]
            output = run_three_statement_model(historical_data, scenario)
            avg_fcf = float(output.fcf["fcf"].mean())
            table.loc[g, m] = avg_fcf

    table.index.name = "revenue_growth_shock"
    table.columns.name = "gross_margin_shock"
    return table
