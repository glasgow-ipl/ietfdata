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
import abc
import os
import logging

from datetime      import datetime, timedelta
from typing        import List, Optional, Tuple, Dict, Iterator, Type, TypeVar, Any
from pathlib       import Path
from email.message import Message
from imapclient    import IMAPClient

# =================================================================================================
# Private helper functions:

def _parse_archive_url(archive_url:str) -> Tuple[str, str]:
    aa_start = archive_url.find("://mailarchive.ietf.org/arch/msg")
    aa_uri   = archive_url[aa_start+33:].strip()

    mailing_list = aa_uri[:aa_uri.find("/")]
    message_hash = aa_uri[aa_uri.find("/")+1:]

    return (mailing_list, message_hash)

# =================================================================================================
# MailArchiveHelper interface:

class MailArchiveHelper(abc.ABC):
    """
    Abstract class for mail archive helpers.
    """

    @property
    @classmethod
    @abc.abstractmethod
    def name(cls):
        return NotImplementedError

    @property
    @classmethod
    @abc.abstractmethod
    def version(cls):
        return NotImplementedError


    @property
    @classmethod
    @abc.abstractmethod
    def provided_fields(cls):
        return NotImplementedError


    @abc.abstractmethod
    def scan_message(self, msg: Message) -> Dict[str, Any]:
        pass


    @abc.abstractmethod
    def filter(self, metadata: Dict[str, Any], **kwargs) -> bool:
        pass


    @abc.abstractmethod
    def serialise(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        pass


    @abc.abstractmethod
    def deserialise(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        pass

# =================================================================================================

class MailingListMessage:
    message       : Message
    _metadata     : Dict[str, Any]

    def __init__(self, message: Message, metadata: Dict[str, Any]):
        self.message = message
        self._metadata = {}
        for helper_name in metadata:
            self._metadata = {**self._metadata, **metadata[helper_name]}


    def has_metadata(self, name: str) -> bool:
        return name in self._metadata


    def metadata(self, name: str) -> Any:
        if not self.has_metadata(name):
            raise Exception(f"Message does not have a metadata field named {name}")
        return self._metadata.get(name)


class MessageThread:
    _msg_ids : List[str]
    messages: List[Tuple[int, MailingListMessage]]

    def __init__(self, index: int, first_message: MailingListMessage):
        self._msg_ids =  [first_message.message['Message-ID']]
        self.messages = [(index, first_message)]


    def should_contain(self, msg: MailingListMessage) -> bool:
        if "References" in msg.message:
            for msg_id in msg.message["References"].split():
                if msg_id in self._msg_ids:
                    return msg_id in self._msg_ids
        return msg.message["In-Reply-To"] in self._msg_ids


    def append(self, index: int, msg: MailingListMessage) -> None:
        assert self.should_contain(msg)
        self._msg_ids.append(msg.message["Message-ID"])
        self.messages.append((index, msg))

# =================================================================================================

class MailingList:
    _list_name         : str
    _cache_dir         : Path
    _cache_folder      : Path
    _last_updated      : datetime
    _num_messages      : int
    _archive_urls      : Dict[str, int]
    _helpers           : List[MailArchiveHelper]
    _msg_metadata      : Dict[int, Dict[str, Any]]
    _cached_metadata   : Dict[str, Dict[str, Any]]

    def __init__(self, cache_dir: Path, list_name: str, helpers: List[MailArchiveHelper] = [], _reuse_imap=None):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log            = logging.getLogger("ietfdata")
        self._list_name    = list_name
        self._cache_dir    = cache_dir
        self._cache_folder = Path(self._cache_dir, "mailing-lists", self._list_name)
        self._cache_folder.mkdir(parents=True, exist_ok=True)
        self._num_messages = len(list(self._cache_folder.glob("*.msg")))
        self._archive_urls = {}
        self._helpers = helpers
        self._msg_metadata = {}
        self._cached_metadata = {}

        # Rebuild the metadata cache:
        metadata_cache = Path(self._cache_folder, "metadata.json")
        metadata_cache_tmp = Path(self._cache_folder, "metadata.json.tmp")
        if metadata_cache.exists():
            with open(metadata_cache, "r") as metadata_file:
                self._cached_metadata = json.load(metadata_file)
                message_metadata = self._cached_metadata["message_metadata"] # type: Dict[str, Dict[str, Dict[str, Any]]]
                for msg_id_str in message_metadata:
                    msg_id = int(msg_id_str)
                    if not Path(self._cache_folder, F"{msg_id:06d}.msg").exists():
                        self.log.warn(F"dropping metadata for non-existing message {self._list_name}/{msg_id:06d}.msg")
                        continue
                    metadata : Dict[str, Dict[str, Any]] = {}
                    message_text = None
                    for helper in self._helpers:
                        if helper.name in self._cached_metadata["helpers"] and helper.version != self._cached_metadata["helpers"][helper.name]:
                            self.log.info(F"{helper.name}: version changed, discarding cached metadata")
                            (message_metadata[msg_id_str]).pop(helper.name)
                        if helper.name not in message_metadata[msg_id_str] or not all(metadata_field in message_metadata[msg_id_str][helper.name] for metadata_field in helper.provided_fields):
                            if message_text is None:
                                message_text = self.raw_message(msg_id)
                            self.log.info(F"scan message {self._list_name}/{msg_id:06} for metadata - {helper.name:15} (cache update)")
                            metadata[helper.name] = helper.scan_message(message_text)
                        else:
                            metadata[helper.name] = helper.deserialise(message_metadata[msg_id_str][helper.name])
                    self._msg_metadata[msg_id] = metadata
        else:
            self.log.info(F"no metadata cache for mailing list {self._list_name}")
            for index in self.message_indices():
                self._msg_metadata[index] = {}

        last_keepalive = datetime.now()
        for msg_id in self.message_indices():
            curr_keepalive = datetime.now()
            if (curr_keepalive - last_keepalive) > timedelta(seconds=10):
                if _reuse_imap is not None:
                    self.log.info("imap keepalive")
                    _reuse_imap.noop()
                    last_keepalive = curr_keepalive
            if msg_id not in self._msg_metadata:
                self._msg_metadata[msg_id] = {}
            message_text = None
            for helper in self._helpers:
                if helper.name not in self._msg_metadata[msg_id] or not all(metadata_field in self._msg_metadata[msg_id][helper.name] for metadata_field in helper.provided_fields):
                    if message_text is None:
                        message_text = self.raw_message(msg_id)
                    self.log.info(F"scan message {self._list_name}/{msg_id:06} for metadata - {helper.name:15} (cache create)")
                    self._msg_metadata[msg_id][helper.name] = helper.scan_message(message_text)
        self.serialise_metadata()

        # Rebuild the archived-at cache:
        aa_cache     = Path(self._cache_folder, "aa-cache.json")
        aa_cache_tmp = Path(self._cache_folder, "aa-cache.json.tmp")
        if aa_cache.exists():
            with open(aa_cache, "r") as cache_file:
                self._archive_urls = json.load(cache_file)
        else:
            self.log.info(F"no archived-at cache for mailing list {self._list_name}")
            for index, msg in self.messages():
                if msg.message["Archived-At"] is not None:
                    self.log.info(F"scan message {self._list_name}/{index:06} for archived-at")
                    list_name, msg_hash = _parse_archive_url(msg.message["Archived-At"])
                    self._archive_urls[msg_hash] = index
            with open(aa_cache_tmp, "w") as cache_file:
                json.dump(self._archive_urls, cache_file, indent=4)
            aa_cache_tmp.rename(aa_cache)



    def name(self) -> str:
        return self._list_name


    def num_messages(self) -> int:
        return self._num_messages


    def serialise_metadata(self) -> None:
        metadata_cache = Path(self._cache_folder, "metadata.json")
        metadata_cache_tmp = Path(self._cache_folder, "metadata.json.tmp")
        with open(metadata_cache_tmp, "w") as metadata_file:
            serialised_metadata = {"helpers": {}, "message_metadata": {}} # type: Dict[str, Dict[Any, Any]]
            serialised_metadata["helpers"] = {}
            serialised_metadata["helpers"] = {**serialised_metadata["helpers"], **self._cached_metadata.get("helpers", {})}
            for helper in self._helpers:
                serialised_metadata["helpers"][helper.name] = helper.version
            for msg_id in self._msg_metadata:
                serialised_metadata["message_metadata"][msg_id] = self.serialise_message(msg_id)
                serialised_metadata["message_metadata"][msg_id] = {**serialised_metadata["message_metadata"][msg_id], **(self._cached_metadata.get("message_metadata", {}).get(str(msg_id), {}))}
            json.dump(serialised_metadata, metadata_file, indent=4)
        metadata_cache_tmp.rename(metadata_cache)


    def serialise_message(self, msg_id: int) -> Dict[str, Dict[str, Any]]:
        metadata : Dict[str, Dict[str, Any]] = {}
        for helper in self._helpers:
            metadata[helper.name] = helper.serialise(self._msg_metadata[msg_id][helper.name])
        return metadata


    def raw_message(self, msg_id: int) -> Message:
        cache_file = Path(self._cache_folder, "{:06d}.msg".format(msg_id))
        with open(cache_file, "rb") as inf:
            message = email.message_from_binary_file(inf)
        return message


    def message_indices(self) -> List[int]:
        return [int(str(msg_path).split("/")[-1][:-4]) for msg_path in sorted(self._cache_folder.glob("*.msg"))]


    def message_from_archive_url(self, archive_url:str) -> MailingListMessage:
        list_name, msg_hash = _parse_archive_url(archive_url)
        assert list_name == self._list_name
        return self.message(self._archive_urls[msg_hash])


    def message(self, msg_id: int) -> MailingListMessage:
        return MailingListMessage(self.raw_message(msg_id), self._msg_metadata[msg_id])


    def messages(self, **kwargs) -> Iterator[Tuple[int, MailingListMessage]]:
        for msg_id in self.message_indices():
            include_msg = True
            for helper in self._helpers:
                if not helper.filter(self._msg_metadata[msg_id][helper.name], **kwargs):
                    include_msg = False
                    break
            if include_msg:
                yield msg_id, self.message(msg_id)


    def threads(self) -> List[MessageThread]:
        threads : List[MessageThread] = []
        for index, message in self.messages():
            threaded = False
            for thread in threads:
                if thread.should_contain(message):
                    thread.append(index, message)
                    threaded = True
                if threaded:
                    break
            if not threaded:
                threads.append(MessageThread(index, message))
        return threads


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

        for msg_id, msg in imap.fetch(msg_list, "RFC822.SIZE").items():
            cache_file = Path(self._cache_folder, F"{msg_id:06d}.msg")
            if not cache_file.exists():
                msg_fetch.append(msg_id)
            else:
                file_size = cache_file.stat().st_size
                imap_size = msg[b"RFC822.SIZE"]
                if file_size != imap_size:
                    self.log.warn(F"message size mismatch: {self._list_name}/{msg_id:06d}.msg ({file_size} != {imap_size})")
                    cache_file.unlink()
                    msg_fetch.append(msg_id)

        if len(msg_fetch) > 0:
            aa_cache     = Path(self._cache_folder, "aa-cache.json")
            aa_cache_tmp = Path(self._cache_folder, "aa-cache.json.tmp")
            aa_cache.unlink()

            for msg_id, msg in imap.fetch(msg_fetch, "RFC822").items():
                cache_file = Path(self._cache_folder, F"{msg_id:06d}.msg")
                fetch_file = Path(self._cache_folder, F"{msg_id:06d}.msg.download")
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

                    self._msg_metadata[msg_id] = {}
                    for helper in self._helpers:
                        self.log.info(F"{helper.name}: scan message {self._list_name}/{msg_id:06} for metadata")
                        self._msg_metadata[msg_id][helper.name] = helper.scan_message(e)

            with open(aa_cache_tmp, "w") as aa_cache_file:
                json.dump(self._archive_urls, aa_cache_file)
            aa_cache_tmp.rename(aa_cache)

        self.serialise_metadata()

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
    _helpers       : List[MailArchiveHelper]

    def __init__(self, cache_dir: Path, helpers: List[MailArchiveHelper] = []):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log            = logging.getLogger("ietfdata")
        self._cache_dir     = cache_dir
        self._mailing_lists = {}
        self._helpers       = helpers


    def mailing_list_names(self) -> Iterator[str]:
        imap = IMAPClient(host='imap.ietf.org', ssl=False, use_uid=True)
        imap.login("anonymous", "anonymous")
        for (flags, delimiter, name) in imap.list_folders():
            if name != "Shared Folders":
                assert name.startswith("Shared Folders/")
                yield name[15:]
        imap.logout()


    def mailing_list(self, mailing_list_name: str, _reuse_imap=None) -> MailingList:
        if not mailing_list_name in self._mailing_lists:
            self._mailing_lists[mailing_list_name] = MailingList(self._cache_dir, mailing_list_name, self._helpers, _reuse_imap)
        return self._mailing_lists[mailing_list_name]


    def message_from_archive_url(self, archive_url: str) -> MailingListMessage:
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


    def download_all_messages(self) -> None:
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
            ml = self.mailing_list(ml_name, _reuse_imap=imap)
            nm = ml.update(_reuse_imap=imap)
            print(F"({ml.num_messages()} messages; {len(nm)} new)")
        imap.logout()


    def messages(self, **kwargs) -> Iterator[Tuple[Tuple[str, int], MailingListMessage]]:
        for mailing_list in self._mailing_lists:
            for msg_id, msg in self._mailing_lists[mailing_list].messages(**kwargs):
                yield ((mailing_list, msg_id), msg)


# =================================================================================================
# vim: set tw=0 ai:
