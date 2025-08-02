import re
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Annotated
from enum import Enum

from .mapped_model import Mapped, MappedModel

class MessageType(Enum):
    SYNC_MESSAGE = "sync_message"
    DATA_MESSAGE = "data_message"
    RECEIPT_MESSAGE = "receipt_message"

class User(BaseModel):
    name: Optional[str] = None
    number: Optional[str] = None
    uuid: Optional[str] = None

class Attachment(BaseModel):
    content_type: Optional[str] = Field(alias='contentType', default=None)
    filename: Optional[str] = None
    id: Optional[str] = None
    size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    caption: Optional[str] = None
    upload_timestamp: Optional[int] = Field(alias='uploadTimestamp', default=None)
    thumbnail: Optional['Attachment'] = None

class Group(BaseModel):
    id: str
    internal_id: str = Field(alias='internalId')
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    members: List[User] = []
    admins: List[User] = []
    blocked: bool = False
    inbox_position: Optional[int] = Field(alias='inboxPosition', default=None)
    archived: bool = False

class SendResponse(BaseModel):
    timestamp: str

class ContactUpdate(BaseModel):
    receiver: str
    expiration_in_seconds: Optional[int] = Field(alias='expirationInSeconds', default=None)
    name: Optional[str] = None

class GroupUpdate(BaseModel):
    group_id: str = Field(alias='groupId')
    base64_avatar: Optional[str] = Field(alias='base64Avatar', default=None)
    description: Optional[str] = None
    expiration_in_seconds: Optional[int] = Field(alias='expirationInSeconds', default=None)
    name: Optional[str] = None

class Mention(MappedModel):
    start: int
    length: int
    target: Annotated[User, Mapped({"name": "name", "number": "number", "uuid": "uuid"})]

class Quote(MappedModel):
    source: Annotated[User, Mapped({"name": "author", "number": "authorNumber", "uuid": "authorUuid"})]
    id: int
    text: Optional[str] = None
    attachments: List[Attachment] = []

class Reaction(MappedModel):
    emoji: Optional[str] = None
    target: Annotated[User, Mapped({"name": "targetAuthor", "number": "targetAuthorNumber", "uuid": "targetAuthorUuid"})]
    timestamp: Optional[int] = Field(alias='targetSentTimestamp', default=None)
    is_remove: Optional[bool] = Field(alias='isRemove', default=None)

class GroupInfo(BaseModel):
    id: Optional[str] = Field(alias='groupId', default=None)
    name: Optional[str] = Field(alias='groupName', default=None)
    revision: int
    type: Optional[str] = None

class MessageData(BaseModel):
    timestamp: Optional[int] = None
    message: Optional[str] = None
    expires_in_seconds: int = Field(default=0, alias='expiresInSeconds')
    view_once: bool = Field(default=False, alias='viewOnce')
    attachments: List[Attachment] = []
    reaction: Optional[Reaction] = None
    quote: Optional[Quote] = None
    group_info: Optional[GroupInfo] = Field(alias='groupInfo', default=None)
    mentions: List[Mention] = []

class Message(MappedModel):
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )
    
    type: MessageType
    source: Annotated[User, Mapped({"name": "sourceName", "number": "sourceNumber", "uuid": "sourceUuid"})]
    server_received_timestamp: int = Field(alias='serverReceivedTimestamp', default=None)
    server_delivered_timestamp: int = Field(alias='serverDeliveredTimestamp', default=None)
    data: MessageData

    def is_group(self) -> bool:
        return self.data.group_info is not None
    
    def is_private(self) -> bool:
        return not self.is_group()
    
    def recipient(self) -> str:
        """Return the recipient (group ID or user number/UUID)"""
        if self.is_group():
            return self.data.group_info.id
        return self.source.number or self.source.uuid or self.source.name
    
    @property
    def group(self) -> Optional[GroupInfo]:
        """Alias for backward compatibility"""
        return self.data.group_info
    
    @property
    def text(self) -> Optional[str]:
        """Alias for message text"""
        return self.data.message
    
    @property
    def timestamp(self) -> Optional[int]:
        """Message timestamp"""
        return self.data.timestamp

class SendMessageRequest(BaseModel):
    receiver: str
    text: str
    base64_attachments: Optional[List[str]] = Field(alias='base64Attachments', default=None)
    quote_author: Optional[str] = Field(alias='quoteAuthor', default=None)
    quote_mentions: Optional[List[dict]] = Field(alias='quoteMentions', default=None)
    quote_message: Optional[str] = Field(alias='quoteMessage', default=None)
    quote_timestamp: Optional[str] = Field(alias='quoteTimestamp', default=None)
    mentions: Optional[List[dict]] = None
    text_mode: Optional[str] = Field(alias='textMode', default=None)

class ReactionRequest(BaseModel):
    recipient: str
    emoji: str
    target_author: str = Field(alias='targetAuthor')
    timestamp: int

class ReceiptRequest(BaseModel):
    recipient: str
    receipt_type: str = Field(alias='receiptType')
    timestamp: int

class TypingRequest(BaseModel):
    receiver: str
