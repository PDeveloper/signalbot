import json
from pydantic import ValidationError
from .types import *

def parse_envelope(data: dict) -> Optional[Message]:
    envelope: dict = data['envelope']
    message_data: dict = None
    
    if "syncMessage" in envelope:
        type = MessageType.SYNC_MESSAGE
        message_data = envelope.pop("syncMessage")["sentMessage"]
    elif "dataMessage" in envelope:
        type = MessageType.DATA_MESSAGE
        message_data = envelope.pop("dataMessage")
    elif "receiptMessage" in envelope:
        type = MessageType.RECEIPT_MESSAGE
        return None  # Handle receipt messages separately if needed
    
    if not message_data:
        return None

    # Combine envelope and message data
    combined_data = {
        **envelope,
        'type': type,
        'data': message_data,
    }

    try:
        return Message(**combined_data)
    except ValidationError as e:
        print(f"Failed to parse message: {e}")
        return None

def message_from_json(data: dict) -> Optional[Message]:
    try:
        return parse_envelope(data)
    except (json.JSONDecodeError, ValidationError):
        print("Error decoding JSON or validating message format.")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

class UnknownMessageFormatError(Exception):
    pass
