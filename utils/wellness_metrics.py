"""
Wellness metrics: streak, consistency score, wellness score (0-100), burnout detection.
"""
from datetime import date, timedelta
from typing import List, Optional, Tuple

# Default thresholds for burnout detection (rule-based)
BURNOUT_SCREEN_THRESHOLD_MIN = 360   # 6 hours
BURNOUT_SLEEP_THRESHOLD_MAX = 6.0   # under 6 hours
BURNOUT_STRESS_THRESHOLD = 4        # stress_level >= 4


def get_activity_dates_sorted(activities) -> List[date]:
    """Return sorted list of unique activity dates (descending)."""
    dates = sorted({a.activity_date for a in activities}, reverse=True)
    return dates


def calculate_streak(activities) -> int:
    """
    Consecutive days with at least one activity entry, counting from today (or most recent).
    """
    if not activities:
        return 0
    dates = get_activity_dates_sorted(activities)
    if not dates:
        return 0
    today = date.today()
    # If most recent activity is not today or yesterday, streak is 0
    if dates[0] < today - timedelta(days=1):
        return 0
    streak = 0
    expected = today
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break
    return streak


def calculate_consistency_score(activities, goals, days: int = 7) -> float:
    """
    Percentage of last `days` days where user had activity and (optionally) met goals.
    Returns 0-100. If no goals set, consistency = % of days with any activity.
    """
    if not activities:
        return 0.0
    today = date.today()
    start = today - timedelta(days=days)
    by_date = {}
    for a in activities:
        if start <= a.activity_date <= today:
            by_date.setdefault(a.activity_date, []).append(a)

    if not by_date:
        return 0.0

    screen_limit = getattr(goals, "screen_limit", None) if goals else None
    study_target = getattr(goals, "study_target", None) if goals else None
    sleep_target = getattr(goals, "sleep_target", None) if goals else None

    met = 0
    total = 0
    for d in (today - timedelta(days=i) for i in range(days)):
        if d not in by_date:
            continue
        total += 1
        day_activities = by_date[d]
        # Use latest entry of the day
        a = day_activities[0]
        screen_ok = screen_limit is None or (getattr(a, "screen_time_minutes", 0) <= screen_limit)
        study_ok = study_target is None or (getattr(a, "work_study_hours", 0) >= study_target)
        sleep_ok = sleep_target is None or (getattr(a, "sleep_hours", 0) >= sleep_target)
        if screen_ok and study_ok and sleep_ok:
            met += 1

    if total == 0:
        return 0.0
    return round(100.0 * met / total, 1)


def calculate_wellness_score(
    activities,
    goals,
    streak: int,
    consistency: float,
    latest_classification: Optional[str],
) -> int:
    """
    Composite wellness score 0-100 from streak, consistency, and latest ML classification.
    """
    score = 50  # base
    if streak > 0:
        score += min(20, streak * 2)   # up to +20 for streak
    score = score * 0.4 + consistency * 0.4  # 40% consistency
    if latest_classification:
        if latest_classification == "Healthy":
            score += 15
        elif latest_classification == "Moderate":
            score += 5
        elif latest_classification == "Unhealthy":
            score -= 10
        elif latest_classification == "Burnout Risk":
            score -= 15
    return max(0, min(100, int(round(score))))


def check_burnout_risk(activity) -> bool:
    """
    Rule-based: True if high screen time, low sleep, and high stress.
    activity can have: screen_time_minutes, sleep_hours, stress_level.
    """
    screen = getattr(activity, "screen_time_minutes", 0) or 0
    sleep = getattr(activity, "sleep_hours", 0) or 0
    stress = getattr(activity, "stress_level", 0) or 0
    if screen >= BURNOUT_SCREEN_THRESHOLD_MIN and sleep < BURNOUT_SLEEP_THRESHOLD_MAX and stress >= BURNOUT_STRESS_THRESHOLD:
        return True
    if sleep < 5 and stress >= 4:
        return True
    return False
