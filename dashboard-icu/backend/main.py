from flask import Flask, jsonify
from flask_cors import CORS
from backend.symulacja import generate_data, check_alarms
"""
Miejsce rozpoczęcie działania prostego API
"""
app = Flask(__name__)
CORS(app)

@app.route("/dane")
def home():
    data = generate_data()
    alarms = check_alarms(data)

    return jsonify({
        "data": data,
        "alarms": alarms
    })

if __name__ == "__main__":
    app.run(debug=True)