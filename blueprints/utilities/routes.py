from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_required
from helpers import get_db_connection, get_leaderboard, record_practice_score
from helpers import get_plan_name, get_plan_price, save_plan_request
from helpers import get_exams_data, get_practice_data
from helpers import get_actual_subject_data, get_recent_activities, get_actual_trend_data
from blueprints.assignments.utils import get_assignments_data


# Create a blueprint for utilities
utilities_bp = Blueprint('utilities', __name__,
                         template_folder='templates', static_folder='static')


@utilities_bp.route('/algebra-calculator')
def algebra_calculator():
    return render_template('algebra_calculator.html')


@utilities_bp.route('/video-conference')
def video_conference():
    return render_template('live_session.html')  # We'll create this file next


@utilities_bp.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


@utilities_bp.route('/leaderboard')
@login_required
def view_leaderboard():
    subject = request.args.get('subject')
    topic = request.args.get('topic')
    time_period = request.args.get('time', 'all')

    leaderboard, user_stats, user_rank = get_leaderboard(
        subject=subject,
        topic=topic,
        time_period=time_period
    )

    # Get available subjects and topics
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT subject FROM practice_scores ORDER BY subject')
    available_subjects = [row[0] for row in cur.fetchall()]

    available_topics = []
    if subject:
        cur.execute('''
            SELECT DISTINCT topic FROM practice_scores 
            WHERE subject = %s ORDER BY topic
        ''', (subject,))
        available_topics = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return render_template('leaderboard.html',
                           leaderboard=leaderboard,
                           available_subjects=available_subjects,
                           available_topics=available_topics,
                           current_subject=subject,
                           current_topic=topic,
                           user_stats=user_stats,
                           user_rank=user_rank)


@utilities_bp.route('/api/leaderboard-details')
@login_required
def get_leaderboard_details():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Get basic user info
        cur.execute('SELECT username FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get overall stats (total score / attempts)
        cur.execute('''
            SELECT 
                ROUND(SUM(score)::numeric / COUNT(id), 2) as avg_score,
                COUNT(*) as attempt_count,
                ROUND(AVG(score::numeric / total_questions * 100), 2) as avg_percentage
            FROM practice_scores
            WHERE student_id = %s
        ''', (user_id,))
        overall_stats = cur.fetchone()

        # Get global rank based on (total score / attempts)
        cur.execute('''
            WITH ranked_students AS (
                SELECT 
                    student_id,
                    SUM(score)::numeric / COUNT(id) as avg_score,
                    DENSE_RANK() OVER (ORDER BY (SUM(score)::numeric / COUNT(id)) DESC) as rank
                FROM practice_scores
                GROUP BY student_id
            )
            SELECT rank 
            FROM ranked_students
            WHERE student_id = %s
        ''', (user_id,))
        rank_result = cur.fetchone()

        # Get performance by subject
        cur.execute('''
            SELECT 
                subject,
                ROUND(SUM(score)::numeric / COUNT(id), 2) as avg_score,
                COUNT(*) as attempt_count,
                ROUND(AVG(score::numeric / total_questions * 100), 2) as avg_percentage
            FROM practice_scores
            WHERE student_id = %s
            GROUP BY subject
            ORDER BY avg_score DESC
        ''', (user_id,))
        subjects = []
        for row in cur.fetchall():
            subjects.append({
                'subject': row[0],
                'avg_score': row[1],
                'attempt_count': row[2],
                'avg_percentage': row[3]
            })

        # Get history for chart
        cur.execute('''
            SELECT 
                score,
                total_questions,
                ROUND((score::numeric / total_questions * 100), 2) as percentage,
                completed_at,
                subject,
                topic
            FROM practice_scores
            WHERE student_id = %s
            ORDER BY completed_at
        ''', (user_id,))

        history = []
        for row in cur.fetchall():
            history.append({
                'score': row[0],
                'total_questions': row[1],
                'percentage': row[2],
                'date': row[3].strftime('%Y-%m-%d'),
                'subject': row[4],
                'topic': row[5]
            })

        return jsonify({
            'username': user[0],
            'avg_score': overall_stats[0] if overall_stats else 0,
            'attempt_count': overall_stats[1] if overall_stats else 0,
            'avg_percentage': overall_stats[2] if overall_stats else 0,
            'rank': rank_result[0] if rank_result else None,
            'subjects': subjects,
            'history': history
        })

    except Exception as e:
        print(f"Error getting leaderboard details: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()


@utilities_bp.route('/api/record-practice', methods=['POST'])
@login_required
def record_practice():
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': 'Only students can record practice'})

    data = request.get_json()
    subject = data.get('subject')
    topic = data.get('topic')
    score = data.get('score')
    total_questions = data.get('total_questions')

    if not all([subject, topic, score is not None, total_questions]):
        return jsonify({'success': False, 'error': 'Missing required fields'})

    try:
        success = record_practice_score(
            student_id=session['user_id'],
            subject=subject,
            topic=topic,
            score=score,
            total_questions=total_questions
        )
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@utilities_bp.route('/submit_plan_request', methods=['POST'])
def submit_plan_request():
    # Get form data
    data = {
        'user_name': request.form.get('name'),
        'user_email': request.form.get('email'),
        'user_phone': request.form.get('phone'),
        'message': request.form.get('message', ''),
        'plan_id': request.form.get('plan_id'),
        'plan_name': get_plan_name(request.form.get('plan_id')),
        'plan_price': get_plan_price(request.form.get('plan_id')),
        'status': 'pending'
    }

    try:
        # Save the request
        request_id = save_plan_request(data)
        if request_id:
            flash('Request submitted successfully!', 'success')
            return redirect(url_for('confirmation'))
        else:
            flash('Error submitting request', 'danger')
            return redirect(url_for('utilities.contact_tutor', plan_id=data['plan_id']))

    except Exception as e:
        current_app.logger.error(f"Database error: {str(e)}")
        flash('Error submitting request. Please try again.', 'danger')
        return redirect(url_for('utilities.contact_tutor', plan_id=data['plan_id']))


def get_plan_details(plan_id):
    # Example implementation - replace with your actual DB query
    plans = {
        1: {'name': 'Access', 'price': 99.99},
        2: {'name': 'Standard', 'price': 199.99},
        3: {'name': 'Premium', 'price': 299.99}
    }
    return plans.get(int(plan_id), {'name': 'Unknown Plan', 'price': 0})

# Email notification function (implement with your email service)


def send_admin_notification(user_email, plan_name, message):
    # Implement using Flask-Mail, SendGrid, etc.
    pass


@utilities_bp.route('/confirmation')
def confirmation():
    """Confirmation page after plan request submission"""
    return render_template('confirmation.html')


@utilities_bp.route('/contact_tutor/<int:plan_id>')
def contact_tutor(plan_id):
    """Contact tutor page with plan information"""
    return render_template('contact_tutor.html', plan_id=plan_id)


@utilities_bp.route('/whiteboards')
@login_required
def list_whiteboards():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get whiteboards the user has access to
        cur.execute('''
            SELECT w.id, w.name, u.username as created_by, w.created_at
            FROM whiteboards w
            JOIN users u ON w.created_by = u.id
            JOIN whiteboard_participants p ON w.id = p.whiteboard_id
            WHERE p.user_id = %s
            ORDER BY w.created_at DESC
        ''', (session['user_id'],))

        whiteboards = [{
            'id': row[0],
            'name': row[1],
            'created_by': row[2],
            'created_at': row[3]
        } for row in cur.fetchall()]

        return render_template('whiteboards/list.html', whiteboards=whiteboards)
    except Exception as e:
        print(f"Error listing whiteboards: {e}")
        return render_template('whiteboards/list.html', whiteboards=[])
    finally:
        cur.close()
        conn.close()


@utilities_bp.route('/api/student/<int:student_id>/chart_data')
def get_chart_data(student_id):
    """Endpoint to fetch all chart data from database"""
    try:
        # Get all data from database
        assignments = get_assignments_data(student_id)
        print(assignments)
        practice = get_practice_data(student_id)
        print(practice)
        exams = get_exams_data(student_id)
        print(exams)
        activities = get_recent_activities(student_id)

        # Get actual trend data with real dates
        trend_data = get_actual_trend_data(student_id)

        # Get actual subject performance data
        subject_data = get_actual_subject_data(student_id)

        return jsonify({
            'assignments': assignments,
            'practice': practice,
            'exams': exams,
            'activities': activities,
            'trend': trend_data,
            'subjects': subject_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# In your app.py file, usually near your other admin routes
