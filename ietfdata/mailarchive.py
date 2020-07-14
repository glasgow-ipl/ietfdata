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
import ietfdata.datatracker as dt

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
        self._num_messages = len(list(self._cache_folder.glob("*.msg")))
        self._archive_urls = {}

        aa_cache     = Path(self._cache_folder, "aa-cache.json")
        aa_cache_tmp = Path(self._cache_folder, "aa-cache.json.tmp")
        if aa_cache.exists():
            with open(aa_cache, "r") as cache_file:
                self._archive_urls = json.load(cache_file)
        else:
            msg_id = 0
            for msg in self.messages():
                msg_id += 1
                if msg["Archived-At"] is not None:
                    list_name, msg_hash = _parse_archive_url(msg["Archived-At"])
                    self._archive_urls[msg_hash] = msg_id
            with open(aa_cache_tmp, "w") as cache_file:
                json.dump(self._archive_urls, cache_file, indent=4)
            aa_cache_tmp.rename(aa_cache)


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


    def update(self, _reuse_imap=None) -> List[int]:
        new_msgs = []
        if _reuse_imap is None:
            imap = IMAPClient(host='imap.ietf.org', ssl=False, use_uid=True)
            imap.login("anonymous", "anonymous")
        else:
            imap = _reuse_imap
        imap.select_folder("Shared Folders/" + self._list_name, readonly=True)

        msg_list  = imap.search()
        msg_fetch = []
        for msg_id in msg_list:
            cache_file = Path(self._cache_folder, "{:06d}.msg".format(msg_id))
            if not cache_file.exists():
                msg_fetch.append(msg_id)

        if len(msg_fetch) > 0:
            aa_cache     = Path(self._cache_folder, "aa-cache.json")
            aa_cache_tmp = Path(self._cache_folder, "aa-cache.json.tmp")
            aa_cache.unlink()   

            for msg_id, msg in imap.fetch(msg_fetch, "RFC822").items():
                cache_file = Path(self._cache_folder, "{:06d}.msg".format(msg_id))
                fetch_file = Path(self._cache_folder, "{:06d}.msg.download".format(msg_id))
                if not cache_file.exists():
                    with open(fetch_file, "wb") as outf:
                        outf.write(msg[b"RFC822"])
                    fetch_file.rename(cache_file)

                    e = email.message_from_bytes(msg[b"RFC822"])
                    if e["Archived-At"] is not None:
                        list_name, msg_hash = _parse_archive_url(e["Archived-At"])
                        self._archive_urls[msg_hash] = msg_id
                    self._num_messages += 1
                    new_msgs.append(msg_id)

            with open(aa_cache_tmp, "w") as cache_file:
                json.dump(self._archive_urls, cache_file)
            aa_cache_tmp.rename(aa_cache)

        imap.unselect_folder()
        if _reuse_imap is None:
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

    def download_all_messages(self):
        """
        Download all messages.

        WARNING: as of July 2020, this fetches ~26GBytes of data. Use with care!
        """
        ml_names = list(self.mailing_list_names())
        num_list = len(ml_names)

        imap = IMAPClient(host='imap.ietf.org', ssl=False, use_uid=True)
        imap.login("anonymous", "anonymous")
        for index, ml_name in enumerate(ml_names):
            print(F"Updating list {index+1:4d}/{num_list:4d}: {ml_name} ", end="", flush=True)
            ml = self.mailing_list(ml_name)
            nm = ml.update(_reuse_imap=imap)
            print(F"({ml.num_messages()} messages; {len(nm)} new)")
        imap.logout()

# =================================================================================================
# vim: set tw=0 ai:
