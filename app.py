from functools import wraps
from flask import Flask, flash, redirect, render_template, redirect, request, session, url_for, jsonify, abort, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask import render_template
from flask_login import current_user
import json
import sympy
from sympy import symbols, Eq, solve, simplify
import psycopg2.extras
from psycopg2.extras import DictCursor
from flask import current_app
from models import get_db_connection, initialize_database
from helpers import submit_assignment, get_student_submission,  get_submission_for_grading, get_user_by_id, update_request_status, get_leaderboard, get_recent_activities, get_request_details, update_submission_grade, record_practice_score, send_approval_notification, send_rejection_notification,  get_plan_name, get_plan_price, generate_password_hash, save_plan_request, get_exams_data, load_exams_from_json, log_student_activity, get_practice_data, get_student_submissions, get_student_performance_stats, get_students_for_parent
from decorators.decorator import login_required, admin_required
from blueprints.announcements.utils import get_unread_announcements_count, get_all_announcements, get_user_announcements, mark_announcement_read, create_announcement
from blueprints.assignments.utils import get_assignment_details, add_assignment, get_all_assignments, get_assignments_data, get_assignments_for_user, get_student_assignments, get_all_student_ids, get_unsubmitted_assignments_count
from blueprints.subscriptions.utils import get_subscription_plans

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
# app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.secret_key = os.environ.get(
    'FLASK_SECRET_KEY', 'fallback-secret-key-for-development')
app.jinja_env.globals.update(float=float)


# Configure upload folder in your app
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not app.secret_key:
    raise ValueError("No secret key set for Flask application")


@app.context_processor
def utility_processor():
    def get_plan_name(plan_id):
        # Query your database or plans list to get the plan name
        plans = get_subscription_plans()
        for plan in plans:
            if plan[0] == plan_id:
                return plan[1]
        return "selected"
    return dict(get_plan_name=get_plan_name)





@app.template_filter('datetime')
def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    """Format a datetime object to a string."""
    if value is None:
        return ""
    return value.strftime(format)


@app.context_processor
def inject_functions():
    return dict(
        get_unread_announcements_count=get_unread_announcements_count,
        get_unsubmitted_assignments_count=get_unsubmitted_assignments_count
    )

# if __name__ == '__main__':
#     from waitress import serve
#     initialize_database()
#     serve(app, host="0.0.0.0", port=5000)


if __name__ == '__main__':
    # Enable Flask debug features
    app.debug = True  # Enables auto-reloader and debugger

    # Initialize database
    initialize_database()

    # Run the development server
    app.run(host='0.0.0.0', port=5000)
