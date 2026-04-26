from transformers import pipeline
import logging
from typing import Dict, List, Tuple
import re
import requests
from urllib.parse import urlparse
from collections import defaultdict

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
            # Model 1: Spam Detection - MULTILINGUAL (English, Hindi, +many languages)
            # Zero-shot NLI is more reliable for fraud/spam intent than toxicity models.
            self.spam_detector = pipeline(
                "zero-shot-classification",
                model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
                device=-1
            )
            self.spam_mode = "zero_shot"
            logger.info("[OK] Multilingual zero-shot spam detector loaded")

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

            # Comprehensive fraud detection keywords (English + Hindi)
            self.fraud_keywords = {
                "Upi Fraud": [
                    "upi", "payment", "transfer", "scan", "collect", "approve", "request",
                    "gpay", "paytm", "phonepe", "bhim", "qr code", "rupee", "withdraw",
                    "confirm transaction", "verify payment", "authorize", "release amount"
                ],
                "Upi Fraud (Hindi)": [
                    "upi", "payment", "भुगतान", "transfer", "स्थानांतरण", "scan", "स्कैन",
                    "collect", "approve", "qr", "क्यूआर", "code", "gpay", "paytm", "phonepe",
                    "bhim", "bheem", "rupee", "रुपये", "withdraw", "निकालना", "verify",
                    "verify payment", "transaction", "लेनदेन", "confirm", "पुष्टि", "release",
                    "amount", "रकम", "authorize", "अधिकृत"
                ],
                "Job Scam": [
                    "job", "work", "home", "registration", "fee", "earn", "hiring", "applicant",
                    "interview", "offer", "position", "vacancy", "salary", "part-time", "full-time",
                    "commission", "bonus", "training", "placement", "appointment letter", "submit documents"
                    ],
                    "Job Scam (Hindi)": [
                        "job", "नौकरी", "काम", "work", "घर", "home", "registration", "पंजीकरण",
                        "fee", "शुल्क", "earn", "कमाना", "earning", "कमाई", "hiring", "नियुक्ति",
                        "applicant", "आवेदक", "interview", "साक्षात्कार", "offer", "प्रस्ताव",
                        "position", "पद", "vacancy", "रिक्ति", "salary", "वेतन", "part-time",
                        "पूर्णकालिक", "commission", "कमीशन", "bonus", "बोनस", "training", "प्रशिक्षण",
                        "placement", "प्लेसमेंट", "appointment", "नियुक्ति", "letter", "पत्र",
                        "submit", "जमा", "documents", "दस्तावेज"
                    ],
                "Lottery Scam": [
                    "lottery", "won", "prize", "claim", "congratulations", "reward", "win",
                    "draw", "lucky", "selected", "claim prize", "process", "tax", "fee",
                    "scratch card", "raffle", "fortune", "bonus", "jackpot", "advance payment"
                    ],
                    "Lottery Scam (Hindi)": [
                        "lottery", "लॉटरी", "won", "जीते", "prize", "पुरस्कार", "claim", "दावा",
                        "congratulations", "बधाई", "reward", "इनाम", "win", "जीतना", "draw",
                        "आरेखण", "lucky", "भाग्यशाली", "selected", "चयनित", "process", "प्रक्रिया",
                        "tax", "कर", "fee", "शुल्क", "scratch", "स्क्रैच", "card", "कार्ड",
                        "raffle", "रैफल", "fortune", "भाग्य", "bonus", "बोनस", "jackpot",
                        "advance", "अग्रिम", "payment", "भुगतान", "confirmation", "पुष्टि",
                        "जीती", "जीता", "क्लेम", "फीस", "प्रोसेसिंग", "भेजें", "भेजो"
                    ],
                "Phishing": [
                    "verify", "password", "click", "secure", "confirm", "update", "account",
                    "email", "bank", "urgent", "expires", "lockout", "suspended", "blocked",
                    "instgram", "facebook", "whatsapp", "link", "login", "credentials",
                    "card number", "cvv", "otp", "pin", "confirm identity", "re-verify",
                    "unusual activity", "suspicious", "action required", "immediately"
                    ],
                    "Phishing (Hindi)": [
                        "verify", "सत्यापित", "password", "पासवर्ड", "click", "क्लिक", "secure",
                        "सुरक्षित", "confirm", "पुष्टि", "update", "अद्यतन", "account", "खाता",
                        "email", "ईमेल", "bank", "बैंक", "urgent", "जरूरी", "expires", "समाप्त",
                        "lockout", "लॉकआउट", "suspended", "निलंबित", "blocked", "अवरुद्ध",
                        "facebook", "फेसबुक", "whatsapp", "व्हाट्सएप", "link", "लिंक",
                        "login", "लॉगिन", "credentials", "साख", "card", "कार्ड", "cvv",
                        "otp", "pin", "पिन", "identity", "पहचान", "unusual", "असामान्य",
                        "activity", "गतिविधि", "suspicious", "संदिग्ध", "action", "कार्रवाई",
                        "required", "आवश्यक", "immediately", "तुरंत"
                    ],
                "Investment Scam": [
                    "investment", "crypto", "profit", "bitcoin", "forex", "guaranteed", "returns",
                    "share market", "stock", "mutual fund", "trading", "multiply money", "double",
                    "high return", "risk free", "fast money", "passive income", "deposit"
                    ],
                    "Investment Scam (Hindi)": [
                        "investment", "निवेश", "crypto", "क्रिप्टो", "profit", "लाभ", "bitcoin",
                        "बिटकॉइन", "forex", "फॉरेक्स", "guaranteed", "गारंटीकृत", "returns",
                        "रिटर्न", "share", "शेयर", "market", "बाजार", "stock", "स्टॉक",
                        "mutual", "म्यूचुअल", "fund", "फंड", "trading", "व्यापार", "multiply",
                        "गुणा", "money", "पैसा", "double", "दोगुना", "high", "उच्च", "return",
                        "रिटर्न", "risk", "जोखिम", "free", "मुफ्त", "fast", "तेजी", "passive",
                        "निष्क्रिय", "income", "आय", "deposit", "जमा", "passive income",
                        "आय"
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
        """Detect spam probability using multilingual zero-shot model + calibration"""
        try:
            message_lower = message.lower()

            # Multilingual zero-shot fraud intent scoring
            result = self.spam_detector(
                message,
                candidate_labels=[
                    "fraudulent scam message",
                    "legitimate normal message"
                ],
                hypothesis_template="This text is {}."
            )

            label_scores = {
                label.lower(): score
                for label, score in zip(result.get("labels", []), result.get("scores", []))
            }
            raw_score = label_scores.get("fraudulent scam message", 0.5) * 100

            # Safe conversational patterns
            safe_patterns = [
                r'\bhow\s+are\s+you\b', r'\bhello\b', r'\bhi\b', r'\bthanks\b',
                r'\bplease\b', r'\bwhen\b', r'\bwhere\b', r'\bwhat\b', r'\bwhy\b',
                r'\bwhat\'s\b', r'\byou\s+ok\b', r'\bthank\s+you\b',
                r'\bकैसे\s+हो\b', r'\bनमस्ते\b', r'\bधन्यवाद\b'
            ]

            # High-risk indicators (English + Hindi)
            risk_patterns = [
                r'\blottery\b', r'\bwon\b', r'\bclaim\b', r'\bscratch\s*card\b',
                r'\bclick\b', r'\bverify\b', r'\bupi\b', r'\bupi\s*pin\b',
                r'\botp\b', r'\bcvv\b', r'\bbank\b', r'\btransfer\b',
                r'http[s]?://', r'\burgent\b', r'\bfee\b',
                r'लॉटरी', r'जीते', r'इनाम', r'दावा', r'क्लिक', r'सत्यापित',
                r'पिन', r'ओटीपी', r'बैंक', r'स्थानांतरण', r'बधाई', r'जीती', r'क्लेम', r'फीस', r'भेजें'
            ]

            has_safe_pattern = any(re.search(pattern, message_lower) for pattern in safe_patterns)
            matched_risks = sum(bool(re.search(pattern, message_lower)) for pattern in risk_patterns)

            adjusted_score = raw_score

            # Strong boost for multiple risk indicators
            if matched_risks >= 3:
                adjusted_score = min(adjusted_score + 35, 100)
            elif matched_risks == 2:
                adjusted_score = min(adjusted_score + 20, 100)
            elif matched_risks == 1:
                adjusted_score = min(adjusted_score + 10, 100)

            # Reduce only when clearly conversational and no risk terms
            if has_safe_pattern and matched_risks == 0:
                adjusted_score = max(adjusted_score * 0.35, 5)

            label = "spam" if adjusted_score >= 50 else "ham"
            logger.info(f"Spam detection: {label} (raw: {raw_score:.2f}% -> adjusted: {adjusted_score:.2f}%)")
            return adjusted_score, label

        except Exception as e:
            logger.error(f"Spam detection error: {e}")
            return 50.0, "unknown"

    def classify_fraud_type(self, message: str) -> Tuple[str, float]:
        """Classify fraud type using multilingual weighted keyword scoring"""
        try:
            message_lower = message.lower()
            scores = defaultdict(float)

            category_critical = {
                "Upi Fraud": ["upi pin", "otp", "cvv", "approve collect", "collect request", "pin"],
                "Job Scam": ["registration fee", "joining fee", "pay for job", "offer letter fee"],
                "Lottery Scam": ["scratch card", "claim prize", "won", "jackpot", "processing fee", "क्लेम", "फीस", "जीती", "बधाई"],
                "Phishing": ["verify account", "suspended", "blocked", "click link", "update kyc"],
                "Investment Scam": ["guaranteed returns", "double money", "risk free", "crypto profit"]
            }

            for raw_type, keywords in self.fraud_keywords.items():
                base_type = raw_type.replace(" (Hindi)", "")
                unique_matches = set()
                for keyword in keywords:
                    kw = keyword.strip().lower()
                    if kw and kw in message_lower:
                        unique_matches.add(kw)

                match_count = len(unique_matches)
                critical_hits = sum(1 for kw in category_critical.get(base_type, []) if kw in message_lower)

                # Weighted score avoids dilution from long keyword lists.
                # 8 points per match + 20 per critical phrase.
                scores[base_type] += (match_count * 8) + (critical_hits * 20)

            # Extra escalation for classic payout + credential theft combo
            payout_terms = ["lottery", "won", "scratch card", "claim", "reward", "prize", "लॉटरी", "इनाम", "दावा"]
            credential_terms = ["upi pin", "otp", "cvv", "pin", "password", "पिन", "ओटीपी", "पासवर्ड"]
            if any(t in message_lower for t in payout_terms) and any(t in message_lower for t in credential_terms):
                scores["Lottery Scam"] = max(scores["Lottery Scam"], 80)

            if scores:
                fraud_type = max(scores, key=scores.get)
                confidence = min(scores[fraud_type], 100.0)
                if confidence < 20:
                    fraud_type = "Normal"
                    confidence = 0.0
            else:
                fraud_type = "Normal"
                confidence = 0.0

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
                "update": "ACTION",
                "बधाई": "REWARD",
                "क्लेम": "ACTION",
                "फीस": "FINANCIAL",
                "भेजें": "ACTION",
                "लॉटरी": "SCAM_TYPE",
                "पिन": "FINANCIAL",
                "ओटीपी": "FINANCIAL"
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

    def apply_contextual_risk_boost(
        self,
        message: str,
        fraud_type: str,
        risk_score: float,
        entities: List[Dict]
    ) -> float:
        """Apply deterministic boosts for known scam combinations (English + Hindi)."""
        message_lower = message.lower()
        boosted = risk_score

        lottery_terms = ["lottery", "लॉटरी", "scratch card", "स्क्रैच", "jackpot", "इनाम", "बधाई", "claim", "क्लेम"]
        payment_terms = ["fee", "processing fee", "payment", "pay", "transfer", "send", "फीस", "भुगतान", "जमा", "भेजें"]
        credential_terms = ["upi pin", "otp", "cvv", "pin", "password", "पिन", "ओटीपी", "पासवर्ड"]
        bank_terms = ["bank", "बैंक", "collect", "collect request", "approve", "transfer", "स्थानांतरण"]

        has_lottery = any(term in message_lower for term in lottery_terms)
        has_payment = any(term in message_lower for term in payment_terms)
        has_credentials = any(term in message_lower for term in credential_terms)
        has_bank_flow = any(term in message_lower for term in bank_terms)

        money_entities = sum(1 for e in entities if e.get("type") == "MONEY")

        # Lottery + demand for money/credentials is almost always a scam.
        if (fraud_type == "Lottery Scam" or has_lottery) and (has_payment or has_credentials):
            boosted = max(boosted, 75.0)

        # Credential theft + banking flow is severe.
        if has_credentials and has_bank_flow:
            boosted = max(boosted, 80.0)

        # Multiple money amounts in scam context increase risk.
        if money_entities >= 2 and (has_lottery or has_payment):
            boosted = min(boosted + 10.0, 100.0)

        return round(min(boosted, 100.0), 2)

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

            # Step 4b: Contextual boost for strong multilingual scam patterns
            risk_score = self.apply_contextual_risk_boost(
                message,
                fraud_type,
                risk_score,
                entities
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

            if risk_score >= 70 and fraud_type == "Lottery Scam":
                reasoning.append("Lottery/reward claim combined with money or credential request indicates high scam probability")

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
