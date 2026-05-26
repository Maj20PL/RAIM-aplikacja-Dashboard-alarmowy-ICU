from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class PatientLog(db.Model):
    """Pojedynczy zapis pomiaru pacjenta w bazie SQLite."""

    __tablename__ = "patient_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.String(20))
    patient_name = db.Column(db.String(80))
    ward_id = db.Column(db.String(20))
    ward_name = db.Column(db.String(80))
    bed = db.Column(db.String(20))
    record_name = db.Column(db.String(20))
    hr = db.Column(db.Float, nullable=False)
    spo2 = db.Column(db.Float, nullable=False)
    alarms = db.Column(db.String(200))

    def to_dict(self):
        """Zwraca log w formacie JSON uzywanym przez frontend."""

        return {
            "timestamp": self.timestamp.strftime("%H:%M:%S"),
            "patientId": self.patient_id,
            "patientName": self.patient_name,
            "wardId": self.ward_id,
            "wardName": self.ward_name,
            "bed": self.bed,
            "record": self.record_name,
            "hr": self.hr,
            "spo2": self.spo2,
            "alarms": self.alarms.split(", ") if self.alarms else [],
        }
