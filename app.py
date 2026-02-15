import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

import qrcode
from io import BytesIO
import base64

app = Flask(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "/data")
QR_DIR = os.path.join(DATA_DIR, "qr_codes")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

os.makedirs(QR_DIR, exist_ok=True)


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate_qr():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    file_id = str(uuid.uuid4())
    filename = f"{file_id}.png"
    filepath = os.path.join(QR_DIR, filename)
    img.save(filepath)

    # Also generate base64 for preview
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    entry = {
        "id": file_id,
        "url": url,
        "filename": filename,
        "created_at": datetime.now().isoformat(),
    }

    history = load_history()
    history.insert(0, entry)
    save_history(history)

    return jsonify({"id": file_id, "url": url, "image": b64, "filename": filename})


@app.route("/api/history")
def get_history():
    return jsonify(load_history())


@app.route("/api/qr/<file_id>")
def get_qr_image(file_id):
    """Return base64 image data for a history entry."""
    filename = f"{file_id}.png"
    filepath = os.path.join(QR_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Not found"}), 404
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return jsonify({"image": b64})


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(QR_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
