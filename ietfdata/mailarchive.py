# Copyright (C) 2020-2021 University of Glasgow
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

import requests
import email
import os
import logging
import gridfs


from datetime      import datetime, timedelta
from typing        import Dict, Iterator, List, Optional, Tuple, Union
from pymongo       import MongoClient, ASCENDING, ReplaceOne, UpdateOne
from email         import policy, utils
from email.message import Message as EmailMessage
from imapclient    import IMAPClient

from dataclasses import dataclass, field

import time

from email_reply_parser import EmailReplyParser

import pandas as pd

# =================================================================================================
# Private helper functions:

def _parse_archive_url(archive_url:str) -> Tuple[str, str]:
    aa_start = archive_url.find("://mailarchive.ietf.org/arch/msg")
    aa_uri   = archive_url[aa_start+33:].strip()

    mailing_list = aa_uri[:aa_uri.find("/")]
    message_hash = aa_uri[aa_uri.find("/")+1:]
    
    if message_hash.endswith(">"):
        message_hash = message_hash[:-1]

    return (mailing_list, message_hash)


def _ml_message_from_db_message(mailing_list: "MailingList", gridfs_id: int, imap_uid: int, headers: Dict[str, str], timestamp: datetime) -> MailingListMessage:
    return MailingListMessage(mailing_list,
                              gridfs_id,
                              imap_uid,
                              headers.get("Message-ID", headers.get("Message-Id", None)),
                              headers.get("From", headers.get("from", None)),
                              headers.get("Subject", headers.get("subject", None)),
                              timestamp,
                              headers.get("In-Reply-To", None),
                              headers.get("References", None),
                              headers.get("Archived-At", None),
                              headers)


# =================================================================================================

@dataclass
class MailingListMessage:
    _mailing_list : "MailingList"
    _gridfs_id    : int
    _imap_uid     : int
    message_id    : Optional[str]
    from_addr     : Optional[str]
    subject       : Optional[str]
    date          : datetime
    in_reply_to   : Optional[str]
    references    : Optional[str]
    archived_at   : Optional[str]
    headers       : Dict[str, str]
    parent        : Optional["MailingListMessage"] = None
    children      : List["MailingListMessage"] = field(default_factory=list)


    def __post_init__(self):
        self.list_name = self._mailing_list._list_name


    def add_child_message(self, child: "MailingListMessage"):
        self.children.append(child)


    def get_child_count(self) -> int:
        return len(self.children) + sum([child.get_child_count() for child in self.children])


    def get_child_from_addrs(self, child_from_addrs: List[str]) -> List[str]:
        if self.from_addr is not None:
            child_from_addrs.append(self.from_addr)
        for child in self.children:
            child.get_child_from_addrs(child_from_addrs)
        return child_from_addrs


    def get_child_dates(self, child_dates: List[datetime]):
        child_dates.append(self.date)
        for child in self.children:
            child.get_child_dates(child_dates)
        return child_dates
        

    def rfc822_message(self) -> EmailMessage:
        email_file = self._mailing_list._mail_archive._fs.get(self._gridfs_id)
        email_obj = email.message_from_bytes(self._mailing_list._mail_archive._fs.get(self._gridfs_id).read(), policy=policy.default)
        return email_obj

        


# =================================================================================================

class MailingListThread:
    root : MailingListMessage

    def __init__(self, root: MailingListMessage):
        self.root = root


    def get_message_count(self):
        return 1 + self.root.get_child_count()


    def get_unique_from_count(self):
        from_addrs = self.root.get_child_from_addrs([])
        return len(list(set(from_addrs)))


    def get_duration(self):
        earliest_date = self.root.date
        latest_date = sorted(self.root.get_child_dates([]), reverse=True)[0]
        return latest_date - earliest_date


# =================================================================================================

class MailingList:
    _mail_archive      : MailArchive
    _list_name         : str
    _num_messages      : int
    _last_updated      : datetime
    _archive_urls      : Dict[str, int]

    def __init__(self, mail_archive: MailArchive, list_name: str, reuse_imap=None):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log           = logging.getLogger("ietfdata")
        self._mail_archive = mail_archive
        self._list_name    = list_name
        self._num_messages = self._mail_archive._db.messages.count_documents({"list": self._list_name})
        self._archive_urls = {}

        ml = self._mail_archive._db.lists.find_one({"list": self._list_name})
        if ml is None:
            if reuse_imap is None:
                imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
                imap.login("anonymous", "anonymous")
            else:
                imap = reuse_imap
            status_imap = imap.folder_status("Shared Folders/" + self._list_name)
            status_json = {
                "list"        : self._list_name,
                "uidvalidity" : status_imap[b'UIDVALIDITY'],
                "messages"    : 0   # Force check for new messages when cache created
            }
            self._mail_archive._db.lists.insert_one(status_json)
            if reuse_imap is None:
                imap.logout()

        # Rebuild the archived-at cache:
        aa_cache = self._mail_archive._db.aa_cache.find_one({"list": self._list_name})
        if aa_cache is not None and len(aa_cache["archive_urls"]) > 0:
            self._archive_urls = aa_cache["archive_urls"]
            self.log.debug(f"_archive_urls: loaded {len(self._archive_urls)} URLs for list {list_name}")
        else:
            for msg in self.messages():
                if msg.archived_at is not None:
                    list_name, msg_hash = _parse_archive_url(msg.archived_at)
                    self._archive_urls[msg_hash] = msg._imap_uid
                    self.log.debug(F"_archive_urls: {self._list_name}/{msg._imap_uid} -> {msg_hash}")
            self._mail_archive._db.aa_cache.replace_one({"list" : self._list_name},
                                                        {"list" : self._list_name, "archive_urls": self._archive_urls}, upsert=True)
            self.log.debug(f"_archive_urls: rebuilt aa_cache for list {list_name} ({len(self._archive_urls)} entries)")


    def name(self) -> str:
        return self._list_name


    def num_messages(self) -> int:
        return self._num_messages


    def message_indices(self) -> List[int]:
        cache_metadata = self._mail_archive._db.messages.find({"list" : self._list_name})
        indices = [message_metadata["imap_uid"] for message_metadata in cache_metadata]
        return sorted(indices)


    def message_from_archive_url(self, archive_url:str) -> Optional[MailingListMessage]:
        list_name, msg_hash = _parse_archive_url(archive_url)
        self.log.debug(f"message_from_archive_url: {archive_url} -> {list_name} {msg_hash}")
        assert list_name == self._list_name
        return self.message(self._archive_urls[msg_hash])


    def message(self, msg_id: int) -> Optional[MailingListMessage]:
        message = self._mail_archive._db.messages.find_one({"list" : self._list_name, "imap_uid": msg_id})
        if message is not None:
            return _ml_message_from_db_message(self, message["gridfs_id"], message["imap_uid"], message["headers"], message["timestamp"])
        else:
            return None


    def messages(self,
                 since : str = "1970-01-01T00:00:00",
                 until : str = "2038-01-19T03:14:07") -> Iterator[MailingListMessage]:
        messages = self._mail_archive._db.messages.find({"list"     : self._list_name,
                                           "timestamp": {"$gt": datetime.strptime(since, "%Y-%m-%dT%H:%M:%S"),
                                                         "$lt": datetime.strptime(until, "%Y-%m-%dT%H:%M:%S")}
                                          },
                                          no_cursor_timeout=True)
        for message in messages:
            yield _ml_message_from_db_message(self, message["gridfs_id"], message["imap_uid"], message["headers"], message["timestamp"])
        messages.close()


    def update(self, reuse_imap=None) -> List[int]:
        new_msgs = []
        if reuse_imap is None:
            imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
            imap.login("anonymous", "anonymous")
        else:
            imap = reuse_imap

        # Check the UIDVALIDITY and number of messages, and compare to the cached values.
        # If they're unchanged, then we know the cache is up-to-date and there's nothing
        # to fetch. If the values have changed, then we fetch new messages. The cache for
        # the UIDVALIDITY and number of messages is updated at the end of this function,
        # once we've successfully fetched the new messages.
        status_imap = imap.folder_status("Shared Folders/" + self._list_name)
        status_json = self._mail_archive._db.lists.find_one({"list": self._list_name})
        assert status_json is not None
        if (status_imap[b'UIDVALIDITY'] == status_json['uidvalidity']) and (status_imap[b'MESSAGES'] == status_json['messages']):
            # Cache is up-to-date for this list, return since nothing to do
            if reuse_imap is None:
                imap.logout()
            return []

        # if UIDVALIDITY has changed, the cache will be invalid. Drop and re-download
        # the entire folder. IMAP servers are supposed to ensure the UIDVALIDITY doesn't
        # change, but sometimes a re-index occurs on the server so we have to handle it.
        if status_imap[b'UIDVALIDITY'] != status_json['uidvalidity']:
            for msg in self._mail_archive._db.messages.find({"list": self._list_name}):
                self._mail_archive._fs.delete(msg["gridfs_id"])
                self._mail_archive._db.messages.delete_one({"list" : self._list_name, "imap_uid" : msg['imap_uid']})
                self.log.info(f"UIDVALIDITY changed: removed message {msg['imap_uid']}")
            self._num_messages = 0

        imap.select_folder("Shared Folders/" + self._list_name, readonly=True)
        msg_list  = imap.search()

        cached_messages = {msg["imap_uid"] : msg for msg in self._mail_archive._db.messages.find({"list": self._list_name})}
        msg_fetch = []
        msg_check = []
        for msg_id in msg_list:
            if msg_id in cached_messages:
                msg_check.append(msg_id)   # Message is in the cache, add to the list of messages to check size matches
            else:
                msg_fetch.append(msg_id)   # Messgae is not in the cache, add to the list of messages to fetch

        # For messages that we have cached, check their sizes match those on the server,
        # to detect silent updates to messages on the server
        self.log.debug(f"{len(msg_check)} messages to check")
        for i in range(0, len(msg_check), 512):
            msg_slice = msg_check[slice(i, i+512, 1)]
            for msg_id, msg in imap.fetch(msg_slice, "RFC822.SIZE").items():
                if cached_messages[msg_id]["size"] != msg[b"RFC822.SIZE"]:
                    self.log.warn(F"message size mismatch: {self._list_name}/{msg_id:06d}.msg ({cached_messages[msg_id]['size']} != {msg[b'RFC822.SIZE']})")
                    self._mail_archive._fs.delete(cached_messages[msg_id]["gridfs_id"])
                    self._mail_archive._db.messages.delete_one({"list" : self._list_name, "imap_uid" : msg_id})
                    msg_fetch.append(msg_id)

        # Fetch the messages
        for i in range(0, len(msg_fetch), 512):
            msg_slice = msg_fetch[slice(i, i+512, 1)]
            for msg_id, msg in imap.fetch(msg_slice, "RFC822").items():
                e = email.message_from_bytes(msg[b"RFC822"], policy=policy.default)
                if e["Archived-At"] is not None:
                    list_name, msg_hash = _parse_archive_url(e["Archived-At"])
                    self._archive_urls[msg_hash] = msg_id
                self._num_messages += 1
                timestamp = None # type: Optional[datetime]
                try:
                    msg_date = email.utils.parsedate(e["Date"]) # type: Optional[Tuple[int, int, int, int, int, int, int, int, int]]
                    if msg_date is not None:
                        timestamp = datetime.fromtimestamp(time.mktime(msg_date))
                    else:
                        timestamp = None
                except:
                    timestamp = None
                try:
                    headers = {}
                    for name, value in e.items():
                        name = name.replace(".", "-")   # No standard mail header names contain "." and it makes MongoDB unhappy
                        if name not in headers:
                            headers[name] = value
                        elif isinstance(headers[name], list):
                            headers[name].append(value)
                        else:
                            headers[name] = [headers[name], value]
                except:
                    headers = {}
                cache_file_id = self._mail_archive._fs.put(msg[b"RFC822"])
                self._mail_archive._db.messages.insert_one({"list"       : self._list_name,
                                                            "imap_uid"   : msg_id,
                                                            "gridfs_id"  : cache_file_id,
                                                            "size"       : len(msg[b"RFC822"]), # FIXME: should be IMAP RFC822.SIZE ?
                                                            "timestamp"  : timestamp,
                                                            "headers"    : headers})
                self.log.debug(f"saved message {self._list_name}/{msg_id}")
                new_msgs.append(msg_id)

        # Update the aa_cache after downloading messages
        self._mail_archive._db.aa_cache.replace_one({"list" : self._list_name},
                                                    {"list" : self._list_name, "archive_urls": self._archive_urls}, upsert=True)
        self.log.debug(f"_archive_urls: saved aa_cache for list {self._list_name} ({len(self._archive_urls)} entries)")

        # Update the list cache based on the folder status we retrieved earlier.
        status_json = {
            "list"        : self._list_name,
            "uidvalidity" : status_imap[b'UIDVALIDITY'],
            "messages"    : status_imap[b'MESSAGES']
        }
        self._mail_archive._db.lists.replace_one({"list" : self._list_name}, status_json)

        imap.unselect_folder()
        if reuse_imap is None:
            imap.logout()
        self._last_updated = datetime.now()
        return new_msgs


    def last_updated(self) -> datetime:
        return self._last_updated


    def messages_dataframe(self,
                 since : str = "1970-01-01T00:00:00",
                 until : str = "2038-01-19T03:14:07") -> pd.DataFrame:
        messages = self.messages(since = since, until = until)
        messages_as_dict = []
        for message in messages:
            messages_as_dict.append({"Message-ID": message.message_id,
                                     "From" : message.from_addr,
                                     "Subject": message.subject,
                                     "Date": message.date,
                                     "In-Reply-To": message.in_reply_to,
                                     "References": message.references})
        df = pd.DataFrame(data=messages_as_dict)
        df.set_index("Message-ID", inplace=True)
        return df


    def threads(self) -> Iterator[MailingListThread]:
        threads = []
        message_by_message_id = {message.message_id : message for message in self.messages()}

        for message_id in message_by_message_id:
            message = message_by_message_id[message_id]
            if message.in_reply_to is None:
                threads.append(message)
            if message.in_reply_to is not None and message.in_reply_to in message_by_message_id:
                message.parent = message_by_message_id[message.in_reply_to]
                message_by_message_id[message.in_reply_to].add_child_message(message)

        return iter([MailingListThread(message) for message in threads])


# =================================================================================================

class MailArchive:
    _mailing_lists : Dict[str, MailingList]


    def __init__(self, mongodb_hostname: str = "localhost", mongodb_port: int = 27017, mongodb_username: Optional[str] = None, mongodb_password: Optional[str] = None):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log            = logging.getLogger("ietfdata")
        self._mailing_lists = {}
        self._last_full_update = None
        self._cache_version = "1.1"

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

        self._fs = gridfs.GridFS(self._db)

        self._check_cache_version()

    def mailing_list_names(self) -> Iterator[str]:
        imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
        imap.login("anonymous", "anonymous")
        for (flags, delimiter, name) in imap.list_folders():
            if name != "Shared Folders":
                assert name.startswith("Shared Folders/")
                yield name[15:]
        imap.logout()


    def _check_cache_version(self):
        cn = self._db.list_collection_names()
        if len(cn) > 0 and "cache_info" not in cn:
            # check if cache pre-dates versioning; if so, set to 1.0
            self.log.info("_check_cache_version: setting mail archive cache version to 1.0")
            self._db.cache_info.insert_one({"list": "__cache_version__", "version" : "1.0", "last_imap_update": None})
            self._db.metadata_cache.drop()
        else:
            cache_version_info = self._db.cache_info.find_one({"list": "__cache_version__"})
            if cache_version_info is not None:
                cache_version = cache_version_info["version"]
                if cache_version == "1.0" and self._cache_version == "1.1":
                    self.log.info("_check_cache_version: mail archive cache version changed (1.0 -> 1.1)")
                    self.log.info("_check_cache_version: rebuilding header cache")
                    cache_updates = []
                    for message in self.messages():
                        try:
                            email_message = message.rfc822_message()
                            self.log.info(f"_check_cache_version: rebuilding {message.list_name}/{message._imap_uid:06}.msg header cache")
                            headers = {}
                            for name, value in email_message.items():
                                if name not in headers:
                                    headers[name] = value
                                elif isinstance(headers[name], list):
                                    headers[name].append(value)
                                else:
                                    headers[name] = [headers[name], value]
                        except:
                            headers = {}
                        self._db.cache_info.update_one({"list" : message.list_name, "imap_uid": message._imap_uid},
                                                       {"$set": {"headers" : headers}, "$unset": {"body":1}}, upsert=True)
            else:
                self.log.info("_check_cache_version: setting mail archive cache version to 1.1")
                cache_version = "1.1"
            self._db.cache_info.update_one({"list": "__cache_version__"}, {"$set": {"version" : cache_version}}, upsert=True)
        # Create indexes:
        self._db.messages.create_index([('list', ASCENDING), ('imap_uid', ASCENDING)], unique=True)
        self._db.messages.create_index([('list', ASCENDING)], unique=False)
        self._db.messages.create_index([('timestamp', ASCENDING)], unique=False)
        self._db.aa_cache.create_index([('list', ASCENDING)], unique=True)
        self._db.lists.create_index([('list', ASCENDING)], unique=True)


    def mailing_list(self, mailing_list_name: str, reuse_imap=None) -> MailingList:
        if not mailing_list_name in self._mailing_lists:
            self._mailing_lists[mailing_list_name] = MailingList(self, mailing_list_name, reuse_imap)
        return self._mailing_lists[mailing_list_name]


    def message_from_archive_url(self, archive_url: str) -> Optional[MailingListMessage]:
        if "//www.ietf.org/mail-archive/web/" in archive_url:
            # This is a legacy mail archive URL. If we retrieve it, the
            # server should redirect us to the current archive location.
            # Unfortunately this will then fail, because messages in the
            # legacy archive are missing the "Archived-At:" header.
            self.log.debug(f"message_from_archive_url (old): {archive_url}")
            response = requests.get(archive_url)
            assert "//mailarchive.ietf.org/arch/msg" in response.url
            return self.message_from_archive_url(response.url)
        elif "//mailarchive.ietf.org/arch/msg" in archive_url:
            list_name, _ = _parse_archive_url(archive_url)
            mailing_list = self.mailing_list(list_name)
            self.log.debug(f"message_from_archive_url (new): {archive_url} -> {mailing_list.name()}")
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

        imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
        imap.login("anonymous", "anonymous")
        for index, ml_name in enumerate(ml_names):
            print(F"Updating list {index+1:4d}/{num_list:4d}: {ml_name} ", end="", flush=True)
            ml = self.mailing_list(ml_name, imap)
            nm = ml.update(reuse_imap=imap)
            print(F"({ml.num_messages()} messages; {len(nm)} new)")
        imap.logout()


    def messages(self,
                 since : str = "1970-01-01T00:00:00",
                 until : str = "2038-01-19T03:14:07") -> Iterator[MailingListMessage]:
        messages = self._db.messages.find({"timestamp": {"$gt": datetime.strptime(since, "%Y-%m-%dT%H:%M:%S"),
                                                         "$lt": datetime.strptime(until, "%Y-%m-%dT%H:%M:%S")}
                                          }).sort([("list", ASCENDING), ("imap_uid", ASCENDING)])

        for message in messages:
            yield _ml_message_from_db_message(self.mailing_list(message["list"]), message["gridfs_id"], message["imap_uid"], message["headers"], message["timestamp"])


# =================================================================================================
# vim: set tw=0 ai:
