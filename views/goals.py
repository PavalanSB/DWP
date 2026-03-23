"""
Goals view for setting and tracking personal wellness goals.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from extensions import db
from models import Goal


goals_bp = Blueprint("goals", __name__, url_prefix="/goals")


@goals_bp.route("/", methods=["GET", "POST"])
@login_required
def manage_goals():
    """Display and update user goals."""
    goal = Goal.get_by_user(current_user.id)
    if not goal:
        goal = Goal(user_id=current_user.id)
        goal.save()

    if request.method == "POST":
        try:
            goal.screen_limit = int(request.form.get("screen_limit", 0)) if request.form.get("screen_limit") else None
            goal.study_target = float(request.form.get("study_target", 0)) if request.form.get("study_target") else None
            goal.sleep_target = float(request.form.get("sleep_target", 0)) if request.form.get("sleep_target") else None
            goal.save()
            flash("Goals updated successfully!", "success")
            return redirect(url_for("goals.manage_goals"))
        except ValueError:
            flash("Invalid input values.", "danger")

    return render_template("goals.html", goal=goal)