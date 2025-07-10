from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
import json
from models import get_db_connection
from flask import current_app as app  # Assuming this utility function exists
from helpers import load_exams_from_json

# Create a blueprint for exam-related routes
exam_bp = Blueprint('exam', __name__)


@app.route('/exam_practice')
@login_required  # Assuming exam practice requires login
# @student_required # Optional: if only students should access
def exam_practice():
    """Renders the exam practice page with data from exams.json."""
    exams = load_exams_from_json(
        'static/js/exams.json')  # Adjust path if needed
    print("DEBUG: Loaded exams:", exams)
    return render_template('exam_practice.html', exams=exams)


@app.route('/exam/<int:exam_id>')
@login_required  # Ensure user is logged in to take exams
# @student_required # Optional: restrict to students
def take_exam(exam_id):
    """Loads a specific exam and renders the exam-taking page."""
    exams = load_exams_from_json('static/js/exams.json')  # Load all exams

    # Find the exam with the matching ID
    selected_exam = None
    for exam in exams:
        if exam.get('id') == exam_id:
            selected_exam = exam
            break

    if selected_exam:
        return render_template('take_exam.html', exam=selected_exam)
    else:
        flash('Exam not found.', 'danger')
        # Redirect back if exam ID is invalid
        return redirect(url_for('exam_practice'))


@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
@login_required  # Ensure user is logged in
# @student_required # Optional: restrict to students
def submit_exam(exam_id):
    """Handles the submission of an exam, grades it, saves the result, and logs the activity."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    # Load all exams from the JSON file
    exams = load_exams_from_json('static/js/exams.json')

    # Find the specific exam the user submitted
    selected_exam = next(
        (exam for exam in exams if exam.get('id') == exam_id), None)

    if not selected_exam:
        flash('Exam not found.', 'danger')
        return redirect(url_for('exam_practice'))

    # Get user's submitted answers
    user_answers = request.form

    # Grade the exam
    correct_answers_count = 0
    total_questions = len(selected_exam.get('questions', []))

    if total_questions > 0:
        correct_answers_count = sum(
            1 for question in selected_exam.get('questions', [])
            if str(user_answers.get(f"question_{question.get('id')}")) == str(question.get('correct_answer')))

        score = (correct_answers_count / total_questions) * 100
    else:
        score = 0

    print(f"User {user_id} submitted Exam {exam_id}. Score: {score:.2f}% ({correct_answers_count}/{total_questions} correct)")

    # Save the result to the database
    conn = get_db_connection()
    cur = conn.cursor()
    result_id = None

    try:
        # Save exam result
        cur.execute('''
            INSERT INTO exam_results (user_id, exam_id, score, total_questions, completion_time)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id;
        ''', (user_id, exam_id, score, total_questions))
        result_id = cur.fetchone()[0]  # type: ignore
        # Log the exam submission activity
        cur.execute('''
            INSERT INTO student_activities 
            (student_id, activity_type, description, icon, metadata)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            user_id,
            'exam',
            f"Completed {selected_exam.get('name', 'Exam')}",
            'file-certificate',
            json.dumps({
                'exam_id': exam_id,
                'score': float(score),
                'correct_answers': correct_answers_count,
                'total_questions': total_questions,
                'result_id': result_id
            })
        ))

        conn.commit()
        flash('Exam submitted and graded successfully!', 'success')
        return redirect(url_for('exam_results', result_id=result_id))

    except Exception as e:
        conn.rollback()
        print(f"Error processing exam submission: {e}")
        flash('Error processing exam submission.', 'danger')
        return redirect(url_for('exam_practice'))
    finally:
        cur.close()
        conn.close()

# Placeholder route for displaying exam results


@app.route('/exam_results/<int:result_id>')
@login_required
def exam_results(result_id):
    """Fetches and displays the results of a completed exam."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    result = None
    try:
        # Fetch the specific exam result from the database
        cur.execute('''
            SELECT id, user_id, exam_id, score, total_questions, completion_time
            FROM exam_results
            WHERE id = %s AND user_id = %s; -- Ensure user can only see their own results
        ''', (result_id, user_id))
        result = cur.fetchone()

    except Exception as e:
        print(f"Error fetching exam result {result_id}: {e}")
        flash('Error fetching exam results.', 'danger')
        return redirect(url_for('exam_practice'))  # Redirect if fetching fails
    finally:
        cur.close()
        conn.close()

    if not result:
        flash('Exam result not found or you do not have permission to view it.', 'danger')
        # Redirect if result not found
        return redirect(url_for('exam_practice'))

    # Unpack result data
    result_id, result_user_id, exam_json_id, score, total_questions, completion_time = result

    # Load the exam details from the JSON file using the exam_json_id
    exams = load_exams_from_json('static/js/exams.json')
    exam_details = None
    for exam in exams:
        if exam.get('id') == exam_json_id:
            exam_details = exam
            break

    if not exam_details:
        # This case means the exam data in the JSON was changed/removed after the user took it
        flash(
            f'Exam details for result ID {result_id} not found in JSON file.', 'warning')
        # We can still show the basic score, but not question-by-question review
        return render_template('exam_results.html',
                               result=result,  # Pass the basic result data
                               exam_details=None)  # Indicate exam details are missing

    # Pass both the result data and exam details to the template
    return render_template('exam_results.html',
                           result=result,
                           exam_details=exam_details)
