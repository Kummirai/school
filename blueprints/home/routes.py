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
from blueprints.subscriptions.utils import get_subscription_plans, add_subscription_to_db
from datetime import datetime, timedelta


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


@home_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        plan_id = request.form.get('plan_id')

        if not all([username, password, role, plan_id]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('home.signup'))

        if User.get_by_username(username):
            flash('Username already exists.', 'danger')
            return redirect(url_for('home.signup'))

        # Create user
        new_user = User.create(username, password, role)

        if new_user:
            # Create a 7-day trial subscription
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=7)
            subscription_id = add_subscription_to_db(
                user_id=new_user.id,
                plan_id=plan_id,
                start_date=start_date,
                end_date=end_date,
                is_active=True,
                payment_status='trial'
            )

            if subscription_id:
                login_user(new_user)
                session['user_id'] = new_user.id
                session['username'] = new_user.username
                session['role'] = new_user.role
                flash(
                    'Account created successfully! Your 7-day trial has started.', 'success')
                return redirect(url_for('home.home'))
            else:
                flash('Could not create subscription.', 'danger')
        else:
            flash('Error creating account.', 'danger')

        return redirect(url_for('home.signup'))

    plans = get_subscription_plans()
    return render_template('auth/signup.html', plans=plans)


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
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
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
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home.home'))


@home_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('admin/dashboard.html', user=current_user)
""
