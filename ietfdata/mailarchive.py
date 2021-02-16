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

from __future__    import annotations

import hashlib
import json
import re
import requests
import email
import ietfdata.datatracker as dt
import abc
import os
import logging
import gridfs

from datetime      import datetime, timedelta
from typing        import List, Optional, Tuple, Dict, Iterator, Type, TypeVar, Any
from pathlib       import Path
from pymongo       import MongoClient, ASCENDING
from email         import policy
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
    class MessageThreadNode:
        parent   : Optional[MessageThread.MessageThreadNode]
        children : List[MessageThread.MessageThreadNode]
        message  : MailingListMessage

        def __init__(self, message: MailingListMessage):
            self.parent = None
            self.children = []
            self.message = message

        def add_child(self, child):
            self.children.append(child)

        def num_messages(self):
            num_messages = 1
            for child in self.children:
                num_messages += child.num_messages()
            return num_messages

    root : MessageThreadNode

    def __init__(self, root: MessageThreadNode):
        self.root = root

    def num_messages(self):
        return self.root.num_messages()


# =================================================================================================

class MailingList:
    _list_name         : str
    _last_updated      : datetime
    _num_messages      : int
    _archive_urls      : Dict[str, int]
    _helpers           : List[MailArchiveHelper]
    _msg_metadata      : Dict[int, Dict[str, Any]]
    _cached_metadata   : Dict[str, Dict[str, Any]]
    _threads           : List[MessageThread]

    def __init__(self, db, fs, list_name: str, helpers: List[MailArchiveHelper] = [], _reuse_imap=None):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log           = logging.getLogger("ietfdata")
        self._list_name    = list_name
        self._db           = db
        self._fs           = fs
        self._num_messages = self._db.messages.find({"list": self._list_name}).count()
        self._archive_urls = {}
        self._helpers = helpers
        self._msg_metadata = {}
        self._cached_metadata = {}
        self._threads         = []

        # Rebuild the metadata cache:
        metadata_cache = self._db.metadata_cache.find_one({"list": self._list_name})
        if metadata_cache:
            self._cached_metadata = metadata_cache["cached_metadata"]
            message_metadata = self._cached_metadata["message_metadata"] # type: Dict[str, Dict[str, Dict[str, Any]]]
            for msg_id_str in message_metadata:
                msg_id = int(msg_id_str)
                if not self._db.messages.find_one({"list": self._list_name, "imap_uid": msg_id}):
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
        aa_cache = self._db.aa_cache.find_one({"list": self._list_name})
        if aa_cache:
            self._archive_urls = aa_cache["archive_urls"]
        else:
            self.log.info(F"no archived-at cache for mailing list {self._list_name}")
            for index, msg in self.messages():
                if msg.message["Archived-At"] is not None:
                    self.log.info(F"scan message {self._list_name}/{index:06} for archived-at")
                    list_name, msg_hash = _parse_archive_url(msg.message["Archived-At"])
                    self._archive_urls[msg_hash] = index
            self._db.aa_cache.replace_one({"list" : self._list_name}, {"list" : self._list_name, "archive_urls": self._archive_urls}, upsert=True)


    def name(self) -> str:
        return self._list_name


    def num_messages(self) -> int:
        return self._num_messages


    def serialise_metadata(self) -> None:
        serialised_metadata = {"helpers": {}, "message_metadata": {}} # type: Dict[str, Dict[Any, Any]]
        serialised_metadata["helpers"] = {}
        serialised_metadata["helpers"] = {**serialised_metadata["helpers"], **self._cached_metadata.get("helpers", {})}
        for helper in self._helpers:
            serialised_metadata["helpers"][helper.name] = helper.version
        for msg_id in self._msg_metadata:
            serialised_metadata["message_metadata"][str(msg_id)] = self.serialise_message(msg_id)
            serialised_metadata["message_metadata"][str(msg_id)] = {**serialised_metadata["message_metadata"][str(msg_id)], **(self._cached_metadata.get("message_metadata", {}).get(str(msg_id), {}))}
        self._db.metadata_cache.replace_one({"list" : self._list_name}, {"list" : self._list_name, "cached_metadata": serialised_metadata}, upsert=True)


    def serialise_message(self, msg_id: int) -> Dict[str, Dict[str, Any]]:
        metadata : Dict[str, Dict[str, Any]] = {}
        for helper in self._helpers:
            metadata[helper.name] = helper.serialise(self._msg_metadata[msg_id][helper.name])
        return metadata


    def raw_message(self, msg_id: int) -> Message:
        cache_metadata = self._db.messages.find_one({"list" : self._list_name, "imap_uid": msg_id})
        if cache_metadata:
            message = email.message_from_bytes(self._fs.get(cache_metadata["gridfs_id"]).read(), policy=policy.default)
        return message


    def message_indices(self) -> List[int]:
        cache_metadata = self._db.messages.find({"list" : self._list_name})
        indices = [message_metadata["imap_uid"] for message_metadata in cache_metadata]
        return sorted(indices)


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
        if self._threads == []:
            msg_nodes = {}
            for index, msg in self.messages():
                msg_nodes[msg.message["Message-ID"]] = MessageThread.MessageThreadNode(msg)
            for msg_id in msg_nodes:
                in_reply_to = msg_nodes[msg_id].message.message["In-Reply-To"]
                if in_reply_to is not None and in_reply_to in msg_nodes:
                    msg_nodes[in_reply_to].add_child(msg_nodes[msg_id])
                else:
                    self._threads.append(MessageThread(msg_nodes[msg_id]))
        return self._threads


    def update(self, _reuse_imap=None) -> List[int]:
        self._threads = []
        new_msgs = []
        if _reuse_imap is None:
            imap = IMAPClient(host='imap.ietf.org', ssl=False, use_uid=True)
            imap.login("anonymous", "anonymous")
        else:
            imap = _reuse_imap
        imap.select_folder("Shared Folders/" + self._list_name, readonly=True)

        msg_list  = imap.search()
        msg_fetch = []

        cached_messages = {msg["imap_uid"] : msg for msg in self._db.messages.find({"list": self._list_name})}

        for msg_id, msg in imap.fetch(msg_list, "RFC822.SIZE").items():
            curr_keepalive = datetime.now()
            if msg_id not in cached_messages:
                msg_fetch.append(msg_id)
            elif cached_messages[msg_id]["size"] != msg[b"RFC822.SIZE"]:
                self.log.warn(F"message size mismatch: {self._list_name}/{msg_id:06d}.msg ({cached_messages[msg_id]['size']} != {msg[b'RFC822.SIZE']})")
                cache_file = self._fs.get(cached_messages[msg_id]["gridfs_id"])
                cache_file.delete()
                self._db.messages.delete_one({"list" : self._list_name, "imap_uid" : msg_id})
                msg_fetch.append(msg_id)

        if len(msg_fetch) > 0:
            for msg_id, msg in imap.fetch(msg_fetch, "RFC822").items():
                cache_file_id = self._fs.put(msg[b"RFC822"])
                e = email.message_from_bytes(msg[b"RFC822"])
                if e["Archived-At"] is not None:
                    list_name, msg_hash = _parse_archive_url(e["Archived-At"])
                    self._archive_urls[msg_hash] = msg_id
                self._num_messages += 1
                self._db.messages.replace_one({"list" : self._list_name, "id": msg_id}, {"list" : self._list_name, "imap_uid": msg_id, "size": len(msg[b"RFC822"]), "message-id": e["Message-ID"], "gridfs_id": cache_file_id}, upsert=True)
                new_msgs.append(msg_id)

                self._msg_metadata[msg_id] = {}
                last_keepalive = datetime.now()
                for helper in self._helpers:
                    curr_keepalive = datetime.now()
                    if (curr_keepalive - last_keepalive) > timedelta(seconds=10):
                        if _reuse_imap is not None:
                            self.log.info("imap keepalive")
                            _reuse_imap.noop()
                            last_keepalive = curr_keepalive
                    self.log.info(F"{helper.name}: scan message {self._list_name}/{msg_id:06} for metadata")
                    self._msg_metadata[msg_id][helper.name] = helper.scan_message(e)

            self._db.aa_cache.replace_one({"list" : self._list_name}, {"list" : self._list_name, "archive_urls": self._archive_urls}, upsert=True)

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
    _mailing_lists : Dict[str,MailingList]
    _helpers       : List[MailArchiveHelper]


    def __init__(self, mongodb_hostname: str = "localhost", mongodb_port: int = 27017, mongodb_username: Optional[str] = None, mongodb_password: Optional[str] = None, helpers: List[MailArchiveHelper] = []):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log            = logging.getLogger("ietfdata")
        self._mailing_lists = {}
        self._helpers       = helpers

        cache_host = os.environ.get('IETFDATA_CACHE_HOST')
        cache_port = os.environ.get('IETFDATA_CACHE_PORT', 27017)
        cache_username = os.environ.get('IETFDATA_CACHE_USER')
        cache_password = os.environ.get('IETFDATA_CACHE_PASSWORD')
        if cache_host is not None:
            mongodb_hostname = cache_host
        if cache_port is not None:
            mongodb_port = int(cache_port)
        if cache_username is not None:
            mongodb_username = cache_username
        if cache_password is not None:
            mongodb_password = cache_password

        if mongodb_username is not None:
            self._db = MongoClient(host=mongodb_hostname, port=mongodb_port, username=mongodb_username, password=mongodb_password).ietfdata_mailarchive
        else:
            self._db = MongoClient(host=mongodb_hostname, port=mongodb_port).ietfdata_mailarchive
        self._fs            = gridfs.GridFS(self._db)

        self._db.messages.create_index([('list', ASCENDING), ('imap_uid', ASCENDING)], unique=True)
        self._db.messages.create_index([('list', ASCENDING)], unique=False)
        self._db.aa_cache.create_index([('list', ASCENDING)], unique=True)
        self._db.metadata_cache.create_index([('list', ASCENDING)], unique=True)


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
            self._mailing_lists[mailing_list_name] = MailingList(self._db, self._fs, mailing_list_name, self._helpers, _reuse_imap)
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
