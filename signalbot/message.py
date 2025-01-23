import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from .types import Attachment

class MessageType(Enum):
    SYNC_MESSAGE = 1
    DATA_MESSAGE = 2

def _parse_attachments(data_message: dict) -> list:
    if "attachments" not in data_message:
        return []

    return [Attachment(**attachment) for attachment in data_message["attachments"]]

def _parse_message(data_message: dict) -> str:
    try:
        text = data_message["message"]
        return text
    except Exception:
        raise UnknownMessageFormatError

def _parse_group_information(message: dict) -> str:
    try:
        group = message["groupInfo"]["groupId"]
        return group
    except Exception:
        return None

def _parse_mentions(data_message: dict) -> list:
    try:
        mentions = data_message["mentions"]
        return mentions
    except Exception:
        return []

def _parse_reaction(message: dict) -> str:
    try:
        reaction = message["reaction"]["emoji"]
        return reaction
    except Exception:
        return None

@dataclass
class Message:
    source: str
    source_number: Optional[str]
    source_uuid: str
    timestamp: int
    type: MessageType
    text: str
    attachments: list[Attachment] = None
    group: str = None
    reaction: str = None
    mentions: list = None
    raw_message: dict = None

    async def download_attachments(self) -> None:
        await asyncio.gather([attachment.download() for attachment in self.attachments])

    def recipient(self) -> str:
        # Case 1: Group chat
        if self.group:
            return self.group  # internal ID

        # Case 2: User chat
        return self.source

    def is_private(self) -> bool:
        return not bool(self.group)

    def is_group(self) -> bool:
        return bool(self.group)

    def __str__(self):
        if self.text is None:
            return ""
        return self.text

def message_from_json(raw_message: str) -> Message:
    try:
        raw_message = json.loads(raw_message)
    except Exception:
        raise UnknownMessageFormatError

    # General attributes
    try:
        source = raw_message["envelope"]["source"]
        source_uuid = raw_message["envelope"]["sourceUuid"]
        timestamp = raw_message["envelope"]["timestamp"]
    except Exception:
        raise UnknownMessageFormatError

    source_number = raw_message["envelope"].get("sourceNumber")

    # Option 1: syncMessage
    if "syncMessage" in raw_message["envelope"]:
        type = MessageType.SYNC_MESSAGE
        if not "sentMessage" in raw_message["envelope"]["syncMessage"]:
            raise UnknownMessageFormatError
        message_data = raw_message["envelope"]["syncMessage"]["sentMessage"]
    # Option 2: dataMessage
    elif "dataMessage" in raw_message["envelope"]:
        type = MessageType.DATA_MESSAGE
        message_data = raw_message["envelope"]["dataMessage"]
    else:
        raise UnknownMessageFormatError
    
    text = _parse_message(message_data)
    group = _parse_group_information(message_data)
    reaction = _parse_reaction(message_data)
    mentions = _parse_mentions(message_data)
    attachments = _parse_attachments(message_data)

    return Message(
        source=source,
        source_number=source_number,
        source_uuid=source_uuid,
        timestamp=timestamp,
        type=type,
        text=text,
        attachments=attachments,
        group=group,
        reaction=reaction,
        mentions=mentions,
        raw_message=raw_message,
    )

class UnknownMessageFormatError(Exception):
    pass
