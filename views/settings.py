"""
Settings: theme, notifications, burnout alerts, mood tracking, daily goals, password, data reset.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, session
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

        goals = Goal.get_by_user(current_user.id)
        if goals is None:
            goals = Goal(user_id=current_user.id)
        goals.screen_limit = screen_limit
        goals.study_target = study_target
        goals.sleep_target = sleep_target

        goals.save()
        current_user.save()

        flash("Settings updated.", "success")
        return redirect(url_for("settings.settings"))

    goals = Goal.get_by_user(current_user.id)

    # Security info
    last_session = None
    sess_list = UserSession.get_by_user(current_user.id)
    if sess_list:
        last_session = sess_list[0]
    last_login = last_session.login_time if last_session else None
    password_changed = current_user.password_updated_at

    # Active sessions
    active_sessions = [s for s in sess_list if getattr(s, 'is_active', False)]

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
    db.activities.delete_many({'user_id': str(current_user.id)})
    db.wellness_snapshots.delete_many({'user_id': str(current_user.id)})
    # Keep goals; optionally clear: db.goals.delete_many({'user_id': str(current_user.id)})

    flash("All activity data has been reset.", "info")
    return redirect(url_for("settings.settings"))


@settings_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    """Permanently delete the current user's account and all related data."""
    password = request.form.get("confirm_password", "")
    if not current_user.check_password(password):
        # If the user originally signed up using an OAuth provider, they
        # may not know the local (random) password we generated. In that
        # case initiate a re-auth flow with their provider so they can
        # confirm account deletion.
        provider = getattr(current_user, "auth_provider", "local")
        if provider and provider != "local":
            flash(
                f"You signed in via {provider.capitalize()}. Please re-authenticate to confirm account deletion.",
                "warning",
            )
            return redirect(url_for("settings.reauth_delete", provider=provider))

        flash("Password is incorrect. Account not deleted.", "danger")
        return redirect(url_for("settings.settings"))

    user_id = current_user.id

    # Delete related records first
    user_id_str = str(user_id)
    db.activities.delete_many({'user_id': user_id_str})
    db.wellness_snapshots.delete_many({'user_id': user_id_str})
    db.goals.delete_many({'user_id': user_id_str})
    db.user_sessions.delete_many({'user_id': user_id_str})

    # Delete the user account
    from bson import ObjectId
    db.users.delete_one({'_id': ObjectId(user_id_str)})

    logout_user()
    session.clear()
    flash("Your account has been deleted permanently.", "info")
    resp = redirect(url_for("landing"))
    # Ensure cookie is cleared
    resp.delete_cookie('session')
    return resp


@settings_bp.route("/delete-account/reauth/<provider>")
@login_required
def reauth_delete(provider):
    """Start an OAuth re-authentication for providers like 'google'.

    After successful provider auth we'll handle confirmation in
    `confirm_delete` which performs the actual deletion if the returned
    email matches the current user's email.
    """
    from flask import current_app

    # Validate provider
    if provider.lower() not in ["google", "facebook"]:
        flash("Invalid provider.", "danger")
        return redirect(url_for("settings.settings"))

    oauth = getattr(current_app, "oauth", None)
    if not oauth or not getattr(oauth, provider, None):
        flash(f"Sign in with {provider.capitalize()} is not configured.", "warning")
        return redirect(url_for("settings.settings"))

    try:
        # Use localhost explicitly to avoid 127.0.0.1 vs localhost mismatch
        redirect_uri = request.host_url.replace('127.0.0.1', 'localhost').rstrip('/') + url_for("settings.confirm_delete", provider=provider)
        return getattr(oauth, provider).authorize_redirect(redirect_uri, prompt="login")
    except Exception as e:
        flash(f"Authentication setup failed: {str(e)}. Please try again or contact support.", "danger")
        return redirect(url_for("settings.settings"))


@settings_bp.route("/delete-account/confirm/<provider>")
@login_required
def confirm_delete(provider):
    """Handle OAuth callback to confirm account deletion."""
    from flask import current_app

    # Validate provider
    if provider.lower() not in ["google", "facebook"]:
        flash("Invalid provider.", "danger")
        return redirect(url_for("settings.settings"))

    oauth = getattr(current_app, "oauth", None)
    if not oauth or not getattr(oauth, provider, None):
        flash(f"Sign in with {provider.capitalize()} is not configured.", "warning")
        return redirect(url_for("settings.settings"))

    try:
        token = getattr(oauth, provider).authorize_access_token()
    except Exception as e:
        flash(f"Re-authentication failed: {str(e)}. Please try again.", "warning")
        return redirect(url_for("settings.settings"))

    # Extract email from provider userinfo
    userinfo = token.get("userinfo") or {}
    email = (userinfo.get("email") or "").strip().lower()

    if not email:
        flash("Could not verify your email from the provider. Account not deleted.", "warning")
        return redirect(url_for("settings.settings"))

    if email != (current_user.email or "").strip().lower():
        flash("Verified account does not match the logged-in user. Account not deleted.", "danger")
        return redirect(url_for("settings.settings"))

    # Proceed to delete (same as delete_account)
    user_id = current_user.id

    user_id_str = str(user_id)
    db.activities.delete_many({'user_id': user_id_str})
    db.wellness_snapshots.delete_many({'user_id': user_id_str})
    db.goals.delete_many({'user_id': user_id_str})
    db.user_sessions.delete_many({'user_id': user_id_str})
    from bson import ObjectId
    db.users.delete_one({'_id': ObjectId(user_id_str)})
    logout_user()
    session.clear()
    flash("Your account has been deleted permanently.", "info")
    resp = redirect(url_for("landing"))
    # Ensure cookie is cleared
    resp.delete_cookie('session')
    return resp


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
    goals = Goal.get_by_user(current_user.id)
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
            "Mood",
            "Stress level",
            "Energy level",
        ]
    )
    activities = Activity.find_by_user(current_user.id)
    # They were requested in reverse order originally in find_by_user, we can sort them
    activities = sorted(activities, key=lambda a: a.activity_date or datetime.min)
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
    db.user_sessions.update_many(
        {'user_id': str(current_user.id), 'is_active': True},
        {'$set': {'is_active': False}}
    )
    flash("All other sessions have been logged out.", "info")
    return redirect(url_for("settings.settings"))
