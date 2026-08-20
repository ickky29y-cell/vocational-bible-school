from pkg import app, db
from pkg.models import Role, User, TeacherProfile, ClassCategory, Class, StudentProfile, Exam, ExamAttempt, SkillAssessment, VbsYear, Skill, teacher_classes
from pkg.utils import get_teacher_classes
from werkzeug.security import generate_password_hash

with app.app_context():
    # Ensure roles
    sa = Role.query.filter_by(name='super_admin').first()
    if not sa:
        sa = Role(name='super_admin')
        db.session.add(sa)
    tr = Role.query.filter_by(name='teacher').first()
    if not tr:
        tr = Role(name='teacher')
        db.session.add(tr)
    st = Role.query.filter_by(name='student').first()
    if not st:
        st = Role(name='student')
        db.session.add(st)
    db.session.commit()

    # Ensure an active VBS year exists
    active = VbsYear.query.filter_by(is_active=True).first()
    if not active:
        active = VbsYear(year=2026, theme='Test', is_active=True)
        db.session.add(active)
        db.session.commit()

    # Create categories
    def ensure_cat(name, min_age, max_age, method):
        c = ClassCategory.query.filter_by(name=name).first()
        if not c:
            c = ClassCategory(name=name, min_age=min_age, max_age=max_age, assessment_method=method)
            db.session.add(c)
            db.session.commit()
        return c

    beginners = ensure_cat('Beginners', 0, 5, 'manual')
    primary = ensure_cat('Primary', 6, 8, 'cbt')
    juniors = ensure_cat('Juniors', 9, 11, 'cbt')
    intermediate = ensure_cat('Intermediate', 12, 15, 'cbt')

    # Create teachers
    def ensure_teacher(username, first, last):
        u = User.query.filter_by(username=username).first()
        if not u:
            u = User(username=username, email=f'{username}@example.com', password_hash=generate_password_hash('testpass'), role_id=tr.id)
            db.session.add(u)
            db.session.flush()
            tp = TeacherProfile(user_id=u.id, first_name=first, last_name=last)
            db.session.add(tp)
            db.session.commit()
            return tp
        return u.teacher_profile

    t_a = ensure_teacher('teacher_a', 'Alice', 'Anderson')
    t_b = ensure_teacher('teacher_b', 'Bob', 'Baker')

    # Create classes
    def ensure_class(name, category, min_age, max_age, method, teachers=[]):
        cl = Class.query.filter_by(name=name, vbs_year_id=active.id).first()
        if not cl:
            cl = Class(name=name, vbs_year_id=active.id, category_id=category.id, min_age=min_age, max_age=max_age, assessment_method=method)
            db.session.add(cl)
            db.session.commit()
        for trp in teachers:
            try:
                # Reconcile associations on existing fixtures as well as new ones.
                exists = db.session.execute(teacher_classes.select().where(teacher_classes.c.teacher_id==trp.id).where(teacher_classes.c.class_id==cl.id)).fetchone()
                if not exists:
                    db.session.execute(teacher_classes.insert().values(teacher_id=trp.id, class_id=cl.id))
            except Exception:
                pass
        db.session.commit()
        return cl

    primary_red = ensure_class('Primary Red Room', primary, 6, 8, 'cbt', [t_a])
    juniors_blue = ensure_class('Juniors Blue Room', juniors, 9, 11, 'cbt', [t_a])
    beginners_room = ensure_class('Beginners Room', beginners, 0, 5, 'manual', [t_b])

    # Create students
    def ensure_student(username, first, last, class_obj):
        u = User.query.filter_by(username=username).first()
        if not u:
            u = User(username=username, email=f'{username}@example.com', password_hash=generate_password_hash('student'), role_id=st.id)
            db.session.add(u)
            db.session.flush()
            sp = StudentProfile(user_id=u.id, first_name=first, last_name=last, age=(class_obj.min_age or 0)+1 if class_obj.min_age else 7, class_id=class_obj.id, vbs_year_id=active.id)
            db.session.add(sp)
            db.session.commit()
            return sp
        return u.student_profile

    s1 = ensure_student('stud_primary', 'Prim', 'One', primary_red)
    s2 = ensure_student('stud_juniors', 'Junior', 'Two', juniors_blue)
    s3 = ensure_student('stud_beg', 'Begin', 'Three', beginners_room)

    # Create shared exam assigned to both primary and juniors (idempotent)
    exam = Exam.query.filter_by(title='Shared Exam', vbs_year_id=active.id).first()
    if not exam:
        exam = Exam(title='Shared Exam', class_id=primary_red.id, vbs_year_id=active.id, duration_minutes=30, is_draft=False)
        db.session.add(exam)
        db.session.commit()

    # ensure assigned classes exist (insert explicitly to avoid executemany encoding issue)
    try:
        exists1 = db.session.execute(db.table('exam_classes').select().where(db.table('exam_classes').c.exam_id==exam.id).where(db.table('exam_classes').c.class_id==primary_red.id)).fetchone()
    except Exception:
        exists1 = None
    if not exists1:
        try:
            db.session.execute(db.table('exam_classes').insert().values(exam_id=exam.id, class_id=primary_red.id))
        except Exception:
            pass

    try:
        exists2 = db.session.execute(db.table('exam_classes').select().where(db.table('exam_classes').c.exam_id==exam.id).where(db.table('exam_classes').c.class_id==juniors_blue.id)).fetchone()
    except Exception:
        exists2 = None
    if not exists2:
        try:
            db.session.execute(db.table('exam_classes').insert().values(exam_id=exam.id, class_id=juniors_blue.id))
        except Exception:
            pass
    db.session.commit()

    # Create or update attempts (idempotent)
    def upsert_attempt(student, exam_obj, score_val):
        att = ExamAttempt.query.filter_by(student_id=student.id, exam_id=exam_obj.id).first()
        if not att:
            att = ExamAttempt(student_id=student.id, exam_id=exam_obj.id, class_id=student.class_id, is_submitted=True, score=score_val)
            db.session.add(att)
        else:
            att.class_id = student.class_id
            att.is_submitted = True
            att.score = score_val
        db.session.commit()

    upsert_attempt(s1, exam, 80.0)
    upsert_attempt(s2, exam, 90.0)

    # Manual assessment for beginner
    # ensure a manual skill exists
    sk = None
    sk = next(iter(Skill.query.filter_by(vbs_year_id=active.id).all()), None)
    if not sk:
        sk = Skill(name='Manual Task', description='Manual grading task', vbs_year_id=active.id)
        db.session.add(sk)
        db.session.commit()

    ma = SkillAssessment.query.filter_by(student_id=s3.id, skill_id=sk.id).first()
    if not ma:
        ma = SkillAssessment(student_id=s3.id, skill_id=sk.id, score=75.0, assessed_by=t_b.id)
        db.session.add(ma)
        db.session.commit()

    # Validate separation
    primary_attempts = ExamAttempt.query.join(StudentProfile).filter(StudentProfile.class_id==primary_red.id).all()
    juniors_attempts = ExamAttempt.query.join(StudentProfile).filter(StudentProfile.class_id==juniors_blue.id).all()
    beginners_manual = SkillAssessment.query.join(StudentProfile).filter(StudentProfile.class_id==beginners_room.id).all()

    print('Primary attempts:', [(a.student_id,a.score) for a in primary_attempts])
    print('Juniors attempts:', [(a.student_id,a.score) for a in juniors_attempts])
    print('Beginners manual assessments:', [(m.student_id,m.score) for m in beginners_manual])

    # Check access: teacher_a should not see beginners manual class
    ta_classes = [c.id for c in get_teacher_classes(t_a.id)]
    print('Teacher A classes:', ta_classes)
    print('Beginners class id should not be in Teacher A classes:', beginners_room.id in ta_classes)

    print('TEST SCRIPT COMPLETE')
