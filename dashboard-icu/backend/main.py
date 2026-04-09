import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from .models import db, PatientLog
from .symulacja import Symulacja


logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(project_dir, 'icu_database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    simulator = Symulacja(record_name='203')


@app.route("/data")
def get_data():
    data = simulator.get_data()

    log = PatientLog(
        hr=data['hr'],
        spo2=data['spo2'],
        alarms=", ".join(data['alarms'])
    )
    db.session.add(log)
    db.session.commit()

    logger.info(f"Pobrano i zapisano: HR={data['hr']} BPM")
    return jsonify(data)


@app.route("/history")
def get_history():
    logs = PatientLog.query.order_by(PatientLog.id.desc()).limit(20).all()
    return jsonify([l.to_dict() for l in logs])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)