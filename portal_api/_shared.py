"""Shared helpers for the portal's Vercel Python backend."""
import base64
import json
import os

import requests

GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
GITHUB_API = "https://api.github.com"
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


def _headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def read_repo_json(path, default=None):
    """Returns (data, sha). sha is None if the file doesn't exist yet."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    resp = requests.get(url, headers=_headers(), params={"ref": GITHUB_BRANCH}, timeout=15)
    if resp.status_code == 404:
        return default, None
    resp.raise_for_status()
    payload = resp.json()
    content = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(content), payload["sha"]


def write_repo_json(path, obj, message, sha=None):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    content = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha
    resp = requests.put(url, headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()


def find_job(job_id):
    jobs_data, _ = read_repo_json("docs/jobs.json", default={"jobs": []})
    for j in jobs_data.get("jobs", []):
        if j.get("id") == job_id:
            return j
    return None


def cors_headers():
    return {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def load_master_cv():
    """Loaded from the MASTER_CV_JSON env var (a Vercel secret) — deliberately
    NOT committed to the repo, since the repo is public and this contains
    Omar's name/phone/email."""
    raw = os.environ.get("MASTER_CV_JSON")
    if not raw:
        raise RuntimeError("MASTER_CV_JSON environment variable is not set")
    return json.loads(raw)
