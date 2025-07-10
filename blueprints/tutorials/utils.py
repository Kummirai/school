from models import get_db_connection


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
