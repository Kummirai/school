from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_required
from .utils import get_subscription_plans, get_user_subscription_details, get_all_subscriptions, mark_subscription_as_paid


# Create a Blueprint for the subscriptions routes
subscriptions_bp = Blueprint(
    'subscriptions', '__name__', template_folder='templates')


@subscriptions_bp.route('/subscriptions')
def subscriptions():
    plans = get_subscription_plans()
    return render_template('subscriptions/subscribe.html', plans=plans)


@subscriptions_bp.route('/subscription/confirmation/<int:subscription_id>')
@login_required
def subscription_confirmation(subscription_id):
    return render_template('subscriptions/confirmation.html', subscription_id=subscription_id)

# Admin subscription management


@subscriptions_bp.route('/subscription/status')
@login_required
def subscription_status():
    # Ensure only students can access this page if needed, although login_required already restricts it
    if session.get('role') != 'student':
        flash('This page is only for students.', 'warning')
        return redirect(url_for('home.home'))  # Or wherever appropriate

    user_id = session.get('user_id')
    if not user_id:
        # This case should be covered by @login_required, but as a fallback:
        flash('User not logged in.', 'danger')
        return redirect(url_for('home.login'))

    subscription = get_user_subscription_details(user_id)
    return render_template('subscription_status.html', subscription=subscription)
