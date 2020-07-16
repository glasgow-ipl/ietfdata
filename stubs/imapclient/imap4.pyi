import imaplib
from typing import Any

class IMAP4WithTimeout(imaplib.IMAP4):
    def __init__(self, address: Any, port: Any, timeout: Any) -> None: ...
