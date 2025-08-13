from flask import Blueprint, request, render_template, current_app
from models import get_db_connection
import psycopg2
import psycopg2.extras
import json

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
    return current_app.response_class(json.dumps(grades), mimetype='application/json')


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
    return current_app.response_class(json.dumps(topics), mimetype='application/json')


@practice_bp.route('/questions')
def get_questions():
    print("DEBUG: Entering get_questions function.")
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
            params.append(int(grade))
        if subject:
            query += " AND subject = %s"
            params.append(subject)
        if topic:
            query += " AND topic = %s"
            params.append(topic)
        if sub_topic:
            query += " AND sub_topic = %s"
            params.append(sub_topic)

        print(f"DEBUG: Executing query: {query} with params: {params}")
        cursor.execute(query, tuple(params))
        questions_raw = cursor.fetchall()
        print(f"DEBUG: Fetched {len(questions_raw)} rows from database.")
        
        questions = []
        for row in questions_raw:
            questions.append(dict(row))

        cursor.close()
        
        print(f"DEBUG: Questions prepared for JSON serialization: {questions[:1]}") # Print first question for brevity
        json_response = json.dumps(questions, default=str)
        print("DEBUG: JSON serialization successful.")
        return current_app.response_class(json_response, mimetype='application/json')

    except Exception as e:
        print(f"DEBUG: An exception occurred in get_questions: {e}")
        error_payload = json.dumps({"error": f"An error occurred: {e}"})
        return current_app.response_class(error_payload, mimetype='application/json', status=500)
    finally:
        if conn:
            conn.close()
            print("DEBUG: Database connection closed.")
    print("DEBUG: Exiting get_questions function.")
