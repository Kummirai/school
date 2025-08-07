from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .utils import get_videos_by_subject, get_all_videos_details
# Create a Blueprint for the tutorials routes
tutorials_bp = Blueprint('tutorials', __name__,
                         template_folder='templates', static_folder='static')


@tutorials_bp.route('/')
def tutorials_home():
    all_videos = get_all_videos_details()
    return render_template('tutorials/video_tutorials.html', all_videos=all_videos)


@tutorials_bp.route('/study_guides')
@login_required
def studyguides_home():
    return render_template('study_guides.html')


@tutorials_bp.route('/tutorials/<string:subject>')
# @login_required
def tutorial_language(subject):
    videos = get_videos_by_subject(subject)
    if not videos:
        flash('Tutorials for this subject not found', 'danger')
        return redirect(url_for('tutorials.tutorials_home'))

    return render_template('tutorials/language.html',
                           videos=videos,
                           subject=subject)
