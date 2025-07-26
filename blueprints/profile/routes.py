from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, get_db_connection
from werkzeug.security import generate_password_hash
from blueprints.subscriptions.utils import get_user_subscription_details

profile_bp = Blueprint('profile', __name__, template_folder='templates')


@profile_bp.route('/profile')
@login_required
def profile():
    subscription = get_user_subscription_details(current_user.id)
    print(subscription)
    return render_template('profile/profile.html', user=current_user, subscription=subscription)


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    new_username = request.form.get('username')
    new_password = request.form.get('password')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if new_username:
            cur.execute("UPDATE users SET username = %s WHERE id = %s",
                        (new_username, current_user.id))

        if new_password:
            hashed_password = generate_password_hash(new_password)
            cur.execute("UPDATE users SET password = %s WHERE id = %s",
                        (hashed_password, current_user.id))

        conn.commit()
        flash('Your profile has been updated.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {e}', 'danger')

    finally:
        cur.close()
        conn.close()

    return redirect(url_for('profile.profile'))
