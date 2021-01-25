from .. import db

class UsageModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String())
    hospital = db.Column(db.String())
    part = db.Column(db.String())
    created_on = db.Column(db.DateTime,server_default=db.func.now())

    def __init__(self, user_id, hospital, part):
        self.user_id = user_id
        self.hospital = hospital
        self.part = part