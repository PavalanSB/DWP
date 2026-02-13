"""
Settings: theme, notifications, burnout alerts, mood tracking, daily goals, password, data reset.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user, logout_user
import csv
import io

from extensions import db
from models import Activity, WellnessSnapshot, Goal, User, UserSession


settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def _int_or_none(val):
    if val is None or val == "":
        return None
    try:
        v = int(val)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _float_or_none(val):
    if val is None or val == "":
        return None
    try:
        v = float(val)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        theme = request.form.get("theme", "light")
        notifications_enabled = bool(request.form.get("notifications_enabled"))
        burnout_alerts_enabled = bool(request.form.get("burnout_alerts_enabled"))
        mood_tracking_enabled = bool(request.form.get("mood_tracking_enabled"))
        profile_private = bool(request.form.get("profile_private"))
        allow_analytics = bool(request.form.get("allow_analytics"))
        show_wellness_public = bool(request.form.get("show_wellness_public"))

        current_user.theme = theme
        current_user.notifications_enabled = notifications_enabled
        current_user.burnout_alerts_enabled = burnout_alerts_enabled
        current_user.mood_tracking_enabled = mood_tracking_enabled
        current_user.profile_private = profile_private
        current_user.allow_analytics = allow_analytics
        current_user.show_wellness_public = show_wellness_public

        # Daily goals
        screen_limit = _int_or_none(request.form.get("screen_limit"))
        study_target = _float_or_none(request.form.get("study_target"))
        sleep_target = _float_or_none(request.form.get("sleep_target"))

        goals = Goal.query.filter_by(user_id=current_user.id).first()
        if goals is None:
            goals = Goal(user_id=current_user.id)
            db.session.add(goals)
        goals.screen_limit = screen_limit
        goals.study_target = study_target
        goals.sleep_target = sleep_target

        db.session.commit()

        flash("Settings updated.", "success")
        return redirect(url_for("settings.settings"))

    goals = Goal.query.filter_by(user_id=current_user.id).first()

    # Security info
    last_session = (
        UserSession.query.filter_by(user_id=current_user.id)
        .order_by(UserSession.login_time.desc())
        .first()
    )
    last_login = last_session.login_time if last_session else None
    password_changed = current_user.password_updated_at

    # Active sessions
    active_sessions = (
        UserSession.query.filter_by(user_id=current_user.id, is_active=True)
        .order_by(UserSession.login_time.desc())
        .all()
    )

    return render_template(
        "settings.html",
        goals=goals,
        last_login=last_login,
        password_changed=password_changed,
        active_sessions=active_sessions,
    )


@settings_bp.route("/reset-data", methods=["POST"])
@login_required
def reset_data():
    Activity.query.filter_by(user_id=current_user.id).delete()
    WellnessSnapshot.query.filter_by(user_id=current_user.id).delete()
    # Keep goals; optionally clear: Goal.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    flash("All activity data has been reset.", "info")
    return redirect(url_for("settings.settings"))


@settings_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    """Permanently delete the current user's account and all related data."""
    password = request.form.get("confirm_password", "")
    if not current_user.check_password(password):
        flash("Password is incorrect. Account not deleted.", "danger")
        return redirect(url_for("settings.settings"))

    user_id = current_user.id

    # Delete related records first
    Activity.query.filter_by(user_id=user_id).delete()
    WellnessSnapshot.query.filter_by(user_id=user_id).delete()
    Goal.query.filter_by(user_id=user_id).delete()
    UserSession.query.filter_by(user_id=user_id).delete()

    # Delete the user account
    User.query.filter_by(id=user_id).delete()

    db.session.commit()

    logout_user()
    flash("Your account has been deleted permanently.", "info")
    return redirect(url_for("landing"))


@settings_bp.route("/export-data", methods=["GET"])
@login_required
def export_data():
    """Download user profile, activities, and goals as a CSV file."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Profile info
    writer.writerow(["Profile"])
    writer.writerow(["Name", current_user.name])
    writer.writerow(["Email", current_user.email])
    writer.writerow(["Created at", current_user.created_at])
    writer.writerow(["Country", current_user.country or ""])
    writer.writerow(["Occupation", current_user.occupation or ""])
    writer.writerow(["Digital goal", current_user.digital_goal or ""])
    writer.writerow(["Bio", current_user.bio or ""])
    writer.writerow([])

    # Goals
    goals = Goal.query.filter_by(user_id=current_user.id).first()
    writer.writerow(["Goals"])
    writer.writerow(["Screen limit (min)", goals.screen_limit if goals else ""])
    writer.writerow(["Study target (hours)", goals.study_target if goals else ""])
    writer.writerow(["Sleep target (hours)", goals.sleep_target if goals else ""])
    writer.writerow([])

    # Activities
    writer.writerow(["Activities"])
    writer.writerow(
        [
            "Date",
            "Screen time (min)",
            "Sleep hours",
            "Work/Study hours",
            "Social (min)",
            "Learning (min)",
            "Entertainment (min)",
            "Productivity (min)",
            "Gaming (min)",
            "Mood",
            "Stress level",
            "Energy level",
        ]
    )
    activities = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.activity_date).all()
    for a in activities:
        writer.writerow(
            [
                a.activity_date,
                a.screen_time_minutes,
                a.sleep_hours,
                a.work_study_hours,
                a.social_time,
                a.learning_time,
                a.entertainment_time,
                a.productivity_time,
                a.gaming_time,
                a.mood or "",
                a.stress_level or "",
                a.energy_level or "",
            ]
        )

    csv_data = output.getvalue()
    output.close()

    filename = f"dwp_data_user_{current_user.id}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@settings_bp.route("/logout-others", methods=["POST"])
@login_required
def logout_other_sessions():
    """Mark all other sessions as inactive for this user."""
    UserSession.query.filter_by(user_id=current_user.id, is_active=True).update(
        {"is_active": False}
    )
    db.session.commit()
    flash("All other sessions have been logged out.", "info")
    return redirect(url_for("settings.settings"))
