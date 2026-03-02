# Tickr Backend

Minimal FastAPI auth backend for Railway deployment.

## Endpoints

- `GET /health`
- `POST /auth/login`
- `GET /api/private`

## Environment variables

- `JWT_SECRET` required
- `JWT_EXPIRES_MINUTES` default `120`
- `ADMIN_EMAIL` required
- `ADMIN_PASSWORD` required
- `ALLOWED_ORIGINS` required and should include `https://dmbriner.github.io`

## Local run

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## Railway start command

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```
