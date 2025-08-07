from models import get_db_connection
import psycopg2.extras


def get_videos_by_subject(subject):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        'SELECT id, title, url, description, grade, subject, youtubeid, thumbnail FROM videos WHERE subject = %s', (subject,))
    videos = cur.fetchall()
    cur.close()
    conn.close()
    return videos


def get_all_videos():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT id, title, url, description, grade, subject, youtubeid, thumbnail, subject as category_name FROM videos')
    videos = cur.fetchall()
    cur.close()
    conn.close()
    return videos


def get_all_videos_details():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute('''
            SELECT
                id,
                title,
                description,
                grade,
                subject,
                youtubeid,
                thumbnail,
                subject as category_name
            FROM
                videos
            ORDER BY
                grade, subject, title
        ''')
        videos = cur.fetchall()
        return videos
    except Exception as e:
        print(f"Error fetching all video details: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def add_video(title, url, description, grade, subject, youtubeid, thumbnail):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO videos (title, url, description, grade, subject, youtubeid, thumbnail) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (title, url, description, grade, subject, youtubeid, thumbnail))
    conn.commit()
    cur.close()
    conn.close()


def delete_video(video_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM videos WHERE id = %s', (video_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_all_subjects():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT subject FROM videos ORDER BY subject')
    subjects = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return subjects
