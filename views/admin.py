from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import User
from extensions import db

admin_bp = Blueprint("admin", __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash("You do not have permission to access that page.", "danger")
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    users_cursor = db.users.find()
    users = [User(**d) for d in users_cursor]
    return render_template("admin/dashboard.html", users=users)

@admin_bp.route("/unlock/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def unlock_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        from flask import abort
        abort(404)
        
    if getattr(user, 'is_locked', False):
        user.is_locked = False
        user.failed_login_attempts = 0
        user.save()
        flash(f"Account for {user.email} has been unlocked.", "success")
    else:
        flash(f"Account for {user.email} is not locked.", "info")
    return redirect(url_for('admin.dashboard'))
