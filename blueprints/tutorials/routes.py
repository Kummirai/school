from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils import get_videos_by_category
from decorators.decorator import admin_required
from flask import current_app as app
from helpers import get_all_categories


@app.route('/admin/tutorials')
@login_required
@admin_required
def manage_tutorials():
    videos = get_all_videos()  # This should return a list of videos
    categories = get_all_categories()  # This should return a list of categories

    # Convert to the structure your template expects
    tutorials_dict = {
        category[1]: {  # category name as key
            # videos for this category
            'videos': [v for v in videos if v[3] == category[1]],
            'id': category[0]  # category id
        }
        for category in categories
    }

    return render_template('admin/tutorials.html',
                           tutorials=tutorials_dict,
                           videos=videos,
                           categories=categories)


@app.route('/admin/tutorials/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_tutorial():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            url = request.form.get('url', '').strip()
            category_id = request.form.get('category_id', '').strip()

            if not all([title, url, category_id]):
                flash('All fields are required', 'danger')
                return redirect(url_for('add_tutorial'))

            add_video(title, url, category_id)
            flash('Tutorial added successfully', 'success')
            return redirect(url_for('manage_tutorials'))

        except Exception as e:
            flash(f'Error adding tutorial: {str(e)}', 'danger')
            return redirect(url_for('add_tutorial'))

    # GET request - show the form
    categories = get_all_categories()
    return render_template('admin/add_tutorial.html', categories=categories)


@app.route('/admin/tutorials/delete/<int:video_id>')
@login_required
@admin_required
def delete_tutorial(video_id):
    delete_video(video_id)
    flash('Tutorial video deleted successfully', 'success')
    return redirect(url_for('manage_tutorials'))


@app.route('/tutorials')
# @login_required
def tutorials_home():
    return render_template('tutorials/video_tutorials.html')


@app.route('/study_guides')
@login_required
def studyguides_home():
    return render_template('study_guides.html')


@app.route('/tutorials/<int:category_id>')
# @login_required
def tutorial_language(category_id):
    videos = get_videos_by_category(category_id)
    if not videos:
        flash('Tutorial category not found', 'danger')
        return redirect(url_for('tutorials_home'))

    # Get the category name
    category_name = get_category_name(category_id)

    return render_template('tutorials/language.html',
                           videos=videos,
                           category={'id': category_id, 'name': category_name})
