import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Common credentials for local MySQL development to auto-detect the configuration
CREDENTIAL_TEMPLATES = [
    "mysql+pymysql://root:admin123@localhost",
    "mysql+pymysql://root:root@localhost",
    "mysql+pymysql://root:@localhost",
]

DB_NAME = "reviewguard_db"
engine = None
SessionLocal = None

# Attempt to connect to the MySQL server and create the database if it doesn't exist
last_err = None
for base_url in CREDENTIAL_TEMPLATES:
    try:
        # Connect to MySQL server without specifying the database first
        temp_engine = create_engine(base_url, connect_args={"connect_timeout": 5})
        with temp_engine.connect() as conn:
            # Commit is required outside transition block to run DDL in some configurations
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
            conn.execute(text("COMMIT"))
        
        # Now create the actual engine with the database specified
        db_url = f"{base_url}/{DB_NAME}"
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        print(f"Successfully connected to MySQL using connection: {base_url}/{DB_NAME}")
        break
    except Exception as e:
        last_err = e
        continue

# If MySQL connection fails, fallback to SQLite to keep the app working
if engine is None:
    print(f"Warning: Failed to connect to MySQL ({last_err}). Falling back to SQLite for local development.")
    SQLITE_URL = "sqlite:///./reviewguard_db.db"
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
