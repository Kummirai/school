from models import get_db_connection
from werkzeug.security import generate_password_hash
import psycopg2.extras


def get_students():
    conn = get_db_connection()
    # Use DictCursor to fetch rows as dictionary-like objects.
    # This allows you to access columns by name (e.g., student['id'] or student.id).
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Ensure your SELECT statement includes 'id' and 'username'
        cur.execute(
            "SELECT id, username FROM users WHERE role = 'student' ORDER BY username")
        students = cur.fetchall()
        # Each item in 'students' will now be a DictRow object, which behaves like a dictionary
        # and also supports attribute access (e.g., student.id, student.username).
        return students
    except Exception as e:
        # It's good practice to log or print errors for debugging
        print(f"Error fetching students in get_students(): {e}")
        return []  # Return an empty list to prevent further errors in the template
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


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
    cur.execute('DELETE FROM users WHERE id = %s AND role = %s',
                (student_id, 'student'))
    conn.commit()
    cur.close()
    conn.close()


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


def get_user_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT id, username, password, role FROM users WHERE username = %s', (username,))
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


def get_all_student_ids():
    conn = get_db_connection()
    cur = conn.cursor()
    # Adjust 'student' role as needed
    cur.execute("SELECT id FROM users WHERE role = 'student'")
    student_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return student_ids
