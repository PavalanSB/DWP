"""
Activity tracking: category breakdown (social, learning, entertainment, productivity),
mood, stress level, energy level. Saves to Activity and triggers wellness snapshot update.
"""
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models import Activity


activity_bp = Blueprint("activity", __name__, url_prefix="/activity")


def _float_or_zero(val):
    try:
        return max(0.0, float(val))
    except (TypeError, ValueError):
        return 0.0


def _hours_to_minutes(hours):
    """Convert hours (float) to minutes (int) for storage."""
    return int(round(_float_or_zero(hours) * 60))


@activity_bp.route("/", methods=["GET", "POST"])
@login_required
def track_activity():
    from app import update_daily_wellness_snapshot

    if request.method == "POST":
        # Category breakdown: form accepts HOURS, we store minutes
        social_time = _hours_to_minutes(request.form.get("social_time"))
        learning_time = _hours_to_minutes(request.form.get("learning_time"))
        entertainment_time = _hours_to_minutes(request.form.get("entertainment_time"))
        productivity_time = _hours_to_minutes(request.form.get("productivity_time"))

        total_screen = social_time + learning_time + entertainment_time + productivity_time
        if total_screen <= 0:
            flash("Please enter at least some screen time in one or more categories.", "danger")
            return redirect(url_for("activity.track_activity"))

        sleep_hours = _float_or_zero(request.form.get("sleep_hours"))
        work_study_hours = _float_or_zero(request.form.get("work_study_hours"))
        if sleep_hours <= 0:
            flash("Sleep hours must be positive.", "danger")
            return redirect(url_for("activity.track_activity"))

        # Mood (optional)
        mood = (request.form.get("mood") or "").strip() or None
        stress_level = request.form.get("stress_level")
        stress_level = int(stress_level) if stress_level and stress_level.isdigit() else None
        if stress_level is not None:
            stress_level = max(1, min(5, stress_level))
        energy_level = request.form.get("energy_level")
        energy_level = int(energy_level) if energy_level and energy_level.isdigit() else None
        if energy_level is not None:
            energy_level = max(1, min(5, energy_level))

        activity = Activity(
            user_id=current_user.id,
            activity_date=datetime.utcnow().date(),
            screen_time_minutes=total_screen,
            sleep_hours=sleep_hours,
            work_study_hours=work_study_hours,
            category=None,
            social_time=social_time,
            learning_time=learning_time,
            entertainment_time=entertainment_time,
            productivity_time=productivity_time,
            mood=mood,
            stress_level=stress_level,
            energy_level=energy_level,
        )
        activity.save()

        update_daily_wellness_snapshot(current_user)

        flash("Activity recorded successfully.", "success")
        return redirect(url_for("dashboard.dashboard"))

    activities = Activity.find_by_user(current_user.id, limit=30)
    return render_template("activity.html", activities=activities)
