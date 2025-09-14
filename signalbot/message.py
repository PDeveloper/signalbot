import json
from pydantic import ValidationError
from .types import *

def parse_envelope(data: dict) -> Optional[Message]:
    envelope: dict = data.get("envelope", {})
    account: str = data.get("account", "")
    
    # Combine envelope and message data
    combined_data = {
        **envelope,
        'account': account,
    }

    try:
        return Message(**combined_data)
    except ValidationError as e:
        print(f"Failed to parse message: {e}")
        return None

def message_from_json(data: dict) -> Optional[Message]:
    try:
        return parse_envelope(data)
    except ValidationError:
        print("Error decoding JSON or validating message format.")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

class UnknownMessageFormatError(Exception):
    pass
