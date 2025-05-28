from functools import wraps
from flask import Flask, flash, redirect, render_template, redirect, request, session, url_for, jsonify, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask import render_template
from flask_login import current_user, login_required
import json
import sympy
from sympy import symbols, Eq, solve, simplify


# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
#app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key-for-development')
app.jinja_env.globals.update(float=float)




# Configure upload folder in your app
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not app.secret_key:
    raise ValueError("No secret key set for Flask application")

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv('host'),
            database=os.getenv('dbname'),
            user=os.getenv('user'),
            password=os.getenv('password'),
            port=os.getenv('5432'),
            # sslmode='require'
        )
        print("✅ Successfully connected to Database!")
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        raise

# Example usage
# client = get_db_connection()
# result = client.table('users').select("*").execute()

def initialize_database():
    conn = get_db_connection()
    cur = conn.cursor()

    # Add this after your other table creations
    cur.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS saved_equations (
            id SERIAL PRIMARY KEY ,
            user_id INTEGER NOT NULL,
            equation TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_announcements (
            announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            is_read BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP,
            PRIMARY KEY (announcement_id, user_id)
        )
    ''')
    
    # Create users table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role VARCHAR(50) NOT NULL
    )
    ''')

    # Subscription tables
    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            duration_days INTEGER NOT NULL
        )
    ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS exam_results (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                exam_id INTEGER NOT NULL, -- Storing the JSON exam ID
                score DECIMAL(5,2) NOT NULL, -- Store score as a percentage or points
                total_questions INTEGER NOT NULL,
                completion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            plan_id INTEGER NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT FALSE,
            payment_status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
            amount DECIMAL(10,2) NOT NULL,
            payment_date TIMESTAMP NOT NULL,
            transaction_id VARCHAR(255),
            status VARCHAR(50) NOT NULL,
            receipt_url VARCHAR(255)
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
            subject VARCHAR(100),
            total_marks INTEGER,
            deadline TIMESTAMP,
            content TEXT, -- For interactive content or complex structures
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')


    cur.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            submission_text TEXT,
            file_path VARCHAR(255), -- Path to uploaded file if any
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            grade INTEGER, -- Nullable, will be set after grading
            feedback TEXT, -- Teacher feedback
            interactive_submission_data JSONB, -- For structured/interactive answers
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_assignment_student_submission UNIQUE (assignment_id, student_id)
        );
    ''')

        # Add this to the initialize_database() function
    cur.execute('''
        CREATE TABLE IF NOT EXISTS practice_scores (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject VARCHAR(50) NOT NULL,
            topic VARCHAR(100) NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_practice_attempt UNIQUE (student_id, subject, topic)
        )
    ''')

    # Add this new table for assignment-user relationships
    cur.execute('''
        CREATE TABLE IF NOT EXISTS assignment_students (
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (assignment_id, user_id)
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

     # >>> ADDED: Check if subscription plans exist before inserting defaults
    cur.execute('SELECT COUNT(*) FROM subscription_plans')
    plan_count = cur.fetchone()[0]

    if plan_count == 0:
        # Insert default subscription plans if they don't exist
        cur.execute('''
            INSERT INTO subscription_plans (name, description, price, duration_days)
            VALUES
                ('Access', 'Access to core tutorials and study guides', 99.99, 30),
                ('Premium', 'All features including priority support', 199.99, 30),
                ('Standard', 'Access to core tutorials, study guides and Exams', 149.99, 30),
                
        ''')
        conn.commit() # Commit is done once at the end
        print("✅ Default subscription plans inserted.")
    else:
        print("Subscription plans already exist, skipping default insert.")
    # <<< END ADDED

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

#Helpers
def get_unsubmitted_assignments_count(user_id):
    """Get count of assignments that haven't been submitted yet"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT COUNT(a.id)
            FROM assignments a
            JOIN assignment_students au ON a.id = au.assignment_id
            LEFT JOIN submissions s ON a.id = s.assignment_id AND s.student_id = %s
            WHERE au.student_id = %s AND s.id IS NULL
        ''', (user_id, user_id))
        return cur.fetchone()[0]
    except Exception as e:
        print(f"Error getting unsubmitted assignments count: {e}")
        return 0
    finally:
        cur.close()
        conn.close()

def get_unread_announcements_count(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT COUNT(*) 
            FROM user_announcements 
            WHERE user_id = %s AND is_read = FALSE
        ''', (user_id,))
        return cur.fetchone()[0]
    except Exception as e:
        print(f"Error getting unread announcements count: {e}")
        return 0
    finally:
        cur.close()
        conn.close()

# Add these helper functions to app.py
def create_announcement(title, message, created_by, user_ids=None):
    """Create a new announcement and optionally assign to specific users"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Create the announcement
        cur.execute('''
            INSERT INTO announcements (title, message, created_by)
            VALUES (%s, %s, %s)
            RETURNING id
        ''', (title, message, created_by))
        announcement_id = cur.fetchone()[0]
        
        # If user_ids is None, send to all users
        if user_ids is None:
            cur.execute('SELECT id FROM users WHERE role = %s', ('student',))
            user_ids = [row[0] for row in cur.fetchall()]
        
        # Assign to selected users
        for user_id in user_ids:
            cur.execute('''
                INSERT INTO user_announcements (announcement_id, user_id)
                VALUES (%s, %s)
            ''', (announcement_id, user_id))
        
        conn.commit()
        return announcement_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_user_announcements(user_id, limit=None):
    """Get announcements for a specific user"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = '''
            SELECT a.id, a.title, a.message, a.created_at, 
                   u.username as created_by, ua.is_read
            FROM announcements a
            JOIN user_announcements ua ON a.id = ua.announcement_id
            JOIN users u ON a.created_by = u.id
            WHERE ua.user_id = %s
            ORDER BY a.created_at DESC
        '''
        
        if limit:
            query += ' LIMIT %s'
            cur.execute(query, (user_id, limit))
        else:
            cur.execute(query, (user_id,))
            
        announcements = []
        for row in cur.fetchall():
            announcements.append({
                'id': row[0],
                'title': row[1],
                'message': row[2],
                'created_at': row[3],
                'created_by': row[4],
                'is_read': row[5]
            })
            
        return announcements
    except Exception as e:
        print(f"Error getting announcements: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def mark_announcement_read(announcement_id, user_id):
    """Mark an announcement as read for a user"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE user_announcements
            SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
            WHERE announcement_id = %s AND user_id = %s
        ''', (announcement_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error marking announcement as read: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_all_announcements():
    """Get all announcements for admin view"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT a.id, a.title, a.message, a.created_at, 
                   u.username as created_by,
                   COUNT(ua.user_id) as recipient_count
            FROM announcements a
            JOIN users u ON a.created_by = u.id
            LEFT JOIN user_announcements ua ON a.id = ua.announcement_id
            GROUP BY a.id, u.username
            ORDER BY a.created_at DESC
        ''')
        
        announcements = []
        for row in cur.fetchall():
            announcements.append({
                'id': row[0],
                'title': row[1],
                'message': row[2],
                'created_at': row[3],
                'created_by': row[4],
                'recipient_count': row[5]
            })
            
        return announcements
    except Exception as e:
        print(f"Error getting all announcements: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def load_exams_from_json(filepath='static/js/exams.json'):
    """Loads exam data from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            exams_data = json.load(f)
            return exams_data
    except FileNotFoundError:
        print(f"Error: Exam data file not found at {filepath}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}. Check file format.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred loading exam data: {e}")
        return []

# Add this new helper function to app.py
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
        subscription_id = cur.fetchone()[0]
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

def record_practice_score(student_id, subject, topic, score, total_questions):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO practice_scores 
            (student_id, subject, topic, score, total_questions)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (student_id, subject, topic) 
            DO UPDATE SET 
                score = EXCLUDED.score,
                total_questions = EXCLUDED.total_questions,
                completed_at = CURRENT_TIMESTAMP
            WHERE practice_scores.score < EXCLUDED.score
        ''', (student_id, subject, topic, score, total_questions))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error recording practice score: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_leaderboard(subject=None, topic=None, time_period='all', limit=20):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Calculate leaderboard based on (total score / number of attempts)
        query = '''
            SELECT 
                u.id,
                u.username,
                ROUND(SUM(ps.score)::numeric / COUNT(ps.id), 2) as avg_score,
                COUNT(ps.id) as attempt_count,
                ROUND(AVG(ps.score::numeric / ps.total_questions * 100), 2) as avg_percentage
            FROM users u
            JOIN practice_scores ps ON u.id = ps.student_id
            WHERE u.role = 'student'
        '''
        params = []
        
        if subject:
            query += ' AND ps.subject = %s'
            params.append(subject)
        if topic:
            query += ' AND ps.topic = %s'
            params.append(topic)
            
        if time_period == 'week':
            query += ' AND ps.completed_at >= CURRENT_DATE - INTERVAL \'7 days\''
        elif time_period == 'month':
            query += ' AND ps.completed_at >= CURRENT_DATE - INTERVAL \'30 days\''
            
        query += '''
            GROUP BY u.id, u.username
            HAVING COUNT(ps.id) > 0
            ORDER BY avg_score DESC, attempt_count DESC
        '''
        
        if limit:
            query += ' LIMIT %s'
            params.append(limit)
        
        cur.execute(query, params)
        
        leaderboard = []
        rank = 0
        prev_avg = None
        actual_rank = 0
        
        for row in cur.fetchall():
            # Handle ties in average score
            if row[2] != prev_avg:
                actual_rank = rank + 1
            prev_avg = row[2]
            rank += 1
            
            leaderboard.append({
                'user_id': row[0],
                'username': row[1],
                'avg_score': row[2],
                'attempt_count': row[3],
                'avg_percentage': row[4],
                'rank': actual_rank
            })
        
        # Get current user's stats if logged in
        user_stats = None
        user_rank = None
        if 'user_id' in session:
            # Get user's total score divided by attempts
            cur.execute('''
                SELECT 
                    ROUND(SUM(score)::numeric / COUNT(id), 2) as avg_score,
                    COUNT(*) as attempt_count,
                    ROUND(AVG(score::numeric / total_questions * 100), 2) as avg_percentage
                FROM practice_scores
                WHERE student_id = %s
            ''', (session['user_id'],))
            avg_result = cur.fetchone()
            
            if avg_result and avg_result[0]:
                user_stats = {
                    'avg_score': avg_result[0],
                    'attempt_count': avg_result[1],
                    'avg_percentage': avg_result[2]
                }
                
                # Get user's rank based on (total score / attempts)
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
                ''', (session['user_id'],))
                rank_result = cur.fetchone()
                if rank_result:
                    user_rank = rank_result[0]
        
        return leaderboard, user_stats, user_rank
        
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return [], None, None
    finally:
        cur.close()
        conn.close()

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
        # Get submission details, including interactive_submission_data
        cur.execute('''
            SELECT s.id, s.submission_text, s.file_path, s.submission_time,  s.grade, s.feedback, u.username, s.interactive_submission_data
            FROM submissions s
            JOIN users u ON s.student_id = u.id
            WHERE s.assignment_id = %s AND s.student_id = %s
        ''', (assignment_id, student_id))
        submission = cur.fetchone()

        if not submission:
            return None

        # Get assignment details, including content
        cur.execute('SELECT id, title, total_marks, content FROM assignments WHERE id = %s', (assignment_id,))
        assignment = cur.fetchone()

        # Parse the content if it exists
        content = None
        if assignment[3]:  # content is at index 3
            try:
                content = json.loads(assignment[3])
            except (TypeError, json.JSONDecodeError):
                content = assignment[3]  # fallback to raw content if not JSON

        return {
            'submission': {
                'id': submission[0],
                'submission_text': submission[1],
                'file_path': submission[2],
                'submitted_at': submission[3],
                'marks_obtained': submission[4],
                'feedback': submission[5],
                'username': submission[6],
                'interactive_submission_data': submission[7]
            },
            'assignment': {
                'id': assignment[0],
                'title': assignment[1],
                'total_marks': assignment[2],
                'content': content  # Now properly parsed
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
            UPDATE submissions
            SET grade = %s, feedback = %s
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
            JOIN assignment_students au ON a.id = au.assignment_id
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

# Assuming you have a function to get all student IDs if assigned_students_ids is None
def get_all_student_ids():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role = 'student'") # Adjust 'student' role as needed
    student_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return student_ids

def add_assignment(title, description, subject, total_marks, deadline, assigned_students_ids=None, content=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO assignments (title, description, subject, total_marks, deadline, content)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
            """,
            (title, description, subject, total_marks, deadline, content)
        )
        assignment_id = cur.fetchone()[0]

        if assigned_students_ids is None: # This means 'all' students
            assigned_students_ids_list = get_all_student_ids()
        else:
            assigned_students_ids_list = assigned_students_ids

        # Insert into the assignment_students linking table
        for student_id in assigned_students_ids_list:
            cur.execute(
                """
                INSERT INTO assignment_students (assignment_id, student_id)
                VALUES (%s, %s);
                """,
                (assignment_id, student_id)
            )

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error adding assignment: {e}")
        return False
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
                   total_marks, deadline, created_at, content
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
            SELECT id, submission_text, file_path, submission_time, grade, feedback
            FROM submissions
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
        SELECT a.title, a.subject, a.deadline, s.submission_time, 
               s.grade, a.total_marks, s.feedback, s.file_path
        FROM submissions s
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

def submit_assignment(assignment_id, student_id, submission_text, file_path=None, interactive_submission_data=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO submissions
            (assignment_id, student_id, submission_text, file_path, interactive_submission_data)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (assignment_id, student_id) DO UPDATE
            SET submission_text = EXCLUDED.submission_text,
                file_path = EXCLUDED.file_path,
                submission_time = CURRENT_TIMESTAMP,
                interactive_submission_data = EXCLUDED.interactive_submission_data -- Update interactive data
            RETURNING id
        ''', (assignment_id, student_id, submission_text, file_path, interactive_submission_data)) # Include interactive_submission_data here
        submission_id = cur.fetchone()[0]
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
    # Initialize subscription to None
    subscription = None
    # Check if user is logged in and 'user_id' is in session
    if 'user_id' in session:
        # Call the function and pass the result to the template
        subscription = get_user_subscription(session['user_id'])

    # Pass the subscription variable to the render_template function
    return render_template('home.html', subscription=subscription)

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
                    solution_text.append(f"x = {sol.as_real_imag()[0].evalf(3)} + {sol.as_real_imag()[1].evalf(3)}i")
            
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
        # Load the JSON data
        with open('static/data/grade7_math.json', 'r') as f:
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

# @app.route('/tutorials')
# @login_required
# def tutorials_home():
#     categories = get_all_categories()
#     # Create a dictionary with category data
#     tutorials_dict = {
#         category[1]: {  # Using category name as key
#             'id': category[0],  # category id
#             'videos': get_videos_by_category(category[0])  # videos for this category
#         }
#         for category in categories
#     }
#     return render_template('tutorials/index.html', tutorials=tutorials_dict, categories=categories)

@app.route('/tutorials')
@login_required
def tutorials_home():
    return render_template('tutorials/video_tutorials.html')

@app.route('/study_guides')
@login_required
def studyguides_home():
    return render_template('study_guides.html')

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
    
    # Get active subscription count
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE")
    active_subscriptions_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    return render_template('admin/dashboard.html', 
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
                'assignment_id': row[8] # Add assignment_id to the dictionary
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
    user_id = session.get('user_id') # Make sure this is how you get the current user's ID
    if not user_id:
        flash('Please log in to view your assignments.', 'warning')
        return redirect(url_for('login')) # Redirect to login if user_id not found

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
            (user_id,) # Pass user_id twice for both EXISTS and WHERE clauses
        )
        for row in cur.fetchall():
            assignments.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'subject': row[3],
                'total_marks': row[4],
                'deadline': row[5],
                'content': row[6] if row[6] else None,  # Removed json.loads() since content is already a dict
                'created_at': row[7],
                'submitted': row[8],
                'grade': row[9]
            })
        
        for assignment in assignments:
            assignment['status'] = 'active' if assignment['deadline'] and assignment['deadline'] > datetime.now() else 'past_deadline'
            
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
        if assignment[7]:  # Check if there's interactive content (index 7 is content)
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
                filename = secure_filename(file.filename)
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


@app.route('/assignments/submissions') # Adjust this route name if yours is different
@login_required # Assuming this page requires login
def view_submissions(): # Adjust this function name if yours is different
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
            average_score = (avg_row[0] / avg_row[1]) * 100 # Percentage
            average_score = round(average_score, 2) # Round to 2 decimal places
        else:
            average_score = 0 # No graded submissions or total marks is zero

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
                percentage = (monthly_grade_sum / monthly_possible_marks_sum) * 100
                monthly_scores.append({
                    'year': year,
                    'month': month,
                    'month_name': datetime(year, month, 1).strftime('%B'), # Get month name
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
            selected_users = request.form.getlist('selected_users[]') if assign_to == 'selected' else []

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
                cur.execute('SELECT id FROM users WHERE role = %s', ('student',))
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
        cur.execute('SELECT id, title, total_marks FROM assignments WHERE id = %s', (assignment_id,))
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

#Leaderboard routes
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
    
# Subscription routes
@app.route('/subscribe')
@login_required
def subscribe():
    plans = get_subscription_plans()
    current_sub = get_user_subscription(session['user_id'])
    return render_template('subscriptions/subscribe.html', 
                         plans=plans,
                         current_sub=current_sub)

@app.route('/subscribe/<int:plan_id>', methods=['POST'])
@login_required
def create_subscription(plan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get plan details
        cur.execute('SELECT id, price, duration_days FROM subscription_plans WHERE id = %s', (plan_id,))
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
        
        subscription_id = cur.fetchone()[0]
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
            mark_paid = request.form.get('mark_paid') is not None # Checkbox value

            if not all([student_id, plan_id, start_date_str, duration_days]):
                flash('All fields are required', 'danger')
                return redirect(url_for('admin_add_subscription'))

            # Convert data types
            student_id = int(student_id)
            plan_id = int(plan_id)
            duration_days = int(duration_days)
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = start_date + timedelta(days=duration_days)

            # Determine payment status and active status
            payment_status = 'paid' if mark_paid else 'pending'
            is_active = mark_paid # Subscription is active immediately if marked as paid

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
                         cur.execute('SELECT name FROM subscription_plans WHERE id = %s', (plan_id,))
                         plan_name = cur.fetchone()[0]
                         if plan_name.lower() == 'premium': # Check plan name for role update
                             cur.execute("UPDATE users SET role = 'premium' WHERE id = %s", (student_id,))
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
    print("DEBUG: Rendering admin/add_subscription.html. Checking if 'float' is in globals:", 'float' in app.jinja_env.globals) # Add this line
    return render_template('admin/add_subscription.html', students=students, plans=plans)

@app.route('/subscription/status')
@login_required
def subscription_status():
    # Ensure only students can access this page if needed, although login_required already restricts it
    if session.get('role') != 'student':
        flash('This page is only for students.', 'warning')
        return redirect(url_for('home')) # Or wherever appropriate

    user_id = session.get('user_id')
    if not user_id:
        # This case should be covered by @login_required, but as a fallback:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    subscription = get_user_subscription(user_id)
    return render_template('subscription_status.html', subscription=subscription)

@app.route('/exam_practice')
@login_required # Assuming exam practice requires login
# @student_required # Optional: if only students should access
def exam_practice():
    """Renders the exam practice page with data from exams.json."""
    exams = load_exams_from_json('static/js/exams.json') # Adjust path if needed
    print("DEBUG: Loaded exams:", exams)
    return render_template('exam_practice.html', exams=exams)

@app.route('/exam/<int:exam_id>')
@login_required # Ensure user is logged in to take exams
# @student_required # Optional: restrict to students
def take_exam(exam_id):
    """Loads a specific exam and renders the exam-taking page."""
    exams = load_exams_from_json('static/js/exams.json') # Load all exams

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
        return redirect(url_for('exam_practice')) # Redirect back if exam ID is invalid

@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
@login_required # Ensure user is logged in
# @student_required # Optional: restrict to students
def submit_exam(exam_id):
    """Handles the submission of an exam, grades it, and saves the result."""
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in.', 'danger')
        return redirect(url_for('login'))

    # Load all exams from the JSON file
    exams = load_exams_from_json('static/js/exams.json')

    # Find the specific exam the user submitted
    selected_exam = None
    for exam in exams:
        if exam.get('id') == exam_id:
            selected_exam = exam
            break

    if not selected_exam:
        flash('Exam not found.', 'danger')
        return redirect(url_for('exam_practice')) # Redirect back if exam ID is invalid

    # Get user's submitted answers
    user_answers = request.form

    # Grade the exam
    correct_answers_count = 0
    total_questions = len(selected_exam.get('questions', []))

    if total_questions > 0:
        for question in selected_exam.get('questions', []):
            question_id_key = f"question_{question.get('id')}"
            submitted_answer = user_answers.get(question_id_key)
            correct_answer = question.get('correct_answer')

            # Compare submitted answer with the correct answer
            # Ensure comparison handles potential data type differences if necessary
            if submitted_answer is not None and str(submitted_answer) == str(correct_answer):
                correct_answers_count += 1

        # Calculate score (as a percentage)
        score = (correct_answers_count / total_questions) * 100
    else:
        score = 0 # Handle exams with no questions

    print(f"User {user_id} submitted Exam {exam_id}. Score: {score:.2f}% ({correct_answers_count}/{total_questions} correct)")

    # Save the result to the database
    conn = get_db_connection()
    cur = conn.cursor()
    result_id = None
    try:
        cur.execute('''
            INSERT INTO exam_results (user_id, exam_id, score, total_questions, completion_time)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id;
        ''', (user_id, exam_id, score, total_questions))
        result_id = cur.fetchone()[0]
        conn.commit()
        flash('Exam submitted and graded successfully!', 'success')

        # Redirect to a results page
        return redirect(url_for('exam_results', result_id=result_id))

    except Exception as e:
        conn.rollback()
        print(f"Error saving exam result: {e}")
        flash('Error saving exam result.', 'danger')
        # Redirect to exam practice page or an error page
        return redirect(url_for('exam_practice'))
    finally:
        cur.close()
        conn.close()

# *** Placeholder route for displaying exam results ***
# You will implement the logic for this route and create the template next.

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
        return redirect(url_for('exam_practice')) # Redirect if fetching fails
    finally:
        cur.close()
        conn.close()

    if not result:
        flash('Exam result not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('exam_practice')) # Redirect if result not found

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
        flash(f'Exam details for result ID {result_id} not found in JSON file.', 'warning')
        # We can still show the basic score, but not question-by-question review
        return render_template('exam_results.html',
                               result=result, # Pass the basic result data
                               exam_details=None) # Indicate exam details are missing


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
            user_ids = None if 'all' in send_to else [int(user_id) for user_id in send_to]
            
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
        cur.execute('DELETE FROM announcements WHERE id = %s', (announcement_id,))
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

        if file and file.filename.endswith('.json'):
            try:
                data = json.load(file)

                # Handle both single assignment and array of assignments
                assignments_data = data if isinstance(data, list) else [data]

                # Determine assigned students from form selection
                form_assigned_users = []
                if 'assign_all' in request.form and request.form['assign_all'] == 'all':
                    form_assigned_users = None # Indicates 'all students' from the form
                else:
                    selected_student_ids = request.form.getlist('selected_students')
                    if selected_student_ids:
                        form_assigned_users = [int(s_id) for s_id in selected_student_ids]
                    else:
                        form_assigned_users = [] # No specific students selected in form

                imported_count = 0
                for assignment_data in assignments_data:
                    # Validate required fields
                    required_fields = ['title', 'description', 'subject', 'total_marks', 'deadline']
                    if not all(field in assignment_data for field in required_fields):
                        flash('Invalid JSON structure - missing required fields for an assignment', 'danger')
                        continue # Skip to the next assignment in the JSON

                    try:
                        # Convert deadline string to datetime
                        deadline = datetime.strptime(assignment_data['deadline'], '%Y-%m-%d %H:%M')
                    except ValueError:
                        flash('Invalid deadline format in JSON (use YYYY-MM-DD HH:MM)', 'danger')
                        continue # Skip to the next assignment in the JSON

                    # Determine final assigned users for this specific assignment
                    final_assigned_users_for_this_assignment = None # Default to 'all' if no specific assignment
                    
                    # Prioritize 'assigned_users' from JSON if it exists
                    assigned_users_from_json = assignment_data.get('assigned_users')
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
                        content = json.dumps(content)  # Convert to string for storage

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
                        flash(f'Error creating assignment: {assignment_data["title"]}', 'warning')

                flash(f'Successfully imported {imported_count} assignments', 'success')
                if imported_count < len(assignments_data):
                    flash(f'{len(assignments_data) - imported_count} assignments could not be imported due to errors.', 'warning')
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
        cur.execute("SELECT id, username FROM users WHERE role = 'student' ORDER BY username")
        students = [{'id': row[0], 'username': row[1]} for row in cur.fetchall()]
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


@app.template_filter('datetime')
def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    """Format a datetime object to a string."""
    if value is None:
        return ""
    return value.strftime(format)

@app.route('/dashboard')
@login_required
def dashboard():
    # Example counts (you might have these already or need to implement)
    student_count = 0  # Replace with actual function call if available
    category_count = 0 # Replace with actual function call if available

    # Fetch all assignments
    all_assignments = get_all_assignments() #

    return render_template(
        'dashboard.html',
        student_count=student_count,
        category_count=category_count,
        assignments=all_assignments #
    )

@app.context_processor
def inject_functions():
    return dict(
        get_unread_announcements_count=get_unread_announcements_count,
        get_unsubmitted_assignments_count=get_unsubmitted_assignments_count
    )
    
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
