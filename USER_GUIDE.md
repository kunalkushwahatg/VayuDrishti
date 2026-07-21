# VayuDrishti - User Guide

This guide will help you set up and run the VayuDrishti application locally. The project is split into a **Python FastAPI backend** and a **React Vite frontend**.

## ✨ Latest Changes

- **Multilingual citizen advisories** — advisories are now auto-generated in each city's regional language: Bengaluru → **Kannada**, Chennai → **Tamil**, Mumbai → Marathi, Kolkata → Bengali, Hyderabad → Telugu (Delhi defaults to Hindi).
- **Real NASA FIRMS satellite integration (Agent 6)** — anomaly investigation now uses real VIIRS active-fire detections and live wind to reason about pollution sources (add an optional `FIRMS_MAP_KEY`, see below).
- **Forecast accuracy metric** — the app now measures its 24h AQI forecast RMSE against a persistence baseline on real backfilled history and shows the result in the ward panel (Delhi beats the baseline by ~6%). Endpoint: `GET /api/forecast_accuracy`.
- **Upgraded LLM** — now uses Groq's `llama-3.3-70b-versatile` for higher-quality justifications and reports.
- **Bug fixes** — fixed an advisory-pipeline crash for newly-searched cities and a hardcoded language label in the advisories panel.


## Prerequisites

Before you start, ensure you have the following installed on your machine:
- **Node.js** (v18 or higher recommended) - [Download Node.js](https://nodejs.org/)
- **Python** (v3.9 or higher recommended) - [Download Python](https://www.python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/)

---

## 1. Setting up the Backend

The backend is a FastAPI application that serves the API and interacts with the AI models.

### Step 1.1: Navigate to the backend directory
Open your terminal and navigate to the backend folder:
```bash
cd backend
```

### Step 1.2: Create and activate a Virtual Environment
It's recommended to use a virtual environment to manage dependencies.

**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 1.3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 1.4: Environment Variables
Create a file named `.env` in the `backend` directory and configure the API keys. Add the following to `.env`:

```env
# REQUIRED — powers all AI text generation (enforcement justifications,
# multilingual advisories, anomaly investigation reports, and the Ask AI chat).
# Get a free key at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# OPTIONAL — lights up REAL NASA FIRMS satellite fire detections in Agent 6.
# Without it, Agent 6 still works and reports "no active fires detected".
# Get a free key at https://firms.modaps.eosdis.nasa.gov/api/area/
FIRMS_MAP_KEY=your_firms_map_key_here

# OPTIONAL — alternate LLM providers (not required if GROQ_API_KEY is set)
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# OPTIONAL — default is sqlite:///./vayudrishti.db
DATABASE_URL=sqlite:///./vayudrishti.db
```

**What needs a key vs. what doesn't:**
- **Needs `GROQ_API_KEY`:** enforcement justifications, advisory translations, anomaly reports, Ask AI chat. Without it these features error out (the app won't crash).
- **Needs nothing (pure math / free APIs):** source attribution %, AQI forecast, current AQI, anomaly z-scores, enforcement scoring, the map, and the forecast-accuracy (RMSE) metric.
- **`FIRMS_MAP_KEY` is optional** — only for real satellite fire dots.

The LLM uses Groq's `llama-3.3-70b-versatile` model by default.

### Step 1.5: Initialize the Database
Ensure the database is set up by running the Alembic migrations (if applicable) or the setup scripts provided:
```bash
python scripts/setup_agent4_mock.py
python scripts/setup_agent6_mock.py
```

### Step 1.6: Run the FastAPI Server
Start the backend server using Uvicorn:
```bash
uvicorn src.api.main:app --reload
```
The backend API will now be running at [http://localhost:8000](http://localhost:8000). You can view the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 2. Setting up the Frontend

The frontend is a React application powered by Vite. Open a **new terminal window** (keep the backend running in the first one).

### Step 2.1: Navigate to the frontend directory
```bash
cd frontend
```

### Step 2.2: Install dependencies
Install all the required Node modules:
```bash
npm install
```

### Step 2.3: Run the Development Server
Start the Vite development server:
```bash
npm run dev
```
The frontend application will now be running. The terminal will output the local URL, which is usually [http://localhost:5173](http://localhost:5173). 

---

## 3. Using the App
- Open your web browser and navigate to the frontend URL (e.g., `http://localhost:5173`).
- You should now be able to interact with the VayuDrishti Urban Air Quality Intelligence Platform.
- Any API calls made from the frontend will automatically route to your locally running backend server.
