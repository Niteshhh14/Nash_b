import os
import sys

# Configure environment variables to mock/stub settings
os.environ["TWILIO_ACCOUNT_SID"] = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
os.environ["TWILIO_AUTH_TOKEN"] = "mock_token"
os.environ["TWILIO_PHONE_NUMBER"] = "+15017122661"
os.environ["TWILIO_WHATSAPP_NUMBER"] = "+14155238886"

os.environ["DOCTOR_PHONE"] = "+12345678901"
os.environ["CAREGIVER_PHONE"] = "+12345678902"
os.environ["EMERGENCY_PHONE"] = "+12345678903"

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.notifications.notification_service import send_emergency_notifications

def run_test():
    print("Running Twilio simulated notifications test...")
    res = send_emergency_notifications(
        patient_name="Ramesh Kumar (Test)",
        score=95.0,
        risk="critical",
        reason="Test Cardiac Arrest Simulation",
        heart_rate=120,
        spo2=85,
        bp="80/40"
    )
    print("Result:", res)
    
    # Assertions for mock client execution
    assert res["success"] is True
    assert res["sms"] == "sent"
    assert res["whatsapp"] == "sent"
    print("All test assertions passed successfully!")

if __name__ == "__main__":
    run_test()
