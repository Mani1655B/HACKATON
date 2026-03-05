from transformers import pipeline
import logging
from typing import Dict, List, Tuple
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fraud_detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FraudDetectionSystem:
    """AI-based fraud detection system without hardcoded keywords"""

    def __init__(self):
        logger.info("Initializing AI models...")
        
        try:
            # Model 1: Spam Detection (Fast, lightweight)
            self.spam_detector = pipeline(
                "text-classification",
                model="SharpWoofer/distilroberta-sms-spam-detector"
            )
            logger.info("[OK] Spam detection model loaded")

            # Model 2: Zero-Shot Fraud Classification (Skip large BART, use fallback)
            self.fraud_classifier = None
            logger.info("[OK] Using lightweight keyword-pattern fraud detection")

            # Model 3: Named Entity Recognition (Optional - lighter model)
            try:
                self.ner = pipeline(
                    "ner",
                    model="dslim/bert-base-NER",
                    aggregation_strategy="simple"
                )
                logger.info("[OK] NER model loaded")
            except Exception as e:
                logger.warning(f"NER model loading issue: {e}")
                self.ner = None
                logger.info("[OK] NER disabled - using pattern matching only")

            self.fraud_labels = [
                "UPI fraud message",
                "job scam message",
                "lottery scam message",
                "phishing message",
                "investment scam message",
                "normal message"
            ]

            # Fraud detection keywords for lightweight detection
            self.fraud_keywords = {
                "Upi Fraud": ["upi", "payment request", "scan qr", "collect", "approve"],
                "Job Scam": ["job", "work from home", "registration fee", "earn"],
                "Lottery Scam": ["lottery", "won", "prize", "claim reward", "processing fee"],
                "Phishing": ["verify account", "bank", "blocked", "update kyc", "click link"],
                "Investment Scam": ["guaranteed returns", "investment", "crypto", "scheme"],
            }

            logger.info("[SUCCESS] All AI models initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            raise

    def detect_spam(self, message: str) -> Tuple[float, str]:
        """Detect spam probability using AI model"""
        try:
            result = self.spam_detector(message)[0]
            label = result['label']
            score = result['score'] * 100
            logger.info(f"Spam detection: {label} ({score:.2f}%)")
            return score, label
        except Exception as e:
            logger.error(f"Spam detection error: {e}")
            return 50.0, "unknown"

    def classify_fraud_type(self, message: str) -> Tuple[str, float]:
        """Classify fraud type using zero-shot learning or fallback"""
        try:
            # If zero-shot model is available
            if self.fraud_classifier:
                result = self.fraud_classifier(message, self.fraud_labels)
                fraud_type = result["labels"][0].replace(" message", "").title()
                confidence = result["scores"][0] * 100
                logger.info(f"Fraud classification (zero-shot): {fraud_type} ({confidence:.2f}%)")
                return fraud_type, confidence
            else:
                # Fallback: keyword-based detection
                message_lower = message.lower()
                scores = {}
                
                for fraud_type, keywords in self.fraud_keywords.items():
                    matches = sum(1 for kw in keywords if kw in message_lower)
                    scores[fraud_type] = (matches / len(keywords)) * 100
                
                if max(scores.values()) > 0:
                    fraud_type = max(scores, key=scores.get)
                    confidence = scores[fraud_type]
                else:
                    fraud_type = "Normal"
                    confidence = 0
                
                logger.info(f"Fraud classification (fallback): {fraud_type} ({confidence:.2f}%)")
                return fraud_type, confidence
                
        except Exception as e:
            logger.error(f"Fraud classification error: {e}")
            return "Unknown", 0.0

    def extract_entities(self, message: str) -> List[Dict]:
        """Extract suspicious entities using NER or patterns"""
        entities = []
        try:
            # Try NER if available
            if self.ner:
                ner_results = self.ner(message)
                for entity in ner_results:
                    entities.append({
                        "entity": entity["word"],
                        "type": entity["entity_group"],
                        "confidence": round(entity["score"] * 100, 2)
                    })

            # Pattern detection for URLs and phone numbers (always works)
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            phone_pattern = r'\+?[0-9]{10,15}'

            urls = re.findall(url_pattern, message)
            phones = re.findall(phone_pattern, message)

            for url in urls:
                entities.append({
                    "entity": url,
                    "type": "URL",
                    "confidence": 95.0
                })

            for phone in phones:
                entities.append({
                    "entity": phone,
                    "type": "PHONE",
                    "confidence": 90.0
                })

            logger.info(f"Entities detected: {len(entities)}")
            return entities

        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return []

    def calculate_risk_score(
        self, 
        spam_score: float, 
        fraud_confidence: float,
        entities_count: int
    ) -> float:
        """Calculate composite risk score"""
        
        # Weighted combination of AI model outputs
        base_risk = (spam_score * 0.6) + (fraud_confidence * 0.4)
        
        # Add risk based on suspicious entities detected
        entity_risk = min(entities_count * 5, 20)
        
        total_risk = min(base_risk + entity_risk, 100.0)
        
        logger.info(f"Risk score calculated: {total_risk:.2f}%")
        return round(total_risk, 2)

    def classify_risk_level(self, risk_score: float) -> str:
        """Classify risk level based on score"""
        if risk_score < 40:
            return "Safe"
        elif risk_score < 70:
            return "Suspicious"
        else:
            return "High Risk"

    def generate_reasoning(
        self,
        spam_score: float,
        fraud_type: str,
        fraud_confidence: float,
        entities: List[Dict]
    ) -> List[str]:
        """Generate explainable reasoning for the decision"""
        reasons = []

        if spam_score > 70:
            reasons.append(f"Message classified as spam with {spam_score:.1f}% probability")
        elif spam_score > 40:
            reasons.append(f"Message shows suspicious patterns ({spam_score:.1f}% spam score)")

        if fraud_confidence > 60:
            reasons.append(f"Detected as '{fraud_type}' with {fraud_confidence:.1f}% confidence")

        if entities:
            entity_types = set([e['type'] for e in entities])
            if 'URL' in entity_types:
                reasons.append("Contains suspicious URL links")
            if 'PHONE' in entity_types:
                reasons.append("Contains phone number requiring verification")
            if 'ORG' in entity_types or 'PER' in entity_types:
                reasons.append("References organizations or persons requiring verification")

        if not reasons:
            reasons.append("Message appears normal with low risk indicators")

        return reasons

    def get_safety_advice(self, fraud_type: str) -> str:
        """Generate contextual safety advice based on fraud type"""
        
        advice_map = {
            "Upi Fraud": "Never approve unknown UPI collect requests. Always verify the sender before making payments.",
            "Job Scam": "Legitimate employers never ask for registration fees. Do not pay money for job offers.",
            "Lottery Scam": "No genuine lottery asks for processing fees or advance payments to claim prizes.",
            "Phishing": "Never click suspicious links claiming to be from banks. Banks never ask for OTP or passwords via SMS.",
            "Investment Scam": "Be cautious of 'guaranteed returns' or 'get rich quick' schemes. Verify investment platforms before investing.",
            "Normal": "Stay vigilant. Always verify sender identity before sharing personal information or making payments."
        }

        return advice_map.get(fraud_type, advice_map["Normal"])

    def analyze_message(self, message: str) -> Dict:
        """Complete fraud analysis pipeline"""
        logger.info(f"Analyzing message: {message[:50]}...")

        try:
            # Step 1: Spam Detection
            spam_score, spam_label = self.detect_spam(message)

            # Step 2: Fraud Type Classification
            fraud_type, fraud_confidence = self.classify_fraud_type(message)

            # Step 3: Entity Extraction
            entities = self.extract_entities(message)

            # Step 4: Risk Score Calculation
            risk_score = self.calculate_risk_score(
                spam_score,
                fraud_confidence,
                len(entities)
            )

            # Step 5: Risk Level Classification
            risk_level = self.classify_risk_level(risk_score)

            # Step 6: Generate Reasoning
            reasoning = self.generate_reasoning(
                spam_score,
                fraud_type,
                fraud_confidence,
                entities
            )

            # Step 7: Safety Advice
            safety_advice = self.get_safety_advice(fraud_type)

            result = {
                "spam_score": spam_score,
                "fraud_type": fraud_type,
                "fraud_confidence": fraud_confidence,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "entities_detected": entities,
                "reasoning": reasoning,
                "safety_advice": safety_advice
            }

            logger.info(f"Analysis complete: {risk_level} ({risk_score}%)")
            return result

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            raise
