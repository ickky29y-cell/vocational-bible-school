import datetime
import csv
import io
from flask import render_template, url_for, request, redirect, flash, session, Response
from sqlalchemy import func, text
from pkg import app, db
from flask_login import current_user
from pkg.utils import current_user_id
from pkg.models import User, Role, VbsYear, TeacherProfile, Class, StudentProfile, Skill, SkillAssessment, QuestionBank, Question, Exam, ExamSection, ExamAttempt, AttemptQuestion, Announcement, AuditLog, SystemSetting, AdmissionApplication, teacher_classes, ClassCategory
from pkg.utils import current_user_id, current_role_name
from pkg.forms import ClassCategoryForm

# Helper to write to audit log
def log_audit(user_id, action, details=None):
    try:
        ip = request.remote_addr
        log = AuditLog(user_id=user_id, action=action, ip_address=ip, details=details)
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

# Retained for compatibility with local verification helpers; production startup
# must never create schema, roles, or users automatically.
def initialize_and_seed():
    return None

# Authorization guard
def require_super_admin():
    # Prefer Flask-Login's current_user when available, fallback to legacy session keys
    try:
        if current_user and getattr(current_user, 'is_authenticated', False):
            return getattr(current_user.role, 'name', None) == 'super_admin'
    except Exception:
        pass
    if current_role_name() != 'super_admin':
        return False
    return True


# Admissions Management
@app.route('/super-admin/admissions/')
def super_admin_admissions():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    apps = AdmissionApplication.query.order_by(AdmissionApplication.created_at.desc()).all()
    return render_template('super_admin/admissions.html', applications=apps)


@app.route('/super-admin/admissions/view/<int:app_id>/', methods=['GET', 'POST'])
def super_admin_admission_view(app_id):
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    application = AdmissionApplication.query.get_or_404(app_id)

    if request.method == 'POST':
        action = request.form.get('action')
        note = (request.form.get('note') or '').strip()

        try:
            if action == 'accept':
                application.status = 'accepted'
                application.notes = note

                # Create linked user and student profile if needed
                if not application.user_id:
                    # Ensure unique username
                    base = application.email.split('@')[0]
                    username = base
                    counter = 1
                    while User.query.filter_by(username=username).first():
                        username = f"{base}{counter}"
                        counter += 1

                    role = Role.query.filter_by(name='student').first()
                    if not role:
                        role = Role(name='student', description='VBS Pupil')
                        db.session.add(role)
                        db.session.flush()

                    import secrets
                    pwd = secrets.token_urlsafe(10)
                    new_user = User(username=username, email=application.email, role_id=role.id)
                    new_user.set_password(pwd)
                    db.session.add(new_user)
                    db.session.flush()

                    # attach student profile
                    active_year = VbsYear.query.filter_by(is_active=True).first()
                    sp = StudentProfile(user_id=new_user.id, first_name=application.first_name, last_name=application.last_name, age=0, vbs_year_id=active_year.id if active_year else None)
                    db.session.add(sp)

                    application.user_id = new_user.id
                    flash(f"Admission accepted. Student account created (username: {new_user.username}, password: {pwd}).", 'feedback')
                else:
                    flash('Admission accepted and linked to existing user.', 'feedback')

            elif action == 'reject':
                application.status = 'rejected'
                application.notes = note
                flash('Admission application rejected.', 'info')

            db.session.commit()
            log_audit(current_user_id(), 'ADMISSION_UPDATE', f"Application {application.id} set to {application.status}")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating application: {str(e)}", 'errormsg')

        return redirect(url_for('super_admin_admissions'))

    return render_template('super_admin/admission_view.html', application=application)


@app.route('/super-admin/admissions/download/')
def super_admin_admissions_download():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    apps = AdmissionApplication.query.order_by(AdmissionApplication.created_at.desc()).all()
    # Simple CSV
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','First Name','Last Name','Email','Phone','Status','Submitted At'])
    for a in apps:
        writer.writerow([a.id, a.first_name, a.last_name, a.email, a.phone, a.status, a.created_at.isoformat()])

    return Response(output.getvalue(), mimetype='text/csv', headers={"Content-Disposition":"attachment; filename=admissions.csv"})

# Super Admin Dashboard
@app.route('/super-admin/dashboard/')
def super_admin_dashboard():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()

    # Metrics
    total_years = VbsYear.query.count()
    total_teachers = TeacherProfile.query.count()
    
    total_classes = 0
    total_students = 0
    avg_score = 0.0

    if active_year:
        total_classes = Class.query.filter_by(vbs_year_id=active_year.id).count()
        total_students = StudentProfile.query.filter_by(vbs_year_id=active_year.id).count()
        
        # Calculate average CBT score
        scores = db.session.query(func.avg(ExamAttempt.score)).join(StudentProfile).filter(
            StudentProfile.vbs_year_id == active_year.id,
            ExamAttempt.is_submitted == True
        ).scalar()
        if scores is not None:
            avg_score = round(float(scores), 2)

    # Load recent audit logs
    recent_audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    # announcements list
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()

    return render_template(
        'super_admin/dashboard.html',
        active_year=active_year,
        total_years=total_years,
        total_teachers=total_teachers,
        total_classes=total_classes,
        total_students=total_students,
        avg_score=avg_score,
        recent_audits=recent_audits,
        announcements=announcements
    )

# Post Announcement endpoint
@app.route('/super-admin/announcements/add/', methods=['POST'])
def super_admin_add_announcement():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    title = (request.form.get('title') or '').strip()
    content = (request.form.get('content') or '').strip()
    target = request.form.get('target_role', 'all')

    if not title or not content:
        flash('All fields are compulsory.', 'errormsg')
        return redirect(url_for('super_admin_dashboard'))

    try:
        ann = Announcement(
            title=title,
            content=content,
            target_role=target,
            user_id=current_user_id()
        )
        db.session.add(ann)
        db.session.commit()
        log_audit(current_user_id(), "POST_ANNOUNCEMENT", f"Posted announcement: {title}")
        flash('Announcement posted!', 'feedback')
    except Exception as e:
        db.session.rollback()
        flash(f"Error posting announcement: {str(e)}", 'errormsg')

    return redirect(url_for('super_admin_dashboard'))

# VBS Years Dashboard
@app.route('/super-admin/years/', methods=['GET', 'POST'])
def super_admin_years():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    years = VbsYear.query.order_by(VbsYear.year.desc()).all()

    if request.method == 'POST':
        year_val_str = request.form.get('year')
        theme = (request.form.get('theme') or '').strip()

        if not year_val_str or not theme:
            flash('Compulsory parameters missing.', 'errormsg')
            return redirect(url_for('super_admin_years'))

        year_val = int(year_val_str)
        # Check existing VBS year
        if VbsYear.query.filter_by(year=year_val).first():
            flash('VBS Year already exists.', 'errormsg')
            return redirect(url_for('super_admin_years'))

        try:
            new_yr = VbsYear(year=year_val, theme=theme, is_active=False)
            db.session.add(new_yr)
            db.session.commit()
            
            log_audit(current_user_id(), "CREATE_VBS_YEAR", f"Created year {year_val} (Theme: {theme})")
            flash('VBS Year created successfully!', 'feedback')
            return redirect(url_for('super_admin_years'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating year: {str(e)}", 'errormsg')
            return redirect(url_for('super_admin_years'))

    return render_template('super_admin/years.html', years=years)

# Activate VBS Year
@app.route('/super-admin/years/activate/<int:year_id>/', methods=['POST'])
def super_admin_year_activate(year_id):
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    yr = VbsYear.query.get_or_404(year_id)
    try:
        # Deactivate all
        VbsYear.query.update({VbsYear.is_active: False})
        yr.is_active = True
        db.session.commit()
        log_audit(current_user_id(), "ACTIVATE_VBS_YEAR", f"Activated VBS Year: {yr.year}")
        flash(f"VBS Year {yr.year} theme is now live!", 'feedback')
    except Exception as e:
        db.session.rollback()
        flash(f"Error activating year: {str(e)}", 'errormsg')

    return redirect(url_for('super_admin_years'))

# Toggle Results Release Flag
@app.route('/super-admin/years/release/<int:year_id>/', methods=['POST'])
def super_admin_year_toggle_results(year_id):
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    yr = VbsYear.query.get_or_404(year_id)
    yr.results_released = not yr.results_released
    try:
        db.session.commit()
        status = "released" if yr.results_released else "locked"
        log_audit(current_user_id(), "TOGGLE_RESULTS_RELEASE", f"VBS Year {yr.year} results {status}")
        flash(f"Exam results are now {status} for student access.", 'feedback')
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating results status: {str(e)}", 'errormsg')

    return redirect(url_for('super_admin_years'))

# Teacher Management & Class Assignments
@app.route('/super-admin/teachers/', methods=['GET', 'POST'])
def super_admin_teachers():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    teachers = TeacherProfile.query.all()

    classes = []
    if active_year:
        classes = Class.query.filter_by(vbs_year_id=active_year.id).all()

    # Build a mapping of teacher_id -> all classes (primary + assigned) for display
    from pkg.utils import get_teacher_classes
    teacher_classes_map = {}
    for t in teachers:
        teacher_classes_map[t.id] = get_teacher_classes(t.id, active_year.id if active_year else None)
    if request.method == 'POST':
        first_name = (request.form.get('first_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = (request.form.get('password') or '').strip()
        confirm = (request.form.get('confirm_password') or '').strip()

        if not all([first_name, last_name, username, email, password]):
            flash('All compulsory fields must be completed.', 'errormsg')
            return redirect(url_for('super_admin_teachers'))

        if password != confirm:
            flash('Passwords do not match.', 'errormsg')
            return redirect(url_for('super_admin_teachers'))

        # Check existing
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already exists.', 'errormsg')
            return redirect(url_for('super_admin_teachers'))

        try:
            role = Role.query.filter_by(name='teacher').first()
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role_id=role.id
            )
            db.session.add(user)
            db.session.flush()

            profile = TeacherProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )
            db.session.add(profile)
            db.session.commit()
            
            log_audit(current_user_id(), "CREATE_TEACHER", f"Created teacher account: {first_name} {last_name}")
            flash('Teacher account created successfully!', 'feedback')
            return redirect(url_for('super_admin_teachers'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating teacher: {str(e)}", 'errormsg')
            return redirect(url_for('super_admin_teachers'))

    return render_template('super_admin/teachers.html', teachers=teachers, classes=classes, teacher_classes_map=teacher_classes_map)


@app.route('/super-admin/view-as/<int:teacher_id>/')
def super_admin_view_as_teacher(teacher_id):
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    # ensure teacher exists
    tp = TeacherProfile.query.get(teacher_id)
    if not tp:
        flash('Teacher not found.', 'errormsg')
        return redirect(url_for('super_admin_teachers'))

    # set impersonation session flag
    session['view_as_teacher'] = tp.id
    log_audit(current_user_id(), 'VIEW_AS_TEACHER', f"Now viewing as teacher: {tp.id} {tp.first_name} {tp.last_name}")
    flash(f'Now viewing as teacher: {tp.first_name} {tp.last_name}', 'feedback')
    return redirect(url_for('teacher_dashboard'))


@app.route('/super-admin/exit-view-as/')
def super_admin_exit_view_as():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))
    session.pop('view_as_teacher', None)
    log_audit(current_user_id(), 'EXIT_VIEW_AS', 'Exited teacher view-as mode')
    flash('Exited teacher view mode.', 'feedback')
    return redirect(url_for('super_admin_teachers'))


@app.route('/super-admin/categories/')
def super_admin_categories():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    categories = ClassCategory.query.order_by(ClassCategory.name).all()
    form = ClassCategoryForm()
    return render_template('super_admin/class_categories.html', categories=categories, form=form)


@app.route('/super-admin/categories/create/', methods=['POST'])
def super_admin_category_create():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    form = ClassCategoryForm()
    if form.validate_on_submit():
        try:
            cat = ClassCategory(
                name=form.name.data.strip(),
                min_age=form.min_age.data,
                max_age=form.max_age.data,
                assessment_method=form.assessment_method.data or 'manual',
                description=form.description.data
            )
            db.session.add(cat)
            db.session.commit()
            log_audit(current_user_id(), 'CREATE_CATEGORY', f"Created category {cat.name}")
            flash('Category created.', 'feedback')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating category: {str(e)}', 'errormsg')
    else:
        flash('Invalid input for category.', 'errormsg')

    return redirect(url_for('super_admin_categories'))


@app.route('/super-admin/categories/edit/<int:cat_id>/', methods=['GET', 'POST'])
def super_admin_category_edit(cat_id):
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    cat = ClassCategory.query.get_or_404(cat_id)
    form = ClassCategoryForm(obj=cat)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                cat.name = form.name.data.strip()
                cat.min_age = form.min_age.data
                cat.max_age = form.max_age.data
                cat.assessment_method = form.assessment_method.data or 'manual'
                cat.description = form.description.data
                db.session.commit()
                log_audit(current_user_id(), 'EDIT_CATEGORY', f"Edited category {cat.name}")
                flash('Category updated.', 'feedback')
                return redirect(url_for('super_admin_categories'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating category: {str(e)}', 'errormsg')
        else:
            flash('Invalid input.', 'errormsg')

    return render_template('super_admin/class_category_edit.html', form=form, category=cat)


@app.route('/super-admin/categories/delete/<int:cat_id>/', methods=['POST'])
def super_admin_category_delete(cat_id):
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    cat = ClassCategory.query.get_or_404(cat_id)
    try:
        db.session.delete(cat)
        db.session.commit()
        log_audit(current_user_id(), 'DELETE_CATEGORY', f"Deleted category {cat.name}")
        flash('Category deleted.', 'feedback')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'errormsg')

    return redirect(url_for('super_admin_categories'))

# Class assignments & creation
@app.route('/super-admin/class-assignment/', methods=['POST'])
def super_admin_class_assignment():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not active_year:
        flash('No active VBS Year. Please activate a year first.', 'errormsg')
        return redirect(url_for('super_admin_teachers'))

    action = request.form.get('action')

    if action == 'create_class':
        name = (request.form.get('class_name') or '').strip()
        primary_teacher_id_str = request.form.get('primary_teacher_id')
        # legacy single-select fallback
        legacy_teacher_id_str = request.form.get('teacher_id')
        category_id_str = request.form.get('category_id')
        min_age_str = request.form.get('min_age')
        max_age_str = request.form.get('max_age')
        assessment_method = request.form.get('assessment_method')

        if not name:
            flash('Class name is required.', 'errormsg')
            return redirect(url_for('super_admin_teachers'))

        teacher_id = None
        if primary_teacher_id_str:
            try:
                teacher_id = int(primary_teacher_id_str)
            except Exception:
                teacher_id = None
        elif legacy_teacher_id_str:
            try:
                teacher_id = int(legacy_teacher_id_str)
            except Exception:
                teacher_id = None
        category_id = int(category_id_str) if category_id_str else None
        try:
            if min_age_str and max_age_str:
                try:
                    if int(min_age_str) > int(max_age_str):
                        flash('Minimum age cannot be greater than maximum age.', 'errormsg')
                        return redirect(url_for('super_admin_teachers'))
                except ValueError:
                    flash('Ages must be valid integers.', 'errormsg')
                    return redirect(url_for('super_admin_teachers'))

            # sanitize assessment method
            if assessment_method not in ('manual', 'cbt', 'both'):
                assessment_method = None

            cls = Class(
                name=name,
                vbs_year_id=active_year.id,
                teacher_id=teacher_id,
                category_id=category_id,
                min_age=int(min_age_str) if min_age_str else None,
                max_age=int(max_age_str) if max_age_str else None,
                assessment_method=assessment_method or None
            )
            db.session.add(cls)
            db.session.commit()
            
            # If multiple instructors were selected, link them (new field name: teacher_ids)
            selected_teachers = request.form.getlist('teacher_ids')
            # ensure primary teacher is included in associations
            if teacher_id and str(teacher_id) not in selected_teachers:
                selected_teachers.insert(0, str(teacher_id))

            for tstr in selected_teachers:
                try:
                    tid = int(tstr)
                    try:
                        db.session.execute(teacher_classes.insert().values(teacher_id=tid, class_id=cls.id))
                    except Exception:
                        pass
                except Exception:
                    continue

            log_audit(current_user_id(), "CREATE_CLASS", f"Created Class: {name}")
            flash('VBS Class created successfully!', 'feedback')
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating class: {str(e)}", 'errormsg')

    elif action == 'assign_teacher':
        class_id_str = request.form.get('class_id')
        teacher_id_str = request.form.get('teacher_id')

        if not class_id_str or not teacher_id_str:
            flash('Parameters missing.', 'errormsg')
            return redirect(url_for('super_admin_teachers'))

        cls = Class.query.get(int(class_id_str))
        if cls:
            try:
                tid = int(teacher_id_str)
                # set primary teacher if not set
                # keep primary teacher if not set
                if not cls.teacher_id:
                    cls.teacher_id = tid
                # add association entry (allow multiple teachers)
                try:
                    db.session.execute(teacher_classes.insert().values(teacher_id=tid, class_id=cls.id))
                except Exception:
                    pass
                db.session.commit()
                teacher_profile = TeacherProfile.query.get(tid)
                log_audit(current_user_id(), "ASSIGN_TEACHER_TO_CLASS", f"Assigned teacher {teacher_profile.first_name} to class {cls.name}")
                flash(f"Teacher assigned to class {cls.name}.", 'feedback')
            except Exception as e:
                db.session.rollback()
                flash(f"Error assigning teacher: {str(e)}", 'errormsg')

    return redirect(url_for('super_admin_teachers'))
    
    return


# Edit an existing class
@app.route('/super-admin/class-edit/<int:class_id>/', methods=['GET', 'POST'])
def super_admin_class_edit(class_id):
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    cls = Class.query.get_or_404(class_id)
    active_year = VbsYear.query.filter_by(is_active=True).first()
    categories = ClassCategory.query.order_by(ClassCategory.name).all()
    teachers = TeacherProfile.query.all()
    # assigned teacher profiles for this class
    try:
        assigned_teachers = TeacherProfile.query.join(teacher_classes, TeacherProfile.id == teacher_classes.c.teacher_id).filter(teacher_classes.c.class_id == cls.id).all()
    except Exception:
        assigned_teachers = []

    if request.method == 'POST':
        name = (request.form.get('class_name') or '').strip()
        primary_teacher_id_str = request.form.get('primary_teacher_id')
        category_id_str = request.form.get('category_id')
        min_age_str = request.form.get('min_age')
        max_age_str = request.form.get('max_age')
        assessment_method = request.form.get('assessment_method')

        if not name:
            flash('Class name is required.', 'errormsg')
            return redirect(url_for('super_admin_class_edit', class_id=class_id))

        try:
            cls.name = name
            cls.category_id = int(category_id_str) if category_id_str else None
            cls.min_age = int(min_age_str) if min_age_str else None
            cls.max_age = int(max_age_str) if max_age_str else None
            cls.assessment_method = assessment_method if assessment_method in ('manual','cbt','both') else None

            # primary teacher
            if primary_teacher_id_str:
                try:
                    cls.teacher_id = int(primary_teacher_id_str)
                except Exception:
                    cls.teacher_id = None

            db.session.commit()

            # update associations: replace teacher_classes entries for this class with selected teacher_ids
            selected_teachers = request.form.getlist('teacher_ids')
            # ensure primary included
            if cls.teacher_id and str(cls.teacher_id) not in selected_teachers:
                selected_teachers.insert(0, str(cls.teacher_id))

            # delete existing associations for this class
            try:
                db.session.execute(teacher_classes.delete().where(teacher_classes.c.class_id == cls.id))
                db.session.commit()
            except Exception:
                db.session.rollback()

            for tstr in selected_teachers:
                try:
                    tid = int(tstr)
                    try:
                        db.session.execute(teacher_classes.insert().values(teacher_id=tid, class_id=cls.id))
                    except Exception:
                        pass
                except Exception:
                    continue
            db.session.commit()

            log_audit(current_user_id(), 'EDIT_CLASS', f'Edited class {cls.id} {cls.name}')
            flash('Class updated successfully.', 'feedback')
            return redirect(url_for('super_admin_teachers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating class: {str(e)}', 'errormsg')
            return redirect(url_for('super_admin_class_edit', class_id=class_id))

    return render_template('super_admin/class_edit.html', cls=cls, categories=categories, teachers=teachers, active_year=active_year, assigned_teachers=assigned_teachers)
# Reports & Ranking Board
@app.route('/super-admin/reports/')
def super_admin_reports():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not active_year:
        flash('No active VBS Year. Archive sheets not available.', 'errormsg')
        return redirect(url_for('super_admin_dashboard'))

    # Load ranking list: students ordered by exam attempt score or manual grade averages
    # For CBT
    cbt_rankings = ExamAttempt.query.join(StudentProfile).filter(
        StudentProfile.vbs_year_id == active_year.id,
        ExamAttempt.is_submitted == True
    ).order_by(ExamAttempt.score.desc()).all()

    # For manual assessments: aggregate score averages by student
    manual_rankings = db.session.query(
        StudentProfile,
        func.avg(SkillAssessment.score).label('avg_score')
    ).join(SkillAssessment, StudentProfile.id == SkillAssessment.student_id).filter(
        StudentProfile.vbs_year_id == active_year.id
    ).group_by(StudentProfile.id).order_by(text('avg_score DESC')).all()

    # Class summaries: include per-class totals and averages
    classes = Class.query.filter_by(vbs_year_id=active_year.id).order_by(Class.name).all()
    class_summaries = []
    for cls in classes:
        stu_count = StudentProfile.query.filter_by(class_id=cls.id, vbs_year_id=active_year.id).count()
        cbt_avg = db.session.query(func.avg(ExamAttempt.score)).join(StudentProfile).filter(
            StudentProfile.class_id == cls.id,
            StudentProfile.vbs_year_id == active_year.id,
            ExamAttempt.is_submitted == True
        ).scalar()
        if cbt_avg is not None:
            cbt_avg = round(float(cbt_avg), 2)

        manual_avg = db.session.query(func.avg(SkillAssessment.score)).join(StudentProfile).filter(
            StudentProfile.class_id == cls.id,
            StudentProfile.vbs_year_id == active_year.id
        ).scalar()
        if manual_avg is not None:
            manual_avg = round(float(manual_avg), 2)

        class_summaries.append({
            'id': cls.id,
            'name': cls.name,
            'student_count': stu_count,
            'cbt_avg': cbt_avg,
            'manual_avg': manual_avg
        })

    # Under-6 dedicated section (but students remain counted in class totals)
    under6_students = StudentProfile.query.filter(
        StudentProfile.vbs_year_id == active_year.id,
        StudentProfile.age < 6
    ).order_by(StudentProfile.class_id, StudentProfile.last_name).all()

    return render_template('super_admin/reports.html', cbt_rankings=cbt_rankings, manual_rankings=manual_rankings, class_summaries=class_summaries, under6_students=under6_students)

# Download CSV Reports
@app.route('/super-admin/reports/download/')
def super_admin_reports_download():
    if not require_super_admin():
        return "Unauthorized", 403

    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not active_year:
        return "No active year", 404

    # Generate CSV of all students and their scores
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Age', 'Gender', 'Class Name', 'Evaluation Mode', 'CBT Attempt Score', 'Manual Skills Score Avg', 'Registration Date'])

    # Allow class-specific or under-6 exports via query params
    class_id = request.args.get('class_id')
    under6 = request.args.get('under6')

    qs = StudentProfile.query.filter_by(vbs_year_id=active_year.id)
    if class_id:
        try:
            cid = int(class_id)
            qs = qs.filter_by(class_id=cid)
        except Exception:
            pass
    if under6 and under6.lower() in ('1','true','yes'):
        qs = qs.filter(StudentProfile.age < 6)

    students = qs.all()
    for s in students:
        cbt_score = "N/A"
        manual_avg = "N/A"
        mode = "CBT (6+ Years)"

        cls = Class.query.get(s.class_id) if s.class_id else None
        if cls:
            effective_method = cls.assessment_method or (cls.category.assessment_method if cls.category else None)
            if effective_method == 'manual':
                mode = f"Manual ({cls.name})"
                # fetch manual average
                avg = db.session.query(func.avg(SkillAssessment.score)).filter_by(student_id=s.id).scalar()
                if avg is not None:
                    manual_avg = round(float(avg), 2)
        else:
            # fetch cbt score
            attempt = ExamAttempt.query.filter_by(student_id=s.id, is_submitted=True).order_by(ExamAttempt.score.desc()).first()
            if attempt:
                cbt_score = attempt.score

        writer.writerow([
            f"{s.first_name} {s.last_name}",
            s.age,
            s.gender,
            cls.name if cls else 'Unassigned',
            mode,
            cbt_score,
            manual_avg,
            s.created_at.strftime('%Y-%m-%d')
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=vbs_{active_year.year}_scorecard_reports.csv"}
    )


@app.route('/super-admin/reports/print/')
def super_admin_reports_print():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    active_year = VbsYear.query.filter_by(is_active=True).first()
    if not active_year:
        flash('No active VBS Year. Archive sheets not available.', 'errormsg')
        return redirect(url_for('super_admin_dashboard'))

    class_id = request.args.get('class_id')
    under6 = request.args.get('under6')

    qs = StudentProfile.query.filter_by(vbs_year_id=active_year.id)
    title = f"VBS {active_year.year} Score Report"
    if class_id:
        try:
            cid = int(class_id)
            cls = Class.query.get(cid)
            if cls:
                title = f"Class Report: {cls.name} - VBS {active_year.year}"
            qs = qs.filter_by(class_id=cid)
        except Exception:
            pass
    if under6 and under6.lower() in ('1','true','yes'):
        title = f"Under-6 Report - VBS {active_year.year}"
        qs = qs.filter(StudentProfile.age < 6)

    students = qs.order_by(StudentProfile.class_id, StudentProfile.last_name).all()
    return render_template('super_admin/reports_print.html', students=students, title=title, active_year=active_year)

# Audit Trail log viewer
@app.route('/super-admin/audit-logs/')
def super_admin_audit_logs():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('super_admin/audit_logs.html', logs=logs)

# System Settings configuration
@app.route('/super-admin/settings/', methods=['GET', 'POST'])
def super_admin_settings():
    if not require_super_admin():
        flash('Access Denied', 'errormsg')
        return redirect(url_for('user_login'))

    settings = SystemSetting.query.all()
    settings_dict = {s.key: s for s in settings}

    if not settings:
        # Prepopulate
        defaults = [
            ("church_name", "Grace Bible Church", "The name of the administering Church"),
            ("accent_color", "#5c67f2", "Accent theme hex code"),
            ("system_rules", "Welcome to VBS Examinations! Please answer honestly.", "Default instructions for examinations")
        ]
        for k, v, d in defaults:
            s = SystemSetting(key=k, value=v, description=d)
            db.session.add(s)
        db.session.commit()
        settings = SystemSetting.query.all()
        settings_dict = {s.key: s for s in settings}

    if request.method == 'POST':
        for key in settings_dict:
            new_val = request.form.get(key)
            if new_val is not None:
                settings_dict[key].value = new_val.strip()
        try:
            db.session.commit()
            log_audit(current_user_id(), "UPDATE_SETTINGS", "Updated system configurations")
            flash('System settings updated successfully.', 'feedback')
            return redirect(url_for('super_admin_settings'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving settings: {str(e)}", 'errormsg')

    return render_template('super_admin/settings.html', settings=settings)
