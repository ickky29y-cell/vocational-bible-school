from pkg import app
from pkg.models import User, Class

with app.app_context():
    chap = User.query.filter_by(username='chaplain').first()
    if not chap:
        print('NO_CHAPLAIN')
        raise SystemExit(0)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['role'] = 'super_admin'
        sess['useronline'] = chap.id
    cls = Class.query.first()
    if not cls:
        print('NO_CLASS')
        raise SystemExit(0)
    r = client.get(f'/super-admin/class-edit/{cls.id}/', follow_redirects=True)
    print('STATUS', r.status_code)
    html = r.get_data(as_text=True)
    start = html.find('<h1 class="dashboard-title">Edit Class</h1>')
    if start == -1:
        print('EDIT_FORM_NOT_FOUND')
        print(html[:2000])
    else:
        print(html[start:start+2000])
