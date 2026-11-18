from .imapclient import IMAPClient as IMAPClient
from typing import Any
from unittest.mock import Mock

class TestableIMAPClient(IMAPClient):
    def __init__(self) -> None: ...

class MockIMAP4(Mock):
    use_uid: bool
    sent: bytes
    tagged_commands: dict[Any, Any]
    untagged_responses: dict[Any, Any]
    capabilities: list[str]
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def send(self, data: bytes) -> None: ...
