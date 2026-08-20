import datetime
from pkg import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # 'super_admin', 'teacher', 'student'
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<Role {self.name}>"

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    profile_photo = db.Column(db.String(255), default='default-avatar.png')

    role = db.relationship('Role', backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class VbsYear(db.Model):
    __tablename__ = 'vbs_years'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, unique=True, nullable=False)
    theme = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    results_released = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<VbsYear {self.year}>"

class TeacherProfile(db.Model):
    __tablename__ = 'teacher_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref=db.backref('teacher_profile', uselist=False, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Teacher {self.first_name} {self.last_name}>"

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vbs_year_id = db.Column(db.Integer, db.ForeignKey('vbs_years.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher_profiles.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('class_categories.id'), nullable=True)
    # New: explicit age bounds and assessment method stored per class
    min_age = db.Column(db.Integer, nullable=True)
    max_age = db.Column(db.Integer, nullable=True)
    assessment_method = db.Column(db.String(20), nullable=True)  # 'manual', 'cbt', 'both'
    manual_grade_weight = db.Column(db.Float, default=50.0, nullable=False)
    cbt_grade_weight = db.Column(db.Float, default=50.0, nullable=False)
    age_group = db.Column(db.String(50))  # legacy field (kept for compatibility)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    vbs_year = db.relationship('VbsYear', backref=db.backref('classes', lazy=True))
    teacher = db.relationship('TeacherProfile', backref=db.backref('classes', lazy=True))
    category = db.relationship('ClassCategory', backref=db.backref('classes', lazy=True))

    def __repr__(self):
        return f"<Class {self.name}>"


# Association table: teachers can be assigned to multiple classes
teacher_classes = db.Table(
    'teacher_classes',
    db.Column('teacher_id', db.Integer, db.ForeignKey('teacher_profiles.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id'), primary_key=True)
)


class ClassCategory(db.Model):
    __tablename__ = 'class_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    min_age = db.Column(db.Integer, nullable=True)
    max_age = db.Column(db.Integer, nullable=True)
    assessment_method = db.Column(db.String(20), default='manual')  # 'manual', 'cbt', 'both'
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<ClassCategory {self.name}>"

class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=True)
    vbs_year_id = db.Column(db.Integer, db.ForeignKey('vbs_years.id'), nullable=False)
    parent_name = db.Column(db.String(150))
    parent_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref=db.backref('student_profile', uselist=False, cascade="all, delete-orphan"))
    class_ = db.relationship('Class', backref=db.backref('students', lazy=True))
    vbs_year = db.relationship('VbsYear', backref=db.backref('students', lazy=True))
    skill = db.relationship('Skill', backref=db.backref('students', lazy=True))

    def __repr__(self):
        return f"<Student {self.first_name} {self.last_name}>"

class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    vbs_year_id = db.Column(db.Integer, db.ForeignKey('vbs_years.id'), nullable=False)

    vbs_year = db.relationship('VbsYear', backref=db.backref('skills', lazy=True))

    def __repr__(self):
        return f"<Skill {self.name}>"

class SkillAssessment(db.Model):
    __tablename__ = 'skill_assessments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Assessment score
    comments = db.Column(db.Text)
    assessed_by = db.Column(db.Integer, db.ForeignKey('teacher_profiles.id'), nullable=False)
    assessed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    student = db.relationship('StudentProfile', backref=db.backref('skill_assessments', cascade="all, delete-orphan", lazy=True))
    skill = db.relationship('Skill', backref=db.backref('assessments', lazy=True))
    teacher = db.relationship('TeacherProfile', backref=db.backref('assessments', lazy=True))

    def __repr__(self):
        return f"<SkillAssessment Student:{self.student_id} Skill:{self.skill_id} Score:{self.score}>"

question_bank_classes = db.Table(
    'question_bank_classes',
    db.Column('question_bank_id', db.Integer, db.ForeignKey('question_banks.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id'), primary_key=True)
)

class QuestionBank(db.Model):
    __tablename__ = 'question_banks'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    class_ = db.relationship('Class', backref=db.backref('question_banks', lazy=True))
    skill = db.relationship('Skill', backref=db.backref('question_banks', lazy=True))
    assigned_classes = db.relationship(
        'Class',
        secondary=question_bank_classes,
        backref=db.backref('assigned_question_banks', lazy=True)
    )

    @property
    def all_class_ids(self):
        ids = {self.class_id}
        ids.update(c.id for c in self.assigned_classes)
        return ids

    def __repr__(self):
        return f"<QuestionBank {self.name}>"

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    question_bank_id = db.Column(db.Integer, db.ForeignKey('question_banks.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255))
    bible_reference = db.Column(db.String(255))
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default='medium')  # 'easy', 'medium', 'hard'
    marks = db.Column(db.Integer, default=1)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    question_bank = db.relationship('QuestionBank', backref=db.backref('questions', lazy=True))

    def __repr__(self):
        return f"<Question {self.id}>"


# Association table: exams can be assigned to multiple classes
exam_classes = db.Table(
    'exam_classes',
    db.Column('exam_id', db.Integer, db.ForeignKey('exams.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id'), primary_key=True)
)

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    vbs_year_id = db.Column(db.Integer, db.ForeignKey('vbs_years.id'), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    skill_question_count = db.Column(db.Integer, nullable=False, default=0)
    is_draft = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    class_ = db.relationship('Class', backref=db.backref('exams', lazy=True))
    vbs_year = db.relationship('VbsYear', backref=db.backref('exams', lazy=True))

    # Assigned classes via many-to-many mapping (keeps multi-class assignments)
    assigned_classes = db.relationship('Class', secondary=exam_classes, backref=db.backref('assigned_exams', lazy=True))

    def __repr__(self):
        return f"<Exam {self.title}>"

class ExamSection(db.Model):
    __tablename__ = 'exam_sections'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    # Primary bank kept for backwards compatibility; when multiple banks are used
    # the detailed per-bank rules are stored in ExamSectionBankRule
    question_bank_id = db.Column(db.Integer, db.ForeignKey('question_banks.id'), nullable=True)
    question_count = db.Column(db.Integer, nullable=False, default=5)
    difficulty_filter = db.Column(db.String(20), default='any')  # 'easy', 'medium', 'hard', 'any'

    exam = db.relationship('Exam', backref=db.backref('sections', cascade="all, delete-orphan", lazy=True))
    question_bank = db.relationship('QuestionBank', backref=db.backref('exam_sections', lazy=True))


class ExamSectionBankRule(db.Model):
    __tablename__ = 'exam_section_bank_rules'
    id = db.Column(db.Integer, primary_key=True)
    exam_section_id = db.Column(db.Integer, db.ForeignKey('exam_sections.id'), nullable=False)
    question_bank_id = db.Column(db.Integer, db.ForeignKey('question_banks.id'), nullable=False)
    question_count = db.Column(db.Integer, nullable=False, default=1)

    section = db.relationship('ExamSection', backref=db.backref('bank_rules', cascade='all, delete-orphan', lazy=True))
    question_bank = db.relationship('QuestionBank')

    def __repr__(self):
        return f"<ExamSection {self.title} (Exam {self.exam_id})>"

class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    end_time = db.Column(db.DateTime)
    is_submitted = db.Column(db.Boolean, default=False)
    score = db.Column(db.Float, default=0.0)
    selfie_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    student = db.relationship('StudentProfile', backref=db.backref('attempts', cascade="all, delete-orphan", lazy=True))
    exam = db.relationship('Exam', backref=db.backref('attempts', lazy=True))
    class_ = db.relationship('Class', backref=db.backref('attempts', lazy=True))

    def __repr__(self):
        return f"<ExamAttempt Student:{self.student_id} Exam:{self.exam_id}>"

class AttemptQuestion(db.Model):
    __tablename__ = 'attempt_questions'
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_option = db.Column(db.String(1))  # 'A', 'B', 'C', 'D' or None
    option_order = db.Column(db.String(50))  # e.g. "B,C,A,D" for display option ordering
    is_correct = db.Column(db.Boolean, default=False)
    marks_obtained = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    attempt = db.relationship('ExamAttempt', backref=db.backref('questions', cascade="all, delete-orphan", lazy=True))
    question = db.relationship('Question', backref=db.backref('attempts', lazy=True))

    def __repr__(self):
        return f"<AttemptQuestion Attempt:{self.attempt_id} Question:{self.question_id}>"

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    target_role = db.Column(db.String(50), default='all')  # 'all', 'teacher', 'student'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    author = db.relationship('User', backref=db.backref('announcements', lazy=True))

    def __repr__(self):
        return f"<Announcement {self.title}>"

class AdmissionWorkflow(db.Model):
    __tablename__ = 'admission_workflows'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<AdmissionWorkflow {self.name}>"

class AdmissionApplication(db.Model):
    __tablename__ = 'admission_applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    dob = db.Column(db.Date)
    status = db.Column(db.String(50), default='pending')  # pending, accepted, rejected
    workflow_id = db.Column(db.Integer, db.ForeignKey('admission_workflows.id'), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref=db.backref('admission_applications', lazy=True))
    workflow = db.relationship('AdmissionWorkflow', backref=db.backref('applications', lazy=True))

    def __repr__(self):
        return f"<AdmissionApplication {self.email} ({self.status})>"

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL for guest login failures
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

    def __repr__(self):
        return f"<AuditLog {self.action} at {self.timestamp}>"

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<SystemSetting {self.key}>"
