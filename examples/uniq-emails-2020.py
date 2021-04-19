# Copyright (C) 2021 University of Glasgow
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

import csv
import email.header
import email.utils
import os
import re
import string
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses                     import dataclass, field
from pathlib                         import Path
from ietfdata.datatracker            import *
from ietfdata.datatracker_ext        import *
from ietfdata.mailarchive            import *
from ietfdata.mailhelper_headerdata  import *
from ietfdata.mailhelper_datatracker import *

dt      = DataTrackerExt()
archive = MailArchive(cache_dir=Path("cache"))
lists   = list(archive.mailing_list_names())
addrs   = {}
people  = {}
addr_no_person = {}
total_spam = 0
total  = 0

archive.download_all_messages()

index = 1
for ml_name in lists:
    print(F"{index:5d} /{len(lists):5d} {ml_name:40}", end="")
    index += 1
    for msg_id, msg in archive.mailing_list(ml_name).messages():
        date_str = msg.message["Date"]
        try:
            date = email.utils.parsedate_to_datetime(date_str)
            year = date.timetuple().tm_year
        except:
            print(f"[{msg_id:06}] can't parse date {date_str}")
            year = 0
        if year == 2020:
            total += 1
            spam = msg.message["X-Spam-Flag"]
            if spam is not None and spam == "YES":
                total_spam += 1
            else:
                try:
                    name, addr = email.utils.parseaddr(msg.message["from"])
                    if addr != "" and addr not in addrs:
                        addrs[addr] = addr
                        p = dt.person_from_name_email(name, addr)
                        if p is not None:
                            people[p.id] = p
                        else:
                            addr_no_person[addr] = addr
                except:
                    print(f"[{msg_id:06}] can't parse From: {msg.message['From']}")
    print(F"   {len(addrs):6} unique emails; {len(addr_no_person)} unmapped; {total} messages; {total_spam} spam")

with open(Path("emails-2020.txt"), "w") as outf:
    for e in addrs.values():
        print(e, file=outf)

with open(Path("emails-2020-no-person.txt"), "w") as outf:
    for e in addr_no_person.values():
        print(e, file=outf)

with open(Path("people-2020.txt"), "w") as outf:
    for p in people.values():
        print(F"{p.id:8}   {p.name}", file=outf)

# =============================================================================
