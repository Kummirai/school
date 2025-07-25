from datetime import timedelta
from models import get_db_connection
import psycopg2.extras


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

    try:
        # Check if session exists and has available spots
        cur.execute('''
            SELECT ts.max_students, COUNT(sb.id) as current_bookings
            FROM tutorial_sessions ts
            LEFT JOIN student_bookings sb ON ts.id = sb.session_id
            WHERE ts.id = %s
            GROUP BY ts.id, ts.max_students
        ''', (session_id,))
        result = cur.fetchone()

        if not result:
            print(f"Session {session_id} not found")
            return False

        max_students, current_bookings = result
        if current_bookings >= max_students:
            print(
                f"Session {session_id} is full ({current_bookings}/{max_students})")
            return False

        # Check if student already booked this session
        cur.execute('''
            SELECT id FROM student_bookings 
            WHERE student_id = %s AND session_id = %s
        ''', (student_id, session_id))
        if cur.fetchone():
            print(f"Student {student_id} already booked session {session_id}")
            return False

        # Create booking
        cur.execute('''
            INSERT INTO student_bookings (student_id, session_id)
            VALUES (%s, %s)
        ''', (student_id, session_id))
        conn.commit()
        print(
            f"Successfully booked session {session_id} for student {student_id}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error booking session: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def cancel_booking(booking_id, student_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            DELETE FROM student_bookings
            WHERE id = %s AND student_id = %s
        ''', (booking_id, student_id))
        affected_rows = cur.rowcount
        conn.commit()
        return affected_rows > 0
    except Exception as e:
        conn.rollback()
        print(f"Error cancelling booking: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def get_all_sessions():
    """Get all tutorial sessions with booking counts"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                ts.id, 
                ts.title, 
                ts.description, 
                ts.start_time, 
                ts.end_time, 
                ts.max_students,
                COALESCE(COUNT(sb.id), 0) as current_bookings
            FROM tutorial_sessions ts
            LEFT JOIN student_bookings sb ON ts.id = sb.session_id AND sb.status = 'confirmed'
            GROUP BY ts.id, ts.title, ts.description, ts.start_time, ts.end_time, ts.max_students
            ORDER BY ts.start_time
        ''')
        sessions = cur.fetchall()
        print(f"Retrieved {len(sessions)} sessions from database")
        for session in sessions:
            print(f"Session: {session}")
        return sessions
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_upcoming_sessions():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT ts.id, ts.title, ts.start_time, ts.end_time,
                   COALESCE(COUNT(sb.id), 0) as booked_count, ts.max_students
            FROM tutorial_sessions ts
            LEFT JOIN student_bookings sb ON ts.id = sb.session_id AND sb.status = 'confirmed'
            WHERE ts.start_time > NOW()
            GROUP BY ts.id, ts.title, ts.start_time, ts.end_time, ts.max_students
            ORDER BY ts.start_time
            LIMIT 5
        ''')
        sessions = cur.fetchall()
        return sessions
    except Exception as e:
        print(f"Error getting upcoming sessions: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_student_bookings(student_id):
    """Get all bookings for a specific student"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                sb.id, 
                ts.title, 
                ts.start_time, 
                ts.end_time,
                ts.id as session_id
            FROM student_bookings sb
            JOIN tutorial_sessions ts ON sb.session_id = ts.id
            WHERE sb.student_id = %s AND sb.status = 'confirmed'
            ORDER BY ts.start_time
        ''', (student_id,))
        bookings = cur.fetchall()
        print(f"Retrieved {len(bookings)} bookings for student {student_id}")
        for booking in bookings:
            print(f"Booking: {booking}")
        return bookings
    except Exception as e:
        print(f"Error getting student bookings: {e}")
        return []
    finally:
        cur.close()
        conn.close()


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
                SELECT title, description, preferred_time, student_id
                FROM session_requests
                WHERE id = %s
            ''', (request_id,))
            request = cur.fetchone()

            if request:
                title, description, preferred_time, student_id = request
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
                        VALUES (%s, %s)
                    ''', (student_id, session_id))
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


def add_sample_sessions():
    """Add some sample sessions for testing"""
    from datetime import datetime, timedelta

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if sessions already exist
        cur.execute('SELECT COUNT(*) FROM tutorial_sessions')
        count = cur.fetchone()[0]

        if count > 0:
            print("Sample sessions already exist")
            return

        # Add sample sessions for the next few days
        base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

        sample_sessions = [
            ("Mathematics Tutoring", "Basic algebra and geometry",
             base_date + timedelta(days=1), 5),
            ("Physics Workshop", "Introduction to mechanics",
             base_date + timedelta(days=1, hours=2), 8),
            ("Chemistry Lab", "Organic chemistry basics",
             base_date + timedelta(days=2), 6),
            ("English Literature", "Shakespeare analysis",
             base_date + timedelta(days=2, hours=3), 10),
            ("Computer Science", "Python programming basics",
             base_date + timedelta(days=3), 12),
            ("Biology Study Group", "Cell biology review",
             base_date + timedelta(days=4, hours=1), 7),
        ]

        for title, description, start_time, max_students in sample_sessions:
            end_time = start_time + timedelta(hours=1)
            cur.execute('''
                INSERT INTO tutorial_sessions (title, description, start_time, end_time, max_students)
                VALUES (%s, %s, %s, %s, %s)
            ''', (title, description, start_time, end_time, max_students))

        conn.commit()
        print(f"Added {len(sample_sessions)} sample sessions")

    except Exception as e:
        conn.rollback()
        print(f"Error adding sample sessions: {e}")
    finally:
        cur.close()
        conn.close()
