import os

# General configuration modeled after user's working example
SECRET_KEY = os.environ.get('SECRET_KEY', 'JNbkMffSwgHLnAU_L_ABRwhF_Os')
TECH_SUPPORT = os.environ.get('TECH_SUPPORT', '08062648647')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Default MySQL URL (no password) — override with DATABASE_URL env var if needed
SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://"
        f"{os.getenv('MYSQLUSER')}:"
        f"{os.getenv('MYSQLPASSWORD')}@"
        f"{os.getenv('MYSQLHOST')}:"
        f"{os.getenv('MYSQLPORT')}/"
        f"{os.getenv('MYSQL_DATABASE')}"
)


# SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'mysql+mysqlconnector://root@localhost/vvs')

# # Backwards-compatible individual settings used by the app
# DATABASE_PASS = os.environ.get('DATABASE_PASS', '')
# DATABASE_NAME = os.environ.get('DATABASE_NAME', 'vvs')
# DATABASE_USER = os.environ.get('DATABASE_USER', 'root')
# DATABASE_HOST = os.environ.get('DATABASE_HOST', 'localhost')
# DATABASE_PORT = int(os.environ.get('DATABASE_PORT', 3306))

# Optional: set USE_SQLITE in environment to force SQLite fallback during development
# e.g. in PowerShell: $env:USE_SQLITE = 'True'