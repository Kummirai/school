from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
import psycopg2.extras
from flask_login import login_required
from decorators.decorator import admin_required
from models import get_db_connection
from subscriptions.utils import add_subscription_to_db, get_subscription_plans
from students.utils import get_students
from flask import current_app as app
import json
from assignments.utils import add_assignment
from helpers import get_submission_for_grading, update_submission_grade, get_user_by_id, get_request_details, update_request_status,  send_approval_notification, send_rejection_notification
from subscriptions.utils import get_subscription_plans
from students.utils import get_user_by_username, get_students
from werkzeug.security import generate_password_hash
from announcements.utils import get_all_announcements, create_announcement


admin = Blueprint('admin', __name__)


# Add these routes to app.py
@app.route('/admin/parents/add', methods=['GET', 'POST'])
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


@app.route('/admin/approve_requests')
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


@app.route('/admin/subscriptions/add', methods=['GET', 'POST'])
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


@app.route('/admin/announcements/delete/<int:announcement_id>', methods=['POST'])
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


@app.route('/admin/assignments/import', methods=['GET', 'POST'])
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


@app.route('/admin/submissions/all')
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


@app.route('/admin/dashboard')
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


@app.route('/admin/assignments/<int:assignment_id>/submissions/<int:student_id>/grade', methods=['GET', 'POST'])
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


@app.route('/admin/approve_request/<int:request_id>')
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


@app.route('/admin/reject_request/<int:request_id>')
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


@app.route('/admin/announcements')
@login_required
@admin_required
def manage_announcements():
    announcements = get_all_announcements()
    return render_template('admin/announcements/list.html', announcements=announcements)


@app.route('/admin/announcements/add', methods=['GET', 'POST'])
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
