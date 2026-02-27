from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelAssumptions:
    projection_years: int = 5
    revenue_growth: list[float] = field(default_factory=lambda: [0.045, 0.04, 0.035, 0.03, 0.03])
    gross_margin: list[float] = field(default_factory=lambda: [0.22, 0.223, 0.225, 0.226, 0.227])
    opex_pct_revenue: list[float] = field(default_factory=lambda: [0.152, 0.151, 0.15, 0.149, 0.148])
    tax_rate: float = 0.24
    dso_days: list[float] = field(default_factory=lambda: [34, 34, 33, 33, 33])
    dio_days: list[float] = field(default_factory=lambda: [8, 8, 8, 7, 7])
    dpo_days: list[float] = field(default_factory=lambda: [31, 31, 32, 32, 32])
    capex_pct_revenue: list[float] = field(default_factory=lambda: [0.055, 0.055, 0.054, 0.053, 0.052])
    depreciation_pct_ppne: float = 0.14
    interest_rate_on_debt: float = 0.052
    debt_amortization: list[float] = field(default_factory=lambda: [350, 350, 400, 400, 450])
    dividend_payout_ratio: float = 0.38
    target_min_cash_pct_revenue: float = 0.03

    def normalize(self) -> None:
        """Extend/truncate vector assumptions to projection length."""
        fields_to_normalize = [
            "revenue_growth",
            "gross_margin",
            "opex_pct_revenue",
            "dso_days",
            "dio_days",
            "dpo_days",
            "capex_pct_revenue",
            "debt_amortization",
        ]

        for field_name in fields_to_normalize:
            values = getattr(self, field_name)
            if not values:
                raise ValueError(f"Assumption list '{field_name}' must not be empty")
            if len(values) < self.projection_years:
                values = values + [values[-1]] * (self.projection_years - len(values))
            elif len(values) > self.projection_years:
                values = values[: self.projection_years]
            setattr(self, field_name, values)
