"""server.py - Lightweight Flask server for auto-update + local dev."""
import os, json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


@app.route("/api/status")
def status():
    meta_path = BASE_DIR / "data" / "processed" / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return jsonify({
            "status": "ok",
            "last_update": meta.get("generated_at", "unknown"),
            "grid_count": meta.get("historical_grid_count", 0),
            "nrt_count": meta.get("nrt_detections_count", 0),
        })
    return jsonify({"status": "no_data"})


@app.route("/api/update", methods=["POST"])
def trigger_update():
    token = request.headers.get("X-Update-Token", "")
    expected = os.environ.get("UPDATE_TOKEN", "")
    if expected and token != expected:
        return jsonify({"error": "unauthorized"}), 401

    results = {}
    steps = [
        ("auto_update", "auto_update.py", 300),
        ("fetch_nrt", "fetch_nrt.py", 120),
        ("build_json", "build_json.py", 60),
    ]
    for name, script, timeout in steps:
        try:
            r = subprocess.run(
                [PYTHON, str(SRC_DIR / script)],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(BASE_DIR),
            )
            results[name] = {"success": r.returncode == 0, "output": r.stdout[-300:] if r.stdout else ""}
        except subprocess.TimeoutExpired:
            results[name] = {"success": False, "error": "timeout"}
        except Exception as e:
            results[name] = {"success": False, "error": str(e)}

    all_ok = all(v.get("success", False) for v in results.values())
    return jsonify({
        "status": "complete" if all_ok else "partial",
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/build", methods=["POST"])
def trigger_build():
    try:
        r = subprocess.run(
            [PYTHON, str(SRC_DIR / "build_json.py")],
            capture_output=True, text=True, timeout=60, cwd=str(BASE_DIR),
        )
        return jsonify({"success": r.returncode == 0, "output": r.stdout[-500:] if r.stdout else ""})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/")
def serve_index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(str(BASE_DIR), path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
