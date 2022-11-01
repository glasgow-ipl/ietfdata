# Copyright (C) 2020-2022 University of Glasgow
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

import concurrent.futures
import email
import pandas as pd
import os
import logging
import time

from datetime           import datetime, timedelta
from graphlib           import TopologicalSorter
from typing             import Dict, Iterator, List, Optional, Tuple, Union
from gridfs             import GridFS
from pymongo            import MongoClient, ASCENDING, ReplaceOne, UpdateOne
from pymongo.database   import Database
from email              import policy, utils
from email.message      import Message as EmailMessage
from email_reply_parser import EmailReplyParser
from imapclient         import IMAPClient

# =================================================================================================
# Database design for the mail archive:
#
# The data is stored in a MongoDB database `ietfdata_mailarchive_v2`. The database
# contains two collections plus a GridFS instance.
#
# The `lists` collection contains documents of the form:
#
#   {
#     list: "100attendees"
#     uidvalidity: 1505323361
#   }
#
# The uidvalidity value is provided by the IMAP server when selecting a mailbox,
# and should never change. If it does, messages with the old uidvalidity MUST be
# deleted and the mailbox MUST be re-downloaded.
#
# The `messages` collections contains documents of the form:
#
#   {
#     "list": "100attendees",
#     "uidvalidity": 1505323361
#     "uid": 1,
#     "gridfs_id": ObjectId("62abb2883f8fcb5b9903e84d"),
#     "timestamp": 2017-09-13T10:11:47.000+00:00,
#     "size": 5512,
#     "message_id": "<CAAiTEH9EVrZzF08F4T3z6QzhAnwBmKk9jhHEf=xMy-=3W4r9+Q@mail.gmail.com>",
#     "in_reply_to": None,
#     "headers": {
#       "from":         ["Matthew Pounsett <matt@conundrum.com>"],
#       "date":         ["Wed, 13 Sep 2017 10:11:47 -0700"],
#       "message-id":   ["<CAAiTEH9EVrZzF08F4T3z6QzhAnwBmKk9jhHEf=xMy-=3W4r9+Q@mail.gmail.com>"],
#       "to":           ["100attendees@ietf.org"],
#       "content-type": ["multipart/alternative; boundary=\"001a1140ae52434d93055915417e\""],
#       "archived-at":  ["<https://mailarchive.ietf.org/arch/msg/100attendees/MLJtEybRr3ZglowtsdNsc0lQrcU>"],
#       "subject":      ["[100attendees] Hotel Room Available: Conrad"],
#       "list-id":      ["\"Mailing list of IETF 100 attendees that have opted in on this list.\" <100attendees.ietf.org>"],
#     }
#   }
#
# where the timestamp is the IMAP INTERNALDATE [RFC 3501, Section 2.3.3] represented
# as a `datetime`, and the size is the IMAP RFC822.SIZE  [RFC 3501, Section 2.3.4].
# The headers is a dictionary containing the headers parsed from the messages, with
# each element containing a list of header values, one for each time that header appears
# in the message. The gridfs_id points to a file containing the raw message content (the
# IMAP RFC822 fetch result).
#
# =================================================================================================

class Message:
    _mailing_list : MailingList
    _uidvalidity  : int
    _uid          : int
    _gridfs_id    : int
    _timestamp    : datetime
    _size         : int
    _headers      : Dict[str, List[str]]

    def __init__(self,
                 ml: MailingList,
                 uidvalidity: int,
                 uid: int,
                 gridfs_id: int,
                 timestamp: datetime,
                 size:int,
                 headers: Dict[str, List[str]]) -> None:
        self._mailing_list = ml
        self._uidvalidity  = uidvalidity
        self._uid          = uid
        self._gridfs_id    = gridfs_id
        self._timestamp    = timestamp
        self._size         = size
        self._headers      = headers


    # Accessors for messages properties. Messages in IMAP are assigned
    # a unique identifier `uid()` within a folder representing a mailing
    # list. That identifier is not supposed to change, but the IMAP
    # standard recognises that mailboxes occasionally get rebuilt. If
    # this happens, the `uidvalidity()` will change. The combination of
    # mailing_list(), uid(), and uidvalidity() uniquely identifies a 
    # message on the server.
    def mailing_list(self) -> MailingList:
        return self._mailing_list


    def uidvalidity(self) -> int:
        return self._uidvalidity


    def uid(self) -> int:
        return self._uid


    # Timestamp is the time the messages was received by the IMAP server
    def timestamp(self) -> datetime:
        return self._timestamp


    def size(self) -> int:
        return self._size


    # Accessors for commonly-used headers:
    def header_from(self) -> Optional[str]:
        return self._headers["from"][0] if "from" in self._headers else None


    def header_to(self) -> Optional[str]:
        return self._headers["to"][0] if "to" in self._headers else None


    def header_cc(self) -> Optional[str]:
        return self._headers["cc"][0] if "cc" in self._headers else None


    def header_subject(self) -> Optional[str]:
        return self._headers["subject"][0] if "subject" in self._headers else None


    def header_date(self) -> Optional[str]:
        return self._headers["date"][0] if "date" in self._headers else None


    def header_message_id(self) -> Optional[str]:
        return self._headers["message-id"][0] if "message-id" in self._headers else None


    def header_in_reply_to(self) -> Optional[str]:
        return self._headers["in-reply-to"][0] if "in-reply-to" in self._headers else None


    def header_references(self) -> Optional[str]:
        return self._headers["references"][0] if "references" in self._headers else None


    # Accessor for other headers:
    def header(self, header_name:str) -> List[str]:
        return self._headers[header_name]


    # Accessor for message body:
    def body(self) -> EmailMessage:
        msg = self._mailing_list._mail_archive._fs.get(self._gridfs_id)
        return email.message_from_bytes(msg.read(), policy=policy.default)


    # Find the messages that this is in reply to. Each message can only be
    # in reply to a single other message, but there may be multiple copies
    # of that message in the archive if it was sent to multiple lists, each
    # of which may have different replies.  This method returns all the copies.
    # If this is the first message in a thread, then an empty list is returned.
    def in_reply_to(self) -> List[Message]:
        in_reply_to = self.header_in_reply_to()
        references  = self.header_references()
        if in_reply_to is not None:
            parent = in_reply_to
        elif references is not None:
            parent = references.split(" ")[-1]
        else:
            return []
        parents = []
        for message in self._mailing_list._mail_archive._db.messages.find({"message_id": parent}):
            mailing_list = self._mailing_list._mail_archive.mailing_list(message["list"])
            uidvalidity  = message["uidvalidity"]
            uid          = message["uid"]
            gridfs_id    = message["gridfs_id"]
            timestamp    = message["timestamp"]
            size         = message["size"]
            headers      = message["headers"]
            parents.append(Message(mailing_list, uidvalidity, uid, gridfs_id, timestamp, size, headers))
        return parents


    def replies(self) -> List[Message]:
        replies = []
        for message in self._mailing_list._mail_archive._db.messages.find({"in_reply_to": self.header_message_id()}):
            mailing_list = self._mailing_list._mail_archive.mailing_list(message["list"])
            uidvalidity  = message["uidvalidity"]
            uid          = message["uid"]
            gridfs_id    = message["gridfs_id"]
            timestamp    = message["timestamp"]
            size         = message["size"]
            headers      = message["headers"]
            replies.append(Message(mailing_list, uidvalidity, uid, gridfs_id, timestamp, size, headers))
        return replies


# =================================================================================================

class MessageThread:
    def __init__(self, root: Message):
        self.root = root


    def get_message_count(self):
        pass # FIXME


    def get_unique_from_count(self):
        pass # FIXME


    def get_duration(self):
        pass # FIXME


# =================================================================================================

class MailingList:
    _log          : logging.Logger
    _mail_archive : MailArchive
    _list_name    : str
    _uidvalidity  : int

    def __init__(self, mail_archive: MailArchive, list_name: str):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self._log          = logging.getLogger("ietfdata")
        self._mail_archive = mail_archive
        self._list_name    = list_name
        ml = self._mail_archive._db.lists.find_one({"list": list_name})
        if ml is None:
            imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
            imap.login("anonymous", "anonymous")
            status_imap = imap.folder_status("Shared Folders/" + self._list_name)
            status_json = {
                "list"         : self._list_name,
                "uidvalidity"  : status_imap[b'UIDVALIDITY'],
            }
            self._mail_archive._db.lists.insert_one(status_json)
            imap.logout()
            self._log.info(f"Created cache for list {self._list_name}")
            self._uidvalidity = status_imap[b'UIDVALIDITY']
        else:
            self._uidvalidity = ml["uidvalidity"] #type: int


    def name(self) -> str:
        return self._list_name


    def uidvalidity(self) -> int:
        return self._uidvalidity


    def num_messages(self) -> int:
        return self._mail_archive._db.messages.count_documents({"list": self._list_name, "uidvalidity": self._uidvalidity})


    def message_uids(self) -> Iterator[int]:
        for msg in self._mail_archive._db.messages.find({"list" : self._list_name, "uidvalidity": self._uidvalidity}):
            yield msg["uid"]


    def message(self, uid: int) -> Optional[Message]:
        message = self._mail_archive._db.messages.find_one({"list" : self._list_name, "uidvalidity": self._uidvalidity, "uid": uid})
        if message is not None:
            uidvalidity = message["uidvalidity"]
            uid         = message["uid"]
            gridfs_id   = message["gridfs_id"]
            timestamp   = message["timestamp"]
            size        = message["size"]
            headers     = message["headers"]
            return Message(self, uidvalidity, uid, gridfs_id, timestamp, size, headers)
        else:
            return None


    def messages(self, since: str = "1970-01-01T00:00:00", until: str = "2038-01-19T03:14:07") -> Iterator[Message]:
        query = {"list"        : self._list_name,
                 "uidvalidity" : self._uidvalidity,
                 "timestamp"   : {
                     "$gt": datetime.strptime(since, "%Y-%m-%dT%H:%M:%S"),
                     "$lt": datetime.strptime(until, "%Y-%m-%dT%H:%M:%S")
                 }
                }
        messages = self._mail_archive._db.messages.find(query, no_cursor_timeout=True)
        for message in messages:
            uidvalidity = message["uidvalidity"]
            uid         = message["uid"]
            gridfs_id   = message["gridfs_id"]
            timestamp   = message["timestamp"]
            size        = message["size"]
            headers     = message["headers"]
            yield Message(self, uidvalidity, uid, gridfs_id, timestamp, size, headers)
        messages.close()


    def messages_as_dataframe(self,
                 since : str = "1970-01-01T00:00:00",
                 until : str = "2038-01-19T03:14:07") -> pd.DataFrame:
        messages_as_dict = []
        for message in self.messages(since = since, until = until):
            mdict = {"Message-ID"  : message.header_message_id(),
                     "From"        : message.header_from(),
                     "To"          : message.header_to(),
                     "Cc"          : message.header_cc(),
                     "Subject"     : message.header_subject(),
                     "Date"        : message.header_date(),
                     "In-Reply-To" : message.header_in_reply_to(),
                     "References"  : message.header_references()}
            messages_as_dict.append(mdict)
        df = pd.DataFrame(data=messages_as_dict)
        df.set_index("Message-ID", inplace=True)
        return df


    def update(self) -> List[int]:
        self._log.info(f"Updating list {self.name()}")
        imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
        imap.login("anonymous", "anonymous")

        folder_status = imap.folder_status("Shared Folders/" + self._list_name)
        if folder_status[b'UIDVALIDITY'] != self._uidvalidity:
            # if UIDVALIDITY has changed, the cache will be invalid and we must re-download
            # the entire folder. IMAP servers are supposed to ensure the UIDVALIDITY doesn't
            # change, but sometimes a re-index occurs on the server so we have to handle it.
            self._log.warn(f"UIDVALIDITY changed for mailing list {self._list_name}")
            # Remove messages with old uidvalidity:
            for msg in self._mail_archive._db.messages.find({"list": self._list_name, "uidvalidity": self._uidvalidity}):
                self._mail_archive._fs.delete(msg["gridfs_id"])
                self._mail_archive._db.messages.delete_one({"list" : self._list_name, "uidvalidity": self._uidvalidity, "uid" : msg['uid']})
            # Write the new uidvalidity to the database:
            list_status = {
                "list"        : self._list_name,
                "uidvalidity" : folder_status[b'UIDVALIDITY'],
            }
            self._mail_archive._db.lists.replace_one({"list" : self._list_name}, list_status)
            self._uidvalidity = folder_status[b'UIDVALIDITY']

        imap.select_folder("Shared Folders/" + self._list_name, readonly=True)
        server_messages = imap.search()
        cached_messages = list(self.message_uids())
        msgs_to_fetch   = []

        # Find the messages to fetch:
        for uid in server_messages:
            if uid not in cached_messages:
                msgs_to_fetch.append(uid)

        # Fetch the messages
        for i in range(0, len(msgs_to_fetch), 16):
            uid_slice = msgs_to_fetch[slice(i, i+16, 1)]
            for uid, msg in imap.fetch(uid_slice, "INTERNALDATE RFC822.SIZE RFC822").items():
                e = email.message_from_bytes(msg[b"RFC822"], policy=policy.default)
                # Extract the headers:
                headers = {}
                try:
                    for header in e.keys():
                        if header not in headers:
                            try:
                                headers[header.lower().replace(".", "-")] = e.get_all(header)
                            except Exception as ex:
                                self._log.info(f"cannot extract header {header} for {self._list_name}/{uid}")
                except:
                    self._log.info(f"cannot extract headers for {self._list_name}/{uid}")
                # Find the parent message:
                if "in-reply-to" in headers:
                    in_reply_to = headers["in-reply-to"][0]
                elif "references" in headers:
                    in_reply_to = headers["references"][0].split(" ")[-1]
                else:
                    in_reply_to = None
                # Save to MongoDB:
                cache_file_id = self._mail_archive._fs.put(msg[b"RFC822"])
                entry = {"list"        : self._list_name,
                         "uidvalidity" : self._uidvalidity,
                         "uid"         : uid,
                         "gridfs_id"   : cache_file_id,
                         "timestamp"   : msg[b"INTERNALDATE"],
                         "size"        : msg[b"RFC822.SIZE"],
                         "message_id"  : headers["message-id"][0] if "message-id" in headers else None,
                         "in_reply_to" : in_reply_to,
                         "headers"     : headers,
                }
                self._mail_archive._db.messages.insert_one(entry)
                self._log.info(f"saved message {self._list_name}/{uid}")

        imap.unselect_folder()
        imap.logout()
        return msgs_to_fetch


    #def threads(self) -> Iterator[MessageThread]:
    #    ts = TopologicalSorter()
    #    for msg in self.messages():
    #        if msg.header_references() is not None:
    #            ts.add(msg.header_message_id(), msg.header_references().split(" ").reverse())
    #        elif msg.header_in_reply_to() is not None:
    #            ts.add(msg.header_message_id(), msg.header_in_reply_to())
    #        else:
    #            ts.add(msg.header_message_id())
    #    for msg_id in ts.static_order():
    #        print(msg_id)


# =================================================================================================

# Private helper for MailArchive::update()
def _update_list(ml: MailingList) -> None:
    ml.update()


class MailArchive:
    _mongoclient   : MongoClient
    _db            : Database
    _fs            : GridFS
    _log           : logging.Logger
    _mailing_lists : Dict[str, MailingList]


    def __init__(self,
            mongodb_hostname : str = "localhost",
            mongodb_port     : int = 27017,
            mongodb_username : Optional[str] = None,
            mongodb_password : Optional[str] = None):
        # Enable logging
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self._log           = logging.getLogger("ietfdata")
        # Connect to MongoDB:
        cache_host     = os.environ.get('IETFDATA_CACHE_HOST',     mongodb_hostname)
        cache_port     = os.environ.get('IETFDATA_CACHE_PORT',     mongodb_port)
        cache_username = os.environ.get('IETFDATA_CACHE_USER',     mongodb_username)
        cache_password = os.environ.get('IETFDATA_CACHE_PASSWORD', mongodb_password)
        if cache_username is not None:
            self._mongoclient = MongoClient(host=cache_host, port=int(cache_port), username=cache_username, password=cache_password)
        else:
            self._mongoclient = MongoClient(host=cache_host, port=int(cache_port))
        self._db = self._mongoclient.ietfdata_mailarchive_v2
        self._db.messages.create_index([('list', ASCENDING), ('uidvalidity', ASCENDING), (       'uid', ASCENDING)], unique=True)
        self._db.messages.create_index([('list', ASCENDING), ('uidvalidity', ASCENDING), ( 'timestamp', ASCENDING)], unique=False)
        self._db.messages.create_index([('list', ASCENDING), ('uidvalidity', ASCENDING), ('message_id', ASCENDING)], unique=False)
        self._db.messages.create_index([('message_id', ASCENDING)], unique=False)
        self._db.lists.create_index([('list', ASCENDING)], unique=True)
        self._fs = GridFS(self._db)
        # Create other state:
        self._mailing_lists = {}


    def mailing_list_names(self) -> Iterator[str]:
        imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
        imap.login("anonymous", "anonymous")
        folders = imap.list_folders()
        imap.logout()
        for (flags, delimiter, name) in folders:
            if b'\Noselect' not in flags:
                yield name.split(delimiter.decode("utf-8"))[-1]


    def mailing_list(self, mailing_list_name: str) -> MailingList:
        if not mailing_list_name in self._mailing_lists:
            self._mailing_lists[mailing_list_name] = MailingList(self, mailing_list_name)
        return self._mailing_lists[mailing_list_name]


    def messages(self,
                 since : str = "1970-01-01T00:00:00",
                 until : str = "2038-01-19T03:14:07") -> Iterator[Message]:
        for ml_name in self.mailing_list_names():
            ml = self.mailing_list(ml_name)
            yield from ml.messages(since, until)


    def update(self) -> None:
        # WARNING: The first time this method is called, it will download the
        # entire mail archive. This will take several hours and download tens
        # of gigabytes of data. Subsequent calls will just fetch new data, so
        # will be much faster. Set the environment variable IETFDATA_LOGLEVEL
        # to INFO before running this to be informed of progress.
        with concurrent.futures.ThreadPoolExecutor(max_workers = 8) as executor:
            for ml_name in self.mailing_list_names():
                ml = self.mailing_list(ml_name)
                executor.submit(_update_list, ml)


# =================================================================================================
# vim: set tw=0 ai:
