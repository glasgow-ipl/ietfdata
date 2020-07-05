# Copyright (C) 2020 University of Glasgow
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

import hashlib
import json
import re
import requests
import email

from datetime      import datetime
from typing        import List, Optional, Tuple, Dict, Iterator, Type, TypeVar, Any
from pathlib       import Path
from email.message import Message
from imapclient    import IMAPClient
from progress.bar  import Bar

# =================================================================================================
# Private helper functions:

def _parse_archive_url(archive_url:str) -> Tuple[str, str]:
    aa_start = archive_url.find("://mailarchive.ietf.org/arch/msg")
    aa_uri   = archive_url[aa_start+33:].strip()

    mailing_list = aa_uri[:aa_uri.find("/")]
    message_hash = aa_uri[aa_uri.find("/")+1:]

    return (mailing_list, message_hash)


# =================================================================================================

class MailingList:
    _list_name    : str
    _cache_dir    : Path
    _cache_folder : Path
    _last_updated : datetime
    _num_messages : int
    _archive_urls : Dict[str, int]


    def __init__(self, cache_dir: Path, list_name: str):
        self._list_name    = list_name
        self._cache_dir    = cache_dir
        self._cache_folder = Path(self._cache_dir, "mailing-lists", self._list_name)
        self._cache_folder.mkdir(parents=True, exist_ok=True)
        self._num_messages = 0
        self._archive_urls = {}
        for msg in self.messages():
            self._num_messages += 1
            if msg["Archived-At"] is not None:
                list_name, msg_hash = _parse_archive_url(msg["Archived-At"])
                self._archive_urls[msg_hash] = self._num_messages


    def name(self) -> str:
        return self._list_name


    def num_messages(self) -> int:
        return self._num_messages


    def message(self, index:int) -> Message:
        cache_file = Path(self._cache_folder, "{:06d}.msg".format(index))
        with open(cache_file, "rb") as inf:
            return email.message_from_binary_file(inf)


    def message_from_archive_url(self, archive_url:str) -> Message:
        list_name, msg_hash = _parse_archive_url(archive_url)
        assert list_name == self._list_name
        return self.message(self._archive_urls[msg_hash])


    def messages(self) -> Iterator[Message]:
        for msg_path in sorted(self._cache_folder.glob("*.msg")):
            with open(msg_path, "rb") as inf:
                yield email.message_from_binary_file(inf)


    def update(self) -> List[int]:
        new_msgs = []
        imap = IMAPClient(host='imap.ietf.org', ssl=False, use_uid=True)
        imap.login("anonymous", "anonymous")
        imap.select_folder("Shared Folders/" + self._list_name, readonly=True)
        msg_list = imap.search()
        progress = Bar("Updating mailing list: {:20}".format(self._list_name), max = len(msg_list))
        for msg_id in msg_list:
            cache_file = Path(self._cache_folder, "{:06d}.msg".format(msg_id))
            if not cache_file.exists() or cache_file.stat().st_size == 0:
                msg = imap.fetch(msg_id, ["RFC822"])
                with open(cache_file, "wb") as outf:
                    outf.write(msg[msg_id][b"RFC822"])
                e = email.message_from_bytes(msg[msg_id][b"RFC822"])
                if e["Archived-At"] is not None:
                    list_name, msg_hash = _parse_archive_url(e["Archived-At"])
                    self._archive_urls[msg_hash] = msg_id
                self._num_messages += 1
                new_msgs.append(msg_id)
            progress.next()

        progress.finish()
        imap.unselect_folder()
        imap.logout()
        self._last_updated = datetime.now()
        return new_msgs


    def last_updated(self) -> datetime:
        return self._last_updated


# =================================================================================================

class MailArchive:
    _cache_dir     : Path
    _mailing_lists : Dict[str,MailingList]


    def __init__(self, cache_dir: Path):
        self._cache_dir     = cache_dir
        self._mailing_lists = {}


    def mailing_list_names(self) -> Iterator[str]:
        imap = IMAPClient(host='imap.ietf.org', ssl=False, use_uid=True)
        imap.login("anonymous", "anonymous")
        for (flags, delimiter, name) in imap.list_folders():
            if name != "Shared Folders":
                assert name.startswith("Shared Folders/")
                yield name[15:]
        imap.logout()


    def mailing_list(self, mailing_list_name: str) -> MailingList:
        if not mailing_list_name in self._mailing_lists:
            self._mailing_lists[mailing_list_name] = MailingList(self._cache_dir, mailing_list_name)
        return self._mailing_lists[mailing_list_name]


    def message_from_archive_url(self, archive_url: str) -> Message:
        if "//www.ietf.org/mail-archive/web/" in archive_url:
            # This is a legacy mail archive URL. If we retrieve it, the
            # server should redirect us to the current archive location.
            # Unfortunately this will then fail, because messages in the
            # legacy archive are missing the "Archived-At:" header.
            print(archive_url)
            response = requests.get(archive_url)
            assert "//mailarchive.ietf.org/arch/msg" in response.url
            return self.message_from_archive_url(response.url)
        elif "//mailarchive.ietf.org/arch/msg" in archive_url:
            list_name, _ = _parse_archive_url(archive_url)
            mailing_list = self.mailing_list(list_name)
            return mailing_list.message_from_archive_url(archive_url)
        else:
            raise RuntimeError("Cannot resolve mail archive URL")
        

    # Formal messages that can be searched for:
    # - "I-D Action:"
    # - "Document Action:"
    # - "Protocol Action:"
    # - "WG Action:"
    # - "WG Review:"
    # - "Last Call:"
    # - "<wg name> Virtual Meeting"
    # - "RFCxxxx on"
    # - RFC errata announcements
    # - <directorate> last call review
    # - <directorate> telechat review 
    # - IESG ballot position announcements
    # (all sometime preceded by "Correction:" or "REVISED")
    # From: addresses have varied over time
    # many of these will need to be implemented in a helper class, that
    # has access to the datatracker, RFC index, and mailing list archives.

# =================================================================================================
# vim: set tw=0 ai:
