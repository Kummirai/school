from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from .utils import get_videos_by_subject, get_all_subjects, get_filtered_videos, get_subjects_by_grade

# Create a Blueprint for the tutorials routes
tutorials_bp = Blueprint('tutorials', __name__,
                         template_folder='templates', static_folder='static')


@tutorials_bp.route('/')
def tutorials_home():
    # Don't pass all videos anymore since we'll fetch them via AJAX
    return render_template('tutorials/video_tutorials.html')


@tutorials_bp.route('/api/videos')
def get_videos():
    """API endpoint to get filtered videos"""
    grade = request.args.get('grade', '').strip()
    subject = request.args.get('subject', '').strip()
    search_term = request.args.get('search', '').strip()
    
    try:
        # Get filtered videos from database
        videos = get_filtered_videos(grade=grade, subject=subject, search_term=search_term)
        
        # Convert database rows to dictionaries for JSON serialization
        videos_list = []
        for video in videos:
            videos_list.append({
                'id': video['id'],
                'title': video['title'],
                'description': video['description'],
                'grade': video['grade'],
                'subject': video['subject'],
                'youtubeid': video['youtubeid'],
                'thumbnail': video['thumbnail']
            })
        
        return jsonify({
            'success': True,
            'videos': videos_list,
            'count': len(videos_list)
        })
        
    except Exception as e:
        print(f"Error in get_videos API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch videos',
            'videos': [],
            'count': 0
        }), 500


@tutorials_bp.route('/api/subjects')
def get_subjects_for_grade():
    """API endpoint to get subjects available for a specific grade"""
    grade = request.args.get('grade', '').strip()
    
    try:
        if grade:
            # Get subjects available for the specific grade
            subjects = get_subjects_by_grade(grade)
        else:
            # Get all subjects
            subjects = get_all_subjects()
        
        return jsonify({
            'success': True,
            'subjects': subjects
        })
        
    except Exception as e:
        print(f"Error in get_subjects_for_grade API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch subjects',
            'subjects': []
        }), 500


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