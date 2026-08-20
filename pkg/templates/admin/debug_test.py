import sys
sys.path.append(r'c:\Users\USER\Downloads\vvs2')

from pkg import app, db
from pkg.models import QuestionBank, Role, User, TeacherProfile, VbsYear, Class
import uuid

with app.app_context():
    from tests.test_question_banks import _seed_teacher_and_classes
    teacher_user, teacher, year, class_a, class_b = _seed_teacher_and_classes()
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['role'] = 'teacher'
            sess['useronline'] = teacher_user.id
            
        bank_name = f'Debug Shared Bank {uuid.uuid4().hex[:8]}'
        response = client.post('/teacher/question-banks/', data={
            'name': bank_name,
            'description': 'Shared class bank',
            'class_ids': [str(class_a.id), str(class_b.id)]
        }, follow_redirects=True)
        
        html = response.get_data(as_text=True)
        lines = html.splitlines()
        for i, line in enumerate(lines):
            if 'vbs-alert' in line:
                # Print current line and next 5 lines
                for j in range(max(0, i - 1), min(len(lines), i + 6)):
                    print(f"{j}: {lines[j].strip()}")
