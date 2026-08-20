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

# Ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)

# Load environment variables from .env if present
load_dotenv()

# Load configuration from instance/config.py
try:
    app.config.from_pyfile('config.py')
except Exception:
    pass

# Retrieve config parameters (env vars override instance config)
db_pass = os.environ.get('DATABASE_PASS', app.config.get('DATABASE_PASS', '1234'))
db_name = os.environ.get('DATABASE_NAME', app.config.get('DATABASE_NAME', 'vital_mesh'))
db_user = os.environ.get('DATABASE_USER', app.config.get('DATABASE_USER', 'root'))
db_host = os.environ.get('DATABASE_HOST', app.config.get('DATABASE_HOST', 'localhost'))
db_port = int(os.environ.get('DATABASE_PORT', app.config.get('DATABASE_PORT', 3306)))

# Database URI choices
mysql_uri = f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
sqlite_uri = "sqlite:///" + os.path.join(app.instance_path, "vbs.db")

# Fallback option if MySQL is not available or USE_SQLITE env is set
use_sqlite = os.environ.get('USE_SQLITE', 'False').lower() in ('true', '1')

if use_sqlite:
    app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
else:
    # Try connecting to MySQL using mysql.connector
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name,
            connect_timeout=2
        )
        conn.close()
        app.config['SQLALCHEMY_DATABASE_URI'] = mysql_uri
    except Exception as e:
        print(f"MySQL connection failed: {str(e)}. Falling back to local SQLite database.")
        app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri

db.init_app(app)


def ensure_database_schema():
    with app.app_context():
        db.create_all()
        engine = db.engine
        inspector = inspect(engine)

        def add_column_if_missing(table_name, column_name, column_sql):
            if table_name not in inspector.get_table_names():
                return
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            if column_name not in columns:
                with engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_sql}'))

        add_column_if_missing('classes', 'category_id', 'category_id INTEGER')
        add_column_if_missing('classes', 'min_age', 'min_age INTEGER')
        add_column_if_missing('classes', 'max_age', 'max_age INTEGER')
        add_column_if_missing('classes', 'assessment_method', 'assessment_method VARCHAR(20)')
        add_column_if_missing('classes', 'manual_grade_weight', 'manual_grade_weight FLOAT DEFAULT 50.0')
        add_column_if_missing('classes', 'cbt_grade_weight', 'cbt_grade_weight FLOAT DEFAULT 50.0')
        add_column_if_missing('classes', 'age_group', 'age_group VARCHAR(50)')
        add_column_if_missing('exam_attempts', 'class_id', 'class_id INTEGER')
        add_column_if_missing('student_profiles', 'skill_id', 'skill_id INTEGER')
        add_column_if_missing('question_banks', 'skill_id', 'skill_id INTEGER')
        add_column_if_missing('exams', 'skill_question_count', 'skill_question_count INTEGER NOT NULL DEFAULT 0')
        add_column_if_missing('users', 'must_change_password', 'must_change_password BOOLEAN NOT NULL DEFAULT FALSE')

        if not inspector.has_table('class_categories'):
            with engine.begin() as conn:
                conn.execute(text('''
                    CREATE TABLE class_categories (
                        id INTEGER NOT NULL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        min_age INTEGER,
                        max_age INTEGER,
                        assessment_method VARCHAR(20) DEFAULT 'manual',
                        description VARCHAR(255)
                    )
                '''))

        if not inspector.has_table('teacher_classes'):
            with engine.begin() as conn:
                conn.execute(text('''
                    CREATE TABLE teacher_classes (
                        teacher_id INTEGER NOT NULL,
                        class_id INTEGER NOT NULL,
                        PRIMARY KEY (teacher_id, class_id),
                        FOREIGN KEY (teacher_id) REFERENCES teacher_profiles(id),
                        FOREIGN KEY (class_id) REFERENCES classes(id)
                    )
                '''))

        if not inspector.has_table('exam_classes'):
            with engine.begin() as conn:
                conn.execute(text('''
                    CREATE TABLE exam_classes (
                        exam_id INTEGER NOT NULL,
                        class_id INTEGER NOT NULL,
                        PRIMARY KEY (exam_id, class_id),
                        FOREIGN KEY (exam_id) REFERENCES exams(id),
                        FOREIGN KEY (class_id) REFERENCES classes(id)
                    )
                '''))

        if not inspector.has_table('question_bank_classes'):
            with engine.begin() as conn:
                conn.execute(text('''
                    CREATE TABLE question_bank_classes (
                        question_bank_id INTEGER NOT NULL,
                        class_id INTEGER NOT NULL,
                        PRIMARY KEY (question_bank_id, class_id),
                        FOREIGN KEY (question_bank_id) REFERENCES question_banks(id),
                        FOREIGN KEY (class_id) REFERENCES classes(id)
                    )
                '''))

        if not inspector.has_table('exam_section_bank_rules'):
            with engine.begin() as conn:
                # Use AUTO_INCREMENT for MySQL, AUTOINCREMENT for SQLite
                if engine.dialect.name == 'mysql':
                    conn.execute(text('''
                        CREATE TABLE exam_section_bank_rules (
                            id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                            exam_section_id INTEGER NOT NULL,
                            question_bank_id INTEGER NOT NULL,
                            question_count INTEGER NOT NULL DEFAULT 1,
                            FOREIGN KEY (exam_section_id) REFERENCES exam_sections(id),
                            FOREIGN KEY (question_bank_id) REFERENCES question_banks(id)
                        )
                    '''))
                else:
                    conn.execute(text('''
                        CREATE TABLE exam_section_bank_rules (
                            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            exam_section_id INTEGER NOT NULL,
                            question_bank_id INTEGER NOT NULL,
                            question_count INTEGER NOT NULL DEFAULT 1,
                            FOREIGN KEY (exam_section_id) REFERENCES exam_sections(id),
                            FOREIGN KEY (question_bank_id) REFERENCES question_banks(id)
                        )
                    '''))

        # Repair tables created before the MySQL AUTO_INCREMENT definition was added.
        if engine.dialect.name == 'mysql' and inspector.has_table('exam_section_bank_rules'):
            rule_columns = {column['name']: column for column in inspector.get_columns('exam_section_bank_rules')}
            if not rule_columns.get('id', {}).get('autoincrement', False):
                with engine.begin() as conn:
                    conn.execute(text(
                        'ALTER TABLE exam_section_bank_rules '
                        'MODIFY COLUMN id INTEGER NOT NULL AUTO_INCREMENT'
                    ))


ensure_database_schema()

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
