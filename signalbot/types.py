from dataclasses import dataclass
from .api import SignalAPI

@dataclass
class Attachment:
    id: str
    size: int
    contentType: str
    width: int
    height: int
    uploadTimestamp: int
    filename: str = None
    caption: str = None

    data: bytes = None

    async def download(self, signal: SignalAPI) -> bytes:
        self.data = await signal.get_attachment_bytes(self.id)
        return self.data
