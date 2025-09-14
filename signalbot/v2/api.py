import httpx

import base64
from typing import Callable, Literal, List

from ..types import SendMessageRequest, SendMessageMention, Group, GroupCreateRequest, GroupUpdateRequest, Contact, Message, Mention, AccountInfo, LinkPreview

class SignalAPI:
    def __init__(self, url: str, on_message_sent: Callable[[SendMessageRequest], None] = None):
        self.url = url
        self.on_message_sent = on_message_sent

        self.client = httpx.AsyncClient(base_url=url, timeout=30.0)
    
    async def init(self) -> None:
        accounts = await self.accounts()
        print(accounts)
    
    async def health(self) -> bool:
        try:
            response = await self.client.get("/v1/health")
            response.raise_for_status()
            return True
        except Exception:
            return False

    async def qr_code(self, device_name: str) -> tuple[str, bytes]:
        response = await self.client.get("/v1/qrcodelink", params={
            "device_name": device_name
        })
        response.raise_for_status()
        return response.headers.get("Content-Type", ""), response.content

    async def accounts(self) -> list[str]:
        response = await self.client.get("/v1/accounts")
        response.raise_for_status()
        return response.json()

    ### ATTACHMENTS

    async def attachments(self) -> list[str]:
        response = await self.client.get(f"/v1/attachments")
        response.raise_for_status()
        return response.json()

    async def attachment(self, id: str) -> tuple[str, bytes]:
        response = await self.client.get(f"/v1/attachments/{id}")
        response.raise_for_status()
        return response.headers.get("Content-Type", ""), response.content

    async def delete_attachment(self, id: str) -> None:
        response = await self.client.delete(f"/v1/attachments/{id}")
        response.raise_for_status()

class SignalAccountAPI:
    def __init__(self, api: SignalAPI, phone_number: str):
        self.api = api
        self.phone_number = phone_number

        self.client = api.client

    async def update_profile(self, name: str = None, about: str = None, base64_avatar: str = None) -> None:
        await self.client.put(f"/v1/profiles/{self.phone_number}", json={"name": name, "about": about, "avatar": base64_avatar})
    
    ### GROUPS

    async def groups(self) -> list[Group]:
        response = await self.client.get(f"/v1/groups/{self.phone_number}")
        response.raise_for_status()
        return [Group(**item) for item in response.json()]

    async def group(self, group_id: str) -> Group:
        response = await self.client.get(f"/v1/groups/{self.phone_number}/{group_id}")
        response.raise_for_status()
        return Group(**response.json())

    async def create_group(self, request: GroupCreateRequest) -> str:
        response = await self.client.post(f"/v1/groups/{self.phone_number}", json=request.model_dump(by_alias=True, exclude_none=True))
        response.raise_for_status()
        return response.json().get("id", "")

    async def update_group(self, group_id: str, request: GroupUpdateRequest) -> None:
        response = await self.client.put(f"/v1/groups/{self.phone_number}/{group_id}", json=request.model_dump(by_alias=True, exclude_none=True))
        response.raise_for_status()

    async def delete_group(self, group_id: str) -> None:
        response = await self.client.delete(f"/v1/groups/{self.phone_number}/{group_id}")
        response.raise_for_status()
    
    async def group_avatar(self, group_id: str) -> tuple[str, bytes]:
        response = await self.client.get(f"/v1/groups/{self.phone_number}/{group_id}/avatar")
        response.raise_for_status()
        return response.headers.get("Content-Type", ""), response.content

    async def add_group_admins(self, group_id: str, admins: list[str]) -> None:
        response = await self.client.post(f"/v1/groups/{self.phone_number}/{group_id}/admins", json={"admins": admins})
        response.raise_for_status()

    async def remove_group_admins(self, group_id: str, admins: list[str]) -> None:
        response = await self.client.delete(f"/v1/groups/{self.phone_number}/{group_id}/admins", json={"admins": admins})
        response.raise_for_status()
    
    async def add_group_members(self, group_id: str, members: list[str]) -> None:
        response = await self.client.post(f"/v1/groups/{self.phone_number}/{group_id}/members", json={"members": members})
        response.raise_for_status()
    
    async def remove_group_members(self, group_id: str, members: list[str]) -> None:
        response = await self.client.delete(f"/v1/groups/{self.phone_number}/{group_id}/members", json={"members": members})
        response.raise_for_status()

    ### MESSAGES

    async def typing_start(self, recipient: str) -> None:
        await self.client.put(f"/v1/typing-indicator/{self.phone_number}", json={"recipient": recipient})
    
    async def typing_stop(self, recipient: str) -> None:
        await self.client.delete(f"/v1/typing-indicator/{self.phone_number}", json={"recipient": recipient})

    async def send(self,
                   recipient: str,
                   message: str = None,
                   attachments: List[str|tuple[str, str|bytes]|tuple[str, str, str|bytes]] = [],
                   mentions: List[Mention] = [],
                   view_once: bool = False,
                   notify_self: bool = None,
                   text_mode: str = None,
                   link_preview: LinkPreview = None) -> int:
        request = SendMessageRequest(
            number=self.phone_number,
            recipients=[recipient],
            message=message,
            base64_attachments=_attachments_to_base64(attachments),
            mentions=_mentions_to_requests(mentions),
            view_once=view_once,
            notify_self=notify_self,
            text_mode=text_mode,
            link_preview=link_preview,
        )
        return await self.send_request(request)

    async def reply(self, quote: Message,
                   message: str = None,
                   attachments: List[str|tuple[str, str|bytes]|tuple[str, str, str|bytes]] = [],
                   mentions: List[Mention] = [],
                   view_once: bool = False,
                   notify_self: bool = None,
                   text_mode: str = None,
                   link_preview: LinkPreview = None) -> int:
        request = SendMessageRequest(
            number=self.phone_number,
            recipients=[quote.recipient()],
            message=message,
            base64_attachments=_attachments_to_base64(attachments),
            mentions=_mentions_to_requests(mentions),
            view_once=view_once,
            notify_self=notify_self,
            text_mode=text_mode,
            link_preview=link_preview,
        ).reply(quote)
        return await self.send_request(request)

    async def edit(self, recipient: str, timestamp: int,
                   message: str = None,
                   attachments: List[str|tuple[str, str|bytes]|tuple[str, str, str|bytes]] = [],
                   mentions: List[Mention] = [],
                   view_once: bool = False,
                   notify_self: bool = None,
                   text_mode: str = None,
                   link_preview: LinkPreview = None) -> int:
        request = SendMessageRequest(
            number=self.phone_number,
            recipients=[recipient],
            message=message,
            base64_attachments=_attachments_to_base64(attachments),
            mentions=_mentions_to_requests(mentions),
            view_once=view_once,
            notify_self=notify_self,
            text_mode=text_mode,
            link_preview=link_preview,
            edit_timestamp=timestamp,
        )
        return await self.send_request(request)

    async def send_request(self, request: SendMessageRequest) -> int:
        response = await self.client.post(f"/v2/send", json=request.model_dump(by_alias=True, exclude_none=True))
        response.raise_for_status()
        timestamp = response.json().get("timestamp")
        request.timestamp = timestamp
        if self.api.on_message_sent:
            self.api.on_message_sent(request)
        return request.timestamp

    async def react(self, recipient: str, target_uuid: str, target_timestamp: int, reaction: str) -> None:
        response = await self.client.post(f"/v1/reactions/{self.phone_number}", json={
            "recipient": recipient,
            "reaction": reaction,
            "target_author": target_uuid,
            "timestamp": target_timestamp,
        })
        response.raise_for_status()
    
    async def delete_react(self, recipient: str, target_uuid: str, target_timestamp: int, reaction: str) -> None:
        response = await self.client.delete(f"/v1/reactions/{self.phone_number}", json={
            "recipient": recipient,
            "reaction": reaction,
            "target_author": target_uuid,
            "timestamp": target_timestamp,
        })
        response.raise_for_status()

    async def receipt(self, recipient: str, timestamp: int, receipt_type: Literal["read", "viewed"]) -> None:
        response = await self.client.post(f"/v1/receipts/{self.phone_number}", json={
            "receipt_type": receipt_type,
            "recipient": recipient,
            "timestamp": timestamp,
        })
        response.raise_for_status()

    ### CONTACTS

    async def contacts(self) -> list[Contact]:
        response = await self.client.get(f"/v1/contacts/{self.phone_number}")
        response.raise_for_status()
        return [Contact(**contact) for contact in response.json()]

    async def update_contact(self, name: str, recipient: str, expiration_in_seconds: int) -> None:
        response = await self.client.put(f"/v1/contacts/{self.phone_number}", json={
            "name": name,
            "recipient": recipient,
            "expiration_in_seconds": expiration_in_seconds,
        })
        response.raise_for_status()

def _mentions_to_requests(mentions: List[Mention]) -> List[SendMessageMention]:
    return [SendMessageMention(author=mention.target.uuid or mention.target.number, length=mention.length, start=mention.start) for mention in mentions]

def _attachments_to_base64(attachments: List[str|tuple[str, str|bytes]|tuple[str, str, str|bytes]]) -> List[str]:
    base64_attachments = []
    for attachment in attachments:
        if isinstance(attachment, str):
            base64_attachments.append(attachment)
        elif isinstance(attachment, tuple):
            if len(attachment) == 2:
                content_type, b64data = attachment
                filename = None
            elif len(attachment) == 3:
                content_type, filename, b64data = attachment
            else:
                continue
            if isinstance(b64data, bytes):
                b64data = base64.b64encode(b64data).decode(encoding='utf-8')
            prefix = f'data:{content_type};filename={filename};base64,' if filename else f'data:{content_type};base64,'
            b64data = prefix + b64data
            base64_attachments.append(b64data)
    return base64_attachments

class MessageContext:
    def __init__(self, api: SignalAccountAPI, info: AccountInfo, message: Message):
        self.api = api
        self.info = info
        self.message = message
        self.data = message.data or message.sync

    def _create_send_request(self, message: str = None, attachments: List[str|tuple[str, str|bytes]|tuple[str, str, str|bytes]] = [], mentions: List[Mention] = []) -> SendMessageRequest:
        return SendMessageRequest(
            number=self.info.number,
            recipients=[self.message.recipient()],
            message=message,
            base64_attachments=_attachments_to_base64(attachments),
            mentions=_mentions_to_requests(mentions),
        )

    async def send(self, message: str = None, attachments: List[str|tuple[str, str|bytes]|tuple[str, str, str|bytes]] = [], mentions: List[Mention] = []) -> int:
        """
        Create a SendMessageRequest.
        Attachments can be:
        - base64 string with data URL prefix
        - tuple of (content_type, base64 string or bytes)
        - tuple of (content_type, filename, base64 string or bytes)
        Bytes will be base64-encoded automatically.
        """
        return await self.api.send(self.message.recipient(), message=message, attachments=attachments, mentions=mentions)

    async def reply(self, message: str = None, attachments: List[str|tuple[str, str|bytes]|tuple[str, str, str|bytes]] = [], mentions: List[Mention] = []) -> int:
        """
        Create a SendMessageRequest as a reply to this message (only applies to data messages).
        Attachments can be:
        - base64 string with data URL prefix
        - tuple of (content_type, base64 string or bytes)
        - tuple of (content_type, filename, base64 string or bytes)
        Bytes will be base64-encoded automatically.
        """
        return await self.api.reply(self.message, message=message, attachments=attachments, mentions=mentions)
    
    async def react(self, reaction: str) -> None:
        if self.data is None:
            return
        
        await self.api.react(
            recipient=self.message.recipient(),
            target_uuid=self.message.source,
            target_timestamp=self.message.timestamp,
            reaction=reaction
        )
    
    async def receipt(self, receipt_type: Literal["read", "viewed"]) -> None:
        if self.data is None or self.message.is_group():
            return
        
        await self.api.receipt(
            recipient=self.message.source,
            timestamp=self.message.timestamp,
            receipt_type=receipt_type
        )
    
    async def start_typing(self) -> None:
        await self.api.typing_start(self.message.recipient())
    
    async def stop_typing(self) -> None:
        await self.api.typing_stop(self.message.recipient())
