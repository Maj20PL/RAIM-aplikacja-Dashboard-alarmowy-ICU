import logging
from flask import Flask, jsonify
from flask_cors import CORS
from backend.symulacja import generate_data, check_alarms
"""
Miejsce rozpoczęcie działania prostego API
"""

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logi = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route("/dane")
@app.route("/dane")
def home():
    data = generate_data()
    alarms = check_alarms(data)

    logi.info(f"Generowanie danych: HR={data['hr']}, SpO2={data['spo2']}")
    if alarms:
        logi.warning(
            f"Ponad granice: HR={data['hr']}, SpO2={data['spo2']} -> {alarms}"
        )

    return jsonify({
        "data": data,
        "alarms": alarms
    })

if __name__ == "__main__":
    app.run(debug=True)