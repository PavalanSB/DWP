from datetime import datetime
from bson.objectid import ObjectId
from extensions import db

class UserSession:
    def __init__(self, **kwargs):
        self._attrs = kwargs
        if '_id' in kwargs:
            self.id = str(kwargs['_id'])
        else:
            self.id = None

    def __getattr__(self, name):
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

    def save(self):
        attrs = dict(self._attrs)
        if '_id' in attrs:
            db.user_sessions.update_one({'_id': attrs['_id']}, {'$set': {k: v for k, v in attrs.items() if k != '_id'}})
        else:
            if 'login_time' not in attrs:
                attrs['login_time'] = datetime.utcnow()
            if 'last_active' not in attrs:
                attrs['last_active'] = datetime.utcnow()
            if 'is_active' not in attrs:
                attrs['is_active'] = True
            result = db.user_sessions.insert_one(attrs)
            self._attrs['_id'] = result.inserted_id
            self.id = str(result.inserted_id)

    @classmethod
    def get_by_user(cls, user_id):
        sessions = db.user_sessions.find({'user_id': str(user_id)}).sort('last_active', -1)
        return [cls(**data) for data in sessions]
