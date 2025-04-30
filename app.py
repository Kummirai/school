from functools import wraps
from flask import Flask, flash, redirect, render_template, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
#app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key-for-development')

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)
        if user and check_password_hash(user['password'], password):  # Changed from user[2] to user['password']
            session['username'] = username
            session['user_id'] = user['id']  # Accessing id from dictionary
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('tutorials_home'))
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
