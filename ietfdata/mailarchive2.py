# Copyright (C) 2020-2023 University of Glasgow
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
from typing             import Dict, Iterator, List, Optional, Tuple, Union, Any
from gridfs             import GridFS
from pymongo            import MongoClient, ASCENDING, ReplaceOne, UpdateOne
from pymongo.database   import Database
from email              import policy, utils
from email.message      import Message
from email_reply_parser import EmailReplyParser
from imapclient         import IMAPClient
from dataclasses        import field

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
# The `lists_metadata` collections contains documents of the form:
#
#   {
#     "list": "100attendees",
#     "project": "sodestream",
#     "key": "is_spam",
#     "value": False,
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
# The `parsed_headers` collections contains documents of the form:
#
#   { # FIXME: implement this
#     "list": "100attendees",
#     "uidvalidity": 1505323361m
#     "uid":  1,
#     "message_id": "<CAAiTEH9EVrZzF08F4T3z6QzhAnwBmKk9jhHEf=xMy-=3W4r9+Q@mail.gmail.com>",
#     "date": 2017-09-13T10:11:47.000+00:00,
#     "from": ["matt@conundrum.com"],        # DMARC rewriting undone, email address extracted
#     "to":   ["100attendees@ietf.org"],     # Email addresses extracted
#     "cc":   [],                            # Email addresses extracted
#   }
#
# The `metadata` collections contains documents of the form:
#
#   {
#     "list": "100attendees",
#     "uidvalidity": 1505323361
#     "uid":  1,
#     "message_id": "<CAAiTEH9EVrZzF08F4T3z6QzhAnwBmKk9jhHEf=xMy-=3W4r9+Q@mail.gmail.com>",
#     "project": "sodestream",
#     "key": "is_spam",
#     "value": False,
#   }
#
# =================================================================================================

class Envelope:
    _mailing_list  : MailingList
    _uidvalidity   : int
    _uid           : int
    _gridfs_id     : int
    _dste_received : datetime
    _size          : int
    _headers       : Dict[str, List[str]]

    def __init__(self,
                 ml            : MailingList,
                 uidvalidity   : int,
                 uid           : int,
                 gridfs_id     : int,
                 date_received : datetime,
                 size          : int,
                 headers       : Dict[str, List[str]]) -> None:
        self._mailing_list  = ml
        self._uidvalidity   = uidvalidity
        self._uid           = uid
        self._gridfs_id     = gridfs_id
        self._dste_received = date_received
        self._size          = size
        self._headers       = headers


    # Accessors for properties of the message in this Envelope.
    #
    # Messages in IMAP are assigned a unique identifier `uid()` within a folder
    # representing a mailing list. That identifier is not supposed to change,
    # but the IMAP standard recognises that mailboxes occasionally get rebuilt.
    # If this happens, the `uidvalidity()` will change. The combination of
    # mailing_list(), uid(), and uidvalidity() uniquely identifies a message on
    # the server.

    def mailing_list(self) -> MailingList:
        return self._mailing_list


    def uidvalidity(self) -> int:
        return self._uidvalidity


    def uid(self) -> int:
        return self._uid


    def date_received(self) -> datetime:
        return self._dste_received


    def size(self) -> int:
        return self._size


    def date(self) -> Optional[datetime]:
        """
        The "Date:" header from the Message within this Envelope, parsed into a
        `DateTime` object.

        This will return `None` if the "Date:" header is not present or cannot
        be parsed.

        The `header("date")` method can be used to return the unparsed "Date:"
        header as a `str`.
        """
        msg_date = None # type: Optional[datetime]
        try:
            parsed_date = email.utils.parsedate(self._headers["date"][0])
            if parsed_date is not None:
                msg_date = datetime.fromtimestamp(time.mktime(parsed_date))
            else:
                msg_date = None
        except:
            msg_date = None
        return msg_date


    def header(self, header_name:str) -> List[str]:
        """
        Accessor for the headers of the message in this Envelope.

        Some headers, e.g., "Received:" are expected to occur multiple times
        within a message and will return a list containing multiple items.

        Other headers, e.g., "From:", are only supposed to occur once in each
        message. In these cases, this method should return a list containing a
        single value. Note, however, that the IETF mail archive contains some
        malformed messages with unexpected duplicate headers. For example,
        there are some messages with two addresses in the "From:" line.
        """
        if not header_name in self._headers:
            return []
        else:
            return self._headers[header_name]


    def contents(self) -> Message:
        """
        Return the Message contained within this Envelope.
        """
        msg = self._mailing_list._mail_archive._fs.get(self._gridfs_id)
        return email.message_from_bytes(msg.read(), policy=policy.default)


    def in_reply_to(self) -> List[Envelope]:
        """
        Return the envelopes containing the messages that this is in reply to.

        Each message can only be in reply to a single other message, but there
        may be multiple copies of that message in the archive if it was sent to
        multiple lists, each of which may itself have different replies. This
        method returns all such copies.

        If this is the first message in a thread, then an empty list is returned.
        """
        in_reply_to = self.header("in-reply-to")
        references  = self.header("references")
        if len(in_reply_to) == 1:
            parent = in_reply_to[0]
        elif references is not None and len(references) > 0:
            parent = references[0].split(" ")[-1]
        else:
            return []
        parents = []
        for message in self._mailing_list._mail_archive._db.messages.find({"message_id": parent}):
            mailing_list  = self._mailing_list._mail_archive.mailing_list(message["list"])
            uidvalidity   = message["uidvalidity"]
            uid           = message["uid"]
            gridfs_id     = message["gridfs_id"]
            date_received = message["timestamp"]
            size          = message["size"]
            headers       = message["headers"]
            parents.append(Envelope(mailing_list, uidvalidity, uid, gridfs_id, date_received, size, headers))
        return parents


    def replies(self) -> List[Envelope]:
        """
        Return the envelopes containing the messages sent in reply to this.
        """
        replies = []
        for message in self._mailing_list._mail_archive._db.messages.find({"in_reply_to": self.header("message-id")[0]}):
            mailing_list  = self._mailing_list._mail_archive.mailing_list(message["list"])
            uidvalidity   = message["uidvalidity"]
            uid           = message["uid"]
            gridfs_id     = message["gridfs_id"]
            date_received = message["timestamp"]
            size          = message["size"]
            headers       = message["headers"]
            replies.append(Envelope(mailing_list, uidvalidity, uid, gridfs_id, date_received, size, headers))
        return replies


    def add_metadata(self, project:str, key:str, value):
        """
        Add metadata relating to the message in this envelope.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata should be scored
        - `value`   -- the value of the metadata to store

        The `project` is intended to allow different users to store metadata
        in a shared mail archive database. For example, a group project that
        works with the mail archive might tag message envelopes with agreed-
        upon metadata using the project's name in the `project` field, while
        exploratory work from individual members of the project might use
        their username as the basis for the `project` (e.g., "alice_test4").
        """
        entry = {"list"        : self.mailing_list().name(),
                 "uidvalidity" : self.uidvalidity(),
                 "uid"         : self.uid(),
                 "message_id"  : self._headers["message-id"][0] if "message-id" in self._headers else None,
                 "project"     : project,
                 "key"         : key,
                 "value"       : value,
        }
        self._mailing_list._mail_archive._db.metadata.insert_one(entry)


    def get_metadata(self, project:str, key:str):
        """
        Get metadata relating to the message in this envelope.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata was scored
        """
        query = {"list"        : self.mailing_list().name(),
                 "uidvalidity" : self.uidvalidity(),
                 "uid"         : self.uid(),
                 "project"     : project,
                 "key"         : key}
        result = self._mailing_list._mail_archive._db.metadata.find_one(query) # type: Optional[Dict[str, Any]]
        if result is not None:
            return result["value"]
        else:
            return None


    def clear_metadata(self, project:str, key:Optional[str] = None):
        """
        Remove metadata relating to the message in this envelope.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata was scored

        If the `key` is specified then only the single metadata value
        identified by the `project` and `key` is removed. If the `key`
        is not specified, then all metadata relating to `project` is
        removed from this envelope.
        """
        query = {"list"        : self.mailing_list().name(),
                 "uidvalidity" : self.uidvalidity(),
                 "uid"         : self.uid(),
                 "project"     : project}
        if key is not None:
            query["key"] = key
        self._mailing_list._mail_archive._db.metadata.delete_many(query)


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
            imap = IMAPClient(host=self._mail_archive._imap_server, ssl=True, use_uid=True)
            imap.login("anonymous", "anonymous")

            _, _, imap_ns_shared = imap.namespace()
            imap_prefix    = imap_ns_shared[0][0]
            imap_separator = imap_ns_shared[0][1]

            status_imap = imap.folder_status(f"{imap_prefix}{self._list_name}")
            status_json = {
                "list"         : self._list_name,
                "uidvalidity"  : status_imap[b'UIDVALIDITY'],
            }
            self._mail_archive._db.lists.insert_one(status_json)
            imap.logout()
            self._uidvalidity = status_imap[b'UIDVALIDITY']
            self._log.info(f"Created cache for list {self._list_name}")
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


    def message(self, uid: int) -> Optional[Envelope]:
        """
        Return the Envelope containing the Message identified by the
        specified uid within this mailing list.
        """
        message = self._mail_archive._db.messages.find_one({"list" : self._list_name, "uidvalidity": self._uidvalidity, "uid": uid})
        if message is not None:
            uidvalidity = message["uidvalidity"]
            uid         = message["uid"]
            gridfs_id   = message["gridfs_id"]
            timestamp   = message["timestamp"]
            size        = message["size"]
            headers     = message["headers"]
            return Envelope(self, uidvalidity, uid, gridfs_id, timestamp, size, headers)
        else:
            return None


    def messages(self,
                 received_after: str = "1970-01-01T00:00:00",
                 received_before: str = "2038-01-19T03:14:07") -> Iterator[Envelope]:
        """
        Return the envelopes containing the specified messages from this mailing list.
        """
        query = {"list"        : self._list_name,
                 "uidvalidity" : self._uidvalidity,
                 "timestamp"   : {
                     "$gt": datetime.strptime(received_after,  "%Y-%m-%dT%H:%M:%S"),
                     "$lt": datetime.strptime(received_before, "%Y-%m-%dT%H:%M:%S")
                 }
                }
        messages = self._mail_archive._db.messages.find(query, sort=[("uid", ASCENDING)], batch_size=100)
        for message in messages:
            uidvalidity = message["uidvalidity"]
            uid         = message["uid"]
            gridfs_id   = message["gridfs_id"]
            timestamp   = message["timestamp"]
            size        = message["size"]
            headers     = message["headers"]
            yield Envelope(self, uidvalidity, uid, gridfs_id, timestamp, size, headers)


    def messages_as_dataframe(self,
                              received_after  : str = "1970-01-01T00:00:00",
                              received_before : str = "2038-01-19T03:14:07") -> pd.DataFrame:
        """
        Return a dataframe containing information about the specified messages from
        this mailing list.
        """
        messages_as_dict = []
        for message in self.messages(received_after = received_after, received_before = received_before):
            mdict = {"Message-ID"  : message.header("message-id")[0] if message.header("message-id") != [] else None,
                     "From"        : message.header("from")[0],
                     "To"          : message.header("to"),
                     "Cc"          : message.header("cc"),
                     "Subject"     : message.header("subject")[0],
                     "Date"        : message.date(),
                     "In-Reply-To" : message.header("in-reply-to") if message.header("in-reply-to") != [] else None,
                     "References"  : message.header("references"),
                    }
            messages_as_dict.append(mdict)
        df = pd.DataFrame(data=messages_as_dict)
        df.set_index("Message-ID", inplace=True)
        return df


    # FIXME: this should update the parsed_headers database collection
    def update(self, verbose=True) -> List[int]:
        """
        Update the local copy of this mailing list from the IMAP server.

        This MUST be called at least once for each mailing list, else no
        messages will be retrieved from the server. That initial update
        may well be slow, since it downloads the entire set of messages
        from the list. Subsequent calls to `update()` only fetch the new
        messages and so are much faster.
        """
        if verbose:
            print(f"[mailarchive] Check {self._list_name}")

        # Login to the IMAP server:
        self._log.info(f"Updating list {self.name()}")
        imap = IMAPClient(host=self._mail_archive._imap_server, ssl=True, use_uid=True)
        imap.login("anonymous", "anonymous")
        _, _, imap_ns_shared = imap.namespace()
        imap_prefix    = imap_ns_shared[0][0]
        imap_separator = imap_ns_shared[0][1]
        folder_status  = imap.folder_status(f"{imap_prefix}{self._list_name}")

        # If UIDVALIDITY has changed, the cache will be invalid and we must re-download
        # the entire folder. IMAP servers are supposed to ensure the UIDVALIDITY doesn't
        # change, but sometimes a re-index occurs on the server so we have to handle it.
        if folder_status[b'UIDVALIDITY'] != self._uidvalidity:
            self._log.warn(f"UIDVALIDITY changed for mailing list {self._list_name}")
            # Remove messages with old uidvalidity:
            for msg in self._mail_archive._db.messages.find({"list": self._list_name, "uidvalidity": self._uidvalidity}):
                self._mail_archive._fs.delete(msg["gridfs_id"])
                self._mail_archive._db.messages.delete_one({"list" : self._list_name, "uidvalidity": self._uidvalidity, "uid" : msg['uid']})
                if verbose:
                    print(f"[mailarchive] Remove {self._list_name}/{msg['uid']} due to UIDVALIDITY change")
            # Write the new uidvalidity to the database:
            list_status = {
                "list"        : self._list_name,
                "uidvalidity" : folder_status[b'UIDVALIDITY'],
            }
            self._mail_archive._db.lists.replace_one({"list" : self._list_name}, list_status)
            self._uidvalidity = folder_status[b'UIDVALIDITY']

        # Find the messages to fetch:
        imap.select_folder(f"{imap_prefix}{self._list_name}", readonly=True)
        server_messages = imap.search()
        cached_messages = list(self.message_uids())
        msgs_to_fetch   = []
        for uid in server_messages:
            if uid not in cached_messages:
                msgs_to_fetch.append(uid)

        # Fetch the messages:
        for i in range(0, len(msgs_to_fetch), 16):
            uid_slice = msgs_to_fetch[slice(i, i+16, 1)]
            for uid, msg in imap.fetch(uid_slice, "INTERNALDATE RFC822.SIZE RFC822").items():
                if verbose:
                    print(f"[mailarchive] Fetch {self._list_name}/{uid}")
                e = email.message_from_bytes(msg[b"RFC822"], policy=policy.default)
                # Extract the headers:
                headers = {}
                try:
                    for header in e.keys():
                        if header not in headers:
                            try:
                                header_values = e.get_all(header)
                                if header_values is not None:
                                    headers[header.lower().replace(".", "-")] = header_values
                            except Exception as ex:
                                self._log.warn(f"Cannot extract header {header} for {self._list_name}/{uid}")
                except:
                    self._log.warn(f"Cannot extract headers for {self._list_name}/{uid}")
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


    def threads(self, this_list_only=False) -> Dict[str, List[Envelope]]:
        """
        Returns a dictionary of threads in this mailing list.

        The dictionary returned maps message-id values of the first messages in
        each thread to lists of the Envelope objects containing that message.

        Threads frequently start on one mailing list and have later messages
        sent to a different mailing list. If you have a complete copy of the
        mail archive (i.e., if you previously called `MailArchive::update()`),
        then this function will track threads across lists to find the first
        message in each (unless `this_list_only` is set to True).

        The first message in a thread can be copied to several mailing lists.
        If this happens, the message-id for the thread will map to a list of
        Envelope objects, each representing a copy of the message sent to a
        different mailing list.
        If the first message in the thread was only sent to a single mailing
        list, then the message-id for the thread will map onto a list with a
        single Envelope.
        """
        threads = {}
        seen    = {} # type: Dict[str,Envelope]
        for msg in self.messages():
            if len(msg.header("message-id")) > 0:
                msg_id  = msg.header("message-id")[0]
                seen[msg_id] = msg
    
                self._log.debug(f"{msg.uid():5} {msg.header('message-id')} {msg.header('subject')}")
    
                parents = msg.in_reply_to()
                if len(parents) == 0:
                    # This is the first message in the thread
                    if msg.header("message-id")[0] not in threads:
                        threads[msg.header("message-id")[0]] = [msg]
                    self._log.debug("      First in thread")
                elif parents[0].header("message-id")[0] in seen:
                    # This is part of a thread we've already seen
                    self._log.debug(f"      {parents[0].header('message-id')} {parents[0].header('subject')}")
                    self._log.debug(f"      Continues known thread")
                else:
                    # This is either a new thread that has been copied to this list
                    # where the earlier messages in the thread are on another list,
                    # or this message is part of an existing thread but has arrived
                    # before its parent.
                    curr = []
                    curr.append(msg)
                    while True:
                        parents = curr[0].in_reply_to()
    
                        parent_in_this_list = False
                        for p in parents:
                            if p.mailing_list() == self.name():
                                parent_in_this_list = True
                        if not parent_in_this_list and this_list_only:
                            self._log.debug(f"      {parents[0].header('message-id')} {parents[0].header('subject')}")
                            self._log.debug(f"      Not in this list")
                            if curr[0].header("message-id")[0] not in threads:
                                threads[curr[0].header("message-id")[0]] = curr
                            break
    
                        if len(parents) == 0:
                            self._log.debug("      First in thread")
                            if curr[0].header("message-id")[0] not in threads:
                                threads[curr[0].header("message-id")[0]] = curr
                            break
                        curr = parents
                        self._log.debug(f"      {curr[0].header('message-id')} {curr[0].header('subject')}")
        return threads


    def add_metadata(self, project:str, key:str, value):
        """
        Add metadata relating to the list.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata should be scored
        - `value`   -- the value of the metadata to store

        The `project` is intended to allow different users to store metadata
        in a shared mail archive database. For example, a group project that
        works with the mail archive might tag message envelopes with agreed-
        upon metadata using the project's name in the `project` field, while
        exploratory work from individual members of the project might use
        their username as the basis for the `project` (e.g., "alice_test4").
        """
        entry = {"list"    : self._list_name,
                 "project" : project,
                 "key"     : key,
                 "value"   : value,
        }
        self._mail_archive._db.lists_metadata.insert_one(entry)


    def get_metadata(self, project:str, key:str):
        """
        Get metadata relating to the list.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata was scored
        """
        query = {"list"    : self._list_name,
                 "project" : project,
                 "key"     : key}
        result = self._mail_archive._db.lists_metadata.find_one(query) # type: Optional[Dict[str, Any]]
        if result is not None:
            return result["value"]
        else:
            return None


    def clear_metadata(self, project:str, key:Optional[str] = None):
        """
        Remove metadata relating to the list.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata was scored

        If the `key` is specified then only the single metadata value
        identified by the `project` and `key` is removed. If the `key`
        is not specified, then all metadata relating to `project` is
        removed from this envelope.
        """
        query = {"list"    : self._list_name,
                 "project" : project}
        if key is not None:
            query["key"] = key
        self._mail_archive._db.lists_metadata.delete_many(query)

# =================================================================================================

class MailArchive:
    """
    A class representing the IETF email archive.
    """

    _log           : logging.Logger
    _imap_server   : str
    _mongoclient   : MongoClient
    _db            : Database
    _fs            : GridFS
    _mailing_lists : Dict[str, MailingList]

    def __init__(self,
                 imap_server      : str = "imap.ietf.org",
                 mongodb_hostname : str = "localhost",
                 mongodb_port     : str = "27017",
                 mongodb_username : Optional[str] = None,
                 mongodb_password : Optional[str] = None):
        """
        Initialise the MailArchive.
        """
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self._log         = logging.getLogger("ietfdata")
        self._imap_server = imap_server
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
        self._db.lists.create_index([('list', ASCENDING),
                                    ], unique=True)
        self._db.lists_metadata.create_index([('list', ASCENDING),
                                              ('project', ASCENDING),
                                              ('key', ASCENDING),
                                             ], unique=True)

        self._db.messages.create_index([('list', ASCENDING),
                                        ('uidvalidity', ASCENDING),
                                        ('uid', ASCENDING),
                                       ], unique=True)
        self._db.messages.create_index([('list', ASCENDING),
                                        ('uidvalidity', ASCENDING),
                                        ('message_id', ASCENDING),
                                       ], unique=False)
        self._db.messages.create_index([('message_id', ASCENDING),
                                       ], unique=False)

        self._db.metadata.create_index([('list', ASCENDING), 
                                        ('uidvalidity', ASCENDING), 
                                        ('uid', ASCENDING),
                                        ('project', ASCENDING),
                                        ('key', ASCENDING),
                                       ], unique=False)
        self._db.metadata.create_index([('message_id', ASCENDING)
                                       ], unique=False)
        self._db.metadata.create_index([('in_reply_to', ASCENDING)
                                       ], unique=False)
        self._fs = GridFS(self._db)
        # Create other state:
        self._mailing_lists = {}


    def mailing_list_names(self) -> Iterator[str]:
        """
        Yield the names of the mailing lists that exist in the mail archive.
        """
        imap = IMAPClient(host=self._imap_server, ssl=True, use_uid=True)
        imap.login("anonymous", "anonymous")
        folders = imap.list_folders()
        imap.logout()
        for (flags, delimiter, name) in folders:
            if b'\Noselect' not in flags:
                yield name.split(delimiter.decode("utf-8"))[-1]


    def mailing_list(self, mailing_list_name: str) -> MailingList:
        """
        Return an object representing the given mailing list.
        """
        if not mailing_list_name in self._mailing_lists:
            self._mailing_lists[mailing_list_name] = MailingList(self, mailing_list_name)
        return self._mailing_lists[mailing_list_name]


    def message(self, message_id:str) -> List[Envelope]:
        """
        Return the envelopes for all messages with the specified `message_id`.

        There can be multiple copies of a message with a particular ID in the
        archive if it was sent to multiple lists. This method returns all the
        copies, since each copy might have a different set of replies.  For
        example, message "<396c8d37-f979-73fe-34fa-475a038b94f8@alum.mit.edu>"
        appears in the archives of the "art", "last-call", and "tsvwg" lists.
        """
        messages = []
        for message in self._db.messages.find({"message_id": message_id}):
            mailing_list  = self.mailing_list(message["list"])
            uidvalidity   = message["uidvalidity"]
            uid           = message["uid"]
            gridfs_id     = message["gridfs_id"]
            date_received = message["timestamp"]
            size          = message["size"]
            headers       = message["headers"]
            messages.append(Envelope(mailing_list, uidvalidity, uid, gridfs_id, date_received, size, headers))
        return messages


    # FIXME: add `addr_from`, `addr_to`, `addr_cc`, `sent_after`, `sent_before`
    # parameters, operating on the parsed_headers database collection
    def messages(self,
                 received_after    : str = "1970-01-01T00:00:00",
                 received_before   : str = "2038-01-19T03:14:07",
                 header_from       : Optional[str] = None,
                 header_to         : Optional[str] = None,
                 header_subject    : Optional[str] = None,
                 mailing_list_name : Optional[str] = None,
                ) -> Iterator[Envelope]:
        """
        Return the envelopes of all specified messages in the archive.
        """
        query = {"timestamp"   : {
                     "$gt": datetime.strptime(received_after,  "%Y-%m-%dT%H:%M:%S"),
                     "$lt": datetime.strptime(received_before, "%Y-%m-%dT%H:%M:%S")
                 }
                } # type: Dict[str, Union[str, Dict[str, Any]]]
        if header_from is not None:
            query["headers.from"] = { "$regex": f"{header_from}"}
        if header_to is not None:
            query["headers.to"] = { "$regex": f"{header_to}"}
        if header_subject is not None:
            query["headers.subject"] = { "$regex": f"{header_subject}"}
        if mailing_list_name is not None:
            query["list"] = mailing_list_name
        messages = self._db.messages.find(query, no_cursor_timeout=True)
        for message in messages:
            mailing_list = self.mailing_list(message["list"])
            uidvalidity  = message["uidvalidity"]
            uid          = message["uid"]
            gridfs_id    = message["gridfs_id"]
            timestamp    = message["timestamp"]
            size         = message["size"]
            headers      = message["headers"]
            yield Envelope(mailing_list, uidvalidity, uid, gridfs_id, timestamp, size, headers)
        messages.close()


    def update(self, verbose = True) -> None:
        """
        Update the local cache of the messages from all the mailing lists.

        This method should be called when working with a complete copy of
        the mail archive to synchronise the local copy with the IETF IMAP
        server.

        To only download a subset of the messages, use the `mailing_list()`
        method to get a MailingList object for the lists of interest, then
        call the `update()` method on those objects.

        WARNING: The first time this method is called, it will download the
        entire mail archive. This will take several hours and download tens
        of gigabytes of data. Subsequent calls will just fetch new data and
        so will be much faster.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers = 8) as executor:
            for ml_name in self.mailing_list_names():
                ml = self.mailing_list(ml_name)
                executor.submit(lambda mailing_list : mailing_list.update(verbose), ml)


    def clear_metadata(self, project: str):
        """
        Remove metadata relating to the project from all mailing lists
        and message envelopes.

        WARNING: This is a destructive operation that should not normally
        be needed. Use with care.
        """
        self._db.lists_metadata.delete_many({"project": project})
        self._db.metadata.delete_many({"project": project})


# =================================================================================================
# vim: set tw=0 ai:
