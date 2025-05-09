from functools import wraps
from flask import Flask, flash, redirect, render_template, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
from flask import render_template
from flask_login import current_user, login_required


# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
#app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key-for-development')


# Configure upload folder in your app
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not app.secret_key:
    raise ValueError("No secret key set for Flask application")

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT'),
        sslmode='require'
    )
    return conn

def initialize_database():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role VARCHAR(50) NOT NULL
    )
    ''')
    
    # Create tutorial_categories table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tutorial_categories (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL
    )
    ''')

      # Add these new tables for assignment system
    cur.execute('''
    CREATE TABLE IF NOT EXISTS assignments (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        subject VARCHAR(100) NOT NULL,
        total_marks INTEGER NOT NULL,
        deadline TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Add this new table for assignment-user relationships
    cur.execute('''
        CREATE TABLE IF NOT EXISTS assignment_users (
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (assignment_id, user_id)
        )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS assignment_submissions (
        id SERIAL PRIMARY KEY,
        assignment_id INTEGER REFERENCES assignments(id) ON DELETE CASCADE,
        student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        submission_text TEXT,
        file_path VARCHAR(255),
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        marks_obtained INTEGER,
        feedback TEXT,
        CONSTRAINT unique_submission UNIQUE (assignment_id, student_id)
    )
    ''')
    
    # Create tutorial_videos table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tutorial_videos (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        category_id INTEGER NOT NULL REFERENCES tutorial_categories(id) ON DELETE CASCADE
    )
    ''')

    # Create tutorial_sessions table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tutorial_sessions (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        max_students INTEGER NOT NULL
    )
    ''')

    # Create student_bookings table
    # In your initialize_database() function
    cur.execute('''
    CREATE TABLE IF NOT EXISTS student_bookings (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        session_id INTEGER NOT NULL REFERENCES tutorial_sessions(id) ON DELETE CASCADE,
        booking_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'confirmed',
        CONSTRAINT unique_booking UNIQUE (student_id, session_id)
    )
    ''')

    conn.commit()

    # Check if there are any users
    cur.execute('SELECT COUNT(*) FROM users')
    user_count = cur.fetchone()[0]

    if user_count == 0:
        # Insert default admin user
        default_admin_username = 'admin'
        default_admin_password = generate_password_hash('admin123')
        cur.execute('''
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, %s)
        ''', (default_admin_username, default_admin_password, 'admin'))
        conn.commit()
        print("✅ Default admin user created: admin / admin123")

    cur.close()
    conn.close()



# Helpers
# Add this helper function to get user by ID
def get_user_by_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user:
        return {'id': user[0], 'username': user[1]}

def get_submission_for_grading(assignment_id, student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get submission details
        cur.execute('''
            SELECT s.id, s.submission_text, s.file_path, s.submitted_at, 
                   s.marks_obtained, s.feedback, u.username
            FROM assignment_submissions s
            JOIN users u ON s.student_id = u.id
            WHERE s.assignment_id = %s AND s.student_id = %s
        ''', (assignment_id, student_id))
        submission = cur.fetchone()
        
        if not submission:
            return None
            
        # Get assignment details
        cur.execute('SELECT id, title, total_marks FROM assignments WHERE id = %s', (assignment_id,))
        assignment = cur.fetchone()
        
        return {
            'submission': {
                'id': submission[0],
                'submission_text': submission[1],
                'file_path': submission[2],
                'submitted_at': submission[3],
                'marks_obtained': submission[4],
                'feedback': submission[5],
                'username': submission[6]
            },
            'assignment': {
                'id': assignment[0],
                'title': assignment[1],
                'total_marks': assignment[2]
            }
        }
    finally:
        cur.close()
        conn.close()

def update_submission_grade(assignment_id, student_id, marks_obtained, feedback):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE assignment_submissions
            SET marks_obtained = %s, feedback = %s
            WHERE assignment_id = %s AND student_id = %s
        ''', (marks_obtained, feedback, assignment_id, student_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error updating grade: {str(e)}")
        return False
    finally:
        cur.close()
        conn.close()

def get_all_assignments():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM assignments ORDER BY deadline')
    assignments = cur.fetchall()
    cur.close()
    conn.close()
    return assignments


def get_assignments_for_user(user_id):
    """Get assignments assigned to a specific user"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT a.id, a.title, a.subject, a.deadline, a.total_marks, a.description
            FROM assignments a
            JOIN assignment_users au ON a.id = au.assignment_id
            WHERE au.user_id = %s
            ORDER BY a.deadline
        ''', (user_id,))
        
        assignments = []
        for row in cur.fetchall():
            assignments.append({
                'id': row[0],
                'title': row[1],
                'subject': row[2],
                'deadline': row[3],
                'total_marks': row[4],
                'description': row[5],
                'status': 'active' if row[3] > datetime.utcnow() else 'expired'
            })
            
        return assignments
    except Exception as e:
        app.logger.error(f"Error getting assignments for user {user_id}: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()

def add_assignment(title, description, subject, total_marks, deadline, assigned_users):
    """Create a new assignment and assign it to specific users"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Create the assignment
        cur.execute('''
            INSERT INTO assignments 
            (title, description, subject, total_marks, deadline)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (title, description, subject, total_marks, deadline))
        assignment_id = cur.fetchone()[0]
        
        # Assign to selected users
        for user_id in assigned_users:
            cur.execute('''
                INSERT INTO assignment_users (assignment_id, user_id)
                VALUES (%s, %s)
            ''', (assignment_id, user_id))
        
        conn.commit()
        return assignment_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_assignment_details(assignment_id):
    """Get full details for a specific assignment"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT id, title, description, subject,
                   total_marks, deadline, created_at
            FROM assignments
            WHERE id = %s
        ''', (assignment_id,))
        assignment = cur.fetchone()
        return assignment
    finally:
        cur.close()
        conn.close()

def get_student_submission(student_id, assignment_id):
    """Get a student's submission for an assignment"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT id, submission_text, file_path, submitted_at, 
                   marks_obtained, feedback
            FROM assignment_submissions
            WHERE student_id = %s AND assignment_id = %s
        ''', (student_id, assignment_id))
        submission = cur.fetchone()
        return submission
    finally:
        cur.close()
        conn.close()

def get_student_submissions(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT a.title, a.subject, a.deadline, s.submitted_at, 
               s.marks_obtained, a.total_marks, s.feedback, s.file_path
        FROM assignment_submissions s
        JOIN assignments a ON s.assignment_id = a.id
        WHERE s.student_id = %s
        ORDER BY a.deadline DESC
    ''', (student_id,))
    
    # Convert tuples to dictionaries with meaningful keys
    submissions = []
    for row in cur.fetchall():
        submissions.append({
            'title': row[0],
            'subject': row[1],
            'deadline': row[2],
            'submitted_at': row[3],
            'marks_obtained': row[4],
            'total_marks': row[5],
            'feedback': row[6],
            'file_path': row[7]
        })
    
    cur.close()
    conn.close()
    return submissions

def submit_assignment(assignment_id, student_id, submission_text, file_path=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO assignment_submissions 
            (assignment_id, student_id, submission_text, file_path)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (assignment_id, student_id) 
            DO UPDATE SET submission_text = EXCLUDED.submission_text,
                          file_path = EXCLUDED.file_path,
                          submitted_at = CURRENT_TIMESTAMP
        ''', (assignment_id, student_id, submission_text, file_path))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error submitting assignment: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, username, password, role FROM users WHERE username = %s', (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user:
        return {
            'id': user[0],
            'username': user[1],
            'password': user[2],
            'role': user[3]
        }
    return None

def get_student_bookings(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sb.id, ts.title, ts.start_time, ts.end_time
        FROM student_bookings sb
        JOIN tutorial_sessions ts ON sb.session_id = ts.id
        WHERE sb.student_id = %s AND ts.start_time > NOW()
        ORDER BY ts.start_time
    ''', (student_id,))
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return bookings

def get_all_categories():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM tutorial_categories')
    categories = cur.fetchall()
    cur.close()
    conn.close()
    return categories

def get_category_name(category_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM tutorial_categories WHERE id = %s', (category_id,))
    category = cur.fetchone()
    cur.close()
    conn.close()
    return category[0] if category else "Unknown Category"

def get_videos_by_category(category_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, title, url FROM tutorial_videos WHERE category_id = %s', (category_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Convert to list of dictionaries
    videos = [
        {'id': row[0], 'title': row[1], 'url': row[2]}
        for row in rows
    ]
    return videos

def get_students():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, username FROM users WHERE role = %s', ('student',))
    students = cur.fetchall()
    cur.close()
    conn.close()
    return students

def add_student_to_db(username, password):  # Changed from add_student
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO users (username, password, role) VALUES (%s, %s, %s)',
                (username, generate_password_hash(password), 'student'))
    conn.commit()
    cur.close()
    conn.close()

def delete_student_by_id(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM users WHERE id = %s AND role = %s', (student_id, 'student'))
    conn.commit()
    cur.close()
    conn.close()

def get_all_sessions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT ts.id, ts.title, ts.description, ts.start_time, ts.end_time, ts.max_students,
            COUNT(sb.id) as booked_count
        FROM tutorial_sessions ts
        LEFT JOIN student_bookings sb ON ts.id = sb.session_id
        GROUP BY ts.id
        ORDER BY ts.start_time
    ''')
    sessions = cur.fetchall()
    cur.close()
    conn.close()
    return sessions

def get_upcoming_sessions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT ts.id, ts.title, ts.start_time, ts.end_time,
               COUNT(sb.id) as booked_count, ts.max_students
        FROM tutorial_sessions ts
        LEFT JOIN student_bookings sb ON ts.id = sb.session_id
        WHERE ts.start_time > NOW()
        GROUP BY ts.id
        ORDER BY ts.start_time
        LIMIT 5
    ''')
    sessions = cur.fetchall()
    cur.close()
    conn.close()
    return sessions

def get_student_bookings(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sb.id, ts.title, ts.start_time, ts.end_time
        FROM student_bookings sb
        JOIN tutorial_sessions ts ON sb.session_id = ts.id
        WHERE sb.student_id = %s AND ts.start_time > NOW()
        ORDER BY ts.start_time
    ''', (student_id,))
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return bookings

def create_session(title, description, start_time, end_time, max_students):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO tutorial_sessions (title, description, start_time, end_time, max_students)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    ''', (title, description, start_time, end_time, max_students))
    session_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return session_id

def book_session(student_id, session_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if session exists and has available spots
    cur.execute('''
        SELECT COUNT(sb.id), ts.max_students
        FROM tutorial_sessions ts
        LEFT JOIN student_bookings sb ON ts.id = sb.session_id
        WHERE ts.id = %s
        GROUP BY ts.id
    ''', (session_id,))
    result = cur.fetchone()
    
    if not result or result[0] >= result[1]:
        cur.close()
        conn.close()
        return False
    
    # Check if student already booked this session
    cur.execute('''
        SELECT id FROM student_bookings 
        WHERE student_id = %s AND session_id = %s
    ''', (student_id, session_id))
    if cur.fetchone():
        cur.close()
        conn.close()
        return False
    
    # Create booking
    cur.execute('''
        INSERT INTO student_bookings (student_id, session_id)
        VALUES (%s, %s)
    ''', (student_id, session_id))
    conn.commit()
    cur.close()
    conn.close()
    return True

def cancel_booking(booking_id, student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        DELETE FROM student_bookings
        WHERE id = %s AND student_id = %s
    ''', (booking_id, student_id))
    affected_rows = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return affected_rows > 0
    

@app.context_processor
def inject_categories():
    if 'username' in session:
        return {'categories': get_all_categories()}
    return {}

@app.route('/video-conference')
def video_conference():
    return render_template('live_session.html')  # We'll create this file next

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
        flash('Could not book session. It might be full or you already booked it.', 'danger')
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
    cur.execute('SELECT title FROM tutorial_sessions WHERE id = %s', (session_id,))
    session_title = cur.fetchone()[0]
    
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
            create_session(title, description, start_time, end_time, int(max_students))
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
            'videos': [v for v in videos if v[3] == category[1]],  # videos for this category
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
    return render_template('home.html')

#Curriculums
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
            session['class'] = user.get('class', 'default_class')  # Add this line
            flash('Logged in successfully!', 'success')
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
@login_required
def tutorials_home():
    categories = get_all_categories()
    # Create a dictionary with category data
    tutorials_dict = {
        category[1]: {  # Using category name as key
            'id': category[0],  # category id
            'videos': get_videos_by_category(category[0])  # videos for this category
        }
        for category in categories
    }
    return render_template('tutorials/index.html', tutorials=tutorials_dict, categories=categories)

@app.route('/tutorials/<int:category_id>')
@login_required
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
    return render_template('admin/dashboard.html', 
                         student_count=len(students), 
                         category_count=len(categories),
                         upcoming_sessions=upcoming_sessions)

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

# Student assignment routes
@app.route('/assignments')
@login_required
def view_assignments():
    if session.get('role') != 'student':
        flash('Only students can view assignments', 'danger')
        return redirect(url_for('home'))
    
    assignments = get_assignments_for_user(session['user_id'])
    return render_template('assignments/list.html', 
                         assignments=assignments,
                         current_time=datetime.utcnow())

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
        
        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
        
        if submit_assignment(assignment_id, session['user_id'], submission_text, file_path):
            flash('Assignment submitted successfully!', 'success')
            return redirect(url_for('view_assignment', assignment_id=assignment_id))
        else:
            flash('Error submitting assignment', 'danger')
    
    return render_template('assignments/view.html',
                         assignment=assignment,
                         submission=submission)
# @login_required
# def view_assignment(assignment_id):
#     if session.get('role') != 'student':
#         flash('Only students can view assignments', 'danger')
#         return redirect(url_for('home'))
    
#     assignment = get_assignment_details(assignment_id)
#     if not assignment:
#         flash('Assignment not found', 'danger')
#         return redirect(url_for('view_assignments'))
    
#     if request.method == 'POST':
#         submission_text = request.form.get('submission_text', '')
#         # Handle file upload if needed
#         file_path = None
#         if 'assignment_file' in request.files:
#             file = request.files['assignment_file']
#             if file.filename != '':
#                 filename = secure_filename(file.filename)
#                 file_path = os.path.join('uploads', filename)
#                 file.save(os.path.join(app.static_folder, file_path))
        
#         if submit_assignment(assignment_id, session['user_id'], submission_text, file_path):
#             flash('Assignment submitted successfully!', 'success')
#         else:
#             flash('Error submitting assignment', 'danger')
#         return redirect(url_for('view_assignment', assignment_id=assignment_id))
    
#     return render_template('assignments/view.html', assignment=assignment)

@app.route('/assignments/submissions')
@login_required
def view_submissions():
    if session.get('role') != 'student':
        flash('Only students can view submissions', 'danger')
        return redirect(url_for('home'))
    
    submissions = get_student_submissions(session['user_id'])
    return render_template('assignments/submissions.html', submissions=submissions)

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
            assigned_users = request.form.getlist('assigned_users')

            # Validate required fields
            if not all([title, description, subject, total_marks, deadline_str]):
                flash('All fields are required', 'danger')
                return redirect(url_for('add_assignment'))

            # Convert and validate total marks
            try:
                total_marks = int(total_marks)
                if total_marks <= 0:
                    flash('Total marks must be positive', 'danger')
                    return redirect(url_for('add_assignment'))
            except ValueError:
                flash('Total marks must be a number', 'danger')
                return redirect(url_for('add_assignment'))

            # Validate deadline
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
                if deadline <= datetime.now():
                    flash('Deadline must be in the future', 'danger')
                    return redirect(url_for('add_assignment'))
            except ValueError:
                flash('Invalid deadline format', 'danger')
                return redirect(url_for('add_assignment'))

            # Validate student selection
            if not assigned_users:
                flash('Please select at least one student', 'danger')
                return redirect(url_for('add_assignment'))

            # Verify all student IDs are valid
            valid_student_ids = {str(student[0]) for student in get_students()}  # Get current valid IDs
            print(valid_student_ids)

            for user_username in assigned_users:
                if user_username not in valid_student_ids:
                    flash('Invalid student selection', 'danger')
                    return redirect(url_for('add_assignment'))

            # Convert to integers
            assigned_users = [int(user_id) for user_id in assigned_users]

            # Create assignment
            assignment_id = add_assignment(
                title=title,
                description=description,
                subject=subject,
                total_marks=total_marks,
                deadline=deadline,
                assigned_users=assigned_users
            )

            flash('Assignment created successfully!', 'success')
            return redirect(url_for('manage_assignments'))

        except Exception as e:
            flash(f'Error creating assignment: {str(e)}', 'danger')
            app.logger.error(f"Assignment creation error: {str(e)}")
    
    # GET request - show form with students
    students = get_students()
    print(students)
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
                   COUNT(au.user_id) as assigned_count,
                   COUNT(s.id) as submission_count
            FROM assignments a
            LEFT JOIN assignment_users au ON a.id = au.assignment_id
            LEFT JOIN assignment_submissions s ON a.id = s.assignment_id
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
        cur.execute('SELECT id, title, total_marks FROM assignments WHERE id = %s', (assignment_id,))
        assignment = cur.fetchone()
        if not assignment:
            flash('Assignment not found', 'danger')
            return redirect(url_for('manage_assignments'))
        
        # Get submissions with student IDs
        cur.execute('''
            SELECT u.username, s.submitted_at, s.marks_obtained, u.id as student_id, s.feedback
            FROM assignment_submissions s
            JOIN users u ON s.student_id = u.id
            WHERE s.assignment_id = %s
            ORDER BY s.submitted_at DESC
        ''', (assignment_id,))
        submissions = cur.fetchall()
        
        return render_template('admin/assignments/submissions.html',
                            assignment_title=assignment[1],
                            assignment_id=assignment_id,
                            submissions=submissions)
    finally:
        cur.close()
        conn.close()

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get the user's class from session or database
        user_class = session.get('class')  # Make sure this is set during login
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT id, title, subject, deadline, total_marks
            FROM assignments
            WHERE class = %s
            ORDER BY deadline
        ''', (user_class,))
        assignments = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template(
            'dashboard.html',
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
            marks_obtained = float(marks_obtained)
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
        marks_obtained = float(marks_obtained)
        
        # Get assignment to validate max marks
        assignment = get_assignment_details(assignment_id)
        if not assignment:
            flash('Assignment not found', 'danger')
            return redirect(url_for('manage_assignments'))
        
        if marks_obtained < 0 or marks_obtained > assignment[4]:  # total_marks is at index 4
            flash('Invalid marks value', 'danger')
            return redirect(url_for('grade_submission', assignment_id=assignment_id, student_id=student_id))
        
        if update_submission_grade(assignment_id, student_id, marks_obtained, feedback):
            flash('Grade submitted successfully', 'success')
        else:
            flash('Error submitting grade', 'danger')
    except ValueError:
        flash('Invalid marks format', 'danger')
    
    return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))

    
if __name__ == '__main__':
    from waitress import serve
    initialize_database()
    serve(app, host="0.0.0.0", port=5000)

# if __name__ == '__main__':
#     # Enable Flask debug features
#     app.debug = True  # Enables auto-reloader and debugger
    
#     # Initialize database
#     initialize_database()
    
#     # Run the development server
#     app.run(host='0.0.0.0', port=5000)
