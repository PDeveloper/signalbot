import re
from pydantic import BaseModel, Field, ConfigDict, AliasPath
from typing import Optional, List, Annotated, Literal, Self
import base64
from enum import Enum

from .mapped_model import Mapped, MappedModel

class MessageType(Enum):
    SYNC = "sync"
    DATA = "data"
    RECEIPT = "receipt"
    TYPING = "typing"
    UNKNOWN = "unknown"

class ReceiptType(Enum):
    READ = "read"
    VIEWED = "viewed"

class AccountInternalInfo(BaseModel):
    version: int
    timestamp: int
    serviceEnvironment: str
    registered: bool
    number: str
    username: str
    deviceId: int

class AccountInfo(BaseModel):
    path: str
    environment: str
    number: str
    uuid: str

    username: Optional[str] = None
    device_id: Optional[int] = None

class AccountList(BaseModel):
    accounts: List[AccountInfo]
    version: int

class Group(BaseModel):
    name: str
    description: str
    id: str
    internal_id: str
    members: List[str]
    blocked: bool
    pending_invites: List[str]
    pending_requests: List[str]
    invite_link: str
    admins: List[str]

class ContactProfile(BaseModel):
    given_name: str
    lastname: str
    about: str
    has_avatar: bool
    last_updated_timestamp: int

class ContactNickname(BaseModel):
    name: str
    given_name: str
    family_name: str

class Contact(BaseModel):
    name: str
    number: str
    uuid: str
    profile_name: str
    username: str
    color: str
    blocked: bool
    message_expiration: str
    note: str
    profile: ContactProfile
    given_name: str
    nickname: ContactNickname

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
    id: str = Field(alias='groupId')
    name: Optional[str] = Field(alias='groupName', default=None)
    revision: int
    type: Optional[str] = None

    def public_id(self) -> str:
        return f'group.{base64.b64encode(self.id.encode()).decode()}'

class RemoteDelete(BaseModel):
    timestamp: int

class DataMessage(BaseModel):
    timestamp: Optional[int] = None
    message: Optional[str] = None
    expires_in_seconds: int = Field(default=0, alias='expiresInSeconds')
    view_once: bool = Field(default=False, alias='viewOnce')
    attachments: List[Attachment] = []
    reaction: Optional[Reaction] = None
    quote: Optional[Quote] = None
    group_info: Optional[GroupInfo] = Field(alias='groupInfo', default=None)
    mentions: List[Mention] = []
    remote_delete: Optional[RemoteDelete] = Field(alias='remoteDelete', default=None)

class ReceiptMessage(BaseModel):
    when: int
    is_delivery: bool = Field(alias='isDelivery', default=False)
    is_read: bool = Field(alias='isRead', default=False)
    is_viewed: bool = Field(alias='isViewed', default=False)
    timestamps: List[int] = []

class TypingMessage(BaseModel):
    action: str
    timestamp: int
    group_id: Optional[str] = Field(alias='groupId', default=None)

### REST API MODELS

class GroupPermissions(BaseModel):
    add_members: Literal["only-admins", "every-member"] = "only-admins"
    edit_group: Literal["only-admins", "every-member"] = "only-admins"

class GroupCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    members: List[str] = []
    expiration_time: Optional[int] = None
    group_link: Optional[Literal["disabled", "enabled", "enabled-with-approval"]] = "disabled"
    permissions: GroupPermissions = Field(default_factory=GroupPermissions)

class GroupUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base64_avatar: Optional[str] = None
    expiration_time: Optional[int] = None
    group_link: Optional[Literal["disabled", "enabled", "enabled-with-approval"]] = "disabled"

class ReactionRequest(BaseModel):
    recipient: str
    reaction: str
    target_author: str
    timestamp: int = 0

class ReceiptRequest(BaseModel):
    receipt_type: Literal["read", "viewed"] = "read"
    recipient: str
    timestamp: int = 0

class TypingRequest(BaseModel):
    recipient: str

### MAIN MESSAGE CLASS

class Message(MappedModel):
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )
    
    source: str
    user: Annotated[User, Mapped({"name": "sourceName", "number": "sourceNumber", "uuid": "sourceUuid"})]
    sourceDevice: int

    timestamp: int
    server_received_timestamp: int = Field(alias='serverReceivedTimestamp', default=None)
    server_delivered_timestamp: int = Field(alias='serverDeliveredTimestamp', default=None)

    data: Optional[DataMessage] = Field(alias='dataMessage', default=None)
    sync: Optional[DataMessage] = Field(validation_alias=AliasPath('syncMessage', 'sentMessage'), default=None)
    receipt: Optional[ReceiptMessage] = Field(alias='receiptMessage', default=None)
    typing: Optional[TypingMessage] = Field(alias='typingMessage', default=None)

    def type(self) -> MessageType:
        if self.data is not None:
            return MessageType.DATA
        elif self.sync is not None:
            return MessageType.SYNC
        elif self.receipt is not None:
            return MessageType.RECEIPT
        elif self.typing is not None:
            return MessageType.TYPING
        else:
            return MessageType.UNKNOWN

    def is_group(self) -> bool:
        return self.data is not None and self.data.group_info is not None
    
    def is_private(self) -> bool:
        return not self.is_group()
    
    def recipient(self) -> str:
        """Return the recipient (group ID or user number/UUID)"""
        if self.is_group():
            return self.data.group_info.public_id()
        return self.user.uuid or self.user.number
    
    @property
    def group(self) -> Optional[GroupInfo]:
        """Alias for backward compatibility"""
        if self.data is None:
            return None
        return self.data.group_info
    
    @property
    def text(self) -> Optional[str]:
        """Alias for message text"""
        if self.data is None:
            return None
        return self.data.message

class LinkPreview(BaseModel):
    base64_thumbnail: Optional[str] = None
    description: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None

class SendMessageMention(BaseModel):
    author: str
    length: int = 0
    start: int = 0

class SendMessageRequest(BaseModel):
    number: str
    recipients: List[str]
    message: Optional[str] = None
    base64_attachments: Optional[List[str]] = None
    quote_author: Optional[str] = None
    quote_mentions: Optional[List[SendMessageMention]] = None
    quote_message: Optional[str] = None
    quote_timestamp: Optional[int] = None
    mentions: Optional[List[SendMessageMention]] = None
    sticker: Optional[str] = None
    edit_timestamp: Optional[int] = None
    view_once: bool = False
    notify_self: Optional[bool] = None
    text_mode: Optional[str] = None
    link_preview: Optional[LinkPreview] = None

    timestamp: Optional[int] = None  # Filled in response

    def reply(self, message: Message) -> Self:
        self.quote_author = message.source
        self.quote_message = message.data.message if message.data and message.data.message is not None else ""
        self.quote_timestamp = message.timestamp
        self.quote_mentions = [SendMessageMention(author=m.target.uuid or m.target.number, start=m.start, length=m.length) for m in message.data.mentions] if message.data else []
        return self

def request_to_message(request: SendMessageRequest, info: AccountInfo) -> Message:
    """Convert SendMessageRequest to Message format for easier processing"""
    return Message(
        source=info.number,
        user=User(name=None, number=info.number, uuid=info.uuid),
        sourceDevice=info.device_id or 0,
        timestamp=request.timestamp or 0,
        data=DataMessage(
            message=request.message,
            attachments=[Attachment(base64_thumbnail=None, caption=None, content_type=None, filename=None, height=None, id=None, size=None, upload_timestamp=None, width=None)] if request.base64_attachments else [],
            quote=Quote(
                id=request.quote_timestamp or 0,
                source=User(name=None, number=request.quote_author, uuid=None),
                message=request.quote_message,
                attachments=[]
            ) if request.quote_author and request.quote_timestamp else None,
            mentions=[Mention(start=m.start, length=m.length, target=User(name=None, number=None, uuid=m.author)) for m in request.mentions] if request.mentions else []
        )
    )
