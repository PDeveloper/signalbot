import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .types import Attachment

class MessageType(Enum):
    SYNC_MESSAGE = 1
    DATA_MESSAGE = 2

def _parse_attachment(d:dict) -> Attachment:
    content_type = d.get('contentType')
    filename = d.get('filename')
    id = d.get('id')
    size = int(d['size']) if d.get('size') else None
    width = int(d['width']) if d.get('width') else None
    height = int(d['height']) if d.get('height') else None
    caption = d.get('caption')
    upload_timestamp = int(d['uploadTimestamp']) if d.get('uploadTimestamp') else None
    thumbnail = _parse_attachment(d['thumbnail']) if d.get('thumbnail') else None
    return Attachment(content_type=content_type, filename=filename,id=id, size=size, width=width, height=height,
                      upload_timestamp=upload_timestamp, caption=caption, thumbnail=thumbnail)

def _parse_attachments(attachments: list) -> list:
    return [_parse_attachment(attachment) for attachment in attachments]

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
class User:
    name: str = None
    number: str = None
    uuid: str = None

@dataclass
class Message:
    source: str
    source_number: str
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

def parse_header(d:dict):
    return User(
        d.get('sourceName'),
        d.get('sourceNumber'),
        d.get('sourceUuid')
    )

@dataclass
class Quote:
    source: User
    timestamp: int
    text: str = None
    attachments: list[Attachment] = field(default_factory=list)

def _parse_quote(d:dict):
    timestamp = int(d.get('id'))
    name = d.get('author', None)
    number = d.get('authorNumber', None)
    uuid = d.get('authorUuid', None)
    text = d.get('text')
    attachments = _parse_attachments(d.get('attachments', []))
    return Quote(source=User(name, number, uuid), timestamp=timestamp, text=text, attachments=attachments)

@dataclass
class Reaction:
    emoji: str
    target: User
    timestamp: int
    is_remove: bool

def _parse_reaction(d:dict) -> Reaction:
    emoji = d.get('emoji')
    target_author = d.get('targetAuthor')
    target_author_number = d.get('targetAuthorNumber')
    target_author_uuid = d.get('targetAuthorUuid')
    target_sent_timestamp = d.get('targetSentTimestamp')
    is_remove = d.get('isRemove')
    return Reaction(emoji=emoji, target=User(target_author, target_author_number, target_author_uuid), timestamp=target_sent_timestamp, is_remove=is_remove)

@dataclass
class GroupInfo:
    id: str
    name: str
    revision: int
    type: str

def _parse_group_info(d:dict):
    id = d.get('groupId')
    name = d.get('groupName')
    revision = int(d.get('revision'))
    type = d.get('type')
    return GroupInfo(id, name, revision, type)

def parse_message(d:dict):
    timestamp = d.get('timestamp')
    message = d.get('message')
    expires_in_seconds = d.get('expiresInSeconds', 0)
    view_once = d.get('viewOnce', False)
    attachments = _parse_attachments(d.get('attachments'), [])
    reaction = _parse_reaction(d['reaction']) if d.get('reaction') else None
    quote = _parse_quote(d['quote']) if d.get('quote') else None
    group_info = _parse_group_info(d['groupInfo']) if d.get('groupInfo') else None

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
    attachments = _parse_attachments(message_data.get('attachments', []))

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
