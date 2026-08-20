"""Production entrypoint using waitress for Windows deployments.

Run as: python run.py
"""
import os

from pkg import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    try:
        from waitress import serve
        print(f'Starting with waitress on http://0.0.0.0:{port}')
        serve(app, host='0.0.0.0', port=port)
    except Exception:
        # Fallback to Flask dev server
        app.run(host='0.0.0.0', port=port)
