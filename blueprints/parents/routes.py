# type: ignore
@app.route('/admin/parents/edit/<int:parent_id>', methods=['GET', 'POST'])
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


@app.route('/admin/parents/<int:parent_id>/link_students', methods=['GET'])
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


@app.route('/admin/parents/<int:parent_id>/update_links', methods=['POST'])
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


@app.route('/admin/parents')
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


@app.route('/admin/parents/link', methods=['POST'])
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


@app.route('/parent/assignments')
@login_required
# @parent_required # If you have a specific decorator for parent role
def parent_view_assignments():
    parent_id = session.get('user_id')
    if not parent_id:
        flash('You must be logged in as a parent to view assignments.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    # Again, using DictCursor is good for fetching parent's students
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    students_with_assignments = []
    try:
        # Get all students linked to this parent
        cur.execute('''
            SELECT u.id AS student_id, u.username AS student_username
            FROM users u
            JOIN parent_students ps ON u.id = ps.student_id
            WHERE ps.parent_id = %s AND u.role = 'student'
            ORDER BY u.username;
        ''', (parent_id,))
        linked_students = cur.fetchall()

        for student_info in linked_students:
            student_id = student_info['student_id']
            student_username = student_info['student_username']

            assignments_for_student = get_student_assignments(student_id)

            students_with_assignments.append({
                'id': student_id,
                'username': student_username,
                'assignments': assignments_for_student
            })

    except Exception as e:
        flash(f'Error loading assignments: {str(e)}', 'danger')
        print(f"Error in parent_view_assignments route: {e}")  # For debugging
        # Redirect to a safe page on error
        return redirect(url_for('parent_dashboard'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('parent/assignments.html', students_with_assignments=students_with_assignments)


@app.route('/parent/dashboard')
@login_required
def parent_dashboard():
    if session.get('role') != 'parent':
        abort(403)

    students = get_students_for_parent(session['user_id'])
    if not students:
        flash('No students linked to your account', 'warning')
        return render_template('parent/dashboard.html',
                               students=[],
                               selected_student=None,
                               stats=None,
                               assignments=[],
                               submissions=[],
                               bookings=[],
                               announcements=[])

    # Default to first student
    selected_student_id = request.args.get('student_id', students[0]['id'])
    try:
        selected_student_id = int(selected_student_id)
    except (ValueError, TypeError):
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parent_dashboard'))

    selected_student = next(
        (s for s in students if s['id'] == selected_student_id), None)

    if not selected_student:
        flash('Invalid student selected', 'danger')
        return redirect(url_for('parent_dashboard'))

    # Get all data for the selected student
    assignments = get_assignments_for_user(selected_student_id)
    submissions = get_student_submissions(selected_student_id)
    bookings = get_student_bookings(selected_student_id)
    stats = get_student_performance_stats(selected_student_id)
    announcements = get_user_announcements(selected_student_id, limit=5)

    return render_template('parent/dashboard.html',
                           students=students,
                           selected_student=selected_student,
                           assignments=assignments,
                           submissions=submissions,
                           bookings=bookings,
                           stats=stats,
                           announcements=announcements)


@app.route('/parent/submissions/<int:student_id>')
@login_required
# @parent_required
def parent_view_submissions(student_id):
    # Verify parent has access to this student
    students = get_students_for_parent(session['user_id'])
    if not any(s['id'] == student_id for s in students):
        abort(403)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                a.title, 
                a.subject, 
                a.deadline, 
                s.submission_time, 
                s.grade, 
                a.total_marks,
                s.feedback,
                s.file_path
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE s.student_id = %s
            ORDER BY a.deadline DESC
        ''', (student_id,))

        # Convert to list of dictionaries with proper field names
        submissions = []
        for row in cur.fetchall():
            submissions.append({
                'title': row[0],
                'subject': row[1],
                'deadline': row[2],  # This should be a datetime object
                'submitted_at': row[3],
                'marks_obtained': row[4],
                'total_marks': row[5],
                'feedback': row[6],
                'file_path': row[7]
            })

        return render_template('parent/submissions.html',
                               student_id=student_id,
                               submissions=submissions)
    finally:
        cur.close()
        conn.close()


@app.route('/parent/sessions/<int:student_id>')
@login_required
def parent_view_sessions(student_id):
    if session.get('role') != 'parent':
        abort(403)

    # Verify parent has access to this student
    students = get_students_for_parent(session['user_id'])
    if not any(s['id'] == student_id for s in students):
        abort(403)

    bookings = get_student_bookings(student_id)
    upcoming_sessions = get_upcoming_sessions()
    return render_template('parent/sessions.html',
                           student_id=student_id,
                           bookings=bookings,
                           upcoming_sessions=upcoming_sessions)
