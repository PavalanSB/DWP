"""
Dashboard: wellness score, mood summary, streak, burnout warning, goals progress,
category distribution, and existing metrics.
"""
from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from extensions import db
from models import Activity, WellnessSnapshot, Goal
from utils.wellness_metrics import (
    calculate_streak,
    calculate_consistency_score,
    calculate_wellness_score,
    check_burnout_risk,
)


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def dashboard():
    activities = Activity.query.filter_by(user_id=current_user.id).order_by(
        Activity.activity_date.desc()
    ).all()

    total_days = len({a.activity_date for a in activities})
    avg_screen_time = 0
    if activities:
        avg_screen_time = int(
            sum(getattr(a, "screen_time_minutes", 0) or 0 for a in activities) / len(activities)
        )

    latest_snapshot = (
        WellnessSnapshot.query.filter_by(user_id=current_user.id)
        .order_by(WellnessSnapshot.snapshot_date.desc())
        .first()
    )
    latest_classification = (
        latest_snapshot.classification if latest_snapshot else "Not yet classified"
    )
    latest_recommendation = (
        latest_snapshot.recommendation if latest_snapshot
        else "Add your first activity entry to receive personalized insights."
    )

    today = date.today()
    today_activity = Activity.query.filter_by(
        user_id=current_user.id, activity_date=today
    ).first()

    # Goals (one per user)
    goals = Goal.query.filter_by(user_id=current_user.id).first()

    # Streak & consistency & wellness score
    streak = calculate_streak(activities)
    consistency = calculate_consistency_score(activities, goals, days=7)
    wellness_score = calculate_wellness_score(
        activities, goals, streak, consistency, latest_classification
    )

    # Burnout risk (from today's activity if available)
    burnout_risk = False
    if today_activity and getattr(current_user, "burnout_alerts_enabled", True):
        burnout_risk = check_burnout_risk(today_activity)
    if latest_classification == "Burnout Risk":
        burnout_risk = True

    # Mood summary (last 7 days)
    mood_summary = None
    if getattr(current_user, "mood_tracking_enabled", True) and activities:
        mood_counts = {}
        for a in activities[:50]:
            m = getattr(a, "mood", None) or "Not set"
            mood_counts[m] = mood_counts.get(m, 0) + 1
        mood_summary = mood_counts

    # Goal completion for today (0-100%)
    goal_screen_pct = goal_study_pct = goal_sleep_pct = None
    if today_activity and goals:
        total = getattr(today_activity, "screen_time_minutes", 0) or 0
        if getattr(goals, "screen_limit", None) and goals.screen_limit > 0:
            # Under limit = 100%; over = 100 * limit / actual
            goal_screen_pct = min(100, int(100 * goals.screen_limit / total)) if total else 100
        study = getattr(today_activity, "work_study_hours", 0) or 0
        if getattr(goals, "study_target", None) and goals.study_target > 0:
            goal_study_pct = min(100, int(100 * study / goals.study_target))
        sleep = getattr(today_activity, "sleep_hours", 0) or 0
        if getattr(goals, "sleep_target", None) and goals.sleep_target > 0:
            goal_sleep_pct = min(100, int(100 * sleep / goals.sleep_target))

    return render_template(
        "dashboard.html",
        avg_screen_time=avg_screen_time,
        total_days=total_days,
        latest_classification=latest_classification,
        latest_recommendation=latest_recommendation,
        today_activity=today_activity,
        goals=goals,
        streak=streak,
        consistency=consistency,
        wellness_score=wellness_score,
        burnout_risk=burnout_risk,
        mood_summary=mood_summary,
        goal_screen_pct=goal_screen_pct,
        goal_study_pct=goal_study_pct,
        goal_sleep_pct=goal_sleep_pct,
    )
