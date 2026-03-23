from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson.objectid import ObjectId
from extensions import db, login_manager

class User(UserMixin):
    def __init__(self, **kwargs):
        self._attrs = kwargs
        # Set id for Flask-Login
        if '_id' in kwargs:
            self.id = str(kwargs['_id'])
        else:
            self.id = None

    def __getattr__(self, name):
        # Allow dotted access like user.email = ...
        if name in ['_attrs', 'id']:
            return super().__getattribute__(name)
        if name in self._attrs:
            return self._attrs[name]
        return None

    def __setattr__(self, name, value):
        if name in ['_attrs', 'id']:
            super().__setattr__(name, value)
        else:
            self._attrs[name] = value

    @property
    def is_active(self):
        return True

    def get_id(self):
        return self.id

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        self.password_updated_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash or "", password)

    def save(self):
        # Insert or update
        attrs = dict(self._attrs)
        if '_id' in attrs:
            # Update
            db.users.update_one({'_id': attrs['_id']}, {'$set': {k: v for k, v in attrs.items() if k != '_id'}})
        else:
            # Insert
            if 'created_at' not in attrs:
                attrs['created_at'] = datetime.utcnow()
            result = db.users.insert_one(attrs)
            self._attrs['_id'] = result.inserted_id
            self.id = str(result.inserted_id)

    @classmethod
    def get_by_id(cls, user_id):
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        data = db.users.find_one({'_id': oid})
        return cls(**data) if data else None

    @classmethod
    def get_by_email(cls, email):
        data = db.users.find_one({'email': email})
        return cls(**data) if data else None

@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    user = User.get_by_id(user_id)
    if user is None:
        from flask import session
        session.pop("_user_id", None)
    return user
