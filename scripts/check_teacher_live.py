from pkg import app
from pkg.models import User

with app.app_context():
    teacher = User.query.filter_by(username='sean').first()
    print('TEACHER_EXISTS', bool(teacher))
    print('TEACHER_ROLE', teacher.role.name if teacher and teacher.role else None)
    print('PASSWORD_OK', teacher.check_password('123456') if teacher else None)

    client = app.test_client()
    client.get('/user/logout/')
    login = client.post('/user/login/', data={'identity': 'sean', 'password': '123456'}, follow_redirects=False)
    print('LOGIN', login.status_code, login.headers.get('Location'))

    paths = [
        '/teacher/dashboard/',
        '/teacher/students/',
        '/teacher/skills/',
        '/teacher/assessment/',
        '/teacher/question-banks/',
        '/teacher/exams/',
        '/teacher/exams/monitor/',
    ]
    for path in paths:
        response = client.get(path, follow_redirects=False)
        html = response.get_data(as_text=True)
        markers = [marker for marker in ('Skill Acquisition', 'Question Banks', 'Exam Builder', 'Test Exam', 'Live Monitor') if marker in html]
        print(path, response.status_code, response.headers.get('Location'), markers)
