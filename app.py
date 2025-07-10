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


# Add this new route to app.py


@app.route('/whiteboards')
@login_required
def list_whiteboards():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get whiteboards the user has access to
        cur.execute('''
            SELECT w.id, w.name, u.username as created_by, w.created_at
            FROM whiteboards w
            JOIN users u ON w.created_by = u.id
            JOIN whiteboard_participants p ON w.id = p.whiteboard_id
            WHERE p.user_id = %s
            ORDER BY w.created_at DESC
        ''', (session['user_id'],))

        whiteboards = [{
            'id': row[0],
            'name': row[1],
            'created_by': row[2],
            'created_at': row[3]
        } for row in cur.fetchall()]

        return render_template('whiteboards/list.html', whiteboards=whiteboards)
    except Exception as e:
        print(f"Error listing whiteboards: {e}")
        return render_template('whiteboards/list.html', whiteboards=[])
    finally:
        cur.close()
        conn.close()


def get_chart_data(student_id):  # type: ignore
    try:
        # Get base data
        assignments = get_assignments_data(student_id)
        practice = get_practice_data(student_id)
        exams = get_exams_data(student_id)
        activities = get_recent_activities(student_id)

        # Get trend data from database
        trend_data = get_actual_trend_data(student_id)
        subject_data = get_actual_subject_data(student_id)

        return jsonify({
            'assignments': assignments,
            'practice': practice,
            'exams': exams,
            'activities': activities,
            'trend': trend_data,
            'subjects': subject_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_actual_trend_data(student_id):
    """Fetch actual trend data from database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get monthly trends for the last 6 months
            cur.execute("""
                WITH months AS (
    SELECT generate_series(
        date_trunc('month', CURRENT_DATE - INTERVAL '5 months'),
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS month
)
SELECT
    TO_CHAR(months.month, 'Mon') AS month_name,
    COALESCE(AVG(a.grade), 0) AS assignment_avg,
    COALESCE(AVG(p.score), 0) AS practice_avg,
    COALESCE(AVG(e.score), 0) AS exam_avg
FROM months
LEFT JOIN (
    SELECT a.*, s.grade 
    FROM assignments a
    JOIN submissions s ON a.id = s.assignment_id
    WHERE s.student_id = %s
) a ON date_trunc('month', a.deadline) = months.month
LEFT JOIN practice_scores p ON
    date_trunc('month', p.completed_at) = months.month AND
    p.student_id = %s
LEFT JOIN exam_results e ON
    date_trunc('month', e.completion_time) = months.month AND
    e.user_id = %s
GROUP BY months.month
ORDER BY months.month
            """, (student_id, student_id, student_id))

            results = cur.fetchall()

            if not results:
                return {
                    'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    'assignments': [0, 0, 0, 0, 0, 0],
                    'practice': [0, 0, 0, 0, 0, 0],
                    'exams': [0, 0, 0, 0, 0, 0]
                }

            # Convert query results to trend format
            labels = [row[0] for row in results]
            assignments = [round(float(row[1]), 1) for row in results]
            practice = [round(float(row[2]), 1) for row in results]
            exams = [round(float(row[3]), 1) for row in results]

            return {
                'labels': labels,
                'assignments': assignments,
                'practice': practice,
                'exams': exams
            }

    except Exception as e:
        print(f"Error fetching trend data: {e}")
        return {
            'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'assignments': [0, 0, 0, 0, 0, 0],
            'practice': [0, 0, 0, 0, 0, 0],
            'exams': [0, 0, 0, 0, 0, 0]
        }
    finally:
        conn.close()


def get_actual_subject_data(student_id):
    """Fetch actual subject data from database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
               SELECT 
                    subject,
                    AVG(grade) as avg_score
                FROM (
                    SELECT 
                        a.title as subject, 
                        s.grade 
                    FROM assignments a
                    JOIN submissions s ON a.id = s.assignment_id
                    WHERE s.student_id = %s
                    
                    UNION ALL
                    
                    SELECT 
                        subject, 
                        score 
                    FROM practice_scores 
                    WHERE student_id = %s
                    
                ) combined
                WHERE grade IS NOT NULL
                GROUP BY subject
                ORDER BY avg_score DESC
                LIMIT 4
            """, (student_id, student_id))

            results = cur.fetchall()
            print(results)
            if not results:
                return {
                    'labels': ['Math', 'Science', 'English', 'History'],
                    'scores': [0, 0, 0, 0]
                }

            # Pad with default values if less than 4 subjects
            labels = [row[0] for row in results]
            scores = [round(float(row[1])) for row in results]

            while len(labels) < 4:
                labels.append(f"Subject {len(labels)+1}")
                scores.append(0)

            return {
                'labels': labels[:4],  # Ensure only 4 subjects
                'scores': scores[:4]
            }

    except Exception as e:
        print(f"Error fetching subject data: {e}")
        return {
            'labels': ['Math', 'Science', 'English', 'History'],
            'scores': [0, 0, 0, 0]
        }
    finally:
        conn.close()


@app.route('/api/student/<int:student_id>/chart_data')
def get_chart_data(student_id):
    """Endpoint to fetch all chart data from database"""
    try:
        # Get all data from database
        assignments = get_assignments_data(student_id)
        print(assignments)
        practice = get_practice_data(student_id)
        print(practice)
        exams = get_exams_data(student_id)
        print(exams)
        activities = get_recent_activities(student_id)

        # Get actual trend data with real dates
        trend_data = get_actual_trend_data(student_id)

        # Get actual subject performance data
        subject_data = get_actual_subject_data(student_id)

        return jsonify({
            'assignments': assignments,
            'practice': practice,
            'exams': exams,
            'activities': activities,
            'trend': trend_data,
            'subjects': subject_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# In your app.py file, usually near your other admin routes


# Studyguides
@app.route('/grade7/numeric_geometric_patterns')
@login_required
def numeric_geometric_patterns():
    return render_template('grade7_maths/numeric_geometric_patterns.html')


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
