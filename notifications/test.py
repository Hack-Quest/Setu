import os
import sys

# Handle Windows emoji printing errors
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# Ensure the root directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from notifications.gmail_alert import send_alert

def run_test():
    print("Starting test for gmail_alert...")
    
    # Mock data simulating what final_data looks like
    mock_need_data = {
        "severity": "critical",
        "category": "medical",
        "description": "Patient needs urgent oxygen supply, running very low.",
        "disaster_type": "earthquake",
        "help_needed": "oxygen cylinder",
        "lat": 28.7041,
        "lng": 77.1025,
        "flag": "verified"
    }
    
    success = send_alert(mock_need_data)
    
    if success:
        print("\n✅ Test passed! The alert email was sent successfully.")
    else:
        print("\n❌ Test failed! The email was not sent.")
        print("💡 Make sure your .env has GMAIL_SENDER and GMAIL_APP_PASSWORD configured correctly.")

if __name__ == "__main__":
    run_test()
