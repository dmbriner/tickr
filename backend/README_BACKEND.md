# Tickr Backend

FastAPI backend for the GitHub Pages frontend at `https://dmbriner.github.io/tickr/`.

## Responsibilities

- user sign-up
- user login
- JWT auth
- saved API profiles
- saved analyses
- company analysis and export endpoints

## Main app

- `backend/app/main.py`

## Auth endpoints

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`

## Persistence endpoints

- `GET /api/me/api-profiles`
- `POST /api/me/api-profiles`
- `PUT /api/me/api-profiles/{profile_id}`
- `DELETE /api/me/api-profiles/{profile_id}`
- `GET /api/me/analyses`
- `POST /api/me/analyses`
- `PUT /api/me/analyses/{analysis_id}`
- `DELETE /api/me/analyses/{analysis_id}`

## Required environment variables

- `DATABASE_URL`
- `JWT_SECRET`
- `CORS_ORIGINS`

Optional:

- `JWT_EXPIRES_MINUTES`
- `ALPHA_VANTAGE_API_KEY`
- `FMP_API_KEY`

## Local run

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Railway start command

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
