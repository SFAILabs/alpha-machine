import requests
import json
from pathlib import Path

# Configuration
TRANSCRIPT_SERVICE_URL = "http://localhost:8000"
LINEAR_SERVICE_URL = "http://localhost:8002"
TRANSCRIPT_FILE = Path(__file__).parent / "data/sf_ai_-_fnrp_transcript.txt"

def run_test():
    """
    Tests the full workflow from transcript processing to Linear issue creation.
    """
    print("="*50)
    print("🚀 STARTING INTEGRATION TEST 🚀")
    print("="*50)

    # 1. Read the transcript from the file
    print(f"📖 Reading transcript from: {TRANSCRIPT_FILE}")
    try:
        with open(TRANSCRIPT_FILE, 'r', encoding='utf-8') as f:
            transcript_content = f.read()
        print("✅ Transcript loaded successfully.")
    except FileNotFoundError:
        print(f"❌ ERROR: Transcript file not found at {TRANSCRIPT_FILE}")
        return

    # 2. Call the Transcript service to extract ticket data
    print("\n" + "-"*50)
    print("🗣️ Calling Transcript Service to extract tickets...")
    print(f"   URL: {TRANSCRIPT_SERVICE_URL}/processor/process")
    
    try:
        transcript_response = requests.post(
            f"{TRANSCRIPT_SERVICE_URL}/processor/process",
            json={"raw_transcript": transcript_content, "metadata": {"source": "test"}}
        )
        transcript_response.raise_for_status()
        extracted_data = transcript_response.json()
        generated_issues = extracted_data.get('issues', [])
        
        print("✅ Transcript processed successfully.")
        
        print("\n" + "="*50)
        print("🔍 EXTRACTED TICKETS (from Transcript Service)")
        print("="*50)
        print(json.dumps(generated_issues, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Failed to call Transcript service: {e}")
        return
    
    if not generated_issues:
        print("\n" + "⚠️ No tickets were extracted from the transcript. Skipping Linear creation.")
        print("\n" + "="*50)
        print("🎉 INTEGRATION TEST FINISHED 🎉")
        print("="*50)
        return

    # 3. Call the Linear service to create the extracted issues
    print("\n" + "-"*50)
    print("🎫 Calling Linear Service to create issues...")
    print(f"   URL: {LINEAR_SERVICE_URL}/create-issues")

    try:
        linear_response = requests.post(
            f"{LINEAR_SERVICE_URL}/create-issues",
            json={"issues": generated_issues}
        )
        linear_response.raise_for_status()
        linear_result = linear_response.json()
        
        print("✅ Linear service workflow completed.")
        
        print("\n" + "="*50)
        print("📝 LINEAR ISSUES CREATED (from Linear Service)")
        print("="*50)
        print(json.dumps(linear_result, indent=2))

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Failed to call Linear service: {e}")
        return

    print("\n" + "="*50)
    print("🎉 INTEGRATION TEST FINISHED 🎉")
    print("="*50)

if __name__ == "__main__":
    run_test() 