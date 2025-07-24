from flask import Blueprint, render_template, redirect, url_for, session, flash, abort, request, jsonify
import psycopg2.extras
from flask_login import login_required
from models import get_db_connection
from flask import current_app as app
from helpers import get_students_for_parent, get_student_submissions, get_student_performance_stats
# Update this import to the correct path
from blueprints.sessions.utils import get_upcoming_sessions, get_student_bookings
# Add these imports
from blueprints.assignments.utils import get_student_assignments
from blueprints.announcements.utils import get_user_announcements  # Add this import


# Create a Blueprint for the parent routes
parents_bp = Blueprint('parents', __name__, url_prefix='/parents')


@parents_bp.route('/assignments')  # Changed from @app.route
@login_required
def parent_view_assignments():
    parent_id = session.get('user_id')
    if not parent_id:
        flash('You must be logged in as a parent to view assignments.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
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
        print(f"Error in parent_view_assignments route: {e}")
        return redirect(url_for('parents.parent_dashboard'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('parent/assignments.html', students_with_assignments=students_with_assignments)


@parents_bp.route('/dashboard')  # Changed from @app.route
@login_required
def parent_dashboard():
    if session.get('role') != 'parent':
        abort(403)

    students = get_students_for_parent(session['user_id'])
    if not students:
        flash('No students linked to your account', 'warning')
        return render_template('parent/dashboard.html',
                               students=[],
                               selected_student=None)

    # Default to first student
    selected_student_id = request.args.get('student_id', students[0]['id'])
    try:
        selected_student_id = int(selected_student_id)
    except (ValueError, TypeError):
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parents.parent_dashboard'))

    selected_student = next(
        (s for s in students if s['id'] == selected_student_id), None)

    if not selected_student:
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parents.parent_dashboard'))

    # Data is now loaded via API, so we only need to pass student info
    return render_template('parent/dashboard.html',
                           students=students,
                           selected_student=selected_student)


@parents_bp.route('/api/student/<int:student_id>/chart_data')
@login_required
def student_chart_data(student_id):
    if session.get('role') != 'parent':
        abort(403)

    # Verify parent has access to this student
    students = get_students_for_parent(session['user_id'])
    if not any(s['id'] == student_id for s in students):
        abort(403)

    try:
        # In a real app, you'd fetch this data from your database.
        # Using placeholder data that matches the JS expectations.
        stats = get_student_performance_stats(student_id)
        submissions = get_student_submissions(student_id)
        announcements = get_user_announcements(student_id, limit=5)

        # Format activities from various sources
        activities = []
        for sub in submissions[:3]:
            activities.append({
                "icon": "fa-file-upload",
                "title": f"Submitted: {sub['title']}",
                "description": f"Score: {sub['marks_obtained']}/{sub['total_marks']}" if sub.get('marks_obtained') else "Awaiting grade",
                "time": sub['submitted_at'].strftime('%b %d')
            })

        for ann in announcements[:2]:
            activities.append({
                "icon": "fa-bullhorn",
                "title": f"Announcement: {ann['title']}",
                "description": ann['message'][:50] + '...',
                "time": ann['created_at'].strftime('%b %d')
            })

        # This data structure should match what your JS expects
        chart_data = {
            "assignments": stats.get('assignments', {}),
            "practice": stats.get('practice', {}),
            "exams": stats.get('exams', {}),
            "trend": stats.get('trend', {}),
            "subjects": stats.get('subjects', {}),
            "activities": activities
        }

        return jsonify(chart_data)

    except Exception as e:
        print(f"Error fetching chart data: {e}")
        return jsonify({"error": "Could not load student data."}), 500


@parents_bp.route('/submissions/<int:student_id>')  # Changed from @app.route
@login_required
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
                'deadline': row[2],
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


@parents_bp.route('/sessions/<int:student_id>')  # Changed from @app.route
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
