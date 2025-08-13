from flask import Blueprint, jsonify, request, render_template
from models import get_db_connection
import psycopg2
import psycopg2.extras

practice_bp = Blueprint('practice_bp', __name__)

@practice_bp.route('/')
def practice_questions_page():
    return render_template('practice_questions.html')

@practice_bp.route('/questions')
def get_questions():
    grade = request.args.get('grade')
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    sub_topic = request.args.get('sub_topic')

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
    questions = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify([dict(q) for q in questions])
