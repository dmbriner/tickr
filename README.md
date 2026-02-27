# Python-Powered 3-Statement Model Engine

A modular Python model engine for building projected financial statements, FCF, and sensitivity tables for companies like UPS.

## Features

- Historical data ingestion:
  - `yfinance` API
  - Manual CSVs
- Dynamic projection engine:
  - Revenue drivers
  - Margin structure
  - Working capital (DSO/DIO/DPO)
  - Debt schedule with cash sweep logic
- Output package:
  - Projected Income Statement
  - Projected Balance Sheet
  - Projected Cash Flow
  - FCF build
  - 2D sensitivity tables
- Delivery:
  - Excel workbook export with clean tabs

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

### Option 1: API-driven (yfinance)

```bash
python run_model.py --ticker UPS --years 5 --out outputs/ups_3statement_model.xlsx
```

### Option 2: Manual historical CSV

```bash
python run_model.py --ticker UPS --historical-csv data/ups_historical_template.csv --years 5 --out outputs/ups_3statement_model.xlsx
```

## Historical CSV format

Required columns:

- `year`
- `revenue`
- `cogs`
- `opex`
- `depreciation`
- `interest_expense`
- `tax_rate`
- `cash`
- `accounts_receivable`
- `inventory`
- `accounts_payable`
- `ppne`
- `debt`
- `shares_outstanding`
- `capex`

See `data/ups_historical_template.csv` for a starter file.

## Notes

- Assumptions live in `model_engine/config.py` (`ModelAssumptions`).
- Sensitivity table in `model_engine/sensitivity.py` shocks revenue growth and gross margin.
- Export logic in `model_engine/export.py` can be extended for dashboard output (e.g., Streamlit).
