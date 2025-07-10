from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from decorators.decorator import login_required, admin_required
from models import get_db_connection
from announcements.utils import (
    get_user_announcements,
    mark_announcement_read
)
from students.utils import get_students
from flask import current_app as app

# Create a blueprint for announcements
announcement_bp = Blueprint('announcement_bp', __name__)


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
