from datetime import datetime, date
from bson.objectid import ObjectId
from extensions import db

class Activity:
    def __init__(self, **kwargs):
        self._attrs = kwargs
        if '_id' in kwargs:
            self.id = str(kwargs['_id'])
        else:
            self.id = None
            
        # Ensure datetimes are proper instead of strings when querying
        if 'activity_date' in self._attrs and isinstance(self._attrs['activity_date'], datetime):
            # Sometimes dates stay as datetime if they were stored that way
            pass
            
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
        
        # Convert date to datetime for MongoDB compatibility if it's a date object
        if 'activity_date' in attrs and isinstance(attrs['activity_date'], date) and not isinstance(attrs['activity_date'], datetime):
            attrs['activity_date'] = datetime.combine(attrs['activity_date'], datetime.min.time())
            
        if '_id' in attrs:
            db.activities.update_one({'_id': attrs['_id']}, {'$set': {k: v for k, v in attrs.items() if k != '_id'}})
        else:
            if 'created_at' not in attrs:
                attrs['created_at'] = datetime.utcnow()
            result = db.activities.insert_one(attrs)
            self._attrs['_id'] = result.inserted_id
            self.id = str(result.inserted_id)

    @classmethod
    def get_by_id(cls, activity_id):
        try:
            oid = ObjectId(activity_id)
        except Exception:
            return None
        data = db.activities.find_one({'_id': oid})
        return cls(**data) if data else None

    @classmethod
    def find_by_user(cls, user_id, limit=None):
        query = db.activities.find({'user_id': str(user_id)}).sort('activity_date', -1)
        if limit:
            query = query.limit(limit)
        return [cls(**data) for data in query]
