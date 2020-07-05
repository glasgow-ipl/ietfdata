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
from email.message import EmailMessage
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


    def __init__(self, cache_dir: Path, list_name: str):
        self._list_name    = list_name
        self._cache_dir    = cache_dir
        self._cache_folder = Path(self._cache_dir, "mailing-lists", "imap", self._list_name)
        self._cache_folder.mkdir(parents=True, exist_ok=True)


    def name(self) -> str:
        return self._list_name


    def num_messages(self) -> int:
        pass


    def message(self, index:int) -> EmailMessage:
        pass


    def messages(self) -> Iterator[EmailMessage]:
        pass


    def message_from_archive_url(self, url:str) -> EmailMessage:
        pass


    def update(self) -> List[int]:
        new_msgs = []
        imap = IMAPClient(host='imap.ietf.org', ssl=False, use_uid=True)
        imap.login("anonymous", "anonymous")
        imap.select_folder("Shared Folders/" + self._list_name, readonly=True)
        msg_list = imap.search()
        progress = Bar("{:20}".format(self._list_name), max = len(msg_list))
        for msg_id in msg_list:
            progress.next()
            cache_file = Path(self._cache_folder, "{:06d}.msg".format(msg_id))
            if not cache_file.exists():
                msg = imap.fetch(msg_id, ["RFC822"])
                e = email.message_from_bytes(msg[msg_id][b"RFC822"])
                if e["Archived-At"] is not None:
                    mailing_list, message_hash = _parse_archive_url(e["Archived-At"])
                    archive_file = Path(self._cache_dir, "mailing-lists", "arch", "msg", mailing_list, message_hash)
                    archive_file.parent.mkdir(parents=True, exist_ok=True)
                    archive_file.symlink_to(F"../../../imap/{mailing_list}/{msg_id:06}.msg")
                with open(cache_file, "wb") as outf:
                    outf.write(msg[msg_id][b"RFC822"])
                new_msgs.append(msg_id)
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


    def message_from_archive_url(self, archive_url: str) -> EmailMessage:
        if "//www.ietf.org/mail-archive/web/" in archive_url:
            # This is a legacy mail archive URL. If we retrieve it, the
            # server should redirect us to the current archive location.
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

if __name__ == '__main__':
    archive = MailArchive(cache_dir=Path("cache"))
    for ml_name in ["rfced-future", "taps", "rmcat", "secdir"]:
        ml = archive.mailing_list(ml_name)
        ml.update()

    m = archive.message_from_archive_url("http://www.ietf.org/mail-archive/web/secdir/current/msg02466.html")
    print(m)

# vim: set tw=0 ai:
