#!/usr/bin/env python3
"""
Simple script to start ngrok tunnel and display the public URL
for Twilio webhook configuration.
"""

from pyngrok import ngrok
import time

def start_tunnel():
    """Start ngrok tunnel and display public URL"""
    
    print("\n" + "="*60)
    print("NGROK TUNNEL STARTER")
    print("="*60 + "\n")
    
    try:
        # Start ngrok tunnel on port 8000
        print("[*] Starting ngrok tunnel on http://localhost:8000...")
        public_url = ngrok.connect(8000, "http")
        
        print("[✓] Tunnel created successfully!\n")
        
        # Extract URL
        ngrok_url = str(public_url).replace("http://", "https://")
        webhook_url = f"{ngrok_url}/api/forward/sms-webhook"
        
        print("="*60)
        print("COPY THIS URL TO TWILIO WEBHOOK:")
        print("="*60)
        print(f"\n{webhook_url}\n")
        print("="*60)
        
        print("\nConfiguration steps:")
        print("1. Go to Twilio Console → Phone Numbers → Your Number")
        print("2. Find 'A message comes in' section")
        print("3. Set Webhook URL to the URL above")
        print("4. Make sure HTTP method is: HTTP POST")
        print("5. Click 'Save configuration'")
        print("\nThen send a test SMS to your Twilio number!")
        
        print("\n[*] Tunnel is running. Press Ctrl+C to stop...\n")
        
        # Keep tunnel running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[*] Shutting down tunnel...")
            ngrok.disconnect(public_url)
            print("[✓] Tunnel closed. Goodbye!")
            
    except Exception as e:
        print(f"\n[✗] Error: {e}")
        print("\nMake sure:")
        print("1. FastAPI server is running on port 8000")
        print("2. pyngrok is installed: pip install pyngrok")
        print("3. You have internet connection")

if __name__ == "__main__":
    start_tunnel()
