# Copyright (C) 2020-2025 University of Glasgow
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

import pandas as pd
import os
import logging
import re
import sqlite3
import sys
import time

from datetime             import date, datetime, timedelta, timezone, UTC
from email                import policy, message_from_bytes
from email.headerregistry import Address
from email.message        import Message
from email.parser         import BytesHeaderParser
from email.policy         import EmailPolicy
from email.utils          import parseaddr, parsedate_to_datetime, getaddresses, unquote
from graphlib             import TopologicalSorter
from imapclient           import IMAPClient
from pathlib              import Path
from typing               import Dict, Iterator, List, Optional, Tuple, Union, Any

# The mailarchive3 package is intended to be a drop-in replacement for the
# mailarchive2 package, storing messages in a local sqlite3 database rather
# than a MongoDB instance.

# =================================================================================================

class Envelope:
    _archive       : MailArchive
    _message_num   : int
    _mailing_list  : str
    _uidvalidity   : int
    _uid           : int
    _message       : bytes
    _size          : int
    _date_received : str

    def __init__(self, mail_archive: MailArchive, message_num : int) -> None:
        """
        This differs from mailarchive2 but should not be called by user code.
        """
        self._archive = mail_archive
        self._message_num = message_num

        dbc = self._archive._db.cursor()
        sql = "SELECT mailing_list, uidvalidity, uid, message, size, date_received FROM ietf_ma_msg WHERE message_num = ?;"
        res = dbc.execute(sql, (message_num, )).fetchone()
        self._mailing_list  = res[0]
        self._uidvalidity   = res[1]
        self._uid           = res[2]
        self._message       = res[3]
        self._size          = res[4]
        self._date_received = res[5]

    # Accessors for properties of the message in this Envelope.
    #
    # Messages in IMAP are assigned a unique identifier `uid()` within a folder
    # representing a mailing list. That identifier is not supposed to change,
    # but the IMAP standard recognises that mailboxes occasionally get rebuilt.
    # If this happens, the `uidvalidity()` will change. The combination of
    # mailing_list(), uid(), and uidvalidity() uniquely identifies a message on
    # the server.

    def mailing_list(self) -> MailingList:
        return self._archive.mailing_list(self._mailing_list)


    def uidvalidity(self) -> int:
        return self._uidvalidity


    def uid(self) -> int:
        return self._uid


    def date_received(self) -> datetime:
        return datetime.fromisoformat(self._date_received).astimezone(UTC)


    def size(self) -> int:
        return self._size


    def message_id(self) -> str:
        dbc = self._archive._db.cursor()
        sql = "SELECT message_id FROM ietf_ma_hdr WHERE message_num = ?;"
        res = dbc.execute(sql, (self._message_num, )).fetchone()
        return str(res[0])


    def from_(self) -> Address:
        """
        Retrieve the parsed "From:" address from the message.

        The mailarchive3 library uses a number of heuristics to correct
        malformed headers, so the value returned might differ from the
        uncorrected value returned by calling `header("from")`.

        New in mailarchive3.
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT from_name, from_addr FROM ietf_ma_hdr WHERE message_num = ?;"
        res = dbc.execute(sql, (self._message_num, )).fetchone()
        return Address(display_name = res[0], addr_spec = res[1])


    def to(self) -> List[Address]:
        """
        Retrieve the parsed "To:" address from the message.

        The mailarchive3 library uses a number of heuristics to correct
        malformed headers, so the value returned might differ from the
        uncorrected value returned by calling `header("to")`.

        New in mailarchive3
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT to_name, to_addr FROM ietf_ma_hdr_to WHERE message_num = ?;"
        res = []
        for name, addr in dbc.execute(sql, (self._message_num, )).fetchall():
            res.append(Address(display_name = name, addr_spec = addr))
        return res


    def cc(self) -> List[Address]:
        """
        Retrieve the parsed "Cc:" address from the message.

        The mailarchive3 library uses a number of heuristics to correct
        malformed headers, so the value returned might differ from the
        uncorrected value returned by calling `header("cc")`.

        New in mailarchive3
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT cc_name, cc_addr FROM ietf_ma_hdr_cc WHERE message_num = ?;"
        res = []
        for name, addr in dbc.execute(sql, (self._message_num, )).fetchall():
            res.append(Address(display_name = name, addr_spec = addr))
        return res


    def subject(self) -> str:
        """
        Retrieve the parsed "Subject:" header from the message.

        The mailarchive3 library uses a number of heuristics to correct
        malformed headers, so the value returned might differ from the
        uncorrected value returned by calling `header("subject")`.

        New in mailarchive3
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT subject FROM ietf_ma_hdr WHERE message_num = ?;"
        res = dbc.execute(sql, (self._message_num, )).fetchone()
        return str(res[0])


    def date(self) -> Optional[datetime]:
        """
        Retrieve the "Date:" header from the message, parsed into a `DateTime`
        object.

        This will return `None` if the "Date:" header is not present or cannot
        be parsed.

        The `header("date")` method can be used to return the unparsed "Date:"
        header as a `str`. The mailarchive3 library uses a number of heuristics
        to correct malformed headers so the value returned by this method might
        differ from the uncorrected value returned by calling `header("date")`.
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT date FROM ietf_ma_hdr WHERE message_num = ?;"
        res = dbc.execute(sql, (self._message_num, )).fetchone()
        return datetime.fromisoformat(res[0]).astimezone(UTC)


    def header(self, header_name:str) -> List[str]:
        """
        Retrieve unparsed headers from the message.

        Do not use this method in you can avoid it: use the `from_()`, `to()`,
        `cc()`, `subject()`, `date()`, and `message_id()` methods instead. The
        mailarchive3 library uses a number of heuristics to correct malformed
        headers, but those heuristics are not applied to the values returned by
        this method. 

        Some headers, e.g., "Received:" are expected to occur multiple times
        within a message and will return a list containing multiple items.

        Other headers, e.g., "From:", are only supposed to occur once in each
        message. In these cases, this method should return a list containing a
        single value. Note, however, that the IETF mail archive contains some
        malformed messages with unexpected duplicate headers. For example,
        there are some messages with two addresses in the "From:" line.
        """
        msg = message_from_bytes(self._message, policy=policy.default)
        try:
            res = msg.get_all(header_name)
            if res is None:
                return []
            else:
                return res
        except:
            self._archive._log.warning(f"mailarchive3:envelope:header: cannot parse \"{header_name}\" header")
            return []


    def contents(self) -> Message:
        """
        Return the Message contained within this Envelope.
        """
        return message_from_bytes(self._message, policy=policy.default)


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
        if in_reply_to is not None and len(in_reply_to) > 0:
            parent = in_reply_to[0]
        elif references is not None and len(references) > 0:
            parent = references[0].split(" ")[-1]
        else:
            return []
        return self._archive.message(parent)


    def replies(self) -> List[Envelope]:
        """
        Return the envelopes containing the messages sent in reply to this.
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT message_num FROM ietf_ma_hdr WHERE in_reply_to = ?;"
        replies = []
        for message_num in dbc.execute(sql, (self.message_id(), )).fetchall():
            replies.append(Envelope(self._archive, message_num[0]))
        return replies


    def add_metadata(self, project:str, key:str, value:str) -> None:
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
        dbc = self._archive._db.cursor()
        sql = """INSERT OR REPLACE INTO ietf_ma_msg_metadata
                 VALUES ((SELECT id FROM ietf_ma_msg_metadata WHERE message_num = ? and project = ? AND key_ = ?), ?, ?, ?, ?)"""
        dbc.execute(sql, (self._message_num, project, key, self._message_num, project, key, value))
        self._archive._db.commit()


    def get_metadata(self, project:str, key:str) -> Optional[str]:
        """
        Get metadata relating to the message in this envelope.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata was scored
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT value FROM ietf_ma_msg_metadata WHERE message_num = ? AND project = ? AND key_ = ?;"
        res = dbc.execute(sql, (self._message_num, project, key)).fetchone()
        if res is None:
            return None
        else:
            return str(res[0])


    def clear_metadata(self, project:str, key:Optional[str] = None) -> None:
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
        dbc = self._archive._db.cursor()
        if key is None:
            sql = "DELETE FROM ietf_ma_msg_metadata WHERE message_num = ? AND project = ?;"
            dbc.execute(sql, (self._message_num, project))
        else:
            sql = "DELETE FROM ietf_ma_msg_metadata WHERE message_num = ? AND project = ? AND key_ = ?;"
            dbc.execute(sql, (self._message_num, project, key))
        self._archive._db.commit()




# =================================================================================================

class EmailPolicyCustom(EmailPolicy):
    """
    This is a private helper class - do not use.
    """
    def __init__(self, **kw):
        super().__init__(**kw)


    def header_source_parse(self, sourcelines):
        name, value = sourcelines[0].split(':', 1)
        value = ''.join((value, *sourcelines[1:])).lstrip(' \t\r\n')
        value = value.rstrip('\r\n')

        if name.lower() == "to" or name.lower() == "cc":
            value = value.replace("\r\n", "")
            patterns_to_replace = [
                # Many messages sent to ietf-announce have malformed "To:" and "Cc:" headers,
                # some of which are so corrupt that they make the Python email package throw
                # an exception ('Group' object has no attribute 'local_part').  Rewrite such
                # headers to use the canonical ietf-announce@ietf.org list address.
                (r'("IETF-Announce:; ; ; ; ; @tis.com"@tis.com[; ]+ , )(.*)', r'ietf-announce@ietf.org, \2'), 
                (r'(.*)(IETF-Announce:[ ;,]+[a-zA-Z\.@:;-]+$)', r'\1ietf-announce@ietf.org'),
                (r'(.*)(IETF-Announce:(; )+[; a-z\.@\r\n]+)',   r'\1ietf-announce@ietf.org'),
                (r'(.*)(<"?IETF-Announce:"?)([a-z0-9\.@;"]+)?(>)(, @tislabs.com@tislabs.com)?(.*)',  r'\1<ietf-announce@ietf.org>\6'),
                (r'IETF-Announce: ;, tis.com@CNRI.Reston.VA.US, tis.com@magellan.tis.com',           r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;, "localhost.MIT.EDU": cclark@ietf.org;',                         r'ietf-announce@ietf.org'),
                (r'IETF-Announce: @IETF.CNRI.Reston.VA.US:;, IETF.CNRI.Reston.VA.US@isi.edu',        r'ietf-announce@ietf.org'),
                (r'IETF-Announce <IETF-Announce:@auemlsrv.firewall.lucent.com;>',                    r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;,  "CNRI.Reston.VA.US" <@sun.com:CNRI.Reston.VA.US@eng.sun.com>', r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;,  "neptune.tis.com" <@tis.com, @baynetworks.com:neptune.tis.com@baynetworks.com>, tis.com@tis.com', r'ietf-announce@ietf.org'),
                (r'IETF-Announce: "IETF-Announce:;@IETF.CNRI.Reston.VA.US@PacBell.COM" <>;,  IETF.CNRI.Reston.VA.US@pacbell.com', r'ietf-announce@ietf.org'),
                (r'IETF-Announce: %IETF.CNRI.Reston.VA.US@tgv.com;',  r'ietf-announce@ietf.org'),
                (r'(IETF-Announce: ; ; ; , )(@pa.dec.com[ ;,]+)+',    r'ietf-announce@ietf.org'), 
                (r'IETF-Announce:;;;@gis.net;',              r'ietf-announce@ietf.org'),
                (r'IETF-Announce:;;@gis.net',                r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@ietf.org, ;;;@ietf.org;',  r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@cisco.com, ";"@cisco.com', r'ietf-announce@ietf.org'),
                (r'IETF-Announce:, ";"@cisco.com',           r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@cisco.com',                r'ietf-announce@ietf.org'),
                (r'"IETF-Announce:"@netcentrex.net',         r'ietf-announce@ietf.org'),
                (r'IETF-Announce:@above.proper.com',         r'ietf-announce@ietf.org'),
                (r'IETF-Announce:all-ietf@ietf.org',         r'ietf-announce@ietf.org'),
                (r'i IETF-Announce: ;',                      r'ietf-announce@ietf.org'),
                (r'IETF-Announce: ;',                        r'ietf-announce@ietf.org'),
                (r'IETF-Announce:;',                         r'ietf-announce@ietf.org'),
                (r'IETF-Announce:',                          r'ietf-announce@ietf.org'),
                # Rewrite variants of "undisclosed-recipients; ;" into a consistent form:
                (r'("?[Uu]ndisclosed.recipients"?: ;+)(, @[a-z\.]+)?(.*)',                        r'undisclosed-recipients: ;\3'),
                (r'(.*)(unlisted-recipients:; \(no To-header on input\))(.*)',                    r'\1undisclosed-recipients: ;\3'),
                (r'(.*)(random-recipients:;;;@cs.utk.edu; \(info-mime and ietf-822 lists\))(.*)', r'\1undisclosed-recipients: ;\3'),
                (r'(.*)("[A-Za-z\.]+":;+@tislabs.com;;;)(.*)',                                    r'\1undisclosed-recipients: ;\3'),
                (r'undisclosed-recipients:;;:;',                                                  r'undisclosed-recipients: ;'),
                # Rewrite other problematic headers:
                (r'(moore@cs.utk.edu)?(, )?(authors:;+@cs.utk.edu;+)(.*)', r'\1\4'),
                (r'(RFC 3023 authors: ;)',                                 r'mmurata@trl.ibm.co.jp, simonstl@simonstl.com, dan@dankohn.com'),
                (r'=\?ISO-8859-1\?B\?QWJhcmJhbmVsLA0KICAgIEJlbmphbWlu\?=', r'Benjamin Abarbanel'),
                (r'=\?ISO-8859-15\?B\?UGV0ZXJzb24sDQogICAgSm9u\?=',        r'Jon Peterson'),
            ]
            for (pattern, replacement) in patterns_to_replace:
                new_value = re.sub(pattern, replacement, value)
                if new_value != value:
                    # print(f"header_reader: [{value}] -> [{new_value}]")
                    value = new_value
                    break

        return (name, value)




def _parse_hdr_from(uid, msg):
    """
    This is a private helper function - do not use.
    """
    hdr = msg["from"]
    if hdr is None:
        # The "From:" header is missing
        return (None, None)
    else:
        addr_list = getaddresses([hdr])
        if len(addr_list) == 0:
            # The "From:" header is present but empty
            from_name = None
            from_addr = None
        elif len(addr_list) == 1:
            # The "From:" header contains a single well-formed address.
            from_name, from_addr = addr_list[0]
        elif len(addr_list) > 1:
            # The "From:" header contains multiple well-formed addresses; use the first one with a valid domain.
            from_name = None
            from_addr = None
            for group in hdr.groups:
                if   len(group.addresses) == 0:
                    pass
                elif len(group.addresses) == 1:
                    if "." in group.addresses[0].domain: # We consider the domain to be valid if it contains a "."
                        from_name = group.addresses[0].display_name
                        from_addr = group.addresses[0].addr_spec
                        break
                else:
                    raise RuntimeError(f"Cannot parse \"From:\" header: uid={uid} - multiple addresses in group")
            # print(f"parse_hdr_from: ({uid}) multiple addresses [{hdr}] -> [{from_name}],[{from_addr}]")
        else:
            raise RuntimeError(f"Cannot parse \"From:\" header: uid={uid} cannot happen")
            sys.exit(1)

        if from_addr == "":
           from_addr = None

        if from_name == "":
            from_name = None

        return (from_name, from_addr)


def _parse_hdr_to_cc(uid, msg, to_cc):
    """
    This is a private helper function - do not use.
    """
    try:
        hdr = msg[to_cc]
        if hdr is None:
            return []
        else:
            try:
                headers = []
                index = 0
                for name, addr in getaddresses([hdr]):
                    headers.append((index, name, addr))
                    index += 1
                return headers
            except:
                print(f"failed: parse_hdr_to_cc (uid: {uid}) {hdr}")
                return []
    except Exception as e: 
        print(f"failed: parse_hdr_to_cc (uid: {uid}) cannot extract {to_cc} header")
        print(f"  {e}")
        return []


def _parse_hdr_subject(uid, msg):
    """
    This is a private helper function - do not use.
    """
    hdr = msg["subject"]
    if hdr is None:
        return None
    else:
        return hdr.strip()


def _parse_hdr_date(uid, msg):
    """
    This is a private helper function - do not use.
    """
    if msg["date"] is None:
        return None
    hdr = msg["date"].strip()

    try:
        # Standard date format:
        temp = parsedate_to_datetime(hdr)
        date = temp.astimezone(UTC).isoformat()
        # print(f"parse_hdr_date: okay (0): {date} | {hdr}")
        return date
    except:
        try:
            # Standard format, with invalid timezone: Mon, 27 Dec 1993 13:46:36 +22306256
            # Parse assuming the timezone is UTC
            split = hdr.split(" ")[:-1]
            split.append("+0000")
            joined = " ".join(split)
            date = parsedate_to_datetime(joined).astimezone(UTC).isoformat()
            # print(f"parse_hdr_date: okay (1): {date} | {hdr}")
            return date
        except:
            try:
                # Non-standard date format: 04-Jan-93 13:22:13 (assume UTC timezone)
                temp = datetime.strptime(hdr, "%d-%b-%y %H:%M:%S")
                date = temp.astimezone(UTC).isoformat()
                # print(f"parse_hdr_date: okay (2): {date} | {hdr}")
                return date
            except:
                try:
                    # Non-standard date format: 30-Nov-93 17:23 (assume UTC timezone)
                    temp = datetime.strptime(hdr, "%d-%b-%y %H:%M")
                    date = temp.astimezone(UTC).isoformat()
                    # print(f"parse_hdr_date: okay (3): {date} | {hdr}")
                    return date
                except:
                    try:
                        # Non-standard date format: 2006-07-29 00:55:01 (assume UTC timezone)
                        temp = datetime.strptime(hdr, "%Y-%m-%d %H:%M:%S")
                        date = temp.astimezone(UTC).isoformat()
                        # print(f"parse_hdr_date: okay (4): {date} | {hdr}")
                        return date
                    except:
                        try:
                            # Non-standard date format: Mon, 17 Apr 2006  8: 9: 2 +0300
                            tmp1 = hdr.replace(": ", ":0").replace("  ", " 0")
                            tmp2 = parsedate_to_datetime(tmp1)
                            date = tmp2.astimezone(UTC).isoformat()
                            # print(f"parse_hdr_date: okay (5): {date} | {hdr}")
                            return date

                        except:
                            print(f"failed: parse_hdr_date (uid: {uid}) {hdr}")
                            return None


def _parse_hdr_message_id(uid, msg):
    """
    This is a private helper function - do not use.
    """
    hdr = msg["message-id"]
    if hdr is None:
        return None
    else:
        return hdr.strip()


def _parse_hdr_in_reply_to(uid, msg):
    """
    This is a private helper function - do not use.
    """
    hdr = msg["in-reply-to"]
    if hdr is not None and hdr != "":
        return hdr.strip()
    hdr = msg["references"]
    if hdr is not None and hdr != "":
        return hdr.strip().split(" ")[-1]
    return None


def _parse_message(uid, raw):
    """
    This is a private helper function - do not use.
    """
    parsing_policy = EmailPolicyCustom()

    msg = BytesHeaderParser(policy=parsing_policy).parsebytes(raw)

    from_name, from_addr = _parse_hdr_from(uid, msg)

    res = {
            "uid"         : uid,
            "from_name"   : from_name,
            "from_addr"   : from_addr,
            "to"          : _parse_hdr_to_cc(uid, msg, "to"),
            "cc"          : _parse_hdr_to_cc(uid, msg, "cc"),
            "subject"     : _parse_hdr_subject(uid, msg),
            "date"        : _parse_hdr_date(uid, msg),
            "message_id"  : _parse_hdr_message_id(uid, msg),
            "in_reply_to" : _parse_hdr_in_reply_to(uid, msg),
            "raw_data"    : raw
          }

    return res


class MailingList:
    """
    A class representing a mailing list in the IETF email archive.
    """

    _archive : MailArchive
    _name    : str

    def __init__(self, mail_archive: MailArchive, list_name: str):
        self._archive = mail_archive
        self._name    = list_name


    def name(self) -> str:
        return self._name


    def uidvalidity(self) -> int:
        dbc = self._archive._db.cursor()
        sql = "SELECT uidvalidity FROM ietf_ma_lists WHERE name = (?);"
        return int(dbc.execute(sql, (self._name, )).fetchone()[0])


    def num_messages(self) -> int:
        dbc = self._archive._db.cursor()
        sql = "SELECT COUNT(*) FROM ietf_ma_msg WHERE mailing_list = (?);"
        return int(dbc.execute(sql, (self._name, )).fetchone()[0])


    def message_uids(self) -> Iterator[int]:
        dbc = self._archive._db.cursor()
        sql = "SELECT uid FROM ietf_ma_msg WHERE mailing_list = ? and uidvalidity = ?;"
        for uid in map(lambda x : x[0], dbc.execute(sql, (self.name(), self.uidvalidity()))):
            yield uid


    def message(self, uid: int) -> Optional[Envelope]:
        """
        Return the Envelope containing the Message identified by the
        specified uid within this mailing list.
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT message_num FROM ietf_ma_msg WHERE mailing_list = ? and uidvalidity = ? and uid = ?;"
        res = dbc.execute(sql, (self._name, self.uidvalidity(), uid)).fetchone()
        if res is None:
            return None
        else:
            return Envelope(self._archive, int(res[0]))


    def messages(self,
                 received_after : str = "1970-01-01T00:00:00",
                 received_before: str = "2038-01-19T03:14:07") -> Iterator[Envelope]:
        """
        Return the envelopes containing the specified messages from this mailing list.
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT uid FROM ietf_ma_msg WHERE mailing_list = ? AND uidvalidity = ? AND date_received >= ? AND date_received < ?;"
        for uid in map(lambda x : x[0], dbc.execute(sql, (self.name(), self.uidvalidity(), received_after, received_before))):
            msg = self.message(uid)
            assert msg is not None
            yield msg


    def messages_as_dataframe(self,
                              received_after : str = "1970-01-01T00:00:00",
                              received_before: str = "2038-01-19T03:14:07") -> pd.DataFrame:
        """
        Return a dataframe containing information about the specified messages from
        this mailing list.
        """
        messages_as_dict = []
        for message in self.messages(received_after = received_after, received_before = received_before):
            mdict = {"Message-ID"  : message.message_id(),
                     "From"        : message.from_(),
                     "To"          : message.to(),
                     "Cc"          : message.cc(),
                     "Subject"     : message.subject(),
                     "Date"        : message.date(),
                     "In-Reply-To" : message.header("in-reply-to") if message.header("in-reply-to") != [] else None,
                     "References"  : message.header("references"),
                    }
            messages_as_dict.append(mdict)
        df = pd.DataFrame(data=messages_as_dict)
        df.set_index("Message-ID", inplace=True)
        return df


    # FIXME: verbose is ignored
    def update(self, verbose=True) -> List[int]:
        """
        Update the local copy of this mailing list from the IMAP server.

        This MUST be called at least once for each mailing list, else no
        messages will be retrieved from the server. That initial update
        may well be slow, since it downloads the entire set of messages
        from the list. Subsequent calls to `update()` only fetch the new
        messages and so are much faster.
        """
        self._archive._log.info(f"mailarchive3:update: {self._name}")
        with IMAPClient(self._archive._imap_server, ssl=True, use_uid=True) as imap:
            self._archive._log.debug(f"mailarchive3:update: connected")
            imap.login("anonymous", "anonymous")

            _, _, imap_ns_shared = imap.namespace()
            imap_prefix    = imap_ns_shared[0][0]
            imap_separator = imap_ns_shared[0][1]

            folder_name = self._name
            folder_path = f"{imap_prefix}{folder_name}"
            folder_info = imap.select_folder(folder_path, readonly=True)
            uidvalidity = folder_info[b'UIDVALIDITY']

            # Save uidvalidity
            dbc = self._archive._db.cursor()
            sql = "INSERT OR REPLACE INTO ietf_ma_lists (name, uidvalidity) VALUES (?, ?);"
            dbc.execute(sql, (self.name(), uidvalidity))
            self._archive._db.commit()

            # FIXME: remove messages from database where uidvalidity doesn't match

            # Retrieve messages on server but not in database
            sql = "SELECT uid FROM ietf_ma_msg WHERE mailing_list = ? and uidvalidity = ?;"
            msg_local  = set(map(lambda x : x[0], dbc.execute(sql, (self.name(), uidvalidity))))
            msg_remote = set(imap.search('NOT DELETED'))
            msg_to_fetch = list(msg_remote - msg_local)

            self._archive._log.debug(f"mailarchive3:update: {len(msg_to_fetch)} messages to fetch")
            for i in range(0, len(msg_to_fetch), 16):
                uid_slice = msg_to_fetch[slice(i, i+16, 1)]
                for uid, msg in imap.fetch(uid_slice, "INTERNALDATE RFC822.SIZE RFC822").items():
                    self._archive._log.info(f"mailarchive3:update: {self._name}/{uid}")
                    rxd = msg[b'INTERNALDATE'].astimezone(UTC).isoformat()
                    cur = self._archive._db.cursor()
                    sql = "INSERT INTO ietf_ma_msg VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING message_num"
                    num = cur.execute(sql, (None, folder_name, uidvalidity, uid, msg[b"RFC822"], msg[b"RFC822.SIZE"], rxd)).fetchone()[0]
                self._archive._db.commit()
            if len(msg_to_fetch) > 0:
                # If we downloaded any messages, rebuild the dependent tables
                self.reindex()
        return msg_to_fetch



    def reindex(self) -> None:
        """
        Rebuild the database tables indexing this mailing list.

        The IETF mailing list archives contain a number of messages with
        malformed or corrupt "Date:", "From:", "To:", and "Cc:" headers.
        This library attempts to correct these headers when indexing the
        retrieved messages. This method refreshes the index for messages
        that have been previously retrieved.

        It is worthwhile to call this method after updating to a new
        version of this library, since the newer version might include
        improved heuristics for detecting and correcting problems with
        the mail archive.

        This function operates on the previously retrieved mail archive
        only, and does not contact the IETF mail server.

        New in mailarchive3
        """
        self._archive._log.info(f"mailarchive3:reindex: {self._name}")

        dbc = self._archive._db.cursor()
        sql = "SELECT message_num, uid, message FROM ietf_ma_msg WHERE mailing_list = ? and uidvalidity = ?;"
        res = dbc.execute(sql, (self.name(), self.uidvalidity())).fetchall()

        for message_num, uid, message in res:
            self._archive._log.debug(f"mailarchive3:reindex: {self._name}/{uid}")

            parsed_msg = _parse_message(uid, message)
            val = (message_num,
                   message_num,
                   parsed_msg["from_name"],
                   parsed_msg["from_addr"],
                   parsed_msg["subject"],
                   parsed_msg["date"],
                   parsed_msg["message_id"],
                   parsed_msg["in_reply_to"])
            sql = """INSERT OR REPLACE INTO ietf_ma_hdr
                     VALUES ((SELECT id FROM ietf_ma_hdr WHERE message_num = ?), ?, ?, ?, ?, ?, ?, ?)"""
            dbc.execute(sql, val)

            max_index = 0
            for index, name, addr in parsed_msg["to"]:
                if index > max_index:
                    max_index = index
                sql = """INSERT OR REPLACE INTO ietf_ma_hdr_to 
                         VALUES ((SELECT id FROM ietf_ma_hdr_to WHERE message_num = ? AND to_index = ?), ?, ?, ?, ?)"""
                dbc.execute(sql, (message_num, index, message_num, index, name, addr))
            sql = "DELETE FROM ietf_ma_hdr_to WHERE message_num = ? AND to_index > ?;"
            dbc.execute(sql, (message_num, max_index))

            max_index = 0
            for index, name, addr in parsed_msg["cc"]:
                if index > max_index:
                    max_index = index
                sql = """INSERT OR REPLACE INTO ietf_ma_hdr_cc 
                         VALUES ((SELECT id FROM ietf_ma_hdr_cc WHERE message_num = ? AND cc_index = ?), ?, ?, ?, ?)"""
                dbc.execute(sql, (message_num, index, message_num, index, name, addr))
            sql = "DELETE FROM ietf_ma_hdr_cc WHERE message_num = ? AND cc_index > ?;"
            dbc.execute(sql, (message_num, max_index))
            self._archive._db.commit()


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
                msg_id = msg.message_id()
                seen[msg_id] = msg

                self._archive._log.debug(f"{msg.uid():5} {msg.message_id()} {msg.subject()}")

                parents = msg.in_reply_to()
                if len(parents) == 0:
                    # This is the first message in the thread
                    if msg.message_id() not in threads:
                        threads[msg.message_id()] = self._archive.message(msg.message_id())
                    self._archive._log.debug("      First in thread")
                elif parents[0].message_id() in seen:
                    # This is part of a thread we've already seen
                    self._archive._log.debug(f"      {parents[0].message_id()} {parents[0].subject()}")
                    self._archive._log.debug(f"      Continues known thread")
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
                            self._archive._log.debug(f"      {parents[0].message_id()} {parents[0].subject()}")
                            self._archive._log.debug(f"      Not in this list")
                            if curr[0].message_id() not in threads:
                                threads[curr[0].message_id()] = curr
                            break
    
                        if len(parents) == 0:
                            self._archive._log.debug("      First in thread")
                            if curr[0].message_id() not in threads:
                                threads[curr[0].message_id()] = curr
                            break
                        curr = parents
                        self._archive._log.debug(f"      {curr[0].message_id()} {curr[0].subject()}")
        return threads


    def add_metadata(self, project:str, key:str, value: str) -> None:
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
        dbc = self._archive._db.cursor()
        sql = """INSERT OR REPLACE INTO ietf_ma_list_metadata
                 VALUES ((SELECT id FROM ietf_ma_list_metadata WHERE mailing_list = ? and project = ? AND key_ = ?), ?, ?, ?, ?)"""
        dbc.execute(sql, (self._name, project, key, self._name, project, key, value))
        self._archive._db.commit()


    def get_metadata(self, project:str, key:str) -> Optional[str]:
        """
        Get metadata relating to the list.

        Parameters:
        - `project` -- the project or user to which this metadata relates
        - `key`     -- the key under which the metadata was scored
        """
        dbc = self._archive._db.cursor()
        sql = "SELECT value FROM ietf_ma_list_metadata WHERE mailing_list = ? AND project = ? AND key_ = ?;"
        res = dbc.execute(sql, (self._name, project, key)).fetchone()
        if res is None:
            return None
        else:
            return str(res[0])


    def clear_metadata(self, project:str, key:Optional[str] = None) -> None:
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
        dbc = self._archive._db.cursor()
        if key is None:
            sql = "DELETE FROM ietf_ma_list_metadata WHERE mailing_list = ? AND project = ?;"
            dbc.execute(sql, (self._name, project))
        else:
            sql = "DELETE FROM ietf_ma_list_metadata WHERE mailing_list = ? AND project = ? AND key_ = ?;"
            dbc.execute(sql, (self._name, project, key))
        self._archive._db.commit()


# =================================================================================================

class MailArchive:
    """
    A class representing the IETF email archive.
    """
    _log         : logging.Logger
    _imap_server :str

    # Differs from mailarchiv2
    def __init__(self,
                 imap_server : str = "imap.ietf.org",
                 sqlite_file : str = "ietfdata.sqlite") -> None:
        """
        Initialise the MailArchive.

        If it doesn't exist, an sqlite3 database, specified by the `sqlite_file`
        argument, is created to hold a local copy of the IETF mail archive. The
        database will initially be empty and must be populated before it can be
        used. There are two ways to populate the database:

        1. Call the `update()` method to populate the database with a
           complete copy of the IETF mail archive. As of January 2025,
           the complete archive is around 35 gigabytes in size.

        2. Call the `update_mailing_list_names()` method to add the mailing
           list names to the database. Then, use the `mailing_list_names()`
           method to query what lists exist and `update_mailing_list()` to
           populate the database with only the lists of interest.

        In normal operation, calling `update()` to fetch the complete mail
        archive is the right thing to do.

        Previous versions of this library used MongoDB to store the archived
        email messages. This version uses an sqlite3 database file instead.
        The following arguments are no longer accepted and should be removed
        from code that use this library: `mongodb_hostname`, `mongodb_port`,
        `mongodb_username`, and `mongodb_password`.
        """
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))

        self._imap_server = imap_server
        self._log = logging.getLogger("ietfdata")
        self._db  = sqlite3.connect(sqlite_file)
        self._db.execute('PRAGMA synchronous = OFF;')
        self._db.execute('PRAGMA foreign_keys = ON;')
        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_ma_lists (
                                name        TEXT NOT NULL PRIMARY KEY,
                                uidvalidity INTEGER
                            );""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_lists ON ietf_ma_lists (name);""")

        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_ma_list_metadata (
                                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                                mailing_list TEXT NOT NULL,
                                project      TEXT,
                                key_         TEXT,
                                value        TEXT);""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_list_metadata
                                                    ON ietf_ma_list_metadata (mailing_list, project, key_);""")

        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_ma_msg (
                                message_num   INTEGER PRIMARY KEY AUTOINCREMENT,
                                mailing_list  TEXT NOT NULL,
                                uidvalidity   INTEGER NOT NULL,
                                uid           INTEGER NOT NULL,
                                message       BLOB,
                                size          INTEGER,
                                date_received TEXT
                            );""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_msg_list_date_uid  ON ietf_ma_msg (mailing_list, date_received, uidvalidity, uid);""")

        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_ma_hdr (
                                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                                message_num  INTEGER,
                                from_name    TEXT,
                                from_addr    TEXT,
                                subject      TEXT,
                                date         TEXT,
                                message_id   TEXT,
                                in_reply_to  TEXT,
                                FOREIGN KEY (message_num)  REFERENCES ietf_ma_msg (message_num)
                            );""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_message_num    ON ietf_ma_hdr (message_num);""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_message_id     ON ietf_ma_hdr (message_id);""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_in_reply_to    ON ietf_ma_hdr (in_reply_to);""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_from_addr_date ON ietf_ma_hdr (from_addr, date);""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_from_name_date ON ietf_ma_hdr (from_name, date);""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_date_subject   ON ietf_ma_hdr (date, subject);""")

        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_ma_hdr_to (
                                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                                message_num INTEGER,
                                to_index    INTEGER,
                                to_name     TEXT,
                                to_addr     TEXT,
                                FOREIGN KEY (message_num) REFERENCES ietf_ma_msg (message_num)
                            );""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_to ON ietf_ma_hdr_to (message_num, to_index);""")

        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_ma_hdr_cc (
                                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                                message_num INTEGER,
                                cc_index    INTEGER,
                                cc_name     TEXT,
                                cc_addr     TEXT,
                                FOREIGN KEY (message_num) REFERENCES ietf_ma_msg (message_num)
                            );""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_hdr_cc ON ietf_ma_hdr_cc (message_num, cc_index);""")

        self._db.execute("""CREATE TABLE IF NOT EXISTS ietf_ma_msg_metadata (
                                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                                message_num INTEGER,
                                project     TEXT,
                                key_        TEXT,
                                value       TEXT);""")
        self._db.execute("""CREATE INDEX IF NOT EXISTS index_ietf_ma_msg_metadata ON ietf_ma_msg_metadata (message_num, project, key_);""")

        self._db.commit()


    def update_mailing_list_names(self) -> None:
        """
        Contact the IETF mail server and update the local copy of the list of
        mailing lists that are available.

        In normal operation you do not need to call this method. It should only
        be used if you plan to download only a subset of the IETF mailing lists,
        in which case you should call this method, then `mailing_list_names()`
        to query what lists exist, then `update_mailing_list()` to populate the
        local database with the messages from the lists of interest.

        New in mailarchive3
        """
        with IMAPClient(host=self._imap_server, ssl=True, use_uid=True) as imap:
            imap.login("anonymous", "anonymous")

            _, _, imap_ns_shared = imap.namespace()
            imap_prefix    = imap_ns_shared[0][0]
            imap_separator = imap_ns_shared[0][1]
            folder_list    = imap.list_folders()

        dbc = self._db.cursor()
        for (flags, delimiter, folder_path) in folder_list:
            if b'\\Noselect' in flags:
                continue
            name = folder_path.split(imap_separator)[-1]
            dbc.execute("INSERT OR IGNORE INTO ietf_ma_lists (name) VALUES (?)", (name,))
        self._db.commit()


    def update_mailing_list(self, mailing_list_name: str) -> None:
        """
        Contact the IETF mail serer to update the local copy of the specified
        mailing list.

        In normal operation you do not need to call this method. It's only used
        when working with a partial copy of the IETF mail archive, as discussed
        in the documentation for `update_mailing_list_names()`.

        New in mailarchive3
        """
        ml = self.mailing_list(mailing_list_name)
        ml.update()


    def update(self, verbose=True) -> None:
        """
        Contact the IETF mail server to update the local copy of the IETF
        mailing list archive.

        This method should be called when working with a complete copy of
        the mail archive to synchronise the local copy of the archive with
        the IETF mail server.

        WARNING: The first time this method is called, it will download the
        entire mail archive. This will take several hours and download tens
        of gigabytes of data. Subsequent calls will fetch only new data and
        so will be much faster.
        """
        self.update_mailing_list_names()
        for ml_name in self.mailing_list_names():
            ml = self.mailing_list(ml_name)
            ml.update()


    def reindex(self) -> None:
        """
        Rebuild the header indexes.

        This rebuilds the index of message headers baed on the downloaded
        messages. It's recommended to run this after updating this library
        since improvements to the heading parsing code may result in more
        accurate indexes.

        Calling `update()` or `update_mailing_list()` will automatically
        reindex any mailing lists that are updated, so there is no need
        to call this method after those operations.

        This nmethod operates locally based on the previously downloaded
        messages.

        New in mailarchive3
        """
        for ml_name in self.mailing_list_names():
            ml = self.mailing_list(ml_name)
            ml.reindex()


    def mailing_list_names(self) -> Iterator[str]:
        """
        Yield the names of the mailing lists that exist in the mail archive.
        """
        dbc = self._db.cursor()
        for name in dbc.execute("SELECT name FROM ietf_ma_lists;", ()):
            yield name[0]


    def mailing_list(self, mailing_list_name: str) -> MailingList:
        """
        Return an object representing the given mailing list.
        """
        return MailingList(self, mailing_list_name)



    def message(self, message_id:str) -> List[Envelope]:
        """
        Return the envelopes for all messages with the specified `message_id`.

        There can be multiple copies of a message with a particular ID in the
        archive if t was sent to multiple lists. This method returns all the
        copies, since each copy might have a different set of replies.  For
        example, message "<396c8d37-f979-73fe-34fa-475a038b94f8@alum.mit.edu>"
        appears in the archives of the "art", "last-call", and "tsvwg" lists.
        """
        dbc = self._db.cursor()
        sql = "SELECT message_num FROM ietf_ma_hdr WHERE message_id = ?;"
        msgs = []
        for msg_num in map(lambda x : x[0], dbc.execute(sql, (message_id, )).fetchall()): 
            msgs.append(Envelope(self, msg_num))
        return msgs


    def messages(self,
                 received_after    : str = "1970-01-01T00:00:00", # Deprecated, use sent_after instead
                 received_before   : str = "2038-01-19T03:14:07", # Deprecated, use sent_before instead
                 header_from       : Optional[str] = None, # Regex match - deprecated, use from_addr or from_name instead
                 header_to         : Optional[str] = None, # Regex match - deprecated, use to_addr instead
                 header_subject    : Optional[str] = None, # Regex match - deprecated, use subject instead
                 mailing_list_name : Optional[str] = None, # Exact match
                 # The following are new for mailarchive3:
                 sent_after        : str = "1970-01-01T00:00:00",
                 sent_before       : str = "2038-01-19T03:14:07",
                 from_name         : Optional[str] = None, # Substring match
                 from_addr         : Optional[str] = None,
                 to_addr           : Optional[str] = None,
                 cc_addr           : Optional[str] = None,
                 subject           : Optional[str] = None, # Substring match
                 message_id        : Optional[str] = None,
                 in_reply_to       : Optional[str] = None,
                ) -> Iterator[Envelope]:
        """
        Search the local copy of the IETF mail archive, returning the envelopes
        of the messages that match all of the specified criteria.

        The `received_after` and `received_before` arguments are deprecated and
        should not be used. These arguments can be used to find messages based
        on the date when they were added to the mail archive, but for a number
        of mailing lists the archive was back-filled after the fact so the date
        when the messages were added to the mail archive bears no relation to
        the date when the messages were sent. In normal use, the `sent_after`
        and `sent_before` arguments should be used instead to find messages
        based on the parsed "Date:" headers.

        The `header_from`, `header_to`, and `header_subject` arguments are
        deprecated and should not be used. The mailarchive3 library uses a
        number of heuristics to correct malformed headers, but these methods
        search only the uncorrected headers. In normal use, the `from_name`,
        `from_addr`, `to_addr`, and `subject` arguments should be used instead
        since they search the corrected data and are much faster.
        """
        dbc = self._db.cursor()
        query = """SELECT DISTINCT ietf_ma_msg.message_num 
                   FROM ietf_ma_msg
                   LEFT JOIN ietf_ma_hdr    ON ietf_ma_msg.message_num = ietf_ma_hdr.message_num
                   LEFT JOIN ietf_ma_hdr_to ON ietf_ma_msg.message_num = ietf_ma_hdr_to.message_num
                   LEFT JOIN ietf_ma_hdr_cc ON ietf_ma_msg.message_num = ietf_ma_hdr_cc.message_num
                   WHERE date_received >= ? AND date_received < ? """
        param = [received_after, received_before]
        if mailing_list_name is not None:
            query += "AND mailing_list == ? "
            param.append(mailing_list_name)

        query += " AND date >= ? AND date < ? "
        param.append(sent_after)
        param.append(sent_before)

        if from_name is not None:
            query += "AND from_name LIKE ? "
            param.append(from_name)
        if from_addr is not None:
            query += "AND from_addr == ? "
            param.append(from_addr)
        if to_addr is not None:
            query += "AND to_addr == ? "
            param.append(to_addr)
        if cc_addr is not None:
            query += "AND cc_addr == ? "
            param.append(cc_addr)
        if subject is not None:
            query += "AND subject LIKE ? "
            param.append(f'%{subject}%')
        if message_id is not None:
            query += "AND message_id == ? "
            param.append(message_id)
        if in_reply_to is not None:
            query += "AND in_reply_to == ? "
            param.append(in_reply_to)
        query += ";"
        if header_from is None and header_to is None and header_subject is None:
            qplan  = dbc.execute("EXPLAIN QUERY PLAN " + query, param).fetchone()
            self._log.debug(query)
            self._log.debug(qplan)

            for msg_num in map(lambda x : x[0], dbc.execute(query, param).fetchall()): 
                yield Envelope(self, msg_num)
        else:
            # Handle deprecated queries that do a regexp match on the raw headers.
            # This is very slow.
            for msg_num in map(lambda x : x[0], dbc.execute(query, param).fetchall()): 
                msg = Envelope(self, msg_num)
                if (header_from    is None or re.search(header_from,    str(msg.header("from")))) and \
                   (header_to      is None or re.search(header_to,      str(msg.header("to"))))   and \
                   (header_subject is None or re.search(header_subject, str(msg.header("subject")))):
                    yield msg


    def clear_metadata(self, project: str):
        """
        Remove metadata relating to the project from all mailing lists
        and message envelopes.

        WARNING: This is a destructive operation that should not normally
        be needed. Use with care.
        """
        for ml_name in self.mailing_list_names():
            ml = self.mailing_list(ml_name)
            ml.clear_metadata(project)


# =================================================================================================
# vim: set tw=0 ai:
