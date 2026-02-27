from __future__ import annotations

from pathlib import Path

import pandas as pd

from .model import ModelOutput


def export_model_to_excel(
    output: ModelOutput,
    sensitivity: pd.DataFrame,
    historical: pd.DataFrame,
    out_path: str | Path,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        historical.to_excel(writer, sheet_name="Historical", index=False)
        output.income_statement.to_excel(writer, sheet_name="Income Statement", index=False)
        output.balance_sheet.to_excel(writer, sheet_name="Balance Sheet", index=False)
        output.cash_flow.to_excel(writer, sheet_name="Cash Flow", index=False)
        output.fcf.to_excel(writer, sheet_name="FCF", index=False)
        sensitivity.to_excel(writer, sheet_name="Sensitivity")

    return out_path
