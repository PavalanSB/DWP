"""
Help view for user guidance.
"""
from flask import Blueprint, render_template
from flask_login import login_required


help_bp = Blueprint("help", __name__, url_prefix="/help")


@help_bp.route("/")
@login_required
def help():
    """Display help and FAQ page."""
    return render_template("help.html")