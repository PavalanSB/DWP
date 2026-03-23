import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from app import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    # Check if we have an admin
    admin = User.query.filter_by(email="admin@example.com").first()
    if not admin:
        admin = User(name="System Admin", email="admin@example.com", is_admin=True)
        admin.set_password("admin123")
        db.session.add(admin)
        print("Created admin@example.com with password 'admin123'")

    # Check for a normal user to lock
    user1 = User.query.filter_by(email="user@example.com").first()
    if not user1:
        user1 = User(name="Normal User", email="user@example.com", is_admin=False)
        user1.set_password("user123")
        db.session.add(user1)
        print("Created user@example.com with password 'user123'")

    db.session.commit()
    print("Test users ready.")
