from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from datetime import datetime
from flask import current_app as app
from utils import create_session_request, get_all_session_requests, get_session_requests_for_student, update_session_request_status, cancel_booking, book_session, get_student_bookings, get_all_sessions, get_upcoming_sessions, create_session
from decorators.decorator import admin_required
from models import get_db_connection


@app.route('/sessions/request', methods=['GET', 'POST'])
@login_required
def create_session_request_route():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        preferred_time_str = request.form.get('preferred_time')

        if not all([title, category]):
            flash('Title and category are required', 'danger')
            return redirect(url_for('create_session_request_route'))

        try:
            preferred_time = datetime.strptime(
                preferred_time_str, '%Y-%m-%dT%H:%M') if preferred_time_str else None
            request_id = create_session_request(
                student_id=session['user_id'],
                title=title,
                description=description,
                category=category,
                preferred_time=preferred_time
            )

            if request_id:
                flash('Session request submitted successfully!', 'success')
                return redirect(url_for('view_my_session_requests'))
            else:
                flash('Error submitting request', 'danger')
        except ValueError:
            flash('Invalid date/time format', 'danger')

    return render_template('sessions/create.html')


@app.route('/sessions/my-requests')
@login_required
def view_my_session_requests():
    requests = get_session_requests_for_student(session['user_id'])
    return render_template('student/session_requests.html', requests=requests)

# Admin routes


@app.route('/admin/session-requests')
@login_required
@admin_required
def manage_session_requests():
    requests = get_all_session_requests()
    return render_template('admin/session_requests.html', requests=requests)


@app.route('/admin/session-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_session_request(request_id):
    notes = request.form.get('notes', '')
    if update_session_request_status(request_id, 'approved', session['user_id'], notes):
        flash('Session request approved and scheduled!', 'success')
    else:
        flash('Error approving request', 'danger')
    return redirect(url_for('manage_session_requests'))


@app.route('/admin/session-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_session_request(request_id):
    notes = request.form.get('notes', '')
    if update_session_request_status(request_id, 'rejected', session['user_id'], notes):
        flash('Session request rejected', 'success')
    else:
        flash('Error rejecting request', 'danger')
    return redirect(url_for('manage_session_requests'))


@app.route('/sessions/book/<int:session_id>', methods=['POST'])
@login_required
def book_session_route(session_id):
    if session.get('role') != 'student':
        flash('Only students can book sessions', 'danger')
        return redirect(url_for('view_sessions'))

    student_id = session.get('user_id')
    if not student_id:
        flash('User not properly authenticated', 'danger')
        return redirect(url_for('view_sessions'))

    if book_session(student_id, session_id):
        flash('Session booked successfully!', 'success')
    else:
        flash(
            'Could not book session. It might be full or you already booked it.', 'danger')
    return redirect(url_for('view_sessions'))


@app.route('/sessions/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking_route(booking_id):
    if cancel_booking(booking_id, session.get('user_id')):
        flash('Booking cancelled successfully', 'success')
    else:
        flash('Could not cancel booking', 'danger')
    return redirect(url_for('view_sessions'))

# Admin session management routes


@app.route('/sessions')
@login_required
def view_sessions():
    student_id = session.get('user_id')
    if not student_id:
        flash('User not properly authenticated', 'danger')
        return redirect(url_for('login'))

    sessions = get_all_sessions()
    student_bookings = get_student_bookings(student_id)
    return render_template('sessions/list.html',
                           sessions=sessions,
                           bookings=student_bookings)

# Add this new route to app.py


@app.route('/admin/sessions/bookings/<int:session_id>')
@login_required
@admin_required
def view_session_bookings(session_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Get session details
    cur.execute(
        'SELECT title FROM tutorial_sessions WHERE id = %s', (session_id,))
    session_title = cur.fetchone()[0]  # type: ignore

    # Get users who booked this session
    cur.execute('''
        SELECT u.id, u.username 
        FROM student_bookings sb
        JOIN users u ON sb.student_id = u.id
        WHERE sb.session_id = %s
    ''', (session_id,))
    booked_users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('admin/session_bookings.html',
                           session_title=session_title,
                           booked_users=booked_users)


@app.route('/admin/sessions')
@login_required
@admin_required
def manage_sessions():
    sessions = get_all_sessions()
    upcoming_sessions = get_upcoming_sessions()
    return render_template('admin/sessions.html',
                           sessions=sessions,
                           upcoming_sessions=upcoming_sessions)


@app.route('/admin/sessions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_session():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        max_students = request.form.get('max_students')

        try:
            create_session(title, description, start_time,
                           end_time, int(max_students))  # type: ignore
            flash('Session created successfully', 'success')
            return redirect(url_for('manage_sessions'))
        except Exception as e:
            flash(f'Error creating session: {str(e)}', 'danger')

    return render_template('admin/add_session.html')


@app.route('/admin/sessions/delete/<int:session_id>')
@login_required
@admin_required
def delete_session(session_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tutorial_sessions WHERE id = %s', (session_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Session deleted successfully', 'success')
    return redirect(url_for('manage_sessions'))

# Add these helper functions
