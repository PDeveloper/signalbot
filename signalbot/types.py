from dataclasses import dataclass
from .api import SignalAPI

@dataclass
class Attachment:
    content_type: str
    filename: str = None
    id: str
    size: int
    width: int
    height: int
    caption: str = None
    upload_timestamp: int
    thumbnail: 'Attachment' = None

    data: bytes = None

    async def download(self, signal: SignalAPI) -> bytes:
        self.data = await signal.get_attachment_bytes(self.id)
        return self.data
