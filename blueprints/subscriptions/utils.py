from flask import Blueprint, request, jsonify
from models import get_db_connection

subscriptions_bp = Blueprint('subscriptions', __name__)


def add_subscription_to_db(user_id, plan_id, start_date, end_date, is_active=False, payment_status='pending'):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO subscriptions
            (user_id, plan_id, start_date, end_date, is_active, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (user_id, plan_id, start_date, end_date, is_active, payment_status))
        subscription_id = cur.fetchone()[0]  # type: ignore
        conn.commit()
        return subscription_id
    except Exception as e:
        conn.rollback()
        print(f"Error adding subscription: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def get_subscription_plans():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM subscription_plans')
    plans = cur.fetchall()
    cur.close()
    conn.close()
    return plans


def get_user_subscription(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.id, p.name, p.price, s.start_date, s.end_date, s.is_active, s.payment_status
        FROM subscriptions s
        JOIN subscription_plans p ON s.plan_id = p.id
        WHERE s.user_id = %s
        ORDER BY s.end_date DESC
        LIMIT 1
    ''', (user_id,))
    subscription = cur.fetchone()
    cur.close()
    conn.close()
    return subscription


def get_all_subscriptions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.id, u.username, p.name, p.price, s.start_date, s.end_date, 
               s.is_active, s.payment_status, s.created_at
        FROM subscriptions s
        JOIN users u ON s.user_id = u.id
        JOIN subscription_plans p ON s.plan_id = p.id
        ORDER BY s.end_date DESC
    ''')
    subscriptions = cur.fetchall()
    cur.close()
    conn.close()
    return subscriptions


def mark_subscription_as_paid(subscription_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE subscriptions
            SET payment_status = 'paid', is_active = TRUE
            WHERE id = %s
            RETURNING user_id, plan_id
        ''', (subscription_id,))
        result = cur.fetchone()

        if result:
            user_id, plan_id = result
            # Update user's role if needed (e.g., give premium access)
            cur.execute('''
                UPDATE users
                SET role = CASE 
                    WHEN %s = 2 THEN 'premium' 
                    ELSE role 
                END
                WHERE id = %s
            ''', (plan_id, user_id))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error marking subscription as paid: {e}")
        return False
    finally:
        cur.close()
        conn.close()
