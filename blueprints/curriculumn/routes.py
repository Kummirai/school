from flask import Blueprint, render_template, abort
from flask_login import login_required
# Create a Blueprint for the curriculum routes
curriculum_bp = Blueprint('curriculum', __name__, url_prefix='/curriculum')
app = curriculum_bp


@app.route('/math-curriculum')
@login_required
def math_curriculum():
    return render_template('math_curriculum.html')


@app.route('/science_curriculum')
@login_required
def science_curriculum():
    return render_template('science_curriculum.html')


@app.route('/english_curriculum')
@login_required
def english_curriculum():
    return render_template('english_curriculum.html')

# API Endpoints
