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

import email.header
import email.utils
import os
import re
import string
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses import dataclass, field
from pathlib              import Path
from ietfdata.datatracker import *
from ietfdata.mailarchive import *

# =============================================================================

@dataclass
class ParticipantEmail:
    addr   : str
    names  : List[str]
    count  : int
    person : Optional[Person]

# =============================================================================

dt      = DataTracker(cache_dir=Path("cache"))
archive = MailArchive(cache_dir=Path("cache"))

addrs = {}
lists = list(archive.mailing_list_names())

print("*** Parsing messages:")
index = 0
for ml_name in lists:
    index += 1
    print(F"{index:5d} /{len(lists):5d} {ml_name:40}", end="")
    for msg_id, msg in archive.mailing_list(ml_name).messages():
        try:
            n, e = email.utils.parseaddr(msg.message["from"])
            if e is not "" and e not in addrs:
                addrs[e] = ParticipantEmail(e, [], 0, None)
            if n is not "" and n not in addrs[e].names:
                name = str(email.header.make_header(email.header.decode_header(n)))
                addrs[e].names.append(name)
            addrs[e].count += 1
        except:
            pass
    print(F"   {len(addrs):6}")
    #if index == 10:
    #    break


print("")
print("*** Resolving email addresses:")
for e in addrs.values():
    assert e.addr != ""
    e.person = dt.person_from_email(e.addr)
    if e.person is not None:
        print(F"    {e.addr:40} -> {e.person.id:8} (exact email match)")
    else:
        print(F"    {e.addr:40}")


print("")
print("*** Resolving names:")
for e in addrs.values():
    if e.person is None:
        for name in e.names:
            if name == "":
                break
            # Check against UTF-8 versions of names in datatracker:
            for person in dt.people(name_contains = name):
                if name == person.name:
                    e.person = person
                    print(F"    {e.addr:40} -> {e.person.id:8} (UTF-8 name match: {name})")
                elif F"Dr. {name}" == person.name:
                    e.person = person
                    print(F"    {e.addr:40} -> {e.person.id:8} (UTF-8 name match: {name} <-> {person.name})")
            if e.person is not None:
                break
            # Check against ASCII versions of names in datatracker:
            for person in dt.people(ascii_contains = name):
                if name == person.ascii:
                    e.person = person
                    print(F"    {e.addr:40} -> {e.person.id:8} (ASCII name match: {name})")
                elif F"Dr. {name}" == person.ascii:
                    e.person = person
                    print(F"    {e.addr:40} -> {e.person.id:8} (ASCII name match: {name} <-> {person.name})")
            if e.person is not None:
                break
        if e.person is None:
            print(F"    {e.addr:40}")

print("")
print("*** Resolving People:")
for person in dt.people():
    pattern = re.compile("[A-Za-z]+ [A-Z]\. [A-Za-z]+")
    if pattern.match(person.name):
        split = person.name.split(" ")
        person_name_initial = F"{split[0]} {split[2]}"
    else:
        person_name_initial = person.name

    for e in addrs.values():
        if e.person is None:
            for name in e.names:
                pattern = re.compile("[A-Za-z], [A-Za-z]")
                if pattern.match(person.name):
                    # Convert "surname, name" into "name surname" and match
                    split = person.name.split(", ")
                    name_reversed = F"{split[1]} {split[0]}"
                    if name_reversed == person.name:
                        e.person = person
                        print(F"    {e.addr:40} -> {e.person.id:8} (UTF-8 name match: {name} <-> {person.name})")
                    if name_reversed == person_name_initial:
                        e.person = person
                        print(F"    {e.addr:40} -> {e.person.id:8} (UTF-8 name match: {name} <-> {person.name})")

                # Does it match the name without a middle initial?
                if name == person_name_initial:
                    e.person = person
                    print(F"    {e.addr:40} -> {e.person.id:8} (UTF-8 name match: {name} <-> {person.name})")



total_resolved = 0
total_notfound = 0

email_resolved = 0
email_notfound = 0

print("")
print("*** Unresolved:")
for e in addrs.values():
    if e.person is None:
        email_notfound += 1
        total_notfound += e.count
        print(F"    {e.addr:40} ({e.count})")
        for name in e.names:
            print(F"        {name}")
        e = dt.email(EmailURI(F"/api/v1/person/email/{e.addr.replace('/', '%40')}/"))
        if e is not None:
            for d in dt.documents_authored_by_email(e):
                print(d.name)

    else:
        email_resolved += 1
        total_resolved += e.count


print(F"Resolved: {total_resolved:8} messages; {email_resolved:6} addresses")
print(F"NotFound: {total_notfound:8} messages; {email_notfound:6} addresses")

data : Dict[str, Any] = {}
for e in addrs.values():
    item : Dict[str, Any] = {}
    item["addr"]  = e.addr
    item["names"] = e.names
    item["count"] = e.count
    if e.person is not None:
        item["person_url"]              = e.person.resource_uri.uri
        item["person_id"]               = e.person.id
        item["person_name"]             = e.person.name
        item["person_name_from_draft"]  = e.person.name_from_draft
        item["person_ascii"]            = e.person.ascii
        item["person_ascii_short"]      = e.person.ascii_short
    else:
        item["person_uri"]              = ""
        item["person_id"]               = ""
        item["person_name"]             = ""
        item["person_name_from_draft"]  = ""
        item["person_ascii"]            = ""
        item["person_ascii_short"]      = ""
    data[e.addr] = item

with open(Path("addrs.json"), "w") as outf:
    json.dump(data, outf)

# =============================================================================
