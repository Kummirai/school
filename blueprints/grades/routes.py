from flask import Blueprint, render_template, url_for, request, jsonify, redirect, abort
import json
import os
from flask_login import login_required
from flask import current_app as app

# Create a Blueprint for the grades routes
grades_bp = Blueprint('grades', __name__,
                      template_folder='templates', static_folder='static')


@grades_bp.route('/grade/<int:grade_num>/maths/chapter/<int:chapter_num>/<filename>')
def study_guide_page(grade_num, chapter_num, filename):
    # Construct the path to the grade-specific JSON file
    json_file_path = os.path.join(
        app.root_path, 'static', 'data', f'grade{grade_num}_math.json')

    try:
        with open(json_file_path, 'r') as f:
            subject_data = json.load(f)
    except FileNotFoundError:
        abort(404)  # Or render a custom error page

    lesson_data = None
    # Iterate through terms, units, and lessons to find the matching study guide
    for term in subject_data.get('terms', []):
        for unit in term.get('units', []):
            for lesson in unit.get('lessons', []):
                # Check if 'study_guide_filename' exists and matches
                if lesson.get('study_guide_filename') == filename:
                    lesson_data = lesson
                    break
            if lesson_data:
                break
        if lesson_data:
            break

    if not lesson_data:
        abort(404)  # Study guide not found in JSON data

    # Render the specific study guide template
    # Assuming study guides are in templates/grade_X/maths/chapter_Y/
    template_path = f'grade_{grade_num}/maths/chapter_{chapter_num}/{filename}'
    return render_template(template_path, lesson=lesson_data)


@grades_bp.route('/grade7/<string:subject>')
def grade_7_subject(subject):
    if subject not in ['maths', 'english']:
        abort(404)
    try:
        json_file_path = os.path.join(
            app.root_path, 'static', 'data', f'grade7_{subject}.json')
        with open(json_file_path, 'r', encoding='utf-8') as f:
            subject_data = json.load(f)

        progress = 0

        template_name = f'{subject}.html'

        return render_template(
            template_name,
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")
    except UnicodeDecodeError:
        abort(500, description="Invalid file encoding - must be UTF-8")


@grades_bp.route('/grade7/<string:subject>/lesson/<int:term_idx>/<int:unit_idx>/<int:lesson_idx>')
def view_lesson(subject, term_idx, unit_idx, lesson_idx):
    print(
        f"Loading {subject} lesson for Term: {term_idx}, Unit: {unit_idx}, Lesson: {lesson_idx}")
    try:
        # Load the JSON data for the given subject
        json_file_path = os.path.join(
            app.root_path, 'static', 'data', f'grade7_{subject}.json')
        with open(json_file_path, 'r', encoding='utf-8') as f:
            subject_data = json.load(f)

        # Validate term index
        terms = subject_data.get('terms', [])
        if term_idx < 0 or term_idx >= len(terms):
            abort(404, description="Term not found")
        term = terms[term_idx]

        # Validate unit index
        units = term.get('units', [])
        if unit_idx < 0 or unit_idx >= len(units):
            abort(404, description="Unit not found")
        unit = units[unit_idx]

        # Validate lesson index
        lessons = unit.get('lessons', [])
        if lesson_idx < 0 or lesson_idx >= len(lessons):
            abort(404, description="Lesson not found")
        lesson = lessons[lesson_idx]

        # Calculate global lesson number
        global_lesson_num = 0
        for t in terms[:term_idx]:
            for u in t.get('units', []):
                global_lesson_num += len(u.get('lessons', []))

        for u in units[:unit_idx]:
            global_lesson_num += len(u.get('lessons', []))

        global_lesson_num += lesson_idx + 1  # +1 to make it 1-based index

        # Get previous and next lessons for navigation
        prev_lesson = next_lesson = None

        # Previous lesson logic
        if lesson_idx > 0:
            prev_lesson = {
                'term_idx': term_idx,
                'unit_idx': unit_idx,
                'lesson_idx': lesson_idx - 1
            }
        elif unit_idx > 0:
            prev_unit = units[unit_idx - 1]
            prev_unit_lessons = prev_unit.get('lessons', [])
            if prev_unit_lessons:
                prev_lesson = {
                    'term_idx': term_idx,
                    'unit_idx': unit_idx - 1,
                    'lesson_idx': len(prev_unit_lessons) - 1
                }
        elif term_idx > 0:
            prev_term = terms[term_idx - 1]
            prev_term_units = prev_term.get('units', [])
            if prev_term_units:
                prev_unit = prev_term_units[-1]
                prev_unit_lessons = prev_unit.get('lessons', [])
                if prev_unit_lessons:
                    prev_lesson = {
                        'term_idx': term_idx - 1,
                        'unit_idx': len(prev_term_units) - 1,
                        'lesson_idx': len(prev_unit_lessons) - 1
                    }

        # Next lesson logic
        if lesson_idx < len(lessons) - 1:
            next_lesson = {
                'term_idx': term_idx,
                'unit_idx': unit_idx,
                'lesson_idx': lesson_idx + 1
            }
        elif unit_idx < len(units) - 1:
            next_unit = units[unit_idx + 1]
            next_unit_lessons = next_unit.get('lessons', [])
            if next_unit_lessons:
                next_lesson = {
                    'term_idx': term_idx,
                    'unit_idx': unit_idx + 1,
                    'lesson_idx': 0
                }
        elif term_idx < len(terms) - 1:
            next_term = terms[term_idx + 1]
            next_term_units = next_term.get('units', [])
            if next_term_units:
                next_unit = next_term_units[0]
                next_unit_lessons = next_unit.get('lessons', [])
                if next_unit_lessons:
                    next_lesson = {
                        'term_idx': term_idx + 1,
                        'unit_idx': 0,
                        'lesson_idx': 0
                    }

        return render_template(
            'lesson_detail.html',
            lesson=lesson,
            subject_data=subject_data,
            subject=subject,
            term_idx=term_idx,
            unit_idx=unit_idx,
            lesson_idx=lesson_idx,
            global_lesson_num=global_lesson_num,
            prev_lesson=prev_lesson,
            next_lesson=next_lesson
        )

    except FileNotFoundError:
        abort(
            404, description=f"Grade 7 {subject.capitalize()} data not found.")
    except json.JSONDecodeError:
        abort(
            500, description=f"Error loading Grade 7 {subject.capitalize()} data.")
    except Exception as e:
        print(f"An error occurred while loading {subject} lesson: {e}")
        abort(500, description="An internal server error occurred.")


@grades_bp.route('/grade8/maths')
def grade_8_maths():
    try:
        # Load the JSON data
        with open('static/data/grade8_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@grades_bp.route('/grade9/maths')
def grade_9_maths():
    try:
        # Load the JSON data
        with open('static/data/grade9_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@grades_bp.route('/grade10/maths')
def grade_10_maths():
    try:
        # Load the JSON data
        with open('static/data/grade10_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@grades_bp.route('/grade11/maths')
def grade_11_maths():
    try:
        # Load the JSON data
        with open('static/data/grade11_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@grades_bp.route('/grade12/maths')
def grade_12_maths():
    try:
        # Load the JSON data
        with open('static/data/grade12_math.json', 'r') as f:
            subject_data = json.load(f)

        # Calculate progress (you would get this from the database in a real app)
        progress = 15  # Example value

        return render_template(
            'maths.html',
            subject_data=subject_data,
            progress=progress
        )
    except FileNotFoundError:
        abort(404, description="Curriculum not found")
    except json.JSONDecodeError:
        abort(500, description="Error loading curriculum data")


@grades_bp.route('/grade7/numeric_geometric_patterns')
@login_required
def numeric_geometric_patterns():
    return render_template('grade7_maths/numeric_geometric_patterns.html')


@grades_bp.route('/mark_lesson_complete', methods=['POST'])
def mark_lesson_complete():
    data = request.get_json()
    term_idx = data.get('term_idx')
    unit_idx = data.get('unit_idx')
    lesson_idx = data.get('lesson_idx')

    # Here, you would implement the logic to mark the lesson as complete.
    # This might involve:
    # 1. Loading the user's progress data (e.g., from a database or session).
    # 2. Updating the status of the specific lesson.
    # 3. Saving the updated progress.

    # For demonstration, let's just return a success message.
    if term_idx is not None and unit_idx is not None and lesson_idx is not None:
        # In a real application, update your data model here
        print(
            f"Lesson T{term_idx}, U{unit_idx}, L{lesson_idx} marked complete for user.")
        return jsonify({'success': True, 'message': 'Lesson marked as complete!'})
    else:
        return jsonify({'success': False, 'message': 'Invalid lesson data provided.'}), 400
