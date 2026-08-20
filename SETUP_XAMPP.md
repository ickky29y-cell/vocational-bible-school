Setup for XAMPP MySQL and Flask app
==================================

1) Start XAMPP and enable MySQL (MariaDB)

2) Create database (example):

   - Open phpMyAdmin (http://localhost/phpmyadmin)
   - Create database `vital_mesh` (or change `DATABASE_NAME` in `instance/config.py`)

3) Edit `instance/config.py` if needed: set `DATABASE_USER`, `DATABASE_PASS`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`.

4) In your virtual environment install dependencies:

```powershell
python -m pip install -r requirements.txt
```

5) Initialize and run migrations:

```powershell
set FLASK_APP=pkg
set FLASK_ENV=development
flask db init        # only once
flask db migrate -m "Initial migration"
flask db upgrade
```

On PowerShell use `$env:FLASK_APP = 'pkg'` and `$env:FLASK_ENV = 'development'` instead of `set` if preferred.

6) Run the app:

```powershell
flask run
```

Notes:
- If you prefer another connector, install `mysqlclient` and adjust `SQLALCHEMY_DATABASE_URI`.
- For local dev you can force SQLite fallback by setting environment variable `USE_SQLITE=True`.

Deployment (Windows / simple production):

- Install `waitress`:

```powershell
python -m pip install waitress
```

- Run via `run.py`:

```powershell
python run.py
```

This will start the app on port 8080 and is suitable for simple hosting behind a reverse proxy (IIS, nginx, Apache). For more robust deployments consider Docker or a Linux host with `gunicorn`.
