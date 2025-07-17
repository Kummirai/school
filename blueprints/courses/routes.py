from flask import Blueprint, render_template, abort
from flask_login import login_required

courses_bp = Blueprint('courses', __name__, template_folder='templates')


@courses_bp.route('/html_course')
@login_required
def html_course():
    try:
        return render_template('html_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/css_course')
@login_required
def css_course():
    try:
        return render_template('css_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/js_course')
@login_required
def js_course():
    try:
        return render_template('js_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/bootstrap_course')
@login_required
def bootstrap_course():
    try:
        return render_template('bootstrap_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/jquery_course')
@login_required
def jquery_course():
    try:
        return render_template('jquery_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('/react_course')
@login_required
def react_course():
    try:
        return render_template('react_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('nodejs_course')
@login_required
def nodejs_course():
    try:
        return render_template('node_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('express_course')
@login_required
def express_course():
    try:
        return render_template('express_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('sql_course')
@login_required
def sql_course():
    try:
        return render_template('sql_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('mongodb_course')
@login_required
def mongodb_course():
    try:
        return render_template('mongodb_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('auth_course')
@login_required
def auth_course():
    try:
        return render_template('auth_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('deployment_course')
@login_required
def deployment_course():
    try:
        return render_template('deployment_course.html')
    except Exception as e:
        abort(500, description=str(e))


@courses_bp.route('catalog')
@login_required
def catalog():
    try:
        return render_template('catalog.html')
    except Exception as e:
        abort(500, description=str(e))
