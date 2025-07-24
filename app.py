from flask import Flask
import os
from dotenv import load_dotenv
from flask_login import LoginManager
from models import initialize_database, User
from blueprints.announcements.utils import get_unread_announcements_count
from blueprints.assignments.utils import get_unsubmitted_assignments_count
from blueprints.subscriptions.utils import get_subscription_plans
from blueprints.home.routes import home_bp
from blueprints.admin.routes import admin_bp
from blueprints.announcements.routes import announcement_bp
from blueprints.assignments.routes import assignments_bp
from blueprints.curriculum.routes import curriculum_bp
from blueprints.sessions.routes import sessions_bp
from blueprints.tutorials.routes import tutorials_bp
from blueprints.utilities.routes import utilities_bp
from blueprints.exam.routes import exam_bp
from blueprints.subscriptions.routes import subscriptions_bp
from blueprints.subscribe.routes import subscribe_bp
from blueprints.grades.routes import grades_bp
from blueprints.courses.routes import courses_bp
from blueprints.parents.routes import parents_bp
from blueprints.profile.routes import profile_bp


load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get(
    'FLASK_SECRET_KEY', 'fallback-secret-key-for-development')
app.jinja_env.globals.update(float=float)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home.login'  # type: ignore
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# User loader callbac


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not app.secret_key:
    raise ValueError("No secret key set for Flask application")

# Register the home blueprint
app.register_blueprint(home_bp, url_prefix='/')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(announcement_bp, url_prefix='/announcements')
app.register_blueprint(assignments_bp, url_prefix='/assignments')
app.register_blueprint(curriculum_bp, url_prefix='/curriculum')
app.register_blueprint(sessions_bp, url_prefix='/sessions')
app.register_blueprint(tutorials_bp, url_prefix='/tutorials')
app.register_blueprint(utilities_bp, url_prefix='/utilities')
app.register_blueprint(exam_bp, url_prefix='/exam')
app.register_blueprint(subscriptions_bp, url_prefix='/subscriptions')
app.register_blueprint(subscribe_bp, url_prefix='/subscribe')
app.register_blueprint(grades_bp, url_prefix='/grades')
app.register_blueprint(courses_bp, url_prefix='/courses')
app.register_blueprint(parents_bp, url_prefix='/parents')
app.register_blueprint(profile_bp, url_prefix='/profile')


@app.context_processor
def utility_processor():
    def get_plan_name(plan_id):
        plans = get_subscription_plans()
        for plan in plans:
            if plan[0] == plan_id:
                return plan[1]
        return "selected"
    return dict(get_plan_name=get_plan_name)


@app.template_filter('datetime')
def format_datetime(value, format="%Y-%m-%d %H:%M:%S"):
    """Format a datetime object to a string."""
    if value is None:
        return ""
    return value.strftime(format)


@app.context_processor
def inject_functions():
    return dict(
        get_unread_announcements_count=get_unread_announcements_count,
        get_unsubmitted_assignments_count=get_unsubmitted_assignments_count
    )

# if __name__ == '__main__':
#     from waitress import serve
#     initialize_database()
#     serve(app, host="0.0.0.0", port=5000)


if __name__ == '__main__':
    app.debug = True
    initialize_database()
    app.run(host='0.0.0.0', port=5000)
