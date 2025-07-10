from models import get_db_connection
from datetime import datetime, timedelta
import json
import psycopg2.extras
from flask import current_app, session, jsonify
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash
from flask import Flask
from blueprints.assignments.utils import get_assignments_data
import json

app = Flask(__name__)


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
