#!/usr/bin/env python3
"""
Test script for image and voice analysis endpoints
"""

import requests
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

BASE_URL = "http://localhost:8000"

# Colors for test images
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)


def create_test_image_phishing():
    """Create a test image with phishing text"""
    img = Image.new('RGB', (400, 200), color=WHITE)
    draw = ImageDraw.Draw(img)
    
    # Add phishing scam text
    text = "URGENT: Confirm your UPI PIN!\nClick here: http://malicious.com\nDon't share with anyone!"
    draw.text((10, 50), text, fill=BLACK)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


def create_test_image_lottery():
    """Create a test image with lottery scam text"""
    img = Image.new('RGB', (400, 200), color=WHITE)
    draw = ImageDraw.Draw(img)
    
    # Add lottery scam text
    text = "Congratulations! You won 5 lakh rupees!\nClaim now: Contact 9876543210\nNo verification needed!"
    draw.text((10, 50), text, fill=BLACK)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


def create_test_image_safe():
    """Create a test image with safe text"""
    img = Image.new('RGB', (400, 200), color=WHITE)
    draw = ImageDraw.Draw(img)
    
    # Add safe text
    text = "Hello friend, how are you today?\nLet's meet up for coffee tomorrow."
    draw.text((10, 50), text, fill=BLACK)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


def test_image_analysis():
    """Test image analysis endpoint"""
    print("\n" + "="*60)
    print("Testing Image Analysis Endpoint (/api/analyze-image)")
    print("="*60)
    
    test_cases = [
        ("Phishing SMS Screenshot", create_test_image_phishing()),
        ("Lottery Scam Screenshot", create_test_image_lottery()),
        ("Safe Message Screenshot", create_test_image_safe()),
    ]
    
    for name, image_data in test_cases:
        print(f"\n[TEST] {name}")
        print("-" * 40)
        
        try:
            files = {'file': ('test_image.png', image_data, 'image/png')}
            response = requests.post(f"{BASE_URL}/api/analyze-image", files=files)
            
            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Request successful")
                print(f"    Risk Level: {result.get('risk_level')}")
                print(f"    Risk Score: {result.get('risk_score')}%")
                print(f"    Fraud Type: {result.get('fraud_type')}")
                print(f"    Source: {result.get('source')}")
                print(f"    Reasoning: {result.get('reasoning')}")
            else:
                print(f"[ERROR] Status code: {response.status_code}")
                print(f"    Error: {response.text}")
        except Exception as e:
            print(f"[ERROR] {str(e)}")


def test_voice_analysis():
    """Test voice analysis endpoint with a test audio file"""
    print("\n" + "="*60)
    print("Testing Voice Analysis Endpoint (/api/analyze-voice)")
    print("="*60)
    
    # Check if we have a sample audio file
    audio_file = Path("test_audio.wav")
    
    if not audio_file.exists():
        print("\n[INFO] No test_audio.wav file found.")
        print("[INFO] To test voice analysis, please provide an audio file named 'test_audio.wav'")
        print("[INFO] Supported formats: MP3, WAV, M4A, OGG, FLAC")
        return
    
    print(f"\n[TEST] Voice Message Analysis")
    print("-" * 40)
    
    try:
        with open(audio_file, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            response = requests.post(f"{BASE_URL}/api/analyze-voice", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Request successful")
            print(f"    Risk Level: {result.get('risk_level')}")
            print(f"    Risk Score: {result.get('risk_score')}%")
            print(f"    Fraud Type: {result.get('fraud_type')}")
            print(f"    Transcribed: {result.get('message')[:100]}...")
            print(f"    Source: {result.get('source')}")
        else:
            print(f"[ERROR] Status code: {response.status_code}")
            print(f"    Error: {response.text}")
    except FileNotFoundError:
        print(f"[ERROR] Audio file not found: {audio_file}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")


def test_text_analysis():
    """Test original text analysis for comparison"""
    print("\n" + "="*60)
    print("Testing Text Analysis Endpoint (/api/analyze) for Comparison")
    print("="*60)
    
    test_messages = [
        "URGENT: Confirm your UPI PIN! Click here: http://malicious.com",
        "Congratulations! You won 5 lakh rupees! Claim now: 9876543210",
        "Hello friend, how are you today?",
    ]
    
    for msg in test_messages:
        print(f"\n[TEST] {msg[:50]}...")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/analyze",
                json={"message": msg}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Request successful")
                print(f"    Risk Level: {result.get('risk_level')}")
                print(f"    Risk Score: {result.get('risk_score')}%")
                print(f"    Fraud Type: {result.get('fraud_type')}")
                print(f"    Source: {result.get('source', 'TEXT')}")
            else:
                print(f"[ERROR] Status code: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] {str(e)}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("MULTIMEDIA FRAUD DETECTION - TEST SUITE")
    print("="*60)
    print("\n[INFO] Make sure the server is running on http://localhost:8000")
    
    # Run tests
    test_image_analysis()
    test_text_analysis()
    test_voice_analysis()
    
    print("\n" + "="*60)
    print("Testing completed!")
    print("="*60)
