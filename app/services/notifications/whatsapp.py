import os
import logging
import time
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger("notifications.whatsapp")
logging.basicConfig(level=logging.INFO)

# Load environment credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

def send_whatsapp(to_number: str, body_text: str) -> dict:
    """
    Sends a WhatsApp message using Twilio WhatsApp Sandbox configuration.
    Retries once on transient errors.
    """
    # Mocking fallback for missing configuration
    if not TWILIO_ACCOUNT_SID or TWILIO_ACCOUNT_SID.startswith("ACXX"):
        logger.info(f"[SIMULATED WHATSAPP SENDER] To: whatsapp:{to_number}\nContent:\n{body_text}\n")
        return {"status": "sent", "message_sid": f"WH_mock_{int(time.time())}"}

    if not to_number or to_number.startswith("+12345678"):
        logger.warning(f"Dummy or invalid recipient phone number ({to_number}). Skipping WhatsApp.")
        return {"status": "skipped", "reason": "Dummy recipient number"}

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    # Twilio Sandbox requires numbers formatted as 'whatsapp:<E.164>'
    from_whatsapp = f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
    to_whatsapp = f"whatsapp:{to_number}"
    
    for attempt in range(2):
        try:
            logger.info(f"Attempting to send WhatsApp message to {to_whatsapp} (attempt {attempt + 1})...")
            message = client.messages.create(
                body=body_text,
                from_=from_whatsapp,
                to=to_whatsapp
            )
            logger.info(f"WhatsApp successfully sent to {to_whatsapp}. SID: {message.sid}")
            return {"status": "sent", "message_sid": message.sid}
        except TwilioRestException as tre:
            logger.error(f"Twilio API error sending WhatsApp on attempt {attempt + 1}: {tre.msg} (status: {tre.status})")
            if 400 <= tre.status < 500:
                return {"status": "failed", "error": f"Twilio Client error: {tre.msg}"}
            if attempt == 0:
                time.sleep(1)
            else:
                return {"status": "failed", "error": f"Twilio server error: {tre.msg}"}
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp on attempt {attempt + 1}: {str(e)}")
            if attempt == 0:
                time.sleep(1)
            else:
                return {"status": "failed", "error": f"Unexpected error: {str(e)}"}
