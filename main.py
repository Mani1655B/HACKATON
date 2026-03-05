from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import json
import logging
import os
from PIL import Image
import easyocr
import speech_recognition as sr
from io import BytesIO
import tempfile
import asyncio
from typing import List, Optional

from database import init_db, get_db, MessageLog, FraudReport
from models import MessageRequest, FraudAnalysisResponse, LogResponse, EntityDetected
from fraud_detector_v2 import FraudDetectionSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Fraud Risk Detection API",
    description="AI-Based Fraud Detection & Digital Awareness System for rural citizens",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and AI system
fraud_system = None

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Initialize database and AI models on startup"""
    global fraud_system
    
    logger.info("Starting Fraud Detection API...")
    init_db()
    logger.info("[OK] Database initialized")
    
    fraud_system = FraudDetectionSystem()
    logger.info("[OK] AI models loaded")
    logger.info("API ready to serve requests")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "message": "AI Fraud Risk Detection API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/api/analyze",
            "logs": "/api/logs",
            "stats": "/api/stats"
        }
    }


@app.post("/api/analyze", response_model=FraudAnalysisResponse)
async def analyze_message(
    request: MessageRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze message for fraud risk
    
    - **message**: SMS/WhatsApp message text to analyze
    
    Returns comprehensive fraud analysis with risk score and safety advice
    """
    try:
        logger.info(f"Received analysis request for message: {request.message[:50]}...")
        
        # Analyze message using AI system
        analysis = fraud_system.analyze_message(request.message)
        
        # Create response
        response = FraudAnalysisResponse(
            message=request.message,
            spam_score=analysis["spam_score"],
            fraud_type=analysis["fraud_type"],
            fraud_confidence=analysis["fraud_confidence"],
            risk_score=analysis["risk_score"],
            risk_level=analysis["risk_level"],
            entities_detected=[
                EntityDetected(**entity) for entity in analysis["entities_detected"]
            ],
            reasoning=analysis["reasoning"],
            safety_advice=analysis["safety_advice"],
            helpline="1930 (Cybercrime Helpline India)",
            timestamp=datetime.utcnow()
        )
        
        # Save to database (logs)
        log_entry = MessageLog(
            message=request.message,
            spam_score=analysis["spam_score"],
            fraud_type=analysis["fraud_type"],
            fraud_confidence=analysis["fraud_confidence"],
            risk_score=analysis["risk_score"],
            risk_level=analysis["risk_level"],
            entities_detected=json.dumps(analysis["entities_detected"])
        )
        db.add(log_entry)
        db.commit()
        
        logger.info(f"Analysis saved to database (ID: {log_entry.id})")
        
        return response
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs", response_model=list[LogResponse])
async def get_logs(
    limit: int = 50,
    risk_level: str = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve message analysis logs
    
    - **limit**: Maximum number of logs to return (default: 50)
    - **risk_level**: Filter by risk level (Safe/Suspicious/High Risk)
    """
    try:
        query = db.query(MessageLog)
        
        if risk_level:
            query = query.filter(MessageLog.risk_level == risk_level)
        
        logs = query.order_by(MessageLog.timestamp.desc()).limit(limit).all()
        
        logger.info(f"Retrieved {len(logs)} log entries")
        return logs
        
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Get fraud detection statistics"""
    try:
        total_messages = db.query(MessageLog).count()
        high_risk_count = db.query(MessageLog).filter(
            MessageLog.risk_level == "High Risk"
        ).count()
        suspicious_count = db.query(MessageLog).filter(
            MessageLog.risk_level == "Suspicious"
        ).count()
        safe_count = db.query(MessageLog).filter(
            MessageLog.risk_level == "Safe"
        ).count()
        
        # Fraud type distribution
        fraud_types = {}
        logs = db.query(MessageLog.fraud_type).all()
        for log in logs:
            fraud_type = log.fraud_type
            fraud_types[fraud_type] = fraud_types.get(fraud_type, 0) + 1
        
        stats = {
            "total_messages_analyzed": total_messages,
            "high_risk": high_risk_count,
            "suspicious": suspicious_count,
            "safe": safe_count,
            "fraud_type_distribution": fraud_types,
            "average_risk_score": round(
                db.query(MessageLog.risk_score).all() and 
                sum([r[0] for r in db.query(MessageLog.risk_score).all()]) / total_messages
                if total_messages > 0 else 0, 2
            )
        }
        
        logger.info(f"Statistics retrieved: {total_messages} total messages")
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze-image", response_model=FraudAnalysisResponse)
async def analyze_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Analyze fraud risk in images/screenshots.
    Extracts text using OCR and analyzes it for fraud indicators.
    
    Args:
        file: Image file (JPG, PNG, BMP, etc.)
        
    Returns:
        FraudAnalysisResponse with analysis results from extracted text
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image file
        contents = await file.read()
        image = Image.open(BytesIO(contents))
        
        # Convert PIL Image to numpy array for easyocr
        import numpy as np
        image_array = np.array(image)
        
        # Extract text using EasyOCR (first run downloads ~100MB model)
        logger.info(f"Analyzing image: {file.filename}")
        
        # Initialize OCR reader (first run downloads model, cached after)
        reader = easyocr.Reader(['en'], gpu=False)
        
        # Perform OCR on the image array
        results = reader.readtext(image_array)
        
        # Extract text from OCR results
        extracted_text = '\n'.join([text[1] for text in results]) if results else ""
        
        if not extracted_text.strip():
            extracted_text = "[No text detected in image]"
        
        logger.info(f"OCR extracted text: {extracted_text[:100]}...")
        
        # Analyze extracted text
        analysis = fraud_system.analyze_message(extracted_text)
        
        # Create proper response (matching FraudAnalysisResponse model)
        response = FraudAnalysisResponse(
            message=extracted_text,
            spam_score=analysis["spam_score"],
            fraud_type=analysis["fraud_type"],
            fraud_confidence=analysis["fraud_confidence"],
            risk_score=analysis["risk_score"],
            risk_level=analysis["risk_level"],
            entities_detected=[
                EntityDetected(**entity) for entity in analysis["entities_detected"]
            ],
            reasoning=analysis["reasoning"],
            safety_advice=analysis["safety_advice"],
            helpline="1930 (Cybercrime Helpline India)",
            timestamp=datetime.utcnow(),
            source='IMAGE_OCR',
            filename=file.filename
        )
        
        # Log to database
        log_entry = MessageLog(
            message=f"[IMAGE_OCR] {extracted_text[:500]}",  # Store first 500 chars of extracted text
            spam_score=analysis['spam_score'],
            fraud_type=analysis['fraud_type'],
            fraud_confidence=analysis['fraud_confidence'],
            risk_score=analysis['risk_score'],
            risk_level=analysis['risk_level'],
            entities_detected=json.dumps(analysis['entities_detected']),
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        
        return response
        
    except Exception as e:
        logger.error(f"Image analysis error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Image analysis failed: {str(e)}")



@app.post("/api/analyze-voice", response_model=FraudAnalysisResponse)
async def analyze_voice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Analyze fraud risk in voice messages.
    Converts speech-to-text and analyzes the transcription for fraud indicators.
    
    Args:
        file: Audio file (MP3, WAV, M4A, OGG, FLAC, etc. - all formats supported)
        
    Returns:
        FraudAnalysisResponse with analysis results from transcribed text
    """
    try:
        # Support all audio formats
        supported_formats = ['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac', 'wma', 'opus']
        file_ext = file.filename.split('.')[-1].lower()
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported format. Supported: {', '.join(supported_formats)}"
            )
        
        # Save to temporary file with original extension
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
            tmp_file.write(contents)
            tmp_path = tmp_file.name
        
        logger.info(f"[VOICE] Processing {file_ext.upper()}: {file.filename}")
        
        try:
            # Convert to WAV using moviepy (handles all formats with ffmpeg)
            wav_path = tmp_path.replace(f'.{file_ext}', '.wav')
            
            if file_ext != 'wav':
                logger.info(f"Converting {file_ext.upper()} to WAV...")
                from moviepy.editor import AudioFileClip
                
                try:
                    # Load audio with moviepy (uses ffmpeg)
                    audio_clip = AudioFileClip(tmp_path)
                    # Write as WAV
                    audio_clip.write_audiofile(wav_path, verbose=False, logger=None)
                    audio_clip.close()
                    logger.info(f"[VOICE] Conversion successful")
                    audio_file_path = wav_path
                except Exception as conv_error:
                    logger.error(f"Audio conversion error: {conv_error}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to convert {file_ext.upper()} to WAV. Error: {str(conv_error)}"
                    )
            else:
                audio_file_path = tmp_path
            
            # Initialize speech recognizer
            recognizer = sr.Recognizer()
            
            logger.info(f"[VOICE] Transcribing: {file.filename}")
            
            # Try with Google Speech Recognition
            try:
                with sr.AudioFile(audio_file_path) as source:
                    audio = recognizer.record(source)
                    transcribed_text = recognizer.recognize_google(audio)
                    logger.info(f"[VOICE] Transcribed: {transcribed_text[:100]}...")
            except sr.UnknownValueError:
                logger.warning("[VOICE] Could not understand audio")
                transcribed_text = "[Voice message - could not transcribe]"
            except sr.RequestError as e:
                logger.warning(f"[VOICE] Transcription request failed: {e}")
                transcribed_text = "[Voice message - transcription unavailable]"
            except Exception as e:
                logger.warning(f"[VOICE] Transcription error: {e}")
                transcribed_text = "[Voice message - transcription unavailable]"
            
            # Create proper response (matching FraudAnalysisResponse model)
            if not transcribed_text or transcribed_text.startswith('['):
                # If transcription failed, create response with safe values
                response = FraudAnalysisResponse(
                    message=transcribed_text,
                    spam_score=0.0,
                    fraud_type='Normal',
                    fraud_confidence=0.0,
                    risk_score=0.0,
                    risk_level='Safe',
                    entities_detected=[],
                    reasoning=['Voice message transcription failed. Manual review recommended.'],
                    safety_advice='Contact customer support for assistance with voice message analysis.',
                    helpline="1930 (Cybercrime Helpline India)",
                    timestamp=datetime.utcnow(),
                    source='VOICE_TRANSCRIPTION',
                    filename=file.filename
                )
            else:
                # Analyze transcribed text and create response
                analysis = fraud_system.analyze_message(transcribed_text)
                response = FraudAnalysisResponse(
                    message=transcribed_text,
                    spam_score=analysis["spam_score"],
                    fraud_type=analysis["fraud_type"],
                    fraud_confidence=analysis["fraud_confidence"],
                    risk_score=analysis["risk_score"],
                    risk_level=analysis["risk_level"],
                    entities_detected=[
                        EntityDetected(**entity) for entity in analysis["entities_detected"]
                    ],
                    reasoning=analysis["reasoning"],
                    safety_advice=analysis["safety_advice"],
                    helpline="1930 (Cybercrime Helpline India)",
                    timestamp=datetime.utcnow(),
                    source='VOICE_TRANSCRIPTION',
                    filename=file.filename
                )
            
            # Log to database
            log_entry = MessageLog(
                message=f"[VOICE_TRANSCRIPTION] {transcribed_text[:500]}",  # Store first 500 chars
                spam_score=response.spam_score,
                fraud_type=response.fraud_type,
                fraud_confidence=response.fraud_confidence,
                risk_score=response.risk_score,
                risk_level=response.risk_level,
                entities_detected=json.dumps([e.dict() for e in response.entities_detected]),
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            
            return response
            
        finally:
            # Clean up temporary files
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
        
    except Exception as e:
        logger.error(f"Voice analysis error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Voice analysis failed: {str(e)}")


@app.delete("/api/logs/clear")
async def clear_logs(db: Session = Depends(get_db)):
    """Clear all logs (use with caution)"""
    try:
        count = db.query(MessageLog).count()
        db.query(MessageLog).delete()
        db.commit()
        logger.warning(f"Cleared {count} log entries")
        return {"message": f"Cleared {count} log entries"}
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== REAL-TIME MOBILE FEATURES ====================

@app.post("/api/mobile/quick-check")
async def mobile_quick_check(request: MessageRequest, db: Session = Depends(get_db)):
    """
    Fast fraud check optimized for mobile apps.
    Returns simplified response with only essential information.
    
    Use this endpoint for real-time SMS scanning in mobile apps.
    """
    try:
        logger.info(f"[MOBILE] Quick check: {request.message[:30]}...")
        
        # Analyze message
        analysis = fraud_system.analyze_message(request.message)
        
        # Create simplified mobile response
        mobile_response = {
            "is_safe": analysis["risk_level"] == "Safe",
            "risk_level": analysis["risk_level"],
            "risk_score": round(analysis["risk_score"], 1),
            "fraud_type": analysis["fraud_type"],
            "alert_message": f"⚠️ {analysis['risk_level']}: {analysis['fraud_type']}" if analysis["risk_level"] != "Safe" else "✓ Message appears safe",
            "quick_advice": analysis["safety_advice"],
            "helpline": "1930"
        }
        
        # Log to database
        log_entry = MessageLog(
            message=f"[MOBILE] {request.message[:200]}",
            spam_score=analysis["spam_score"],
            fraud_type=analysis["fraud_type"],
            fraud_confidence=analysis["fraud_confidence"],
            risk_score=analysis["risk_score"],
            risk_level=analysis["risk_level"],
            entities_detected=json.dumps(analysis["entities_detected"]),
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        
        # Broadcast to WebSocket clients if high risk
        if analysis["risk_score"] >= 70:
            await manager.broadcast({
                "type": "high_risk_alert",
                "message": request.message[:100],
                "risk_score": analysis["risk_score"],
                "fraud_type": analysis["fraud_type"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return mobile_response
        
    except Exception as e:
        logger.error(f"Mobile quick check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """
    WebSocket endpoint for real-time fraud detection monitoring.
    
    Mobile apps and dashboards can connect to receive live updates
    when high-risk messages are detected.
    
    Example usage:
    - Connect: ws://localhost:8000/ws/monitor
    - Receive real-time alerts for risk_score >= 70
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Client can send ping to keep alive
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
            
            # Client can request current stats
            elif data == "stats":
                from sqlalchemy import func
                db = next(get_db())
                stats = {
                    "type": "stats",
                    "total_messages": db.query(MessageLog).count(),
                    "high_risk_today": db.query(MessageLog).filter(
                        MessageLog.risk_level == "High Risk",
                        func.date(MessageLog.timestamp) == datetime.utcnow().date()
                    ).count(),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_json(stats)
                db.close()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


@app.post("/api/mobile/batch-check")
async def mobile_batch_check(messages: List[str], db: Session = Depends(get_db)):
    """
    Batch analyze multiple messages at once.
    Useful for analyzing SMS inbox or message history.
    
    Request body: ["message1", "message2", "message3"]
    Returns: List of simplified fraud analysis results
    """
    try:
        logger.info(f"[MOBILE] Batch check: {len(messages)} messages")
        
        results = []
        high_risk_count = 0
        
        for msg in messages[:50]:  # Limit to 50 messages per batch
            analysis = fraud_system.analyze_message(msg)
            
            result = {
                "message": msg[:50] + "..." if len(msg) > 50 else msg,
                "risk_level": analysis["risk_level"],
                "risk_score": round(analysis["risk_score"], 1),
                "fraud_type": analysis["fraud_type"],
                "is_safe": analysis["risk_level"] == "Safe"
            }
            results.append(result)
            
            if analysis["risk_score"] >= 70:
                high_risk_count += 1
                
                # Log high-risk messages
                log_entry = MessageLog(
                    message=f"[BATCH] {msg[:200]}",
                    spam_score=analysis["spam_score"],
                    fraud_type=analysis["fraud_type"],
                    fraud_confidence=analysis["fraud_confidence"],
                    risk_score=analysis["risk_score"],
                    risk_level=analysis["risk_level"],
                    entities_detected=json.dumps(analysis["entities_detected"]),
                    timestamp=datetime.utcnow()
                )
                db.add(log_entry)
        
        db.commit()
        
        return {
            "total_analyzed": len(results),
            "high_risk_found": high_risk_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mobile/recent-alerts")
async def mobile_recent_alerts(limit: int = 10, db: Session = Depends(get_db)):
    """
    Get recent high-risk messages detected.
    Useful for mobile app notification center.
    """
    try:
        alerts = db.query(MessageLog).filter(
            MessageLog.risk_level == "High Risk"
        ).order_by(MessageLog.timestamp.desc()).limit(limit).all()
        
        return {
            "count": len(alerts),
            "alerts": [
                {
                    "id": alert.id,
                    "message": alert.message[:100] + "..." if len(alert.message) > 100 else alert.message,
                    "fraud_type": alert.fraud_type,
                    "risk_score": alert.risk_score,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Recent alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MESSAGE FORWARDING FEATURE ====================

@app.post("/api/forward/sms-webhook")
async def sms_forward_webhook(
    From: str = Form(None),
    Body: str = Form(None),
    MessageSid: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Twilio SMS Webhook - Receives forwarded SMS messages and sends analysis back.
    
    Setup Instructions:
    1. Sign up for Twilio (free trial: twilio.com/try-twilio)
    2. Get a phone number (e.g., +1-XXX-XXX-XXXX)
    3. Configure webhook URL: https://your-domain.com/api/forward/sms-webhook
    4. Users can forward suspicious SMS to your Twilio number
    5. This endpoint auto-analyzes and REPLIES with results via SMS
    
    Example user flow:
    - User receives: "You won 10 lakh! Click here..."
    - User forwards to: +1-XXX-XXX-XXXX (your Twilio number)
    - Gets instant SMS reply: "⚠️ HIGH RISK: Lottery Scam detected!"
    """
    try:
        sender_phone = From or "Unknown"
        message_text = Body or ""
        message_id = MessageSid or "N/A"
        
        logger.info(f"[SMS FORWARD] From {sender_phone} (ID: {message_id})")
        logger.info(f"[SMS CONTENT] {message_text[:100]}...")
        
        if not message_text or len(message_text.strip()) < 5:
            reply = (
                "Welcome to Fraud Detection Service!\n\n"
                "Forward any suspicious SMS to this number to get instant fraud analysis.\n\n"
                "Example: Forward lottery scam SMS and get risk assessment.\n\n"
                "📞 Helpline: 1930"
            )
        else:
            # Analyze forwarded message
            analysis = fraud_system.analyze_message(message_text)
            
            logger.info(f"[SMS ANALYSIS] Risk: {analysis['risk_level']} ({analysis['risk_score']:.1f}%)")
            
            # Create response message based on risk level
            if analysis["risk_level"] == "High Risk":
                reply = (
                    f"🚨 HIGH RISK DETECTED!\n\n"
                    f"Type: {analysis['fraud_type']}\n"
                    f"Risk: {analysis['risk_score']:.0f}%\n\n"
                    f"⚠️ {analysis['safety_advice'][:120]}\n\n"
                    f"📞 Report: 1930 (Cybercrime)"
                )
            elif analysis["risk_level"] == "Suspicious":
                reply = (
                    f"⚠️ SUSPICIOUS MESSAGE\n\n"
                    f"Type: {analysis['fraud_type']}\n"
                    f"Risk: {analysis['risk_score']:.0f}%\n\n"
                    f"Be cautious. Verify sender before taking action.\n\n"
                    f"📞 Report if fraud: 1930"
                )
            else:
                reply = (
                    f"✅ Appears SAFE\n\n"
                    f"Risk: {analysis['risk_score']:.0f}%\n\n"
                    f"Always verify sender identity before sharing personal info.\n\n"
                    f"📞 Help: 1930"
                )
            
            # Log forwarded message
            log_entry = MessageLog(
                message=f"[FORWARDED from {sender_phone}] {message_text[:200]}",
                spam_score=analysis["spam_score"],
                fraud_type=analysis["fraud_type"],
                fraud_confidence=analysis["fraud_confidence"],
                risk_score=analysis["risk_score"],
                risk_level=analysis["risk_level"],
                entities_detected=json.dumps(analysis["entities_detected"]),
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            
            logger.info(f"[SMS REPLY] Sending {len(reply)} chars to {sender_phone}")
        
        # Return TwiML response (Twilio's XML format for SMS replies)
        # This tells Twilio to send the reply SMS back to the user
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply[:1600]}</Message>
</Response>"""
        
        logger.info("[SMS WEBHOOK] TwiML response generated successfully")
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"SMS forward webhook error: {e}")
        error_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Error analyzing message. Please try again or call 1930 for help.</Message>
</Response>"""
        return Response(content=error_twiml, media_type="application/xml")


@app.post("/api/forward/email-webhook")
async def email_forward_webhook(
    sender: str = None,
    subject: str = None,
    body: str = None,
    db: Session = Depends(get_db)
):
    """
    Email Webhook - Receives forwarded messages via email.
    
    Setup Instructions:
    1. Use services like SendGrid, Mailgun, or AWS SES
    2. Create email: fraud-check@yourdomain.com
    3. Configure inbound webhook to this endpoint
    4. Users forward suspicious messages to that email
    5. System sends analysis via reply email
    
    Example user flow:
    - User receives suspicious email/SMS
    - Forwards to: fraud-check@yourdomain.com
    - Receives analysis email within seconds
    """
    try:
        message_text = body or subject or ""
        sender_email = sender or "Unknown"
        
        logger.info(f"[EMAIL FORWARD] From {sender_email}: {message_text[:50]}...")
        
        if not message_text:
            return {
                "status": "error",
                "message": "No content received"
            }
        
        # Analyze message
        analysis = fraud_system.analyze_message(message_text)
        
        # Log forwarded email
        log_entry = MessageLog(
            message=f"[EMAIL from {sender_email}] {message_text[:200]}",
            spam_score=analysis["spam_score"],
            fraud_type=analysis["fraud_type"],
            fraud_confidence=analysis["fraud_confidence"],
            risk_score=analysis["risk_score"],
            risk_level=analysis["risk_level"],
            entities_detected=json.dumps(analysis["entities_detected"]),
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        
        # Return analysis (email service will format and send)
        return {
            "status": "success",
            "analysis": {
                "risk_level": analysis["risk_level"],
                "risk_score": analysis["risk_score"],
                "fraud_type": analysis["fraud_type"],
                "safety_advice": analysis["safety_advice"],
                "helpline": "1930"
            },
            "reply_to": sender_email,
            "subject": f"Fraud Analysis: {analysis['risk_level']}",
            "body": (
                f"Fraud Risk Analysis Result\n"
                f"{'='*40}\n\n"
                f"Risk Level: {analysis['risk_level']}\n"
                f"Risk Score: {analysis['risk_score']:.1f}%\n"
                f"Fraud Type: {analysis['fraud_type']}\n\n"
                f"Safety Advice:\n{analysis['safety_advice']}\n\n"
                f"Detected Elements:\n"
                + "\n".join([f"- {e['entity']} ({e['type']})" for e in analysis['entities_detected'][:5]])
                + f"\n\n📞 Report fraud: 1930 (Cybercrime Helpline India)"
            )
        }
        
    except Exception as e:
        logger.error(f"Email forward webhook error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/forward/info")
async def forwarding_info():
    """
    Get information about message forwarding service.
    Shows users how to forward suspicious messages for analysis.
    
    Using Fast2SMS - Indian SMS provider with +91 numbers
    No international charges, works with JIO/Airtel/Idea
    """
    return {
        "service": "Fraud Detection SMS Forwarding (Fast2SMS)",
        "description": "Forward suspicious SMS to get instant fraud analysis",
        "provider": "Fast2SMS (Indian SMS Provider)",
        "number_type": "+91 Indian Number (Local SMS, no international charges)",
        "supported_carriers": ["JIO", "Airtel", "Idea", "Vi", "BSNL"],
        "cost": "Local SMS rates only - no international charges",
        "setup": {
            "step_1": "Create Fast2SMS account at fast2sms.com",
            "step_2": "Get your Fast2SMS API key",
            "step_3": "Configure webhook: https://yourdomain.com/api/forward/sms-webhook",
            "step_4": "Share your +91 number with users",
            "step_5": "Users text suspicious messages to the +91 number"
        },
        "features": [
            "Instant fraud analysis within 5-10 seconds",
            "Local Indian SMS (no international charges)",
            "Works with all Indian carriers",
            "SMS reply with risk assessment",
            "Automatic logging to database"
        ],
        "response_format": {
            "high_risk": "HIGH RISK! Type: [Fraud Type], Risk: [%], Safety Tips: [Advice], Report: 1930",
            "suspicious": "SUSPICIOUS! Type: [Fraud Type], Risk: [%], Verify sender before action, Report: 1930",
            "safe": "SAFE! Risk: [%], Always verify sender identity, Helpline: 1930"
        },
        "example_user_flow": {
            "step_1": "User receives: 'Congratulations! Won Rs 10 lakh...'",
            "step_2": "User forwards to your +91 SMS number",
            "step_3": "System analyzes within 5 seconds",
            "step_4": "User gets back: 'HIGH RISK! Lottery Scam, Risk: 95%, Report: 1930'"
        },
        "helpline": "1930 (Cybercrime Helpline India)",
        "endpoint": "/api/forward/sms-webhook"
    }


@app.post("/api/reports/submit-fraud")
async def submit_fraud_report(
    fraudType: str = Form(...),
    description: str = Form(...),
    urgency: str = Form(...),
    anonymous: str = Form(default="true"),
    fullName: str = Form(default=None),
    contact: str = Form(default=None),
    evidence: UploadFile = File(default=None),
    db: Session = Depends(get_db)
):
    """
    Submit fraud report from user feedback form.
    
    Request (Form Data):
    - fraudType: Type of fraud (e.g., "Online Shopping Fraud", "Lottery", etc.)
    - description: Detailed description of fraud
    - urgency: Low, Medium, High, Critical
    - anonymous: "true" or "false" (string)
    - fullName: User's name (if not anonymous)
    - contact: Phone/Email (if not anonymous)
    - evidence: Optional file upload (image/screenshot)
    
    Returns: Confirmation with report ID
    """
    try:
        # Convert anonymous string to boolean
        is_anonymous_bool = anonymous.lower() in ['true', '1', 'yes']
        
        # Handle file upload if provided
        evidence_url = None
        if evidence and evidence.filename:
            file_path = f"evidence/{evidence.filename}"
            os.makedirs("evidence", exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(await evidence.read())
            evidence_url = file_path
            logger.info(f"[REPORT] Evidence file saved: {file_path}")
        
        # Validate inputs
        if len(description.strip()) < 10:
            raise HTTPException(status_code=400, detail="Description must be at least 10 characters")
        
        if not is_anonymous_bool and not fullName:
            raise HTTPException(status_code=400, detail="Name required for non-anonymous reports")
        
        # Create fraud report
        report = FraudReport(
            fraud_category=fraudType,
            description=description,
            evidence_url=evidence_url,
            urgency=urgency,
            reporter_name=fullName if not is_anonymous_bool else None,
            reporter_contact=contact if not is_anonymous_bool else None,
            is_anonymous=1 if is_anonymous_bool else 0,
            status="pending"
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        logger.info(f"[FRAUD REPORT] Submitted - ID: {report.id}, Category: {fraudType}, Anonymous: {is_anonymous_bool}")
        
        return {
            "status": "success",
            "report_id": report.id,
            "message": "Thank you! Your report has been submitted. Our team will review it within 24-48 hours.",
            "reference_number": f"FR-{report.id:06d}",
            "helpline": "1930"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fraud report submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/status/{report_id}")
async def get_report_status(report_id: int, db: Session = Depends(get_db)):
    """Check status of submitted fraud report"""
    try:
        report = db.query(FraudReport).filter(FraudReport.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {
            "report_id": report.id,
            "status": report.status,
            "fraud_category": report.fraud_category,
            "submitted_at": report.timestamp,
            "urgency": report.urgency
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/stats")
async def reports_stats(db: Session = Depends(get_db)):
    """Get fraud report statistics"""
    try:
        total_reports = db.query(FraudReport).count()
        pending = db.query(FraudReport).filter(FraudReport.status == "pending").count()
        verified = db.query(FraudReport).filter(FraudReport.status == "verified").count()
        
        # Count by category
        categories = db.query(FraudReport.fraud_category, func.count().label("count")).group_by(FraudReport.fraud_category).all()
        
        return {
            "total_reports": total_reports,
            "pending": pending,
            "verified": verified,
            "by_category": [{"category": cat[0], "count": cat[1]} for cat in categories],
            "helpline": "1930"
        }
        
    except Exception as e:
        logger.error(f"Error fetching report stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
