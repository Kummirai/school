from flask import Blueprint, render_template, abort
from flask_login import login_required

courses_bp = Blueprint('courses', __name__, template_folder='templates')


@courses_bp.route('/html_course')
@login_required
def html_course():
    try:
        return render_template('/courses/html_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/css_course')
@login_required
def css_course():
    try:
        return render_template('/courses/css_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/js_course')
@login_required
def js_course():
    try:
        return render_template('/courses/js_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/bootstrap_course')
@login_required
def bootstrap_course():
    try:
        return render_template('/courses/bootstrap_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/jquery_course')
@login_required
def jquery_course():
    try:
        return render_template('/courses/jquery_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/react_course')
@login_required
def react_course():
    try:
        return render_template('/courses/react_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('nodejs_course')
@login_required
def nodejs_course():
    try:
        return render_template('/courses/node_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('express_course')
@login_required
def express_course():
    try:
        return render_template('/courses/express_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('sql_course')
@login_required
def sql_course():
    try:
        return render_template('/courses/sql_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('mongodb_course')
@login_required
def mongodb_course():
    try:
        return render_template('/courses/mongodb_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('auth_course')
@login_required
def auth_course():
    try:
        return render_template('/courses/auth_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('deployment_course')
@login_required
def deployment_course():
    try:
        return render_template('/courses/deployment_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('catalog')
@login_required
def catalog():
    try:
        return render_template('/courses/catalog.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/python_basics_course')
@login_required
def python_basics_course():
    try:
        return render_template('/courses/python_basics_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/oop_python_course')
@login_required
def oop_python_course():
    try:
        return render_template('/courses/oop_python_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/python_web_course')
@login_required
def python_web_course():
    try:
        return render_template('/courses/python_web_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/django_course')
@login_required
def django_course():
    try:
        return render_template('/courses/django_course.html')
    except Exception as e:
        abort(500, description=str(e))


# advanced python course
@courses_bp.route('/advanced_python_course')
@login_required
def advanced_python_course():
    try:
        return render_template('/courses/advanced_python_course.html')
    except Exception as e:
        abort(500, description=str(e))

#data_science_course
@courses_bp.route('/data_science_course')
@login_required
def data_science_course():
    try:
        return render_template('/courses/data_science_course.html')
    except Exception as e:
        abort(500, description=str(e))

#ml_python_course
@courses_bp.route('/ml_python_course')
@login_required
def ml_python_course():
    try:
        return render_template('/courses/ml_python_course.html')
    except Exception as e:
        abort(500, description=str(e))


#automation_python_course
@courses_bp.route('/automation_python_course')
@login_required
def automation_python_course():
    try:
        return render_template('/courses/automation_python_course.html')
    except Exception as e:
        abort(500, description=str(e))

#python_deployment_course
@courses_bp.route('/python_deployment_course')
@login_required
def python_deployment_course():
    try:
        return render_template('/courses/python_deployment_course.html')
    except Exception as e:
        abort(500, description=str(e))

#algorithms_python_course
@courses_bp.route('/algorithms_python_course')
@login_required
def algorithms_python_course():
    try:
        return render_template('/courses/algorithms_python_course.html')
    except Exception as e:
        abort(500, description=str(e))

