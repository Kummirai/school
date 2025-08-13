from models import get_db_connection
import psycopg2.extras
import random

def get_random_question(grade):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Fetch all questions for the given grade
        cur.execute("SELECT * FROM practice_questions WHERE grade = %s", (grade,))
        questions = cur.fetchall()
        
        if questions:
            # Return a random question from the fetched list
            return random.choice(questions)
        else:
            return None
    except Exception as e:
        print(f"Error fetching random question: {e}")
        return None
    finally:
        cur.close()
        conn.close()