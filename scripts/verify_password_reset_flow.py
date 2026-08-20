from pkg import app, db
from pkg.models import User, StudentProfile

with app.app_context():
    student = StudentProfile.query.first()
    if not student:
        print('NO_STUDENT')
        raise SystemExit(0)
    user = student.user
    original_hash = user.password_hash
    original_flag = user.must_change_password
    try:
        user.set_password('temporary123')
        user.must_change_password = True
        db.session.commit()

        client = app.test_client()
        login = client.post('/user/login/', data={'identity': user.username, 'password': 'temporary123'}, follow_redirects=False)
        print('LOGIN', login.status_code, login.headers.get('Location'))
        form = client.get('/student/change-password/', follow_redirects=False)
        print('FORM', form.status_code, b'Set a New Password' in form.data)
        saved = client.post('/student/change-password/', data={'password': 'newsecure123', 'confirm_password': 'newsecure123'}, follow_redirects=False)
        print('SAVE', saved.status_code, saved.headers.get('Location'))
        dashboard = client.get('/student/dashboard/', follow_redirects=False)
        print('DASHBOARD', dashboard.status_code, dashboard.headers.get('Location'))
        assert login.headers.get('Location', '').endswith('/student/change-password/')
        assert form.status_code == 200
        assert saved.headers.get('Location', '').endswith('/student/dashboard/')
        assert dashboard.status_code == 200
        print('PASSWORD_RESET_FLOW_OK')
    finally:
        user.password_hash = original_hash
        user.must_change_password = original_flag
        db.session.commit()
