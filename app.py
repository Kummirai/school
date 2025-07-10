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
from helpers import get_students, get_all_categories, get_videos_by_category, get_category_name, get_user_subscription, book_session, cancel_booking, get_student_bookings, get_all_sessions, create_session, get_upcoming_sessions, add_student_to_db, delete_student_by_id, get_assignment_details, submit_assignment, get_student_submission, add_assignment, get_user_announcements, get_submission_for_grading, get_user_by_id, update_request_status, get_leaderboard, get_recent_activities, get_unread_announcements_count, get_request_details, update_session_request_status, update_submission_grade, record_practice_score, send_approval_notification, send_rejection_notification,  get_plan_name, get_plan_price, generate_password_hash, get_all_announcements, get_all_session_requests, save_plan_request, get_subscription_plans, get_session_requests_for_student, get_all_subscriptions, get_assignments_data, get_assignments_for_user, get_exams_data, mark_announcement_read, mark_subscription_as_paid, load_exams_from_json, log_student_activity, add_subscription_to_db, get_all_assignments, create_announcement, create_session_request, get_unsubmitted_assignments_count, get_practice_data, get_student_submissions, get_student_performance_stats, get_students_for_parent, get_student_assignments, get_user_by_username

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


@app.route('/grade/<int:grade_num>/maths/chapter/<int:chapter_num>/<filename>')
def study_guide_page(grade_num, chapter_num, filename):
    # Construct the path to the grade-specific JSON file
    json_file_path = os.path.join(
        app.root_path, 'static', 'data', f'grade{grade_num}_math.json')

    try:
        with open(json_file_path, 'r') as f:
            subject_data = json.load(f)
    except FileNotFoundError:
        abort(404)  # Or render a custom error page

    lesson_data = None
    # Iterate through terms, units, and lessons to find the matching study guide
    for term in subject_data.get('terms', []):
        for unit in term.get('units', []):
            for lesson in unit.get('lessons', []):
                # Check if 'study_guide_filename' exists and matches
                if lesson.get('study_guide_filename') == filename:
                    lesson_data = lesson
                    break
            if lesson_data:
                break
        if lesson_data:
            break

    if not lesson_data:
        abort(404)  # Study guide not found in JSON data

    # Render the specific study guide template
    # Assuming study guides are in templates/grade_X/maths/chapter_Y/
    template_path = f'grade_{grade_num}/maths/chapter_{chapter_num}/{filename}'
    return render_template(template_path, lesson=lesson_data)

# Decorators


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

# Student session booking routes


@app.route('/sessions/book/<int:session_id>', methods=['POST'])
@login_required
def book_session_route(session_id):
    if session.get('role') != 'student':
        flash('Only students can book sessions', 'danger')
        return redirect(url_for('view_sessions'))

    student_id = session.get('user_id')
    if not student_id:
        flash('User not properly authenticated', 'danger')
        return redirect(url_for('view_sessions'))

    if book_session(student_id, session_id):
        flash('Session booked successfully!', 'success')
    else:
        flash(
            'Could not book session. It might be full or you already booked it.', 'danger')
    return redirect(url_for('view_sessions'))


@app.route('/sessions/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking_route(booking_id):
    if cancel_booking(booking_id, session.get('user_id')):
        flash('Booking cancelled successfully', 'success')
    else:
        flash('Could not cancel booking', 'danger')
    return redirect(url_for('view_sessions'))

# Admin session management routes


@app.route('/sessions')
@login_required
def view_sessions():
    student_id = session.get('user_id')
    if not student_id:
        flash('User not properly authenticated', 'danger')
        return redirect(url_for('login'))

    sessions = get_all_sessions()
    student_bookings = get_student_bookings(student_id)
    return render_template('sessions/list.html',
                           sessions=sessions,
                           bookings=student_bookings)

# Add this new route to app.py


@app.route('/admin/sessions/bookings/<int:session_id>')
@login_required
@admin_required
def view_session_bookings(session_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Get session details
    cur.execute(
        'SELECT title FROM tutorial_sessions WHERE id = %s', (session_id,))
    session_title = cur.fetchone()[0]  # type: ignore

    # Get users who booked this session
    cur.execute('''
        SELECT u.id, u.username 
        FROM student_bookings sb
        JOIN users u ON sb.student_id = u.id
        WHERE sb.session_id = %s
    ''', (session_id,))
    booked_users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('admin/session_bookings.html',
                           session_title=session_title,
                           booked_users=booked_users)


@app.route('/admin/sessions')
@login_required
@admin_required
def manage_sessions():
    sessions = get_all_sessions()
    upcoming_sessions = get_upcoming_sessions()
    return render_template('admin/sessions.html',
                           sessions=sessions,
                           upcoming_sessions=upcoming_sessions)


@app.route('/admin/sessions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_session():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        max_students = request.form.get('max_students')

        try:
            create_session(title, description, start_time,
                           end_time, int(max_students))  # type: ignore
            flash('Session created successfully', 'success')
            return redirect(url_for('manage_sessions'))
        except Exception as e:
            flash(f'Error creating session: {str(e)}', 'danger')

    return render_template('admin/add_session.html')


@app.route('/admin/sessions/delete/<int:session_id>')
@login_required
@admin_required
def delete_session(session_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tutorial_sessions WHERE id = %s', (session_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Session deleted successfully', 'success')
    return redirect(url_for('manage_sessions'))

# Add these helper functions


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


@app.route('/admin/tutorials')
@login_required
@admin_required
def manage_tutorials():
    videos = get_all_videos()  # This should return a list of videos
    categories = get_all_categories()  # This should return a list of categories

    # Convert to the structure your template expects
    tutorials_dict = {
        category[1]: {  # category name as key
            # videos for this category
            'videos': [v for v in videos if v[3] == category[1]],
            'id': category[0]  # category id
        }
        for category in categories
    }

    return render_template('admin/tutorials.html',
                           tutorials=tutorials_dict,
                           videos=videos,
                           categories=categories)


@app.route('/admin/tutorials/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_tutorial():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            url = request.form.get('url', '').strip()
            category_id = request.form.get('category_id', '').strip()

            if not all([title, url, category_id]):
                flash('All fields are required', 'danger')
                return redirect(url_for('add_tutorial'))

            add_video(title, url, category_id)
            flash('Tutorial added successfully', 'success')
            return redirect(url_for('manage_tutorials'))

        except Exception as e:
            flash(f'Error adding tutorial: {str(e)}', 'danger')
            return redirect(url_for('add_tutorial'))

    # GET request - show the form
    categories = get_all_categories()
    return render_template('admin/add_tutorial.html', categories=categories)


@app.route('/admin/tutorials/delete/<int:video_id>')
@login_required
@admin_required
def delete_tutorial(video_id):
    delete_video(video_id)
    flash('Tutorial video deleted successfully', 'success')
    return redirect(url_for('manage_tutorials'))

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


@app.route('/math-curriculum')
@login_required
def math_curriculum():
    return render_template('math_curriculum.html')


@app.route('/science_curriculum')
@login_required
def science_curriculum():
    return render_template('science_curriculum.html')


@app.route('/english_curriculum')
@login_required
def english_curriculum():
    return render_template('english_curriculum.html')

# API Endpoints


@app.route('/api/solve-equation', methods=['POST'])
def api_solve_equation():
    data = request.get_json()
    expr = data.get('expression', '')

    try:
        # Use SymPy for more advanced solving
        x = symbols('x')

        if '=' in expr:
            # Handle equations
            parts = expr.split('=')
            lhs = sympy.sympify(parts[0])
            rhs = sympy.sympify(parts[1])
            equation = Eq(lhs, rhs)
            solutions = solve(equation, x)

            # Format solutions
            solution_text = []
            for sol in solutions:
                if sol.is_real:
                    solution_text.append(f"x = {sol.evalf(3)}")
                else:
                    solution_text.append(
                        f"x = {sol.as_real_imag()[0].evalf(3)} + {sol.as_real_imag()[1].evalf(3)}i")

            return jsonify({
                'solution': ', '.join(solution_text),
                'steps': [str(step) for step in sympy.solveset(equation, x, domain=sympy.S.Reals).args]
            })
        else:
            # Handle expressions
            simplified = simplify(expr)
            return jsonify({
                'solution': str(simplified),
                'steps': [f"Simplified: {simplified}"]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/save-equation', methods=['POST'])
@login_required
def api_save_equation():
    data = request.get_json()
    equation = data.get('equation', '')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO saved_equations (user_id, equation) VALUES (%s, %s)',
            (session['user_id'], equation)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get-saved-equations', methods=['GET'])
@login_required
def api_get_saved_equations():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT id, equation FROM saved_equations WHERE user_id = %s ORDER BY created_at DESC',
            (session['user_id'],)
        )
        equations = cur.fetchall()
        cur.close()
        conn.close()
        # Convert to list of dicts
        return jsonify([{'id': eq[0], 'equation': eq[1]} for eq in equations])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-equation/<int:eq_id>', methods=['DELETE'])
@login_required
def api_delete_equation(eq_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'DELETE FROM saved_equations WHERE id = %s AND user_id = %s',
            (eq_id, session['user_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/grade7/maths')
def grade_7_maths():
    try:
        # Load the JSON data with explicit UTF-8 encoding
        with open('static/data/grade7_math.json', 'r', encoding='utf-8') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")
    except UnicodeDecodeError:
        abort(500, description="Invalid file encoding - must be UTF-8")


@app.route('/grade8/maths')
def grade_8_maths():
    try:
        # Load the JSON data
        with open('static/data/grade8_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@app.route('/grade9/maths')
def grade_9_maths():
    try:
        # Load the JSON data
        with open('static/data/grade9_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@app.route('/grade10/maths')
def grade_10_maths():
    try:
        # Load the JSON data
        with open('static/data/grade10_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@app.route('/grade11/maths')
def grade_11_maths():
    try:
        # Load the JSON data
        with open('static/data/grade11_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@app.route('/grade12/maths')
def grade_12_maths():
    try:
        # Load the JSON data
        with open('static/data/grade12_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@app.route('/algebra-calculator')
def algebra_calculator():
    return render_template('algebra_calculator.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['class'] = user.get(
                'class', 'default_class')  # Add this line
            flash('Logged in successfully!', 'success')

            if user['role'] == 'parent':
                return redirect(url_for('parent_dashboard'))
            else:
                return redirect(request.args.get('next') or url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/tutorials')
# @login_required
def tutorials_home():
    return render_template('tutorials/video_tutorials.html')


@app.route('/study_guides')
@login_required
def studyguides_home():
    return render_template('study_guides.html')


@app.route('/tutorials/<int:category_id>')
# @login_required
def tutorial_language(category_id):
    videos = get_videos_by_category(category_id)
    if not videos:
        flash('Tutorial category not found', 'danger')
        return redirect(url_for('tutorials_home'))

    # Get the category name
    category_name = get_category_name(category_id)

    return render_template('tutorials/language.html',
                           videos=videos,
                           category={'id': category_id, 'name': category_name})

# Admin dashboard


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    students = get_students()
    categories = get_all_categories()
    upcoming_sessions = get_upcoming_sessions()

    # Get active subscription count
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE")
    active_subscriptions_count = cur.fetchone()[0]  # type: ignore
    cur.execute('''
            SELECT username, assignment_id, title, subject, deadline, total_marks, created_at
                FROM assignments a
                JOIN assignment_students au ON a.id = au.assignment_id
                JOIN users u ON u.id = au.student_id;
        ''')
    assignments = cur.fetchall()
    cur.close()
    conn.close()

    print(assignments[0][0])
    return render_template('admin/dashboard.html',
                           assignments=assignments,
                           student_count=len(students),
                           category_count=len(categories),
                           upcoming_sessions=upcoming_sessions,
                           active_subscriptions_count=active_subscriptions_count)


@app.route('/admin/students')
@login_required
@admin_required
def manage_students():
    students = get_students()
    return render_template('admin/students.html', students=students)


@app.route('/admin/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = get_user_by_username(username)
        if existing_user:
            flash('Username already exists', 'danger')
        else:
            add_student_to_db(username, password)
            flash('Student added successfully', 'success')
            return redirect(url_for('manage_students'))

    return render_template('admin/add_student.html')


@app.route('/admin/students/delete/<int:student_id>')
@login_required
@admin_required
def delete_student(student_id):
    delete_student_by_id(student_id)
    flash('Student deleted successfully', 'success')
    return redirect(url_for('manage_students'))


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


@app.route('/assignments', methods=['GET'])
@login_required
def student_assignments():
    # Make sure this is how you get the current user's ID
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to view your assignments.', 'warning')
        # Redirect to login if user_id not found
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    assignments = []
    try:
        cur.execute(
            """
            SELECT
            a.id,
            a.title,
            a.description,
            a.subject,
            a.total_marks,
            a.deadline,
            a.content,
            a.created_at,
            s.grade,                                -- Now fetching grade directly from the joined 'submissions' table
            (s.id IS NOT NULL) AS submitted_status  -- Check if a submission exists (s.id will be NULL if no submission)
        FROM
            assignments a
        JOIN
            assignment_students asl ON a.id = asl.assignment_id
        LEFT JOIN
            submissions s ON a.id = s.assignment_id AND asl.student_id = s.student_id -- LEFT JOIN to include all assignments, even without submissions
        WHERE asl.student_id = %s
        ORDER BY a.deadline DESC;
            """,
            (user_id,)  # Pass user_id twice for both EXISTS and WHERE clauses
        )
        for row in cur.fetchall():
            assignments.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'subject': row[3],
                'total_marks': row[4],
                'deadline': row[5],
                # Removed json.loads() since content is already a dict
                'content': row[6] if row[6] else None,
                'created_at': row[7],
                'submitted': row[8],
                'grade': row[9]
            })

        for assignment in assignments:
            assignment['status'] = 'active' if assignment['deadline'] and assignment['deadline'] > datetime.now(
            ) else 'past_deadline'

    except Exception as e:
        print(f"Error fetching student assignments: {e}")
        flash('Could not load your assignments.', 'danger')
    finally:
        cur.close()
        conn.close()

    return render_template('assignments/list.html', assignments=assignments)

# Update the view_assignment route to handle interactive assignments


@app.route('/assignments/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def view_assignment(assignment_id):
    if session.get('role') != 'student':
        flash('Only students can view assignments', 'danger')
        return redirect(url_for('home'))

    assignment = get_assignment_details(assignment_id)
    if not assignment:
        flash('Assignment not found', 'danger')
        return redirect(url_for('view_assignments'))

    submission = get_student_submission(session['user_id'], assignment_id)

    if request.method == 'POST':
        submission_text = request.form.get('submission_text', '')
        file_path = None

        # Handle interactive submission data if present
        interactive_data = None
        # Check if there's interactive content (index 7 is content)
        if assignment[7]:
            try:
                # Get form data for interactive questions
                interactive_data = {}
                assignment_content = json.loads(assignment[7])

                # Extract answers for each interactive question
                for question in assignment_content.get('questions', []):
                    qid = question.get('id')
                    if qid:
                        answer = request.form.get(f'q_{qid}')
                        if answer is not None:
                            interactive_data[qid] = {
                                'question': question.get('question'),
                                'answer': answer,
                                'correct_answer': question.get('correct_answer')
                            }

                interactive_data = json.dumps(interactive_data)
            except Exception as e:
                print(f"Error processing interactive data: {e}")

        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file.filename != '':
                filename = secure_filename(file.filename)  # type: ignore
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

        if submit_assignment(assignment_id, session['user_id'], submission_text, file_path, interactive_data):
            flash('Assignment submitted successfully!', 'success')
            return redirect(url_for('view_assignment', assignment_id=assignment_id))
        else:
            flash('Error submitting assignment', 'danger')

    # Parse assignment content if it exists
    content = None
    if assignment[7]:  # index 7 is the content field
        try:
            content = json.loads(assignment[7])
        except (TypeError, json.JSONDecodeError):
            content = assignment[7]  # fallback to raw content if not JSON

    return render_template('assignments/view.html',
                           assignment={
                               'id': assignment[0],
                               'title': assignment[1],
                               'description': assignment[2],
                               'subject': assignment[3],
                               'total_marks': assignment[4],
                               'deadline': assignment[5],
                               'created_at': assignment[6],
                               'content': content
                           },
                           submission=submission)


# Adjust this route name if yours is different
@app.route('/assignments/submissions')
@login_required  # Assuming this page requires login
def view_submissions():  # Adjust this function name if yours is different
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view your submissions.", "warning")
        return redirect(url_for('login'))

    conn = None
    cur = None
    submissions_data = []
    average_score = None
    monthly_scores = []

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch all submissions for the current user
        cur.execute(
            """
            SELECT
                s.id,
                a.title,
                a.subject,
                s.submission_time,
                s.file_path,
                s.submission_text,
                s.grade,
                a.total_marks,
                s.feedback,
                s.interactive_submission_data
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            WHERE
                s.student_id = %s
            ORDER BY
                s.submission_time DESC;
            """,
            (user_id,)
        )
        for row in cur.fetchall():
            submissions_data.append({
                'id': row[0],
                'title': row[1],
                'subject': row[2],
                'submitted_at': row[3],
                'file_path': row[4],
                'submission_text': row[5],
                'marks_obtained': row[6],
                'total_marks': row[7],
                'feedback': row[8],
                'interactive_submission_data': row[9]
            })

        # Calculate Average Score
        cur.execute(
            """
            SELECT
                SUM(s.grade) AS total_grade_sum,
                SUM(a.total_marks) AS total_possible_marks_sum
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            WHERE
                s.student_id = %s AND s.grade IS NOT NULL;
            """,
            (user_id,)
        )
        avg_row = cur.fetchone()
        if avg_row and avg_row[0] is not None and avg_row[1] is not None and avg_row[1] > 0:
            average_score = (avg_row[0] / avg_row[1]) * 100  # Percentage
            # Round to 2 decimal places
            average_score = round(average_score, 2)
        else:
            average_score = 0  # No graded submissions or total marks is zero

        # Fetch Monthly Scores
        cur.execute(
            """
            SELECT
                EXTRACT(YEAR FROM s.submission_time) AS year,
                EXTRACT(MONTH FROM s.submission_time) AS month,
                SUM(s.grade) AS monthly_grade_sum,
                SUM(a.total_marks) AS monthly_possible_marks_sum
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            WHERE
                s.student_id = %s AND s.grade IS NOT NULL
            GROUP BY
                year, month
            ORDER BY
                year DESC, month DESC;
            """,
            (user_id,)
        )
        for row in cur.fetchall():
            year = int(row[0])
            month = int(row[1])
            monthly_grade_sum = row[2]
            monthly_possible_marks_sum = row[3]

            if monthly_possible_marks_sum and monthly_possible_marks_sum > 0:
                percentage = (monthly_grade_sum /
                              monthly_possible_marks_sum) * 100
                monthly_scores.append({
                    'year': year,
                    'month': month,
                    # Get month name
                    'month_name': datetime(year, month, 1).strftime('%B'),
                    'score': round(percentage, 2)
                })

    except Exception as e:
        print(f"Error fetching submission data: {e}")
        flash("Could not load your submission data.", "danger")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template(
        'assignments/submissions.html',
        submissions=submissions_data,
        average_score=average_score,
        monthly_scores=monthly_scores
    )


@app.route('/admin/assignments/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_assignment_route():
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            subject = request.form.get('subject', '').strip()
            total_marks = request.form.get('total_marks', '').strip()
            deadline_str = request.form.get('deadline', '').strip()
            assign_to = request.form.get('assign_to')  # 'all' or 'selected'
            selected_users = request.form.getlist(
                'selected_users[]') if assign_to == 'selected' else []

            # Validate required fields
            if not all([title, description, subject, total_marks, deadline_str]):
                flash('All fields are required', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Convert and validate total marks
            try:
                total_marks = int(total_marks)
                if total_marks <= 0:
                    flash('Total marks must be positive', 'danger')
                    return redirect(url_for('add_assignment_route'))
            except ValueError:
                flash('Total marks must be a number', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Validate deadline
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
                if deadline <= datetime.utcnow():
                    flash('Deadline must be in the future', 'danger')
                    return redirect(url_for('add_assignment_route'))
            except ValueError:
                flash('Invalid deadline format', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Get user IDs based on selection
            if assign_to == 'all':
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    'SELECT id FROM users WHERE role = %s', ('student',))
                user_ids = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
            elif assign_to == 'selected' and selected_users:
                user_ids = [int(user_id) for user_id in selected_users]
            else:
                flash('Please select at least one student', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Create assignment
            assignment_id = add_assignment(
                title=title,
                description=description,
                subject=subject,
                total_marks=total_marks,
                deadline=deadline,
                assigned_students_ids=user_ids
            )

            flash('Assignment created successfully!', 'success')
            return redirect(url_for('manage_assignments'))

        except Exception as e:
            flash(f'Error creating assignment: {str(e)}', 'danger')
            app.logger.error(f"Assignment creation error: {str(e)}")

    # GET request - show form with students
    students = get_students()
    return render_template('admin/assignments/add.html', students=students)


@app.route('/admin/assignments')
@login_required
@admin_required
def manage_assignments():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT a.id, a.title, a.subject, a.deadline, a.total_marks, a.created_at,
                   COUNT(s.student_id) as assigned_count,
                   COUNT(s.id) as submission_count
            FROM assignments a
            LEFT JOIN assignment_students au ON a.id = au.assignment_id
            LEFT JOIN submissions s ON a.id = s.assignment_id
            GROUP BY a.id
            ORDER BY a.deadline
        ''')

        assignments = []
        for row in cur.fetchall():
            assignments.append({
                'id': row[0],
                'title': row[1],
                'subject': row[2],
                'deadline': row[3],
                'total_marks': row[4],
                'created_at': row[5],
                'assigned_count': row[6],
                'submission_count': row[7]
            })

        return render_template('admin/assignments/list.html', assignments=assignments)
    finally:
        cur.close()
        conn.close()


@app.route('/admin/assignments/<int:assignment_id>/submissions')
@login_required
@admin_required
def view_assignment_submissions(assignment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get assignment details
        cur.execute(
            'SELECT id, title, total_marks FROM assignments WHERE id = %s', (assignment_id,))
        assignment = cur.fetchone()
        if not assignment:
            flash('Assignment not found', 'danger')
            return redirect(url_for('manage_assignments'))

        # Get submissions with student IDs
        cur.execute('''
            SELECT u.username, s.submission_time, s.grade, u.id as student_id, s.feedback
            FROM submissions s
            JOIN users u ON s.student_id = u.id
            WHERE s.assignment_id = %s
            ORDER BY s.submission_time DESC
        ''', (assignment_id,))
        submissions = cur.fetchall()

        return render_template('admin/assignments/submissions.html',
                               assignment_title=assignment[1],
                               assignment_id=assignment_id,
                               submissions=submissions)
    finally:
        cur.close()
        conn.close()


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


@app.route('/admin/assignments/<int:assignment_id>/submissions/<int:student_id>/submit-grade', methods=['POST'])
@login_required
@admin_required
def submit_grade(assignment_id, student_id):
    marks_obtained = request.form.get('marks_obtained')
    feedback = request.form.get('feedback', '')

    try:
        marks_obtained = float(marks_obtained)  # type: ignore

        # Get assignment to validate max marks
        assignment = get_assignment_details(assignment_id)
        if not assignment:
            flash('Assignment not found', 'danger')
            return redirect(url_for('manage_assignments'))

        # total_marks is at index 4
        if marks_obtained < 0 or marks_obtained > assignment[4]:
            flash('Invalid marks value', 'danger')
            return redirect(url_for('grade_submission', assignment_id=assignment_id, student_id=student_id))

        if update_submission_grade(assignment_id, student_id, marks_obtained, feedback):
            flash('Grade submitted successfully', 'success')
        else:
            flash('Error submitting grade', 'danger')
    except ValueError:
        flash('Invalid marks format', 'danger')

    return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))

# Leaderboard routes


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


@app.route('/exam_practice')
@login_required  # Assuming exam practice requires login
# @student_required # Optional: if only students should access
def exam_practice():
    """Renders the exam practice page with data from exams.json."""
    exams = load_exams_from_json(
        'static/js/exams.json')  # Adjust path if needed
    print("DEBUG: Loaded exams:", exams)
    return render_template('exam_practice.html', exams=exams)


@app.route('/exam/<int:exam_id>')
@login_required  # Ensure user is logged in to take exams
# @student_required # Optional: restrict to students
def take_exam(exam_id):
    """Loads a specific exam and renders the exam-taking page."""
    exams = load_exams_from_json('static/js/exams.json')  # Load all exams

    # Find the exam with the matching ID
    selected_exam = None
    for exam in exams:
        if exam.get('id') == exam_id:
            selected_exam = exam
            break

    if selected_exam:
        return render_template('take_exam.html', exam=selected_exam)
    else:
        flash('Exam not found.', 'danger')
        # Redirect back if exam ID is invalid
        return redirect(url_for('exam_practice'))


@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
@login_required  # Ensure user is logged in
# @student_required # Optional: restrict to students
def submit_exam(exam_id):
    """Handles the submission of an exam, grades it, saves the result, and logs the activity."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    # Load all exams from the JSON file
    exams = load_exams_from_json('static/js/exams.json')

    # Find the specific exam the user submitted
    selected_exam = next(
        (exam for exam in exams if exam.get('id') == exam_id), None)

    if not selected_exam:
        flash('Exam not found.', 'danger')
        return redirect(url_for('exam_practice'))

    # Get user's submitted answers
    user_answers = request.form

    # Grade the exam
    correct_answers_count = 0
    total_questions = len(selected_exam.get('questions', []))

    if total_questions > 0:
        correct_answers_count = sum(
            1 for question in selected_exam.get('questions', [])
            if str(user_answers.get(f"question_{question.get('id')}")) == str(question.get('correct_answer')))

        score = (correct_answers_count / total_questions) * 100
    else:
        score = 0

    print(f"User {user_id} submitted Exam {exam_id}. Score: {score:.2f}% ({correct_answers_count}/{total_questions} correct)")

    # Save the result to the database
    conn = get_db_connection()
    cur = conn.cursor()
    result_id = None

    try:
        # Save exam result
        cur.execute('''
            INSERT INTO exam_results (user_id, exam_id, score, total_questions, completion_time)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id;
        ''', (user_id, exam_id, score, total_questions))
        result_id = cur.fetchone()[0]  # type: ignore
        # Log the exam submission activity
        cur.execute('''
            INSERT INTO student_activities 
            (student_id, activity_type, description, icon, metadata)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            user_id,
            'exam',
            f"Completed {selected_exam.get('name', 'Exam')}",
            'file-certificate',
            json.dumps({
                'exam_id': exam_id,
                'score': float(score),
                'correct_answers': correct_answers_count,
                'total_questions': total_questions,
                'result_id': result_id
            })
        ))

        conn.commit()
        flash('Exam submitted and graded successfully!', 'success')
        return redirect(url_for('exam_results', result_id=result_id))

    except Exception as e:
        conn.rollback()
        print(f"Error processing exam submission: {e}")
        flash('Error processing exam submission.', 'danger')
        return redirect(url_for('exam_practice'))
    finally:
        cur.close()
        conn.close()

# Placeholder route for displaying exam results


@app.route('/exam_results/<int:result_id>')
@login_required
def exam_results(result_id):
    """Fetches and displays the results of a completed exam."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    result = None
    try:
        # Fetch the specific exam result from the database
        cur.execute('''
            SELECT id, user_id, exam_id, score, total_questions, completion_time
            FROM exam_results
            WHERE id = %s AND user_id = %s; -- Ensure user can only see their own results
        ''', (result_id, user_id))
        result = cur.fetchone()

    except Exception as e:
        print(f"Error fetching exam result {result_id}: {e}")
        flash('Error fetching exam results.', 'danger')
        return redirect(url_for('exam_practice'))  # Redirect if fetching fails
    finally:
        cur.close()
        conn.close()

    if not result:
        flash('Exam result not found or you do not have permission to view it.', 'danger')
        # Redirect if result not found
        return redirect(url_for('exam_practice'))

    # Unpack result data
    result_id, result_user_id, exam_json_id, score, total_questions, completion_time = result

    # Load the exam details from the JSON file using the exam_json_id
    exams = load_exams_from_json('static/js/exams.json')
    exam_details = None
    for exam in exams:
        if exam.get('id') == exam_json_id:
            exam_details = exam
            break

    if not exam_details:
        # This case means the exam data in the JSON was changed/removed after the user took it
        flash(
            f'Exam details for result ID {result_id} not found in JSON file.', 'warning')
        # We can still show the basic score, but not question-by-question review
        return render_template('exam_results.html',
                               result=result,  # Pass the basic result data
                               exam_details=None)  # Indicate exam details are missing

    # Pass both the result data and exam details to the template
    return render_template('exam_results.html',
                           result=result,
                           exam_details=exam_details)

# Announcement routes


@app.route('/announcements')
@login_required
def view_announcements():
    announcements = get_user_announcements(session['user_id'])
    return render_template('announcements/list.html', announcements=announcements)


@app.route('/announcements/<int:announcement_id>')
@login_required
def view_announcement(announcement_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get the announcement and mark it as read
        cur.execute('''
            SELECT a.id, a.title, a.message, a.created_at, u.username as created_by
            FROM announcements a
            JOIN users u ON a.created_by = u.id
            JOIN user_announcements ua ON a.id = ua.announcement_id
            WHERE ua.user_id = %s AND a.id = %s
        ''', (session['user_id'], announcement_id))

        announcement = cur.fetchone()
        if not announcement:
            flash('Announcement not found', 'danger')
            return redirect(url_for('view_announcements'))

        # Mark as read
        mark_announcement_read(announcement_id, session['user_id'])

        return render_template('announcements/view.html', announcement={
            'id': announcement[0],
            'title': announcement[1],
            'message': announcement[2],
            'created_at': announcement[3],
            'created_by': announcement[4]
        })
    except Exception as e:
        flash('Error viewing announcement', 'danger')
        return redirect(url_for('view_announcements'))
    finally:
        cur.close()
        conn.close()

# Admin announcement management


@app.route('/admin/announcements')
@login_required
@admin_required
def manage_announcements():
    announcements = get_all_announcements()
    return render_template('admin/announcements/list.html', announcements=announcements)


@app.route('/admin/announcements/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_announcement():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        send_to = request.form.getlist('send_to')  # List of user IDs or 'all'

        if not title or not message:
            flash('Title and message are required', 'danger')
            return redirect(url_for('add_announcement'))

        try:
            # If "all" is selected, send to all students
            user_ids = None if 'all' in send_to else [
                int(user_id) for user_id in send_to]

            create_announcement(
                title=title,
                message=message,
                created_by=session['user_id'],
                user_ids=user_ids
            )

            flash('Announcement created successfully!', 'success')
            return redirect(url_for('manage_announcements'))
        except Exception as e:
            flash(f'Error creating announcement: {str(e)}', 'danger')
            return redirect(url_for('add_announcement'))

    # GET request - show form
    students = get_students()
    return render_template('admin/announcements/add.html', students=students)


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



@app.route('/admin/parents/edit/<int:parent_id>', methods=['GET', 'POST']) #type: ignore
@login_required
@admin_required
def edit_parent(parent_id):
    conn = get_db_connection()
    cur = conn.cursor()
    parent = None  # Initialize parent variable

    try:
        # GET request: Display the current parent's data in the form
        if request.method == 'GET':
            cur.execute(
                "SELECT id, username FROM users WHERE id = %s AND role = 'parent'", (parent_id,))
            parent = cur.fetchone()

            if not parent:
                flash('Parent not found.', 'danger')
                return redirect(url_for('manage_parents'))

            # Fetch students linked to this parent
            cur.execute('''
                SELECT s.id, s.username
                FROM users s
                JOIN parent_students ps ON s.id = ps.student_id
                WHERE ps.parent_id = %s
            ''', (parent_id,))
            linked_students = [row[0] for row in cur.fetchall(
            )]  # Get a list of IDs of linked students

            all_students = get_students()  # Get all students for the checkboxes

            return render_template('admin/edit_parent.html',
                                   parent=parent,
                                   all_students=all_students,  # Pass all students for checkbox list
                                   linked_students=linked_students)  # Pass linked student IDs to pre-check checkboxes

        # POST request: Process the form submission to update parent
        elif request.method == 'POST':
            new_username = request.form['username']
            # Password can be optional for edit
            new_password = request.form.get('password')
            student_ids_str_list = request.form.getlist('student_ids')

            # Check if username already exists for another user
            cur.execute(
                "SELECT id FROM users WHERE username = %s AND id != %s", (new_username, parent_id))
            if cur.fetchone():
                flash('Username already exists for another user.', 'danger')
                # Re-render the form with current data and students
                cur.execute(
                    "SELECT id, username FROM users WHERE id = %s AND role = 'parent'", (parent_id,))
                parent = cur.fetchone()
                cur.execute('''
                    SELECT s.id, s.username FROM users s JOIN parent_students ps ON s.id = ps.student_id WHERE ps.parent_id = %s
                ''', (parent_id,))
                linked_students = [row[0] for row in cur.fetchall()]
                all_students = get_students()
                return render_template('admin/edit_parent.html',
                                       parent=parent,
                                       all_students=all_students,
                                       linked_students=linked_students)

            # Update parent user data
            if new_password:
                hashed_password = generate_password_hash(new_password)
                cur.execute("UPDATE users SET username = %s, password = %s WHERE id = %s",
                            (new_username, hashed_password, parent_id))
            else:
                cur.execute("UPDATE users SET username = %s WHERE id = %s",
                            (new_username, parent_id))

            # Update parent-student links:
            # 1. Delete all existing links for this parent
            cur.execute(
                "DELETE FROM parent_students WHERE parent_id = %s", (parent_id,))

            # 2. Insert new links based on selected checkboxes
            if student_ids_str_list:
                for student_id_str in student_ids_str_list:
                    if not student_id_str.strip():
                        flash(
                            'Invalid (empty) student ID found. Skipping link for an empty ID.', 'warning')
                        continue
                    try:
                        student_id_int = int(student_id_str)
                        cur.execute("INSERT INTO parent_students (parent_id, student_id) VALUES (%s, %s)",
                                    (parent_id, student_id_int))
                    except ValueError:
                        flash(
                            f'Invalid student ID format found for "{student_id_str}". Skipping.', 'warning')
                        continue

            conn.commit()
            flash('Parent updated successfully!', 'success')
            return redirect(url_for('manage_parents'))

    except Exception as e:
        conn.rollback()
        flash(f'Error editing parent: {str(e)}', 'danger')
        # On error, try to re-render the form with existing data if available
        if parent:
            all_students = get_students()
            cur.execute('''
                SELECT s.id, s.username FROM users s JOIN parent_students ps ON s.id = ps.student_id WHERE ps.parent_id = %s
            ''', (parent_id,))
            linked_students = [row[0] for row in cur.fetchall()]
            return render_template('admin/edit_parent.html',
                                   parent=parent,
                                   all_students=all_students,
                                   linked_students=linked_students)
        # Fallback if parent not found on error
        return redirect(url_for('manage_parents'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# In your app.py file, usually alongside your other admin routes


@app.route('/admin/parents/<int:parent_id>/link_students', methods=['GET'])
@login_required
@admin_required
def link_parent_student_ui(parent_id):
    conn = get_db_connection()
    cur = conn.cursor()
    parent_info = None
    all_students = []
    linked_student_ids = []

    try:
        # Get parent details to display on the page
        cur.execute(
            "SELECT id, username FROM users WHERE id = %s AND role = 'parent'", (parent_id,))
        parent_info = cur.fetchone()

        if not parent_info:
            flash('Parent not found.', 'danger')
            return redirect(url_for('manage_parents'))

        # Get all students to populate the checkboxes
        # Assuming get_students() fetches all students for the admin
        all_students = get_students()

        # Get the IDs of students already linked to this parent
        cur.execute('''
            SELECT student_id FROM parent_students WHERE parent_id = %s
        ''', (parent_id,))
        linked_student_ids = [row[0] for row in cur.fetchall()]

        return render_template('admin/link_parent_student.html',
                               parent=parent_info,
                               all_students=all_students,
                               linked_student_ids=linked_student_ids)

    except Exception as e:
        flash(f'Error loading student linking page: {str(e)}', 'danger')
        return redirect(url_for('manage_parents'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# In your app.py file


@app.route('/admin/parents/<int:parent_id>/update_links', methods=['POST'])
@login_required
@admin_required
def update_parent_student_links(parent_id):
    # Get the selected student IDs as strings
    student_ids_str_list = request.form.getlist('student_ids')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Step 1: Delete all existing links for this parent
        cur.execute(
            "DELETE FROM parent_students WHERE parent_id = %s", (parent_id,))

        # Step 2: Insert new links based on the submitted data
        if student_ids_str_list:
            for student_id_str in student_ids_str_list:
                if not student_id_str.strip():
                    flash(
                        f'Invalid (empty) student ID found in submission. Skipping.', 'warning')
                    continue
                try:
                    student_id_int = int(student_id_str)
                    cur.execute("INSERT INTO parent_students (parent_id, student_id) VALUES (%s, %s)",
                                (parent_id, student_id_int))
                except ValueError:
                    flash(
                        f'Invalid student ID format "{student_id_str}" in submission. Skipping.', 'warning')
                    continue
        else:
            # No students were selected, so all previous links for this parent have been removed
            flash(
                'No students selected. All previous links for this parent have been removed.', 'info')

        conn.commit()
        flash('Parent-student links updated successfully!', 'success')
        # Redirect back to the parent management page
        return redirect(url_for('manage_parents'))

    except Exception as e:
        conn.rollback()
        flash(f'Error updating parent-student links: {str(e)}', 'danger')
        # On error, redirect back to the linking UI page to allow retrying
        return redirect(url_for('link_parent_student_ui', parent_id=parent_id))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@app.route('/admin/parents')
@login_required
@admin_required
def manage_parents():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get all parents with their linked students
        cur.execute('''
            SELECT u.id, u.username, 
                   STRING_AGG(s.username, ', ') as students,
                   COUNT(ps.student_id) as student_count
            FROM users u
            LEFT JOIN parent_students ps ON u.id = ps.parent_id
            LEFT JOIN users s ON ps.student_id = s.id
            WHERE u.role = 'parent'
            GROUP BY u.id
            ORDER BY u.username
        ''')
        parents = [{
            'id': row[0],
            'username': row[1],
            'students': row[2] or 'No students linked',
            'student_count': row[3]
        } for row in cur.fetchall()]

        return render_template('admin/parents.html', parents=parents)
    finally:
        cur.close()
        conn.close()


@app.route('/admin/parents/link', methods=['POST'])
@login_required
@admin_required
def link_parent_student():
    parent_id = request.form['parent_id']
    student_id = request.form['student_id']
    action = request.form['action']  # 'link' or 'unlink'

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if action == 'link':
            cur.execute('''
                INSERT INTO parent_students (parent_id, student_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            ''', (parent_id, student_id))
        else:
            cur.execute('''
                DELETE FROM parent_students
                WHERE parent_id = %s AND student_id = %s
            ''', (parent_id, student_id))

        conn.commit()
        flash('Relationship updated successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating relationship: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('manage_parents'))


@app.route('/parent/assignments')
@login_required
# @parent_required # If you have a specific decorator for parent role
def parent_view_assignments():
    parent_id = session.get('user_id')
    if not parent_id:
        flash('You must be logged in as a parent to view assignments.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Again, using DictCursor is good for fetching parent's students
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    students_with_assignments = []
    try:
        # Get all students linked to this parent
        cur.execute('''
            SELECT u.id AS student_id, u.username AS student_username
            FROM users u
            JOIN parent_students ps ON u.id = ps.student_id
            WHERE ps.parent_id = %s AND u.role = 'student'
            ORDER BY u.username;
        ''', (parent_id,))
        linked_students = cur.fetchall()

        for student_info in linked_students:
            student_id = student_info['student_id']
            student_username = student_info['student_username']

            assignments_for_student = get_student_assignments(student_id)

            students_with_assignments.append({
                'id': student_id,
                'username': student_username,
                'assignments': assignments_for_student
            })

    except Exception as e:
        flash(f'Error loading assignments: {str(e)}', 'danger')
        print(f"Error in parent_view_assignments route: {e}")  # For debugging
        # Redirect to a safe page on error
        return redirect(url_for('parent_dashboard'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('parent/assignments.html', students_with_assignments=students_with_assignments)

# Student routes


@app.route('/sessions/request', methods=['GET', 'POST'])
@login_required
def create_session_request_route():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        preferred_time_str = request.form.get('preferred_time')

        if not all([title, category]):
            flash('Title and category are required', 'danger')
            return redirect(url_for('create_session_request_route'))

        try:
            preferred_time = datetime.strptime(
                preferred_time_str, '%Y-%m-%dT%H:%M') if preferred_time_str else None
            request_id = create_session_request(
                student_id=session['user_id'],
                title=title,
                description=description,
                category=category,
                preferred_time=preferred_time
            )

            if request_id:
                flash('Session request submitted successfully!', 'success')
                return redirect(url_for('view_my_session_requests'))
            else:
                flash('Error submitting request', 'danger')
        except ValueError:
            flash('Invalid date/time format', 'danger')

    return render_template('sessions/create.html')


@app.route('/sessions/my-requests')
@login_required
def view_my_session_requests():
    requests = get_session_requests_for_student(session['user_id'])
    return render_template('student/session_requests.html', requests=requests)

# Admin routes


@app.route('/admin/session-requests')
@login_required
@admin_required
def manage_session_requests():
    requests = get_all_session_requests()
    return render_template('admin/session_requests.html', requests=requests)


@app.route('/admin/session-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_session_request(request_id):
    notes = request.form.get('notes', '')
    if update_session_request_status(request_id, 'approved', session['user_id'], notes):
        flash('Session request approved and scheduled!', 'success')
    else:
        flash('Error approving request', 'danger')
    return redirect(url_for('manage_session_requests'))


@app.route('/admin/session-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_session_request(request_id):
    notes = request.form.get('notes', '')
    if update_session_request_status(request_id, 'rejected', session['user_id'], notes):
        flash('Session request rejected', 'success')
    else:
        flash('Error rejecting request', 'danger')
    return redirect(url_for('manage_session_requests'))


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
