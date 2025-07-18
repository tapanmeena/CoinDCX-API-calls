from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import databases
from app.core.config import get_settings

settings = get_settings()

# Database URL
DATABASE_URL = settings.DATABASE_URL

# Create sync engine for database creation
engine = create_engine(DATABASE_URL, echo=settings.DEBUG)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create database instance for async queries
database = databases.Database(DATABASE_URL)

# Create declarative base
Base = declarative_base()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_database():
    """Dependency to get database connection"""
    return database

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session():
    """Get database session for direct usage"""
    return SessionLocal()
