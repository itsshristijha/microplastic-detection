<div align="center">

# 🌊 ELLE
### Environmental Microplastic Detection System

*AI-powered microscopic particle analysis for researchers and citizen scientists*

[![Built with React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB?logo=react&style=flat-square)](https://react.dev/)
[![Backend Flask](https://img.shields.io/badge/Backend-Flask%20%28Python%29-000000?logo=flask&style=flat-square)](https://flask.palletsprojects.com/)
[![AI Engine](https://img.shields.io/badge/AI%2FML-YOLOv8%20%2B%20PyTorch-EE4C2C?logo=pytorch&style=flat-square)](https://ultralytics.com/)
[![Database](https://img.shields.io/badge/Database-MongoDB%20Atlas-47A248?logo=mongodb&style=flat-square)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

</div>

---

**Project ELLE** is an AI-driven, full-stack platform that automates the detection and classification of microplastics in water samples. Upload a microscopic image, receive instant particle classifications with annotated bounding boxes, and generate actionable environmental health risk assessments — no laboratory infrastructure required.

Developed as part of the **EPICS Project**.

---

## Table of Contents

- [The Problem](#-the-problem)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [AI & Machine Learning](#-ai--machine-learning)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Deployment](#-deployment)

---

## 🧪 The Problem

Microplastics are pervasive in global ecosystems — infiltrating drinking water, food chains, and marine habitats. Traditional detection methods are slow, cost-prohibitive, and require specialized laboratory infrastructure, creating a massive bottleneck for environmental monitoring at scale.

ELLE bridges this gap by combining a custom-trained deep learning model with an intuitive analytical dashboard, making sophisticated environmental diagnostics accessible to anyone with a microscope.

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| **Real-Time Detection** | Drag-and-drop microscopic images for instant server-side inference with on-image bounding box annotations |
| **Analytics Dashboard** | Filter and monitor historical sample trends with dynamic graphs powered by Recharts |
| **Global Hotspot Map** | Visualize contamination concentrations geographically via an interactive Leaflet map |
| **PDF Report Export** | Generate and download standardized, audit-ready PDF summaries of any sample analysis |

---

## 🏗️ Architecture

ELLE uses a decoupled, cloud-native full-stack architecture optimized for high-throughput ML inference and responsive UX.

```
┌─────────────────────────────────────────────────────────────┐
│                       REACT FRONTEND                        │
│          (Vite + Tailwind CSS + Shadcn/UI + Leaflet)        │
└─────────────────────────────┬───────────────────────────────┘
                              │  HTTPS · POST /api/analyze
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        FLASK BACKEND                        │
│             (Python API + Request Controller)               │
└────────────────────┬──────────────────────────┬─────────────┘
                     │                          │
            ▼ Local Inference           ▼ Metadata Sync
      ┌───────────────────────┐   ┌──────────────────────────┐
      │     YOLOv8 ENGINE     │   │      MONGODB ATLAS       │
      │  (PyTorch + OpenCV)   │   │    (NoSQL Cloud DB)      │
      └───────────────────────┘   └──────────────────────────┘

```

### Stack

| Layer | Technology | Libraries |
|---|---|---|
| **Frontend** | React 18 (Vite) | Tailwind CSS, Shadcn/UI, Leaflet, Recharts, Framer Motion |
| **Backend** | Python 3.10+ | Flask, Gunicorn |
| **AI / ML** | PyTorch | Ultralytics YOLOv8, OpenCV |
| **Database** | NoSQL | MongoDB Atlas |

### Data Flow

1. **Upload** — User drops a microscopic water sample image into the React UI
2. **Delivery** — Frontend sends the image via `multipart/form-data` POST to the Flask API
3. **Inference** — Backend processes the image with OpenCV and runs it through the YOLOv8 model
4. **Post-Processing** — Bounding boxes, confidence scores, and particle counts are computed; OpenCV annotates the image
5. **Persistence** — Quantitative data, coordinates, and hazard levels are written to MongoDB Atlas
6. **Render** — Backend returns the annotated image URI and structured JSON metadata to the client
7. **Export** — User can trigger on-demand PDF report generation from the dashboard

---

## 🧠 AI & Machine Learning

The core analytical pipeline uses a custom-tuned **YOLOv8** model trained specifically for micro-particle morphology.

### Model Specs

| Parameter | Value |
|---|---|
| Architecture | YOLOv8nano (`yolov8n.pt`) |
| Input Resolution | 640 × 640 px (normalized via OpenCV) |
| Confidence Threshold | ≥ 0.10 (hyper-sensitive to capture translucent/low-contrast particles) |

### Particle Classifications

| Class | Description |
|---|---|
| 🔹 **Fragment** | Hard, jagged, irregular particles splintered off larger plastic waste |
| 🧵 **Fiber** | Elongated filaments from synthetic textiles or fishing gear |
| 🎞️ **Film** | Ultra-thin transparent fragments from plastic bags or packaging |
| 🔮 **Pellet** | Spherical industrial pre-production resin beads |
| 🧽 **Foam** | Aerated cellular structures from polystyrene insulation or packaging |

### Health Risk Assessment

Contamination level is calculated by volumetric density ratio:

$$\text{Concentration} = \frac{\text{Total Detected Particles}}{\text{Sample Volume (mL)}}$$

| Risk Level | Threshold | Indicator |
|---|---|---|
| **Safe** | < 0.1 particles/mL | 🟢 Low Risk |
| **Caution** | 0.1 – 0.2 particles/mL | 🟡 Moderate Risk |
| **Critical** | > 0.2 particles/mL | 🔴 High Risk |

---

## 📦 Project Structure

```
ELLE/
├── frontend/                   # React + Vite application
│   ├── src/
│   │   ├── components/         # Reusable UI elements (Shadcn/UI)
│   │   ├── pages/              # Dashboard, Map, Upload views
│   │   └── utils/              # Mapping and analytics config
│   └── package.json
│
├── backend/                    # Flask API + ML engine
│   ├── app.py                  # Main application server
│   ├── models/                 # Custom YOLOv8 weights (best.pt)
│   ├── requirements.txt        # Python dependencies
│   └── utils/                  # PDF engine and database client
│
├── documentation/              # Technical whitepapers and research
└── start_elle.bat              # Windows dev automation script
```

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.10+
- Node.js v18+ and npm
- A MongoDB Atlas cluster (free tier works)

### 1. Clone the repository

```bash
git clone https://github.com/itsshristijha/microplastic-detection.git
cd microplastic-detection
```

### 2. Configure environment variables

**Backend** — copy `backend/.env.example` to `backend/.env`:
```env
MONGO_URI=your_mongodb_atlas_connection_string
PORT=5000
```

MongoDB is optional for image inference, but the reports and statistics APIs require it.

**Frontend** — copy `frontend/.env.example` to `frontend/.env.local` and fill in the Firebase web-app configuration from your Firebase project:
```env
VITE_API_BASE_URL=http://localhost:5000
# Add the VITE_FIREBASE_* values listed in frontend/.env.example.
```

### 3. Install dependencies

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 4. Run the application

**Option A — Automated (Windows):**
```bash
./start_elle.bat
```

**Option B — Manual:**
```bash
# Terminal 1: Backend (from /backend with venv active)
python app.py

# Terminal 2: Frontend (from /frontend)
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🌐 Deployment

| Service | Provider |
|---|---|
| **Frontend** | [Vercel](https://vercel.com) — the repository includes a root-level `vercel.json` |
| **Backend** | [Render](https://render.com) — the repository includes a `render.yaml` blueprint for the Flask/ONNX API |
| **Database** | [MongoDB Atlas](https://www.mongodb.com/atlas) — Shared Tier cloud cluster |

### Deploy

1. Create the Flask API from this repository in Render using the included `render.yaml` blueprint. Set `MONGO_URI` in Render if you want persistent reports and dashboard statistics. The API health-check endpoint is `/api/health`.
2. Import the GitHub repository into Vercel. Leave **Root Directory** at the repository root; the included configuration installs and builds the Vite app in `frontend/`.
3. In Vercel project settings, set `VITE_API_BASE_URL` to the deployed Render service URL (without a trailing slash) and add the `VITE_FIREBASE_*` values from `frontend/.env.example`. Redeploy after setting environment variables.
4. In Firebase Authentication settings, add the Vercel deployment domain to the authorized domains.

The Vercel deployment hosts the React frontend; the Flask inference API must run on a Python-capable host such as Render. Do not commit populated `.env` files or production credentials.

---

<div align="center">

Built for the **EPICS Project** &nbsp;·&nbsp; *Making environmental science accessible*

</div>
