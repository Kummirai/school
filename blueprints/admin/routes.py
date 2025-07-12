from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
import psycopg2.extras
from flask_login import login_required
from decorators.decorator import admin_required
from models import get_db_connection
from blueprints.subscriptions.utils import add_subscription_to_db, get_subscription_plans
from blueprints.students.utils import get_students
from flask import current_app as app
import json
from blueprints.assignments.utils import add_assignment
from helpers import get_submission_for_grading, update_submission_grade, get_user_by_id, get_request_details, update_request_status,  send_approval_notification, send_rejection_notification
from blueprints.subscriptions.utils import get_subscription_plans
from blueprints.students.utils import get_user_by_username, get_students
from werkzeug.security import generate_password_hash
from blueprints.announcements.utils import get_all_announcements, create_announcement
from blueprints.tutorials.utils import get_all_categories, get_all_videos, add_video, delete_video
from blueprints.sessions.utils import get_upcoming_sessions, create_session, get_all_sessions
from blueprints.sessions.utils import get_all_session_requests, update_session_request_status
from blueprints.students.utils import add_student_to_db, delete_student_by_id
from blueprints.assignments.utils import get_assignment_details


admin_bp = Blueprint('admin', __name__, template_folder='templates/admin')


@admin_bp.route('/assignments/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_assignment_route():
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            subject = request.form.get('subject', '').strip()
            total_marks = request.form.get('total_marks', '').strip()
            deadline_str = request.form.get('deadline', '').strip()
            assign_to = request.form.get('assign_to')  # 'all' or 'selected'
            selected_users = request.form.getlist(
                'selected_users[]') if assign_to == 'selected' else []

            # Validate required fields
            if not all([title, description, subject, total_marks, deadline_str]):
                flash('All fields are required', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Convert and validate total marks
            try:
                total_marks = int(total_marks)
                if total_marks <= 0:
                    flash('Total marks must be positive', 'danger')
                    return redirect(url_for('add_assignment_route'))
            except ValueError:
                flash('Total marks must be a number', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Validate deadline
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
                if deadline <= datetime.utcnow():
                    flash('Deadline must be in the future', 'danger')
                    return redirect(url_for('add_assignment_route'))
            except ValueError:
                flash('Invalid deadline format', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Get user IDs based on selection
            if assign_to == 'all':
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    'SELECT id FROM users WHERE role = %s', ('student',))
                user_ids = [row[0] for row in cur.fetchall()]
                cur.close()
                conn.close()
            elif assign_to == 'selected' and selected_users:
                user_ids = [int(user_id) for user_id in selected_users]
            else:
                flash('Please select at least one student', 'danger')
                return redirect(url_for('add_assignment_route'))

            # Create assignment
            assignment_id = add_assignment(
                title=title,
                description=description,
                subject=subject,
                total_marks=total_marks,
                deadline=deadline,
                assigned_students_ids=user_ids
            )

            flash('Assignment created successfully!', 'success')
            return redirect(url_for('manage_assignments'))

        except Exception as e:
            flash(f'Error creating assignment: {str(e)}', 'danger')
            app.logger.error(f"Assignment creation error: {str(e)}")

    # GET request - show form with students
    students = get_students()
    return render_template('admin/assignments/add.html', students=students)


@admin_bp.route('/assignments')
@login_required
@admin_required
def manage_assignments():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT a.id, a.title, a.subject, a.deadline, a.total_marks, a.created_at,
                   COUNT(s.student_id) as assigned_count,
                   COUNT(s.id) as submission_count
            FROM assignments a
            LEFT JOIN assignment_students au ON a.id = au.assignment_id
            LEFT JOIN submissions s ON a.id = s.assignment_id
            GROUP BY a.id
            ORDER BY a.deadline
        ''')

        assignments = []
        for row in cur.fetchall():
            assignments.append({
                'id': row[0],
                'title': row[1],
                'subject': row[2],
                'deadline': row[3],
                'total_marks': row[4],
                'created_at': row[5],
                'assigned_count': row[6],
                'submission_count': row[7]
            })

        return render_template('admin/assignments/list.html', assignments=assignments)
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/assignments/<int:assignment_id>/submissions')
@login_required
@admin_required
def view_assignment_submissions(assignment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get assignment details
        cur.execute(
            'SELECT id, title, total_marks FROM assignments WHERE id = %s', (assignment_id,))
        assignment = cur.fetchone()
        if not assignment:
            flash('Assignment not found', 'danger')
            return redirect(url_for('manage_assignments'))

        # Get submissions with student IDs
        cur.execute('''
            SELECT u.username, s.submission_time, s.grade, u.id as student_id, s.feedback
            FROM submissions s
            JOIN users u ON s.student_id = u.id
            WHERE s.assignment_id = %s
            ORDER BY s.submission_time DESC
        ''', (assignment_id,))
        submissions = cur.fetchall()

        return render_template('admin/assignments/submissions.html',
                               assignment_title=assignment[1],
                               assignment_id=assignment_id,
                               submissions=submissions)
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/assignments/<int:assignment_id>/submissions/<int:student_id>/submit-grade', methods=['POST'])
@login_required
@admin_required
def submit_grade(assignment_id, student_id):
    marks_obtained = request.form.get('marks_obtained')
    feedback = request.form.get('feedback', '')

    try:
        marks_obtained = float(marks_obtained)  # type: ignore

        # Get assignment to validate max marks
        assignment = get_assignment_details(assignment_id)
        if not assignment:
            flash('Assignment not found', 'danger')
            return redirect(url_for('manage_assignments'))

        # total_marks is at index 4
        if marks_obtained < 0 or marks_obtained > assignment[4]:
            flash('Invalid marks value', 'danger')
            return redirect(url_for('grade_submission', assignment_id=assignment_id, student_id=student_id))

        if update_submission_grade(assignment_id, student_id, marks_obtained, feedback):
            flash('Grade submitted successfully', 'success')
        else:
            flash('Error submitting grade', 'danger')
    except ValueError:
        flash('Invalid marks format', 'danger')

    return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))


@admin_bp.route('/students')
@login_required
@admin_required
def manage_students():
    students = get_students()
    return render_template('admin/students.html', students=students)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = get_user_by_username(username)
        if existing_user:
            flash('Username already exists', 'danger')
        else:
            add_student_to_db(username, password)
            flash('Student added successfully', 'success')
            return redirect(url_for('manage_students'))

    return render_template('admin/add_student.html')


@admin_bp.route('/students/delete/<int:student_id>')
@login_required
@admin_required
def delete_student(student_id):
    delete_student_by_id(student_id)
    flash('Student deleted successfully', 'success')
    return redirect(url_for('manage_students'))


@admin_bp.route('/session-requests')
@login_required
@admin_required
def manage_session_requests():
    requests = get_all_session_requests()
    return render_template('admin/session_requests.html', requests=requests)


@admin_bp.route('/session-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_session_request(request_id):
    notes = request.form.get('notes', '')
    if update_session_request_status(request_id, 'approved', session['user_id'], notes):
        flash('Session request approved and scheduled!', 'success')
    else:
        flash('Error approving request', 'danger')
    return redirect(url_for('manage_session_requests'))


@admin_bp.route('/session-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_session_request(request_id):
    notes = request.form.get('notes', '')
    if update_session_request_status(request_id, 'rejected', session['user_id'], notes):
        flash('Session request rejected', 'success')
    else:
        flash('Error rejecting request', 'danger')
    return redirect(url_for('manage_session_requests'))


@admin_bp.route('/parents/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_parent():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # student_ids will be a list of strings (e.g., ['1', '2', '5'])
        student_ids_str_list = request.form.getlist('student_ids')

        existing_user = get_user_by_username(username)
        if existing_user:
            flash('Username already exists', 'danger')
            # If username exists, you still need to render the form with students
            students = get_students()
            return render_template('admin/add_parent.html', students=students)
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            try:
                # Create parent user
                cur.execute('''
                    INSERT INTO users (username, password, role) VALUES (%s, %s, %s) RETURNING id
                ''', (username, generate_password_hash(password), 'parent'))
                parent_id = cur.fetchone()[0]  # type: ignore

                # Link parent to students
                if student_ids_str_list:  # Only iterate if at least one student was selected
                    for student_id_str in student_ids_str_list:
                        # --- IMPORTANT: Validate and convert to integer ---
                        if not student_id_str.strip():  # Check for empty string after stripping whitespace
                            flash(
                                'Invalid (empty) student ID found. Skipping link for an empty ID.', 'warning')
                            continue  # Skip to the next student_id in the list

                        try:
                            # Convert the string to an integer
                            student_id_int = int(student_id_str)
                            cur.execute(
                                'INSERT INTO parent_students (parent_id, student_id) VALUES (%s, %s)',
                                # Use the integer version
                                (parent_id, student_id_int))
                        except ValueError:
                            # This catches cases like 'abc' or malformed data in value attribute
                            flash(
                                f'Invalid student ID format found for "{student_id_str}". Skipping.', 'warning')
                            continue  # Skip to the next student_id in the list
                else:
                    # Optional: If no students were selected, you might want to flash a message
                    # This message won't stop the parent from being created.
                    flash(
                        'Parent created successfully, but no students were linked.', 'info')

                conn.commit()
                flash('Parent and linked students added successfully!', 'success')
                return redirect(url_for('manage_parents'))
            except Exception as e:
                conn.rollback()  # Rollback user creation if linking fails
                flash(
                    f'Error adding parent or linking students: {str(e)}', 'danger')
                # If there's an error, you still need to render the form with students
                students = get_students()
                return render_template('admin/add_parent.html', students=students)
            finally:
                cur.close()
                conn.close()

    # GET request - show form
    students = get_students()
    return render_template('admin/add_parent.html', students=students)


@admin_bp.route('/approve_requests')
@login_required
@admin_required
def approve_requests():
    conn = get_db_connection()
    try:
        # Use DictCursor to get results as dictionaries
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, user_name, user_email, user_phone, 
                   plan_name, plan_price, request_date
            FROM requests 
            WHERE status = 'pending'
            ORDER BY request_date DESC
        """)
        requests = cur.fetchall()
        return render_template('admin/approve_requests.html',
                               pending_requests=requests)
    except Exception as e:
        print(f"Error fetching requests: {e}")
        flash('Error loading requests', 'danger')
        return render_template('admin/approve_requests.html',
                               pending_requests=[])
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/subscriptions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_subscription():
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id')
            plan_id = request.form.get('plan_id')
            start_date_str = request.form.get('start_date')
            duration_days = request.form.get('duration_days')
            mark_paid = request.form.get(
                'mark_paid') is not None  # Checkbox value

            if not all([student_id, plan_id, start_date_str, duration_days]):
                flash('All fields are required', 'danger')
                return redirect(url_for('admin_add_subscription'))

            # Convert data types
            student_id = int(student_id)  # type: ignore
            plan_id = int(plan_id)  # type: ignore
            duration_days = int(duration_days)  # type: ignore
            start_date = datetime.strptime(
                start_date_str, '%Y-%m-%d')  # type: ignore
            end_date = start_date + timedelta(days=duration_days)

            # Determine payment status and active status
            payment_status = 'paid' if mark_paid else 'pending'
            is_active = mark_paid  # Subscription is active immediately if marked as paid

            subscription_id = add_subscription_to_db(
                user_id=student_id,
                plan_id=plan_id,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active,
                payment_status=payment_status
            )

            if subscription_id:
                # If marked paid, update user role if necessary (e.g., grant premium access)
                if is_active:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            'SELECT name FROM subscription_plans WHERE id = %s', (plan_id,))
                        plan_name = cur.fetchone()[0]  # type: ignore
                        if plan_name.lower() == 'premium':  # Check plan name for role update
                            cur.execute(
                                "UPDATE users SET role = 'premium' WHERE id = %s", (student_id,))
                            conn.commit()
                    except Exception as e:
                        print(f"Error updating user role: {e}")
                    finally:
                        cur.close()
                        conn.close()

                flash('Subscription added successfully', 'success')
                return redirect(url_for('manage_subscriptions'))
            else:
                flash('Error adding subscription', 'danger')

        except ValueError:
            flash('Invalid input data', 'danger')
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            app.logger.error(f"Admin add subscription error: {str(e)}")

    # GET request
    students = get_students()
    plans = get_subscription_plans()
    print("DEBUG: Rendering admin/add_subscription.html. Checking if 'float' is in globals:",
          'float' in app.jinja_env.globals)  # Add this line
    return render_template('admin/add_subscription.html', students=students, plans=plans)


@admin_bp.route('/announcements/delete/<int:announcement_id>', methods=['POST'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM announcements WHERE id = %s',
                    (announcement_id,))
        conn.commit()
        flash('Announcement deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error deleting announcement', 'danger')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('manage_announcements'))


@admin_bp.route('/assignments/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_assignments():
    if request.method == 'POST':
        if 'json_file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)

        file = request.files['json_file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)

        if file and file.filename.endswith('.json'):  # type: ignore
            try:
                data = json.load(file)  # type: ignore

                # Handle both single assignment and array of assignments
                assignments_data = data if isinstance(data, list) else [data]

                # Determine assigned students from form selection
                form_assigned_users = []
                if 'assign_all' in request.form and request.form['assign_all'] == 'all':
                    form_assigned_users = None  # Indicates 'all students' from the form
                else:
                    selected_student_ids = request.form.getlist(
                        'selected_students')
                    if selected_student_ids:
                        form_assigned_users = [int(s_id)
                                               for s_id in selected_student_ids]
                    else:
                        form_assigned_users = []  # No specific students selected in form

                imported_count = 0
                for assignment_data in assignments_data:
                    # Validate required fields
                    required_fields = ['title', 'description',
                                       'subject', 'total_marks', 'deadline']
                    if not all(field in assignment_data for field in required_fields):
                        flash(
                            'Invalid JSON structure - missing required fields for an assignment', 'danger')
                        continue  # Skip to the next assignment in the JSON

                    try:
                        # Convert deadline string to datetime
                        deadline = datetime.strptime(
                            assignment_data['deadline'], '%Y-%m-%d %H:%M')
                    except ValueError:
                        flash(
                            'Invalid deadline format in JSON (use YYYY-MM-DD HH:MM)', 'danger')
                        continue  # Skip to the next assignment in the JSON

                    # Determine final assigned users for this specific assignment
                    # Default to 'all' if no specific assignment
                    final_assigned_users_for_this_assignment = None

                    # Prioritize 'assigned_users' from JSON if it exists
                    assigned_users_from_json = assignment_data.get(
                        'assigned_users')
                    if assigned_users_from_json is not None:
                        if assigned_users_from_json == 'all':
                            # Map JSON 'all' string to None for add_assignment, meaning all students
                            final_assigned_users_for_this_assignment = None
                        else:
                            # Use the list of user IDs from JSON
                            final_assigned_users_for_this_assignment = assigned_users_from_json
                    else:
                        # If JSON doesn't specify, use what was selected in the form
                        final_assigned_users_for_this_assignment = form_assigned_users

                    # Get the interactive content if provided
                    content = assignment_data.get('content', None)
                    if content:
                        # Convert to string for storage
                        content = json.dumps(content)

                    # Create assignment with the interactive content
                    success = add_assignment(
                        title=assignment_data['title'],
                        description=assignment_data['description'],
                        subject=assignment_data['subject'],
                        total_marks=int(assignment_data['total_marks']),
                        deadline=deadline,
                        assigned_students_ids=final_assigned_users_for_this_assignment,
                        content=content
                    )

                    if success:
                        imported_count += 1
                    else:
                        flash(
                            f'Error creating assignment: {assignment_data["title"]}', 'warning')

                flash(
                    f'Successfully imported {imported_count} assignments', 'success')
                if imported_count < len(assignments_data):
                    flash(
                        f'{len(assignments_data) - imported_count} assignments could not be imported due to errors.', 'warning')
                return redirect(url_for('manage_assignments'))

            except json.JSONDecodeError:
                flash('Invalid JSON file. Please ensure it is well-formed.', 'danger')
            except Exception as e:
                flash(f'Error importing assignments: {str(e)}', 'danger')

        else:
            flash('Only JSON files are allowed', 'danger')

    # GET request - show import form
    conn = None
    cur = None
    students = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Fetch all students to populate the checkboxes in the form
        cur.execute(
            "SELECT id, username FROM users WHERE role = 'student' ORDER BY username")
        students = [{'id': row[0], 'username': row[1]}
                    for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching students for import form: {e}")
        flash('Could not load student list. Please check database connection.', 'danger')
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('admin/assignments/import.html', students=students)


@admin_bp.route('/submissions/all')
@login_required
# @roles_required('admin', 'teacher') # Assuming only admins/teachers can view all submissions
def list_all_submissions():
    conn = None
    cur = None
    submissions_data = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                s.id,
                a.title AS assignment_title,
                u.username AS student_username,
                s.submission_time,
                s.grade,
                s.file_path,
                s.submission_text,
                s.interactive_submission_data,
                s.assignment_id -- Add assignment_id here
            FROM
                submissions s
            JOIN
                assignments a ON s.assignment_id = a.id
            JOIN
                users u ON s.student_id = u.id
            ORDER BY
                s.submission_time DESC;
            """
        )
        for row in cur.fetchall():
            submissions_data.append({
                'id': row[0],
                'assignment_title': row[1],
                'student_username': row[2],
                'submission_time': row[3],
                'grade': row[4],
                'file_path': row[5],
                'submission_text': row[6],
                'interactive_submission_data': row[7],
                'assignment_id': row[8]  # Add assignment_id to the dictionary
            })
    except Exception as e:
        print(f"Error fetching all submissions: {e}")
        flash("Could not load all submissions.", "danger")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('admin/all_submissions.html', submissions=submissions_data)

# Student assignment routes


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    try:

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT username, assignment_id, title, subject, deadline, total_marks
                FROM assignments a
                JOIN assignment_students au ON a.id = au.assignment_id
                JOIN users u ON u.id = au.student_id;
        ''')
        assignments = cur.fetchall()
        cur.close()
        conn.close()

        print(assignments)
        return render_template(
            'admin/dashboard.html',
            assignments=assignments,
            current_time=datetime.utcnow()
        )
    except Exception as e:
        app.logger.error(f"Error fetching assignments: {str(e)}")
        return render_template('dashboard.html',
                               assignments=[],
                               current_time=datetime.utcnow())

# Add these new routes to app.py


@admin_bp.route('/assignments/<int:assignment_id>/submissions/<int:student_id>/grade', methods=['GET', 'POST'])
@login_required
@admin_required
def grade_submission(assignment_id, student_id):
    # Get student details
    student = get_user_by_id(student_id)
    if not student:
        flash('Student not found', 'danger')
        return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))

    # Get submission and assignment details
    data = get_submission_for_grading(assignment_id, student_id)
    if not data:
        flash('Submission not found', 'danger')
        return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))

    if request.method == 'POST':
        marks_obtained = request.form.get('marks_obtained')
        feedback = request.form.get('feedback', '')

        try:
            marks_obtained = float(marks_obtained)  # type: ignore
            if marks_obtained < 0 or marks_obtained > data['assignment']['total_marks']:
                flash('Invalid marks value', 'danger')
                return redirect(url_for('grade_submission', assignment_id=assignment_id, student_id=student_id))

            if update_submission_grade(assignment_id, student_id, marks_obtained, feedback):
                flash('Grade submitted successfully', 'success')
                return redirect(url_for('view_assignment_submissions', assignment_id=assignment_id))
            else:
                flash('Error submitting grade', 'danger')
        except ValueError:
            flash('Invalid marks format', 'danger')

    return render_template('admin/assignments/grade.html',
                           assignment_id=assignment_id,
                           student=student,
                           submission=data['submission'],
                           assignment=data['assignment'])


@admin_bp.route('/approve_request/<int:request_id>')
@admin_required  # Add your admin auth decorator
def approve_request(request_id):
    # Update request status in DB
    update_request_status(request_id, 'approved')

    # Get request details
    request = get_request_details(request_id)

    # Create subscription for user
    create_subscription(request['user_email'],  # type: ignore
                        request['plan_id'])  # type: ignore

    # Send confirmation email to user
    send_approval_notification(
        request.user_email, request.plan_name)  # type: ignore

    flash('Request approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@admin_bp.route('/reject_request/<int:request_id>')
@admin_required
def reject_request(request_id):
    # Update request status
    update_request_status(request_id, 'rejected')

    # Get request details
    request = get_request_details(request_id)

    # Send rejection email
    send_rejection_notification(
        request.user_email, request.plan_name)  # type: ignore

    flash('Request rejected.', 'info')
    return redirect(url_for('admin_dashboard'))


@admin_bp.route('/announcements')
@login_required
@admin_required
def manage_announcements():
    announcements = get_all_announcements()
    return render_template('admin/announcements/list.html', announcements=announcements)


@admin_bp.route('/announcements/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_announcement():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        send_to = request.form.getlist('send_to')  # List of user IDs or 'all'

        if not title or not message:
            flash('Title and message are required', 'danger')
            return redirect(url_for('add_announcement'))

        try:
            # If "all" is selected, send to all students
            user_ids = None if 'all' in send_to else [
                int(user_id) for user_id in send_to]

            create_announcement(
                title=title,
                message=message,
                created_by=session['user_id'],
                user_ids=user_ids
            )

            flash('Announcement created successfully!', 'success')
            return redirect(url_for('manage_announcements'))
        except Exception as e:
            flash(f'Error creating announcement: {str(e)}', 'danger')
            return redirect(url_for('add_announcement'))

    # GET request - show form
    students = get_students()
    return render_template('admin/announcements/add.html', students=students)


# type: ignore
# type: ignore
# type: ignore
@admin_bp.route('/parents/edit/<int:parent_id>', methods=['GET', 'POST']) #type: ignore
@login_required
@admin_required
def edit_parent(parent_id):
    conn = get_db_connection()
    cur = conn.cursor()
    parent = None  # Initialize parent variable

    try:
        # GET request: Display the current parent's data in the form
        if request.method == 'GET':
            cur.execute(
                "SELECT id, username FROM users WHERE id = %s AND role = 'parent'", (parent_id,))
            parent = cur.fetchone()

            if not parent:
                flash('Parent not found.', 'danger')
                return redirect(url_for('manage_parents'))

            # Fetch students linked to this parent
            cur.execute('''
                SELECT s.id, s.username
                FROM users s
                JOIN parent_students ps ON s.id = ps.student_id
                WHERE ps.parent_id = %s
            ''', (parent_id,))
            linked_students = [row[0] for row in cur.fetchall(
            )]  # Get a list of IDs of linked students

            all_students = get_students()  # Get all students for the checkboxes

            return render_template('admin/edit_parent.html',
                                   parent=parent,
                                   all_students=all_students,  # Pass all students for checkbox list
                                   linked_students=linked_students)  # Pass linked student IDs to pre-check checkboxes

        # POST request: Process the form submission to update parent
        elif request.method == 'POST':
            new_username = request.form['username']
            # Password can be optional for edit
            new_password = request.form.get('password')
            student_ids_str_list = request.form.getlist('student_ids')

            # Check if username already exists for another user
            cur.execute(
                "SELECT id FROM users WHERE username = %s AND id != %s", (new_username, parent_id))
            if cur.fetchone():
                flash('Username already exists for another user.', 'danger')
                # Re-render the form with current data and students
                cur.execute(
                    "SELECT id, username FROM users WHERE id = %s AND role = 'parent'", (parent_id,))
                parent = cur.fetchone()
                cur.execute('''
                    SELECT s.id, s.username FROM users s JOIN parent_students ps ON s.id = ps.student_id WHERE ps.parent_id = %s
                ''', (parent_id,))
                linked_students = [row[0] for row in cur.fetchall()]
                all_students = get_students()
                return render_template('admin/edit_parent.html',
                                       parent=parent,
                                       all_students=all_students,
                                       linked_students=linked_students)

            # Update parent user data
            if new_password:
                hashed_password = generate_password_hash(new_password)
                cur.execute("UPDATE users SET username = %s, password = %s WHERE id = %s",
                            (new_username, hashed_password, parent_id))
            else:
                cur.execute("UPDATE users SET username = %s WHERE id = %s",
                            (new_username, parent_id))

            # Update parent-student links:
            # 1. Delete all existing links for this parent
            cur.execute(
                "DELETE FROM parent_students WHERE parent_id = %s", (parent_id,))

            # 2. Insert new links based on selected checkboxes
            if student_ids_str_list:
                for student_id_str in student_ids_str_list:
                    if not student_id_str.strip():
                        flash(
                            'Invalid (empty) student ID found. Skipping link for an empty ID.', 'warning')
                        continue
                    try:
                        student_id_int = int(student_id_str)
                        cur.execute("INSERT INTO parent_students (parent_id, student_id) VALUES (%s, %s)",
                                    (parent_id, student_id_int))
                    except ValueError:
                        flash(
                            f'Invalid student ID format found for "{student_id_str}". Skipping.', 'warning')
                        continue

            conn.commit()
            flash('Parent updated successfully!', 'success')
            return redirect(url_for('manage_parents'))

    except Exception as e:
        conn.rollback()
        flash(f'Error editing parent: {str(e)}', 'danger')
        # On error, try to re-render the form with existing data if available
        if parent:
            all_students = get_students()
            cur.execute('''
                SELECT s.id, s.username FROM users s JOIN parent_students ps ON s.id = ps.student_id WHERE ps.parent_id = %s
            ''', (parent_id,))
            linked_students = [row[0] for row in cur.fetchall()]
            return render_template('admin/edit_parent.html',
                                   parent=parent,
                                   all_students=all_students,
                                   linked_students=linked_students)
        # Fallback if parent not found on error
        return redirect(url_for('manage_parents'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# In your app.py file, usually alongside your other admin routes


@admin_bp.route('/parents/<int:parent_id>/link_students', methods=['GET'])
@login_required
@admin_required
def link_parent_student_ui(parent_id):
    conn = get_db_connection()
    cur = conn.cursor()
    parent_info = None
    all_students = []
    linked_student_ids = []

    try:
        # Get parent details to display on the page
        cur.execute(
            "SELECT id, username FROM users WHERE id = %s AND role = 'parent'", (parent_id,))
        parent_info = cur.fetchone()

        if not parent_info:
            flash('Parent not found.', 'danger')
            return redirect(url_for('manage_parents'))

        # Get all students to populate the checkboxes
        # Assuming get_students() fetches all students for the admin
        all_students = get_students()

        # Get the IDs of students already linked to this parent
        cur.execute('''
            SELECT student_id FROM parent_students WHERE parent_id = %s
        ''', (parent_id,))
        linked_student_ids = [row[0] for row in cur.fetchall()]

        return render_template('admin/link_parent_student.html',
                               parent=parent_info,
                               all_students=all_students,
                               linked_student_ids=linked_student_ids)

    except Exception as e:
        flash(f'Error loading student linking page: {str(e)}', 'danger')
        return redirect(url_for('manage_parents'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# In your app.py file


@admin_bp.route('/parents/<int:parent_id>/update_links', methods=['POST'])
@login_required
@admin_required
def update_parent_student_links(parent_id):
    # Get the selected student IDs as strings
    student_ids_str_list = request.form.getlist('student_ids')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Step 1: Delete all existing links for this parent
        cur.execute(
            "DELETE FROM parent_students WHERE parent_id = %s", (parent_id,))

        # Step 2: Insert new links based on the submitted data
        if student_ids_str_list:
            for student_id_str in student_ids_str_list:
                if not student_id_str.strip():
                    flash(
                        f'Invalid (empty) student ID found in submission. Skipping.', 'warning')
                    continue
                try:
                    student_id_int = int(student_id_str)
                    cur.execute("INSERT INTO parent_students (parent_id, student_id) VALUES (%s, %s)",
                                (parent_id, student_id_int))
                except ValueError:
                    flash(
                        f'Invalid student ID format "{student_id_str}" in submission. Skipping.', 'warning')
                    continue
        else:
            # No students were selected, so all previous links for this parent have been removed
            flash(
                'No students selected. All previous links for this parent have been removed.', 'info')

        conn.commit()
        flash('Parent-student links updated successfully!', 'success')
        # Redirect back to the parent management page
        return redirect(url_for('manage_parents'))

    except Exception as e:
        conn.rollback()
        flash(f'Error updating parent-student links: {str(e)}', 'danger')
        # On error, redirect back to the linking UI page to allow retrying
        return redirect(url_for('link_parent_student_ui', parent_id=parent_id))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@admin_bp.route('/parents')
@login_required
@admin_required
def manage_parents():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get all parents with their linked students
        cur.execute('''
            SELECT u.id, u.username, 
                   STRING_AGG(s.username, ', ') as students,
                   COUNT(ps.student_id) as student_count
            FROM users u
            LEFT JOIN parent_students ps ON u.id = ps.parent_id
            LEFT JOIN users s ON ps.student_id = s.id
            WHERE u.role = 'parent'
            GROUP BY u.id
            ORDER BY u.username
        ''')
        parents = [{
            'id': row[0],
            'username': row[1],
            'students': row[2] or 'No students linked',
            'student_count': row[3]
        } for row in cur.fetchall()]

        return render_template('admin/parents.html', parents=parents)
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/parents/link', methods=['POST'])
@login_required
@admin_required
def link_parent_student():
    parent_id = request.form['parent_id']
    student_id = request.form['student_id']
    action = request.form['action']  # 'link' or 'unlink'

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if action == 'link':
            cur.execute('''
                INSERT INTO parent_students (parent_id, student_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            ''', (parent_id, student_id))
        else:
            cur.execute('''
                DELETE FROM parent_students
                WHERE parent_id = %s AND student_id = %s
            ''', (parent_id, student_id))

        conn.commit()
        flash('Relationship updated successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating relationship: {str(e)}', 'danger')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('manage_parents'))


@admin_bp.route('/tutorials')
@login_required
@admin_required
def manage_tutorials():
    videos = get_all_videos()  # This should return a list of videos
    categories = get_all_categories()  # This should return a list of categories

    # Convert to the structure your template expects
    tutorials_dict = {
        category[1]: {  # category name as key
            # videos for this category
            'videos': [v for v in videos if v[3] == category[1]],
            'id': category[0]  # category id
        }
        for category in categories
    }

    return render_template('admin/tutorials.html',
                           tutorials=tutorials_dict,
                           videos=videos,
                           categories=categories)


@admin_bp.route('/tutorials/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_tutorial():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            url = request.form.get('url', '').strip()
            category_id = request.form.get('category_id', '').strip()

            if not all([title, url, category_id]):
                flash('All fields are required', 'danger')
                return redirect(url_for('add_tutorial'))

            add_video(title, url, category_id)
            flash('Tutorial added successfully', 'success')
            return redirect(url_for('manage_tutorials'))

        except Exception as e:
            flash(f'Error adding tutorial: {str(e)}', 'danger')
            return redirect(url_for('add_tutorial'))

    # GET request - show the form
    categories = get_all_categories()
    return render_template('admin/add_tutorial.html', categories=categories)


@admin_bp.route('/tutorials/delete/<int:video_id>')
@login_required
@admin_required
def delete_tutorial(video_id):
    delete_video(video_id)
    flash('Tutorial video deleted successfully', 'success')
    return redirect(url_for('manage_tutorials'))


@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    students = get_students()
    categories = get_all_categories()
    upcoming_sessions = get_upcoming_sessions()

    # Get active subscription count
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE")
    active_subscriptions_count = cur.fetchone()[0]  # type: ignore
    cur.execute('''
            SELECT username, assignment_id, title, subject, deadline, total_marks, created_at
                FROM assignments a
                JOIN assignment_students au ON a.id = au.assignment_id
                JOIN users u ON u.id = au.student_id;
        ''')
    assignments = cur.fetchall()
    cur.close()
    conn.close()

    print(assignments[0][0])
    return render_template('admin/dashboard.html',
                           assignments=assignments,
                           student_count=len(students),
                           category_count=len(categories),
                           upcoming_sessions=upcoming_sessions,
                           active_subscriptions_count=active_subscriptions_count)


@admin_bp.route('/sessions/bookings/<int:session_id>')
@login_required
@admin_required
def view_session_bookings(session_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Get session details
    cur.execute(
        'SELECT title FROM tutorial_sessions WHERE id = %s', (session_id,))
    session_title = cur.fetchone()[0]  # type: ignore

    # Get users who booked this session
    cur.execute('''
        SELECT u.id, u.username 
        FROM student_bookings sb
        JOIN users u ON sb.student_id = u.id
        WHERE sb.session_id = %s
    ''', (session_id,))
    booked_users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('admin/session_bookings.html',
                           session_title=session_title,
                           booked_users=booked_users)


@admin_bp.route('/sessions')
@login_required
@admin_required
def manage_sessions():
    sessions = get_all_sessions()
    upcoming_sessions = get_upcoming_sessions()
    return render_template('admin/sessions.html',
                           sessions=sessions,
                           upcoming_sessions=upcoming_sessions)


@admin_bp.route('/sessions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_session():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        max_students = request.form.get('max_students')

        try:
            create_session(title, description, start_time,
                           end_time, int(max_students))  # type: ignore
            flash('Session created successfully', 'success')
            return redirect(url_for('manage_sessions'))
        except Exception as e:
            flash(f'Error creating session: {str(e)}', 'danger')

    return render_template('admin/add_session.html')


@admin_bp.route('/sessions/delete/<int:session_id>')
@login_required
@admin_required
def delete_session(session_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tutorial_sessions WHERE id = %s', (session_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Session deleted successfully', 'success')
    return redirect(url_for('manage_sessions'))
