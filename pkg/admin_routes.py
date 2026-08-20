import datetime
import os
import time
from flask import render_template, url_for, request, redirect, flash, session, jsonify
from flask_login import current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from pkg import app, db
from pkg.models import User, Role, VbsYear, TeacherProfile, Class, StudentProfile, Skill, SkillAssessment, QuestionBank, Question, Exam, ExamSection, ExamSectionBankRule, ExamAttempt, AttemptQuestion, Announcement, AuditLog, exam_classes
from pkg.utils import current_user_id, current_role_name, get_teacher_classes, teacher_has_access_to_class, set_active_class, get_active_class, get_effective_teacher_profile
from pkg.exam_paper import build_exam_questions, exam_skill_options, present_questions

# Helper to write to audit log
def log_audit(user_id, action, details=None):
    try:
        ip = request.remote_addr
        log = AuditLog(user_id=user_id, action=action, ip_address=ip, details=details)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

# Decorator-like helper to check authorization
def require_teacher():
    # Prefer Flask-Login's current_user when available, fallback to legacy session keys.
    # Super admins may use teacher routes only through explicit view-as mode.
    try:
        if current_user and getattr(current_user, 'is_authenticated', False):
            role_name = getattr(getattr(current_user, 'role', None), 'name', None)
            if role_name == 'teacher':
                return True
            if role_name == 'super_admin' and session.get('view_as_teacher'):
                return True
    except Exception:
        pass

    role_name = current_role_name()
    if role_name == 'teacher':
        return True
    if role_name == 'super_admin' and session.get('view_as_teacher'):
        return True
    return False

# Teacher Dashboard Route
@app.route('/teacher/dashboard/')
def teacher_dashboard():
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    # Allow impersonation: get the effective teacher profile
    from pkg.utils import get_effective_teacher_profile
    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found.', 'errormsg')
        session.clear()
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    
    # Get teacher's assigned classes
    classes = get_teacher_classes(teacher.id, active_year.id if active_year else None)
    class_ids = [c.id for c in classes]

    # Metrics
    total_students = StudentProfile.query.filter(StudentProfile.class_id.in_(class_ids)).count() if class_ids else 0
    total_banks = QuestionBank.query.filter(
        (QuestionBank.class_id.in_(class_ids)) |
        (QuestionBank.assigned_classes.any(Class.id.in_(class_ids)))
    ).count() if class_ids else 0
    # Include exams assigned directly or via exam_classes association
    total_exams = 0
    if class_ids:
        sub = db.session.query(exam_classes.c.exam_id).filter(exam_classes.c.class_id.in_(class_ids))
        total_exams = Exam.query.filter((Exam.class_id.in_(class_ids)) | (Exam.id.in_(sub))).count()
    
    # Live ongoing attempts
    active_attempts_count = 0
    if class_ids:
        active_attempts_count = ExamAttempt.query.join(StudentProfile).filter(
            StudentProfile.class_id.in_(class_ids),
            ExamAttempt.is_submitted == False
        ).count()

    announcements = Announcement.query.filter(Announcement.target_role.in_(['all', 'teacher'])).order_by(Announcement.created_at.desc()).all()
    
    # Recent exam attempts by students
    recent_attempts = []
    if class_ids:
        recent_attempts = ExamAttempt.query.join(StudentProfile).filter(
            StudentProfile.class_id.in_(class_ids)
        ).order_by(ExamAttempt.start_time.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        teacher=teacher,
        classes=classes,
        total_students=total_students,
        total_banks=total_banks,
        total_exams=total_exams,
        active_attempts_count=active_attempts_count,
        announcements=announcements,
        recent_attempts=recent_attempts,
        active_class_id=get_active_class()
    )


@app.route('/teacher/switch-class/<int:class_id>/')
def teacher_switch_class(class_id):
    from pkg.utils import get_effective_teacher_profile
    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    if not teacher_has_access_to_class(teacher.id, class_id):
        flash('Unauthorized class switch.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    set_active_class(class_id)
    flash('Switched active class.', 'feedback')
    return redirect(url_for('teacher_dashboard'))

# Student Management (List & Register)
@app.route('/teacher/students/', methods=['GET', 'POST'])
def teacher_students():
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))
    active_year = VbsYear.query.filter_by(is_active=True).first()

    classes = get_teacher_classes(teacher.id, active_year.id if active_year else None)
    if not classes:
        classes = get_teacher_classes(teacher.id)

    if not classes:
        flash('No classes have been assigned to you yet. Please contact the Super Admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    class_ids = [c.id for c in classes]
    skills = Skill.query.filter_by(vbs_year_id=active_year.id if active_year else 0).order_by(Skill.name).all()
    selected_class_id = request.args.get('class_id')
    selected_class = None

    if selected_class_id is not None:
        try:
            selected_class_id = int(selected_class_id)
        except (TypeError, ValueError):
            selected_class_id = None

    if selected_class_id is not None:
        if selected_class_id not in class_ids:
            flash('Unauthorized class access.', 'errormsg')
            return redirect(url_for('teacher_students'))
        selected_class = next((c for c in classes if c.id == selected_class_id), None)
        students = StudentProfile.query.filter_by(class_id=selected_class_id).all()
    else:
        students = []

    if request.method == 'POST':
        first_name = (request.form.get('first_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()
        age_str = request.form.get('age')
        gender = request.form.get('gender')
        class_id_str = request.form.get('class_id')
        parent_name = (request.form.get('parent_name') or '').strip()
        parent_phone = (request.form.get('parent_phone') or '').strip()
        skill_id_str = request.form.get('skill_id')

        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = (request.form.get('password') or '').strip()
        confirm = (request.form.get('confirm_password') or '').strip()

        if not all([first_name, last_name, age_str, gender, class_id_str, username, email, password]):
            flash('Please complete all compulsory fields.', 'errormsg')
            if selected_class_id is not None:
                return redirect(url_for('teacher_students', class_id=selected_class_id))
            return redirect(url_for('teacher_students'))

        try:
            target_class_id = int(class_id_str)
        except (TypeError, ValueError):
            flash('A valid class is required.', 'errormsg')
            return redirect(url_for('teacher_students'))

        selected_skill = None
        if skill_id_str:
            try:
                selected_skill = Skill.query.filter_by(id=int(skill_id_str), vbs_year_id=active_year.id).first()
            except (TypeError, ValueError):
                selected_skill = None
            if not selected_skill:
                flash('Selected skill is not valid for the active VBS year.', 'errormsg')
                return redirect(url_for('teacher_students', class_id=target_class_id))

        if target_class_id not in class_ids:
            flash('Unauthorized class access.', 'errormsg')
            return redirect(url_for('teacher_students'))

        if password != confirm:
            flash('Passwords do not match.', 'errormsg')
            return redirect(url_for('teacher_students', class_id=target_class_id))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already taken.', 'errormsg')
            return redirect(url_for('teacher_students', class_id=target_class_id))

        try:
            role = Role.query.filter_by(name='student').first()
            if not role:
                role = Role(name='student', description='VBS Pupil')
                db.session.add(role)
                db.session.flush()

            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role_id=role.id
            )
            db.session.add(user)
            db.session.flush()

            student = StudentProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                age=int(age_str),
                gender=gender,
                class_id=target_class_id,
                skill_id=selected_skill.id if selected_skill else None,
                vbs_year_id=active_year.id,
                parent_name=parent_name,
                parent_phone=parent_phone
            )
            db.session.add(student)
            db.session.commit()

            log_audit(current_user_id(), "REGISTER_STUDENT", f"Registered student {first_name} {last_name}")
            flash('Student registered successfully!', 'feedback')
            return redirect(url_for('teacher_students', class_id=target_class_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error registering student: {str(e)}", 'errormsg')
            return redirect(url_for('teacher_students', class_id=target_class_id))

    attempts_by_student = {
        student.id: ExamAttempt.query.filter_by(student_id=student.id).order_by(ExamAttempt.created_at.desc()).all()
        for student in students
    }
    return render_template('admin/students.html', students=students, classes=classes, selected_class=selected_class, selected_class_id=selected_class_id, skills=skills, attempts_by_student=attempts_by_student)


@app.route('/teacher/skills/', methods=['GET', 'POST'])
def teacher_skills():
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not teacher or not active_year:
        flash('Teacher profile or active VBS year not found.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        action = request.form.get('action', 'create')
        skill_id = request.form.get('skill_id')
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip()
        skill = Skill.query.filter_by(id=int(skill_id), vbs_year_id=active_year.id).first() if skill_id and skill_id.isdigit() else None

        try:
            if action == 'delete' and skill:
                # Keep existing question banks/results safe; remove the optional link only.
                for student in skill.students:
                    student.skill_id = None
                for bank in QuestionBank.query.filter_by(skill_id=skill.id).all():
                    bank.skill_id = None
                db.session.delete(skill)
                flash('Skill removed. Existing question banks were kept as normal banks.', 'feedback')
            elif action == 'edit' and skill and name:
                skill.name = name
                skill.description = description
                flash('Skill updated.', 'feedback')
            elif action == 'create' and name:
                db.session.add(Skill(name=name, description=description, vbs_year_id=active_year.id))
                flash('Skill added.', 'feedback')
            else:
                flash('Skill name is required.', 'errormsg')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating skills: {str(e)}', 'errormsg')
        return redirect(url_for('teacher_skills'))

    skills = Skill.query.filter_by(vbs_year_id=active_year.id).order_by(Skill.name).all()
    return render_template('admin/skills.html', skills=skills, active_year=active_year)

# Edit Student
@app.route('/teacher/students/edit/<int:student_id>/', methods=['GET', 'POST'])
def teacher_student_edit(student_id):
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))
    student = StudentProfile.query.get_or_404(student_id)
    active_year = VbsYear.query.filter_by(is_active=True).first()

    classes = get_teacher_classes(teacher.id, active_year.id if active_year else None)
    if not classes:
        classes = get_teacher_classes(teacher.id)

    class_ids = [c.id for c in classes]

    if student.class_id not in class_ids:
        flash('Unauthorized student modification.', 'errormsg')
        return redirect(url_for('teacher_students'))

    if request.method == 'POST':
        student.first_name = (request.form.get('first_name') or '').strip()
        student.last_name = (request.form.get('last_name') or '').strip()
        student.age = int(request.form.get('age') or student.age)
        student.gender = request.form.get('gender') or student.gender
        target_cls_id = int(request.form.get('class_id') or student.class_id)
        if target_cls_id not in class_ids:
            flash('Unauthorized class transfer.', 'errormsg')
            return redirect(url_for('teacher_students', class_id=student.class_id))
        student.class_id = target_cls_id
        student.parent_name = (request.form.get('parent_name') or '').strip()
        student.parent_phone = (request.form.get('parent_phone') or '').strip()
        skill_id_str = request.form.get('skill_id')
        if skill_id_str:
            try:
                selected_skill = Skill.query.filter_by(id=int(skill_id_str), vbs_year_id=active_year.id).first()
            except (TypeError, ValueError):
                selected_skill = None
            if not selected_skill:
                flash('Selected skill is not valid for the active VBS year.', 'errormsg')
                return redirect(url_for('teacher_student_edit', student_id=student.id))
            student.skill_id = selected_skill.id
        else:
            student.skill_id = None

        try:
            db.session.commit()
            log_audit(current_user_id(), "EDIT_STUDENT", f"Updated details for student {student.first_name}")
            flash('Student record updated.', 'feedback')
            return redirect(url_for('teacher_students', class_id=student.class_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating record: {str(e)}", 'errormsg')
            return redirect(url_for('teacher_student_edit', student_id=student.id))

    skills = Skill.query.filter_by(vbs_year_id=active_year.id if active_year else 0).order_by(Skill.name).all()
    return render_template('admin/student_edit.html', student=student, classes=classes, skills=skills)


@app.route('/teacher/students/reset_password/<int:student_id>/', methods=['POST'])
def teacher_student_reset_password(student_id):
    """Generate a temporary password for the given student and return it to the teacher.
    Only teachers assigned to the student's class may perform this action.
    This avoids storing or exposing an existing plaintext password while still
    allowing teachers to obtain a usable password when necessary.
    """
    if not require_teacher():
        return jsonify({'error': 'Access Denied'}), 403

    teacher = get_effective_teacher_profile()
    if not teacher:
        return jsonify({'error': 'Teacher profile not found'}), 403

    student = StudentProfile.query.get_or_404(student_id)
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    if student.class_id not in class_ids:
        return jsonify({'error': 'Unauthorized student access'}), 403

    try:
        import secrets
        # short, human-friendly temporary password
        pwd = secrets.token_urlsafe(6)
        user = User.query.get(student.user_id)
        if not user:
            return jsonify({'error': 'Linked user not found'}), 404

        user.set_password(pwd)
        user.must_change_password = True
        db.session.commit()
        log_audit(current_user_id(), 'RESET_STUDENT_PASSWORD', f'Reset password for student {student.id} by teacher {teacher.id}')
        return jsonify({'password': pwd})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/teacher/exams/reset-attempt/<int:attempt_id>/', methods=['POST'])
def teacher_reset_exam_attempt(attempt_id):
    if not require_teacher():
        return jsonify(success=False, error='Unauthorized'), 403

    teacher = get_effective_teacher_profile()
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if not teacher or not _teacher_can_access_exam(teacher, attempt.exam):
        return jsonify(success=False, error='Unauthorized'), 403

    if request.is_json:
        payload = request.get_json() or {}
        reason = (payload.get('reason') or 'Teacher-approved reset').strip()
    else:
        reason = (request.form.get('reason') or 'Teacher-approved reset').strip()

    student_id = attempt.student_id
    exam_title = attempt.exam.title
    try:
        db.session.delete(attempt)
        db.session.commit()
        log_audit(current_user_id(), 'RESET_EXAM_ATTEMPT', f'Reset student {student_id} attempt for {exam_title}. Reason: {reason}')
        return jsonify(success=True, message='Attempt reset. Student can start again.')
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500

# Delete Student
@app.route('/teacher/students/delete/<int:student_id>/', methods=['POST'])
def teacher_student_delete(student_id):
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))
    student = StudentProfile.query.get_or_404(student_id)

    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    if student.class_id not in class_ids:
        flash('Unauthorized student modification.', 'errormsg')
        return redirect(url_for('teacher_students'))

    redirect_class_id = student.class_id
    user = User.query.get(student.user_id)
    try:
        db.session.delete(student)
        if user:
            db.session.delete(user)
        db.session.commit()

        log_audit(current_user_id(), "DELETE_STUDENT", f"Deleted student: {student.first_name} {student.last_name}")
        flash('Student deleted successfully.', 'feedback')
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting student: {str(e)}", 'errormsg')

    return redirect(url_for('teacher_students', class_id=redirect_class_id))

# Manual Assessment for Under 6 Students
@app.route('/teacher/assessment/', methods=['GET', 'POST'])
def teacher_assessment():
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not active_year:
        flash('VBS active year must be set first.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    classes = get_teacher_classes(teacher.id, active_year.id)
    if not classes:
        classes = get_teacher_classes(teacher.id)

    selected_class_id = request.args.get('class_id')
    selected_class = None
    if selected_class_id:
        try:
            selected_class_id = int(selected_class_id)
            selected_class = next((c for c in classes if c.id == selected_class_id), None)
        except (TypeError, ValueError):
            selected_class = None

    if not selected_class and classes:
        selected_class = classes[0]
        selected_class_id = selected_class.id

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save_weights':
            class_id = request.form.get('class_id')
            manual_weight = request.form.get('manual_grade_weight')
            cbt_weight = request.form.get('cbt_grade_weight')
            assessment_method = (request.form.get('assessment_method') or '').strip().lower()

            if not class_id or manual_weight is None or cbt_weight is None:
                flash('Class and both weights are required.', 'errormsg')
                return redirect(url_for('teacher_assessment'))

            try:
                target_class = Class.query.get(int(class_id))
                if not target_class or target_class.id not in [c.id for c in classes]:
                    flash('Unauthorized class access.', 'errormsg')
                    return redirect(url_for('teacher_assessment'))

                manual_value = float(manual_weight)
                cbt_value = float(cbt_weight)
                if manual_value < 0 or cbt_value < 0:
                    flash('Weights cannot be negative.', 'errormsg')
                    return redirect(url_for('teacher_assessment', class_id=target_class.id))

                total = manual_value + cbt_value
                if total <= 0:
                    flash('Total weight must be greater than zero.', 'errormsg')
                    return redirect(url_for('teacher_assessment', class_id=target_class.id))

                if assessment_method and assessment_method not in ('manual', 'cbt', 'both'):
                    flash('Assessment mode is invalid.', 'errormsg')
                    return redirect(url_for('teacher_assessment', class_id=target_class.id))

                target_class.manual_grade_weight = manual_value
                target_class.cbt_grade_weight = cbt_value
                if assessment_method:
                    target_class.assessment_method = assessment_method
                db.session.commit()
                log_audit(current_user_id(), 'EDIT_GRADE_WEIGHTS', f"Updated grade weights for {target_class.name}: manual={manual_value}, cbt={cbt_value}, assessment_method={target_class.assessment_method}")
                flash('Class grade weights updated successfully.', 'feedback')
                return redirect(url_for('teacher_assessment', class_id=target_class.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Error updating weights: {str(e)}", 'errormsg')
                return redirect(url_for('teacher_assessment', class_id=class_id))

        if action == 'save_manual_score':
            class_id = request.form.get('class_id')
            student_id_str = request.form.get('student_id')
            manual_score_str = request.form.get('manual_score')
            manual_comment = (request.form.get('manual_comment') or '').strip()

            if not class_id or not student_id_str or manual_score_str is None:
                flash('Class, student, and manual score are required.', 'errormsg')
                return redirect(url_for('teacher_assessment', class_id=selected_class_id or ''))

            try:
                target_class = Class.query.get(int(class_id))
                if not target_class or target_class.id not in [c.id for c in classes]:
                    flash('Unauthorized class access.', 'errormsg')
                    return redirect(url_for('teacher_assessment', class_id=selected_class_id or ''))

                student_id = int(student_id_str)
                target_student = StudentProfile.query.get(student_id)
                if not target_student or target_student.class_id != target_class.id:
                    flash('Invalid student selected.', 'errormsg')
                    return redirect(url_for('teacher_assessment', class_id=target_class.id))

                manual_score = float(manual_score_str)
                if manual_score < 0 or manual_score > 100:
                    flash('Manual score must be between 0 and 100.', 'errormsg')
                    return redirect(url_for('teacher_assessment', class_id=target_class.id))

                fallback_skill = Skill.query.filter_by(vbs_year_id=active_year.id).order_by(Skill.id.asc()).first()
                if not fallback_skill:
                    fallback_skill = Skill(name='Manual Assessment', vbs_year_id=active_year.id)
                    db.session.add(fallback_skill)
                    db.session.commit()

                eval_rec = SkillAssessment.query.filter_by(student_id=student_id).order_by(SkillAssessment.assessed_at.desc()).first()
                if not eval_rec or eval_rec.skill_id != fallback_skill.id:
                    eval_rec = SkillAssessment(student_id=student_id, skill_id=fallback_skill.id, assessed_by=teacher.id)
                    db.session.add(eval_rec)

                eval_rec.score = manual_score
                eval_rec.comments = manual_comment
                eval_rec.assessed_by = teacher.id
                eval_rec.assessed_at = datetime.datetime.utcnow()
                db.session.commit()

                log_audit(current_user_id(), 'MANUAL_ASSESSMENT', f"Saved manual score for {target_student.first_name} {target_student.last_name} in {target_class.name}: {manual_score}")
                flash('Manual score saved successfully.', 'feedback')
                return redirect(url_for('teacher_assessment', class_id=target_class.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Error saving manual score: {str(e)}", 'errormsg')
                return redirect(url_for('teacher_assessment', class_id=class_id))

        student_id_str = request.form.get('student_id')
        skill_id_str = request.form.get('skill_id')
        score_str = request.form.get('score')
        comments = (request.form.get('comments') or '').strip()

        if not student_id_str or not skill_id_str or not score_str:
            flash('All parameters are required.', 'errormsg')
            return redirect(url_for('teacher_assessment', class_id=selected_class_id or ''))

        student_id = int(student_id_str)
        skill_id = int(skill_id_str)
        score = float(score_str)

        target_student = StudentProfile.query.get(student_id)
        if not target_student or target_student.class_id not in [c.id for c in classes]:
            flash('Invalid student selected.', 'errormsg')
            return redirect(url_for('teacher_assessment', class_id=selected_class_id or ''))

        eval_rec = SkillAssessment.query.filter_by(student_id=student_id, skill_id=skill_id).first()
        if not eval_rec:
            eval_rec = SkillAssessment(student_id=student_id, skill_id=skill_id, assessed_by=teacher.id)
            db.session.add(eval_rec)

        eval_rec.score = score
        eval_rec.comments = comments
        eval_rec.assessed_at = datetime.datetime.utcnow()

        try:
            db.session.commit()
            log_audit(current_user_id(), 'MANUAL_ASSESSMENT', f"Assessed student {target_student.first_name} in skill {skill_id} with score {score}")
            flash('Skill assessment saved successfully!', 'feedback')
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving score: {str(e)}", 'errormsg')

        return redirect(url_for('teacher_assessment', class_id=selected_class_id or ''))

    grade_rows = []
    if selected_class:
        selected_class_students = StudentProfile.query.filter_by(class_id=selected_class.id).order_by(StudentProfile.first_name, StudentProfile.last_name).all()
        assessment_mode = (selected_class.assessment_method or (selected_class.category.assessment_method if selected_class.category else 'manual') or 'manual').lower()
        for student in selected_class_students:
            manual_score = None
            manual_comment = ''
            manual_assessment = SkillAssessment.query.filter_by(student_id=student.id).order_by(SkillAssessment.assessed_at.desc()).first()
            if manual_assessment is not None:
                manual_score = min(max(float(manual_assessment.score), 0.0), 100.0)
                manual_comment = manual_assessment.comments or ''

            cbt_score = None
            cbt_possible = 0
            latest_attempt = ExamAttempt.query.filter_by(student_id=student.id, is_submitted=True).order_by(ExamAttempt.end_time.desc(), ExamAttempt.created_at.desc()).first()
            if latest_attempt and latest_attempt.score is not None:
                cbt_score = float(latest_attempt.score)
                cbt_possible = sum(float(aq.question.marks or 0) for aq in latest_attempt.questions)
                if cbt_possible <= 0:
                    cbt_possible = 100.0

            manual_percent = min(max((manual_score / 100.0) * 100.0, 0.0), 100.0) if manual_score is not None else None
            cbt_percent = min(max((cbt_score / cbt_possible) * 100.0, 0.0), 100.0) if cbt_score is not None and cbt_possible else None

            manual_weight = float(selected_class.manual_grade_weight or 50.0)
            cbt_weight = float(selected_class.cbt_grade_weight or 50.0)

            manual_display = f'{manual_score:g} / 100 ({manual_percent:.2f}%)' if manual_score is not None else ('Pending' if assessment_mode == 'both' else '—')
            cbt_display = f'{cbt_score:g} / {cbt_possible:g} ({cbt_percent:.2f}%)' if cbt_score is not None else ('Pending' if assessment_mode == 'both' else '—')

            if manual_score is not None and cbt_score is not None:
                final_score = round(((manual_percent * manual_weight) + (cbt_percent * cbt_weight)) / (manual_weight + cbt_weight), 2)
                mode = 'both'
                final_display = final_score
                comment = manual_comment or 'Manual and CBT scores combined.'
            elif manual_score is not None and assessment_mode == 'both':
                final_score = 'Pending'
                mode = 'manual_pending'
                final_display = 'Pending'
                comment = 'CBT score pending.'
            elif cbt_score is not None and assessment_mode == 'both':
                final_score = 'Pending'
                mode = 'cbt_pending'
                final_display = 'Pending'
                comment = 'Manual score pending.'
            elif manual_score is not None:
                final_score = round(manual_percent, 2)
                mode = 'manual'
                final_display = final_score
                comment = manual_comment or 'Manual assessment only.'
            elif cbt_score is not None:
                final_score = round(cbt_percent, 2)
                mode = 'cbt'
                final_display = final_score
                comment = 'CBT score recorded.'
            else:
                final_score = 'Pending'
                mode = 'pending'
                final_display = 'Pending'
                comment = 'No grade recorded yet.'

            grade_rows.append({
                'student': student,
                'manual_score': manual_score,
                'cbt_score': cbt_score,
                'manual_percent': manual_percent,
                'cbt_percent': cbt_percent,
                'cbt_possible': cbt_possible,
                'manual_display': manual_display,
                'cbt_display': cbt_display,
                'final_score': final_display,
                'mode': mode,
                'comment': comment,
                'assessment_mode': assessment_mode,
            })

    return render_template(
        'admin/assessment.html',
        classes=classes,
        selected_class=selected_class,
        grade_rows=grade_rows,
        students=StudentProfile.query.filter(StudentProfile.class_id.in_([c.id for c in classes])).all() if classes else []
    )

# Question Bank Management (List & Create)
@app.route('/teacher/question-banks/', methods=['GET', 'POST'])
def teacher_question_banks():
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    active_year = VbsYear.query.filter_by(is_active=True).first()

    # Load classes; fall back if the active-year record is stale or a teacher has classes outside the current default year
    classes = get_teacher_classes(teacher.id, active_year.id if active_year else None)
    if not classes:
        classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    skills = Skill.query.filter_by(vbs_year_id=active_year.id if active_year else 0).order_by(Skill.name).all()

    banks = []
    if class_ids:
        banks = QuestionBank.query.filter(
            (QuestionBank.class_id.in_(class_ids)) |
            (QuestionBank.assigned_classes.any(Class.id.in_(class_ids)))
        ).all()

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip()
        class_ids_selected = request.form.getlist('class_ids')
        skill_id_str = request.form.get('skill_id')

        if not name or not class_ids_selected:
            flash('Bank name and at least one class assignment are compulsory.', 'errormsg')
            return redirect(url_for('teacher_question_banks'))

        try:
            selected_classes = []
            for cls_id in class_ids_selected:
                try:
                    cid = int(cls_id)
                    if cid not in class_ids:
                        continue
                    selected_classes.append(cid)
                except (TypeError, ValueError):
                    continue

            if not selected_classes:
                flash('Select a valid class assignment for the question bank.', 'errormsg')
                return redirect(url_for('teacher_question_banks'))

            primary_class_id = selected_classes[0]
            skill_id = None
            if skill_id_str:
                selected_skill = Skill.query.filter_by(id=int(skill_id_str), vbs_year_id=active_year.id).first()
                if not selected_skill:
                    flash('Selected skill is not valid for the active VBS year.', 'errormsg')
                    return redirect(url_for('teacher_question_banks'))
                skill_id = selected_skill.id
            qb = QuestionBank(
                name=name,
                description=description,
                class_id=primary_class_id,
                skill_id=skill_id
            )
            db.session.add(qb)
            db.session.flush()

            for cid in dict.fromkeys(selected_classes[1:]):
                cls = Class.query.get(cid)
                if cls:
                    qb.assigned_classes.append(cls)

            db.session.commit()
            
            log_audit(current_user_id(), "CREATE_QUESTION_BANK", f"Created bank {name} for classes {selected_classes}")
            flash('Question Bank created!', 'feedback')
            return redirect(url_for('teacher_question_banks'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating bank: {str(e)}", 'errormsg')
            return redirect(url_for('teacher_question_banks'))

    return render_template('admin/question_banks.html', banks=banks, classes=classes, skills=skills)

# View details of a specific Question Bank (CRUD questions)
@app.route('/teacher/question-banks/<int:bank_id>/', methods=['GET', 'POST'])
def teacher_question_bank_view(bank_id):
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    bank = QuestionBank.query.get_or_404(bank_id)

    # Auth check
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    if not (set(bank.all_class_ids) & set(class_ids)):
        flash('Access Denied', 'errormsg')
        return redirect(url_for('teacher_question_banks'))

    questions = Question.query.filter_by(question_bank_id=bank.id, is_archived=False).all()

    if request.method == 'POST':
        q_text = (request.form.get('question_text') or '').strip()
        opt_a = (request.form.get('option_a') or '').strip()
        opt_b = (request.form.get('option_b') or '').strip()
        opt_c = (request.form.get('option_c') or '').strip()
        opt_d = (request.form.get('option_d') or '').strip()
        correct = request.form.get('correct_option')
        difficulty = request.form.get('difficulty', 'medium')
        marks_str = request.form.get('marks', '1')
        bible_ref = (request.form.get('bible_reference') or '').strip()
        explanation = (request.form.get('explanation') or '').strip()

        if not all([q_text, opt_a, opt_b, opt_c, opt_d, correct]):
            flash('Question content and options are required.', 'errormsg')
            return redirect(url_for('teacher_question_bank_view', bank_id=bank.id))

        # Check for image file upload
        image_name = None
        img_file = request.files.get('question_image')
        if img_file and img_file.filename != '':
            upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'questions')
            os.makedirs(upload_dir, exist_ok=True)
            ext = os.path.splitext(img_file.filename)[1] or '.jpg'
            image_name = f"q_{bank.id}_{int(time.time())}{ext}"
            img_file.save(os.path.join(upload_dir, image_name))

        try:
            q = Question(
                question_bank_id=bank.id,
                question_text=q_text,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_option=correct,
                difficulty=difficulty,
                marks=int(marks_str),
                bible_reference=bible_ref,
                explanation=explanation,
                image_path=image_name
            )
            db.session.add(q)
            db.session.commit()
            
            log_audit(current_user_id(), "ADD_QUESTION", f"Added question to bank {bank.name}")
            flash('Question added to bank!', 'feedback')
            return redirect(url_for('teacher_question_bank_view', bank_id=bank.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving question: {str(e)}", 'errormsg')
            return redirect(url_for('teacher_question_bank_view', bank_id=bank.id))

    return render_template('admin/question_bank_view.html', bank=bank, questions=questions)

# Edit Question Bank Class Assignments
@app.route('/teacher/question-banks/<int:bank_id>/edit/', methods=['GET', 'POST'])
def teacher_question_bank_edit(bank_id):
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    bank = QuestionBank.query.get_or_404(bank_id)

    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    if not (set(bank.all_class_ids) & set(class_ids)):
        flash('Access Denied', 'errormsg')
        return redirect(url_for('teacher_question_banks'))

    selected_ids = {bank.class_id} | {c.id for c in bank.assigned_classes}

    if request.method == 'POST':
        chosen = request.form.getlist('class_ids')
        valid_ids = []
        for raw_id in chosen:
            try:
                cid = int(raw_id)
                if cid in class_ids and cid not in valid_ids:
                    valid_ids.append(cid)
            except (TypeError, ValueError):
                continue

        if not valid_ids:
            flash('Select at least one valid class for the question bank.', 'errormsg')
            return redirect(url_for('teacher_question_bank_edit', bank_id=bank.id))

        try:
            bank.class_id = valid_ids[0]
            bank.assigned_classes = []
            for cid in valid_ids[1:]:
                cls = Class.query.get(cid)
                if cls:
                    bank.assigned_classes.append(cls)

            db.session.commit()
            log_audit(current_user_id(), "EDIT_QUESTION_BANK_CLASSES", f"Updated classes for bank {bank.name}: {valid_ids}")
            flash('Question bank class assignments updated.', 'feedback')
            return redirect(url_for('teacher_question_bank_view', bank_id=bank.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating bank classes: {str(e)}", 'errormsg')
            return redirect(url_for('teacher_question_bank_edit', bank_id=bank.id))

    return render_template('admin/question_bank_edit.html', bank=bank, classes=classes, selected_ids=selected_ids)

# Edit Question
@app.route('/teacher/question-banks/question/edit/<int:question_id>/', methods=['GET', 'POST'])
def teacher_question_edit(question_id):
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))
    q = Question.query.get_or_404(question_id)
    bank = QuestionBank.query.get(q.question_bank_id)

    # Auth check
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    if not (set(bank.all_class_ids) & set(class_ids)):
        flash('Access Denied', 'errormsg')
        return redirect(url_for('teacher_question_banks'))

    if request.method == 'POST':
        q.question_text = (request.form.get('question_text') or '').strip()
        q.option_a = (request.form.get('option_a') or '').strip()
        q.option_b = (request.form.get('option_b') or '').strip()
        q.option_c = (request.form.get('option_c') or '').strip()
        q.option_d = (request.form.get('option_d') or '').strip()
        q.correct_option = request.form.get('correct_option') or q.correct_option
        q.difficulty = request.form.get('difficulty') or q.difficulty
        q.marks = int(request.form.get('marks') or q.marks)
        q.bible_reference = (request.form.get('bible_reference') or '').strip()
        q.explanation = (request.form.get('explanation') or '').strip()

        img_file = request.files.get('question_image')
        if img_file and img_file.filename != '':
            upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'questions')
            os.makedirs(upload_dir, exist_ok=True)
            ext = os.path.splitext(img_file.filename)[1] or '.jpg'
            image_name = f"q_{bank.id}_{int(time.time())}{ext}"
            img_file.save(os.path.join(upload_dir, image_name))
            q.image_path = image_name

        try:
            db.session.commit()
            log_audit(current_user_id(), "EDIT_QUESTION", f"Modified question ID {q.id}")
            flash('Question updated successfully.', 'feedback')
            return redirect(url_for('teacher_question_bank_view', bank_id=bank.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error modifying question: {str(e)}", 'errormsg')

    return render_template('admin/question_edit.html', question=q, bank=bank)

# Archive Question
@app.route('/teacher/question-banks/question/archive/<int:question_id>/', methods=['POST'])
def teacher_question_archive(question_id):
    if not require_teacher():
        return jsonify(success=False, error="Unauthorized"), 403

    teacher = get_effective_teacher_profile()
    if not teacher:
        return jsonify(success=False, error="Teacher profile not found"), 403
    q = Question.query.get_or_404(question_id)
    bank = QuestionBank.query.get(q.question_bank_id)

    # Auth check
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    if not (set(bank.all_class_ids) & set(class_ids)):
        return jsonify(success=False, error="Unauthorized"), 403

    q.is_archived = True
    db.session.commit()
    log_audit(current_user_id(), "ARCHIVE_QUESTION", f"Archived question ID {q.id}")
    return jsonify(success=True)

# Exam Builder Dashboard (List & Create Exams)
@app.route('/teacher/exams/', methods=['GET', 'POST'])
def teacher_exams():
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))
    active_year = VbsYear.query.filter_by(is_active=True).first()

    if not active_year:
        flash('VBS active year must be set first.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))

    # Load classes
    classes = get_teacher_classes(teacher.id, active_year.id)
    class_ids = [c.id for c in classes]

    exams = []
    if class_ids:
        sub = db.session.query(exam_classes.c.exam_id).filter(exam_classes.c.class_id.in_(class_ids))
        exams = Exam.query.filter((Exam.class_id.in_(class_ids)) | (Exam.id.in_(sub))).all()

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        selected_classes = request.form.getlist('class_ids')
        duration_str = request.form.get('duration_minutes', '30')
        skill_count_str = request.form.get('skill_question_count', '0')

        if not title or not selected_classes:
            flash('Compulsory fields must be completed.', 'errormsg')
            return redirect(url_for('teacher_exams'))

        try:
            primary_class = int(selected_classes[0])
            exam = Exam(
                title=title,
                class_id=primary_class,
                vbs_year_id=active_year.id,
                duration_minutes=int(duration_str),
                skill_question_count=max(0, int(skill_count_str or 0)),
                is_draft=True
            )
            db.session.add(exam)
            db.session.flush()

            # handle multiple class assignments
            for cs in selected_classes:
                try:
                    cid = int(cs)
                    db.session.execute(exam_classes.insert().values(exam_id=exam.id, class_id=cid))
                except Exception:
                    continue

            db.session.commit()

            log_audit(current_user_id(), "CREATE_EXAM", f"Created exam paper {title}")
            flash('Exam header created! Add sections to complete quiz setup.', 'feedback')
            return redirect(url_for('teacher_exam_edit', exam_id=exam.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating exam: {str(e)}", 'errormsg')
            return redirect(url_for('teacher_exams'))

    # Build map of exam_id -> assigned classes using ORM relationship
    exam_classes_map = {}
    for ex in exams:
        cls_list = []
        if ex.class_:
            cls_list.append(ex.class_)
        for c in getattr(ex, 'assigned_classes', []):
            if c.id not in [x.id for x in cls_list]:
                cls_list.append(c)
        exam_classes_map[ex.id] = cls_list

    return render_template('admin/exams.html', exams=exams, classes=classes, exam_classes_map=exam_classes_map)


def _teacher_can_access_exam(teacher, exam):
    if not teacher:
        return False
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    assigned_ids = [c.id for c in getattr(exam, 'assigned_classes', [])]
    return exam.class_id in class_ids or any(cid in class_ids for cid in assigned_ids)


def _clear_teacher_preview_session():
    session.pop('teacher_preview_exam_id', None)
    session.pop('teacher_preview_skill_id', None)
    session.pop('teacher_preview_question_ids', None)


@app.route('/teacher/exams/preview/<int:exam_id>/', methods=['GET'])
def teacher_exam_preview(exam_id):
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    exam = Exam.query.get_or_404(exam_id)
    if not _teacher_can_access_exam(teacher, exam):
        flash('Access Denied', 'errormsg')
        return redirect(url_for('teacher_exams'))

    skill_map = exam_skill_options(exam)
    if request.args.get('skill_id') or request.args.get('no_skill') == '1':
        session['teacher_preview_exam_id'] = exam.id
        session['teacher_preview_skill_id'] = request.args.get('skill_id', type=int)
        session.pop('teacher_preview_question_ids', None)
        return render_template('user/exam_prestart.html', exam=exam, test_mode=True)

    return render_template('admin/exam_preview_select.html', exam=exam, skill_map=skill_map)


@app.route('/teacher/exams/preview/<int:exam_id>/start/', methods=['POST'])
def teacher_exam_preview_start(exam_id):
    if not require_teacher():
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    exam = Exam.query.get_or_404(exam_id)
    if not _teacher_can_access_exam(teacher, exam) or session.get('teacher_preview_exam_id') != exam_id:
        flash('Choose a Test Exam scenario first.', 'errormsg')
        return redirect(url_for('teacher_exam_preview', exam_id=exam.id))

    selected_questions = build_exam_questions(exam, skill_id=session.get('teacher_preview_skill_id'))
    if not selected_questions:
        flash('This exam has no available questions to preview.', 'errormsg')
        return redirect(url_for('teacher_exams'))

    session['teacher_preview_question_ids'] = [q.id for q in selected_questions]
    questions = present_questions(selected_questions)
    return render_template(
        'user/exam_run.html',
        exam=exam,
        attempt={'id': 0},
        questions=questions,
        remaining_seconds=exam.duration_minutes * 60,
        test_mode=True,
    )


@app.route('/teacher/exams/preview/<int:exam_id>/submit/', methods=['POST'])
def teacher_exam_preview_submit(exam_id):
    if not require_teacher() or session.get('teacher_preview_exam_id') != exam_id:
        return redirect(url_for('teacher_exams'))
    question_ids = session.pop('teacher_preview_question_ids', [])
    exam = Exam.query.get_or_404(exam_id)
    questions = Question.query.filter(Question.id.in_(question_ids)).all() if question_ids else []
    answers = {str(qid): request.form.get(f'q_option_{qid}') for qid in question_ids}
    correct = sum(1 for q in questions if answers.get(str(q.id)) == q.correct_option)
    _clear_teacher_preview_session()
    return render_template('admin/exam_preview_result.html', exam=exam, total=len(question_ids), correct=correct)

# Edit Exam & Manage Sections Rules
@app.route('/teacher/exams/edit/<int:exam_id>/', methods=['GET', 'POST'])
def teacher_exam_edit(exam_id):
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))
    exam = Exam.query.get_or_404(exam_id)

    # Auth check
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    # Allow access if teacher manages the primary class or any assigned class for this exam
    assigned_ids = [c.id for c in getattr(exam, 'assigned_classes', [])]
    if not (exam.class_id in class_ids or any(a in class_ids for a in assigned_ids)):
        flash('Access Denied', 'errormsg')
        return redirect(url_for('teacher_exams'))

    sections = ExamSection.query.filter_by(exam_id=exam.id).all()
    
    # Pull valid question banks matching any class connected to this exam
    exam_class_ids = [exam.class_id] + [c.id for c in getattr(exam, 'assigned_classes', [])]
    question_banks = QuestionBank.query.filter(
        (QuestionBank.class_id.in_(exam_class_ids)) |
        (QuestionBank.assigned_classes.any(Class.id.in_(exam_class_ids)))
    ).distinct().all()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_header':
            exam.title = (request.form.get('title') or '').strip()
            exam.duration_minutes = int(request.form.get('duration_minutes') or 30)
            exam.skill_question_count = max(0, int(request.form.get('skill_question_count') or 0))
            db.session.commit()
            log_audit(current_user_id(), "EDIT_EXAM_HEADER", f"Updated exam settings for {exam.title}")
            flash('Exam settings updated.', 'feedback')
            return redirect(url_for('teacher_exam_edit', exam_id=exam.id))
            
        elif action == 'add_section':
            sec_title = (request.form.get('sec_title') or '').strip()
            sec_desc = (request.form.get('sec_description') or '').strip()
            # Support either legacy single-bank (question_bank_id + question_count)
            # or new multi-bank flow using bank_ids[] and bank_counts[]
            bank_id_str = request.form.get('question_bank_id')
            q_count_str = request.form.get('question_count')
            bank_ids = request.form.getlist('bank_ids')
            bank_counts = request.form.getlist('bank_counts')
            # support comma-separated single value like "2,3" posted from simple form
            if bank_counts and len(bank_counts) == 1 and isinstance(bank_counts[0], str) and ',' in bank_counts[0]:
                bank_counts = [x.strip() for x in bank_counts[0].split(',') if x.strip()!='']
            difficulty = request.form.get('difficulty_filter', 'any')

            if not sec_title or (not bank_id_str and not bank_ids):
                flash('All section details must be completed.', 'errormsg')
                return redirect(url_for('teacher_exam_edit', exam_id=exam.id))

            try:
                # Create section record first; if multi-bank, set primary to first bank
                if bank_ids:
                    primary_bank = int(bank_ids[0])
                    # compute per-bank counts
                    counts = []
                    if bank_counts and len(bank_counts) == len(bank_ids):
                        for c in bank_counts:
                            try:
                                counts.append(int(c))
                            except Exception:
                                counts.append(0)
                    else:
                        # fallback: if a single question_count provided, distribute to first
                        total = int(q_count_str) if q_count_str else 0
                        if total and len(bank_ids) == 1:
                            counts = [total]
                        else:
                            # default 1 per bank
                            counts = [1] * len(bank_ids)

                    total_q = sum(counts)
                    new_sec = ExamSection(
                        exam_id=exam.id,
                        title=sec_title,
                        description=sec_desc,
                        question_bank_id=primary_bank,
                        question_count=total_q,
                        difficulty_filter=difficulty
                    )
                    db.session.add(new_sec)
                    db.session.flush()

                    # persist rules
                    for bid, cnt in zip(bank_ids, counts):
                        try:
                            bid_i = int(bid)
                        except Exception:
                            continue
                        rule = ExamSectionBankRule(exam_section_id=new_sec.id, question_bank_id=bid_i, question_count=max(0, int(cnt)))
                        db.session.add(rule)

                    db.session.commit()
                else:
                    # legacy single bank
                    if not q_count_str or not bank_id_str:
                        flash('All section details must be completed.', 'errormsg')
                        return redirect(url_for('teacher_exam_edit', exam_id=exam.id))

                    new_sec = ExamSection(
                        exam_id=exam.id,
                        title=sec_title,
                        description=sec_desc,
                        question_bank_id=int(bank_id_str),
                        question_count=int(q_count_str),
                        difficulty_filter=difficulty
                    )
                    db.session.add(new_sec)
                    db.session.commit()

                log_audit(current_user_id(), "ADD_EXAM_SECTION", f"Added section {sec_title} to exam {exam.title}")
                flash('Exam Section added successfully!', 'feedback')
                return redirect(url_for('teacher_exam_edit', exam_id=exam.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Error creating section: {str(e)}", 'errormsg')
                return redirect(url_for('teacher_exam_edit', exam_id=exam.id))

    return render_template('admin/exam_edit.html', exam=exam, sections=sections, question_banks=question_banks, classes=classes)

# Delete Exam Section
@app.route('/teacher/exams/section/delete/<int:section_id>/', methods=['POST'])
def teacher_exam_section_delete(section_id):
    if not require_teacher():
        return jsonify(success=False, error="Unauthorized"), 403

    teacher = get_effective_teacher_profile()
    if not teacher:
        return jsonify(success=False, error="Teacher profile not found"), 403
    sec = ExamSection.query.get_or_404(section_id)
    exam = Exam.query.get(sec.exam_id)

    # Auth check
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    assigned_ids = [c.id for c in getattr(exam, 'assigned_classes', [])]
    if not (exam.class_id in class_ids or any(a in class_ids for a in assigned_ids)):
        return jsonify(success=False, error="Unauthorized"), 403

    try:
        db.session.delete(sec)
        db.session.commit()
        log_audit(current_user_id(), "DELETE_EXAM_SECTION", f"Deleted section ID {sec.id} from exam {exam.title}")
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500

# Toggle Exam Published Status (Draft vs Published)
@app.route('/teacher/exams/toggle-draft/<int:exam_id>/', methods=['POST'])
def teacher_exam_toggle_draft(exam_id):
    if not require_teacher():
        return jsonify(success=False, error="Unauthorized"), 403

    teacher = get_effective_teacher_profile()
    if not teacher:
        return jsonify(success=False, error="Teacher profile not found"), 403
    exam = Exam.query.get_or_404(exam_id)

    # Auth check
    classes = get_teacher_classes(teacher.id)
    class_ids = [c.id for c in classes]
    assigned_ids = [c.id for c in getattr(exam, 'assigned_classes', [])]
    if not (exam.class_id in class_ids or any(a in class_ids for a in assigned_ids)):
        return jsonify(success=False, error="Unauthorized"), 403

    if exam.is_draft:
        exam_class_ids = {exam.class_id} | {c.id for c in exam.assigned_classes}
        other_active = []
        for other in Exam.query.filter(Exam.vbs_year_id == exam.vbs_year_id, Exam.id != exam.id, Exam.is_draft == False).all():
            other_class_ids = {other.class_id} | {c.id for c in other.assigned_classes}
            if exam_class_ids & other_class_ids:
                other_active.append(other)
        if other_active:
            return jsonify(success=False, error='Each class can have only one active CBT exam per VBS year.'), 409

    exam.is_draft = not exam.is_draft
    db.session.commit()
    
    status = "drafted" if exam.is_draft else "published"
    log_audit(current_user_id(), "TOGGLE_EXAM_STATUS", f"Exam {exam.title} is now {status}")
    return jsonify(success=True, is_draft=exam.is_draft)

# Live Exam Monitoring
@app.route('/teacher/exams/monitor/')
def teacher_exam_monitor():
    if not require_teacher():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    teacher = get_effective_teacher_profile()
    if not teacher:
        flash('Teacher profile not found. Please contact the admin.', 'errormsg')
        return redirect(url_for('teacher_dashboard'))
    active_year = VbsYear.query.filter_by(is_active=True).first()

    classes = get_teacher_classes(teacher.id, active_year.id if active_year else None)
    if not classes:
        classes = get_teacher_classes(teacher.id)

    class_ids = [c.id for c in classes]

    active_attempts = []
    class_groups = {}
    if class_ids:
        active_attempts = ExamAttempt.query.join(StudentProfile).filter(
            StudentProfile.class_id.in_(class_ids),
            ExamAttempt.is_submitted == False
        ).order_by(ExamAttempt.start_time.desc()).all()

        for cls in classes:
            class_groups[cls.id] = []
        for attempt in active_attempts:
            student = attempt.student
            if student and student.class_id in class_groups:
                class_groups[student.class_id].append(attempt)

    return render_template('admin/monitor.html', attempts=active_attempts, class_groups=class_groups, classes=classes)
