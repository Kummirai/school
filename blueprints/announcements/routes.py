from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from decorators.decorator import login_required, admin_required
from models import get_db_connection
from announcements.utils import (
    get_user_announcements,
    mark_announcement_read,
    get_all_announcements,
    create_announcement
)
from helpers import get_students

app = Blueprint('announcements', __name__)
# Announcement routes


@app.route('/announcements')
@login_required
def view_announcements():
    announcements = get_user_announcements(session['user_id'])
    return render_template('announcements/list.html', announcements=announcements)


@app.route('/announcements/<int:announcement_id>')
@login_required
def view_announcement(announcement_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get the announcement and mark it as read
        cur.execute('''
            SELECT a.id, a.title, a.message, a.created_at, u.username as created_by
            FROM announcements a
            JOIN users u ON a.created_by = u.id
            JOIN user_announcements ua ON a.id = ua.announcement_id
            WHERE ua.user_id = %s AND a.id = %s
        ''', (session['user_id'], announcement_id))

        announcement = cur.fetchone()
        if not announcement:
            flash('Announcement not found', 'danger')
            return redirect(url_for('view_announcements'))

        # Mark as read
        mark_announcement_read(announcement_id, session['user_id'])

        return render_template('announcements/view.html', announcement={
            'id': announcement[0],
            'title': announcement[1],
            'message': announcement[2],
            'created_at': announcement[3],
            'created_by': announcement[4]
        })
    except Exception as e:
        flash('Error viewing announcement', 'danger')
        return redirect(url_for('view_announcements'))
    finally:
        cur.close()
        conn.close()

# Admin announcement management


@app.route('/admin/announcements')
@login_required
@admin_required
def manage_announcements():
    announcements = get_all_announcements()
    return render_template('admin/announcements/list.html', announcements=announcements)


@app.route('/admin/announcements/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_announcement():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        send_to = request.form.getlist('send_to')  # List of user IDs or 'all'

        if not title or not message:
            flash('Title and message are required', 'danger')
            return redirect(url_for('add_announcement'))

        try:
            # If "all" is selected, send to all students
            user_ids = None if 'all' in send_to else [
                int(user_id) for user_id in send_to]

            create_announcement(
                title=title,
                message=message,
                created_by=session['user_id'],
                user_ids=user_ids
            )

            flash('Announcement created successfully!', 'success')
            return redirect(url_for('manage_announcements'))
        except Exception as e:
            flash(f'Error creating announcement: {str(e)}', 'danger')
            return redirect(url_for('add_announcement'))

    # GET request - show form
    students = get_students()
    return render_template('admin/announcements/add.html', students=students)
