"""
Test examples for AI Fraud Detection API
Run after starting the server with: python main.py
"""

import requests
import json

API_URL = "http://localhost:8000"

# Test messages covering different fraud types
test_messages = [
    {
        "name": "UPI Fraud",
        "message": "Dear customer, your account will be blocked. Approve this UPI collect request immediately to prevent suspension."
    },
    {
        "name": "Lottery Scam",
        "message": "CONGRATULATIONS! You won Rs 25 lakhs in lucky draw. Pay processing fee of Rs 5000 to claim your prize."
    },
    {
        "name": "Job Scam",
        "message": "Work from home opportunity! Earn 50k monthly. Pay Rs 2000 registration fee now. Limited slots available."
    },
    {
        "name": "Phishing",
        "message": "Your bank account KYC expired. Click http://fake-bank.com/verify to update immediately or account will be frozen."
    },
    {
        "name": "Investment Scam",
        "message": "Guaranteed 300% returns in 30 days! Invest minimum Rs 10000 in our crypto scheme. WhatsApp: 9876543210"
    },
    {
        "name": "Safe Message",
        "message": "Hi, are you coming to the meeting tomorrow at 10 AM? Let me know."
    }
]


def test_analyze():
    """Test fraud analysis endpoint"""
    print("\n" + "="*60)
    print("TESTING FRAUD DETECTION API")
    print("="*60)
    
    for test in test_messages:
        print(f"\n🔍 Testing: {test['name']}")
        print(f"Message: {test['message']}\n")
        
        try:
            response = requests.post(
                f"{API_URL}/api/analyze",
                json={"message": test["message"]}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"📊 ANALYSIS RESULT")
                print(f"├─ Risk Score: {result['risk_score']}%")
                print(f"├─ Risk Level: {result['risk_level']}")
                print(f"├─ Fraud Type: {result['fraud_type']}")
                print(f"├─ Fraud Confidence: {result['fraud_confidence']:.1f}%")
                print(f"├─ Spam Score: {result['spam_score']:.1f}%")
                
                if result['entities_detected']:
                    print(f"├─ Entities Detected:")
                    for entity in result['entities_detected']:
                        print(f"│  • {entity['entity']} ({entity['type']}) - {entity['confidence']:.1f}%")
                
                print(f"├─ Reasoning:")
                for reason in result['reasoning']:
                    print(f"│  • {reason}")
                
                print(f"├─ Safety Advice: {result['safety_advice']}")
                print(f"└─ Helpline: {result['helpline']}")
                
            else:
                print(f"❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print("-" * 60)


def test_logs():
    """Test logs retrieval"""
    print("\n" + "="*60)
    print("TESTING LOGS RETRIEVAL")
    print("="*60 + "\n")
    
    try:
        response = requests.get(f"{API_URL}/api/logs?limit=10")
        if response.status_code == 200:
            logs = response.json()
            print(f"📝 Retrieved {len(logs)} logs\n")
            
            for log in logs[:5]:  # Show first 5
                print(f"ID: {log['id']} | Risk: {log['risk_level']} ({log['risk_score']}%) | Type: {log['fraud_type']}")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")


def test_stats():
    """Test statistics endpoint"""
    print("\n" + "="*60)
    print("TESTING STATISTICS")
    print("="*60 + "\n")
    
    try:
        response = requests.get(f"{API_URL}/api/stats")
        if response.status_code == 200:
            stats = response.json()
            
            print(f"📈 FRAUD DETECTION STATISTICS")
            print(f"├─ Total Messages: {stats['total_messages_analyzed']}")
            print(f"├─ High Risk: {stats['high_risk']}")
            print(f"├─ Suspicious: {stats['suspicious']}")
            print(f"├─ Safe: {stats['safe']}")
            print(f"├─ Average Risk Score: {stats['average_risk_score']}%")
            print(f"└─ Fraud Type Distribution:")
            for fraud_type, count in stats['fraud_type_distribution'].items():
                print(f"   • {fraud_type}: {count}")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")


if __name__ == "__main__":
    print("\n🚀 AI Fraud Detection API Tester")
    print("Make sure the API server is running (python main.py)\n")
    
    # Run tests
    test_analyze()
    test_logs()
    test_stats()
    
    print("\n✅ Testing completed!")
