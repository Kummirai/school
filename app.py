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
from helpers import get_all_categories, get_videos_by_category, get_category_name, get_user_subscription, submit_assignment, get_student_submission,  get_submission_for_grading, get_user_by_id, update_request_status, get_leaderboard, get_recent_activities, get_request_details, update_submission_grade, record_practice_score, send_approval_notification, send_rejection_notification,  get_plan_name, get_plan_price, generate_password_hash, save_plan_request, get_subscription_plans, get_all_subscriptions, get_exams_data, mark_subscription_as_paid, load_exams_from_json, log_student_activity, add_subscription_to_db,  get_practice_data, get_student_submissions, get_student_performance_stats, get_students_for_parent
from decorators.decorator import login_required, admin_required
from blueprints.announcements.utils import get_unread_announcements_count, get_all_announcements, get_user_announcements, mark_announcement_read, create_announcement
from blueprints.assignments.utils import get_assignment_details, add_assignment, get_all_assignments, get_assignments_data, get_assignments_for_user, get_student_assignments, get_all_student_ids, get_unsubmitted_assignments_count

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


@app.route('/video-conference')
def video_conference():
    return render_template('live_session.html')  # We'll create this file next


# Student session booking routes


def get_all_videos():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT tv.id, tv.title, tv.url, tc.name 
        FROM tutorial_videos tv
        JOIN tutorial_categories tc ON tv.category_id = tc.id
    ''')
    videos = cur.fetchall()
    cur.close()
    conn.close()
    return videos


def add_video(title, url, category_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO tutorial_videos (title, url, category_id) VALUES (%s, %s, %s)',
                (title, url, category_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_video(video_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tutorial_videos WHERE id = %s', (video_id,))
    conn.commit()
    cur.close()
    conn.close()



# Routes


@app.route('/')
def home():
    # Initialize subscription to None
    subscription = None
    # Check if user is logged in and 'user_id' is in session
    if 'user_id' in session:
        # Call the function and pass the result to the template
        subscription = get_user_subscription(session['user_id'])

    # Pass the subscription variable to the render_template function
    return render_template('home.html', subscription=subscription)

# Curriculums



# Admin dashboard





@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

# app.py


@app.route('/admin/submissions/all')
@login_required
# @roles_required('admin', 'teacher') # Assuming only admins/teachers can view all submissions
def list_all_submissions():
    conn = None
    cur = None
    submissions_data = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                s.id,
                a.title AS assignment_title,
                u.username AS student_username,
                s.submission_time,
                s.grade,
                s.file_path,
                s.submission_text,
                s.interactive_submission_data,
                s.assignment_id -- Add assignment_id here
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            JOIN
                users u ON s.student_id = u.id
            ORDER BY
                s.submission_time DESC;
            """
        )
        for row in cur.fetchall():
            submissions_data.append({
                'id': row[0],
                'assignment_title': row[1],
                'student_username': row[2],
                'submission_time': row[3],
                'grade': row[4],
                'file_path': row[5],
                'submission_text': row[6],
                'interactive_submission_data': row[7],
                'assignment_id': row[8]  # Add assignment_id to the dictionary
            })
    except Exception as e:
        print(f"Error fetching all submissions: {e}")
        flash("Could not load all submissions.", "danger")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('admin/all_submissions.html', submissions=submissions_data)

# Student assignment routes


@app.route('/admin/dashboard')
@login_required
def dashboard():
    try:

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT username, assignment_id, title, subject, deadline, total_marks
                FROM assignments a
                JOIN assignment_students au ON a.id = au.assignment_id
                JOIN users u ON u.id = au.student_id;
        ''')
        assignments = cur.fetchall()
        cur.close()
        conn.close()

        print(assignments)
        return render_template(
            'admin/dashboard.html',
            assignments=assignments,
            current_time=datetime.utcnow()
        )
    except Exception as e:
        app.logger.error(f"Error fetching assignments: {str(e)}")
        return render_template('dashboard.html',
                               assignments=[],
                               current_time=datetime.utcnow())

# Add these new routes to app.py


@app.route('/admin/assignments/<int:assignment_id>/submissions/<int:student_id>/grade', methods=['GET', 'POST'])
@login_required
@admin_required
def grade_submission(assignment_id, student_id):
    # Get student details
    student = get_user_by_id(student_id)
    if not student:
        flash('Student not found', 'danger')
        return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))

    # Get submission and assignment details
    data = get_submission_for_grading(assignment_id, student_id)
    if not data:
        flash('Submission not found', 'danger')
        return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))

    if request.method == 'POST':
        marks_obtained = request.form.get('marks_obtained')
        feedback = request.form.get('feedback', '')

        try:
            marks_obtained = float(marks_obtained)  # type: ignore
            if marks_obtained < 0 or marks_obtained > data['assignment']['total_marks']:
                flash('Invalid marks value', 'danger')
                return redirect(url_for('grade_submission', assignment_id=assignment_id, student_id=student_id))

            if update_submission_grade(assignment_id, student_id, marks_obtained, feedback):
                flash('Grade submitted successfully', 'success')
                return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))
            else:
                flash('Error submitting grade', 'danger')
        except ValueError:
            flash('Invalid marks format', 'danger')

    return render_template('admin/assignments/grade.html',
                           assignment_id=assignment_id,
                           student=student,
                           submission=data['submission'],
                           assignment=data['assignment'])


@app.route('/leaderboard')
@login_required
def view_leaderboard():
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    time_period = request.args.get('time', 'all')

    leaderboard, user_stats, user_rank = get_leaderboard(
        subject=subject,
        topic=topic,
        time_period=time_period
    )

    # Get available subjects and topics
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT subject FROM practice_scores ORDER BY subject')
    available_subjects = [row[0] for row in cur.fetchall()]

    available_topics = []
    if subject:
        cur.execute('''
            SELECT DISTINCT topic FROM practice_scores 
            WHERE subject = %s ORDER BY topic
        ''', (subject,))
        available_topics = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return render_template('leaderboard.html',
                           leaderboard=leaderboard,
                           available_subjects=available_subjects,
                           available_topics=available_topics,
                           current_subject=subject,
                           current_topic=topic,
                           user_stats=user_stats,
                           user_rank=user_rank)


@app.route('/api/leaderboard-details')
@login_required
def get_leaderboard_details():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get basic user info
        cur.execute('SELECT username FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get overall stats (total score / attempts)
        cur.execute('''
            SELECT 
                ROUND(SUM(score)::numeric / COUNT(id), 2) as avg_score,
                COUNT(*) as attempt_count,
                ROUND(AVG(score::numeric / total_questions * 100), 2) as avg_percentage
            FROM practice_scores
            WHERE student_id = %s
        ''', (user_id,))
        overall_stats = cur.fetchone()

        # Get global rank based on (total score / attempts)
        cur.execute('''
            WITH ranked_students AS (
                SELECT 
                    student_id,
                    SUM(score)::numeric / COUNT(id) as avg_score,
                    DENSE_RANK() OVER (ORDER BY (SUM(score)::numeric / COUNT(id)) DESC) as rank
                FROM practice_scores
                GROUP BY student_id
            )
            SELECT rank 
            FROM ranked_students
            WHERE student_id = %s
        ''', (user_id,))
        rank_result = cur.fetchone()

        # Get performance by subject
        cur.execute('''
            SELECT 
                subject,
                ROUND(SUM(score)::numeric / COUNT(id), 2) as avg_score,
                COUNT(*) as attempt_count,
                ROUND(AVG(score::numeric / total_questions * 100), 2) as avg_percentage
            FROM practice_scores
            WHERE student_id = %s
            GROUP BY subject
            ORDER BY avg_score DESC
        ''', (user_id,))
        subjects = []
        for row in cur.fetchall():
            subjects.append({
                'subject': row[0],
                'avg_score': row[1],
                'attempt_count': row[2],
                'avg_percentage': row[3]
            })

        # Get history for chart
        cur.execute('''
            SELECT 
                score,
                total_questions,
                ROUND((score::numeric / total_questions * 100), 2) as percentage,
                completed_at,
                subject,
                topic
            FROM practice_scores
            WHERE student_id = %s
            ORDER BY completed_at
        ''', (user_id,))

        history = []
        for row in cur.fetchall():
            history.append({
                'score': row[0],
                'total_questions': row[1],
                'percentage': row[2],
                'date': row[3].strftime('%Y-%m-%d'),
                'subject': row[4],
                'topic': row[5]
            })

        return jsonify({
            'username': user[0],
            'avg_score': overall_stats[0] if overall_stats else 0,
            'attempt_count': overall_stats[1] if overall_stats else 0,
            'avg_percentage': overall_stats[2] if overall_stats else 0,
            'rank': rank_result[0] if rank_result else None,
            'subjects': subjects,
            'history': history
        })

    except Exception as e:
        print(f"Error getting leaderboard details: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/record-practice', methods=['POST'])
@login_required
def record_practice():
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Only students can record practice'})

    data = request.get_json()
    subject = data.get('subject')
    topic = data.get('topic')
    score = data.get('score')
    total_questions = data.get('total_questions')

    if not all([subject, topic, score is not None, total_questions]):
        return jsonify({'success': False, 'error': 'Missing required fields'})

    try:
        success = record_practice_score(
            student_id=session['user_id'],
            subject=subject,
            topic=topic,
            score=score,
            total_questions=total_questions
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/admin/approve_request/<int:request_id>')
@admin_required  # Add your admin auth decorator
def approve_request(request_id):
    # Update request status in DB
    update_request_status(request_id, 'approved')

    # Get request details
    request = get_request_details(request_id)

    # Create subscription for user
    create_subscription(request['user_email'],  # type: ignore
                        request['plan_id'])  # type: ignore

    # Send confirmation email to user
    send_approval_notification(
        request.user_email, request.plan_name)  # type: ignore

    flash('Request approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject_request/<int:request_id>')
@admin_required
def reject_request(request_id):
    # Update request status
    update_request_status(request_id, 'rejected')

    # Get request details
    request = get_request_details(request_id)

    # Send rejection email
    send_rejection_notification(
        request.user_email, request.plan_name)  # type: ignore

    flash('Request rejected.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/submit_plan_request', methods=['POST'])
def submit_plan_request():
    # Get form data
    data = {
        'user_name': request.form.get('name'),
        'user_email': request.form.get('email'),
        'user_phone': request.form.get('phone'),
        'message': request.form.get('message', ''),
        'plan_id': request.form.get('plan_id'),
        'plan_name': get_plan_name(request.form.get('plan_id')),
        'plan_price': get_plan_price(request.form.get('plan_id')),
        'status': 'pending'
    }

    try:
        # Save the request
        request_id = save_plan_request(data)
        if request_id:
            flash('Request submitted successfully!', 'success')
            return redirect(url_for('confirmation'))
        else:
            flash('Error submitting request', 'danger')
            return redirect(url_for('contact_tutor', plan_id=data['plan_id']))

    except Exception as e:
        current_app.logger.error(f"Database error: {str(e)}")
        flash('Error submitting request. Please try again.', 'danger')
        return redirect(url_for('contact_tutor', plan_id=data['plan_id']))


def get_plan_details(plan_id):
    # Example implementation - replace with your actual DB query
    plans = {
        1: {'name': 'Access', 'price': 99.99},
        2: {'name': 'Standard', 'price': 199.99},
        3: {'name': 'Premium', 'price': 299.99}
    }
    return plans.get(int(plan_id), {'name': 'Unknown Plan', 'price': 0})

# Email notification function (implement with your email service)


def send_admin_notification(user_email, plan_name, message):
    # Implement using Flask-Mail, SendGrid, etc.
    pass


@app.route('/confirmation')
def confirmation():
    """Confirmation page after plan request submission"""
    return render_template('confirmation.html')


@app.route('/contact_tutor/<int:plan_id>')
def contact_tutor(plan_id):
    """Contact tutor page with plan information"""
    return render_template('contact_tutor.html', plan_id=plan_id)


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

# Add this new route to app.py


@app.route('/admin/approve_requests')
@login_required
@admin_required
def approve_requests():
    conn = get_db_connection()
    try:
        # Use DictCursor to get results as dictionaries
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, user_name, user_email, user_phone, 
                   plan_name, plan_price, request_date
            FROM requests 
            WHERE status = 'pending'
            ORDER BY request_date DESC
        """)
        requests = cur.fetchall()
        return render_template('admin/approve_requests.html',
                               pending_requests=requests)
    except Exception as e:
        print(f"Error fetching requests: {e}")
        flash('Error loading requests', 'danger')
        return render_template('admin/approve_requests.html',
                               pending_requests=[])
    finally:
        cur.close()
        conn.close()


@app.route('/admin/subscriptions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_subscription():
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id')
            plan_id = request.form.get('plan_id')
            start_date_str = request.form.get('start_date')
            duration_days = request.form.get('duration_days')
            mark_paid = request.form.get(
                'mark_paid') is not None  # Checkbox value

            if not all([student_id, plan_id, start_date_str, duration_days]):
                flash('All fields are required', 'danger')
                return redirect(url_for('admin_add_subscription'))

            # Convert data types
            student_id = int(student_id)  # type: ignore
            plan_id = int(plan_id)  # type: ignore
            duration_days = int(duration_days)  # type: ignore
            start_date = datetime.strptime(
                start_date_str, '%Y-%m-%d')  # type: ignore
            end_date = start_date + timedelta(days=duration_days)

            # Determine payment status and active status
            payment_status = 'paid' if mark_paid else 'pending'
            is_active = mark_paid  # Subscription is active immediately if marked as paid

            subscription_id = add_subscription_to_db(
                user_id=student_id,
                plan_id=plan_id,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active,
                payment_status=payment_status
            )

            if subscription_id:
                # If marked paid, update user role if necessary (e.g., grant premium access)
                if is_active:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            'SELECT name FROM subscription_plans WHERE id = %s', (plan_id,))
                        plan_name = cur.fetchone()[0]  # type: ignore
                        if plan_name.lower() == 'premium':  # Check plan name for role update
                            cur.execute(
                                "UPDATE users SET role = 'premium' WHERE id = %s", (student_id,))
                            conn.commit()
                    except Exception as e:
                        print(f"Error updating user role: {e}")
                    finally:
                        cur.close()
                        conn.close()

                flash('Subscription added successfully', 'success')
                return redirect(url_for('manage_subscriptions'))
            else:
                flash('Error adding subscription', 'danger')

        except ValueError:
            flash('Invalid input data', 'danger')
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            app.logger.error(f"Admin add subscription error: {str(e)}")

    # GET request
    students = get_students()
    plans = get_subscription_plans()
    print("DEBUG: Rendering admin/add_subscription.html. Checking if 'float' is in globals:",
          'float' in app.jinja_env.globals)  # Add this line
    return render_template('admin/add_subscription.html', students=students, plans=plans)


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


@app.route('/admin/announcements/delete/<int:announcement_id>', methods=['POST'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM announcements WHERE id = %s',
                    (announcement_id,))
        conn.commit()
        flash('Announcement deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error deleting announcement', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('manage_announcements'))


@app.route('/admin/assignments/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_assignments():
    if request.method == 'POST':
        if 'json_file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)

        file = request.files['json_file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)

        if file and file.filename.endswith('.json'):  # type: ignore
            try:
                data = json.load(file)  # type: ignore

                # Handle both single assignment and array of assignments
                assignments_data = data if isinstance(data, list) else [data]

                # Determine assigned students from form selection
                form_assigned_users = []
                if 'assign_all' in request.form and request.form['assign_all'] == 'all':
                    form_assigned_users = None  # Indicates 'all students' from the form
                else:
                    selected_student_ids = request.form.getlist(
                        'selected_students')
                    if selected_student_ids:
                        form_assigned_users = [int(s_id)
                                               for s_id in selected_student_ids]
                    else:
                        form_assigned_users = []  # No specific students selected in form

                imported_count = 0
                for assignment_data in assignments_data:
                    # Validate required fields
                    required_fields = ['title', 'description',
                                       'subject', 'total_marks', 'deadline']
                    if not all(field in assignment_data for field in required_fields):
                        flash(
                            'Invalid JSON structure - missing required fields for an assignment', 'danger')
                        continue  # Skip to the next assignment in the JSON

                    try:
                        # Convert deadline string to datetime
                        deadline = datetime.strptime(
                            assignment_data['deadline'], '%Y-%m-%d %H:%M')
                    except ValueError:
                        flash(
                            'Invalid deadline format in JSON (use YYYY-MM-DD HH:MM)', 'danger')
                        continue  # Skip to the next assignment in the JSON

                    # Determine final assigned users for this specific assignment
                    # Default to 'all' if no specific assignment
                    final_assigned_users_for_this_assignment = None

                    # Prioritize 'assigned_users' from JSON if it exists
                    assigned_users_from_json = assignment_data.get(
                        'assigned_users')
                    if assigned_users_from_json is not None:
                        if assigned_users_from_json == 'all':
                            # Map JSON 'all' string to None for add_assignment, meaning all students
                            final_assigned_users_for_this_assignment = None
                        else:
                            # Use the list of user IDs from JSON
                            final_assigned_users_for_this_assignment = assigned_users_from_json
                    else:
                        # If JSON doesn't specify, use what was selected in the form
                        final_assigned_users_for_this_assignment = form_assigned_users

                    # Get the interactive content if provided
                    content = assignment_data.get('content', None)
                    if content:
                        # Convert to string for storage
                        content = json.dumps(content)

                    # Create assignment with the interactive content
                    success = add_assignment(
                        title=assignment_data['title'],
                        description=assignment_data['description'],
                        subject=assignment_data['subject'],
                        total_marks=int(assignment_data['total_marks']),
                        deadline=deadline,
                        assigned_students_ids=final_assigned_users_for_this_assignment,
                        content=content
                    )

                    if success:
                        imported_count += 1
                    else:
                        flash(
                            f'Error creating assignment: {assignment_data["title"]}', 'warning')

                flash(
                    f'Successfully imported {imported_count} assignments', 'success')
                if imported_count < len(assignments_data):
                    flash(
                        f'{len(assignments_data) - imported_count} assignments could not be imported due to errors.', 'warning')
                return redirect(url_for('manage_assignments'))

            except json.JSONDecodeError:
                flash('Invalid JSON file. Please ensure it is well-formed.', 'danger')
            except Exception as e:
                flash(f'Error importing assignments: {str(e)}', 'danger')

        else:
            flash('Only JSON files are allowed', 'danger')

    # GET request - show import form
    conn = None
    cur = None
    students = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Fetch all students to populate the checkboxes in the form
        cur.execute(
            "SELECT id, username FROM users WHERE role = 'student' ORDER BY username")
        students = [{'id': row[0], 'username': row[1]}
                    for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching students for import form: {e}")
        flash('Could not load student list. Please check database connection.', 'danger')
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('admin/assignments/import.html', students=students)


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


@app.route('/parent/dashboard')
@login_required
def parent_dashboard():
    if session.get('role') != 'parent':
        abort(403)

    students = get_students_for_parent(session['user_id'])
    if not students:
        flash('No students linked to your account', 'warning')
        return render_template('parent/dashboard.html',
                               students=[],
                               selected_student=None,
                               stats=None,
                               assignments=[],
                               submissions=[],
                               bookings=[],
                               announcements=[])

    # Default to first student
    selected_student_id = request.args.get('student_id', students[0]['id'])
    try:
        selected_student_id = int(selected_student_id)
    except (ValueError, TypeError):
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parent_dashboard'))

    selected_student = next(
        (s for s in students if s['id'] == selected_student_id), None)

    if not selected_student:
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parent_dashboard'))

    # Get all data for the selected student
    assignments = get_assignments_for_user(selected_student_id)
    submissions = get_student_submissions(selected_student_id)
    bookings = get_student_bookings(selected_student_id)
    stats = get_student_performance_stats(selected_student_id)
    announcements = get_user_announcements(selected_student_id, limit=5)

    return render_template('parent/dashboard.html',
                           students=students,
                           selected_student=selected_student,
                           assignments=assignments,
                           submissions=submissions,
                           bookings=bookings,
                           stats=stats,
                           announcements=announcements)


@app.route('/parent/submissions/<int:student_id>')
@login_required
# @parent_required
def parent_view_submissions(student_id):
    # Verify parent has access to this student
    students = get_students_for_parent(session['user_id'])
    if not any(s['id'] == student_id for s in students):
        abort(403)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                a.title, 
                a.subject, 
                a.deadline, 
                s.submission_time, 
                s.grade, 
                a.total_marks,
                s.feedback,
                s.file_path
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.student_id = %s
            ORDER BY a.deadline DESC
        ''', (student_id,))

        # Convert to list of dictionaries with proper field names
        submissions = []
        for row in cur.fetchall():
            submissions.append({
                'title': row[0],
                'subject': row[1],
                'deadline': row[2],  # This should be a datetime object
                'submitted_at': row[3],
                'marks_obtained': row[4],
                'total_marks': row[5],
                'feedback': row[6],
                'file_path': row[7]
            })

        return render_template('parent/submissions.html',
                               student_id=student_id,
                               submissions=submissions)
    finally:
        cur.close()
        conn.close()


@app.route('/parent/sessions/<int:student_id>')
@login_required
def parent_view_sessions(student_id):
    if session.get('role') != 'parent':
        abort(403)

    # Verify parent has access to this student
    students = get_students_for_parent(session['user_id'])
    if not any(s['id'] == student_id for s in students):
        abort(403)

    bookings = get_student_bookings(student_id)
    upcoming_sessions = get_upcoming_sessions()
    return render_template('parent/sessions.html',
                           student_id=student_id,
                           bookings=bookings,
                           upcoming_sessions=upcoming_sessions)


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


# Add these routes to app.py
@app.route('/admin/parents/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_parent():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # student_ids will be a list of strings (e.g., ['1', '2', '5'])
        student_ids_str_list = request.form.getlist('student_ids')

        existing_user = get_user_by_username(username)
        if existing_user:
            flash('Username already exists', 'danger')
            # If username exists, you still need to render the form with students
            students = get_students()
            return render_template('admin/add_parent.html', students=students)
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            try:
                # Create parent user
                cur.execute('''
                    INSERT INTO users (username, password, role) VALUES (%s, %s, %s) RETURNING id
                ''', (username, generate_password_hash(password), 'parent'))
                parent_id = cur.fetchone()[0]  # type: ignore

                # Link parent to students
                if student_ids_str_list:  # Only iterate if at least one student was selected
                    for student_id_str in student_ids_str_list:
                        # --- IMPORTANT: Validate and convert to integer ---
                        if not student_id_str.strip():  # Check for empty string after stripping whitespace
                            flash(
                                'Invalid (empty) student ID found. Skipping link for an empty ID.', 'warning')
                            continue  # Skip to the next student_id in the list

                        try:
                            # Convert the string to an integer
                            student_id_int = int(student_id_str)
                            cur.execute(
                                'INSERT INTO parent_students (parent_id, student_id) VALUES (%s, %s)',
                                # Use the integer version
                                (parent_id, student_id_int))
                        except ValueError:
                            # This catches cases like 'abc' or malformed data in value attribute
                            flash(
                                f'Invalid student ID format found for "{student_id_str}". Skipping.', 'warning')
                            continue  # Skip to the next student_id in the list
                else:
                    # Optional: If no students were selected, you might want to flash a message
                    # This message won't stop the parent from being created.
                    flash(
                        'Parent created successfully, but no students were linked.', 'info')

                conn.commit()
                flash('Parent and linked students added successfully!', 'success')
                return redirect(url_for('manage_parents'))
            except Exception as e:
                conn.rollback()  # Rollback user creation if linking fails
                flash(
                    f'Error adding parent or linking students: {str(e)}', 'danger')
                # If there's an error, you still need to render the form with students
                students = get_students()
                return render_template('admin/add_parent.html', students=students)
            finally:
                cur.close()
                conn.close()

    # GET request - show form
    students = get_students()
    return render_template('admin/add_parent.html', students=students)


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
