from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from datetime import datetime
from flask import current_app as app
from utils import create_session_request, get_all_session_requests, get_session_requests_for_student, update_session_request_status
from decorators.decorator import admin_required


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
