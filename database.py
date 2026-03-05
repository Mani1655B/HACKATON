from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./fraud_detection.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MessageLog(Base):
    """SQLite table to store all message analysis logs"""
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    spam_score = Column(Float, nullable=False)
    fraud_type = Column(String, nullable=False)
    fraud_confidence = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    entities_detected = Column(Text)  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)


class FraudReport(Base):
    """SQLite table to store user fraud reports"""
    __tablename__ = "fraud_reports"

    id = Column(Integer, primary_key=True, index=True)
    fraud_category = Column(String, nullable=False)  # UPI, Job, Lottery, Phishing, Investment
    description = Column(Text, nullable=False)
    evidence_url = Column(String, nullable=True)  # File path or URL
    urgency = Column(String, nullable=False)  # Low, Medium, High, Critical
    reporter_name = Column(String, nullable=True)  # Null if anonymous
    reporter_contact = Column(String, nullable=True)  # Phone/Email, null if anonymous
    is_anonymous = Column(Integer, default=1)  # 1 = anonymous, 0 = with details
    status = Column(String, default="pending")  # pending, reviewing, verified, resolved
    timestamp = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
