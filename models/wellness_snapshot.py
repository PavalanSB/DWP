from datetime import datetime, date
from bson.objectid import ObjectId
from extensions import db

class WellnessSnapshot:
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
        
        # Convert date to datetime if necessary
        if 'snapshot_date' in attrs and isinstance(attrs['snapshot_date'], date) and not isinstance(attrs['snapshot_date'], datetime):
            attrs['snapshot_date'] = datetime.combine(attrs['snapshot_date'], datetime.min.time())
            
        if '_id' in attrs:
            db.wellness_snapshots.update_one({'_id': attrs['_id']}, {'$set': {k: v for k, v in attrs.items() if k != '_id'}})
        else:
            if 'created_at' not in attrs:
                attrs['created_at'] = datetime.utcnow()
            result = db.wellness_snapshots.insert_one(attrs)
            self._attrs['_id'] = result.inserted_id
            self.id = str(result.inserted_id)

    @classmethod
    def get_latest_for_user(cls, user_id):
        data = db.wellness_snapshots.find_one(
            {'user_id': str(user_id)}, 
            sort=[('snapshot_date', -1)]
        )
        return cls(**data) if data else None

    @classmethod
    def find_by_user_and_date(cls, user_id, snapshot_date):
        if isinstance(snapshot_date, date) and not isinstance(snapshot_date, datetime):
            snapshot_date = datetime.combine(snapshot_date, datetime.min.time())
            
        data = db.wellness_snapshots.find_one({
            'user_id': str(user_id),
            'snapshot_date': snapshot_date
        })
        return cls(**data) if data else None
