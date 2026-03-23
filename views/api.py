"""
API endpoints for dashboard and analytics charts.
"""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from models import Activity, WellnessSnapshot


api_bp = Blueprint("api", __name__)


def _daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def _get_activities(start_date, end_date):
    from extensions import db
    from datetime import datetime, date
    
    # Fallback to client-side filtering to gracefully handle migrated SQLite string dates
    activities_cur = db.activities.find({'user_id': str(current_user.id)})
    
    activities = []
    for d in activities_cur:
        act = Activity(**d)
        
        act_date = act.activity_date
        if isinstance(act_date, datetime):
            act_date = act_date.date()
        elif isinstance(act_date, str):
            try:
                act_date = date.fromisoformat(act_date[:10].replace('Z', ''))
            except ValueError:
                continue
        elif not isinstance(act_date, date):
            continue
            
        act.activity_date = act_date
        
        if start_date <= act_date <= end_date:
            activities.append(act)
            
    return activities


def _get_float(obj, field):
    """Safely cast BSON migrated fields to float."""
    val = getattr(obj, field, 0)
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

@api_bp.route("/analytics/daily-screen-time")
@login_required
def daily_screen_time():
    days = request.args.get("days", default=14, type=int)
    today = date.today()
    start = today - timedelta(days=days - 1)

    activities = _get_activities(start, today)

    by_date = {}
    for a in activities:
        by_date.setdefault(a.activity_date, 0)
        by_date[a.activity_date] += _get_float(a, "screen_time_minutes")

    data = [
        {"date": d.isoformat(), "screen_time_minutes": by_date.get(d, 0)}
        for d in _daterange(start, today)
    ]
    return jsonify(data)


@api_bp.route("/analytics/weekly-usage")
@login_required
def weekly_usage():
    today = date.today()
    start = today - timedelta(days=27)

    activities = _get_activities(start, today)

    by_week = {}
    for a in activities:
        year, week_num, _ = a.activity_date.isocalendar()
        key = f"{year}-W{week_num}"
        by_week.setdefault(key, 0)
        by_week[key] += _get_float(a, "screen_time_minutes")

    data = [
        {"week": week, "screen_time_minutes": minutes}
        for week, minutes in sorted(by_week.items())
    ]
    return jsonify(data)


@api_bp.route("/analytics/category-distribution")
@login_required
def category_distribution():
    """Pie chart: Social, Learning, Entertainment, Productivity."""
    days = request.args.get("days", default=7, type=int)
    today = date.today()
    start = today - timedelta(days=days - 1)

    activities = _get_activities(start, today)
    
    totals = {
        "Social Media": 0,
        "Learning": 0,
        "Entertainment": 0,
        "Productivity": 0,
    }
    for a in activities:
        totals["Social Media"] += _get_float(a, "social_time")
        totals["Learning"] += _get_float(a, "learning_time")
        totals["Entertainment"] += _get_float(a, "entertainment_time")
        totals["Productivity"] += _get_float(a, "productivity_time")

    data = [{"category": k, "screen_time_minutes": v} for k, v in totals.items()]
    return jsonify(data)


@api_bp.route("/analytics/mood-trend")
@login_required
def mood_trend():
    """Last 14 days: mood per day (for mood trend chart)."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)

    by_date = {}
    for a in activities:
        mood = getattr(a, "mood", None)
        by_date[a.activity_date] = mood if mood else "Not set"

    # Map mood to number for line chart
    mood_order = {"Happy": 5, "Motivated": 4, "Neutral": 3, "Tired": 2, "Stressed": 1, "Not set": 0}
    data = [
        {
            "date": d.isoformat(),
            "mood": by_date.get(d, "Not set"),
            "mood_value": mood_order.get(by_date.get(d, "Not set"), 0),
        }
        for d in _daterange(start, today)
    ]
    return jsonify(data)


@api_bp.route("/analytics/stress-trend")
@login_required
def stress_trend():
    """Last 14 days: average stress level per day."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)

    by_date = {}
    for a in activities:
        stress = getattr(a, "stress_level", None)
        if stress is not None:
            try:
                by_date.setdefault(a.activity_date, []).append(float(stress))
            except (ValueError, TypeError):
                pass

    data = [
        {
            "date": d.isoformat(),
            "stress_level": sum(by_date[d]) / len(by_date[d]) if d in by_date else 0,
        }
        for d in _daterange(start, today)
    ]
    return jsonify(data)


@api_bp.route("/analytics/weekly-category-comparison")
@login_required
def weekly_category_comparison():
    """Last 4 weeks: total minutes per category per week."""
    today = date.today()
    start = today - timedelta(days=27)
    activities = _get_activities(start, today)

    categories = ["Social Media", "Learning", "Entertainment", "Productivity"]
    by_week = {}
    for a in activities:
        year, week_num, _ = a.activity_date.isocalendar()
        key = f"{year}-W{week_num}"
        if key not in by_week:
            by_week[key] = {c: 0 for c in categories}
        by_week[key]["Social Media"] += _get_float(a, "social_time")
        by_week[key]["Learning"] += _get_float(a, "learning_time")
        by_week[key]["Entertainment"] += _get_float(a, "entertainment_time")
        by_week[key]["Productivity"] += _get_float(a, "productivity_time")

    weeks = sorted(by_week.keys())
    data = {
        "weeks": weeks,
        "categories": categories,
        "series": {
            cat: [by_week[w][cat] for w in weeks] for cat in categories
        },
    }
    return jsonify(data)


def _daily_series(activities, start, end, value_key, value_fn):
    """Build daily series: list of {date, value} for each day in range. value_fn(activity) -> value."""
    by_date = {}
    for a in activities:
        by_date.setdefault(a.activity_date, []).append(a)
    data = []
    for d in _daterange(start, end):
        vals = by_date.get(d, [])
        data.append({
            "date": d.isoformat(),
            value_key: value_fn(vals[0]) if vals else 0,
        })
    return data


@api_bp.route("/analytics/daily-sleep")
@login_required
def daily_sleep():
    """Last 14 days: sleep hours per day (for sleep analytics chart)."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)
    return jsonify(_daily_series(
        activities, start, today, "hours",
        lambda a: round(_get_float(a, "sleep_hours"), 2),
    ))


@api_bp.route("/analytics/daily-work-study")
@login_required
def daily_work_study():
    """Last 14 days: work/study hours per day."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)
    return jsonify(_daily_series(
        activities, start, today, "hours",
        lambda a: round(_get_float(a, "work_study_hours"), 2),
    ))


@api_bp.route("/analytics/daily-social")
@login_required
def daily_social():
    """Last 14 days: social media time in hours per day."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)
    return jsonify(_daily_series(
        activities, start, today, "hours",
        lambda a: round(_get_float(a, "social_time") / 60.0, 2),
    ))


@api_bp.route("/analytics/daily-learning")
@login_required
def daily_learning():
    """Last 14 days: learning time in hours per day."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)
    return jsonify(_daily_series(
        activities, start, today, "hours",
        lambda a: round(_get_float(a, "learning_time") / 60.0, 2),
    ))


@api_bp.route("/analytics/daily-entertainment")
@login_required
def daily_entertainment():
    """Last 14 days: entertainment time in hours per day."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)
    return jsonify(_daily_series(
        activities, start, today, "hours",
        lambda a: round(_get_float(a, "entertainment_time") / 60.0, 2),
    ))


@api_bp.route("/analytics/daily-productivity")
@login_required
def daily_productivity():
    """Last 14 days: productivity time in hours per day."""
    today = date.today()
    start = today - timedelta(days=13)
    activities = _get_activities(start, today)
    return jsonify(_daily_series(
        activities, start, today, "hours",
        lambda a: round(_get_float(a, "productivity_time") / 60.0, 2),
    ))



@api_bp.route("/insights/latest")
@login_required
def latest_insights():
    snapshot = WellnessSnapshot.get_latest_for_user(current_user.id)
    if not snapshot:
        return jsonify(
            {
                "classification": "Not yet classified",
                "recommendation": "Record your first activity to generate insights.",
            }
        )
    return jsonify(
        {
            "classification": snapshot.classification,
            "recommendation": snapshot.recommendation,
            "snapshot_date": snapshot.snapshot_date.isoformat(),
        }
    )
