from pkg import app

with app.app_context():
    client = app.test_client()
    login = client.post('/user/login/', data={'identity': 'chaplain', 'password': 'admin1234'}, follow_redirects=False)
    print('LOGIN', login.status_code, login.headers.get('Location'))
    paths = [
        '/super-admin/dashboard/',
        '/super-admin/teachers/',
        '/teacher/dashboard/',
        '/teacher/skills/',
        '/teacher/question-banks/',
        '/teacher/exams/',
        '/teacher/students/',
    ]
    for path in paths:
        response = client.get(path, follow_redirects=False)
        html = response.get_data(as_text=True)
        markers = [marker for marker in ('Skill Acquisition', 'Test Exam', 'Optional Skill Questions', 'Question Banks', 'Exam Builder') if marker in html]
        print(path, response.status_code, response.headers.get('Location'), markers)
