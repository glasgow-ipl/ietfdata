# Copyright (C) 2024 University of Glasgow
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

import os
import sys
import textwrap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime             import date, datetime, timedelta, timezone
from pathlib              import Path
from ietfdata.datatracker import *


# Derive conflict lists for an IETF meeting.
#
# This finds all active working groups and research groups and, for each, 
# finds the set of active internet drafts and their authors. This is then
# used to derive a conflict list that can be used for agenda planning.
#
# The conflict list is saved in the file conflicts.txt


dt = DataTracker(cache_timeout = timedelta(hours = 12))

doc_state    = dt.document_state_type_from_slug("draft")
draft        = dt.document_type_from_slug("draft")
active_draft = dt.document_state_from_slug(state_type = doc_state, slug = "active")
active_group = dt.group_state_from_slug("active")
iesg         = dt.group_from_acronym("iesg")
irtf         = dt.group_from_acronym("irtf")

people_in_wg  = {}
wg_for_person = {}


def save_info(wg):
    people_in_wg[wg.acronym] = []
    for doc in dt.documents(group = wg, doctype = draft, state = active_draft):
        print(f"    {doc.name}")
        for author in dt.document_authors(doc):
            person = dt.person(author.person)
            print(f"      {person.resource_uri} {person.name}")
            if person.id not in people_in_wg[wg.acronym]:
                people_in_wg[wg.acronym].append(person.id)
            if person.id not in wg_for_person:
                wg_for_person[person.id] = []
            if wg.acronym not in wg_for_person[person.id]:
                wg_for_person[person.id].append(wg.acronym)


# Find adopted drafts for IETF working groups:
for area in dt.groups(state = active_group, parent = iesg):
    print(area.acronym)
    for wg in dt.groups(state = active_group, parent = area):
        if wg.type == GroupTypeNameURI(uri="/api/v1/name/grouptypename/wg/"):
            print(f"  {wg.acronym}")
            save_info(wg)

# Find adopted drafts for IETF research groups:
print("irtf")
for rg in dt.groups(state = active_group, parent = irtf):
    if rg.type == GroupTypeNameURI(uri="/api/v1/name/grouptypename/rg/"):
        print(f"  {rg.acronym}")
        save_info(rg)

# Find individual submissions:
print("individual")
no_group = dt.group(GroupURI(uri="/api/v1/group/group/1027/"))
for doc in dt.documents(group = no_group, doctype = draft, state = active_draft):
    print(f"  {doc.name}")
    related_group = doc.name.split("-")[2]
    if related_group in people_in_wg.keys():
        for author in dt.document_authors(doc):
            person = dt.person(author.person)
            print(f"      {person.resource_uri} {person.name}")
            if person.id not in people_in_wg[related_group]:
                people_in_wg[related_group].append(person.id)
            if person.id not in wg_for_person:
                wg_for_person[person.id] = []
            if related_group not in wg_for_person[person.id]:
                wg_for_person[person.id].append(related_group)

# Generate conflict lists:
conflicts = {}
for wg in people_in_wg.keys():
    conflicts[wg] = []
    for person_id in people_in_wg[wg]:
        for conflict in wg_for_person[person_id]:
            if conflict not in conflicts[wg] and conflict != wg:
                conflicts[wg].append(conflict)

# Print conflicts:
with open("conflicts.txt", "w") as outf:
    for group in people_in_wg.keys():
        print(f"", file=outf)
        print(f"Group {group.upper()}", file=outf)
        for conflict in conflicts[group]:
            print(f"  conflicts with {conflict.upper()}", file=outf)
            for person_id in people_in_wg[group]:
                if person_id in people_in_wg[conflict]:
                    person_uri = PersonURI(uri=f"/api/v1/person/person/{person_id}/")
                    person = dt.person(person_uri)
                    print(f"    due to author {person.name}", file=outf)


