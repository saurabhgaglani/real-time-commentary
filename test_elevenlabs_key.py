"""
Quick test script to verify ElevenLabs API key
Run this locally (not in Docker) to test your API key
"""
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load environment variables
load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")

if not api_key:
    print("❌ ELEVENLABS_API_KEY not found in .env")
    exit(1)

print(f"Testing API key: {api_key[:10]}...")

try:
    client = ElevenLabs(api_key=api_key)
    
    # Try to get user info
    print("✅ API key is valid!")
    print("Testing text-to-speech...")
    
    # Simple test
    audio = client.text_to_dialogue.convert(
        inputs=[
            {
                "text": "Test",
                "voice_id": "PdJQAOWyIMAQwD7gQcSc",
            }
        ]
    )
    
    print("✅ Text-to-speech works!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPossible issues:")
    print("1. Invalid API key")
    print("2. API quota exceeded")
    print("3. Network connectivity issue")
    print("4. Voice ID not available")
