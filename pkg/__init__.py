import os
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from sqlalchemy import inspect, text

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

app = Flask(__name__, instance_relative_config=True)

# Set defaults (allow override via environment variable)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'vbs-secret-key-12345')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Load environment variables from .env if present
load_dotenv()

# Load configuration from instance/config.py
try:
    app.config.from_pyfile('config.py')
except Exception:
    pass

# Retrieve config parameters (support both deployment naming conventions)
def first_valid_env(*names, default=None):
    for name in names:
        value = os.environ.get(name)
        if value and not value.startswith('${{'):
            return value
    return default


db_url = first_valid_env('DATABASE_URL', 'MYSQL_URL', default=app.config.get('DATABASE_URL'))

def normalize_database_url(url):
    if not url:
        return url
    normalized = url.strip()
    if normalized.startswith('mysql://'):
        return 'mysql+mysqlconnector://' + normalized.split('://', 1)[1]
    if normalized.startswith('mysql+pymysql://'):
        return 'mysql+mysqlconnector://' + normalized.split('://', 1)[1]
    if normalized.startswith('mysql+mysqldb://'):
        return 'mysql+mysqlconnector://' + normalized.split('://', 1)[1]
    return normalized


db_url = normalize_database_url(db_url)
db_pass = first_valid_env('DATABASE_PASS', 'MYSQLPASSWORD', default=app.config.get('DATABASE_PASS', ''))
db_name = first_valid_env('DATABASE_NAME', 'MYSQLDATABASE', 'MYSQL_DATABASE', default=app.config.get('DATABASE_NAME', 'vvs'))
db_user = first_valid_env('DATABASE_USER', 'MYSQLUSER', default=app.config.get('DATABASE_USER', 'root'))
db_host = first_valid_env('DATABASE_HOST', 'MYSQLHOST', default=app.config.get('DATABASE_HOST', 'localhost'))
try:
    db_port = int(first_valid_env('DATABASE_PORT', 'MYSQLPORT', default=app.config.get('DATABASE_PORT', 3306)))
except (TypeError, ValueError):
    db_port = 3306

# Database URI choices
mysql_uri = db_url or f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
sqlite_uri = "sqlite:///" + os.path.join(app.instance_path, "vbs.db")

# SQLite is available only when explicitly enabled for local development.
use_sqlite = os.environ.get('USE_SQLITE', 'False').lower() in ('true', '1')

if use_sqlite:
    app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = mysql_uri

db.init_app(app)

migrate.init_app(app, db)
login_manager.init_app(app)
login_manager.login_view = 'user_login'
login_manager.login_message_category = 'errormsg'

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    from pkg.models import User
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# Register Error Handlers
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error/500.html'), 500

# Import route files at bottom to prevent circular import issues
from pkg import user_routes
from pkg import admin_routes
from pkg import super_admin_routes
