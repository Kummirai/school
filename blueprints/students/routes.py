from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from decorators.decorator import admin_required
from utils import get_students, add_student_to_db, delete_student_by_id, get_user_by_username
from models import get_db_connection
from flask import current_app as app

# Blueprint for student management
students_bp = Blueprint('students', __name__)


