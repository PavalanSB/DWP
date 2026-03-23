from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Profile details
    avatar_filename = db.Column(db.String(255), nullable=True)  # acts as profile image
    age = db.Column(db.Integer, nullable=True)
    country = db.Column(db.String(100), nullable=True)
    occupation = db.Column(db.String(120), nullable=True)
    digital_goal = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)

    # Preferences & privacy
    theme = db.Column(db.String(20), default="light")  # light or dark
    notifications_enabled = db.Column(db.Boolean, default=True)
    burnout_alerts_enabled = db.Column(db.Boolean, default=True)
    mood_tracking_enabled = db.Column(db.Boolean, default=True)
    profile_private = db.Column(db.Boolean, default=False)
    allow_analytics = db.Column(db.Boolean, default=True)
    show_wellness_public = db.Column(db.Boolean, default=False)

    # Security metadata
    password_updated_at = db.Column(db.DateTime, nullable=True)
    # 'local' for username/password accounts, or provider name like 'google', 'facebook'
    auth_provider = db.Column(db.String(50), default="local", nullable=False)

    # Account Lockout & Admin
    failed_login_attempts = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    activities = db.relationship("Activity", backref="user", lazy=True)
    wellness_snapshots = db.relationship(
        "WellnessSnapshot", backref="user", lazy=True
    )
    goals = db.relationship("Goal", backref="user", lazy=True)
    sessions = db.relationship("UserSession", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        self.password_updated_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    user = User.query.get(uid)
    if user is None:
        from flask import session
        session.pop("_user_id", None)
    return user


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    activity_date = db.Column(db.Date, default=date.today, index=True)
    # Total screen time (minutes); kept for backward compatibility, computed from categories when provided
    screen_time_minutes = db.Column(db.Integer, nullable=False)
    sleep_hours = db.Column(db.Float, nullable=False)
    work_study_hours = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=True)  # legacy main category

    # App category breakdown (minutes each)
    social_time = db.Column(db.Integer, default=0)
    learning_time = db.Column(db.Integer, default=0)
    entertainment_time = db.Column(db.Integer, default=0)
    productivity_time = db.Column(db.Integer, default=0)

    # Mood tracking
    mood = db.Column(db.String(30), nullable=True)  # Happy, Neutral, Stressed, Tired, Motivated
    stress_level = db.Column(db.Integer, nullable=True)  # 1-5
    energy_level = db.Column(db.Integer, nullable=True)  # 1-5

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class WellnessSnapshot(db.Model):
    __tablename__ = "wellness_snapshots"
    __table_args__ = (
        db.UniqueConstraint('user_id', 'snapshot_date', name='uq_wellness_snapshot_user_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    snapshot_date = db.Column(db.Date, default=date.today, index=True)
    classification = db.Column(db.String(50), nullable=False)
    recommendation = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Goal(db.Model):
    """Daily goals per user (one active set per user, updated on save)."""
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    screen_limit = db.Column(db.Integer, nullable=True)   # daily screen time limit (minutes)
    study_target = db.Column(db.Float, nullable=True)     # daily study/work target (hours)
    sleep_target = db.Column(db.Float, nullable=True)     # sleep goal (hours)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSession(db.Model):
    """Tracks login sessions per user and basic device info."""

    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    device_info = db.Column(db.String(255), nullable=True)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)

