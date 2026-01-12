import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

# In a real environment, we'd need a token, but let's assume local test or session cookie
# For this script to work, uvicorn must be running and we might need an admin user

def test_event_payloads():
    # 1. Create a session or get a token (assuming we have one or uvicorn is running)
    # Since I'm an agent, I'll try to use the database directly or assume the API is open for this test
    # Actually, the better way is to use the actual endpoints if possible.
    
    # Let's try to login first if needed, or assume we have a bypass for testing
    # For now, I'll just print what should be tested and try a simple GET
    try:
        response = requests.get(f"{BASE_URL}/events", timeout=5)
        print(f"GET /events status: {response.status_code}")
        if response.status_code == 200:
            events = response.json()
            print(f"Found {len(events)} events.")
            for event in events:
                print(f"Event ID {event['id']}: attendees={type(event.get('attendees'))}, reminders={type(event.get('reminders'))}")
                if event.get('attendees'):
                    print(f"  Attendees: {event['attendees']}")
                if event.get('reminders'):
                    print(f"  Reminders: {event['reminders']}")
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_event_payloads()
