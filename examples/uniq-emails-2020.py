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
import pprint
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dataclasses                     import dataclass, field
from pathlib                         import Path
from ietfdata.datatracker            import *
from ietfdata.datatracker_ext        import *
from ietfdata.mailarchive            import *
from ietfdata.mailhelper_headerdata  import *
from ietfdata.mailhelper_datatracker import *

dt      = DataTrackerExt()

# archive.download_all_messages()

# =================================================================================================================================
# Find and categorise the mailing lists:

lists = {}
for ml in dt.mailing_lists():
    lists[ml.name.lower()] = {"name": ml.name.lower(), "category" : "other", "active": False}

print(f"Found {len(lists)} mailing lists")

print("")
print(f"Categorising meeting lists:")
next_meeting = dt.next_ietf_meeting()
for meeting in dt.meetings(meeting_type = dt.meeting_type_from_slug("ietf")):
    if next_meeting is not None and next_meeting.number == meeting.number:
        active = True
    else:
        active = False
    for list_name in [
                F"ietf-{meeting.number}", 
                F"ietf{meeting.number}bnb",
                F"ietf{meeting.number}-1st-timers", 
                F"ietf{meeting.number}-bitsnbites",
                F"ietf{meeting.number}-sponsor-info",
                F"ietf{meeting.number}-team",
                F"ietf{meeting.number}-ieee",
                F"ietf{meeting.number}planning", 
                F"{meeting.number}_attendees", 
                F"{meeting.number}_all", 
                F"{meeting.number}-1st-timers", 
                F"{meeting.number}all", 
                F"{meeting.number}attendees", 
                F"{meeting.number}companion", 
                F"{meeting.number}companions", 
                F"{meeting.number}guestpass", 
                F"{meeting.number}hackathon", 
                F"{meeting.number}onsite", 
                F"{meeting.number}newcomers", 
                F"{meeting.number}reg", 
                F"{meeting.number}remote", 
                F"{meeting.number}remote-all", 
                F"{meeting.number}-mentees", 
                F"{meeting.number}-mentors", 
                F"{meeting.number}-newcomers",
            ]:
        if list_name in lists:
            lists[list_name]["category"] = "ietf-admin"
            lists[list_name]["active"]   = active
            print(f"  {list_name:25} -> {lists[list_name]['category']:14} {active:1} IETF {meeting.number})")


print("")
print(f"Categorising IAB lists:")
for group in dt.groups(parent = dt.group_from_acronym("iab")):
    if group.list_archive.startswith("https://mailarchive.ietf.org/arch/browse/"):
        list_name = group.list_archive[41:-1]
    elif group.list_archive.startswith("https://mailarchive.ietf.org/arch/search/?email_list="): 
        list_name = group.list_archive[53:]
    elif group.list_email.count("@") == 1:
        list_name, domain = group.list_email.split("@")
    else:
        list_name = group.acronym

    group_state = dt.group_state(group.state).slug
    if group_state == "active" or group_state == "bof" or group_state == "proposed":
        active = True
    else:
        active = False

    for ln in [list_name, F"{list_name}-discuss"]:
        if ln in lists:
            lists[ln]["category"] = "iab"
            lists[ln]["active"]   = active
            print(f"  {ln:25} -> {lists[ln]['category']:14} {active:1} {group.name}")


print("")
print(f"Categorising IRTF lists:")
for group in dt.groups(parent = dt.group_from_acronym("irtf")):
    if group.list_archive.startswith  ("http://www.irtf.org/mail-archive/web/"):
        list_name = group.list_archive[37:-1]
    elif group.list_archive.startswith("https://irtf.org/mail-archive/web/"):
        list_name = group.list_archive[34:-1]
    elif group.list_archive.startswith("https://mailarchive.ietf.org/arch/browse/"):
        list_name = group.list_archive[41:-1]
    elif group.list_archive.startswith("https://mailarchive.ietf.org/arch/search/?email_list="): 
        list_name = group.list_archive[53:]
    elif group.list_email.count("@") == 1:
        list_name, domain = group.list_email.split("@")
    else:
        list_name = group.acronym

    group_state = dt.group_state(group.state).slug
    if group_state == "active" or group_state == "bof" or group_state == "proposed":
        active = True
    else:
        active = False

    if list_name in lists:
        lists[list_name]["category"] = "irtf"
        lists[list_name]["active"]   = active
        print(f"  {list_name:25} -> {lists[list_name]['category']:14} {active:1} {group.name}")


print("")
print(f"Categorising IETF area, working group, BoF, and directorate lists:")
for area in dt.groups(parent = dt.group_from_acronym("iesg")):
    print(F"  {area.name} ({area.acronym})")
    for ln in [F"{area.acronym}-area", F"{area.acronym}-discuss"]:
        if ln in lists:
            lists[ln]["category"] = "ietf-technical"
            lists[ln]["active"]   = active
            print(f"    {ln:25} -> {lists[ln]['category']:14} {active:1} {area.name}")


    for group in dt.groups(parent = area):
        if group.list_archive.startswith("https://mailarchive.ietf.org/arch/browse/"):
            list_name = group.list_archive[41:-1]
        elif group.list_archive.startswith("https://mailarchive.ietf.org/arch/search/?email_list="): 
            list_name = group.list_archive[53:]
        elif group.list_email.count("@") == 1:
            list_name, domain = group.list_email.split("@")
        else:
            list_name = group.acronym

        group_state = dt.group_state(group.state).slug
        if group_state == "active" or group_state == "bof" or group_state == "proposed":
            active = True
        else:
            active = False

        if list_name in lists:
            if area.acronym == "gen" or area.acronym == "usv":
                lists[list_name]["category"] = "ietf-admin"
                lists[list_name]["active"]   = active
            else:
                lists[list_name]["category"] = "ietf-technical"
                lists[list_name]["active"]   = active
            print(f"    {list_name:25} -> {lists[list_name]['category']:14} {active:1} {group.name}")

            for ml in lists:
                if ml.startswith(F"{list_name}-") and lists[ml]["category"] == "other":
                    lists[ml]["category"] = lists[list_name]["category"]
                    lists[ml]["active"]   = lists[list_name]["active"]
                    print(f"    {ml:25} -> {lists[ml]['category']:14} {active:1} {group.name} (inferred)")



print("")
print(f"Categorising IETF administrative lists:")
for ml in lists:
    if ml.startswith("llc") or ml.startswith("iaoc") or ml.startswith("isoc") or ml.startswith("rsoc") \
            or ml.startswith("icann") or ml.startswith("interim-board") or ml.startswith("ipr-") \
            or ml.startswith("iesg") or ml.startswith("iab") or ml.startswith("iana"):
        categorise = True
        category   = "ietf-admin"
    elif ml.startswith("anrw") or ml.startswith("anrp"):
        categorise = True
        category   = "irtf"
    elif ml.endswith("-vote") or ml.endswith("-coord"):
        categorise = True
        category   = "ietf-admin"
    elif "workshop" in ml or "program" in ml:
        categorise = True
        category   = "iab"
    elif "nomcom" in ml or "-llc-" in ml or "venue" in ml or "datatravker" in ml or "3gpp" in ml or "sponsorship" in ml:
        categorise = True
        category   = "ietf-admin"
    else:
        categorise = False
    if categorise and lists[ml]["category"] == "other":
        lists[ml]["category"] = category
        lists[ml]["active"]   = True
        print(f"  {ml:25} -> {lists[ml]['category']:14} {active:1}")

print("")
print(f"Categorising miscellaneous lists:")
for list_name, category, active in [
        ("admin-discuss",     "ietf-admin", True),
        ("ietf-announce",     "ietf-admin", True),
        ("bofchairs",         "ietf-admin", True),
        ("recentattendees",   "ietf-admin", True),
        ("training-wgchairs", "ietf-admin", True),
        ("wgchairs",          "ietf-admin", True),
        ("irtf-announce",     "irtf",       True),
        ("irtf-discuss",      "irtf",       True),
        ("model-t",           "iab",        True),
        ("rfc-markdown",      "ietf-admin", True),
    ]:
    lists[list_name]["category"] = category
    lists[list_name]["active"]   = active
    print(f"  {list_name:25} -> {lists[list_name]['category']:14} {active:1}")


print("")
for category in ["ietf-admin", "ietf-technical", "irtf", "iab", "other"]:
    for active in [True, False]:
        if active:
            active_label = "(active)"
        else:
            active_label = "(inactive)"
        print(f"Mailing lists in category {category} {active_label}:")
        print(f"   ", end="")
        plen = 3
        for ml in lists:
            if lists[ml]["category"] == category and lists[ml]["active"] == active:
                plen += len(ml) + 1
                if plen > 80:
                    print(f"")
                    print(f"   ", end="")
                    plen = 3 + len(ml) + 1
                print(f"{ml} ", end="")
        print("")
print("")

# =================================================================================================================================
print("")
print("Analysing Mailing Lists:")

archive = MailArchive(cache_dir=Path("cache"))
addrs   = {}
people  = {}
person_for_addr = {}
addr_no_person = {}
lists_for_email = {}
lists_for_person = {}
categories_for_email = {}
categories_for_person = {}
total_spam = 0
total_mail  = 0

index = 1
for ml_name in sorted(lists):
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
            total_mail += 1
            spam = msg.message["X-Spam-Flag"]
            if spam is not None and spam == "YES":
                total_spam += 1
            else:
                #try:
                name, addr = email.utils.parseaddr(msg.message["from"])
                if addr != "": 
                    # Record email address:
                    if addr not in addrs:
                        addrs[addr] = addr

                    # Record mailing lists for email address:
                    if addr not in lists_for_email:
                        lists_for_email[addr] = [ml_name]
                    else:
                        if not ml_name in lists_for_email[addr]:
                            lists_for_email[addr].append(ml_name)

                    # Record categories for email address:
                    if addr not in categories_for_email:
                        categories_for_email[addr] = [lists[ml_name]["category"]]
                    else:
                        if not lists[ml_name]["category"] in categories_for_email[addr]:
                            categories_for_email[addr].append(lists[ml_name]["category"])

                    # Record person:
                    if F"{name}+{addr}" not in person_for_addr:
                        p = dt.person_from_name_email(name, addr)
                        person_for_addr[F"{name}+{addr}"] = p

                    p = person_for_addr[F"{name}+{addr}"]
                    if p is not None:
                        people[p.id] = p
                        # Record Mailing lists for person:
                        if p.id not in lists_for_person:
                            lists_for_person[p.id] = [ml_name]
                        else:
                            if not ml_name in lists_for_person[p.id]:
                                lists_for_person[p.id].append(ml_name)
                        # Record categories for person:
                        if p.id not in categories_for_person:
                            categories_for_person[p.id] = [lists[ml_name]["category"]]
                        else:
                            if not lists[ml_name]["category"] in categories_for_person[p.id]:
                                categories_for_person[p.id].append(lists[ml_name]["category"])
                    else:
                        addr_no_person[addr] = addr
                #except:
                #    print(f"[{msg_id:06}] can't parse From: {msg.message['From']}")
    print(F"   {len(addrs):6} unique emails; {len(addr_no_person)} unmapped; {total_mail} messages; {total_spam} spam")

# =================================================================================================================================
# Save Results:

with open(Path("2020-emails.txt"), "w") as outf:
    for e in addrs.values():
        print(e, file=outf)

with open(Path("2020-emails-no-person.txt"), "w") as outf:
    for e in addr_no_person.values():
        print(e, file=outf)

with open(Path("2020-people.txt"), "w") as outf:
    for p in people.values():
        print(F"{p.id:8}   {p.name}", file=outf)

with open(Path("2020-lists-for-email.txt"), "w") as outf:
    print(json.dumps(lists_for_email, sort_keys=True, indent=2), file=outf)

with open(Path("2020-lists-for-person.txt"), "w") as outf:
    print(json.dumps(lists_for_person, sort_keys=True, indent=2), file=outf)

with open(Path("2020-categories-for-email.txt"), "w") as outf:
    print(json.dumps(categories_for_email, sort_keys=True, indent=2), file=outf)

with open(Path("2020-categories-for-person.txt"), "w") as outf:
    print(json.dumps(categories_for_person, sort_keys=True, indent=2), file=outf)

for category in ["ietf-admin", "ietf-technical", "irtf", "iab", "other"]:
    print("")
    print(f"Finding people only in category {category}:")
    with open(Path(F"2020-people-only-in-category-{category}.txt"), "w") as outf:
        for p in people.values():
            if categories_for_person[p.id] == [category]:
                print(f"  {p.name}")
                print(f"{p.id:8} | {p.name:36} | ", end="", file=outf)
                for l in lists_for_person[p.id]:
                    print(f"{l} ", end="", file=outf)
                print("", file=outf)

    print("")
    print(f"Finding drafts for people only in category {category}")
    with open(Path(F"2020-drafts-for-people-only-in-category-{category}.txt"), "w") as outf:
        for p in people.values():
            if categories_for_person[p.id] == [category]:
                print(f"  {p.name}")
                print(f"{p.id:8} | {p.name:36} | ", end="", file=outf)
                drafts = {}
                for da in dt.documents_authored_by_person(p):
                    d = dt.document(da.document)
                    if dt.document_type(d.type) == dt.document_type_from_slug("draft"):
                        print(f"    {d.name}")
                        for submit_uri in d.submissions:
                            submission = dt.submission(submit_uri)
                            if submission is not None and d.name not in drafts and submission.document_date.year == 2020:
                                print(f"      {submission.rev} -> {submission.document_date}")
                                drafts[d.name] = d.name
                                break
                for draft in drafts.values():
                    print(F"{draft} ", end="", file=outf)
                print("", file=outf)







# =================================================================================================================================
