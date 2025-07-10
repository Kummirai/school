from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from flask_login import login_required
from utils import get_subscription_plans, get_user_subscription, get_all_subscriptions, mark_subscription_as_paid
from decorators.decorator import admin_required
from models import get_db_connection
from flask import current_app as app


# Create a Blueprint for the subscriptions routes
subscriptions_bp = Blueprint(
    'subscriptions', '__name__', url_prefix='/subscriptions')


@app.route('/subscriptions')
def subscriptions():
    plans = get_subscription_plans()
    return render_template('subscriptions/subscribe.html', plans=plans)


@app.route('/subscribe')
@login_required
def subscribe():
    plans = get_subscription_plans()
    current_sub = get_user_subscription(session['user_id'])
    return render_template('subscriptions/subscribe.html',
                           plans=plans,
                           current_sub=current_sub)


@app.route('/subscribe/<int:plan_id>', methods=['POST'])
# @login_required
def create_subscription(plan_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if 'user' not in session:
        selected_plan = request.form.get('selected_plan')
        return redirect(url_for('contact_tutor', plan_id=selected_plan))

    try:
        # Get plan details
        cur.execute(
            'SELECT id, price, duration_days FROM subscription_plans WHERE id = %s', (plan_id,))
        plan = cur.fetchone()
        if not plan:
            flash('Invalid subscription plan', 'danger')
            return redirect(url_for('subscribe'))

        # Create subscription (payment will be marked as pending)
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan[2])

        cur.execute('''
            INSERT INTO subscriptions 
            (user_id, plan_id, start_date, end_date, is_active, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (session['user_id'], plan_id, start_date, end_date, False, 'pending'))

        subscription_id = cur.fetchone()[0]  # type: ignore
        conn.commit()

        # In a real app, you would integrate with a payment gateway here
        # For now, we'll just redirect to a confirmation page
        return redirect(url_for('subscription_confirmation', subscription_id=subscription_id))

    except Exception as e:
        conn.rollback()
        flash('Error creating subscription: ' + str(e), 'danger')
        return redirect(url_for('subscribe'))
    finally:
        cur.close()
        conn.close()


@app.route('/subscription/confirmation/<int:subscription_id>')
@login_required
def subscription_confirmation(subscription_id):
    return render_template('subscriptions/confirmation.html', subscription_id=subscription_id)

# Admin subscription management


@app.route('/admin/subscriptions')
@login_required
@admin_required
def manage_subscriptions():
    subscriptions = get_all_subscriptions()
    return render_template('admin/subscriptions/list.html', subscriptions=subscriptions)


@app.route('/admin/subscriptions/mark-paid/<int:subscription_id>', methods=['POST'])
@login_required
@admin_required
def mark_subscription_paid(subscription_id):
    if mark_subscription_as_paid(subscription_id):
        flash('Subscription marked as paid', 'success')
    else:
        flash('Failed to mark subscription as paid', 'danger')
    return redirect(url_for('manage_subscriptions'))


@app.route('/subscription/status')
@login_required
def subscription_status():
    # Ensure only students can access this page if needed, although login_required already restricts it
    if session.get('role') != 'student':
        flash('This page is only for students.', 'warning')
        return redirect(url_for('home'))  # Or wherever appropriate

    user_id = session.get('user_id')
    if not user_id:
        # This case should be covered by @login_required, but as a fallback:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    subscription = get_user_subscription(user_id)
    return render_template('subscription_status.html', subscription=subscription)
