import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .types import *

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

def _parse_source(d:dict):
    return User(
        d.get('sourceName'),
        d.get('sourceNumber'),
        d.get('sourceUuid')
    )

def _parse_quote(d:dict):
    timestamp = int(d.get('id'))
    name = d.get('author', None)
    number = d.get('authorNumber', None)
    uuid = d.get('authorUuid', None)
    text = d.get('text')
    attachments = _parse_attachments(d.get('attachments', []))
    return Quote(source=User(name, number, uuid), timestamp=timestamp, text=text, attachments=attachments)

def _parse_reaction(d:dict) -> Reaction:
    emoji = d.get('emoji')
    target_author = d.get('targetAuthor')
    target_author_number = d.get('targetAuthorNumber')
    target_author_uuid = d.get('targetAuthorUuid')
    target_sent_timestamp = d.get('targetSentTimestamp')
    is_remove = d.get('isRemove')
    return Reaction(emoji=emoji, target=User(target_author, target_author_number, target_author_uuid), timestamp=target_sent_timestamp, is_remove=is_remove)

def _parse_group_info(d:dict):
    id = d.get('groupId')
    name = d.get('groupName')
    revision = int(d.get('revision'))
    type = d.get('type')
    return GroupInfo(id, name, revision, type)

def _parse_mention(d: dict):
    start = int(d['start'])
    length = int(d['length'])
    return Mention(start=start, length=length, target=User(d['name'], d['number'], d['uuid']))

def _parse_mentions(mentions: list):
    return [_parse_mention(mention) for mention in mentions]

def parse_envelope(data:dict):
    envelope = data['envelope']
    message_data:dict = None
    if "syncMessage" in envelope:
        type = MessageType.SYNC_MESSAGE
        message_data = envelope["syncMessage"]["sentMessage"]
    elif "dataMessage" in envelope:
        type = MessageType.DATA_MESSAGE
        message_data = envelope["dataMessage"]
    
    if not message_data:
        return None

    source = _parse_source(envelope)
    timestamp = message_data.get('timestamp')
    text = message_data.get('message')
    expires_in_seconds = message_data.get('expiresInSeconds', 0)
    view_once = message_data.get('viewOnce', False)
    attachments = _parse_attachments(message_data.get('attachments', []))
    reaction = _parse_reaction(message_data['reaction']) if message_data.get('reaction') else None
    quote = _parse_quote(message_data['quote']) if message_data.get('quote') else None
    group_info = _parse_group_info(message_data['groupInfo']) if message_data.get('groupInfo') else None
    mentions = _parse_mentions(message_data['mentions']) if message_data.get('mentions') else None

    return Message(
        type=type,
        source=source,
        timestamp=timestamp,
        text=text,
        expires_in_seconds=expires_in_seconds,
        view_once=view_once,
        attachments=attachments,
        reaction=reaction,
        quote=quote,
        group_info=group_info,
        mentions=mentions,

        raw_message=data
    )

def message_from_json(json_string: str) -> Message:
    try:
        data = json.loads(json_string)
        return parse_envelope(data)
    except Exception:
        raise UnknownMessageFormatError
    return None

class UnknownMessageFormatError(Exception):
    pass
