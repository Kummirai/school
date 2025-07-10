from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from students.utils import get_user_by_username,  get_students
from flask import current_app as app
from decorators.decorator import login_required, admin_required
from models import get_db_connection
from tutorials.utils import get_all_categories
from sessions.utils import get_upcoming_sessions

auth_bp = Blueprint('auth', __name__)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['class'] = user.get(
                'class', 'default_class')  # Add this line
            flash('Logged in successfully!', 'success')

            if user['role'] == 'parent':
                return redirect(url_for('parent_dashboard'))
            else:
                return redirect(request.args.get('next') or url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))
