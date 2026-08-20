"""Production entrypoint using waitress for Windows deployments.

Run as: python run.py
"""
from pkg import app

if __name__ == '__main__':
    try:
        from waitress import serve
        print('Starting with waitress on http://0.0.0.0:8080')
        serve(app, host='0.0.0.0', port=8080)
    except Exception:
        # Fallback to Flask dev server
        app.run(host='0.0.0.0', port=8080)
