import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .routes import router

# Create the FastAPI app instance
app = FastAPI(
    title="ReviewGuard AI API",
    description="Backend API for Fake Review Detection & Summarization System",
    version="1.0.0"
)

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local project evaluation
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Database tables on startup
@app.on_event("startup")
def startup_db_setup():
    try:
        # Create all tables defined in models.py
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized successfully.")
        
        # Schema migration: Add user_id column if it doesn't exist
        from sqlalchemy import text
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE analysis_history ADD COLUMN user_id INTEGER REFERENCES users(user_id)"))
                print("Schema migration: successfully added user_id column to analysis_history.")
        except Exception:
            # If the column already exists (or ALTER is not supported), ignore
            pass
    except Exception as e:
        print(f"Error initializing database tables: {e}")

# Include API endpoints under prefix /api
app.include_router(router, prefix="/api")

# Resolve frontend directory path
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Mount frontend directory as static files at root
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    print(f"Mounted frontend static files from: {FRONTEND_DIR}")
else:
    print(f"Warning: Frontend directory '{FRONTEND_DIR}' not found. Serving API only.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
