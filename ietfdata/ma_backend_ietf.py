# Copyright (C) 2026 University of Glasgow
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from ietfdata.ma_backend import *
from imapclient          import IMAPClient
from typing              import Any, Dict

class MailArchiveBackendIETF(MailArchiveBackend):
    _imap           : IMAPClient | None
    _imap_server    : str
    _mailbox        : str
    _mailbox_prefix : str
    _mailbox_path   : str
    _mailbox_info   : Dict[bytes,Any]

    def __init__(self):
        self._imap_server = "imap.ietf.org"
        self._imap        = None


    def mailboxes(self) -> List[str]:
        with IMAPClient(host=self._imap_server, ssl=True, use_uid=True) as imap:
            imap.login("anonymous", "anonymous")

            _, _, imap_ns_shared = imap.namespace()
            imap_prefix    = imap_ns_shared[0][0]
            imap_separator = imap_ns_shared[0][1]
            folder_list    = imap.list_folders()

        mailboxes = []
        for (flags, delimiter, folder_path) in folder_list:
            if b'\\Noselect' in flags:
                continue
            name = folder_path.split(imap_separator)[-1]
            mailboxes.append(name)
        return mailboxes


    def open_mailbox(self, mailbox: str) -> None:
        self._mailbox = mailbox
        self._imap = IMAPClient(self._imap_server, ssl=True, use_uid=True)
        self._imap.login("anonymous", "anonymous")

        _, _, imap_ns_shared = self._imap.namespace()

        self._mailbox_prefix = imap_ns_shared[0][0]
        self._mailbox_path   = f"{self._mailbox_prefix}{self._mailbox}"
        self._mailbox_info   = self._imap.select_folder(self._mailbox_path, readonly=True)


    def close_mailbox(self) -> None:
        assert self._imap is not None
        self._imap.logout()
        self._imap = None


    def validity(self) -> int:
        assert self._imap is not None
        return int(self._mailbox_info[b'UIDVALIDITY'])


    def message_ids(self) -> List[int]:
        assert self._imap is not None
        return list(self._imap.search('NOT DELETED'))


    def fetch(self, message_ids: List[int]) -> Iterator[Tuple[int, str]]:
        assert self._imap is not None
        for uid, msg in self._imap.fetch(message_ids, "INTERNALDATE RFC822.SIZE RFC822").items():
            yield(uid, msg[b"RFC822"])

