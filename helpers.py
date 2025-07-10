from models import get_db_connection
from datetime import datetime, timedelta
import json
import psycopg2.extras
from flask import current_app, session
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash
from flask import Flask

app = Flask(__name__)


def create_session_request(student_id, title, description, category, preferred_time):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO session_requests 
            (student_id, title, description, category, preferred_time)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (student_id, title, description, category, preferred_time))
        request_id = cur.fetchone()[0]  # type: ignore
        conn.commit()
        return request_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating session request: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def get_session_requests_for_student(student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT id, title, description, category, preferred_time, status, created_at
            FROM session_requests
            WHERE student_id = %s
            ORDER BY created_at DESC
        ''', (student_id,))
        return [{
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'category': row[3],
            'preferred_time': row[4],
            'status': row[5],
            'created_at': row[6]
        } for row in cur.fetchall()]
    except Exception as e:
        print(f"Error getting session requests: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_all_session_requests():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT sr.id, sr.title, sr.description, sr.category, sr.preferred_time, 
                   sr.status, sr.created_at, u.username as student_name
            FROM session_requests sr
            JOIN users u ON sr.student_id = u.id
            ORDER BY sr.created_at DESC
        ''')
        return [{
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'category': row[3],
            'preferred_time': row[4],
            'status': row[5],
            'created_at': row[6],
            'student_name': row[7]
        } for row in cur.fetchall()]
    except Exception as e:
        print(f"Error getting all session requests: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def update_session_request_status(request_id, status, admin_id, notes=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Update the request status
        cur.execute('''
            UPDATE session_requests
            SET status = %s,
                admin_notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (status, notes, request_id))

        # If approved, create a tutorial session
        if status == 'approved':
            cur.execute('''
                SELECT title, description, preferred_time
                FROM session_requests
                WHERE id = %s
            ''', (request_id,))
            request = cur.fetchone()

            if request:
                title, description, preferred_time = request
                # Create a session with default duration (1 hour)
                end_time = preferred_time + timedelta(hours=1)
                cur.execute('''
                    INSERT INTO tutorial_sessions 
                    (title, description, start_time, end_time, max_students)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (title, description, preferred_time, end_time, 1))
                session_row = cur.fetchone()
                if session_row:
                    session_id = session_row[0]

                    # Book the student automatically
                    cur.execute('''
                        INSERT INTO student_bookings (student_id, session_id)
                        SELECT student_id, %s
                        FROM session_requests
                        WHERE id = %s
                    ''', (session_id, request_id))
                else:
                    print("Failed to create tutorial session: no session_id returned.")
                    conn.rollback()
                    return False

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating session request: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def update_request_status(request_id, status):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE requests
            SET status = %s,
                processed_date = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (status, request_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating request status: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def send_approval_notification(email, plan_name):
    # Implement with your email service (Flask-Mail, SendGrid, etc.)
    print(f"Sending approval email to {email} for plan {plan_name}")
    pass


def send_rejection_notification(email, plan_name):
    # Implement with your email service
    print(f"Sending rejection email to {email} for plan {plan_name}")
    pass


def get_request_details(request_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT id, user_name, user_email, plan_id, plan_name, plan_price
            FROM requests
            WHERE id = %s
        ''', (request_id,))
        row = cur.fetchone()
        if row:
            return {
                'id': row[0],
                'user_name': row[1],
                'user_email': row[2],
                'plan_id': row[3],
                'plan_name': row[4],
                'plan_price': row[5]
            }
        return None
    except Exception as e:
        print(f"Error getting request details: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def complete_practice_session(practice_session_id):  # type: ignore
    """Fetches practice results from DB and logs the activity"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch practice session details
        cur.execute('''
            SELECT 
                student_id, 
                topic, 
                duration_minutes, 
                score,
                completed_at
            FROM practice_sessions
            WHERE id = %s
        ''', (practice_session_id,))

        session = cur.fetchone()

        if not session:
            print(f"No practice session found with ID: {practice_session_id}")
            return False

        student_id, topic, duration, score, completed_at = session

        # Log the activity
        cur.execute('''
            INSERT INTO student_activities 
            (student_id, activity_type, description, icon, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            student_id,
            'practice',
            f"Completed {duration} minute {topic} practice",
            'book-open',
            json.dumps({
                'topic': topic,
                'duration': duration,
                'score': float(score) if score else None,
                'completed_at': completed_at.isoformat() if completed_at else datetime.utcnow().isoformat(),
                'practice_id': practice_session_id
            }),
            completed_at or datetime.utcnow()
        ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error logging practice session: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def log_student_activity(student_id, activity_type, description=None, icon=None, metadata=None):
    """
    Logs student activity to the database
    Args:
        student_id: ID of the student
        activity_type: Type of activity ('assignment', 'practice', 'exam', etc.)
        description: Human-readable description
        icon: Font Awesome icon name
        metadata: Additional JSON data about the activity
    """
    conn = current_app.db_connection  # type: ignore # Or your DB connection method
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO student_activities 
                (student_id, activity_type, description, icon, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                        (
                            student_id,
                            activity_type,
                            description,
                            icon or _get_default_icon(activity_type),
                            metadata,
                            datetime.utcnow()
                        ))
            conn.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log activity: {e}")
        conn.rollback()


def _get_default_icon(activity_type):
    icon_map = {
        'assignment': 'file-alt',
        'practice': 'book-open',
        'exam': 'file-certificate',
        'submission': 'file-upload',
        'grade': 'award',
        'login': 'sign-in-alt'
    }
    return icon_map.get(activity_type, 'check')


def get_practice_data(student_id):
    """Fetch actual practice statistics with completion dates as labels"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
              WITH practice_stats AS (
    SELECT 
        AVG(score) as avg_score,
        COUNT(*) as total,
        MAX(score) as best_score,
        ARRAY_AGG(score ORDER BY completed_at) as scores,
        ARRAY(
            SELECT TO_CHAR(completed_at, 'MM/DD HH24:MI')
            FROM practice_scores
            WHERE student_id = %s
            AND completed_at >= NOW() - INTERVAL '30 days'
            AND score IS NOT NULL
            ORDER BY completed_at
            LIMIT 4
        ) as labels
    FROM practice_scores
    WHERE student_id = %s
    AND completed_at >= NOW() - INTERVAL '30 days'
    AND score IS NOT NULL
)
SELECT 
    COALESCE(avg_score, 0) as avg_score,
    COALESCE(total, 0) as total,
    COALESCE(best_score, 0) as best_score,
    CASE WHEN scores IS NOT NULL AND array_length(scores, 1) > 0 THEN scores ELSE ARRAY[0,0,0,0] END as scores,
    CASE WHEN labels IS NOT NULL AND array_length(labels, 1) > 0 THEN labels ELSE ARRAY['No sessions','','',''] END as labels
FROM practice_stats
            """, (student_id, student_id))

            practice_data = cur.fetchone()

            return {
                'avg_score': float(practice_data[0]),  # type: ignore
                'total': practice_data[1],  # type: ignore
                'best_score': float(practice_data[2]),  # type: ignore
                'scores': practice_data[3],  # type: ignore
                'labels': practice_data[4]  # type: ignore
            }

    except Exception as e:
        print(f"Error fetching practice data: {e}")
        return {
            'avg_score': 0,
            'total': 0,
            'best_score': 0,
            'scores': [0, 0, 0, 0],
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        }
    finally:
        conn.close()


def get_exams_data(student_id):
    """Fetch actual exam statistics from database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get exam statistics for the last 30 days
            cur.execute("""
                WITH exam_stats AS (
    SELECT 
        AVG(score) as avg_score,
        COUNT(*) as total,
        MAX(score) as best_score,
        ARRAY_AGG(score ORDER BY completion_time) as scores,
        ARRAY(
            SELECT TO_CHAR(completion_time, 'MM/DD HH24:MI')
            FROM exam_results
            WHERE user_id = %s
            AND completion_time >= NOW() - INTERVAL '30 days'
            AND score IS NOT NULL
            ORDER BY completion_time
            LIMIT 4
        ) as labels
    FROM exam_results
    WHERE user_id = %s
    AND completion_time >= NOW() - INTERVAL '30 days'
    AND score IS NOT NULL
)
SELECT 
    COALESCE(avg_score, 0) as avg_score,
    COALESCE(total, 0) as total,
    COALESCE(best_score, 0) as best_score,
    CASE WHEN scores IS NOT NULL AND array_length(scores, 1) > 0 THEN scores ELSE ARRAY[0,0,0,0] END as scores,
    CASE WHEN labels IS NOT NULL AND array_length(labels, 1) > 0 THEN labels ELSE ARRAY['Week 1','Week 2','Week 3','Week 4'] END as labels
FROM exam_stats
            """, (student_id, student_id))

            exam_data = cur.fetchone()

            # If no data was found, return default values
            if not exam_data:
                return {
                    'avg_score': 0,
                    'total': 0,
                    'best_score': 0,
                    'scores': [0, 0, 0, 0],
                    'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4']
                }

            return {
                'avg_score': float(exam_data[0]),
                'total': exam_data[1],
                'best_score': float(exam_data[2]),
                'scores': exam_data[3],
                'labels': exam_data[4]
            }

    except Exception as e:
        print(f"Error fetching exam data: {e}")
        return {
            'avg_score': 0,
            'total': 0,
            'best_score': 0,
            'scores': [0, 0, 0, 0],
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        }
    finally:
        conn.close()


def get_recent_activities(student_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT 
                    activity_type as title,
                    description,
                    icon,
                    created_at as time
                FROM student_activities
                WHERE student_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """, (student_id,))

            return [{
                'title': a['title'],
                'description': a['description'],
                'icon': a['icon'] or 'check',
                'time': a['time'].strftime('%b %d, %H:%M')
            } for a in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching activities: {e}")
        return []
    finally:
        conn.close()


def complete_practice_session(practice_session_id):
    """Fetches practice results from DB and logs the activity"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch practice session details
        cur.execute('''
            SELECT 
                student_id, 
                subject, 
                topic, 
                score,
                completed_at
            FROM practice_sessions
            WHERE id = %s
        ''', (practice_session_id,))

        session = cur.fetchone()

        if not session:
            print(f"No practice session found with ID: {practice_session_id}")
            return False

        student_id, topic, duration, score, completed_at = session

        # Log the activity
        cur.execute('''
            INSERT INTO student_activities 
            (student_id, activity_type, description, icon, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            student_id,
            'practice',
            f"Completed {duration} minute {topic} practice",
            'book-open',
            json.dumps({
                'topic': topic,
                'score': float(score) if score else None,
                'completed_at': completed_at.isoformat() if completed_at else datetime.utcnow().isoformat(),
                'practice_id': practice_session_id
            }),
            completed_at or datetime.utcnow()
        ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error logging practice session: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def get_parents():
    """Get all parent users"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, username FROM users WHERE role = 'parent' ORDER BY username")
        return [{'id': row[0], 'username': row[1]} for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_parent_by_id(parent_id):
    """Get parent user by ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, username FROM users WHERE id = %s AND role = 'parent'", (parent_id,))
        row = cur.fetchone()
        return {'id': row[0], 'username': row[1]} if row else None
    finally:
        cur.close()
        conn.close()


def get_students_for_parent(parent_id):
    """Get all students linked to a parent"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT u.id, u.username 
            FROM users u
            JOIN parent_students ps ON u.id = ps.student_id
            WHERE ps.parent_id = %s
        ''', (parent_id,))
        return [{'id': row[0], 'username': row[1]} for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_student_performance_stats(student_id):
    """Get comprehensive performance stats for a student"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get assignment stats
        cur.execute('''
            SELECT
                COUNT(*) as total_assignments,
                COUNT(CASE WHEN s.id IS NOT NULL THEN 1 END) as submitted_count,
                AVG(s.grade::float/a.total_marks*100) as avg_score_percentage,
                MAX(s.grade::float/a.total_marks*100) as best_score,
                MIN(s.grade::float/a.total_marks*100) as worst_score
            FROM assignments a
            JOIN assignment_students au ON a.id = au.assignment_id
            LEFT JOIN submissions s ON a.id = s.assignment_id AND s.student_id = %s
            WHERE au.student_id = %s
        ''', (student_id, student_id))  # <--- Changed this line: pass student_id twice!
        assignment_stats = cur.fetchone()

        # Handle the case where no assignments are found for the student
        if assignment_stats and assignment_stats[0] is not None and assignment_stats[0] > 0:
            total_assignments = assignment_stats[0]
            submitted_count = assignment_stats[1]
            avg_assignment_score = round(
                assignment_stats[2], 2) if assignment_stats[2] is not None else None
            best_assignment_score = round(
                assignment_stats[3], 2) if assignment_stats[3] is not None else None
            worst_assignment_score = round(
                assignment_stats[4], 2) if assignment_stats[4] is not None else None
        else:
            total_assignments = 0
            submitted_count = 0
            avg_assignment_score = None
            best_assignment_score = None
            worst_assignment_score = None

        # Get practice stats
        cur.execute('''
            SELECT
                COUNT(*) as total_practices,
                AVG(score::float/total_questions*100) as avg_score_percentage,
                MAX(score::float/total_questions*100) as best_score,
                MIN(score::float/total_questions*100) as worst_score
            FROM practice_scores
            WHERE student_id = %s
        ''', (student_id,))
        practice_stats = cur.fetchone()

        if practice_stats and practice_stats[0] is not None and practice_stats[0] > 0:
            total_practices = practice_stats[0]
            avg_practice_score = round(
                practice_stats[1], 2) if practice_stats[1] is not None else None
            best_practice_score = round(
                practice_stats[2], 2) if practice_stats[2] is not None else None
            worst_practice_score = round(
                practice_stats[3], 2) if practice_stats[3] is not None else None
        else:
            total_practices = 0
            avg_practice_score = None
            best_practice_score = None
            worst_practice_score = None

        # Get exam stats
        cur.execute('''
            SELECT
                COUNT(*) as total_exams,
                AVG(score) as avg_score_percentage,
                MAX(score) as best_score,
                MIN(score) as worst_score
            FROM exam_results
            WHERE user_id = %s
        ''', (student_id,))
        exam_stats = cur.fetchone()

        if exam_stats and exam_stats[0] is not None and exam_stats[0] > 0:
            total_exams = exam_stats[0]
            avg_exam_score = round(
                exam_stats[1], 2) if exam_stats[1] is not None else None
            best_exam_score = round(
                exam_stats[2], 2) if exam_stats[2] is not None else None
            worst_exam_score = round(
                exam_stats[3], 2) if exam_stats[3] is not None else None
        else:
            total_exams = 0
            avg_exam_score = None
            best_exam_score = None
            worst_exam_score = None

        return {
            'assignments': {
                'total': total_assignments,
                'submitted': submitted_count,
                'avg_score': avg_assignment_score,
                'best_score': best_assignment_score,
                'worst_score': worst_assignment_score
            },
            'practice': {
                'total': total_practices,
                'avg_score': avg_practice_score,
                'best_score': best_practice_score,
                'worst_score': worst_practice_score
            },
            'exams': {
                'total': total_exams,
                'avg_score': avg_exam_score,
                'best_score': best_exam_score,
                'worst_score': worst_exam_score
            }
        }
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
        return cur.fetchone()[0]  # type: ignore
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
        announcement_id = cur.fetchone()[0]  # type: ignore

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
        print(
            f"Error: Could not decode JSON from {filepath}. Check file format.")
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
        cur.execute(
            'SELECT id, title, total_marks, content FROM assignments WHERE id = %s', (assignment_id,))
        assignment = cur.fetchone()

        # Parse the content if it exists
        content = None
        if assignment[3]:  # content is at index 3 # type: ignore
            try:
                content = json.loads(assignment[3])  # type: ignore
            except (TypeError, json.JSONDecodeError):
                # fallback to raw content if not JSON # type: ignore
                content = assignment[3]  # type: ignore

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
                'id': assignment[0],  # type: ignore
                'title': assignment[1],  # type: ignore
                'total_marks': assignment[2],  # type: ignore
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


def save_plan_request(request_data):
    """Save a new plan request to the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO requests 
            (user_name, user_email, user_phone, plan_id, plan_name, plan_price, message, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            request_data['user_name'],
            request_data['user_email'],
            request_data['user_phone'],
            request_data['plan_id'],
            request_data['plan_name'],
            request_data['plan_price'],
            request_data.get('message', ''),
            'pending'
        ))
        request_id = cur.fetchone()[0]  # type: ignore
        conn.commit()
        return request_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def get_all_student_ids():
    conn = get_db_connection()
    cur = conn.cursor()
    # Adjust 'student' role as needed
    cur.execute("SELECT id FROM users WHERE role = 'student'")
    student_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return student_ids


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
        SELECT u.username, a.title, a.subject, a.deadline, s.submission_time, 
               s.grade, a.total_marks, s.feedback, s.file_path
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN users u ON u.id = s.student_id
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


def get_student_sessions_data(student_id):
    conn = get_db_connection()
    # Use DictCursor for easy access in template
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    sessions_data = []
    try:
        # Assuming your sessions table links directly to students or through classes
        # This query fetches sessions associated with a student, including tutor and class info.
        cur.execute('''
            SELECT
                s.id AS session_id,
                s.session_date,
                s.start_time,
                s.end_time,
                s.topic,
                s.notes,
                t.username AS tutor_name,
                c.name AS class_name
            FROM sessions s
            JOIN users t ON s.tutor_id = t.id -- Assuming tutor_id links to users table
            LEFT JOIN classes c ON s.class_id = c.id -- Assuming sessions can be linked to a class
            WHERE s.student_id = %s -- Assuming sessions link directly to student_id
            ORDER BY s.session_date DESC, s.start_time DESC;
        ''', (student_id,))
        sessions_data = cur.fetchall()
    except Exception as e:
        print(f"Error fetching sessions for student {student_id}: {e}")
        # Log this error properly in a real application
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return sessions_data


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
        ''', (assignment_id, student_id, submission_text, file_path, interactive_submission_data))  # Include interactive_submission_data here
        submission_id = cur.fetchone()[0]  # type: ignore
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


def get_student_bookings(student_id):  # type: ignore
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
    cur.execute(
        'SELECT name FROM tutorial_categories WHERE id = %s', (category_id,))
    category = cur.fetchone()
    cur.close()
    conn.close()
    return category[0] if category else "Unknown Category"


def get_videos_by_category(category_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'SELECT id, title, url FROM tutorial_videos WHERE category_id = %s', (category_id,))
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
    session_id = cur.fetchone()[0]  # type: ignore
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


def get_plan_name(plan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            'SELECT name FROM subscription_plans WHERE id = %s', (plan_id,))
        row = cur.fetchone()
        return row[0] if row else "Unknown Plan"
    finally:
        cur.close()
        conn.close()


def get_plan_price(plan_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            'SELECT price FROM subscription_plans WHERE id = %s', (plan_id,))
        row = cur.fetchone()
        return float(row[0]) if row else 0.00
    finally:
        cur.close()
        conn.close()
