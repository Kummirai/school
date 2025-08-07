from models import get_db_connection
import psycopg2.extras


def get_videos_by_category(category_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        'SELECT id, title, url, description, grade, subject, youtubeid, thumbnail FROM videos WHERE category_id = %s', (category_id,))
    videos = cur.fetchall()
    cur.close()
    conn.close()
    return videos


def get_all_videos():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT v.id, v.title, v.url, v.description, v.grade, v.subject, v.youtubeid, v.thumbnail, tc.name as category_name
        FROM videos v
        JOIN tutorial_categories tc ON v.category_id = tc.id
    ''')
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
                v.id,
                v.title,
                v.description,
                v.grade,
                v.subject,
                v.youtubeid,
                v.thumbnail,
                tc.name as category_name
            FROM
                videos v
            JOIN
                tutorial_categories tc ON v.category_id = tc.id
            ORDER BY
                v.grade, v.subject, v.title
        ''')
        videos = cur.fetchall()
        return videos
    except Exception as e:
        print(f"Error fetching all video details: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def add_video(title, url, description, grade, subject, youtubeid, thumbnail, category_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO videos (title, url, description, grade, subject, youtubeid, thumbnail, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (title, url, description, grade, subject, youtubeid, thumbnail, category_id))
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
