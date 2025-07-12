from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from blueprints.subscriptions.utils import get_user_subscription
from flask import current_app as app
from blueprints.students.utils import get_user_by_username
from werkzeug.security import check_password_hash
from decorators.decorator import login_required
from blueprints.students.utils import get_students


# Create a Blueprint for the home routes
home_bp = Blueprint(
    'home', __name__, template_folder='templates', static_folder='static')


@home_bp.route('/')
def home():
    # Initialize subscription to None
    subscription = None
    # Check if user is logged in and 'user_id' is in session
    if 'user_id' in session:
        # Call the function and pass the result to the template
        subscription = get_user_subscription(session['user_id'])

    # Pass the subscription variable to the render_template function
    return render_template('home.html', subscription=subscription)


@home_bp.route('/login', methods=['GET', 'POST'])
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
                return redirect(request.args.get('next') or url_for('home.home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@home_bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home.home'))
