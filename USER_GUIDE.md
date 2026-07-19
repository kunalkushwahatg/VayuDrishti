# VayuDrishti - User Guide

This guide will help you set up and run the VayuDrishti application locally. The project is split into a **Python FastAPI backend** and a **React Vite frontend**.

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
Create a file named `.env` in the `backend` directory and configure the required API keys. Add the following to `.env`:

```env
# Optional but recommended for LLM integrations
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Default is sqlite:///./vayudrishti.db
DATABASE_URL=sqlite:///./vayudrishti.db
```

*(Note: If you don't have these keys, the app might use dummy keys, but some AI features might not work properly).*

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
