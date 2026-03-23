from datetime import date, timedelta, datetime

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from extensions import db
from models import WellnessSnapshot, Activity


insights_bp = Blueprint("insights", __name__, url_prefix="/insights")


@insights_bp.route("/")
@login_required
def insights():
    latest_snapshot = WellnessSnapshot.get_latest_for_user(current_user.id)
    
    # Get previous snapshot for trend comparison
    previous_snapshot = None
    if latest_snapshot:
        snap_dt = latest_snapshot.snapshot_date
        if isinstance(snap_dt, date) and not isinstance(snap_dt, datetime):
            snap_dt = datetime.combine(snap_dt, datetime.min.time())
            
        data = db.wellness_snapshots.find_one({
            'user_id': str(current_user.id),
            'snapshot_date': {'$lt': snap_dt}
        }, sort=[('snapshot_date', -1)])
        previous_snapshot = WellnessSnapshot(**data) if data else None
    
    # Get recent activities for trend calculation (last 14 days)
    today = date.today()
    start = today - timedelta(days=13)
    start_dt = datetime.combine(start, datetime.min.time())
    today_dt = datetime.combine(today, datetime.max.time())
    
    activities_cur = db.activities.find({
        'user_id': str(current_user.id),
        'activity_date': {'$gte': start_dt, '$lte': today_dt}
    })
    recent_activities = [Activity(**d) for d in activities_cur]

    # Calculate metrics from activities
    this_week_total = 0
    last_week_total = 0
    this_week_sleep = 0
    sleep_count = 0
    this_week_stress = 0
    stress_count = 0
    this_week_productivity = 0

    for activity in recent_activities:
        act_date = activity.activity_date.date() if isinstance(activity.activity_date, datetime) else activity.activity_date
        days_ago = (today - act_date).days
        
        # Calculate screen time
        screen_time = (
            (activity.social_time or 0) +
            (activity.learning_time or 0) +
            (activity.entertainment_time or 0) +
            (activity.productivity_time or 0)
        )
        if screen_time == 0:
            screen_time = activity.screen_time_minutes or 0
        
        if days_ago <= 6:
            this_week_total += screen_time
            if activity.sleep_hours:
                this_week_sleep += activity.sleep_hours
                sleep_count += 1
            if activity.stress_level:
                this_week_stress += activity.stress_level
                stress_count += 1
            this_week_productivity += activity.work_study_hours or 0
        elif days_ago <= 13:
            last_week_total += screen_time

    # Calculate averages
    avg_sleep = round(this_week_sleep / sleep_count, 1) if sleep_count > 0 else 0
    avg_stress = round(this_week_stress / stress_count, 1) if stress_count > 0 else 3
    avg_productivity = round(this_week_productivity / 7, 1)

    # Calculate wellness score and trend
    wellness_score = 60  # default moderate
    trend = "stable"
    
    if latest_snapshot:
        classification = latest_snapshot.classification
        if classification == "Healthy":
            wellness_score = 85
        elif classification == "Unhealthy":
            wellness_score = 35
        
        if previous_snapshot:
            prev_class = previous_snapshot.classification
            if prev_class == "Healthy" and classification != "Healthy":
                trend = "down"
            elif prev_class == "Unhealthy" and classification != "Unhealthy":
                trend = "up"
            elif prev_class == "Moderate" and classification == "Healthy":
                trend = "up"
            elif prev_class == "Moderate" and classification == "Unhealthy":
                trend = "down"

    return render_template(
        "insights.html",
        snapshot=latest_snapshot,
        previous_snapshot=previous_snapshot,
        today=today,
        this_week_total=this_week_total,
        last_week_total=last_week_total,
        avg_sleep=avg_sleep,
        avg_stress=avg_stress,
        avg_productivity=avg_productivity,
        wellness_score=wellness_score,
        trend=trend,
    )

