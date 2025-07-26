from flask import Blueprint, render_template, abort
from flask_login import login_required

curriculum_bp = Blueprint('curriculum', __name__,
                          template_folder='templates')


@curriculum_bp.route('/math')
@login_required
def math_curriculum():
    return render_template('math_curriculum.html')


@curriculum_bp.route('/science')
@login_required
def science_curriculum():
    return render_template('science_curriculum.html')


@curriculum_bp.route('/web_development')
@login_required
def web_development_curriculum():
    return render_template('webdevelopment_curriculum.html')


@curriculum_bp.route('/english')
@login_required
def english_curriculum():
    return render_template('english_curriculum.html')


@curriculum_bp.route('/python_curriculum')
@login_required
def python_curriculum():
    try:
        return render_template('python_curriculum.html')
    except Exception as e:
        abort(500, description=str(e))


@curriculum_bp.route('/social_studies')
@login_required
def social_studies_curriculum():
    return render_template('social_studies_curriculum.html')


@curriculum_bp.route('/microsoft_office')
@login_required
def microsoft_office_curriculum():
    return render_template('microsoft_office_curriculum.html')
