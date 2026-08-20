from pkg import app, db
from pkg.models import User, TeacherProfile

app.testing = True
app.config['PROPAGATE_EXCEPTIONS'] = True

with app.app_context():
    teacher_user = User.query.filter_by(username='sean').first()
    teacher = TeacherProfile.query.filter_by(user_id=teacher_user.id).first() if teacher_user else None
    print('teacher_user', teacher_user.id if teacher_user else None)
    print('teacher_profile', teacher.id if teacher else None)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['role'] = 'teacher'
        sess['useronline'] = teacher_user.id
    resp = client.get('/teacher/students/', follow_redirects=True)
    print('status', resp.status_code)
    print(resp.data.decode('utf-8', 'ignore')[:4000])
