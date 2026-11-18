import imaplib

class IMAP4WithTimeout(imaplib.IMAP4):
    def __init__(self, address: str, port: int, timeout: float | None) -> None: ...
