from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from flask_login import login_required
from models import get_db_connection
from blueprints.subscriptions.utils import get_subscription_plans, get_user_subscription

# Create a Blueprint for the subscriptions routes
subscribe_bp = Blueprint(
    'subscribe', __name__, template_folder='templates')


@subscribe_bp.route('/')
@login_required
def subscribe():
    plans = get_subscription_plans()
    current_sub = get_user_subscription(session['user_id'])
    return render_template('subscriptions/subscribe.html',
                           plans=plans,
                           current_sub=current_sub)


@subscribe_bp.route('/<int:plan_id>', methods=['POST'])
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

        # In a real subscriptions_bp, you would integrate with a payment gateway here
        # For now, we'll just redirect to a confirmation page
        return redirect(url_for('subscription_confirmation', subscription_id=subscription_id))

    except Exception as e:
        conn.rollback()
        flash('Error creating subscription: ' + str(e), 'danger')
        return redirect(url_for('subscribe'))
    finally:
        cur.close()
        conn.close()
