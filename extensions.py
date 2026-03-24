from flask_login import LoginManager
from pymongo import MongoClient
import os
from werkzeug.local import LocalProxy
from flask import current_app, g
from flask_cors import CORS

# Initialize CORS
cors = CORS()

# Helper to get the db reference easily in any request
def get_db():
    if 'db' not in g:
        client = MongoClient(current_app.config["MONGO_URI"])
        # db name can be parsed from URI or use default 'dwp'
        # pymongo gets default database from URI if provided
        g.db = client.get_database() 
    return g.db

# db proxy to be imported from models/views
db = LocalProxy(get_db)

login_manager = LoginManager()

def init_extensions(app):
    """Initialize Flask extensions."""
    login_manager.init_app(app)
    
    # Configure CORS to allow credentials from the frontend origin
    cors.init_app(app, supports_credentials=True, origins=[
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "https://dwp-vert.vercel.app",
        os.environ.get("FRONTEND_URL", "https://dwp-vert.vercel.app")
    ])

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

