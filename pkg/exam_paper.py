import random

from pkg.models import ExamSection, Question, QuestionBank


def _section_sources(section):
    rules = getattr(section, 'bank_rules', None) or []
    if rules:
        return [(rule.question_bank_id, int(rule.question_count or 0), section.difficulty_filter) for rule in rules]
    return [(section.question_bank_id, int(section.question_count or 0), section.difficulty_filter)]


def exam_skill_options(exam):
    skill_map = {}
    for section in ExamSection.query.filter_by(exam_id=exam.id).all():
        for bank_id, _count, _difficulty in _section_sources(section):
            bank = QuestionBank.query.get(bank_id) if bank_id else None
            if bank and bank.skill_id:
                skill_map[bank.skill_id] = bank.skill.name if bank.skill else 'Skill'
    return skill_map


def _pool_for_bank(bank_id, difficulty, exclude_ids=None):
    query = Question.query.filter_by(question_bank_id=bank_id, is_archived=False)
    if difficulty and difficulty != 'any':
        query = query.filter_by(difficulty=difficulty)
    if exclude_ids:
        query = query.filter(~Question.id.in_(list(exclude_ids)))
    return query.all()


def build_exam_questions(exam, skill_id=None):
    """Build one mixed paper: normal questions plus skill questions or normal fallback.

    Skill registration is optional. The reserved skill slot is always filled so every
    student receives the same total number of questions. Skill source labels are not
    attached to the returned Question objects.
    """
    selected = []
    used_ids = set()
    common_bank_ids = set()
    skill_bank_ids_by_skill = {}

    for section in ExamSection.query.filter_by(exam_id=exam.id).all():
        for bank_id, count, difficulty in _section_sources(section):
            bank = QuestionBank.query.get(bank_id) if bank_id else None
            if not bank:
                continue
            if bank.skill_id:
                skill_bank_ids_by_skill.setdefault(bank.skill_id, set()).add(bank.id)
                continue
            common_bank_ids.add(bank.id)
            pool = _pool_for_bank(bank.id, difficulty, used_ids)
            picked = random.sample(pool, min(max(0, count), len(pool)))
            selected.extend(picked)
            used_ids.update(q.id for q in picked)

    skill_count = max(0, int(exam.skill_question_count or 0))
    if skill_count:
        skill_pool = []
        if skill_id and skill_id in skill_bank_ids_by_skill:
            skill_pool = Question.query.filter(
                Question.question_bank_id.in_(skill_bank_ids_by_skill[skill_id]),
                Question.is_archived == False,
            ).all()
            skill_pool = [q for q in skill_pool if q.id not in used_ids]

        picked_skill = random.sample(skill_pool, min(skill_count, len(skill_pool))) if skill_pool else []
        selected.extend(picked_skill)
        used_ids.update(q.id for q in picked_skill)

        remaining = skill_count - len(picked_skill)
        if remaining > 0 and common_bank_ids:
            fallback = Question.query.filter(
                Question.question_bank_id.in_(common_bank_ids),
                Question.is_archived == False,
            ).all()
            fallback = [q for q in fallback if q.id not in used_ids]
            selected.extend(random.sample(fallback, min(remaining, len(fallback))))

    random.shuffle(selected)
    return selected


def present_questions(questions):
    presented = []
    for question in questions:
        letters = ['A', 'B', 'C', 'D']
        random.shuffle(letters)
        values = {
            'A': question.option_a,
            'B': question.option_b,
            'C': question.option_c,
            'D': question.option_d,
        }
        presented.append({
            'aq_id': question.id,
            'q_id': question.id,
            'text': question.question_text,
            'image': question.image_path,
            'bible_ref': question.bible_reference,
            'options': [{'letter': letter, 'text': values[letter]} for letter in letters],
            'selected': None,
        })
    return presented
