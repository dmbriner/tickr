from __future__ import annotations

import argparse
from pathlib import Path

from model_engine import (
    ModelAssumptions,
    build_sensitivity_table,
    export_model_to_excel,
    load_historical_data,
    run_three_statement_model,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python-powered 3-statement model engine")
    parser.add_argument("--ticker", default="UPS", help="Ticker symbol (default: UPS)")
    parser.add_argument("--years", type=int, default=5, help="Projection years (default: 5)")
    parser.add_argument(
        "--historical-csv",
        type=str,
        default=None,
        help="Path to historical CSV (uses yfinance when not provided)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="outputs/ups_3statement_model.xlsx",
        help="Excel output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    assumptions = ModelAssumptions(projection_years=args.years)
    historical = load_historical_data(ticker=args.ticker, csv_path=args.historical_csv)

    model_output = run_three_statement_model(historical, assumptions)
    sensitivity = build_sensitivity_table(historical, assumptions)

    result_file = export_model_to_excel(
        output=model_output,
        sensitivity=sensitivity,
        historical=historical.df,
        out_path=Path(args.out),
    )

    print(f"Model complete for {args.ticker}")
    print(f"Output: {result_file}")


if __name__ == "__main__":
    main()
