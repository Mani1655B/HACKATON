from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MessageRequest(BaseModel):
    """Request model for message analysis"""
    message: str


class EntityDetected(BaseModel):
    """Detected entity (URL, phone, organization, etc.)"""
    entity: str
    type: str
    confidence: float


class FraudAnalysisResponse(BaseModel):
    """Complete fraud analysis response"""
    message: str
    spam_score: float
    fraud_type: str
    fraud_confidence: float
    risk_score: float
    risk_level: str
    entities_detected: List[EntityDetected]
    reasoning: List[str]
    safety_advice: str
    helpline: str
    timestamp: datetime
    source: Optional[str] = "TEXT"  # TEXT, IMAGE_OCR, or VOICE_TRANSCRIPTION
    filename: Optional[str] = None  # Original filename for image/voice


class LogResponse(BaseModel):
    """Log entry response"""
    id: int
    message: str
    spam_score: float
    fraud_type: str
    risk_score: float
    risk_level: str
    timestamp: datetime

    class Config:
        from_attributes = True
