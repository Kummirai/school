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
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("SELECT DISTINCT subject as name FROM videos ORDER BY name")
        subjects_from_db = cur.fetchall()
        subjects = []
        for i, subject in enumerate(subjects_from_db):
            subjects.append({'id': i + 1, 'name': subject['name']})
        return subjects
    except Exception as e:
        print(f"Error fetching all subjects: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_subjects_by_grade(grade):
    """Get subjects available for a specific grade"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        if not grade: # If grade is empty, return all subjects
            return get_all_subjects()

        params = []
        query_conditions = []

        # Normalize incoming grade for comparison
        normalized_grade_input = grade.strip().lower()

        if normalized_grade_input.isdigit():
            grade_num = int(normalized_grade_input)
            # Match '7' or 'grade 7' or 'Grade 7'
            query_conditions.append("TRIM(LOWER(grade)) = %s")
            params.append(normalized_grade_input) # '7'
            
            query_conditions.append("TRIM(LOWER(grade)) = %s")
            params.append(f"grade {grade_num}") # 'grade 7'

            # Match ranges like '10-12'
            query_conditions.append("""
                (TRIM(LOWER(grade)) LIKE '%-%' AND 
                 CAST(SPLIT_PART(TRIM(grade), '-', 1) AS INTEGER) <= %s AND 
                 CAST(SPLIT_PART(TRIM(grade), '-', 2) AS INTEGER) >= %s)
            """)
            params.extend([grade_num, grade_num])
        else:
            # For non-numeric grades like 'Python', 'HTML', 'Ms Word'
            query_conditions.append("TRIM(LOWER(grade)) = %s")
            params.append(normalized_grade_input)

        query = f"SELECT DISTINCT subject as name FROM videos WHERE {' OR '.join(query_conditions)} ORDER BY subject"
        
        cur.execute(query, tuple(params))
        subjects_from_db = cur.fetchall()
        
        subjects = []
        for i, subject in enumerate(subjects_from_db):
            subjects.append({'id': i + 1, 'name': subject['name']})
        
        return subjects
        
    except Exception as e:
        print(f"Error fetching subjects by grade: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_filtered_videos(grade=None, subject=None, search_term=None):
    """Enhanced filtering with better grade handling"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    query = """
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
        WHERE 1=1
    """
    params = []

    if grade:
        # Handle non-numeric grades (Python, Javascript, HTML, etc.)
        if not grade.isdigit():
            query += " AND grade = %s"
            params.append(grade)
        else:
            # Handle numeric grades and grade ranges
            grade_num = int(grade)
            query += """ AND (
                grade = %s OR 
                grade = %s OR
                (grade LIKE '%-%' AND 
                 CAST(SPLIT_PART(grade, '-', 1) AS INTEGER) <= %s AND 
                 CAST(SPLIT_PART(grade, '-', 2) AS INTEGER) >= %s)
            )"""
            params.extend([str(grade_num), f"Grade {grade_num}", grade_num, grade_num])

    if subject:
        query += " AND subject = %s"
        params.append(subject)

    if search_term:
        search_pattern = f'%{search_term}%'
        query += " AND (title ILIKE %s OR description ILIKE %s OR subject ILIKE %s OR grade ILIKE %s)"
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    query += " ORDER BY grade, subject, title"

    try:
        cur.execute(query, tuple(params))
        videos = cur.fetchall()
        return videos
    except Exception as e:
        print(f"Error fetching filtered video details: {e}")
        return []
    finally:
        cur.close()
        conn.close()