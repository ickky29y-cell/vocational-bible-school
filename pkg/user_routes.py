import datetime
import json
import time
import os
import random
import base64
from flask import render_template, url_for, request, redirect, flash, session, jsonify
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from pkg import app, db
from flask_login import login_user, logout_user, current_user
from pkg.models import User, Role, VbsYear, StudentProfile, Class, Exam, ExamSection, Question, QuestionBank, ExamAttempt, AttemptQuestion, Announcement, AuditLog, SkillAssessment, TeacherProfile, Skill
from pkg.models import AdmissionApplication
from pkg.utils import current_user_id, current_role_name
from pkg.exam_paper import build_exam_questions

# Helper to write to audit log
def log_audit(user_id, action, details=None):
    try:
        ip = request.remote_addr
        log = AuditLog(user_id=user_id, action=action, ip_address=ip, details=details)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

# Global template context injector
@app.context_processor
def inject_global_data():
    deets = None
    if current_user and getattr(current_user, 'is_authenticated', False):
        deets = current_user
    else:
        uid = current_user_id()
        if uid:
            deets = User.query.get(uid)
    active_year = VbsYear.query.filter_by(is_active=True).first()
    return dict(
        deets=deets,
        active_year=active_year,
        datetime=datetime
    )

# Home / Index Router
@app.route('/', endpoint='home_page')
@app.route('/user/index/', endpoint='user_index')
def home_page():
    if current_user and getattr(current_user, 'is_authenticated', False):
        role = current_role_name()
        if role == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
        elif role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif role == 'student':
            return redirect(url_for('student_dashboard'))
    return render_template('user/index.html')


# Public admission application
@app.route('/admission/apply/', methods=['GET', 'POST'])
def admission_apply():
    if request.method == 'POST':
        first_name = (request.form.get('first_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()
        email = (request.form.get('email') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        dob_str = (request.form.get('dob') or '').strip()

        if not first_name or not last_name or not email:
            flash('Please complete required fields', 'errormsg')
            return redirect(url_for('admission_apply'))

        dob = None
        try:
            if dob_str:
                dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d').date()
        except Exception:
            dob = None

        try:
            app_rec = AdmissionApplication(first_name=first_name, last_name=last_name, email=email, phone=phone, dob=dob)
            db.session.add(app_rec)
            db.session.commit()
            log_audit(None, 'ADMISSION_SUBMIT', f"Admission submitted: {email}")
            flash('Application submitted. Chaplain will review and contact you.', 'feedback')
            return redirect(url_for('home_page'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting application: {str(e)}', 'errormsg')
            return redirect(url_for('admission_apply'))

    return render_template('user/admission_apply.html')

# User login routing
@app.route('/user/login/', methods=['GET', 'POST'])
def user_login():
    if current_user and getattr(current_user, 'is_authenticated', False):
        return redirect(url_for('home_page'))

    if request.method == 'POST':
        identity = (request.form.get('identity') or '').strip() # Can be username or email
        password = (request.form.get('password') or '').strip()

        if not identity or not password:
            flash('Both fields are compulsory', 'errormsg')
            return redirect(url_for('user_login'))

        user = User.query.filter((User.email == identity) | (User.username == identity)).first()
        if user and user.is_active and user.check_password(password):
            # Login via Flask-Login and keep legacy session vars for templates
            login_user(user)
            session['useronline'] = user.id
            session['role'] = user.role.name
            user.last_login_at = datetime.datetime.utcnow()
            db.session.commit()

            log_audit(user.id, "LOGIN", f"Successful login for {user.username}")
            flash('Welcome! Login successful.', 'feedback')
            if user.must_change_password and user.role.name == 'student':
                return redirect(url_for('student_change_password'))
            return redirect(url_for('home_page'))
        else:
            log_audit(None, "LOGIN_FAILED", f"Attempted login with username/email: {identity}")
            flash('Invalid username/email or password', 'errormsg')
            return redirect(url_for('user_login'))

    return render_template('user/login.html')


@app.route('/student/change-password/', methods=['GET', 'POST'])
def student_change_password():
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        return redirect(url_for('user_login'))

    if not current_user.must_change_password:
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        password = (request.form.get('password') or '').strip()
        confirmation = (request.form.get('confirm_password') or '').strip()
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'errormsg')
        elif password != confirmation:
            flash('Passwords do not match.', 'errormsg')
        else:
            current_user.set_password(password)
            current_user.must_change_password = False
            db.session.commit()
            flash('Password updated successfully.', 'feedback')
            return redirect(url_for('student_dashboard'))

    return render_template('user/change_password.html')

# User logout routing
@app.route('/user/logout/')
def user_logout():
    user_id = current_user_id()
    if user_id:
        log_audit(user_id, "LOGOUT", "User logged out")
    # Logout from Flask-Login and clear session
    try:
        logout_user()
    except Exception:
        pass
    session.clear()
    flash('You have logged out successfully', 'info')
    return redirect(url_for('home_page'))

# Student Dashboard
@app.route('/student/dashboard/')
def student_dashboard():
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        flash('Login as student first', 'errormsg')
        return redirect(url_for('user_login'))

    if current_user.must_change_password:
        return redirect(url_for('student_change_password'))

    student = StudentProfile.query.filter_by(user_id=current_user_id()).first()
    if not student:
        flash('Student record not found.', 'errormsg')
        session.clear()
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    announcements = Announcement.query.filter(Announcement.target_role.in_(['all', 'student'])).order_by(Announcement.created_at.desc()).all()
    
    # Fetch student's assigned class for active VBS Year
    student_class = Class.query.filter_by(id=student.class_id, vbs_year_id=active_year.id if active_year else None).first()
    
    exams = []
    attempts_map = {}
    attempt_totals_map = {}
    is_under_six = False
    has_manual_assessment = False
    skills_assessments = []
    assessment_summary = {'manual_earned': 0, 'manual_possible': 0, 'cbt_earned': 0, 'cbt_possible': 0}

    if student_class:
        effective_method = student_class.assessment_method or (student_class.category.assessment_method if student_class.category else None)
        if effective_method == 'manual':
            is_under_six = True
        skills_assessments = SkillAssessment.query.filter_by(student_id=student.id).all()
        has_manual_assessment = effective_method in ('manual', 'both') or bool(skills_assessments)
        if effective_method != 'manual':
            # Fetch exams for student class
            # Include exams directly assigned to the class plus exams assigned via the many-to-many mapping
            sub = db.session.query(Exam.id).join(Exam.assigned_classes).filter(Class.id == student_class.id)
            exams = Exam.query.filter((Exam.class_id == student_class.id) | (Exam.id.in_(sub)), Exam.is_draft == False).all()
            for exam in exams:
                attempt = ExamAttempt.query.filter_by(student_id=student.id, exam_id=exam.id).order_by(ExamAttempt.created_at.desc()).first()
                if attempt:
                    attempts_map[exam.id] = attempt
                    attempt_totals_map[exam.id] = sum((q.question.marks or 0) for q in attempt.questions)

    assessment_summary['manual_earned'] = sum(float(record.score or 0) for record in skills_assessments)
    assessment_summary['manual_possible'] = len(skills_assessments) * 100
    has_printable_result = bool(skills_assessments) or any(attempt.is_submitted for attempt in attempts_map.values())
    if attempts_map:
        latest_exam_id = next(iter(attempts_map))
        assessment_summary['cbt_earned'] = float(attempts_map[latest_exam_id].score or 0)
        assessment_summary['cbt_possible'] = attempt_totals_map.get(latest_exam_id, 0)

    return render_template(
        'user/dashboard.html',
        student=student,
        student_class=student_class,
        exams=exams,
        attempts_map=attempts_map,
        attempt_totals_map=attempt_totals_map,
        is_under_six=is_under_six,
        has_manual_assessment=has_manual_assessment,
        assessment_summary=assessment_summary,
        skills_assessments=skills_assessments,
        has_printable_result=has_printable_result,
        announcements=announcements
    )


@app.route('/student/result/print/')
def student_result_print():
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    student = StudentProfile.query.filter_by(user_id=current_user_id()).first()
    if not student:
        flash('Student record not found.', 'errormsg')
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not active_year or not active_year.results_released:
        flash('Results are not yet released by the Chaplain.', 'info')
        return redirect(url_for('student_dashboard'))

    student_class = Class.query.filter_by(id=student.class_id, vbs_year_id=active_year.id).first()
    if not student_class:
        flash('Your class result is not available yet.', 'info')
        return redirect(url_for('student_dashboard'))

    effective_method = (student_class.assessment_method or (student_class.category.assessment_method if student_class.category else None) or 'cbt').lower()
    manual_assessments = SkillAssessment.query.filter_by(student_id=student.id).order_by(SkillAssessment.assessed_at.asc()).all()

    sub = db.session.query(Exam.id).join(Exam.assigned_classes).filter(Class.id == student_class.id)
    exams = Exam.query.filter(((Exam.class_id == student_class.id) | (Exam.id.in_(sub))), Exam.is_draft == False).order_by(Exam.title.asc()).all()
    cbt_results = []
    for exam in exams:
        attempt = ExamAttempt.query.filter_by(student_id=student.id, exam_id=exam.id, is_submitted=True).order_by(ExamAttempt.end_time.desc(), ExamAttempt.created_at.desc()).first()
        if not attempt:
            continue
        possible = sum(float(aq.question.marks or 0) for aq in attempt.questions) or 100.0
        earned = float(attempt.score or 0)
        cbt_results.append({'exam': exam, 'attempt': attempt, 'earned': earned, 'possible': possible, 'percentage': round((earned / possible) * 100, 2) if possible else 0})

    manual_earned = sum(float(record.score or 0) for record in manual_assessments)
    manual_possible = len(manual_assessments) * 100
    cbt_earned = sum(result['earned'] for result in cbt_results)
    cbt_possible = sum(result['possible'] for result in cbt_results)
    manual_percentage = round((manual_earned / manual_possible) * 100, 2) if manual_possible else None
    cbt_percentage = round((cbt_earned / cbt_possible) * 100, 2) if cbt_possible else None

    has_manual = bool(manual_assessments)
    has_cbt = bool(cbt_results)
    if has_manual and has_cbt:
        result_type = 'Combined'
        manual_weight = float(student_class.manual_grade_weight or 50.0)
        cbt_weight = float(student_class.cbt_grade_weight or 50.0)
        final_percentage = round(((manual_percentage * manual_weight) + (cbt_percentage * cbt_weight)) / (manual_weight + cbt_weight), 2)
    elif has_manual:
        result_type = 'Manual'
        manual_weight = cbt_weight = None
        final_percentage = manual_percentage
    elif has_cbt:
        result_type = 'CBT'
        manual_weight = cbt_weight = None
        final_percentage = cbt_percentage
    else:
        flash('Your result is not available yet.', 'info')
        return redirect(url_for('student_dashboard'))

    return render_template('user/result_print.html', student=student, student_class=student_class, active_year=active_year, result_type=result_type, manual_assessments=manual_assessments if has_manual else [], manual_earned=manual_earned if has_manual else None, manual_possible=manual_possible if has_manual else None, manual_percentage=manual_percentage if has_manual else None, cbt_results=cbt_results if has_cbt else [], cbt_earned=cbt_earned if has_cbt else None, cbt_possible=cbt_possible if has_cbt else None, cbt_percentage=cbt_percentage if has_cbt else None, manual_weight=manual_weight, cbt_weight=cbt_weight, final_percentage=final_percentage, generated_at=datetime.datetime.now())

# Student Exam Instructions Accept and Selfie snap
@app.route('/student/exam/prestart/<int:exam_id>/', methods=['GET', 'POST'])
def student_exam_prestart(exam_id):
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        flash('Unauthorized Access', 'errormsg')
        return redirect(url_for('user_login'))

    student = StudentProfile.query.filter_by(user_id=current_user_id()).first()
    exam = Exam.query.get_or_404(exam_id)
    
    # Check if student is allowed in class (support exams assigned to multiple classes)
    allowed_class_ids = [exam.class_id] + [c.id for c in exam.assigned_classes]
    if student.class_id not in allowed_class_ids:
        flash('Unauthorized exam session', 'errormsg')
        return redirect(url_for('student_dashboard'))

    # Check if already submitted
    attempt = ExamAttempt.query.filter_by(student_id=student.id, exam_id=exam.id, is_submitted=True).first()
    if attempt:
        flash('You have already taken this exam.', 'info')
        return redirect(url_for('student_dashboard'))

    # If post, save selfie and create draft attempt
    if request.method == 'POST':
        selfie_data = request.form.get('selfie_image') # base64 format
        if not selfie_data:
            flash('Webcam selfie snapshot is required to start the exam.', 'errormsg')
            return redirect(url_for('student_exam_prestart', exam_id=exam.id))

        try:
            # Create attempt
            new_attempt = ExamAttempt.query.filter_by(student_id=student.id, exam_id=exam.id, is_submitted=False).first()
            if not new_attempt:
                new_attempt = ExamAttempt(student_id=student.id, exam_id=exam.id, class_id=student.class_id, is_submitted=False)
                db.session.add(new_attempt)
                db.session.flush()

            if selfie_data == 'skipped':
                new_attempt.selfie_path = 'skipped'
                new_attempt.start_time = datetime.datetime.utcnow()
                db.session.commit()
                log_audit(current_user_id(), "EXAM_START_WITHOUT_SELFIE", f"Started exam {exam.title} (Selfie Skipped, Attempt: {new_attempt.id})")
            else:
                # Save selfie image to disk
                upload_dir = os.path.join(app.instance_path, 'uploads', 'selfies')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Remove base64 metadata header if present
                if ',' in selfie_data:
                    selfie_data = selfie_data.split(',')[1]

                img_bytes = base64.b64decode(selfie_data)
                filename = f"selfie_{new_attempt.id}_{int(time.time())}.jpg"
                file_path = os.path.join(upload_dir, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(img_bytes)

                new_attempt.selfie_path = filename
                new_attempt.start_time = datetime.datetime.utcnow()
                db.session.commit()
                log_audit(current_user_id(), "EXAM_START", f"Started exam {exam.title} (Attempt: {new_attempt.id})")
            
            return redirect(url_for('student_exam_run', attempt_id=new_attempt.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error starting exam: {str(e)}", 'errormsg')
            return redirect(url_for('student_exam_prestart', exam_id=exam.id))

    return render_template('user/exam_prestart.html', exam=exam, student=student)

# CBT Exam navigation and answering screen
@app.route('/student/exam/run/<int:attempt_id>/')
def student_exam_run(attempt_id):
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    student = StudentProfile.query.filter_by(user_id=current_user_id()).first()
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id:
        flash('Unauthorized Access', 'errormsg')
        return redirect(url_for('student_dashboard'))

    if attempt.is_submitted:
        flash('This attempt has already been submitted.', 'info')
        return redirect(url_for('student_dashboard'))

    exam = attempt.exam
    elapsed = (datetime.datetime.utcnow() - attempt.start_time).total_seconds()
    time_limit = exam.duration_minutes * 60
    
    if elapsed >= time_limit:
        # Time expired, auto-submit
        return redirect(url_for('student_exam_submit_route', attempt_id=attempt.id))

    remaining_seconds = int(time_limit - elapsed)

    # Initialize questions if they are empty
    attempt_questions = AttemptQuestion.query.filter_by(attempt_id=attempt.id).order_by(AttemptQuestion.id.asc()).all()
    
    if not attempt_questions:
        selected_questions = build_exam_questions(exam, skill_id=student.skill_id)

        if not selected_questions:
            flash('No questions found for this exam. Please contact your teacher.', 'errormsg')
            return redirect(url_for('student_dashboard'))

        # Add to AttemptQuestion table
        for q in selected_questions:
            # Shuffle presentation order of options: A, B, C, D
            opts = ['A', 'B', 'C', 'D']
            random.shuffle(opts)
            opt_order = ",".join(opts)

            aq = AttemptQuestion(
                attempt_id=attempt.id,
                question_id=q.id,
                option_order=opt_order
            )
            db.session.add(aq)
        
        try:
            db.session.commit()
            attempt_questions = AttemptQuestion.query.filter_by(attempt_id=attempt.id).order_by(AttemptQuestion.id.asc()).all()
        except Exception as e:
            db.session.rollback()
            flash(f"Error building quiz questions: {str(e)}", 'errormsg')
            return redirect(url_for('student_dashboard'))

    # Load questions alongside the custom option display order mapping
    parsed_questions = []
    for aq in attempt_questions:
        q = aq.question
        opts_mapping = {
            'A': q.option_a,
            'B': q.option_b,
            'C': q.option_c,
            'D': q.option_d
        }
        ordered_options = []
        for letter in aq.option_order.split(','):
            ordered_options.append({
                'letter': letter,
                'text': opts_mapping[letter]
            })

        parsed_questions.append({
            'aq_id': aq.id,
            'q_id': q.id,
            'text': q.question_text,
            'image': q.image_path,
            'bible_ref': q.bible_reference,
            'options': ordered_options,
            'selected': aq.selected_option
        })

    return render_template(
        'user/exam_run.html',
        attempt=attempt,
        exam=exam,
        questions=parsed_questions,
        remaining_seconds=remaining_seconds
    )

# Student Exam Autosave Endpoint
@app.route('/student/exam/autosave/<int:attempt_id>/', methods=['POST'])
def student_exam_autosave(attempt_id):
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        return jsonify(success=False, error="Unauthorized"), 403

    student = StudentProfile.query.filter_by(user_id=current_user_id()).first()
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id or attempt.is_submitted:
        return jsonify(success=False, error="Unauthorized/Submitted"), 403

    data = request.get_json() or {}
    aq_id = data.get('aq_id')
    selected_option = data.get('selected_option') # 'A', 'B', 'C', 'D' or None/Null

    aq = AttemptQuestion.query.filter_by(id=aq_id, attempt_id=attempt.id).first()
    if aq:
        aq.selected_option = selected_option
        
        # Verify correctness immediately and score
        q = aq.question
        if selected_option and selected_option == q.correct_option:
            aq.is_correct = True
            aq.marks_obtained = q.marks
        else:
            aq.is_correct = False
            aq.marks_obtained = 0

        db.session.commit()
        return jsonify(success=True)

    return jsonify(success=False, error="Question not found"), 404

# Submit exam route
@app.route('/student/exam/submit/<int:attempt_id>/', methods=['POST', 'GET'], endpoint='student_exam_submit_route')
def student_exam_submit(attempt_id):
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    student = StudentProfile.query.filter_by(user_id=current_user_id()).first()
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id:
        flash('Unauthorized Access', 'errormsg')
        return redirect(url_for('student_dashboard'))

    if not attempt.is_submitted:
        attempt.is_submitted = True
        attempt.end_time = datetime.datetime.utcnow()
        
        # Sum marks obtained
        total_marks = db.session.query(func.sum(AttemptQuestion.marks_obtained)).filter_by(attempt_id=attempt.id).scalar() or 0
        attempt.score = float(total_marks)
        
        db.session.commit()
        log_audit(current_user_id(), "EXAM_SUBMISSION", f"Submitted Exam: {attempt.exam.title}. Score: {attempt.score}")
        flash('Exam successfully submitted! Good job.', 'feedback')

    return redirect(url_for('student_dashboard'))

# Student view exam feedback details (only after release by Super Admin)
@app.route('/student/exam/result/<int:attempt_id>/')
def student_exam_result(attempt_id):
    if not (current_user and getattr(current_user, 'is_authenticated', False)) or current_role_name() != 'student':
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    student = StudentProfile.query.filter_by(user_id=current_user_id()).first()
    attempt = ExamAttempt.query.get_or_404(attempt_id)

    if attempt.student_id != student.id:
        flash('Unauthorized Access', 'errormsg')
        return redirect(url_for('student_dashboard'))

    exam = attempt.exam
    vbs_year = VbsYear.query.get(exam.vbs_year_id)

    if not vbs_year or not vbs_year.results_released:
        flash('Exam results are not yet released by the Chaplain.', 'info')
        return redirect(url_for('student_dashboard'))

    # Load details of questions
    attempt_questions = AttemptQuestion.query.filter_by(attempt_id=attempt.id).order_by(AttemptQuestion.id.asc()).all()
    questions_feedback = []
    
    for aq in attempt_questions:
        q = aq.question
        opts_mapping = {
            'A': q.option_a,
            'B': q.option_b,
            'C': q.option_c,
            'D': q.option_d
        }
        
        # Build options order matching student's display order
        ordered_options = []
        for letter in aq.option_order.split(','):
            ordered_options.append({
                'letter': letter,
                'text': opts_mapping[letter]
            })

        questions_feedback.append({
            'q_id': q.id,
            'text': q.question_text,
            'image': q.image_path,
            'bible_ref': q.bible_reference,
            'options': ordered_options,
            'selected': aq.selected_option,
            'correct_option': q.correct_option,
            'correct_text': opts_mapping[q.correct_option],
            'is_correct': aq.is_correct,
            'marks_obtained': aq.marks_obtained,
            'explanation': q.explanation
        })

    return render_template(
        'user/exam_result.html',
        attempt=attempt,
        exam=exam,
        feedback=questions_feedback
    )

# Static helper route to display uploaded files (like questions images and selfies)
@app.route('/uploads/selfies/<filename>')
def serve_selfie(filename):
    from flask import send_from_directory
    upload_dir = os.path.join(app.instance_path, 'uploads', 'selfies')
    return send_from_directory(upload_dir, filename)

@app.route('/uploads/questions/<filename>')
def serve_question_image(filename):
    from flask import send_from_directory
    upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'questions')
    return send_from_directory(upload_dir, filename)
