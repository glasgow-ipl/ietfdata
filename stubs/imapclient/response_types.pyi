import dataclasses
import datetime
from .typing_imapclient import _Atom
from .util import to_unicode as to_unicode
from typing import Any

@dataclasses.dataclass
class Envelope:
    date: datetime.datetime | None
    subject: bytes
    from_: tuple['Address', ...] | None
    sender: tuple['Address', ...] | None
    reply_to: tuple['Address', ...] | None
    to: tuple['Address', ...] | None
    cc: tuple['Address', ...] | None
    bcc: tuple['Address', ...] | None
    in_reply_to: bytes
    message_id: bytes

@dataclasses.dataclass
class Address:
    name: bytes
    route: bytes
    mailbox: bytes
    host: bytes

class SearchIds(list[int]):
    modseq: int | None
    def __init__(self, *args: Any) -> None: ...

class BodyData(_BodyDataType):
    @classmethod
    def create(cls, response: tuple[_Atom, ...]) -> BodyData: ...
    @property
    def is_multipart(self) -> bool: ...
