# Tickr Deployment Guide

## Goal

Deploy:

- frontend on GitHub Pages at `https://dmbriner.github.io/tickr/`
- backend on Railway
- auth and saved data through the Railway API

## 1. Create the database

Create a Railway Postgres instance and copy `DATABASE_URL`.

## 2. Configure backend secrets

Set these Railway variables:

- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_EXPIRES_MINUTES`
- `CORS_ORIGINS`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

Recommended `CORS_ORIGINS`:

```text
https://dmbriner.github.io,http://localhost:3000,http://127.0.0.1:3000
```

## 3. Run migrations

```bash
cd backend
alembic upgrade head
```

## 4. Deploy the backend to Railway

Use the repo root in Railway.

- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Healthcheck Path: `/healthz`

## 5. Point GitHub Pages to Railway

Update:

- `docs/assets/config.js`

Set:

```js
window.TICKR_BACKEND_URL = "https://your-backend.up.railway.app";
```

Then commit and push so GitHub Pages serves the updated frontend.

## 6. Verify

- `https://dmbriner.github.io/tickr/`
- `https://your-backend.up.railway.app/healthz`
- sign up on `https://dmbriner.github.io/tickr/login.html`
- sign in and confirm the account page loads
