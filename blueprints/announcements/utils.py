from models import get_db_connection


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
