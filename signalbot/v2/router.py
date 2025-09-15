import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
import time
import traceback
from typing import Protocol, Callable

from pydantic import ValidationError

from .api import SignalAPI, SignalAccountAPI, MessageContext
from .utils import rerun_on_exception, store_reference_to_task
from ..types import AccountList, AccountInternalInfo, AccountInfo, Message, Contact, Group, SendMessageRequest

logger = logging.getLogger(__name__)

class SignalMessageFilter(Protocol):
    def filter(self, phone_number: str, message: Message) -> bool:
        ...

class SignalAccount:
    def __init__(self, api: SignalAPI, info: AccountInfo):
        self.api = SignalAccountAPI(api, info.number)
        self.info = info

        self.contacts: list[Contact] = []
        self.groups: list[Group] = []
    
    async def refresh(self) -> None:
        self.contacts = await self.api.contacts()
        self.groups = await self.api.groups()
    
@dataclass
class SignalListenerFilter:
    contacts: list[str] | bool = False
    groups: list[str] | bool = False
    filter: Callable[[MessageContext], bool] | None = None

class SignalMessageListener(Protocol):
    async def handle(self, context: MessageContext) -> None:
        ...

def _filter_message(filter: SignalListenerFilter, context: MessageContext) -> bool:
    if context.message.is_group():
        if type(filter.groups) is bool:
            return filter.groups
        group_id = context.message.data.group_info.public_id()
        if group_id not in filter.groups:
            return False
    else:
        if type(filter.contacts) is bool:
            return filter.contacts
        if context.message.user.uuid not in filter.contacts:
            return False
    if filter.filter and not filter.filter(context):
        return False
    return True
    
class SignalRouter:
    def __init__(self, url: str, directory: Path = Path('signal-cli-config'), filter: SignalMessageFilter = None, on_message_sent: Callable[[SendMessageRequest], None] = None):
        self.api = SignalAPI(url, on_message_sent=on_message_sent)
        self.directory = directory
        self.filter = filter

        self.accounts: dict[str, SignalAccount] = {}
        self.listeners: dict[str, list[tuple[SignalListenerFilter, SignalMessageListener]]] = {}
        self.refresh_accounts()

        self._q = asyncio.Queue()
        self._consume_tasks: set[asyncio.Task] = set()

    def register(self, source: list[str] | str, listener: SignalMessageListener, contacts: list[str] | bool = False, groups: list[str] | bool = False, filter: Callable[[MessageContext], bool] | None = None) -> None:
        if type(source) is str:
            source = [source]
        for phone_number in source:
            if phone_number not in self.accounts:
                logger.error(f"Cannot register listener for unknown Signal account {phone_number}")
            self.listeners[phone_number].append((SignalListenerFilter(contacts, groups, filter), listener))

    def unregister(self, source: list[str] | str, listener: SignalMessageListener) -> None:
        if type(source) is str:
            source = [source]
        for phone_number in source:
            if phone_number not in self.accounts:
                logger.error(f"Cannot unregister listener for unknown Signal account {phone_number}")
            self.listeners[phone_number] = [l for l in self.listeners[phone_number] if l[1] != listener]

    def refresh_accounts(self) -> None:
        accounts_json_path = self.directory / 'data' / 'accounts.json'
        if accounts_json_path.exists():
            try:
                accounts_str = accounts_json_path.read_text(encoding='utf-8')
                accounts = AccountList.model_validate_json(accounts_str)
                for account_info in accounts.accounts:
                    if account_info.number not in self.accounts:
                        account_profile_info_path = self.directory / 'data' / account_info.path
                        account_profile_info = AccountInternalInfo.model_validate_json(account_profile_info_path.read_text(encoding='utf-8'))
                        account_info.username = account_profile_info.username
                        account_info.device_id = account_profile_info.deviceId
                        account = SignalAccount(self.api, account_info)
                        self.accounts[account_info.number] = account
                        self.listeners[account_info.number] = []
                logger.info(f"{len(self.accounts)} Signal accounts loaded")
            except Exception as e:
                logger.error(f"Cannot read accounts from {accounts_json_path}: {e}")

    async def wait_available(self) -> None:
        while (await self.api.health()) is False:
            logger.error(f"Cannot connect to Signal at {self.api.url}, retrying")
            await asyncio.sleep(1)

    async def start(self) -> None:
        await self.wait_available()
        logger.info(f"Connected to Signal at {self.api.url}")
        
        for account in self.accounts.values():
            await account.refresh()

        await self._produce_consume_messages()
        await asyncio.gather(*self._consume_tasks)

    async def _produce_consume_messages(self, consumers=3) -> None:
        for task in self._consume_tasks:
            task.cancel()

        self._consume_tasks.clear()

        for n in range(1, consumers + 1):
            consume_task = rerun_on_exception(self._consume, n)
            consume_task = asyncio.create_task(consume_task)
            store_reference_to_task(consume_task, self._consume_tasks)

    async def _consume(self, name: int) -> None:
        logging.info(f"[Bot] Consumer #{name} started")
        while True:
            try:
                await self._consume_new_item(name)
            except Exception:
                continue

    async def _consume_new_item(self, name: int) -> None:
        job = await self._q.get()
        try:
            phone_number: str = job[0]
            message: Message = job[1]
            t: float = job[2]

            now = time.perf_counter()
            logging.info(f"[Bot] Consumer #{name} got new job in {now-t:0.5f} seconds")
            
            account = self.accounts[phone_number]
            context = MessageContext(account.api, account.info, message)

            for filter, listener in self.listeners[phone_number]:
                if not _filter_message(filter, context):
                    continue
                try:
                    await listener.handle(context)
                except Exception as e:
                    for log in "".join(traceback.format_exception(e)).rstrip().split("\n"):
                        logging.error(f"[Listener][{account.info.number}] {log}")
                    raise e
        finally:
            self._q.task_done()

    async def on_json_message(self, account: str, data: dict) -> None:
        if not account in self.accounts:
            logging.error(f"[Bot] Unknown account for phone number {account}, skipping message")
            return
        
        try:
            message = Message(**data)
            if not message:
                return None
        except ValidationError as e:
            logger.error(f"[Bot] UnknownMessageFormatError: {e}")
            return None

        if self.filter and not self.filter.filter(account, message):
            return
        
        await self._q.put((account, message, time.perf_counter()))
