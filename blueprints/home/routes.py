from flask import Blueprint, request, render_template, redirect, url_for, flash
from models import User
from flask_login import login_user, logout_user, login_required, current_user
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from blueprints.subscriptions.utils import get_user_subscription
from flask import current_app as app
from blueprints.students.utils import get_user_by_username
from werkzeug.security import check_password_hash
from decorators.decorator import login_required
from blueprints.students.utils import get_students
from blueprints.subscriptions.utils import get_subscription_plans


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
    return render_template('home.html', subscription=subscription, plans=get_subscription_plans())


@home_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('auth/login.html')

        user = User.get_by_username(username)

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')

            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home.home'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('auth/login.html')


@home_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home.home'))


@home_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('admin/dashboard.html', user=current_user)
