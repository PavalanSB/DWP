from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
import os
import uuid

from extensions import db
from models import Activity, WellnessSnapshot


profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


def _save_avatar(file_storage):
    if not file_storage or file_storage.filename == "":
        return None

    filename = file_storage.filename.lower()
    allowed = (".png", ".jpg", ".jpeg", ".gif")
    if not any(filename.endswith(ext) for ext in allowed):
        return None

    ext = os.path.splitext(filename)[1]
    new_name = f"{uuid.uuid4().hex}{ext}"
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, new_name)
    file_storage.save(file_path)
    return new_name


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        age = request.form.get("age")
        country = request.form.get("country", "").strip()
        occupation = request.form.get("occupation", "").strip()
        digital_goal = request.form.get("digital_goal", "").strip()
        bio = request.form.get("bio", "").strip()

        if not name or not email:
            flash("Name and email are required.", "danger")
        else:
            current_user.name = name
            current_user.email = email
            current_user.country = country or None
            current_user.occupation = occupation or None
            current_user.digital_goal = digital_goal or None
            current_user.bio = bio or None
            try:
                current_user.age = int(age) if age else None
            except ValueError:
                current_user.age = None

            avatar_file = request.files.get("avatar")
            avatar_filename = _save_avatar(avatar_file)
            if avatar_filename:
                current_user.avatar_filename = avatar_filename

            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("profile.profile"))

    # Wellness summary metrics
    total_days = (
        db.session.query(Activity.activity_date)
        .filter_by(user_id=current_user.id)
        .distinct()
        .count()
    )
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    avg_screen = 0
    avg_sleep = 0
    longest_streak = 0

    if activities:
        # Average screen time (minutes)
        screen_minutes = [
            (a.social_time or 0)
            + (a.learning_time or 0)
            + (a.entertainment_time or 0)
            + (a.productivity_time or 0)
            + (a.gaming_time or 0)
            or (a.screen_time_minutes or 0)
            for a in activities
        ]
        avg_screen = sum(screen_minutes) / len(screen_minutes)

        # Average sleep hours
        sleep_vals = [a.sleep_hours for a in activities if a.sleep_hours]
        if sleep_vals:
            avg_sleep = sum(sleep_vals) / len(sleep_vals)

        # Longest tracking streak (consecutive days with activity)
        dates = sorted({a.activity_date for a in activities})
        streak = 1
        longest_streak = 1
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i - 1]).days
            if delta == 1:
                streak += 1
            else:
                streak = 1
            if streak > longest_streak:
                longest_streak = streak

    # Current wellness score from latest snapshot (reuse mapping used in insights)
    latest_snapshot = (
        WellnessSnapshot.query.filter_by(user_id=current_user.id)
        .order_by(WellnessSnapshot.snapshot_date.desc())
        .first()
    )
    wellness_score = None
    if latest_snapshot:
        if latest_snapshot.classification == "Healthy":
            wellness_score = 85
        elif latest_snapshot.classification == "Moderate":
            wellness_score = 60
        else:
            wellness_score = 35

    # Profile completion
    fields = 0
    completed = 0

    # avatar
    fields += 1
    if current_user.avatar_filename:
        completed += 1
    # bio
    fields += 1
    if getattr(current_user, "bio", None):
        completed += 1
    # goal
    fields += 1
    if current_user.digital_goal:
        completed += 1
    # age
    fields += 1
    if current_user.age:
        completed += 1
    # country
    fields += 1
    if current_user.country:
        completed += 1

    profile_completion = int(round((completed / fields) * 100)) if fields else 0

    return render_template(
        "profile.html",
        total_days=total_days,
        avg_screen_minutes=avg_screen,
        avg_sleep_hours=avg_sleep,
        longest_streak=longest_streak,
        wellness_score=wellness_score,
        profile_completion=profile_completion,
    )


@profile_bp.route("/avatar", methods=["POST"])
@login_required
def upload_avatar():
    """Accept cropped avatar image (file upload) and update current user. Returns JSON with new URL."""
    avatar_file = request.files.get("avatar")
    avatar_filename = _save_avatar(avatar_file)
    if not avatar_filename:
        return jsonify({"ok": False, "error": "Invalid or missing image"}), 400
    current_user.avatar_filename = avatar_filename
    db.session.commit()
    url = url_for("static", filename="uploads/avatars/" + avatar_filename)
    return jsonify({"ok": True, "url": url})


@profile_bp.route("/password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_user.check_password(current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("profile.profile"))

    if not new_password or new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("profile.profile"))

    current_user.set_password(new_password)
    db.session.commit()

    flash("Password changed successfully.", "success")
    return redirect(url_for("profile.profile"))

