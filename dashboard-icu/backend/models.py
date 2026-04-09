import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class PatientLog(db.Model):
    __tablename__ = 'patient_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    hr = db.Column(db.Float, nullable=False)
    spo2 = db.Column(db.Float, nullable=False)
    alarms = db.Column(db.String(200))

    def to_dict(self):
        return {
            "timestamp": self.timestamp.strftime("%H:%M:%S"),
            "hr": self.hr,
            "spo2": self.spo2,
            "alarms": self.alarms.split(", ") if self.alarms else []
        }