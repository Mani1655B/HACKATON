from transformers import pipeline
import logging
from typing import Dict, List, Tuple
import re
import requests
from urllib.parse import urlparse

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
    """AI-based fraud detection system - Lightweight version"""

    def __init__(self):
        logger.info("Initializing AI models...")
        
        try:
            # Model 1: Spam Detection (Fast, lightweight)
            self.spam_detector = pipeline(
                "text-classification",
                model="SharpWoofer/distilroberta-sms-spam-detector"
            )
            logger.info("[OK] Spam detection model loaded")

            # Skip large BART model - use keyword patterns
            self.fraud_classifier = None

            # Skip NER - use pattern matching only
            self.ner = None

            self.fraud_labels = [
                "UPI fraud message",
                "job scam message",
                "lottery scam message",
                "phishing message",
                "investment scam message",
                "normal message"
            ]

            # Comprehensive fraud detection keywords
            self.fraud_keywords = {
                "Upi Fraud": [
                    "upi", "payment", "transfer", "scan", "collect", "approve", "request",
                    "gpay", "paytm", "phonepe", "bhim", "qr code", "rupee", "withdraw",
                    "confirm transaction", "verify payment", "authorize", "release amount"
                ],
                "Job Scam": [
                    "job", "work", "home", "registration", "fee", "earn", "hiring", "applicant",
                    "interview", "offer", "position", "vacancy", "salary", "part-time", "full-time",
                    "commission", "bonus", "training", "placement", "appointment letter", "submit documents"
                ],
                "Lottery Scam": [
                    "lottery", "won", "prize", "claim", "congratulations", "reward", "win",
                    "draw", "lucky", "selected", "claim prize", "process", "tax", "fee",
                    "scratch card", "raffle", "fortune", "bonus", "jackpot", "advance payment"
                ],
                "Phishing": [
                    "verify", "password", "click", "secure", "confirm", "update", "account",
                    "email", "bank", "urgent", "expires", "lockout", "suspended", "blocked",
                    "instgram", "facebook", "whatsapp", "link", "login", "credentials",
                    "card number", "cvv", "otp", "pin", "confirm identity", "re-verify",
                    "unusual activity", "suspicious", "action required", "immediately"
                ],
                "Investment Scam": [
                    "investment", "crypto", "profit", "bitcoin", "forex", "guaranteed", "returns",
                    "share market", "stock", "mutual fund", "trading", "multiply money", "double",
                    "high return", "risk free", "fast money", "passive income", "deposit"
                ],
            }

            logger.info("[SUCCESS] All models initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            raise

    def check_url_safety(self, url: str) -> Tuple[bool, str]:
        """Check URL against threat intelligence APIs"""
        try:
            # Extract domain from URL
            parsed = urlparse(url if url.startswith('http') else f'http://{url}')
            domain = parsed.netloc or parsed.path
            
            # API 1: Check against URLhaus (phishing/malware database)
            try:
                urlhaus_response = requests.post(
                    'https://urlhaus-api.abuse.ch/v1/url/',
                    data={'url': url},
                    timeout=3
                )
                if urlhaus_response.status_code == 200:
                    result = urlhaus_response.json()
                    if result.get('query_status') == 'ok' and result.get('url_status') == 'blacklisted':
                        logger.warning(f"URL flagged as malicious by URLhaus: {url}")
                        return True, "Malicious URL (URLhaus)"
            except Exception as e:
                logger.debug(f"URLhaus check failed: {e}")
            
            # API 2: Check against PhishTank (phishing URLs)
            try:
                phishtank_response = requests.get(
                    f'https://phishapi.com/api/info?url={url}&format=json&app_key=free',
                    timeout=3
                )
                if phishtank_response.status_code == 200:
                    result = phishtank_response.json()
                    if result.get('phishing') == '1':
                        logger.warning(f"URL flagged as phishing by PhishTank: {url}")
                        return True, "Phishing URL (PhishTank)"
            except Exception as e:
                logger.debug(f"PhishTank check failed: {e}")
            
            # API 3: Basic malware check with abuse.ch
            try:
                response = requests.get(
                    f'https://sslbl.abuse.ch/api/v1/?lookup=host&host={domain}',
                    timeout=3
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get('query_status') == 'ok' and result.get('abuse_confidence_score', 0) > 50:
                        logger.warning(f"Domain flagged suspicious: {domain}")
                        return True, f"Suspicious domain (abuse.ch score: {result.get('abuse_confidence_score')})"
            except Exception as e:
                logger.debug(f"abuse.ch check failed: {e}")
            
            return False, "URL appears safe"
            
        except Exception as e:
            logger.error(f"URL safety check error: {e}")
            return False, "Unable to verify"

    def validate_phone_number(self, phone: str) -> Tuple[bool, str]:
        """Validate phone number patterns for scams"""
        try:
            # Remove non-digits
            digits = re.sub(r'\D', '', phone)
            
            # Indian phone numbers are typically 10 digits
            if len(digits) == 10:
                # Check if it's a known scam pattern
                # Suspicious: starting with 0, repeated digits, etc.
                if digits.startswith('0'):
                    return True, "Suspicious pattern: starts with 0"
                if len(set(digits)) == 1:
                    return True, "Suspicious pattern: all digits same"
                return False, "Valid phone format"
            elif len(digits) > 10:
                return True, "Suspicious: too many digits"
            else:
                return True, "Suspicious: too few digits"
                
        except Exception as e:
            logger.debug(f"Phone validation error: {e}")
            return False, "Unable to validate"

    def detect_spam(self, message: str) -> Tuple[float, str]:
        """Detect spam probability using AI model with smart calibration"""
        try:
            # Get raw model prediction
            result = self.spam_detector(message)[0]
            label = result['label']
            raw_score = result['score'] * 100
            
            # Smart calibration: Adjust based on message characteristics
            adjusted_score = raw_score
            
            # Check if message has conversational patterns (safe indicators)
            safe_patterns = [
                r'\bhow\s+are\s+you\b',
                r'\bhello\b',
                r'\bhi\b',
                r'\bthanks\b',
                r'\bplease\b',
                r'\bwhen\b',
                r'\bwhere\b',
                r'\bwhat\b',
                r'\bwhy\b',
                r'\bwhat\'s\b',
                r'\byou\s+ok\b'
            ]
            
            message_lower = message.lower()
            has_safe_pattern = any(re.search(pattern, message_lower) for pattern in safe_patterns)
            
            # Check for fraud keywords (danger indicators)
            fraud_patterns = [
                r'\blottery\b',
                r'\bwon\b',
                r'\bclick\b',
                r'\bupi\b',
                r'\bpayment\b',
                r'\bverify\b',
                r'\bbank\b',
                r'\bblocked\b',
                r'\burge\b',
                r'\bwork\s+from\s+home\b',
                r'\bresistration\s+fee\b',
                r'http[s]?://'
            ]
            
            has_fraud_keyword = any(re.search(pattern, message_lower) for pattern in fraud_patterns)
            
            # Calibration logic
            if has_safe_pattern and not has_fraud_keyword:
                # Clear conversational message = reduce spam score significantly
                adjusted_score = max(raw_score * 0.2, 5)  # Min 5%, max 20% of original
            elif has_fraud_keyword:
                # Has fraud keywords = boost spam score
                adjusted_score = min(raw_score * 1.2, 100)  # Boost by 20%
            else:
                # Normal case - slight reduction for very high scores
                if raw_score > 95:
                    adjusted_score = raw_score * 0.8  # Reduce extreme confidence
            
            logger.info(f"Spam detection: {label} (raw: {raw_score:.2f}% -> adjusted: {adjusted_score:.2f}%)")
            return adjusted_score, label
            
        except Exception as e:
            logger.error(f"Spam detection error: {e}")
            return 50.0, "unknown"

    def classify_fraud_type(self, message: str) -> Tuple[str, float]:
        """Classify fraud type using intelligent keyword pattern matching"""
        try:
            message_lower = message.lower()
            scores = {}
            
            for fraud_type, keywords in self.fraud_keywords.items():
                matches = 0
                for keyword in keywords:
                    # Check if keyword appears in message
                    if keyword in message_lower:
                        matches += 1
                
                # Calculate confidence: percentage of keywords matched
                confidence = (matches / len(keywords)) * 100 if keywords else 0
                scores[fraud_type] = confidence
            
            # Get the fraud type with highest score
            if scores:
                fraud_type = max(scores, key=scores.get)
                confidence = scores[fraud_type]
                
                # Only consider it a fraud if confidence >= 15% (lower threshold)
                # Exception: Phishing needs 10% since it has many keywords
                min_threshold = 10 if fraud_type == "Phishing" else 15
                
                if confidence < min_threshold:
                    fraud_type = "Normal"
                    confidence = 0
            else:
                fraud_type = "Normal"
                confidence = 0
            
            logger.info(f"Fraud classification: {fraud_type} ({confidence:.2f}%)")
            return fraud_type, confidence
                
        except Exception as e:
            logger.error(f"Fraud classification error: {e}")
            return "Unknown", 0.0

    def extract_entities(self, message: str) -> List[Dict]:
        """Extract suspicious entities using pattern matching"""
        entities = []
        try:
            # Pattern 1: URLs (with http/https)
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, message)
            for url in urls:
                # Check URL safety against threat intelligence
                is_malicious, reason = self.check_url_safety(url)
                entities.append({
                    "entity": url,
                    "type": "URL_MALICIOUS" if is_malicious else "URL",
                    "confidence": 95.0 if is_malicious else 85.0
                })

            # Pattern 1b: Domain URLs (without http, like example.com/path)
            domain_pattern = r'(?:www\.)?[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+(?:/[^\s]*)?'
            domains = re.findall(domain_pattern, message)
            for domain in domains:
                if '.' in domain and len(domain) > 5 and not domain.endswith(('.com)', '.me)', '.in)')):
                    if not any(e["entity"] == domain for e in entities):
                        # Check domain safety
                        is_malicious, reason = self.check_url_safety(domain)
                        entities.append({
                            "entity": domain,
                            "type": "URL_MALICIOUS" if is_malicious else "URL",
                            "confidence": 90.0 if is_malicious else 75.0
                        })

            # Pattern 2: Phone numbers (10+ digits)
            phone_pattern = r'\+?[0-9]{10,15}'
            phones = re.findall(phone_pattern, message)
            for phone in phones:
                if not any(e["entity"] == phone for e in entities):
                    # Validate phone number
                    is_suspicious, reason = self.validate_phone_number(phone)
                    entities.append({
                        "entity": phone,
                        "type": "PHONE_SUSPICIOUS" if is_suspicious else "PHONE",
                        "confidence": 85.0 if is_suspicious else 70.0
                    })

            # Pattern 3: Money amounts (Rs/rupees or currency symbols)
            money_pattern = r'(?:Rs\.?\s*|rupees?\s+)?(\d+(?:[,\.]\d+)*)'
            money_matches = re.findall(money_pattern, message, re.IGNORECASE)
            for amount in money_matches:
                if len(amount) > 2:
                    entity_text = f"Rs {amount}"
                    if not any(e["entity"] == entity_text for e in entities):
                        entities.append({
                            "entity": entity_text,
                            "type": "MONEY",
                            "confidence": 85.0
                        })

            # Pattern 4: Suspicious keywords as entities
            suspicious_keywords = {
                "prize": "REWARD",
                "claim": "ACTION",
                "urgent": "URGENCY",
                "click": "ACTION",
                "verify": "ACTION",
                "confirm": "ACTION",
                "approve": "ACTION",
                "won": "REWARD",
                "lottery": "SCAM_TYPE",
                "payment": "FINANCIAL",
                "transfer": "FINANCIAL",
                "account": "ACCOUNT",
                "secure": "ACTION",
                "update": "ACTION"
            }
            
            message_lower = message.lower()
            for keyword, entity_type in suspicious_keywords.items():
                if keyword in message_lower:
                    for match in re.finditer(r'\b' + keyword + r'\b', message_lower):
                        start = match.start()
                        end = match.end()
                        entity_word = message[start:end]
                        if not any(e["entity"].lower() == entity_word.lower() for e in entities):
                            entities.append({
                                "entity": entity_word,
                                "type": entity_type,
                                "confidence": 75.0
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
        """Calculate composite risk score with better calibration"""
        
        # If fraud confidence is 0 and no entities, it's likely safe despite spam score
        if fraud_confidence == 0 and entities_count == 0:
            # Only 30% weight to spam score when no fraud indicators
            base_risk = spam_score * 0.3
        else:
            # Normal weighting when fraud indicators present
            base_risk = (spam_score * 0.6) + (fraud_confidence * 0.4)
        
        # Add risk based on suspicious entities
        entity_risk = min(entities_count * 5, 20)
        total_risk = min(base_risk + entity_risk, 100.0)
        
        # Cap at reasonable max if no fraud detected
        if fraud_confidence == 0:
            total_risk = min(total_risk, 50.0)  # Max 50% for safe messages
        
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

        # If it's marked as Normal and no suspicious entities, it's safe
        if fraud_type == "Normal" and fraud_confidence == 0 and not entities:
            reasons.append("No fraud indicators detected")
            reasons.append("Message appears to be normal communication")
            return reasons

        if spam_score > 70:
            reasons.append(f"Message classified as spam with {spam_score:.1f}% probability")
        elif spam_score > 40:
            reasons.append(f"Message shows suspicious patterns ({spam_score:.1f}% spam score)")

        if fraud_confidence > 30:
            reasons.append(f"Detected as '{fraud_type}' with {fraud_confidence:.1f}% confidence")

        if entities:
            entity_types = set([e['type'] for e in entities])
            if 'URL' in entity_types:
                reasons.append("Contains suspicious URL links")
            if 'PHONE' in entity_types:
                reasons.append("Contains phone number requiring verification")
            if 'MONEY' in entity_types:
                reasons.append("References financial amounts")
            if 'ACTION' in entity_types:
                reasons.append("Contains action-prompting keywords (click, verify, etc.)")

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
