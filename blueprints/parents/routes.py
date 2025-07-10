from flask import Blueprint, render_template, redirect, url_for, session, flash, abort, request
import psycopg2.extras
from flask_login import login_required
from students.utils import get_student_bookings
from models import get_db_connection
from flask import current_app as app
from assignments.utils import get_student_assignments, get_assignments_for_user
from helpers import get_students_for_parent, get_student_submissions, get_student_performance_stats
from announcements.utils import get_user_announcements
from sessions.utils import get_upcoming_sessions

# Create a Blueprint for the parent routes
parents_bp = Blueprint('parents', __name__, url_prefix='/parent')


@app.route('/assignments')
@login_required
# @parent_required # If you have a specific decorator for parent role
def parent_view_assignments():
    parent_id = session.get('user_id')
    if not parent_id:
        flash('You must be logged in as a parent to view assignments.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Again, using DictCursor is good for fetching parent's students
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    students_with_assignments = []
    try:
        # Get all students linked to this parent
        cur.execute('''
            SELECT u.id AS student_id, u.username AS student_username
            FROM users u
            JOIN parent_students ps ON u.id = ps.student_id
            WHERE ps.parent_id = %s AND u.role = 'student'
            ORDER BY u.username;
        ''', (parent_id,))
        linked_students = cur.fetchall()

        for student_info in linked_students:
            student_id = student_info['student_id']
            student_username = student_info['student_username']

            assignments_for_student = get_student_assignments(student_id)

            students_with_assignments.append({
                'id': student_id,
                'username': student_username,
                'assignments': assignments_for_student
            })

    except Exception as e:
        flash(f'Error loading assignments: {str(e)}', 'danger')
        print(f"Error in parent_view_assignments route: {e}")  # For debugging
        # Redirect to a safe page on error
        return redirect(url_for('parent_dashboard'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('parent/assignments.html', students_with_assignments=students_with_assignments)


@app.route('/dashboard')
@login_required
def parent_dashboard():
    if session.get('role') != 'parent':
        abort(403)

    students = get_students_for_parent(session['user_id'])
    if not students:
        flash('No students linked to your account', 'warning')
        return render_template('parent/dashboard.html',
                               students=[],
                               selected_student=None,
                               stats=None,
                               assignments=[],
                               submissions=[],
                               bookings=[],
                               announcements=[])

    # Default to first student
    selected_student_id = request.args.get('student_id', students[0]['id'])
    try:
        selected_student_id = int(selected_student_id)
    except (ValueError, TypeError):
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parent_dashboard'))

    selected_student = next(
        (s for s in students if s['id'] == selected_student_id), None)

    if not selected_student:
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parent_dashboard'))

    # Get all data for the selected student
    assignments = get_assignments_for_user(selected_student_id)
    submissions = get_student_submissions(selected_student_id)
    bookings = get_student_bookings(selected_student_id)
    stats = get_student_performance_stats(selected_student_id)
    announcements = get_user_announcements(selected_student_id, limit=5)

    return render_template('parent/dashboard.html',
                           students=students,
                           selected_student=selected_student,
                           assignments=assignments,
                           submissions=submissions,
                           bookings=bookings,
                           stats=stats,
                           announcements=announcements)


@app.route('/submissions/<int:student_id>')
@login_required
# @parent_required
def parent_view_submissions(student_id):
    # Verify parent has access to this student
    students = get_students_for_parent(session['user_id'])
    if not any(s['id'] == student_id for s in students):
        abort(403)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                a.title, 
                a.subject, 
                a.deadline, 
                s.submission_time, 
                s.grade, 
                a.total_marks,
                s.feedback,
                s.file_path
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.student_id = %s
            ORDER BY a.deadline DESC
        ''', (student_id,))

        # Convert to list of dictionaries with proper field names
        submissions = []
        for row in cur.fetchall():
            submissions.append({
                'title': row[0],
                'subject': row[1],
                'deadline': row[2],  # This should be a datetime object
                'submitted_at': row[3],
                'marks_obtained': row[4],
                'total_marks': row[5],
                'feedback': row[6],
                'file_path': row[7]
            })

        return render_template('parent/submissions.html',
                               student_id=student_id,
                               submissions=submissions)
    finally:
        cur.close()
        conn.close()


@app.route('/sessions/<int:student_id>')
@login_required
def parent_view_sessions(student_id):
    if session.get('role') != 'parent':
        abort(403)

    # Verify parent has access to this student
    students = get_students_for_parent(session['user_id'])
    if not any(s['id'] == student_id for s in students):
        abort(403)

    bookings = get_student_bookings(student_id)
    upcoming_sessions = get_upcoming_sessions()
    return render_template('parent/sessions.html',
                           student_id=student_id,
                           bookings=bookings,
                           upcoming_sessions=upcoming_sessions)
