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

import email.utils
import os
import string
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib              import Path
from ietfdata.datatracker import DataTracker
from ietfdata.mailarchive import *

# =============================================================================

dt      = DataTracker(cache_dir=Path("cache"))
archive = MailArchive(cache_dir=Path("cache"))

count = {}
addrs = {}
lists = list(archive.mailing_list_names())

print("*** Parsing messages:")
index = 0
for ml_name in lists:
    index += 1
    print(F"{index:5d} /{len(lists):5d} {ml_name:40}", end="")
    for msg_id, msg in archive.mailing_list(ml_name).messages():
        try:
            n, e = email.utils.parseaddr(msg["from"])
            addrs[e] = n
            if e in count:
                count[e] += 1
            else:
                count[e] = 1
        except:
            pass
    print(F"   {len(addrs):6}")


print("*** Caching email addressess:")
index = 0
for e in dt.emails():
    index += 1
    print(F"{index:10} {e.address}")


print("*** Resolving email addresses:")
with open("addrs.dat", "w") as outf:
    for e, n in addrs.items():
        if e != "":
            p = dt.person_from_email(e)
            if p is not None:
                dt_id   = p.id
                dt_name = p.name
                status  = "found"
            else:
                name = n.strip()
                if name != "" and count[e] > 100:
                    people = list(dt.people(name_contains=name))
                    if len(people) == 1:
                        p = people[0]
                        dt_id   = p.id
                        dt_name = p.name
                        status  = "match"
                    else:
                        dt_id   = ""
                        dt_name = ""
                        status  = "notfound"
                else:
                    dt_id   = ""
                    dt_name = ""
                    status  = "unchecked"
            n = re.sub(f'[^{re.escape(string.printable)}]', ' ', n)
            n = re.sub('\n', ' ', n)
            n = re.sub('§', ' ', n)
            res = F"{e:50s} § {count[e]:5d} § {n:50s} § {status:10} § {dt_id:6} § {dt_name}\n"
            outf.write(res)
            print(res, end="")

# =============================================================================
