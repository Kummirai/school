import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
import json
from models import get_db_connection
from bs4 import BeautifulSoup

# Create a blueprint for exam-related routes
exam_bp = Blueprint('exam', __name__,
                    template_folder='templates', static_folder='static')

def load_exams_from_html():
    """Loads exam metadata from HTML files in the templates/exams directory."""
    exams = []
    exam_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'exams')
    if not os.path.exists(exam_dir):
        return []

    for filename in os.listdir(exam_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(exam_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                # Extract metadata from meta tags
                exam_data = {
                    'id': filename.replace('.html', ''),
                    'title': soup.find('meta', {'name': 'exam-title'})['content'] if soup.find('meta', {'name': 'exam-title'}) else 'Untitled Exam',
                    'grade': soup.find('meta', {'name': 'exam-grade'})['content'] if soup.find('meta', {'name': 'exam-grade'}) else 'N/A',
                    'subject': soup.find('meta', {'name': 'exam-subject'})['content'] if soup.find('meta', {'name': 'exam-subject'}) else 'N/A',
                    'description': soup.find('meta', {'name': 'exam-description'})['content'] if soup.find('meta', {'name': 'exam-description'}) else 'No description available.',
                    'questions_count': len(soup.find_all('div', {'class': 'question'})),
                    'duration_minutes': int(soup.find('meta', {'name': 'exam-duration'})['content']) if soup.find('meta', {'name': 'exam-duration'}) else 60,
                    'difficulty': soup.find('meta', {'name': 'exam-difficulty'})['content'] if soup.find('meta', {'name': 'exam-difficulty'}) else 'Medium',
                    'html_template': f'exams/{filename}'
                }
                exams.append(exam_data)
    return exams

@exam_bp.route('/exam_practice')
@login_required
def exam_practice():
    """Renders the exam practice page with categorized exams."""
    exams = load_exams_from_html()
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
    """Renders a specific exam from an HTML file."""
    exams = load_exams_from_html()
    selected_exam = next((exam for exam in exams if exam.get('id') == exam_id), None)

    if selected_exam and selected_exam.get('html_template'):
        return render_template(selected_exam['html_template'], exam=selected_exam)
    else:
        flash('Exam not found.', 'danger')
        return redirect(url_for('exam.exam_practice'))


@exam_bp.route('/submit_exam/<exam_id>', methods=['POST'])
@login_required
def submit_exam(exam_id):
    """Handles the submission of an HTML-based exam."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    exams = load_exams_from_html()
    selected_exam = next((exam for exam in exams if exam.get('id') == exam_id), None)

    if not selected_exam:
        flash('Exam not found.', 'danger')
        return redirect(url_for('exam.exam_practice'))

    user_answers = request.form
    
    exam_filepath = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', selected_exam['html_template'])
    with open(exam_filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    questions_html = soup.find_all('div', {'class': 'question'})
    total_questions = len(questions_html)
    correct_answers_count = 0
    
    # Prepare data for exam_results.html
    questions_for_review = []

    for i, question_html in enumerate(questions_html):
        question_id = f'question_{i+1}'
        question_text = str(question_html.find('p', class_='card-text')) if question_html.find('p', class_='card-text') else ''
        
        correct_answer_element = question_html.find('input', {'type': 'radio', 'correct': 'true'})
        correct_answer_value = correct_answer_element['value'] if correct_answer_element else 'N/A'
        
        user_submitted_answer = user_answers.get(question_id)

        if user_submitted_answer == correct_answer_value:
            correct_answers_count += 1

        questions_for_review.append({
            'id': question_id,
            'question_text': question_text,
            'correct_answer': correct_answer_value,
            'user_answer': user_submitted_answer
        })

    score = (correct_answers_count / total_questions) * 100 if total_questions > 0 else 0

    conn = get_db_connection()
    cur = conn.cursor()
    result_id = None
    try:
        cur.execute('''
            INSERT INTO exam_results (user_id, exam_id, score, total_questions, completion_time)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id;
        ''', (user_id, selected_exam['id'], score, total_questions))
        result_id = cur.fetchone()[0]
        conn.commit()
        flash('Exam submitted and graded successfully!', 'success')
        
        # Pass review data to the results page
        session['last_exam_review_data'] = {
            'exam_id': selected_exam['id'],
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
    cur = conn.cursor()
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
        return redirect(url_for('exam.exam_practice'))
    finally:
        cur.close()
        conn.close()

    if not result:
        flash('Exam result not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('exam.exam_practice'))

    # Unpack result data
    result_db_id, result_user_id, exam_id_from_db, score, total_questions, completion_time = result

    # Retrieve review data from session (set during submit_exam)
    review_data = session.pop('last_exam_review_data', None)
    
    exam_details = None
    questions_for_review = []

    if review_data and review_data['exam_id'] == exam_id_from_db:
        exam_details = next((exam for exam in load_exams_from_html() if exam.get('id') == exam_id_from_db), None)
        questions_for_review = review_data['questions_for_review']
    else:
        # Fallback: if session data is not available, try to reconstruct basic review
        # This is less ideal as it won't have user's specific answers
        exam_details = next((exam for exam in load_exams_from_html() if exam.get('id') == exam_id_from_db), None)
        if exam_details:
            exam_filepath = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', exam_details['html_template'])
            with open(exam_filepath, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            questions_html = soup.find_all('div', {'class': 'question'})
            for i, question_html in enumerate(questions_html):
                question_id = f'question_{i+1}'
                question_text = str(question_html.find('p', class_='card-text')) if question_html.find('p', class_='card-text') else ''
                correct_answer_element = question_html.find('input', {'type': 'radio', 'correct': 'true'})
                correct_answer_value = correct_answer_element['value'] if correct_answer_element else 'N/A'
                questions_for_review.append({
                    'id': question_id,
                    'question_text': question_text,
                    'correct_answer': correct_answer_value,
                    'user_answer': 'Not available (session expired)' # Indicate missing user answer
                })

    return render_template('exam_results.html',
                           result=result,
                           exam_details=exam_details,
                           questions_for_review=questions_for_review,
                           user_id=user_id)