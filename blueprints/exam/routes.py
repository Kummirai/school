import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
import psycopg2.extras
from models import get_db_connection

# Create a blueprint for exam-related routes
exam_bp = Blueprint('exam', __name__,
                    template_folder='templates', static_folder='static')

def get_exams_from_db():
    """Fetches exam metadata from the questions table in the database."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Query for distinct exams
    cur.execute("""
        SELECT DISTINCT grade, subject, year, month
        FROM questions
        ORDER BY grade, subject, year, month
    """)
    distinct_exams = cur.fetchall()
    
    exams = []
    for exam_meta in distinct_exams:
        grade = exam_meta['grade']
        subject = exam_meta['subject']
        year = exam_meta['year']
        month = exam_meta['month']
        
        # Count questions for this exam
        cur.execute("SELECT COUNT(id) FROM questions WHERE grade = %s AND subject = %s AND year = %s AND month = %s", (grade, subject, year, month))
        questions_count = cur.fetchone()[0]
        
        exam_id = f"{grade}|{subject}|{year}|{month}"
        
        exam_data = {
            'id': exam_id,
            'title': f"{subject} - {month} {year}",
            'grade': str(grade),
            'subject': subject,
            'description': f"A practice exam for Grade {grade} {subject} from {month} {year}.",
            'questions_count': questions_count,
            'duration_minutes': 60,  # Default value
            'difficulty': 'Medium', # Default value
        }
        exams.append(exam_data)
        
    cur.close()
    conn.close()
    return exams

@exam_bp.route('/exam_practice')
@login_required
def exam_practice():
    """Renders the exam practice page with categorized exams and user's results."""
    user_id = session.get('user_id')
    exams = get_exams_from_db()
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Fetch all results for the current user
    cur.execute("SELECT * FROM exam_results WHERE user_id = %s", (user_id,))
    results = cur.fetchall()
    
    # Create a dictionary for easy lookup of results by exam_id
    results_map = {}
    for result in results:
        exam_id = result['exam_id']
        if exam_id not in results_map:
            results_map[exam_id] = []
        results_map[exam_id].append(result)
    
    # Enhance exam data with latest score and attempts
    for exam in exams:
        exam_id = exam['id']
        if exam_id in results_map:
            # Sort results by completion time to find the latest
            latest_result = sorted(results_map[exam_id], key=lambda r: r['completion_time'], reverse=True)[0]
            exam['latest_score'] = float(latest_result['score'])
            exam['attempts'] = len(results_map[exam_id])
        else:
            exam['latest_score'] = None
            exam['attempts'] = 0

    cur.close()
    conn.close()

    # Categorize exams for display
    categorized_exams = {}
    for exam in exams:
        grade = exam.get('grade')
        subject = exam.get('subject')
        if grade and subject:
            if grade not in categorized_exams:
                categorized_exams[grade] = {}
            if subject not in categorized_exams[grade]:
                categorized_exams[grade][subject] = []
            categorized_exams[grade][subject].append(exam)

    # Sort grades and subjects for ordered display
    try:
        sorted_grades = sorted(categorized_exams.keys(), key=lambda g: int(g))
    except (ValueError, TypeError):
        sorted_grades = sorted(categorized_exams.keys())

    sorted_categorized_exams = {grade: categorized_exams[grade] for grade in sorted_grades}

    for grade in sorted_categorized_exams:
        sorted_subjects = sorted(sorted_categorized_exams[grade].keys())
        sorted_categorized_exams[grade] = {subject: sorted_categorized_exams[grade][subject] for subject in sorted_subjects}

    return render_template('exam_practice.html', categorized_exams=sorted_categorized_exams)


@exam_bp.route('/exam/<exam_id>')
@login_required
def take_exam(exam_id):
    """Renders a specific exam by fetching questions from the database."""
    try:
        grade, subject, year, month = exam_id.split('|')
    except ValueError:
        flash('Invalid exam identifier.', 'danger')
        return redirect(url_for('exam.exam_practice'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        "SELECT * FROM questions WHERE grade = %s AND subject = %s AND year = %s AND month = %s ORDER BY section, number",
        (grade, subject, year, month)
    )
    questions = cur.fetchall()
    cur.close()
    conn.close()

    if not questions:
        flash('Exam not found or has no questions.', 'danger')
        return redirect(url_for('exam.exam_practice'))

    exam_details = {
        'id': exam_id,
        'title': f"{subject} - {month} {year}",
        'grade': grade,
        'subject': subject,
        'year': year,
        'month': month,
        'duration_minutes': 60 # Default
    }
    
    processed_questions = []
    for q in questions:
        new_q = dict(q)
        if new_q.get('options'):
            try:
                new_q['options'] = json.loads(new_q['options'])
            except (json.JSONDecodeError, TypeError):
                new_q['options'] = []
        processed_questions.append(new_q)

    return render_template('take_exam.html', exam=exam_details, questions=processed_questions)


@exam_bp.route('/submit_exam/<exam_id>', methods=['POST'])
@login_required
def submit_exam(exam_id):
    """Handles the submission of a database-driven exam."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    try:
        grade, subject, year, month = exam_id.split('|')
    except ValueError:
        flash('Invalid exam identifier.', 'danger')
        return redirect(url_for('exam.exam_practice'))

    user_answers = request.form

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        "SELECT id, number, type, answer, question_text, options FROM questions WHERE grade = %s AND subject = %s AND year = %s AND month = %s",
        (grade, subject, year, month)
    )
    db_questions = cur.fetchall()
    
    if not db_questions:
        flash('Exam questions not found.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('exam.exam_practice'))

    total_questions = len(db_questions)
    correct_answers_count = 0
    questions_for_review = []

    for question in db_questions:
        question_id = str(question['id'])
        question_type = question['type']
        correct_answer = question['answer']
        options = json.loads(question['options']) if question.get('options') and question['options'] else {}

        user_submitted_answer = None
        if question_type == 'matching':
            matching_answers = {}
            stems = options.get('stems', [])
            for i, stem in enumerate(stems, 1):
                answer_key = f'question_{question_id}_{i}'
                matching_answers[stem] = user_answers.get(answer_key)
            user_submitted_answer = json.dumps(matching_answers, sort_keys=True)
            
            try:
                correct_answer_dict = json.loads(correct_answer)
                correct_answer = json.dumps(correct_answer_dict, sort_keys=True)
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            user_submitted_answer = user_answers.get(f'question_{question_id}')

        is_correct = user_submitted_answer == correct_answer
        if is_correct:
            correct_answers_count += 1

        questions_for_review.append({
            'id': question_id,
            'number': question['number'],
            'type': question_type,
            'question_text': question['question_text'],
            'options': options,
            'correct_answer': correct_answer,
            'user_answer': user_submitted_answer,
            'is_correct': is_correct
        })

    score = (correct_answers_count / total_questions) * 100 if total_questions > 0 else 0

    result_id = None
    try:
        cur.execute('''
            INSERT INTO exam_results (user_id, exam_id, score, total_questions, completion_time)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id;
        ''', (user_id, exam_id, score, total_questions))
        result_id = cur.fetchone()[0]
        conn.commit()
        flash('Exam submitted and graded successfully!', 'success')
        
        session['last_exam_review_data'] = {
            'exam_id': exam_id,
            'score': score,
            'total_questions': total_questions,
            'correct_answers_count': correct_answers_count,
            'questions_for_review': questions_for_review
        }
        
        return redirect(url_for('exam.exam_results', result_id=result_id))
    except Exception as e:
        conn.rollback()
        print(f"Error processing exam submission: {e}")
        flash('Error processing exam submission.', 'danger')
        return redirect(url_for('exam.exam_practice'))
    finally:
        cur.close()
        conn.close()

@exam_bp.route('/exam_results/<int:result_id>')
@login_required
def exam_results(result_id):
    """Fetches and displays the results of a completed exam, including review data."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    result = None
    try:
        cur.execute('''
            SELECT id, user_id, exam_id, score, total_questions, completion_time
            FROM exam_results
            WHERE id = %s AND user_id = %s;
        ''', (result_id, user_id))
        result = cur.fetchone()
    except Exception as e:
        print(f"Error fetching exam result {result_id}: {e}")
        flash('Error fetching exam results.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('exam.exam_practice'))

    if not result:
        flash('Exam result not found or you do not have permission to view it.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('exam.exam_practice'))

    exam_id_from_db = result['exam_id']
    review_data = session.pop('last_exam_review_data', None)
    
    exam_details = None
    questions_for_review = []

    try:
        grade, subject, year, month = exam_id_from_db.split('|')
        exam_details = {
            'id': exam_id_from_db,
            'title': f"{subject} - {month} {year}",
            'grade': grade,
            'subject': subject,
            'year': year,
            'month': month
        }
    except (ValueError, IndexError):
        flash('Invalid exam identifier found in results.', 'danger')

    if review_data and review_data['exam_id'] == exam_id_from_db:
        questions_for_review = review_data['questions_for_review']
        for q in questions_for_review:
            if q.get('type') == 'matching':
                if isinstance(q.get('user_answer'), str):
                    try:
                        q['user_answer'] = json.loads(q['user_answer'])
                    except (json.JSONDecodeError, TypeError):
                        q['user_answer'] = {}
                if isinstance(q.get('correct_answer'), str):
                    try:
                        q['correct_answer'] = json.loads(q['correct_answer'])
                    except (json.JSONDecodeError, TypeError):
                        q['correct_answer'] = {}
    else:
        if exam_details:
            cur.execute(
                "SELECT id, number, type, question_text, answer, options FROM questions WHERE grade = %s AND subject = %s AND year = %s AND month = %s",
                (grade, subject, year, month)
            )
            db_questions = cur.fetchall()
            for q in db_questions:
                questions_for_review.append({
                    'id': q['id'],
                    'number': q['number'],
                    'type': q['type'],
                    'question_text': q['question_text'],
                    'options': json.loads(q['options']) if q.get('options') and q['options'] else {},
                    'correct_answer': q['answer'],
                    'user_answer': 'Not available (session expired)',
                    'is_correct': False
                })

    cur.close()
    conn.close()

    return render_template('exam_results.html',
                           result=result,
                           exam_details=exam_details,
                           questions_for_review=questions_for_review,
                           user_id=user_id)
