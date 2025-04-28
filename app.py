from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Mock database (replace with real database in production)
# User database structure
users = {
    "admin": {
        "password": generate_password_hash("admin123"),  # Hashed password stored here
        "role": "admin"
    },
    "student": {
        "password": generate_password_hash("student123"),
        "role": "student"
    }
}

tutorials = {
    "html": {
        "title": "HTML Tutorials",
        "videos": [
            {"title": "HTML Basics", "url": "https://example.com/html1"},
            {"title": "Forms and Input", "url": "https://example.com/html2"}
        ]
    },
    "css": {
        "title": "CSS Tutorials",
        "videos": [
            {"title": "CSS Selectors", "url": "https://example.com/css1"},
            {"title": "Flexbox Layout", "url": "https://example.com/css2"}
        ]
    },
    "javascript": {
        "title": "JavaScript Tutorials",
        "videos": [
            {"title": "JS Fundamentals", "url": "https://example.com/js1"},
            {"title": "DOM Manipulation", "url": "https://example.com/js2"}
        ]
    },
    "python": {
        "title": "Python Tutorials",
        "videos": [
            {"title": "Python Basics", "url": "https://example.com/py1"},
            {"title": "Flask Web Development", "url": "https://example.com/py2"}
        ]
    },
    "microsoft": {
        "title": "Microsoft Technologies",
        "videos": [
            {"title": "Azure Fundamentals", "url": "https://example.com/ms1"},
            {"title": ".NET Core", "url": "https://example.com/ms2"}
        ]
    }
}


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
        
#         # Check if user exists and password matches
#         user_data = users.get(username)
#         if user_data and check_password_hash(user_data['password'], password):
#             session['username'] = username
#             session['role'] = user_data['role']  # Store user role in session
#             flash('Logged in successfully!', 'success')
#             next_page = request.args.get('next')
#             return redirect(next_page or url_for('tutorials_home'))
#         else:
#             flash('Invalid username or password', 'danger')
    
#     return render_template('auth/login.html')

# And your login route sets the role properly:
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_data = users.get(username)
        if user_data and check_password_hash(user_data['password'], password):
            session['username'] = username
            session['role'] = user_data['role']  # This is crucial
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('tutorials_home'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/tutorials')
@login_required
def tutorials_home():
    return render_template('tutorials/index.html', tutorials=tutorials)

@app.route('/tutorials/<language>')
@login_required
def tutorial_language(language):
    if language not in tutorials:
        flash('Tutorial category not found', 'danger')
        return redirect(url_for('tutorials_home'))
    
    return render_template('tutorials/language.html', 
                         language=language, 
                         tutorial=tutorials[language])

#admin_required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function


# Admin Dashboard
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Count students by filtering users with 'student' role
    student_count = len([user for user, data in users.items() if data.get('role') == 'student'])
    
    # Count tutorial categories
    tutorial_count = len(tutorials)
    
    return render_template('admin/dashboard.html', 
                         student_count=student_count,
                         tutorial_count=tutorial_count)

# Manage Students
@app.route('/admin/students')
@login_required
@admin_required
def manage_students():
    student_users = {user: data for user, data in users.items() if data.get('role') == 'student'}
    return render_template('admin/students.html', students=student_users)

# Add New Student
@app.route('/admin/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users:
            flash('Username already exists', 'danger')
        else:
            users[username] = {
                "password": generate_password_hash(password),
                "role": "student"
            }
            flash('Student account created successfully', 'success')
            return redirect(url_for('manage_students'))
    
    return render_template('admin/add_student.html')

# Delete Student
@app.route('/admin/students/delete/<username>')
@login_required
@admin_required
def delete_student(username):
    if username in users and users[username].get('role') == 'student':
        del users[username]
        flash('Student account deleted', 'success')
    else:
        flash('Student not found', 'danger')
    return redirect(url_for('manage_students'))

# Manage Tutorials
@app.route('/admin/tutorials')
@login_required
@admin_required
def manage_tutorials():
    return render_template('admin/tutorials.html', tutorials=tutorials)

# Add Tutorial Video
@app.route('/admin/tutorials/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_tutorial():
    if request.method == 'POST':
        language = request.form['language']
        title = request.form['title']
        url = request.form['url']
        
        if language in tutorials:
            tutorials[language]['videos'].append({"title": title, "url": url})
        else:
            tutorials[language] = {
                "title": language.capitalize() + " Tutorials",
                "videos": [{"title": title, "url": url}]
            }
        flash('Tutorial added successfully', 'success')
        return redirect(url_for('manage_tutorials'))
    
    return render_template('admin/add_tutorial.html', languages=tutorials.keys())

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

if __name__ == '__main__':
    app.run(debug=True)