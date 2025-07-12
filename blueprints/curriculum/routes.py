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


@curriculum_bp.route('/english')
@login_required
def english_curriculum():
    return render_template('english_curriculum.html')
