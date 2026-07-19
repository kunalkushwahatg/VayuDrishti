from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

app = FastAPI(
    title="VayuDrishti API",
    description="API for the VayuDrishti Urban Air Quality Intelligence Platform",
    version="1.0.0"
)

# Allow CORS for the frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the endpoints
app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Welcome to the VayuDrishti API. Go to /docs for the swagger documentation."}
