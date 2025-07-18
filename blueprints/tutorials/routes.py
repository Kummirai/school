from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .utils import get_videos_by_category, get_category_name
# Create a Blueprint for the tutorials routes
tutorials_bp = Blueprint('tutorials', __name__,
                         template_folder='templates', static_folder='static')


@tutorials_bp.route('/')
# @login_required
def tutorials_home():
    return render_template('tutorials/video_tutorials.html')


@tutorials_bp.route('/study_guides')
@login_required
def studyguides_home():
    return render_template('study_guides.html')


@tutorials_bp.route('/tutorials/<int:category_id>')
# @login_required
def tutorial_language(category_id):
    videos = get_videos_by_category(category_id)
    if not videos:
        flash('Tutorial category not found', 'danger')
        return redirect(url_for('tutorials.tutorials_home'))

    # Get the category name
    category_name = get_category_name(category_id)

    return render_template('tutorials/language.html',
                           videos=videos,
                           category={'id': category_id, 'name': category_name})
