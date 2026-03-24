import secrets

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, UserSession


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _oauth_user_from_email_name(email, name, provider="google"):
    """Find user by email or create one (OAuth). New users get a random password.

    Also records the oauth provider in `auth_provider` so we can treat
    oauth-created accounts differently (for example reauth flows).
    """
    user = User.get_by_email(email)
    if user:
        # If existing user has no provider set, set it now for consistency
        if not getattr(user, "auth_provider", None):
            user.auth_provider = provider
            user.save()
        return user
    user = User(name=name or "User", email=email, auth_provider=provider)
    user.set_password(secrets.token_urlsafe(32))
    user.save()
    return user


def _create_session_for(user):
    """Create a UserSession entry for this login."""
    ua = request.user_agent
    device = f"{ua.platform or ''} {ua.browser or ''} {ua.version or ''}".strip()
    session = UserSession(
        user_id=user.id,
        device_info=device[:255] if device else "Unknown device",
    )
    session.save()


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
        elif User.get_by_email(email):
            flash("An account with this email already exists.", "warning")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            user.save()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/google-register", methods=["GET", "POST"])
def google_register():
    """Register a new user account after Google OAuth verification."""
    from flask import session as flask_session
    
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))
    
    # Check if user came from Google OAuth
    google_email = flask_session.get('google_email')
    google_name = flask_session.get('google_name')
    
    if not google_email:
        flash("Invalid registration request. Please sign in with Google again.", "danger")
        return redirect(url_for("auth.google_login"))
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Email should match Google email
        if email != google_email:
            flash("Email must match your Google account email.", "danger")
            return redirect(url_for("auth.google_register"))
        
        if not name or not email or not password:
            flash("All fields are required.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif User.get_by_email(email):
            flash("An account with this email already exists.", "warning")
        else:
            # Create user with Google provider
            user = User(name=name, email=email, auth_provider="google")
            user.set_password(password)
            user.save()
            
            # Clear Google session data
            flask_session.pop('google_email', None)
            flask_session.pop('google_name', None)
            
            # Log them in
            login_user(user)
            _create_session_for(user)
            flash("Account created successfully with Google. You are now logged in.", "success")
            return redirect(url_for("dashboard.dashboard"))
    
    # GET request - show form with pre-filled Google data
    return render_template("auth/google_register.html", 
                         google_email=google_email, 
                         google_name=google_name)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "1"

        user = User.get_by_email(email)
        if user:
            if getattr(user, "is_locked", False):
                flash("Your account is locked. Please contact an admin to unlock.", "danger")
                return render_template("auth/login.html")

            if user.check_password(password):
                # Reset failed login attempts on successful login
                if getattr(user, "failed_login_attempts", 0) > 0:
                    user.failed_login_attempts = 0
                    user.save()

                login_user(user, remember=remember)
                _create_session_for(user)
                flash("Logged in successfully.", "success")
                next_page = request.args.get("next") or url_for("dashboard.dashboard")
                return redirect(next_page)
            else:
                # Increment failed attempts
                user.failed_login_attempts = getattr(user, "failed_login_attempts", 0) + 1
                if user.failed_login_attempts >= 3:
                    user.is_locked = True
                    user.save()
                    flash("Incorrect password. Your account is now locked due to 3 failed attempts.", "danger")
                else:
                    attempts_left = 3 - user.failed_login_attempts
                    user.save()
                    flash(f"Incorrect password. You have {attempts_left} attempt(s) left.", "danger")
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
    
    # Store action to distinguish between login and signup
    action = request.args.get('action', 'login')
    from flask import session as flask_session
    flask_session['google_auth_action'] = action
    
    # Use OAUTH_BASE_URL if set, else fallback to request.host_url
    base_url = current_app.config.get("OAUTH_BASE_URL")
    if not base_url or "localhost" in base_url or "127.0.0.1" in base_url:
        base_url = request.host_url.replace('127.0.0.1', 'localhost').rstrip('/')
    redirect_uri = base_url + url_for("auth.google_callback")
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    oauth = getattr(current_app, "oauth", None)
    if not oauth or not getattr(oauth, "google", None):
        flash("Sign in with Google is not configured.", "warning")
        return redirect(url_for("auth.login"))
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        error_msg = str(e)
        if "redirect_uri_mismatch" in error_msg:
            flash(
                f"OAuth setup error: Redirect URI mismatch. Please ensure both '{current_app.config.get('OAUTH_BASE_URL')}/auth/google/callback' and 'http://127.0.0.1:5000/auth/google/callback' are registered in Google Cloud Console.",
                "danger",
            )
        else:
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
    
    # Check action
    from flask import session as flask_session
    action = flask_session.get('google_auth_action', 'login')
    
    # Check if user already exists
    user = User.get_by_email(email)
    
    if action == 'register':
        if user:
            # User exists but clicked Sign Up
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for("auth.login"))
        else:
            # New user, proceed to register
            flask_session['google_email'] = email
            flask_session['google_name'] = name
            flash("Please complete your registration to create an account.", "info")
            return redirect(url_for("auth.google_register"))
            
    else: # login action
        if user:
            # User exists - log them in
            login_user(user)
            _create_session_for(user)
            flash("Signed in with Google.", "success")
            return redirect(request.args.get("next") or url_for("dashboard.dashboard"))
        else:
            # User doesn't exist but clicked Login
            flash("No account found with this email. Please sign up.", "info")
            return redirect(url_for("auth.register"))

