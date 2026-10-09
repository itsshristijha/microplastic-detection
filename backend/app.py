import os
import sys
import cv2
import numpy as np
import uuid
import json
import datetime
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS # CRITICAL for React

# Database imports
from dotenv import load_dotenv
import pymongo

# --- 1. SETUP PATHS ---
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.infer import load_model, infer as run_infer

# Configuration
UPLOAD_FOLDER = os.path.join(ROOT, 'uploads')
OUTPUT_FOLDER = os.path.join(ROOT, 'web_outputs')
MODELS_DIR = os.path.join(ROOT, 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'best.onnx')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- CACHE SETUP ---
# Cache for the /api/stats endpoint to minimize MongoDB requests
STATS_CACHE = None
CACHE_TIMESTAMP = 0
CACHE_DURATION_SECONDS = 300  # 5 minutes

# --- 2. INITIALIZE FLASK, MODEL & MONGODB ---
app = Flask(__name__)
CORS(app)

load_dotenv(os.path.join(ROOT, '.env'))
MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client["project_elle"]
        analyses_collection = db["analyses"]
        print("✅ MongoDB connected successfully!")
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        analyses_collection = None
else:
    print("⚠️ MONGO_URI not found in environment. Database persistence disabled.")
    analyses_collection = None

# --- LAZY MODEL LOADING ---
# Model is NOT loaded at startup to avoid OOM on Render free tier (512MB).
# It will be loaded on the first /api/predict request instead.
model_handle = None
MODEL_LOAD_ATTEMPTED = False  # Flag to prevent retrying a failed load every request

# --- 3. THE "BRAIN" LOGIC ---
def calculate_health_risk(total_particles, water_volume_ml=100):
    concentration = total_particles / water_volume_ml
    
    if concentration < 0.1: (status, risk_score) = ("Safe", "Low")
    elif concentration < 0.2: (status, risk_score) = ("Caution", "Moderate")
    else: (status, risk_score) = ("Critical", "High")

    return {
        "concentration_per_ml": concentration,
        "status": status,
        "risk_level": risk_score,
        "message": f"Sample contains {concentration:.2f} particles/mL."
    }

def resize_image_strict(image, size=(640, 640)):
    return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)

# --- 4. API ENDPOINTS ---
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/api/predict', methods=['POST'])
def predict():
    global STATS_CACHE, model_handle, MODEL_LOAD_ATTEMPTED

    # --- Lazy load: only load the model on first request ---
    if model_handle is None and not MODEL_LOAD_ATTEMPTED:
        MODEL_LOAD_ATTEMPTED = True
        print("⏳ Lazy-loading ELLE Model on first request... please wait.")
        try:
            model_config = {
                'weights': MODEL_PATH,
                'format': 'onnx',
                'classes_path': None
            }
            model_handle = load_model(model_config)
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            model_handle = None
            return jsonify({"error": f"Model failed to load: {str(e)}"}), 500

    if model_handle is None:
        return jsonify({"error": "Model is not available. It failed to load on a previous attempt."}), 500

    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    unique_filename = str(uuid.uuid4()) + ".jpg"
    input_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(input_path)

    img = cv2.imread(input_path)
    if img is None:
        return jsonify({"error": "Invalid image file"}), 400

    img_resized = resize_image_strict(img, (640, 640))

    # REDUCED THRESHOLD TO INCREASE SENSITIVITY from 0.25 to 0.10
    results = run_infer(model_handle, img_resized, conf=0.10)

    annotated_img = img_resized.copy()
    class_names = model_handle.classes if model_handle.classes else {}
    
    for box, score, cid in zip(results['boxes'], results['scores'], results['class_ids']):
        x1, y1, x2, y2 = map(int, box)
        label = class_names[cid] if isinstance(class_names, list) and cid < len(class_names) else str(cid)
        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(annotated_img, f"{label} {score:.2f}", (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    output_filename = "processed_" + unique_filename
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    cv2.imwrite(output_path, annotated_img)

    total_count = sum(results['counts_by_class'].values())
    health_impact = calculate_health_risk(total_count)

    response_data = {
        "success": True,
        "image_url": f"{request.host_url}web_outputs/{output_filename}",
        "analysis": {
            "total_particles": total_count,
            "breakdown": results['counts_by_class']
        },
        "health_risk": health_impact
    }

    # Save to MongoDB
    if analyses_collection is not None:
        try:
            db_doc = {
                "timestamp": datetime.datetime.utcnow(),
                "original_filename": file.filename,
                "saved_filename": unique_filename,
                "total_particles": total_count,
                "breakdown": results['counts_by_class'],
                "health_risk": health_impact
            }
            analyses_collection.insert_one(db_doc)
            print(f"📦 Saved analysis {unique_filename} to database")
            
            # Invalidate the cache since new data was added
            STATS_CACHE = None
            
        except Exception as e:
            print(f"⚠️ Failed to save to MongoDB: {e}")

    return jsonify(response_data)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retrieve aggregate statistics from MongoDB for the React Dashboard with caching"""
    global STATS_CACHE, CACHE_TIMESTAMP
    
    if analyses_collection is None:
        return jsonify({"error": "Database not connected"}), 500

    # 1. Check if we have a valid cache
    current_time = time.time()
    if STATS_CACHE and (current_time - CACHE_TIMESTAMP) < CACHE_DURATION_SECONDS:
        print("⚡ Serving dashboard stats from memory cache")
        return jsonify(STATS_CACHE)

    print("📊 Querying MongoDB for fresh dashboard stats...")
    try:
        # Aggregations using MongoDB native pipeline to save RAM
        # 1. Overall stats (total samples, total particles)
        pipeline_stats = [
            {"$group": {"_id": None, "total_samples": {"$sum": 1}, "total_particles_all": {"$sum": "$total_particles"}}}
        ]
        stats_res = list(analyses_collection.aggregate(pipeline_stats))
        
        if not stats_res or stats_res[0].get("total_samples", 0) == 0:
            result = {
                "metrics": {
                    "avg_particles_per_liter": 0,
                    "avg_contamination": "Safe",
                    "total_samples": 0
                },
                "trendData": [],
                "pieData": []
            }
            STATS_CACHE = result
            CACHE_TIMESTAMP = current_time
            return jsonify(result)

        total_samples = stats_res[0]["total_samples"]
        total_particles_all = stats_res[0].get("total_particles_all", 0)
        
        # Calculate avg particles per liter (our formula is per 100mL, so multiply by 10)
        avg_particles = total_particles_all / total_samples
        avg_particles_per_liter = avg_particles * 10
        
        # 2. Breakdown pie data
        pipeline_breakdown = [
            {"$match": {"breakdown": {"$type": "object"}}},
            {"$project": {"breakdown_array": {"$objectToArray": "$breakdown"}}},
            {"$unwind": "$breakdown_array"},
            {"$group": {"_id": "$breakdown_array.k", "count": {"$sum": "$breakdown_array.v"}}}
        ]
        breakdown_res = list(analyses_collection.aggregate(pipeline_breakdown))
        breakdown_counts = {item["_id"]: item["count"] for item in breakdown_res}
        
        pieData = [{"name": k, "value": v, "color": "hsl(175, 80%, 50%)"} for k, v in breakdown_counts.items()]

        # 3. Generate trend line (aggregate by day)
        pipeline_trend = [
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "count": {"$avg": "$total_particles"}
            }},
            {"$sort": {"_id": 1}}
        ]
        trend_res = list(analyses_collection.aggregate(pipeline_trend))
        trendData = [{"date": item["_id"], "count": item["count"]} for item in trend_res if item["_id"]]
        
        # Overall health logic
        if avg_particles_per_liter >= 2.0:  # 0.2/ml * 10
            overall_status = "Danger"
        elif avg_particles_per_liter >= 1.0: # 0.1/ml * 10
            overall_status = "Moderate"
        else:
            overall_status = "Safe"

        result = {
            "metrics": {
                "avg_particles_per_liter": round(avg_particles_per_liter),
                "avg_contamination": overall_status,
                "total_samples": total_samples
            },
            "trendData": trendData,
            "pieData": pieData
        }
        
        # Update Cache
        STATS_CACHE = result
        CACHE_TIMESTAMP = current_time
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/reports', methods=['GET'])
def get_reports():
    """Return the 50 most recent analyses for the Reports page"""
    if analyses_collection is None:
        return jsonify({"error": "Database not connected"}), 500
    try:
        docs = list(analyses_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(50))
        for doc in docs:
            if "timestamp" in doc:
                doc["timestamp"] = doc["timestamp"].isoformat()
        return jsonify({"reports": docs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/web_outputs/<filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_ENV") == "development"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
