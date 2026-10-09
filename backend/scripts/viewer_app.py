import os
import json
from flask import Flask, render_template, send_from_directory, jsonify

# Paths
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ANNOTATED_DIR = os.path.join(ROOT, 'annotated')
RESULTS_DIR = os.path.join(ROOT, 'results')
STATS_FILE = os.path.join(RESULTS_DIR, 'stats.json')

os.makedirs(ANNOTATED_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

app = Flask(__name__)

@app.route('/')
def index():
    # Load statistics
    stats = {}
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                stats = json.load(f)
        except Exception:
            stats = {}
    # List annotated images (safe if folder empty)
    try:
        images = [f for f in os.listdir(ANNOTATED_DIR) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        images.sort()
    except Exception:
        images = []
    return render_template('index.html', stats=stats, images=images)

@app.route('/annotated/<filename>')
def annotated_image(filename):
    return send_from_directory(ANNOTATED_DIR, filename)

@app.route('/stats')
def stats_api():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)
        return jsonify(stats)
    return jsonify({})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
