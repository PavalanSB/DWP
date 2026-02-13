import secrets

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, UserSession


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _oauth_user_from_email_name(email, name):
    """Find user by email or create one (OAuth). New users get a random password."""
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    user = User(name=name or "User", email=email)
    user.set_password(secrets.token_urlsafe(32))
    db.session.add(user)
    db.session.commit()
    return user


def _create_session_for(user):
    """Create a UserSession entry for this login."""
    ua = request.user_agent
    device = f"{ua.platform or ''} {ua.browser or ''} {ua.version or ''}".strip()
    session = UserSession(
        user_id=user.id,
        device_info=device[:255] if device else "Unknown device",
    )
    db.session.add(session)
    db.session.commit()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "warning")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "1"

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            _create_session_for(user)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next") or url_for("dashboard.dashboard")
            return redirect(next_page)
        else:
            flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("landing"))


@auth_bp.route("/google")
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    oauth = getattr(current_app, "oauth", None)
    if not oauth or not getattr(oauth, "google", None):
        flash("Sign in with Google is not configured.", "warning")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    oauth = getattr(current_app, "oauth", None)
    if not oauth or not getattr(oauth, "google", None):
        flash("Sign in with Google is not configured.", "warning")
        return redirect(url_for("auth.login"))
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash("Sign in with Google was cancelled or failed.", "warning")
        return redirect(url_for("auth.login"))
    userinfo = token.get("userinfo")
    if not userinfo:
        flash("Could not get your Google profile.", "warning")
        return redirect(url_for("auth.login"))
    email = (userinfo.get("email") or "").strip().lower()
    name = (userinfo.get("name") or userinfo.get("given_name") or "User").strip()
    if not email:
        flash("Google did not provide an email address.", "warning")
        return redirect(url_for("auth.login"))
    user = _oauth_user_from_email_name(email, name)
    login_user(user)
    _create_session_for(user)
    flash("Signed in with Google.", "success")
    return redirect(request.args.get("next") or url_for("dashboard.dashboard"))


@auth_bp.route("/facebook")
def facebook_login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    oauth = getattr(current_app, "oauth", None)
    if not oauth or not getattr(oauth, "facebook", None):
        flash("Sign in with Facebook is not configured.", "warning")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.facebook_callback", _external=True)
    return oauth.facebook.authorize_redirect(redirect_uri)


@auth_bp.route("/facebook/callback")
def facebook_callback():
    oauth = getattr(current_app, "oauth", None)
    if not oauth or not getattr(oauth, "facebook", None):
        flash("Sign in with Facebook is not configured.", "warning")
        return redirect(url_for("auth.login"))
    try:
        token = oauth.facebook.authorize_access_token()
    except Exception:
        flash("Sign in with Facebook was cancelled or failed.", "warning")
        return redirect(url_for("auth.login"))
    resp = oauth.facebook.get("me", params={"fields": "id,name,email"})
    if resp.status_code != 200:
        flash("Could not get your Facebook profile.", "warning")
        return redirect(url_for("auth.login"))
    profile = resp.json()
    email = (profile.get("email") or "").strip().lower()
    name = (profile.get("name") or "User").strip()
    if not email:
        flash("Facebook did not provide an email address. Please allow email permission.", "warning")
        return redirect(url_for("auth.login"))
    user = _oauth_user_from_email_name(email, name)
    login_user(user)
    _create_session_for(user)
    flash("Signed in with Facebook.", "success")
    return redirect(request.args.get("next") or url_for("dashboard.dashboard"))

