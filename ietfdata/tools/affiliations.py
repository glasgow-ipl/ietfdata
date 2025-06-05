# Copyright (C) 2025 University of Glasgow
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

import json
import sys
import textwrap

from datetime import datetime, date
from pathlib  import Path
from typing   import List, Dict, Optional, Iterator

from ietfdata.datatracker import *
from ietfdata.rfcindex    import *

class AffiliationsForPerson:
    _pid: str
    _aff: List[Dict[str,str]]

    def __init__(self, pid:str) -> None:
        self._pid = pid
        self._aff = []


    def _add_at_start(self, date_:date, org_id:str) -> None:
        """
        Add an organisation, `org_id`, valid on `date_`, to the start of the
        list of known affiliations.
        """
        if org_id == self._aff[0]["org"]:
            print(f"    {self._pid} extend first affiliation {org_id} {self._aff[0]['start']} -> {date_}")
            self._aff[0]["start"] = date_.isoformat()
        else:
            print(f"    {self._pid} add first affiliation {org_id} {self._aff[0]['start']} -> {date_}")
            self._aff.insert(0, {"org"  : org_id,
                                 "start": date_.isoformat(), 
                                 "end"  : self._aff[0]["start"]})


    def _add_at_end(self, date_:date, org_id:str) -> None:
        """
        Add an organisation, `org_id`, valid on `date_`, to the end of the
        list of known affiliations.
        """
        if org_id == self._aff[-1]["org"]:
            print(f"    {self._pid} extend final affiliation {self._aff[-1]['org']} {self._aff[-1]['end']} -> {date_}")
            self._aff[-1]["end"] = date_.isoformat()
        else:
            print(f"    {self._pid} extend final affiliation {self._aff[-1]['org']} {self._aff[-1]['end']} -> {date_}")
            self._aff[-1]["end"] = date_.isoformat()
            print(f"   {self._pid} add final affiliation {org_id} on {date_}")
            self._aff.append({"org"  : org_id,
                              "start": date_.isoformat(),
                              "end"  : date_.isoformat()})


    def _add_in_middle(self, date_:date, org_id:str) -> None:
        """
        Add an organisation, `org_id`, valid on `date_`, in the middle of
        the list of known affiliations.
        """
        found = False
        new_aff = []
        for old_aff in self._aff:
            if date_.isoformat() == old_aff["start"] and date_.isoformat() == old_aff["end"]:
                found = True
                if org_id == old_aff["org"]:
                    print(f"    {self._pid} duplicate affiliation {old_aff['org']} on {date_}")
                    new_aff.append(old_aff)
                else:
                    print(f"    {self._pid} conflicting affiliation: {org_id} != {old_aff['org']} on {date_}")
            elif date_.isoformat() == old_aff["start"] and date_.isoformat() < old_aff["end"]:
                found = True
                if org_id != old_aff["org"]:
                    print(f"    {self._pid} add before: {org_id} on {date_}")
                    new_aff.append({"org"  : org_id,
                                    "start": date_.isoformat(),
                                    "end"  : date_.isoformat()})
                new_aff.append(old_aff)
            elif date_.isoformat() > old_aff["start"] and date_.isoformat() == old_aff["end"]:
                found = True
                new_aff.append(old_aff)
                if org_id != old_aff["org"]:
                    print(f"    {self._pid} add after: {org_id} on {date_}")
                    new_aff.append({"org"  : org_id,
                                    "start": date_.isoformat(),
                                    "end"  : date_.isoformat()})
            elif date_.isoformat() > old_aff["start"] and date_.isoformat() < old_aff["end"]:
                found = True
                if org_id == old_aff["org"]:
                    # Overlaps with a previously known affilation and date range
                    print(f"    {self._pid} affiliation {old_aff['org']} on {date_} is within known range {old_aff['start']} -> {old_aff['end']}")
                    new_aff.append(old_aff)
                else:
                    # Split an existing affiliation record
                    print(f"    {self._pid} Split affiliation:")
                    print(f"    {self._pid}   {old_aff['org']} {old_aff['start']} - {date_}")
                    print(f"    {self._pid}   {org_id} {date_} - {date_}")
                    print(f"    {self._pid}   {old_aff['org']} {date_} - {old_aff['end']}")
                    new_aff.append({"org": old_aff["org"], "start": old_aff["start"],  "end": date_.isoformat()})
                    new_aff.append({"org": org_id,         "start": date_.isoformat(), "end": date_.isoformat()})
                    new_aff.append({"org": old_aff["org"], "start": date_.isoformat(), "end": old_aff["end"]})
            else:
                # Date range doesn't match, pass through
                new_aff.append(old_aff)
        self._aff = new_aff
        if not found:
            raise KeyError(f"Unable to add {org_id} to {self._pid} on {date_}")


    def add(self, date_:date, org_id:str) -> None:
        if self._aff == []:
            print(f"    {self._pid} initial affiliation {org_id} {date_}")
            self._aff = [{"org"  : org_id,
                          "start": date_.isoformat(),
                          "end"  : date_.isoformat()}]
        else:
            if date_.isoformat() < self._aff[0]["start"]:
                self._add_at_start(date_, org_id)
            elif date_.isoformat() > self._aff[-1]["end"]:
                self._add_at_end(date_, org_id)
            else:
                self._add_in_middle(date_, org_id)


    def get(self) -> Dict[str,List[Dict[str,str]]]:
        res : Dict[str,List[Dict[str,str]]] = {"affiliations": []}
        for aff in self._aff:
            item = {"organisation": aff["org"], 
                    "start_date"  : aff["start"],
                    "end_date"    : aff["end"]}
            res["affiliations"].append(item)
        return res


    def print(self) -> None:
        for aff in self._aff:
            print(f"   {aff}")


class Affiliations:
    _affiliations_per_person: Dict[str,AffiliationsForPerson]

    def __init__(self) -> None: 
        self._affiliations_for_person : Dict[str,AffiliationsForPerson] = {}


    def add(self, date_:date, pid:str, org_id:str) -> None:
        if pid not in self._affiliations_for_person:
            self._affiliations_for_person[pid] = AffiliationsForPerson(pid)
            print(f"    {pid} created")
        self._affiliations_for_person[pid].add(date_, org_id)


    def save(self, affiliations_json:str) -> None:
        print(f"Saving to {affiliations_json}")
        res = {}
        for pid, aff in self._affiliations_for_person.items():
            res[pid] = aff.get()

        with open(affiliations_json, "w") as outf:
            json.dump(res, outf, indent=3)


def rfc_date(year:int, month:str) -> date:
    if month == "January":
        month_num = 1
    elif month == "February":
        month_num = 2
    elif month == "March":
        month_num = 3
    elif month == "April":
        month_num = 4
    elif month == "May":
        month_num = 5
    elif month == "June":
        month_num = 6
    elif month == "July":
        month_num = 7
    elif month == "August":
        month_num = 8
    elif month == "September":
        month_num = 9
    elif month == "October":
        month_num = 10
    elif month == "November":
        month_num = 11
    elif month == "December":
        month_num = 12
    else:
        print(f"Invalid month: {month}")
        sys.exit(1)
    return date(year, month_num, 1)



if __name__ == "__main__":
    print(f"*** ietfdata.tools.affiliations")

    if len(sys.argv) != 4:
        print('')
        print('Usage: python3 -m ietfdata.tools.affiliations <ietfdata.sqlite> <participants.json> <organisation.json> <affiliations.json>')
        sys.exit(1)

    print(f"Loading {sys.argv[2]}")
    with open(sys.argv[2], "r") as inf:
        participants = json.load(inf)
        print(f"  {len(participants):5} participants")
        emails = {}
        for pid in participants:
            if "email" in participants[pid]:
                for email in participants[pid]["email"]:
                    emails[email] = pid
            #else:
            #    print(f"      {pid} doesn't have email")
        print(f"  {len(emails):5} email addresses")


    print(f"Loading {sys.argv[3]}")
    with open(sys.argv[3], "r") as inf:
        organisations = json.load(inf)
        print(f"  {len(organisations):5} organisations")
        org_names = {}
        for org in organisations:
            for name in organisations[org]["names"]:
                org_names[name] = org
        print(f"  {len(org_names):5} organisation names")


    dt = DataTracker(DTBackendArchive(sqlite_file=sys.argv[1]))
    ri = RFCIndex(cache_dir = "cache")
    af = Affiliations()

    print("Finding affiliations of RFC authors:")
    for rfc in ri.rfcs(since="1995-01"):
        print(f"  {rfc.doc_id}: {textwrap.shorten(rfc.title, width=80, placeholder='...')}")
        dt_document = dt.document_from_rfc(rfc.doc_id)
        if dt_document is not None:
            for dt_author in dt.document_authors(dt_document):
                if dt_author.affiliation == "" or dt_author.email is None:
                    continue
                affil = dt_author.affiliation.replace("\n", " ")
                email = dt.email(dt_author.email)
                if email is None:
                    continue
                date_ = rfc_date(rfc.year, rfc.month) # FIXME get the actual publication date
                if email.address not in emails or affil not in org_names:
                    print(f"skipped {email} {affil}")
                    continue
                pid = emails[email.address]
                oid = org_names[affil]
                af.add(date_, pid, oid)
    print("")

    print("Finding affiliations in internet-draft submissions:")
    for submission in dt.submissions():
        print(f"  {submission.name}-{submission.rev}")
        for authors in submission.parse_authors():
            if "affiliation" not in authors:
                continue
            if "email" not in authors:
                continue
            if authors["email"] not in emails or authors["affiliation"] not in org_names:
                continue
            pid = emails[authors["email"]]
            oid = org_names[authors["affiliation"]]
            af.add(submission.submission_date, pid, oid)
    print("")

    print("Finding affiliations in meeting registration records:")
    for reg in dt.meeting_registrations():
        meeting = dt.meeting(reg.meeting)
        assert meeting is not None
        date_  = meeting.date
        email = reg.email
        affil = reg.affiliation
        if email not in emails or affil not in org_names:
            print(f"skipped {email} {affil}")
            continue
        pid = emails[email]
        oid = org_names[affil]
        af.add(date_, pid, oid)
    print("")

    af.save(sys.argv[4])

