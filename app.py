from datetime import date
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, redirect, url_for
from flask_login import current_user

from config import get_config
from extensions import init_extensions, db
from ml import wellness_model
from models import Activity, WellnessSnapshot


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    # Ensure upload folder exists
    upload_folder = app.config.get("UPLOAD_FOLDER")
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)

    init_extensions(app)

    # OAuth (Google & Facebook) – credentials from env
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        oauth.register(
            "google",
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    if app.config.get("FACEBOOK_CLIENT_ID") and app.config.get("FACEBOOK_CLIENT_SECRET"):
        oauth.register(
            "facebook",
            client_kwargs={"scope": "email public_profile"},
            authorize_url="https://www.facebook.com/v21.0/dialog/oauth",
            authorize_params=None,
            access_token_url="https://graph.facebook.com/v21.0/oauth/access_token",
            access_token_params=None,
        )
    app.oauth = oauth

    # Register blueprints
    from views.auth import auth_bp
    from views.dashboard import dashboard_bp
    from views.activity import activity_bp
    from views.analytics import analytics_bp
    from views.insights import insights_bp
    from views.profile import profile_bp
    from views.settings import settings_bp
    from views.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def landing():
        # Logged-in users go straight to dashboard; landing page only for guests
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.dashboard"))
        return render_template("landing.html")

    with app.app_context():
        db.create_all()

    return app


def update_daily_wellness_snapshot(user):
    """
    Create or update today's wellness snapshot using latest activity and 8-feature ML model.
    """
    today = date.today()
    latest_activity = (
        Activity.query.filter_by(user_id=user.id, activity_date=today)
        .order_by(Activity.created_at.desc())
        .first()
    )
    if not latest_activity:
        return

    # Category times (default 0 for legacy activities)
    social = getattr(latest_activity, "social_time", None) or 0
    learning = getattr(latest_activity, "learning_time", None) or 0
    entertainment = getattr(latest_activity, "entertainment_time", None) or 0
    productivity = getattr(latest_activity, "productivity_time", None) or 0
    gaming = getattr(latest_activity, "gaming_time", None) or 0
    total = social + learning + entertainment + productivity + gaming
    if total == 0:
        total = latest_activity.screen_time_minutes or 0
    stress = getattr(latest_activity, "stress_level", None) or 3
    energy = getattr(latest_activity, "energy_level", None) or 3

    prediction = wellness_model.predict(
        social_time=social,
        learning_time=learning,
        entertainment_time=entertainment,
        productivity_time=productivity,
        gaming_time=gaming,
        sleep_hours=latest_activity.sleep_hours,
        stress_level=stress,
        energy_level=energy,
    )

    snapshot = WellnessSnapshot.query.filter_by(
        user_id=user.id, snapshot_date=today
    ).first()
    if not snapshot:
        snapshot = WellnessSnapshot(
            user_id=user.id,
            snapshot_date=today,
            classification=prediction.label,
            recommendation=prediction.recommendation,
        )
        db.session.add(snapshot)
    else:
        snapshot.classification = prediction.label
        snapshot.recommendation = prediction.recommendation

    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
