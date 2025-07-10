from models import get_db_connection
from datetime import datetime
import psycopg2.extras
from flask import current_app as app
from helpers import get_all_student_ids


def get_assignments_data(student_id):
    """Fetch actual assignment statistics with submission dates as labels"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                WITH submission_details AS (
    SELECT 
        s.submission_time,
        s.grade,
        a.subject
    FROM submissions s
    JOIN assignments a ON s.assignment_id = a.id
    WHERE s.student_id = %s
    AND s.submission_time >= NOW() - INTERVAL '30 days'
    AND s.grade IS NOT NULL
),

assignment_stats AS (
    SELECT 
        AVG(grade) as avg_score,
        COUNT(*) as total,
        COUNT(CASE WHEN submission_time IS NOT NULL THEN 1 END) as submitted,
        MAX(grade) as best_score,
        ARRAY_AGG(grade ORDER BY submission_time) as scores,
        ARRAY(
            SELECT subject
            FROM submission_details
            ORDER BY subject
            LIMIT 4
        ) as subject_labels,
        ARRAY(
            SELECT DISTINCT ON (DATE_TRUNC('week', submission_time))
                TO_CHAR(submission_time, 'Mon DD')
            FROM submission_details
            ORDER BY DATE_TRUNC('week', submission_time), submission_time
        ) as date_labels,
        ARRAY(
            SELECT JSON_BUILD_OBJECT(
                'date', TO_CHAR(submission_time, 'YYYY-MM-DD HH24:MI'),
                'grade', grade,
                'subject', subject
            )
            FROM submission_details
            ORDER BY submission_time
        ) as detailed_submissions
    FROM submission_details
)
SELECT 
    COALESCE(avg_score, 0) as avg_score,
    COALESCE(total, 0) as total,
    COALESCE(submitted, 0) as submitted,
    COALESCE(best_score, 0) as best_score,
    CASE WHEN array_length(scores, 1) > 0 THEN scores ELSE ARRAY[0,0,0,0] END as scores,
    CASE WHEN array_length(subject_labels, 1) > 0 THEN subject_labels ELSE ARRAY['Math','Science','English','History'] END as subject_labels,
    CASE WHEN array_length(date_labels, 1) > 0 THEN date_labels ELSE ARRAY['Week 1','Week 2','Week 3','Week 4'] END as date_labels,
    detailed_submissions
FROM assignment_stats;
            """, (student_id,))

            assignment_data = cur.fetchone()

            return {
                'avg_score': float(assignment_data[0]),  # type: ignore
                'total': assignment_data[1],  # type: ignore
                'submitted': assignment_data[2],  # type: ignore
                'best_score': float(assignment_data[3]),  # type: ignore
                'scores': assignment_data[4],  # type: ignore
                'labels': assignment_data[5]  # type: ignore
            }

    except Exception as e:
        print(f"Error fetching assignment data: {e}")
        return {
            'avg_score': 0,
            'total': 0,
            'submitted': 0,
            'best_score': 0,
            'scores': [24, 45, 54, 87],
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        }
    finally:
        conn.close()


def get_student_assignments(student_id):
    conn = get_db_connection()
    # Using DictCursor is highly recommended here for easy access in template
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    assignments = []
    try:
        cur.execute('''
            SELECT
                a.id AS assignment_id,
                a.title,
                a.description,
                a.deadline,
                a.total_marks,
                s.grade AS submission_grade,
                s.submission_time AS submission_date,
                CASE WHEN s.id IS NOT NULL THEN TRUE ELSE FALSE END AS is_submitted
            FROM assignments a
            JOIN assignment_students au ON a.id = au.assignment_id
            LEFT JOIN submissions s ON a.id = s.assignment_id AND s.student_id = au.student_id
            WHERE au.student_id = %s
            ORDER BY a.deadline ASC;
        ''', (student_id,))
        assignments = cur.fetchall()
    except Exception as e:
        print(f"Error fetching assignments for student {student_id}: {e}")
        # Log this error properly in a real application
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    return assignments


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
        return cur.fetchone()[0]  # type: ignore
    except Exception as e:
        print(f"Error getting unsubmitted assignments count: {e}")
        return 0
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
            WHERE au.student_id = %s
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
        app.logger.error(
            f"Error getting assignments for user {user_id}: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()

# Assuming you have a function to get all student IDs if assigned_students_ids is None


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
        assignment_id = cur.fetchone()[0]  # type: ignore

        if assigned_students_ids is None:  # This means 'all' students
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
