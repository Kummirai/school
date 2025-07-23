from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, session, Flask
from datetime import datetime
import json
import os
from flask_login import login_required
from models import get_db_connection
from helpers import get_student_submission, submit_assignment
from blueprints.assignments.utils import get_assignment_details
from flask import current_app as app


assignments_bp = Blueprint('assignments', __name__,
                           template_folder='templates')


@assignments_bp.route('/assignments', methods=['GET'])
@login_required
def student_assignments():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view your assignments.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    assignments = []
    try:
        cur.execute(
            """
            SELECT
            a.id,
            a.title,
            a.description,
            a.subject,
            a.total_marks,
            a.deadline,
            a.content,
            a.created_at,
            s.grade,                                -- Now fetching grade directly from the joined 'submissions' table
            (s.id IS NOT NULL) AS submitted_status  -- Check if a submission exists (s.id will be NULL if no submission)
        FROM
            assignments a
        JOIN
            assignment_students asl ON a.id = asl.assignment_id
        LEFT JOIN
            submissions s ON a.id = s.assignment_id AND asl.student_id = s.student_id -- LEFT JOIN to include all assignments, even without submissions
        WHERE asl.student_id = %s
        ORDER BY a.deadline DESC;
            """,
            (user_id,)
        )
        for row in cur.fetchall():
            assignments.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'subject': row[3],
                'total_marks': row[4],
                'deadline': row[5],
                'content': row[6] if row[6] else None,
                'created_at': row[7],
                'submitted': row[8],
                'grade': row[9]
            })

        for assignment in assignments:
            assignment['status'] = 'active' if assignment['deadline'] and assignment['deadline'] > datetime.now(
            ) else 'past_deadline'

    except Exception as e:
        print(f"Error fetching student assignments: {e}")
        flash('Could not load your assignments.', 'danger')
    finally:
        cur.close()
        conn.close()

    return render_template('assignments/list.html', assignments=assignments)


@assignments_bp.route('/assignments/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def view_assignment(assignment_id):
    if session.get('role') != 'student':
        flash('Only students can view assignments', 'danger')
        return redirect(url_for('home.home'))

    assignment = get_assignment_details(assignment_id)
    if not assignment:
        flash('Assignment not found', 'danger')
        return redirect(url_for('view_assignments'))

    submission = get_student_submission(session['user_id'], assignment_id)

    if request.method == 'POST':
        submission_text = request.form.get('submission_text', '')
        file_path = None

        # Handle interactive submission data if present
        interactive_data = None
        # Check if there's interactive content (index 7 is content)
        if assignment[7]:
            try:
                # Get form data for interactive questions
                interactive_data = {}
                assignment_content = json.loads(assignment[7])

                # Extract answers for each interactive question
                for question in assignment_content.get('questions', []):
                    qid = question.get('id')
                    if qid:
                        answer = request.form.get(f'q_{qid}')
                        if answer is not None:
                            interactive_data[qid] = {
                                'question': question.get('question'),
                                'answer': answer,
                                'correct_answer': question.get('correct_answer')
                            }

                interactive_data = json.dumps(interactive_data)
            except Exception as e:
                print(f"Error processing interactive data: {e}")

        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file.filename != '':
                filename = secure_filename(file.filename)  # type: ignore
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

        if submit_assignment(assignment_id, session['user_id'], submission_text, file_path, interactive_data):
            flash('Assignment submitted successfully!', 'success')
            return redirect(url_for('assignments.student_assignments'))
        else:
            flash('Error submitting assignment', 'danger')

    # Parse assignment content if it exists
    content = None
    if assignment[7]:  # index 7 is the content field
        try:
            content = json.loads(assignment[7])
        except (TypeError, json.JSONDecodeError):
            content = assignment[7]  # fallback to raw content if not JSON

    return render_template('assignments/view.html',
                           assignment={
                               'id': assignment[0],
                               'title': assignment[1],
                               'description': assignment[2],
                               'subject': assignment[3],
                               'total_marks': assignment[4],
                               'deadline': assignment[5],
                               'created_at': assignment[6],
                               'content': content
                           },
                           submission=submission)


# Adjust this route name if yours is different
@assignments_bp.route('/assignments/submissions')
@login_required  # Assuming this page requires login
def view_submissions():  # Adjust this function name if yours is different
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view your submissions.", "warning")
        return redirect(url_for('home.login'))

    conn = None
    cur = None
    submissions_data = []
    average_score = None
    monthly_scores = []

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch all submissions for the current user
        cur.execute(
            """
            SELECT
                s.id,
                a.title,
                a.subject,
                s.submission_time,
                s.file_path,
                s.submission_text,
                s.grade,
                a.total_marks,
                s.feedback,
                s.interactive_submission_data
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            WHERE
                s.student_id = %s
            ORDER BY
                s.submission_time DESC;
            """,
            (user_id,)
        )
        for row in cur.fetchall():
            submissions_data.append({
                'id': row[0],
                'title': row[1],
                'subject': row[2],
                'submitted_at': row[3],
                'file_path': row[4],
                'submission_text': row[5],
                'marks_obtained': row[6],
                'total_marks': row[7],
                'feedback': row[8],
                'interactive_submission_data': row[9]
            })

        # Calculate Average Score
        cur.execute(
            """
            SELECT
                SUM(s.grade) AS total_grade_sum,
                SUM(a.total_marks) AS total_possible_marks_sum
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            WHERE
                s.student_id = %s AND s.grade IS NOT NULL;
            """,
            (user_id,)
        )
        avg_row = cur.fetchone()
        if avg_row and avg_row[0] is not None and avg_row[1] is not None and avg_row[1] > 0:
            average_score = (avg_row[0] / avg_row[1]) * 100  # Percentage
            # Round to 2 decimal places
            average_score = round(average_score, 2)
        else:
            average_score = 0  # No graded submissions or total marks is zero

        # Fetch Monthly Scores
        cur.execute(
            """
            SELECT
                EXTRACT(YEAR FROM s.submission_time) AS year,
                EXTRACT(MONTH FROM s.submission_time) AS month,
                SUM(s.grade) AS monthly_grade_sum,
                SUM(a.total_marks) AS monthly_possible_marks_sum
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            WHERE
                s.student_id = %s AND s.grade IS NOT NULL
            GROUP BY
                year, month
            ORDER BY
                year DESC, month DESC;
            """,
            (user_id,)
        )
        for row in cur.fetchall():
            year = int(row[0])
            month = int(row[1])
            monthly_grade_sum = row[2]
            monthly_possible_marks_sum = row[3]

            if monthly_possible_marks_sum and monthly_possible_marks_sum > 0:
                percentage = (monthly_grade_sum /
                              monthly_possible_marks_sum) * 100
                monthly_scores.append({
                    'year': year,
                    'month': month,
                    # Get month name
                    'month_name': datetime(year, month, 1).strftime('%B'),
                    'score': round(percentage, 2)
                })

    except Exception as e:
        print(f"Error fetching submission data: {e}")
        flash("Could not load your submission data.", "danger")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template(
        'assignments/submissions.html',
        submissions=submissions_data,
        average_score=average_score,
        monthly_scores=monthly_scores
    )


# Leaderboard routes
