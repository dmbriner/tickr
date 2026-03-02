# Tickr

Live frontend: `https://dmbriner.github.io/tickr/`

This repository now uses:

- `docs/` as the only frontend, deployed through GitHub Pages
- `backend/` as the Railway-hosted FastAPI API
- Postgres for saved user data and account records

## Frontend

GitHub Pages should publish from `docs/`.

Main files:

- `docs/index.html`
- `docs/login.html`
- `docs/app.html`
- `docs/assets/styles.css`
- `docs/assets/app.js`
- `docs/assets/config.js`

Set your Railway backend URL in `docs/assets/config.js`.

## Backend

Deploy the repo to Railway with:

```bash
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Run migrations before using auth or saved data:

```bash
cd backend
alembic upgrade head
```

Required environment variables:

- `DATABASE_URL`
- `JWT_SECRET`
- `CORS_ORIGINS`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

Useful local default for `CORS_ORIGINS`:

```text
https://dmbriner.github.io,http://localhost:3000,http://127.0.0.1:3000
```
