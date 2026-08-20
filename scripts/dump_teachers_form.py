from pkg import app
from pkg.models import User

with app.app_context():
    chap = User.query.filter_by(username='chaplain').first()
    if not chap:
        print('NO_CHAPLAIN')
        raise SystemExit(0)

    client = app.test_client()
    # try login
    resp = client.post('/user/login/', data={'identity': 'chaplain', 'password': 'admin1234'}, follow_redirects=True)
    r = client.get('/super-admin/teachers/', follow_redirects=True)
    if r.status_code != 200:
        print('STATUS', r.status_code)
        raise SystemExit(0)
    html = r.get_data(as_text=True)
    start = html.find('<h4 class="fw-bold mb-3 text-primary"><i class="fas fa-school"></i> Create VBS Class')
    if start == -1:
        print('FORM_NOT_FOUND')
        print(html[:2000])
    else:
        cut = html[start:start+5000]
        print(cut)
