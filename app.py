from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line

app = Flask(__name__)
# Allow cross-origin requests so the static HTML can POST from localhost or file://
CORS(app, resources={r"/v1/*": {"origins": "*"}})

def sha256_hash(data: str) -> str:
    #Computes the SHA-256 hash of the input string
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

@app.route("/ping", methods=["GET"])
def ping():
    """Simple health check endpoint."""
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422
    record_data=submission.dict()
    raw_email = record_data['email']
    raw_age = record_data['age']

    record_data['email'] = sha256_hash(raw_email)
    record_data['age'] = sha256_hash(str(raw_age))

    if not record_data.get('submission_id'):
        current_hour_str = datetime.now(timezone.utc).strftime('%Y%m%d%H')
        hash_input = raw_email + current_hour_str
        computed_id = sha256_hash(hash_input)
        record_data['submission_id'] = computed_id

    record = StoredSurveyRecord(
        **submission.dict(),
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")
    )
    append_json_line(record.dict())
    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(host ='127.0.0.1',port=5001, debug=True)
