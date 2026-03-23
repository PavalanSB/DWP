from app import create_app
from extensions import db
from models import User

app = create_app()
with app.app_context():
    # Test PyMongo Insert
    print("Deleting old test user...")
    db.users.delete_many({"email": "test@example.com"})
    
    print("Creating test user...")
    u = User(email="test@example.com", name="Test User")
    u.set_password("password")
    u.save()
    print("User saved. ID:", u.id)

    # Test PyMongo Query
    print("Fetching test user...")
    fetched = User.get_by_email("test@example.com")
    if fetched:
        print("User fetched successfully:")
        print(" - Name:", fetched.name)
        print(" - Email:", fetched.email)
        print(" - Password match:", fetched.check_password("password"))
    else:
        print("FAILED to fetch user.")
