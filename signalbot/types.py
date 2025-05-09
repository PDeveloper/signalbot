from dataclasses import dataclass, field
from enum import Enum

@dataclass
class User:
    name: str = field(compare=False, default=None)
    number: str = field(compare=False, default=None)
    uuid: str = None

@dataclass
class Attachment:
    content_type: str
    filename: str
    id: str
    size: int
    width: int
    height: int
    caption: str
    upload_timestamp: int

    thumbnail: 'Attachment' = None

class MessageType(Enum):
    SYNC_MESSAGE = 1
    DATA_MESSAGE = 2
    RECEIPT_MESSAGE = 3

@dataclass
class Quote:
    source: User
    timestamp: int
    text: str = None
    attachments: list[Attachment] = field(default_factory=list)

@dataclass
class Reaction:
    emoji: str
    target: User
    timestamp: int
    is_remove: bool

@dataclass
class GroupInfo:
    id: str
    name: str = field(compare=False)
    revision: int = field(compare=False)
    type: str = field(compare=False)

@dataclass
class Mention:
    start: int
    length: int
    target: User

@dataclass
class Message:
    source: User
    timestamp: int
    type: MessageType
    text: str
    expires_in_seconds: int = 0
    view_once: bool = False
    attachments: list[Attachment] = field(default_factory=list)
    
    group_info: GroupInfo = None
    reaction: Reaction = None
    quote: Quote = None
    mentions: list[Mention] = None

    raw_message: dict = None

    def recipient(self) -> str:
        # Case 1: Group chat
        if self.group_info:
            return self.group_info.id  # internal ID

        # Case 2: User chat
        return self.source.uuid

    def is_private(self) -> bool:
        return not bool(self.group_info)

    def is_group(self) -> bool:
        return bool(self.group_info)

    def __str__(self):
        if self.text is None:
            return ""
        return self.text
