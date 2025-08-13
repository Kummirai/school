from flask import Blueprint, jsonify, request, render_template
from models import get_db_connection
import psycopg2
import psycopg2.extras

practice_bp = Blueprint('practice_bp', __name__)


@practice_bp.route('/')
def practice_questions_page():
    return render_template('practice_questions.html')


@practice_bp.route('/grades')
def get_grades():
    subject = request.args.get('subject')
    conn = get_db_connection()
    cursor = conn.cursor()
    if subject:
        cursor.execute("SELECT DISTINCT grade FROM practice_questions WHERE subject = %s ORDER BY grade", (subject,))
    else:
        cursor.execute("SELECT DISTINCT grade FROM practice_questions ORDER BY grade")
    grades = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(grades)


@practice_bp.route('/topics')
def get_topics():
    subject = request.args.get('subject')
    grade = request.args.get('grade')
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT DISTINCT topic FROM practice_questions WHERE subject = %s AND grade = %s ORDER BY topic"
    cursor.execute(query, (subject, grade))
    topics = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(topics)


@practice_bp.route('/questions')
def get_questions():
    grade = request.args.get('grade')
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    sub_topic = request.args.get('sub_topic')

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        query = "SELECT * FROM practice_questions WHERE 1=1"
        params = []

        if grade:
            query += " AND grade = %s"
            params.append(grade)
        if subject:
            query += " AND subject = %s"
            params.append(subject)
        if topic:
            query += " AND topic = %s"
            params.append(topic)
        if sub_topic:
            query += " AND sub_topic = %s"
            params.append(sub_topic)

        cursor.execute(query, tuple(params))
        questions_raw = cursor.fetchall()
        
        questions = []
        for row in questions_raw:
            questions.append(dict(row))

        cursor.close()
        return jsonify(questions)
    except Exception as e:
        print(f"Error in get_questions: {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500
    finally:
        if conn:
            conn.close()
