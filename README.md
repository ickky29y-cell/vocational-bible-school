VBS Examination & CBT Platform
=================================

Overview
- A Flask-based admission and CBT platform with admin, teacher, and student roles.

Quick start (local, SQLite fallback)

```powershell
python -m pip install -r requirements.txt
$env:FLASK_APP='pkg'; $env:FLASK_ENV='development'
flask db upgrade
python scripts/seed_roles.py
python run.py
```

Production (recommended: Docker)

- Copy `.env.example` to `.env` and set DB credentials and `SECRET_KEY`.
- Start with Docker Compose (MySQL + app):

```powershell
docker-compose up --build -d
docker-compose exec web flask db upgrade
docker-compose exec web python scripts/seed_roles.py
```

Security notes
- Change `SECRET_KEY` before deploying.
- Do not use the default admin passwords in production.
- Serve behind TLS and a reverse proxy.

Files added for deployment
- `run.py` — waitress entrypoint for Windows.
- `Dockerfile` + `docker-compose.yml` — containerized MySQL + app setup.
- `.env.example` — environment variables sample.
