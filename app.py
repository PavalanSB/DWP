from datetime import date
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, redirect, url_for, jsonify
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

    # OAuth (Google only) – credentials from env
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth()
    oauth.init_app(app)
    
    google_client_id = app.config.get("GOOGLE_CLIENT_ID", "")
    google_client_secret = app.config.get("GOOGLE_CLIENT_SECRET", "")
    
    # Debug: Print whether credentials are loaded
    print(f"[OAuth Setup] Google Client ID loaded: {bool(google_client_id)}")
    if google_client_id:
        print(f"[OAuth Setup] Client ID (first 20 chars): {google_client_id[:20]}...")
    
    if google_client_id and google_client_secret:
        try:
            oauth.register(
                name="google",
                client_id=google_client_id,
                client_secret=google_client_secret,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
            print("[OAuth Setup] Google OAuth registered successfully")
        except Exception as e:
            print(f"[OAuth Setup] Failed to register Google OAuth: {e}")
    else:
        print("[OAuth Setup] WARNING: Google credentials not found in config!")
        print(f"[OAuth Setup] GOOGLE_CLIENT_ID in .env: {bool(os.environ.get('GOOGLE_CLIENT_ID'))}")
        print(f"[OAuth Setup] GOOGLE_CLIENT_SECRET in .env: {bool(os.environ.get('GOOGLE_CLIENT_SECRET'))}")
    
    app.oauth = oauth

    # Register blueprints
    from views.auth import auth_bp
    from views.dashboard import dashboard_bp
    from views.activity import activity_bp
    from views.analytics import analytics_bp
    from views.insights import insights_bp
    from views.profile import profile_bp
    from views.settings import settings_bp
    from views.goals import goals_bp
    from views.help import help_bp
    from views.api import api_bp
    from views.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.route("/")
    def landing():
        # Logged-in users go straight to dashboard; landing page only for guests
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.dashboard"))
        return render_template("landing.html")

    @app.route("/debug/oauth")
    def debug_oauth():
        """Debug endpoint to check OAuth configuration"""
        from flask import jsonify
        oauth_config = app.oauth
        google_oauth = getattr(oauth_config, "google", None)
        
        return jsonify({
            "google_oauth_registered": google_oauth is not None,
            "client_id_set": bool(app.config.get("GOOGLE_CLIENT_ID")),
            "client_secret_set": bool(app.config.get("GOOGLE_CLIENT_SECRET")),
            "client_id_preview": (app.config.get("GOOGLE_CLIENT_ID", "")[:20] + "...") if app.config.get("GOOGLE_CLIENT_ID") else "NOT SET",
            "flask_env": os.environ.get("FLASK_ENV", "not set"),
            "app_debug": app.debug,
            "message": "If google_oauth_registered is False, check your .env file for GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
        })

    @app.route("/insights")
    def insights():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        snapshot = WellnessSnapshot.get_latest_for_user(current_user.id)
        wellness_score = snapshot.wellness_score if snapshot and hasattr(snapshot, 'wellness_score') else 0
        classification = snapshot.classification if snapshot else "Unknown"
        recommendations = get_recommendations(wellness_score, classification)

        return render_template(
            "insights.html",
            snapshot=snapshot,
            wellness_score=wellness_score,
            classification=classification,
            recommendations=recommendations,
        )

    return app


def update_daily_wellness_snapshot(user):
    """
    Create or update today's wellness snapshot using latest activity and 8-feature ML model.
    """
    from datetime import datetime
    today = date.today()
    today_dt = datetime.combine(today, datetime.min.time())
    
    # Get latest activity for today
    data = db.activities.find_one(
        {'user_id': str(user.id), 'activity_date': {"$gte": today_dt}}, 
        sort=[('created_at', -1)]
    )
    latest_activity = Activity(**data) if data else None
    
    if not latest_activity:
        return

    # Category times (default 0 for legacy activities)
    social = getattr(latest_activity, "social_time", None) or 0
    learning = getattr(latest_activity, "learning_time", None) or 0
    entertainment = getattr(latest_activity, "entertainment_time", None) or 0
    productivity = getattr(latest_activity, "productivity_time", None) or 0
    total = social + learning + entertainment + productivity
    if total == 0:
        total = latest_activity.screen_time_minutes or 0
    stress = getattr(latest_activity, "stress_level", None) or 3
    energy = getattr(latest_activity, "energy_level", None) or 3
    sleep = latest_activity.sleep_hours or 0

    prediction = wellness_model.predict(
        social_time=social,
        learning_time=learning,
        entertainment_time=entertainment,
        productivity_time=productivity,
        sleep_hours=sleep,
        stress_level=stress,
        energy_level=energy,
    )

    snapshot = WellnessSnapshot.find_by_user_and_date(user.id, today)
    if not snapshot:
        snapshot = WellnessSnapshot(
            user_id=str(user.id),
            snapshot_date=today,
            classification=prediction.label,
            recommendation=prediction.recommendation,
        )
    else:
        snapshot.classification = prediction.label
        snapshot.recommendation = prediction.recommendation

    snapshot.save()


def get_recommendations(wellness_score, classification):
    """
    Generate detailed and actionable recommendations based on the wellness score and classification.
    """
    recommendations = []

    if classification == "Healthy":
        recommendations.append("Maintain your current habits to stay healthy.")
        recommendations.append("Explore new wellness activities like yoga or meditation to enhance your routine.")
        recommendations.append("Consider setting new goals to challenge yourself and grow further.")
    elif classification == "Moderate":
        recommendations.append("Focus on getting consistent sleep by setting a regular bedtime.")
        recommendations.append("Incorporate at least 30 minutes of physical activity into your daily routine.")
        recommendations.append("Practice mindfulness or relaxation techniques to reduce stress.")
    elif classification == "Unhealthy":
        recommendations.append("Prioritize getting 7-8 hours of sleep each night.")
        recommendations.append("Limit screen time, especially before bed, to improve sleep quality.")
        recommendations.append("Start with small, manageable changes like taking short walks or drinking more water.")
    elif classification == "Burnout":
        recommendations.append("Take immediate steps to reduce stress, such as deep breathing or meditation.")
        recommendations.append("Schedule regular breaks during work to avoid overexertion.")
        recommendations.append("Reach out to a trusted friend, family member, or professional for support.")

    return recommendations


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
