import requests
import time
import json
import os
import logging
from datetime import datetime
from dotenv import load_dotenv # Add dotenv import

# Explicitly load .env file relative to the current working directory
dotenv_path = os.path.join(os.getcwd(), '.env')
# dotenv_path = os.path.join(os.path.dirname(__file__), '.env') # Previous attempt
loaded = load_dotenv(dotenv_path=dotenv_path)
if not loaded:
    logging.warning(f"Could not load .env file from path: {dotenv_path}")
else:
    logging.info(f"Successfully loaded .env file from {dotenv_path}")

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VapiLeadCaller:
    """Handles placing and retrieving calls using the Vapi API."""
    def __init__(self, auth_token, assistant_id, phone_number_id):
        """
        Initialize with Vapi credentials and assistant ID.
        Args:
            auth_token (str): Your Vapi Bearer token.
            assistant_id (str): The ID of the Vapi assistant to use.
            phone_number_id (str): The ID of the Vapi phone number to call from.
        """
        if not all([auth_token, assistant_id, phone_number_id]):
            raise ValueError("Auth token, assistant ID, and phone number ID are required.")
        self.auth_token = auth_token
        self.assistant_id = assistant_id
        self.phone_number_id = phone_number_id
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        logging.info(f"VapiLeadCaller initialized for assistant: {assistant_id}")

    def place_call(self, lead):
        """
        Place a call to a single lead.
        Args:
            lead (dict): Dict containing lead info with at least:
                         'mobile_no' (phone number), 'name' (lead record ID),
                         'first_name', 'last_name'.
        Returns:
            dict: Result containing success status, call_id/error, and lead_id.
        """
        lead_phone = lead.get("mobile_no")
        lead_record_name = lead.get("name") # Using Frappe record name as lead_id
        full_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()

        if not lead_phone or not lead_record_name:
            logging.error(f"Lead missing phone number or name (ID): {lead}")
            return {"success": False, "lead_id": lead_record_name, "error": "Missing phone or name"}

        # --- Simplified Payload --- #
        call_data = {
            "assistantId": self.assistant_id,
            "phoneNumberId": self.phone_number_id,
            "customer": {
                "number": lead_phone
                # Removed "name": full_name if full_name else lead_record_name,
                # Removed "metadata": { ... }
            }
            # Removed top-level "name": f"Lead call - {lead_record_name}"
        }

        logging.info(f"Placing call to {lead_phone} for lead {lead_record_name} (Simplified Payload)")
        logging.debug(f"Call payload: {json.dumps(call_data, indent=2)}")

        try:
            response = requests.post(
                f"{self.base_url}/call",
                headers=self.headers,
                json=call_data,
                timeout=30 # 30 second timeout for API request
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            call_result = response.json()
            logging.info(f"Call initiated successfully for lead {lead_record_name}. Call ID: {call_result.get('id')}")
            return {
                "success": True,
                "call_id": call_result.get("id"),
                "lead_id": lead_record_name,
                "status": call_result.get("status")
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to create call via Vapi API for lead {lead_record_name}: {e}")
            error_details = e.response.text if e.response else str(e)
            logging.error(f"Response body: {error_details}")
            return {
                "success": False,
                "lead_id": lead_record_name,
                "error": error_details
            }

    def get_call_details(self, call_id):
        """
        Get details of a specific call using its ID.
        Args:
            call_id (str): The ID of the call to retrieve.
        Returns:
            dict or None: Call details if successful, None otherwise.
        """
        if not call_id:
            logging.warning("get_call_details called with no call_id")
            return None
        logging.debug(f"Fetching call details for call ID: {call_id}")
        try:
            response = requests.get(
                f"{self.base_url}/call/{call_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            call_details = response.json()
            logging.debug(f"Successfully fetched details for call ID: {call_id}")
            return call_details
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to get call details for call ID {call_id}: {e}")
            return None

    def wait_for_call_completion(self, call_id, timeout=300, check_interval=15):
        """
        Poll Vapi API until the call is completed, failed, or canceled, or timeout occurs.
        Args:
            call_id (str): The ID of the call to monitor.
            timeout (int): Maximum seconds to wait.
            check_interval (int): Seconds between status checks.
        Returns:
            dict: Final call details or a timeout/error status.
        """
        if not call_id:
            logging.error("wait_for_call_completion called with no call_id")
            return {"call_id": None, "status": "error", "error": "Missing call_id"}

        elapsed_time = 0
        logging.info(f"Waiting for call {call_id} to complete (timeout: {timeout}s)...")
        while elapsed_time < timeout:
            call_details = self.get_call_details(call_id)

            # --- ADDED: Print full details received during polling --- #
            if call_details:
                logging.info(f"Polling Response for {call_id}:")
                print(json.dumps(call_details, indent=2, default=str)) # Pretty print the JSON
            # --- END ADDED SECTION --- #

            if call_details:
                status = call_details.get("status")
                logging.info(f"Call {call_id} status: {status}")
                if status in ["completed", "failed", "canceled"]:
                    logging.info(f"Call {call_id} finished with status: {status}")
                    # Extract relevant info as per documentation example
                    result = {
                        "call_id": call_details.get("id"),
                        "lead_id": call_details.get("customer", {}).get("metadata", {}).get("lead_id"),
                        "status": status,
                        "duration": call_details.get("duration"),
                        "start_time": call_details.get("startTime"),
                        "end_time": call_details.get("endTime"),
                        "recording_url": None,
                        "transcript": call_details.get("transcript"),
                        "summary": call_details.get("summary"), # Check if Vapi provides summary
                        "cost": call_details.get("cost"),
                        "call_end_reason": call_details.get("endReason")
                    }
                    # Get recording URL if available
                    artifact = call_details.get("artifact")
                    if artifact and artifact.get("recording"):
                        result["recording_url"] = artifact["recording"].get("url")
                    return result
            else:
                logging.warning(f"Could not fetch details for call {call_id} on this attempt.")

            logging.info(f"Waiting {check_interval}s before next status check for call {call_id}...")
            time.sleep(check_interval)
            elapsed_time += check_interval

        logging.warning(f"Wait timeout exceeded for call {call_id} after {timeout} seconds.")
        return {"call_id": call_id, "status": "timeout", "error": "Wait timeout exceeded"}

# --- Main execution --- #

if __name__ == "__main__":
    logging.info("Starting Vapi Call Test Script")

    # --- Configuration --- #
    VAPI_ASSISTANT_ID = "d5d4e25c-abdb-486c-b134-5e32cb4e23de"
    # Get sensitive credentials from environment variables loaded from .env
    VAPI_AUTH_TOKEN = os.getenv("VAPI_API_KEY") # Use VAPI_API_KEY from .env
    # VAPI_PHONE_NUMBER_ID = os.getenv("NEXT_PUBLIC_VAPI_PHONE_NUMBER_ID") # Use NEXT_PUBLIC_VAPI_PHONE_NUMBER_ID from .env
    # *** TEMPORARILY HARDCODING Phone Number ID for testing ***
    VAPI_PHONE_NUMBER_ID = "5010dade-aaa5-42e4-8f39-395dd0555df8"
    logging.warning("Using HARDCODED VAPI_PHONE_NUMBER_ID for testing!") # Add warning

    LEADS_FILE = "leads_test_data.json" # Assumes script is run from vapi_test dir
    # The specific phone number we updated in the JSON for testing
    TEST_PHONE_NUMBER = "+919136820958"

    if not VAPI_AUTH_TOKEN:
        logging.error("Fatal: VAPI_API_KEY not found in .env file or environment.")
        exit(1)
    # Remove check for VAPI_PHONE_NUMBER_ID from env as it's hardcoded now
    # if not VAPI_PHONE_NUMBER_ID:
    #    logging.error("Fatal: NEXT_PUBLIC_VAPI_PHONE_NUMBER_ID not found in .env file or environment.")
    #    exit(1)
    
    # Add explicit check for the hardcoded value just in case
    if not VAPI_PHONE_NUMBER_ID:
        logging.error("Fatal: Hardcoded VAPI_PHONE_NUMBER_ID is missing or empty.")
        exit(1)

    # --- Load Test Data --- #
    leads = []
    try:
        with open(LEADS_FILE, 'r') as f:
            leads = json.load(f)
        logging.info(f"Loaded {len(leads)} leads from {LEADS_FILE}")
    except FileNotFoundError:
        logging.error(f"Fatal: Leads data file not found at {LEADS_FILE}")
        exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"Fatal: Error decoding JSON from {LEADS_FILE}: {e}")
        exit(1)

    # --- Find the Lead to Call --- #
    lead_to_call = None
    for lead in leads:
        if lead.get("mobile_no") == TEST_PHONE_NUMBER:
            lead_to_call = lead
            break

    if not lead_to_call:
        logging.error(f"Fatal: Could not find lead with test phone number {TEST_PHONE_NUMBER} in {LEADS_FILE}")
        exit(1)

    logging.info(f"Found lead to call: {lead_to_call.get('name')} ({lead_to_call.get('mobile_no')})")

    # --- Initialize Caller and Make Call --- #
    try:
        caller = VapiLeadCaller(
            auth_token=VAPI_AUTH_TOKEN,
            assistant_id=VAPI_ASSISTANT_ID,
            phone_number_id=VAPI_PHONE_NUMBER_ID
        )

        placement_result = caller.place_call(lead_to_call)

        if placement_result["success"]:
            call_id = placement_result["call_id"]
            logging.info(f"Call placed successfully. Call ID: {call_id}. Now waiting for completion...")
            # Wait for the call to finish
            final_details = caller.wait_for_call_completion(call_id, timeout=600) # Wait up to 10 minutes

            logging.info("--- FINAL CALL DETAILS ---")
            print(json.dumps(final_details, indent=4))
            logging.info("--- END OF CALL DETAILS ---")
        else:
            logging.error(f"Failed to place call: {placement_result.get('error')}")

    except ValueError as e:
        logging.error(f"Initialization Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)

    logging.info("Vapi Call Test Script Finished.") 