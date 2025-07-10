from flask import Blueprint, render_template, abort
import json
import os
# Create a Blueprint for the grades routes
grades_bp = Blueprint('grades', __name__, url_prefix='/grades')
app = grades_bp


@app.route('/grade/<int:grade_num>/maths/chapter/<int:chapter_num>/<filename>')
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


@app.route('/grade7/maths')
def grade_7_maths():
    try:
        # Load the JSON data with explicit UTF-8 encoding
        with open('static/data/grade7_math.json', 'r', encoding='utf-8') as f:
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
    except UnicodeDecodeError:
        abort(500, description="Invalid file encoding - must be UTF-8")


@app.route('/grade8/maths')
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


@app.route('/grade9/maths')
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


@app.route('/grade10/maths')
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


@app.route('/grade11/maths')
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


@app.route('/grade12/maths')
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


@app.route('/algebra-calculator')
def algebra_calculator():
    return render_template('algebra_calculator.html')
