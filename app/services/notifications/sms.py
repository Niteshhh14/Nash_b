import os
import logging
import time
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger("notifications.sms")
logging.basicConfig(level=logging.INFO)

# Load environment credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

def send_sms(to_number: str, body_text: str) -> dict:
    """
    Sends an SMS notification using Twilio SMS client.
    Retries once on transient errors.
    """
    # Mocking fallback for missing configuration
    if not TWILIO_ACCOUNT_SID or TWILIO_ACCOUNT_SID.startswith("ACXX"):
        logger.info(f"[SIMULATED SMS SENDER] To: {to_number}\nContent:\n{body_text}\n")
        return {"status": "sent", "message_sid": f"SM_mock_{int(time.time())}"}

    if not to_number or to_number.startswith("+12345678"):
        logger.warning(f"Dummy or invalid recipient phone number ({to_number}). Skipping SMS.")
        return {"status": "skipped", "reason": "Dummy recipient number"}

    if not TWILIO_PHONE_NUMBER:
        logger.warning("TWILIO_PHONE_NUMBER is not configured. Skipping SMS dispatch.")
        return {"status": "skipped", "reason": "Missing sender phone number"}

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    for attempt in range(2):
        try:
            logger.info(f"Attempting to send SMS to {to_number} (attempt {attempt + 1})...")
            message = client.messages.create(
                body=body_text,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            logger.info(f"SMS successfully sent to {to_number}. SID: {message.sid}")
            return {"status": "sent", "message_sid": message.sid}
        except TwilioRestException as tre:
            logger.error(f"Twilio API error sending SMS on attempt {attempt + 1}: {tre.msg} (status: {tre.status})")
            if 400 <= tre.status < 500:
                # Client errors (e.g. invalid number) shouldn't be retried
                return {"status": "failed", "error": f"Twilio Client error: {tre.msg}"}
            if attempt == 0:
                time.sleep(1)
            else:
                return {"status": "failed", "error": f"Twilio server error: {tre.msg}"}
        except Exception as e:
            logger.error(f"Unexpected error sending SMS on attempt {attempt + 1}: {str(e)}")
            if attempt == 0:
                time.sleep(1)
            else:
                return {"status": "failed", "error": f"Unexpected error: {str(e)}"}
