from datetime import datetime, timezone

from flask import Flask, jsonify, request

from _shared import cors_headers, read_repo_json, write_repo_json

app = Flask(__name__)

ALLOWED_STATUSES = {"new", "shortlisted", "applied", "interview", "rejected"}


@app.route("/", defaults={"path": ""}, methods=["POST", "OPTIONS"])
@app.route("/<path:path>", methods=["POST", "OPTIONS"])
def status(path):
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())

    body = request.get_json(force=True, silent=True) or {}
    job_id = body.get("job_id")
    new_status = body.get("status")

    if not job_id or new_status not in ALLOWED_STATUSES:
        resp = jsonify({"error": "job_id and a valid status are required"})
        return resp, 400, cors_headers()

    status_data, sha = read_repo_json("docs/status.json", default={})
    status_data[job_id] = {
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_repo_json(
        "docs/status.json", status_data,
        f"portal: {job_id} -> {new_status} [skip ci]", sha=sha,
    )

    resp = jsonify({"ok": True})
    return resp, 200, cors_headers()
