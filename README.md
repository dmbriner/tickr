# Tickr

Live site: https://dmbriner.github.io/tickr

This repository is set up as:

- a GitHub Pages project site served from [`docs/`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/docs)
- a Railway-deployable FastAPI backend in [`backend/`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend)

## Frontend

GitHub Pages should be configured to deploy from `/docs`.

Frontend entry pages:

- [`docs/index.html`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/docs/index.html)
- [`docs/login.html`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/docs/login.html)
- [`docs/app.html`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/docs/app.html)

Static assets:

- [`docs/assets/styles.css`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/docs/assets/styles.css)
- [`docs/assets/app.js`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/docs/assets/app.js)

## Backend

Deploy the backend on Railway from the `backend/` directory with:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Files:

- [`backend/main.py`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend/main.py)
- [`backend/requirements.txt`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend/requirements.txt)
- [`backend/.env.example`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend/.env.example)
- [`backend/README_BACKEND.md`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/backend/README_BACKEND.md)

After Railway deployment, update `BACKEND_URL` in [`docs/assets/app.js`](/Users/danabriner/Desktop/Extracurriculars/Projects/Python%203%20Statement%20Model/python-3statement-model/docs/assets/app.js).

## Repository rename

The GitHub repository should be renamed to:

`tickr`

After renaming it on GitHub, update the local remote:

```bash
git remote set-url origin https://github.com/dmbriner/tickr.git
git remote -v
```
