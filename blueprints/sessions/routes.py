from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from datetime import datetime
from flask import current_app as app
from .utils import create_session_request, get_session_requests_for_student, cancel_booking, book_session, get_student_bookings, get_all_sessions

# Create a Blueprint for the session routes
sessions_bp = Blueprint('sessions', __name__,
                        template_folder='templates', static_folder='static')


@sessions_bp.route('/request', methods=['GET', 'POST'])
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
                return redirect(url_for('sessions.view_my_session_requests'))
            else:
                flash('Error submitting request', 'danger')
        except ValueError:
            flash('Invalid date/time format', 'danger')

    return render_template('sessions/create.html')


@sessions_bp.route('/my-requests')
@login_required
def view_my_session_requests():
    requests = get_session_requests_for_student(session['user_id'])
    return render_template('student/session_requests.html', requests=requests)


@sessions_bp.route('/book/<int:session_id>', methods=['POST'])
@login_required
def book_session_route(session_id):
    if session.get('role') != 'student':
        flash('Only students can book sessions', 'danger')
        return redirect(url_for('sessions.view_sessions'))

    student_id = session.get('user_id')
    if not student_id:
        flash('User not properly authenticated', 'danger')
        return redirect(url_for('sessions.view_sessions'))

    if book_session(student_id, session_id):
        flash('Session booked successfully!', 'success')
    else:
        flash(
            'Could not book session. It might be full or you already booked it.', 'danger')
    return redirect(url_for('sessions.view_sessions'))


@sessions_bp.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking_route(booking_id):
    if cancel_booking(booking_id, session.get('user_id')):
        flash('Booking cancelled successfully', 'success')
    else:
        flash('Could not cancel booking', 'danger')
    return redirect(url_for('sessions.view_sessions'))


@sessions_bp.route('/')
@login_required
def view_sessions():
    student_id = session.get('user_id')
    print("your student_id is", student_id)
    if not student_id:
        flash('User not properly authenticated', 'danger')
        return redirect(url_for('home.login'))

    sessions = get_all_sessions()
    student_bookings = get_student_bookings(student_id)
    return render_template('sessions/list.html',
                           sessions=sessions,
                           bookings=student_bookings)

# Add this new route to app.py
